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


@dataclass
class BotDecision:
    estado: str
    confianza: str
    resumen: str
    fuentes: list[EvidenceSource] = field(default_factory=list)
    siguiente_accion: str = ""
    requiere_escalamiento: bool = False
