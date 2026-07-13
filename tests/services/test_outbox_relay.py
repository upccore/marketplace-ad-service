from typing import Any

import pytest

from src.application.ports.message_broker import MessageBroker
from src.application.services.outbox_relay import OutboxRelay
from src.tracing import reset_trace_id, set_trace_id
from tests.conftest import FakeMessageBroker, FakeUnitOfWork


class RaisingBroker(MessageBroker):
    async def send(self, payload: dict[str, Any], trace_id: str | None = None) -> None:
        raise RuntimeError("kafka unavailable")


@pytest.mark.asyncio
async def test_relay_sends_and_marks_published(
    fake_uow: FakeUnitOfWork, fake_broker: FakeMessageBroker
) -> None:
    await fake_uow.outbox.add("ad.created", {"ad_id": 1})
    await fake_uow.outbox.add("ad.updated", {"ad_id": 1})

    relay = OutboxRelay(uow_factory=lambda: fake_uow, broker=fake_broker)
    processed = await relay._process_batch()

    assert processed == 2
    assert fake_broker.sent == [
        {"event": "ad.created", "payload": {"ad_id": 1}},
        {"event": "ad.updated", "payload": {"ad_id": 1}},
    ]
    assert fake_uow.committed
    assert fake_uow.outbox.messages == []


@pytest.mark.asyncio
async def test_relay_noop_when_outbox_empty(
    fake_uow: FakeUnitOfWork, fake_broker: FakeMessageBroker
) -> None:
    relay = OutboxRelay(uow_factory=lambda: fake_uow, broker=fake_broker)
    processed = await relay._process_batch()

    assert processed == 0
    assert fake_broker.sent == []
    assert not fake_uow.committed


@pytest.mark.asyncio
async def test_relay_rolls_back_and_leaves_messages_on_broker_failure(
    fake_uow: FakeUnitOfWork,
) -> None:
    await fake_uow.outbox.add("ad.created", {"ad_id": 1})

    relay = OutboxRelay(uow_factory=lambda: fake_uow, broker=RaisingBroker())

    with pytest.raises(RuntimeError):
        await relay._process_batch()

    assert not fake_uow.committed
    assert fake_uow.rolled_back
    assert len(fake_uow.outbox.messages) == 1


@pytest.mark.asyncio
async def test_relay_forwards_trace_id_from_outbox_row(
    fake_uow: FakeUnitOfWork, fake_broker: FakeMessageBroker
) -> None:
    token = set_trace_id("trace-abc")
    try:
        await fake_uow.outbox.add("ad.created", {"ad_id": 1})
    finally:
        reset_trace_id(token)

    relay = OutboxRelay(uow_factory=lambda: fake_uow, broker=fake_broker)
    await relay._process_batch()

    assert fake_broker.trace_ids == ["trace-abc"]
