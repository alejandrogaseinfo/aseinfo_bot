"""Health and readiness checks that do not expose secrets or call dependencies."""

from __future__ import annotations

DEFAULT_RUNTIME_REVISION = "unversioned"


def readiness_payload(config) -> dict[str, object]:
    """Return the configuration readiness required for this deployment mode."""
    model_ready = bool(
        getattr(config, "openai_api_key", "") or getattr(config, "openai_base_url", "")
    )
    search_ready = bool(getattr(config, "azure_search_configured", False))
    require_search = bool(getattr(config, "require_azure_search", False))

    missing: list[str] = []
    if not model_ready:
        missing.append("model")
    if require_search and not search_ready:
        missing.append("azure_ai_search")

    return {
        "status": "ready" if not missing else "not_ready",
        "runtime_revision": getattr(config, "runtime_revision", DEFAULT_RUNTIME_REVISION),
        "environment": getattr(config, "environment", "local"),
        "retrieval_strategy": getattr(config, "retrieval_strategy", "legacy"),
        "model_configured": model_ready,
        "azure_search_configured": search_ready,
        "azure_search_required": require_search,
        "missing": missing,
    }
