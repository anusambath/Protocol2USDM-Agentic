"""
Unit tests for MessageQueue.

Covers: publishing, polling, priority ordering, dead-letter queue,
filtering, serialization.
"""

import pytest
from agents.message_queue import AgentMessage, MessageQueue, MessageType, Priority


class TestPublishAndPoll:
    def test_publish_and_poll(self, message_queue):
        msg = AgentMessage(
            sender_id="sender",
            receiver_id="receiver",
            message_type=MessageType.REQUEST,
            payload={"data": "test"},
        )
        message_queue.publish(msg)
        received = message_queue.poll("receiver", timeout_ms=100)
        assert received is not None
        assert received.payload["data"] == "test"

    def test_poll_empty_returns_none(self, message_queue):
        result = message_queue.poll("agent_1", timeout_ms=50)
        assert result is None

    def test_broadcast(self, message_queue):
        message_queue.subscribe("a1")
        message_queue.subscribe("a2")
        msg = AgentMessage(
            sender_id="broadcaster",
            message_type=MessageType.BROADCAST,
            payload={"event": "status_update"},
        )
        message_queue.publish(msg)
        r1 = message_queue.poll("a1", timeout_ms=100)
        r2 = message_queue.poll("a2", timeout_ms=100)
        assert r1 is not None
        assert r2 is not None
        # Broadcaster should not receive own broadcast
        r3 = message_queue.poll("broadcaster", timeout_ms=50)
        assert r3 is None


class TestPriorityOrdering:
    def test_high_priority_first(self, message_queue):
        low = AgentMessage(sender_id="s", receiver_id="r",
                           priority=Priority.LOW, payload={"p": "low"})
        high = AgentMessage(sender_id="s", receiver_id="r",
                            priority=Priority.HIGH, payload={"p": "high"})
        normal = AgentMessage(sender_id="s", receiver_id="r",
                              priority=Priority.NORMAL, payload={"p": "normal"})
        message_queue.publish(low)
        message_queue.publish(high)
        message_queue.publish(normal)

        r1 = message_queue.poll("r", timeout_ms=100)
        r2 = message_queue.poll("r", timeout_ms=100)
        r3 = message_queue.poll("r", timeout_ms=100)
        assert r1.payload["p"] == "high"
        assert r2.payload["p"] == "normal"
        assert r3.payload["p"] == "low"


class TestDeadLetterQueue:
    def test_dead_letter(self, message_queue):
        msg = AgentMessage(sender_id="s", receiver_id="r")
        message_queue.dead_letter(msg, "processing failed")
        dead = message_queue.get_dead_letters()
        assert len(dead) == 1
        assert dead[0].payload["_dead_letter_reason"] == "processing failed"

    def test_retry_or_dead_letter_retries(self, message_queue):
        msg = AgentMessage(sender_id="s", receiver_id="r",
                           retry_count=0, max_retries=3)
        retried = message_queue.retry_or_dead_letter(msg, "error")
        assert retried is True
        assert msg.retry_count == 1
        assert message_queue.pending_count("r") == 1

    def test_retry_or_dead_letter_exhausted(self, message_queue):
        msg = AgentMessage(sender_id="s", receiver_id="r",
                           retry_count=3, max_retries=3)
        retried = message_queue.retry_or_dead_letter(msg, "final error")
        assert retried is False
        assert len(message_queue.get_dead_letters()) == 1


class TestFiltering:
    def test_poll_filtered(self, message_queue):
        req = AgentMessage(sender_id="s", receiver_id="r",
                           message_type=MessageType.REQUEST, payload={"t": "req"})
        status = AgentMessage(sender_id="s", receiver_id="r",
                              message_type=MessageType.STATUS, payload={"t": "status"})
        message_queue.publish(req)
        message_queue.publish(status)

        result = message_queue.poll_filtered("r", MessageType.STATUS, timeout_ms=100)
        assert result is not None
        assert result.payload["t"] == "status"


class TestQueueManagement:
    def test_pending_count(self, message_queue):
        for i in range(5):
            message_queue.publish(AgentMessage(sender_id="s", receiver_id="r"))
        assert message_queue.pending_count("r") == 5
        assert message_queue.total_pending() == 5

    def test_clear_mailbox(self, message_queue):
        for i in range(3):
            message_queue.publish(AgentMessage(sender_id="s", receiver_id="r"))
        cleared = message_queue.clear_mailbox("r")
        assert cleared == 3
        assert message_queue.pending_count("r") == 0

    def test_acknowledge(self, message_queue):
        msg = AgentMessage(sender_id="s", receiver_id="r")
        message_queue.publish(msg)
        received = message_queue.poll("r", timeout_ms=100)
        message_queue.acknowledge(received.id)
        log = message_queue.get_message_log()
        ack_entries = [e for e in log if e["event"] == "acknowledged"]
        assert len(ack_entries) == 1


class TestSerialization:
    def test_message_round_trip(self):
        msg = AgentMessage(
            sender_id="s", receiver_id="r",
            message_type=MessageType.REQUEST,
            priority=Priority.HIGH,
            payload={"key": "value"},
            correlation_id="corr_1",
        )
        d = msg.to_dict()
        restored = AgentMessage.from_dict(d)
        assert restored.sender_id == msg.sender_id
        assert restored.message_type == MessageType.REQUEST
        assert restored.priority == Priority.HIGH
        assert restored.payload["key"] == "value"

    def test_queue_round_trip(self, message_queue):
        message_queue.subscribe("a1", [MessageType.REQUEST])
        for i in range(3):
            message_queue.publish(AgentMessage(
                sender_id="s", receiver_id="a1",
                payload={"i": i},
            ))
        serialized = message_queue.serialize()
        restored = MessageQueue.deserialize(serialized)
        assert restored.pending_count("a1") == 3

    def test_message_log(self, message_queue):
        msg = AgentMessage(sender_id="s", receiver_id="r")
        message_queue.publish(msg)
        log = message_queue.get_message_log()
        assert len(log) >= 1
        assert log[-1]["event"] == "published"
