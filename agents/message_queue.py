"""
Message Queue for inter-agent communication.

Provides priority-based message ordering, persistence for recovery,
dead-letter queue, message filtering, and timeout handling.
"""

import heapq
import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of inter-agent messages."""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    ERROR = "error"
    STATUS = "status"


class Priority(Enum):
    """Message priority levels."""
    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass
class AgentMessage:
    """Message exchanged between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: str = ""  # Empty for broadcasts
    message_type: MessageType = MessageType.REQUEST
    timestamp: datetime = field(default_factory=datetime.now)
    priority: Priority = Priority.NORMAL
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    timeout_ms: int = 30000
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timeout_ms": self.timeout_ms,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(
            id=data["id"],
            sender_id=data["sender_id"],
            receiver_id=data.get("receiver_id", ""),
            message_type=MessageType(data["message_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=Priority(data["priority"]),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id"),
            timeout_ms=data.get("timeout_ms", 30000),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )

    def __lt__(self, other: "AgentMessage") -> bool:
        """For heap ordering: lower priority value = higher priority."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.timestamp < other.timestamp


class MessageQueue:
    """
    Priority-based message queue for inter-agent communication.

    Features:
    - Priority-based ordering (HIGH > NORMAL > LOW)
    - Per-agent mailboxes
    - Message persistence for recovery
    - Dead-letter queue for failed messages
    - Message filtering by type and capability
    - Timeout handling with automatic retry
    - Broadcast support
    - Message logging
    """

    def __init__(self):
        self._mailboxes: Dict[str, List[AgentMessage]] = defaultdict(list)
        self._subscriptions: Dict[str, Set[MessageType]] = defaultdict(set)
        self._dead_letters: List[AgentMessage] = []
        self._message_log: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._events: Dict[str, threading.Event] = defaultdict(threading.Event)

    # --- Publishing ---

    def publish(self, message: AgentMessage) -> None:
        """
        Publish a message. Routes to receiver's mailbox or broadcasts.
        """
        with self._lock:
            self._log_message(message, "published")

            if message.message_type == MessageType.BROADCAST:
                # Deliver to all subscribers
                for agent_id, subscribed_types in self._subscriptions.items():
                    if (agent_id != message.sender_id and
                            (MessageType.BROADCAST in subscribed_types or not subscribed_types)):
                        heapq.heappush(self._mailboxes[agent_id], message)
                        self._events[agent_id].set()
            elif message.receiver_id:
                # Direct delivery
                heapq.heappush(self._mailboxes[message.receiver_id], message)
                self._events[message.receiver_id].set()
            else:
                logger.warning(f"Message {message.id} has no receiver and is not a broadcast")

    # --- Subscribing ---

    def subscribe(self, agent_id: str,
                  message_types: Optional[List[MessageType]] = None) -> None:
        """Subscribe an agent to receive messages of specified types."""
        with self._lock:
            if message_types:
                self._subscriptions[agent_id].update(message_types)
            else:
                self._subscriptions[agent_id] = set()  # Subscribe to all

    def unsubscribe(self, agent_id: str) -> None:
        """Remove all subscriptions for an agent."""
        with self._lock:
            self._subscriptions.pop(agent_id, None)

    # --- Polling ---

    def poll(self, agent_id: str, timeout_ms: int = 1000) -> Optional[AgentMessage]:
        """
        Poll for the next message for an agent.
        Blocks up to timeout_ms. Returns None if no message available.
        """
        deadline = time.monotonic() + (timeout_ms / 1000.0)

        while True:
            with self._lock:
                mailbox = self._mailboxes.get(agent_id, [])
                if mailbox:
                    message = heapq.heappop(mailbox)
                    if not mailbox:
                        self._events[agent_id].clear()
                    self._log_message(message, "delivered")
                    return message

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None

            self._events[agent_id].wait(timeout=min(remaining, 0.1))

    def poll_filtered(self, agent_id: str, message_type: MessageType,
                      timeout_ms: int = 1000) -> Optional[AgentMessage]:
        """Poll for a message of a specific type."""
        deadline = time.monotonic() + (timeout_ms / 1000.0)

        while True:
            with self._lock:
                mailbox = self._mailboxes.get(agent_id, [])
                for i, msg in enumerate(mailbox):
                    if msg.message_type == message_type:
                        mailbox.pop(i)
                        heapq.heapify(mailbox)
                        self._log_message(msg, "delivered_filtered")
                        return msg

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None

            self._events[agent_id].wait(timeout=min(remaining, 0.1))

    # --- Acknowledgment ---

    def acknowledge(self, message_id: str) -> None:
        """Acknowledge successful processing of a message."""
        self._log_message_event(message_id, "acknowledged")

    # --- Dead Letter Queue ---

    def dead_letter(self, message: AgentMessage, reason: str) -> None:
        """Move a message to the dead-letter queue."""
        with self._lock:
            message.payload["_dead_letter_reason"] = reason
            message.payload["_dead_letter_at"] = datetime.now().isoformat()
            self._dead_letters.append(message)
            self._log_message(message, f"dead_lettered: {reason}")

    def get_dead_letters(self) -> List[AgentMessage]:
        """Get all messages in the dead-letter queue."""
        with self._lock:
            return list(self._dead_letters)

    def retry_or_dead_letter(self, message: AgentMessage, reason: str) -> bool:
        """
        Retry a message or move to dead-letter queue if max retries exceeded.
        Returns True if retried, False if dead-lettered.
        """
        if message.retry_count < message.max_retries:
            message.retry_count += 1
            self.publish(message)
            return True
        else:
            self.dead_letter(message, reason)
            return False

    # --- Queue Management ---

    def pending_count(self, agent_id: str) -> int:
        """Number of pending messages for an agent."""
        with self._lock:
            return len(self._mailboxes.get(agent_id, []))

    def total_pending(self) -> int:
        """Total pending messages across all mailboxes."""
        with self._lock:
            return sum(len(mb) for mb in self._mailboxes.values())

    def clear_mailbox(self, agent_id: str) -> int:
        """Clear all messages for an agent. Returns count cleared."""
        with self._lock:
            count = len(self._mailboxes.get(agent_id, []))
            self._mailboxes[agent_id] = []
            self._events[agent_id].clear()
            return count

    # --- Persistence ---

    def serialize(self) -> Dict[str, Any]:
        """Serialize queue state for persistence."""
        with self._lock:
            return {
                "mailboxes": {
                    agent_id: [msg.to_dict() for msg in msgs]
                    for agent_id, msgs in self._mailboxes.items()
                },
                "dead_letters": [msg.to_dict() for msg in self._dead_letters],
                "subscriptions": {
                    agent_id: [mt.value for mt in types]
                    for agent_id, types in self._subscriptions.items()
                },
                "serialized_at": datetime.now().isoformat(),
            }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "MessageQueue":
        """Deserialize queue state from persistence."""
        queue = cls()
        for agent_id, msgs in data.get("mailboxes", {}).items():
            for msg_data in msgs:
                msg = AgentMessage.from_dict(msg_data)
                heapq.heappush(queue._mailboxes[agent_id], msg)
        for msg_data in data.get("dead_letters", []):
            queue._dead_letters.append(AgentMessage.from_dict(msg_data))
        for agent_id, types in data.get("subscriptions", {}).items():
            queue._subscriptions[agent_id] = {MessageType(t) for t in types}
        return queue

    # --- Logging ---

    def _log_message(self, message: AgentMessage, event: str) -> None:
        entry = {
            "message_id": message.id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "message_type": message.message_type.value,
            "priority": message.priority.value,
            "event": event,
            "timestamp": datetime.now().isoformat(),
        }
        self._message_log.append(entry)
        logger.debug(f"MQ [{event}] {message.sender_id} -> {message.receiver_id}: "
                     f"{message.message_type.value} (id={message.id[:8]})")

    def _log_message_event(self, message_id: str, event: str) -> None:
        self._message_log.append({
            "message_id": message_id,
            "event": event,
            "timestamp": datetime.now().isoformat(),
        })

    def get_message_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent message log entries."""
        with self._lock:
            return self._message_log[-limit:]

    def __repr__(self) -> str:
        return (f"<MessageQueue mailboxes={len(self._mailboxes)} "
                f"pending={self.total_pending()} "
                f"dead_letters={len(self._dead_letters)}>")
