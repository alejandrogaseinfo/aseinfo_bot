"""OpenAI Conversations/Responses adapter used by the Teams entry point."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConversationTurn:
    text: str
    recorded: bool = False


class OpenAIConversationAdapter:
    def __init__(self, client, timeout_seconds: float = 5):
        self.client = client
        self.timeout_seconds = timeout_seconds

    def create(self) -> str:
        conversation = self.client.conversations.create(
            timeout=self.timeout_seconds,
            metadata={"application": "libras"},
        )
        return str(conversation.id)

    def respond(self, conversation_id: str, user_message: str, *, instructions: str, model: str) -> str:
        response = self.client.responses.create(
            model=model,
            conversation=conversation_id,
            instructions=instructions,
            input=user_message,
            timeout=self.timeout_seconds,
        )
        text = getattr(response, "output_text", "") or ""
        if not text:
            raise RuntimeError("Responses API devolvió una respuesta sin texto.")
        return text.strip()

    def append_turn(self, conversation_id: str, user_message: str, assistant_message: str) -> None:
        self.client.conversations.items.create(
            conversation_id,
            items=[
                {"type": "message", "role": "user", "content": user_message},
                {"type": "message", "role": "assistant", "content": assistant_message},
            ],
            timeout=self.timeout_seconds,
        )

    def last_assistant_text(self, conversation_id: str) -> str | None:
        page = self.client.conversations.items.list(
            conversation_id,
            limit=50,
            order="desc",
            timeout=self.timeout_seconds,
        )
        for item in page:
            if getattr(item, "type", None) != "message" or getattr(item, "role", None) != "assistant":
                continue
            content = getattr(item, "content", None) or []
            for part in content:
                text = getattr(part, "text", None)
                if text:
                    return str(text)
        return None

    def delete(self, conversation_id: str) -> None:
        self.client.conversations.delete(
            conversation_id,
            timeout=self.timeout_seconds,
        )
