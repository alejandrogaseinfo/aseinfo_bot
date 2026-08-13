"""Campos no sensibles para observar latencia por etapa.

Este módulo solo deriva identificadores operativos. Nunca conserva ni registra
el texto original de la consulta, prompts, documentos o credenciales.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlparse


def request_hash(message: str) -> str:
    """Return a short, non-reversible correlation identifier."""
    return hashlib.sha256(str(message or "").encode("utf-8")).hexdigest()[:16]


def endpoint_host(endpoint: str) -> str:
    """Return only the hostname portion of a provider endpoint."""
    try:
        return urlparse(str(endpoint or "")).hostname or "unconfigured"
    except (TypeError, ValueError):
        return "unconfigured"


def error_code(error: BaseException) -> str:
    """Return an exception type, never its potentially sensitive message."""
    return type(error).__name__
