import asyncio
import json
import sys
import aio_pika
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bird_worker.runtime import connect, publish


async def replay():
    connection = await connect()
    restored = 0
    retained = 0
    async with connection:
        channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
        await channel.set_qos(prefetch_count=1)
        exchange = await channel.get_exchange("bird.analysis", ensure=True)
        dead_exchange = await channel.get_exchange("bird.analysis.dlx", ensure=True)
        queue = await channel.get_queue("bird.analysis.dead", ensure=True)
        count = (await queue.declare()).message_count
        async def retain(message):
            headers = {key: value for key, value in (message.headers or {}).items() if key != "x-delivery-count"}
            confirmed = await dead_exchange.publish(aio_pika.Message(message.body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT, content_type=message.content_type, message_id=message.message_id, correlation_id=message.correlation_id, headers=headers), routing_key="analysis.dead", mandatory=True, timeout=10)
            if confirmed is None or confirmed is False:
                raise RuntimeError("Брокер не підтвердив збереження DLQ-повідомлення.")
            await message.ack()
        for _ in range(count):
            message = await queue.get(fail=False, no_ack=False)
            if message is None:
                break
            try:
                body = json.loads(message.body)
                if isinstance(body, dict) and body.get("schemaVersion") == 1 and body.get("status") in {"processing", "completed", "failed"}:
                    await publish(exchange, message.body)
                    await message.ack()
                    restored += 1
                else:
                    await retain(message)
                    retained += 1
            except (ValueError, KeyError):
                await retain(message)
                retained += 1
    print(json.dumps({"results_replayed_with_confirms": restored, "other_messages_retained": retained}))


if __name__ == "__main__":
    asyncio.run(replay())
