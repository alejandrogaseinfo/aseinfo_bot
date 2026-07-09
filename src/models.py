from dataclasses import dataclass, field


@dataclass
class EvidenceSource:
    tipo: str
    titulo: str
    ubicacion: str
    fragmento: str


@dataclass
class BotDecision:
    estado: str
    confianza: str
    resumen: str
    fuentes: list[EvidenceSource] = field(default_factory=list)
    siguiente_accion: str = ""
    requiere_escalamiento: bool = False

