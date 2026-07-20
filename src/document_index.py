import re
import unicodedata
from pathlib import Path

from models import EvidenceSource


STOP_WORDS = {
    "a",
    "al",
    "ante",
    "como",
    "con",
    "cual",
    "cuales",
    "cuando",
    "cuanto",
    "cuantos",
    "de",
    "del",
    "donde",
    "el",
    "en",
    "es",
    "esta",
    "este",
    "la",
    "las",
    "lo",
    "los",
    "para",
    "por",
    "que",
    "se",
    "sin",
    "si",
    "su",
    "un",
    "una",
    "ya",
}


def _normalize_token(token: str) -> str:
    normalized = unicodedata.normalize("NFKD", token.strip().lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    # A lightweight normalization lets "empleado" match "empleados" without
    # changing acronyms such as ISSS.
    if len(normalized) > 7 and normalized.endswith("mente"):
        return normalized[:-5]
    if len(normalized) > 5 and normalized.endswith("es"):
        return normalized[:-2]
    if len(normalized) > 4 and normalized.endswith("s") and not normalized.endswith("ss"):
        return normalized[:-1]
    return normalized


def tokenize(text: str) -> list[str]:
    normalized_text = _normalize_token(text)
    tokens = [_normalize_token(token) for token in re.findall(r"[a-zA-Z0-9_]+", normalized_text)]
    return [
        token
        for token in tokens
        if token not in STOP_WORDS and (len(token) > 2 or token.isdigit())
    ]


def split_into_chunks(content: str) -> list[str]:
    sections = [section.strip() for section in re.split(r"\n\s*\n", content) if section.strip()]
    return [section for section in sections if not section.startswith("#")]


def load_document_chunks() -> list[dict]:
    knowledge_base_path = Path(__file__).resolve().parent.parent / "docs" / "knowledge-base"
    chunks: list[dict] = []

    for file_path in sorted(knowledge_base_path.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")
        title = content.splitlines()[0].lstrip("# ").strip() if content else file_path.name
        for chunk in split_into_chunks(content):
            chunks.append(
                {
                    "titulo": title,
                    "ubicacion": str(file_path.relative_to(Path(__file__).resolve().parent.parent)),
                    "fragmento": chunk.replace("\n", " "),
                    "tokens": set(tokenize(chunk)),
                }
            )

    return chunks


def retrieve_document_evidence(user_message: str, limit: int = 3) -> list[EvidenceSource]:
    query_tokens = set(tokenize(user_message))
    if not query_tokens:
        return []

    scored_chunks = []
    for chunk in load_document_chunks():
        overlap = query_tokens.intersection(chunk["tokens"])
        if overlap:
            score = len(overlap)
            scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    return [
        EvidenceSource(
            tipo="documento",
            titulo=chunk["titulo"],
            ubicacion=chunk["ubicacion"],
            fragmento=chunk["fragmento"][:500],
        )
        for _, chunk in scored_chunks[:limit]
    ]
