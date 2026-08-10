"""Persistent mapping between a Teams chat and an OpenAI conversation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Any


PARTITION_KEY = "libras"


@dataclass(frozen=True)
class ConversationMapping:
    teams_key: str
    openai_conversation_id: str
    created_at: str
    last_seen_at: str


def mapping_key(tenant_id: str, teams_conversation_id: str) -> str:
    """Return a stable, non-reversible Azure Table row key."""
    raw = f"{tenant_id}\x00{teams_conversation_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryConversationMappingStore:
    """Small store used by tests and local development."""

    def __init__(self):
        self._entries: dict[str, ConversationMapping] = {}

    def get(self, teams_key: str) -> ConversationMapping | None:
        return self._entries.get(teams_key)

    def create_if_absent(self, teams_key: str, openai_conversation_id: str) -> ConversationMapping:
        existing = self._entries.get(teams_key)
        if existing:
            return existing
        timestamp = _now()
        value = ConversationMapping(teams_key, openai_conversation_id, timestamp, timestamp)
        self._entries[teams_key] = value
        return value

    def touch(self, teams_key: str) -> ConversationMapping | None:
        existing = self._entries.get(teams_key)
        if not existing:
            return None
        value = ConversationMapping(existing.teams_key, existing.openai_conversation_id, existing.created_at, _now())
        self._entries[teams_key] = value
        return value

    def delete_expired(self, cutoff) -> int:
        expired = [
            key for key, value in self._entries.items()
            if datetime.fromisoformat(value.last_seen_at) < cutoff
        ]
        for key in expired:
            self._entries.pop(key, None)
        return len(expired)

    def delete(self, teams_key: str) -> None:
        self._entries.pop(teams_key, None)


class AzureTableConversationMappingStore:
    """Azure Table implementation; content is never stored in the table."""

    def __init__(self, table_client):
        self._table = table_client
        self._table.create_table_if_not_exists()

    @classmethod
    def from_config(cls, config):
        from azure.data.tables import TableClient

        if config.azure_storage_connection_string:
            client = TableClient.from_connection_string(
                config.azure_storage_connection_string,
                table_name=config.conversation_mapping_table,
            )
        elif config.azure_storage_table_url:
            from azure.identity import DefaultAzureCredential

            client = TableClient(
                endpoint=config.azure_storage_table_url,
                table_name=config.conversation_mapping_table,
                credential=DefaultAzureCredential(),
            )
        else:
            raise RuntimeError(
                "USE_OPENAI_CONVERSATIONS=true requiere "
                "AZURE_STORAGE_TABLE_URL o AZURE_STORAGE_CONNECTION_STRING."
            )
        return cls(client)

    @staticmethod
    def _to_mapping(entity: dict[str, Any]) -> ConversationMapping:
        return ConversationMapping(
            teams_key=str(entity["RowKey"]),
            openai_conversation_id=str(entity["openai_conversation_id"]),
            created_at=str(entity["created_at"]),
            last_seen_at=str(entity["last_seen_at"]),
        )

    def get(self, teams_key: str) -> ConversationMapping | None:
        try:
            entity = self._table.get_entity(PARTITION_KEY, teams_key)
        except Exception as exc:
            from azure.core.exceptions import ResourceNotFoundError

            if isinstance(exc, ResourceNotFoundError):
                return None
            raise
        return self._to_mapping(entity)

    def create_if_absent(self, teams_key: str, openai_conversation_id: str) -> ConversationMapping:
        timestamp = _now()
        entity = {
            "PartitionKey": PARTITION_KEY,
            "RowKey": teams_key,
            "openai_conversation_id": openai_conversation_id,
            "created_at": timestamp,
            "last_seen_at": timestamp,
        }
        try:
            self._table.create_entity(entity)
            return self._to_mapping(entity)
        except Exception as exc:
            from azure.core.exceptions import ResourceExistsError

            if not isinstance(exc, ResourceExistsError):
                raise
            existing = self.get(teams_key)
            if existing:
                return existing
            raise

    def touch(self, teams_key: str) -> ConversationMapping | None:
        existing = self.get(teams_key)
        if not existing:
            return None
        entity = {
            "PartitionKey": PARTITION_KEY,
            "RowKey": teams_key,
            "openai_conversation_id": existing.openai_conversation_id,
            "created_at": existing.created_at,
            "last_seen_at": _now(),
        }
        from azure.data.tables import UpdateMode

        self._table.update_entity(entity, mode=UpdateMode.MERGE)
        return self._to_mapping(entity)

    def delete(self, teams_key: str) -> None:
        try:
            self._table.delete_entity(PARTITION_KEY, teams_key)
        except Exception as exc:
            from azure.core.exceptions import ResourceNotFoundError

            if not isinstance(exc, ResourceNotFoundError):
                raise

    def delete_expired(self, cutoff) -> int:
        deleted = 0
        for entity in self._table.query_entities(
            query_filter="PartitionKey eq @partition",
            parameters={"partition": PARTITION_KEY},
        ):
            try:
                last_seen = datetime.fromisoformat(str(entity["last_seen_at"]))
            except (KeyError, ValueError):
                continue
            if last_seen < cutoff:
                self.delete(str(entity["RowKey"]))
                deleted += 1
        return deleted


def build_conversation_mapping_store(config):
    if not getattr(config, "use_openai_conversations", False):
        return None
    if not getattr(config, "openai_conversations_supported", False):
        return None
    return AzureTableConversationMappingStore.from_config(config)
