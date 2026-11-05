import asyncio
import json
import logging
import os
import signal
import time
from pathlib import Path

import aio_pika
from pydantic import ValidationError

from birdlab.errors import InputError, ModelError
from bird_worker.contracts import AnalysisRequest, encode, event
from bird_worker.inference import infer
from bird_worker.storage import Ledger


logger = logging.getLogger("birdlab.worker")
MAX_ATTEMPTS = 4
STATE = Path(os.getenv("BIRD_WORKER_STATE", ".worker-state"))


async def connect():
    user = os.environ.get("RABBITMQ_USERNAME", "birdlab")
    password = os.environ.get("RABBITMQ_PASSWORD", "")
    if not password or user == "guest":
        raise ValueError("Налаштуйте окремі RABBITMQ_USERNAME та RABBITMQ_PASSWORD.")
    return await aio_pika.connect_robust(host=os.getenv("RABBITMQ_HOST", "127.0.0.1"), port=int(os.getenv("RABBITMQ_PORT", "5672")), login=user, password=password, virtualhost=os.getenv("RABBITMQ_VHOST", "birdlab"), timeout=10, reconnect_interval=5, heartbeat=20)


async def publish(exchange, body: bytes, retry: int = 0, routing_key="analysis.event"):
    payload = json.loads(body)
    confirmation = await exchange.publish(aio_pika.Message(body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT, content_type="application/json", message_id=payload["eventId"], correlation_id=payload["correlationId"], headers={"x-retry": retry}), routing_key=routing_key, mandatory=True, timeout=10)
    if confirmation is None or confirmation is False:
        raise RuntimeError("Брокер не підтвердив публікацію.")


class Handler:
    def __init__(self, ledger, exchange, retry_exchange, root, offline, inference=infer):
        self.ledger = ledger
        self.exchange = exchange
        self.retry_exchange = retry_exchange
        self.root = root
        self.offline = offline
        self.inference = inference

    async def deliver(self, message):
        try:
            request = AnalysisRequest.read(message.body)
            attempts, final = self.ledger.get(request)
        except (ValidationError, ValueError):
            logger.warning("Некоректне завдання; відправлено до DLQ")
            await message.reject(requeue=False)
            return
        if final is not None:
            await self.finish(message, final)
            return
        if attempts >= MAX_ATTEMPTS:
            final = self.ledger.finish(request, encode(event(request, "failed", attempts, errorMessage="Вичерпано спроби після переривання worker. Перевірте журнал і DLQ.")))
            await self.finish(message, final)
            return
        attempt = self.ledger.begin_attempt(request)
        await publish(self.exchange, encode(event(request, "processing", attempt)))
        logger.info("analysis=%s correlation=%s attempt=%s", request.analysisId, request.correlationId, attempt)
        try:
            fields = await asyncio.to_thread(self.inference, request, self.root, self.offline)
            final = encode(event(request, "completed", attempt, **fields))
        except InputError as exc:
            final = encode(event(request, "failed", attempt, errorMessage=str(exc)[:2000]))
        except (ModelError, OSError, TimeoutError) as exc:
            if attempt < MAX_ATTEMPTS:
                await publish(self.retry_exchange, message.body, retry=attempt, routing_key=f"requests.{attempt}")
                await message.ack()
                logger.warning("analysis=%s retry=%s reason=%s", request.analysisId, attempt, type(exc).__name__)
                return
            final = encode(event(request, "failed", attempt, errorMessage=f"Тимчасова помилка не усунута за {MAX_ATTEMPTS} спроби: {type(exc).__name__}."))
        except Exception as exc:
            logger.exception("Непередбачена помилка inference")
            final = encode(event(request, "failed", attempt, errorMessage=f"Помилка AI Worker: {type(exc).__name__}."))
        final = self.ledger.finish(request, final)
        await self.finish(message, final)

    async def finish(self, message, final):
        await publish(self.exchange, final)
        if json.loads(final)["status"] == "failed":
            await message.reject(requeue=False)
        else:
            await message.ack()


async def heartbeat(connection, stop):
    while not stop.is_set():
        path = STATE / "heartbeat"
        if connection.connected.is_set():
            path.write_text(str(time.time()), encoding="ascii")
        try:
            await asyncio.wait_for(stop.wait(), 5)
        except TimeoutError:
            pass


async def run():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))
    ledger = Ledger(STATE)
    try:
        while not stop.is_set():
            try:
                connection = await connect()
                async with connection:
                    channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
                    await channel.set_qos(prefetch_count=1)
                    exchange = await channel.declare_exchange("bird.analysis", aio_pika.ExchangeType.DIRECT, durable=True)
                    retry_exchange = await channel.declare_exchange("bird.analysis.retry", aio_pika.ExchangeType.DIRECT, durable=True)
                    queue = await channel.declare_queue("bird.analysis.requests", durable=True, arguments={"x-queue-type": "quorum"})
                    await queue.bind(exchange, "analysis.requested")
                    handler = Handler(ledger, exchange, retry_exchange, Path(os.getenv("BIRD_MEDIA_ROOT", "central-server/storage")), os.getenv("BIRD_OFFLINE", "true").lower() == "true")
                    pulse = asyncio.create_task(heartbeat(connection, stop))
                    try:
                        async with queue.iterator(no_ack=False) as messages:
                            while not stop.is_set():
                                delivery = asyncio.create_task(messages.__anext__())
                                stopped = asyncio.create_task(stop.wait())
                                done, _ = await asyncio.wait({delivery, stopped}, return_when=asyncio.FIRST_COMPLETED)
                                if delivery not in done:
                                    delivery.cancel()
                                    await asyncio.gather(delivery, return_exceptions=True)
                                    break
                                stopped.cancel()
                                await asyncio.gather(stopped, return_exceptions=True)
                                message = delivery.result()
                                try:
                                    await handler.deliver(message)
                                except Exception as exc:
                                    logger.warning("Доставку не підтверджено: %s", type(exc).__name__)
                                    await asyncio.sleep(5)
                                    if not message.channel.is_closed and not message.processed:
                                        await message.nack(requeue=True)
                    finally:
                        pulse.cancel()
                        await asyncio.gather(pulse, return_exceptions=True)
            except Exception as exc:
                logger.warning("Worker перепідключається: %s", type(exc).__name__)
                try:
                    await asyncio.wait_for(stop.wait(), 5)
                except TimeoutError:
                    pass
    finally:
        ledger.close()
        (STATE / "heartbeat").unlink(missing_ok=True)
