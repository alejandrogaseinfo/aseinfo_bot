from dataclasses import dataclass, field


@dataclass
class EvidenceSource:
    tipo: str
    titulo: str
    ubicacion: str
    fragmento: str
    # Metadatos opcionales: permiten rastrear una respuesta hasta el PDF de
    # SharePoint sin exponer detalles internos en la respuesta de Teams.
    source_system: str = ""
    document_id: str = ""
    document_version: str = ""
    last_modified: str = ""
    document_type: str = ""
    folder_path: str = ""
    artifact_role: str = ""
    quality_status: str = ""
    evidence_kind: str = ""
    covered_requirements: tuple[str, ...] = ()
    descripcion: str = ""


@dataclass
class BotDecision:
    estado: str
    confianza: str
    resumen: str
    fuentes: list[EvidenceSource] = field(default_factory=list)
    siguiente_accion: str = ""
    requiere_escalamiento: bool = False


@dataclass
class RetrievalTrace:
    """Non-sensitive retrieval diagnostics for evaluation and telemetry."""

    sources: list[EvidenceSource] = field(default_factory=list)
    query_hash: str = ""
    candidate_count: int = 0
    direct_evidence_count: int = 0
    requirement_count: int = 0
    covered_requirement_count: int = 0
    rejected_reasons: dict[str, int] = field(default_factory=dict)
