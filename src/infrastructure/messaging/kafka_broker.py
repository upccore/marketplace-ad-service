import json
import typing

from aiokafka import AIOKafkaProducer

from src.application.ports.message_broker import MessageBroker
from src.tracing import TRACE_ID_HEADER, new_trace_id


class KafkaMessageBroker(MessageBroker):
    def __init__(self, producer: AIOKafkaProducer, topic: str) -> None:
        self._producer = producer
        self._topic = topic

    async def send(
        self,
        payload: dict[str, typing.Any],
        trace_id: str | None = None,
    ) -> None:
        headers = [(TRACE_ID_HEADER, (trace_id or new_trace_id()).encode())]
        await self._producer.send_and_wait(self._topic, payload, headers=headers)


def serialize(value: dict[str, typing.Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")
