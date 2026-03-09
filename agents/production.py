"""
Production configuration for Protocol2USDM.

Provides Redis-backed Context Store and RabbitMQ-backed Message Queue
for production deployments. Falls back to in-memory implementations
when external services are unavailable.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from agents.context_store import ContextStore, ContextEntity, EntityProvenance
from agents.message_queue import MessageQueue, AgentMessage

logger = logging.getLogger(__name__)


class RedisContextStore(ContextStore):
    """
    Redis-backed Context Store for production use.

    Extends the in-memory ContextStore with Redis persistence.
    Entities are stored as JSON in Redis hashes, with automatic
    serialization/deserialization.

    Falls back to in-memory storage if Redis is unavailable.
    """

    def __init__(self, redis_url: str = None):
        super().__init__()
        self._redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self._redis = None
        self._prefix = "p2u:entity:"
        self._connected = False

    def connect(self) -> bool:
        """Connect to Redis. Returns True if successful."""
        try:
            import redis
            self._redis = redis.from_url(self._redis_url, decode_responses=True)
            self._redis.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self._redis_url}")
            return True
        except ImportError:
            logger.warning("redis package not installed, using in-memory store")
            return False
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using in-memory store")
            return False

    def add_entity(self, entity: ContextEntity) -> None:
        """Add entity to both in-memory and Redis."""
        super().add_entity(entity)
        if self._connected and self._redis:
            try:
                key = f"{self._prefix}{entity.id}"
                data = {
                    "id": entity.id,
                    "entity_type": entity.entity_type,
                    "data": json.dumps(entity.data),
                    "provenance": json.dumps({
                        "entity_id": entity.provenance.entity_id if entity.provenance else "",
                        "source_agent_id": entity.provenance.source_agent_id if entity.provenance else "",
                        "confidence_score": entity.provenance.confidence_score if entity.provenance else 0.0,
                    }) if entity.provenance else "{}",
                }
                self._redis.hset(key, mapping=data)
                self._redis.sadd("p2u:entity_ids", entity.id)
            except Exception as e:
                logger.error(f"Redis write failed for entity {entity.id}: {e}")

    def sync_to_redis(self) -> int:
        """Sync all in-memory entities to Redis. Returns count synced."""
        if not self._connected or not self._redis:
            return 0
        count = 0
        for entity in self.query_entities():
            try:
                key = f"{self._prefix}{entity.id}"
                data = {
                    "id": entity.id,
                    "entity_type": entity.entity_type,
                    "data": json.dumps(entity.data),
                }
                self._redis.hset(key, mapping=data)
                self._redis.sadd("p2u:entity_ids", entity.id)
                count += 1
            except Exception:
                pass
        return count

    def sync_from_redis(self) -> int:
        """Load all entities from Redis into memory. Returns count loaded."""
        if not self._connected or not self._redis:
            return 0
        count = 0
        try:
            entity_ids = self._redis.smembers("p2u:entity_ids")
            for eid in entity_ids:
                key = f"{self._prefix}{eid}"
                raw = self._redis.hgetall(key)
                if raw:
                    entity = ContextEntity(
                        id=raw["id"],
                        entity_type=raw.get("entity_type", "unknown"),
                        data=json.loads(raw.get("data", "{}")),
                    )
                    try:
                        super().add_entity(entity)
                        count += 1
                    except ValueError:
                        pass  # Already exists
        except Exception as e:
            logger.error(f"Redis sync failed: {e}")
        return count


class RabbitMQMessageQueue(MessageQueue):
    """
    RabbitMQ-backed Message Queue for production use.

    Extends the in-memory MessageQueue with RabbitMQ persistence.
    Falls back to in-memory queue if RabbitMQ is unavailable.
    """

    def __init__(self, rabbitmq_url: str = None):
        super().__init__()
        self._rabbitmq_url = rabbitmq_url or os.environ.get(
            "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"
        )
        self._connection = None
        self._channel = None
        self._connected = False
        self._exchange = "p2u_agents"
        self._queue_name = "p2u_tasks"

    def connect(self) -> bool:
        """Connect to RabbitMQ. Returns True if successful."""
        try:
            import pika
            params = pika.URLParameters(self._rabbitmq_url)
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()

            # Declare exchange and queue
            self._channel.exchange_declare(
                exchange=self._exchange, exchange_type="topic", durable=True
            )
            self._channel.queue_declare(queue=self._queue_name, durable=True)
            self._channel.queue_bind(
                exchange=self._exchange, queue=self._queue_name, routing_key="agent.*"
            )

            self._connected = True
            logger.info(f"Connected to RabbitMQ at {self._rabbitmq_url}")
            return True
        except ImportError:
            logger.warning("pika package not installed, using in-memory queue")
            return False
        except Exception as e:
            logger.warning(f"RabbitMQ connection failed: {e}, using in-memory queue")
            return False

    def publish(self, routing_key: str, message_data: dict) -> bool:
        """Publish a message to RabbitMQ."""
        if not self._connected or not self._channel:
            return False
        try:
            import pika
            self._channel.basic_publish(
                exchange=self._exchange,
                routing_key=routing_key,
                body=json.dumps(message_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type="application/json",
                ),
            )
            return True
        except Exception as e:
            logger.error(f"RabbitMQ publish failed: {e}")
            return False

    def close(self):
        """Close the RabbitMQ connection."""
        if self._connection and not self._connection.is_closed:
            try:
                self._connection.close()
            except Exception:
                pass
        self._connected = False


def create_production_context_store() -> ContextStore:
    """Create a production Context Store (Redis-backed if available)."""
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        store = RedisContextStore(redis_url)
        if store.connect():
            return store
    logger.info("Using in-memory Context Store")
    return ContextStore()


def create_production_message_queue() -> MessageQueue:
    """Create a production Message Queue (RabbitMQ-backed if available)."""
    rabbitmq_url = os.environ.get("RABBITMQ_URL")
    if rabbitmq_url:
        mq = RabbitMQMessageQueue(rabbitmq_url)
        if mq.connect():
            return mq
    logger.info("Using in-memory Message Queue")
    return MessageQueue()
