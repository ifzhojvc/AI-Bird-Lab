import asyncio
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai-server"))

from birdlab.errors import InputError, ModelError
from bird_worker.contracts import AnalysisRequest, encode
from bird_worker.runtime import Handler
from bird_worker.storage import Ledger, read_media


def request(**fields):
    return AnalysisRequest.read(encode({"schemaVersion": 1, "eventId": str(uuid4()), "analysisId": str(uuid4()), "analysisType": "image", "fileId": str(uuid4()), "fileSha256": hashlib.sha256(b"bird").hexdigest(), "createdAt": "2026-10-29T10:00:00Z", "correlationId": str(uuid4()), **fields}))


def delivery(body):
    return Mock(body=body, ack=AsyncMock(), reject=AsyncMock())


def unit_inference(*args):
    return {"predictedSpecies": "unit first", "confidence": .8, "predictions": [{"species": f"unit {i}", "scientificName": None, "confidence": score, "rank": i} for i, score in enumerate([.8, .15, .05], 1)], "modelName": "unit-model", "modelRevision": "unit", "elapsedSeconds": .1, "metadata": {"mock_used": True}}


@pytest.mark.parametrize("fields", [{"schemaVersion": 2}, {"analysisType": "../../evil"}, {"fileId": "../../birds.db"}, {"absolutePath": "C:/secret"}, {"fileSha256": "bad"}, {"eventId": "00000000-0000-0000-0000-000000000000"}, {"createdAt": "2026-10-29"}])
def test_request_rejects_unsafe_contract(fields):
    with pytest.raises(ValueError):
        request(**fields)


def test_file_resolution_hash_and_no_arbitrary_paths(tmp_path):
    r = request()
    path = tmp_path / f"{r.fileId.hex}.jpg"
    path.write_bytes(b"bird")
    assert read_media(tmp_path, r)[0] == b"bird"
    path.write_bytes(b"modified")
    with pytest.raises(InputError, match="сума"):
        read_media(tmp_path, r)
    path.unlink()
    with pytest.raises(InputError, match="відсутній"):
        read_media(tmp_path, r)


def test_ledger_survives_restart_and_prevents_changed_request(tmp_path):
    r = request()
    ledger = Ledger(tmp_path)
    ledger.get(r)
    assert ledger.begin_attempt(r) == 1
    ledger.finish(r, b"stored-result")
    ledger.close()
    restored = Ledger(tmp_path)
    try:
        assert restored.get(r) == (1, b"stored-result")
        with pytest.raises(ValueError):
            restored.get(request(analysisId=str(r.analysisId)))
    finally:
        restored.close()


def test_success_acknowledges_after_confirm_and_redelivery_uses_saved_result(tmp_path):
    async def scenario():
        ledger = Ledger(tmp_path)
        r = request()
        message = delivery(r.model_dump_json().encode())
        order = []
        async def confirmed(*args, **kwargs):
            order.append("confirmed")
            return True
        message.ack.side_effect = lambda: order.append("ack")
        exchange = Mock(publish=AsyncMock(side_effect=confirmed))
        inference = Mock(side_effect=unit_inference)
        handler = Handler(ledger, exchange, exchange, tmp_path, True, inference)
        try:
            await handler.deliver(message)
            assert order == ["confirmed", "confirmed", "ack"]
            again = delivery(message.body)
            await handler.deliver(again)
            assert inference.call_count == 1
            assert exchange.publish.call_args_list[-1].args[0].body == ledger.get(r)[1]
            again.ack.assert_awaited_once()
        finally:
            ledger.close()
    asyncio.run(scenario())


def test_unconfirmed_result_does_not_ack_and_is_replayed_after_restart(tmp_path):
    async def scenario():
        r = request()
        ledger = Ledger(tmp_path)
        exchange = Mock(publish=AsyncMock(side_effect=[True, RuntimeError("unit confirm lost")]))
        message = delivery(r.model_dump_json().encode())
        handler = Handler(ledger, exchange, exchange, tmp_path, True, unit_inference)
        with pytest.raises(RuntimeError):
            await handler.deliver(message)
        message.ack.assert_not_awaited()
        assert ledger.get(r)[1] is not None
        ledger.close()
        restored = Ledger(tmp_path)
        no_inference = Mock(side_effect=AssertionError("must reuse final"))
        confirmed = Mock(publish=AsyncMock(return_value=True))
        try:
            await Handler(restored, confirmed, confirmed, tmp_path, True, no_inference).deliver(delivery(message.body))
            no_inference.assert_not_called()
        finally:
            restored.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("permanent", [True, False])
def test_permanent_errors_fail_and_transient_errors_have_bounded_delayed_retries(tmp_path, permanent):
    async def scenario():
        ledger = Ledger(tmp_path)
        r = request()
        exchange = Mock(publish=AsyncMock(return_value=True))
        retry = Mock(publish=AsyncMock(return_value=True))
        error = InputError("unit corrupt image") if permanent else ModelError("unit unavailable")
        handler = Handler(ledger, exchange, retry, tmp_path, True, Mock(side_effect=error))
        try:
            for _ in range(1 if permanent else 4):
                message = delivery(r.model_dump_json().encode())
                await handler.deliver(message)
            message.reject.assert_awaited_once_with(requeue=False)
            assert json.loads(ledger.get(r)[1])["status"] == "failed"
            assert retry.publish.await_count == (0 if permanent else 3)
            assert ledger.get(r)[0] == (1 if permanent else 4)
        finally:
            ledger.close()
    asyncio.run(scenario())


def test_invalid_json_goes_to_dlq_without_inference(tmp_path):
    async def scenario():
        ledger = Ledger(tmp_path)
        message = delivery(b"{}")
        inference = Mock()
        try:
            await Handler(ledger, Mock(), Mock(), tmp_path, True, inference).deliver(message)
            message.reject.assert_awaited_once_with(requeue=False)
            inference.assert_not_called()
        finally:
            ledger.close()
    asyncio.run(scenario())
