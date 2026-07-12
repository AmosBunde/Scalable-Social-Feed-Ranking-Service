"""Kafka producer/consumer wrapper with circuit breaker and retry logic."""

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: timedelta = timedelta(seconds=30)
    _failure_count: int = field(default=0, init=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _last_failure_time: datetime | None = field(default=None, init=False)

    @property
    def state(self) -> CircuitState:
        if (
            self._state == CircuitState.OPEN
            and self._last_failure_time
            and datetime.now(UTC) - self._last_failure_time >= self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = datetime.now(UTC)
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker opened after %d failures", self._failure_count)

    @property
    def is_callable(self) -> bool:
        return self.state != CircuitState.OPEN


try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

    class KafkaClient:
        """Async Kafka producer/consumer with circuit breaker protection."""

        def __init__(
            self,
            bootstrap_servers: str,
            client_id: str = "sfr-client",
        ) -> None:
            self.bootstrap_servers = bootstrap_servers
            self.client_id = client_id
            self._producer: AIOKafkaProducer | None = None
            self._consumers: dict[str, AIOKafkaConsumer] = {}
            self._circuit = CircuitBreaker()

        async def start_producer(self) -> None:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
                retry_backoff_ms=100,
            )
            await self._producer.start()
            logger.info("Kafka producer started for %s", self.bootstrap_servers)

        async def stop_producer(self) -> None:
            if self._producer:
                await self._producer.stop()

        async def produce(self, topic: str, value: dict[str, Any], key: str | None = None) -> None:
            if not self._circuit.is_callable:
                raise ConnectionError("Circuit breaker is open, Kafka unavailable")
            if not self._producer:
                raise RuntimeError("Producer not started. Call start_producer() first.")
            try:
                await self._producer.send_and_wait(topic, value=value, key=key)
                self._circuit.record_success()
            except Exception as exc:
                self._circuit.record_failure()
                logger.error("Kafka produce failed for topic %s: %s", topic, exc)
                raise

        async def start_consumer(
            self,
            topic: str,
            group_id: str,
            handler: Callable,
            auto_offset_reset: str = "latest",
        ) -> None:
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                enable_auto_commit=False,
            )
            await consumer.start()
            self._consumers[topic] = consumer
            logger.info("Kafka consumer started for topic %s", topic)

            asyncio.create_task(self._consume_loop(consumer, handler, topic))

        async def _consume_loop(
            self, consumer: AIOKafkaConsumer, handler: Callable, topic: str
        ) -> None:
            try:
                async for msg in consumer:
                    try:
                        await handler(msg.value)
                        await consumer.commit()
                    except Exception as exc:
                        logger.error("Handler error for topic %s: %s", topic, exc, exc_info=True)
            except Exception as exc:
                logger.critical("Consumer loop crashed for %s: %s", topic, exc)
            finally:
                await consumer.stop()

        async def stop_all(self) -> None:
            await self.stop_producer()
            for consumer in self._consumers.values():
                await consumer.stop()
            self._consumers.clear()

except ImportError:
    logger.info("aiokafka not installed; KafkaClient unavailable")
