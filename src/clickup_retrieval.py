import json
import re
from html import unescape
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from document_index import tokenize
from logging_utils import get_logger
from models import EvidenceSource


logger = get_logger()

CLICKUP_API_BASE_URL = "https://api.clickup.com/api/v2"


def _clean_text(value: Any, limit: int = 420) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    shortened = text[:limit].rsplit(" ", 1)[0].strip()
    return f"{shortened}..."


def _clickup_get(path: str, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    query = f"?{urlencode(params)}" if params else ""
    request = Request(
        url=f"{CLICKUP_API_BASE_URL}{path}{query}",
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {error.code}: {details}") from error
    except URLError as error:
        raise RuntimeError(f"Network error: {error.reason}") from error


def _task_search_text(task: dict[str, Any]) -> str:
    assignees = " ".join(
        filter(
            None,
            [
                assignee.get("username", "")
                for assignee in task.get("assignees", [])
                if isinstance(assignee, dict)
            ],
        )
    )
    status = ""
    if isinstance(task.get("status"), dict):
        status = task["status"].get("status", "")
    return " ".join(
        [
            task.get("name", ""),
            task.get("text_content", ""),
            task.get("description", ""),
            status,
            assignees,
        ]
    ).strip()


def _score_task(user_message: str, task: dict[str, Any]) -> int:
    query_tokens = set(tokenize(user_message))
    if not query_tokens:
        return 0

    name_tokens = set(tokenize(task.get("name", "")))
    body_tokens = set(tokenize(_task_search_text(task)))
    body_overlap_tokens = query_tokens.intersection(body_tokens)
    name_overlap_tokens = query_tokens.intersection(name_tokens)
    overlap = len(body_overlap_tokens)
    name_overlap = len(name_overlap_tokens)
    coverage = overlap / max(len(query_tokens), 1)

    min_overlap = 2 if len(query_tokens) >= 4 else 1
    min_coverage = 0.5 if len(query_tokens) >= 4 else 0.34

    if name_overlap == 0 and (overlap < min_overlap or coverage < min_coverage):
        return 0

    if name_overlap == 1 and overlap < min_overlap and coverage < min_coverage:
        return 0

    return overlap + (name_overlap * 3)


def _build_task_fragment(task: dict[str, Any], list_name: str) -> str:
    status = ""
    if isinstance(task.get("status"), dict):
        status = task["status"].get("status", "")
    assignees = ", ".join(
        filter(
            None,
            [
                assignee.get("username", "")
                for assignee in task.get("assignees", [])
                if isinstance(assignee, dict)
            ],
        )
    )
    description = _clean_text(task.get("text_content") or task.get("description") or "")

    parts = [f"Lista: {list_name}."]
    if status:
        parts.append(f"Estado: {status}.")
    if assignees:
        parts.append(f"Asignado a: {assignees}.")
    if description:
        parts.append(description)

    return _clean_text(" ".join(parts), limit=420)


def retrieve_clickup_evidence(user_message: str, config, limit: int = 2) -> list[EvidenceSource]:
    token = getattr(config, "clickup_api_token", "")
    list_id = getattr(config, "clickup_list_id", "")
    if not token or not list_id:
        return []

    try:
        list_data = _clickup_get(f"/list/{list_id}", token)
        tasks_payload = _clickup_get(
            f"/list/{list_id}/task",
            token,
            params={"subtasks": "true", "page": 0},
        )
    except Exception:
        logger.exception("Fallo la consulta de solo lectura a ClickUp.")
        return []

    list_name = list_data.get("name", "ClickUp")
    list_url = list_data.get("url", "")
    tasks = tasks_payload.get("tasks", [])
    if not isinstance(tasks, list):
        return []

    ranked_tasks: list[tuple[int, dict[str, Any]]] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        score = _score_task(user_message, task)
        if score <= 0:
            continue
        ranked_tasks.append((score, task))

    ranked_tasks.sort(key=lambda item: item[0], reverse=True)
    best_score = ranked_tasks[0][0] if ranked_tasks else 0

    evidence: list[EvidenceSource] = []
    for score, task in ranked_tasks:
        if score < max(best_score - 1, 1):
            continue
        evidence.append(
            EvidenceSource(
                tipo="clickup",
                titulo=task.get("name", "Tarea de ClickUp"),
                ubicacion=task.get("url") or list_url or f"clickup:list:{list_id}",
                fragmento=_build_task_fragment(task, list_name),
            )
        )
        if len(evidence) >= limit:
            break

    return evidence
