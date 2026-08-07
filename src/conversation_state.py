"""Ephemeral, bounded context for one active Teams conversation.

This module deliberately keeps state in the worker process. It is not a
persistent transcript and must not be replaced with an external conversation
store for the current Libras scope.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic


MAX_TEXT_LENGTH = 12_000


@dataclass
class ChatThreadState:
    """Small amount of context needed by the existing follow-up resolver."""

    previous_documentary_response: str | None = None
    topic: str | None = None
    subject: str | None = None


class ConversationStateStore:
    """Bounded in-memory state keyed by the Teams conversation ID."""

    def __init__(self, ttl_seconds: float = 1800, max_conversations: int = 1000):
        self.ttl_seconds = max(0.0, float(ttl_seconds))
        self.max_conversations = max(1, int(max_conversations))
        self._entries: OrderedDict[str, tuple[float, ChatThreadState]] = OrderedDict()

    def _purge_expired(self, now: float) -> None:
        if self.ttl_seconds <= 0:
            self._entries.clear()
            return
        expired = [
            conversation_id
            for conversation_id, (last_seen, _state) in self._entries.items()
            if now - last_seen > self.ttl_seconds
        ]
        for conversation_id in expired:
            self._entries.pop(conversation_id, None)

    def get(self, conversation_id: str) -> ChatThreadState:
        """Return the current state, refreshing its inactivity TTL."""
        if not conversation_id:
            return ChatThreadState()
        now = monotonic()
        self._purge_expired(now)
        entry = self._entries.get(conversation_id)
        if entry is None:
            return ChatThreadState()
        _last_seen, state = entry
        self._entries.move_to_end(conversation_id)
        self._entries[conversation_id] = (now, state)
        return state

    def record_response(
        self,
        conversation_id: str,
        answer: str,
        *,
        is_documentary: bool,
        subject: str | None = None,
    ) -> None:
        """Record bounded context without clearing it on conversational turns."""
        if not conversation_id:
            return
        now = monotonic()
        self._purge_expired(now)
        state = self._entries.get(conversation_id, (now, ChatThreadState()))[1]
        if is_documentary:
            state.previous_documentary_response = (answer or "")[:MAX_TEXT_LENGTH] or None
        if subject:
            state.subject = subject[:240]
        self._entries[conversation_id] = (now, state)
        self._entries.move_to_end(conversation_id)
        while len(self._entries) > self.max_conversations:
            self._entries.popitem(last=False)

    def set_topic(self, conversation_id: str, topic: str) -> None:
        """Store a closed guided topic for the active chat only."""
        if not conversation_id or not topic:
            return
        state = self.get(conversation_id)
        state.topic = topic
        self._entries[conversation_id] = (monotonic(), state)

    def clear(self, conversation_id: str) -> None:
        """Forget one active chat; used by the future ``/nuevo`` command."""
        if conversation_id:
            self._entries.pop(conversation_id, None)

    def __len__(self) -> int:
        self._purge_expired(monotonic())
        return len(self._entries)
