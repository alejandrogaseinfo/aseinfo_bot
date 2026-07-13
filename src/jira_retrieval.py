import json
import urllib.parse
import urllib.request
import base64
from typing import Any

from document_index import tokenize
from logging_utils import get_logger
from models import EvidenceSource

logger = get_logger()

def retrieve_jira_evidence(user_message: str, config, limit: int = 2) -> list[EvidenceSource]:
    """
    Realiza una búsqueda de solo lectura en Jira usando JQL y devuelve los tickets más relevantes.
    """
    domain = getattr(config, "jira_domain", "")
    email = getattr(config, "jira_email", "")
    api_token = getattr(config, "jira_api_token", "")
    project_key = getattr(config, "jira_project_key", "")
    
    if not domain or not email or not api_token:
        return []

    # AQUÍ PUEDES MODIFICAR TU JQL:
    # Usamos una consulta JQL base buscando en texto. Puedes ajustar esto para que busque
    # estados cerrados (status = Closed) o cosas específicas del proyecto.
    # Por ejemplo: f'project = "{project_key}" AND text ~ "{jql_search_term}" ORDER BY created DESC'
    
    # Extraemos palabras clave básicas de la consulta del usuario para el JQL
    keywords = [word for word in tokenize(user_message) if len(word) > 3]
    if not keywords:
        return []
    
    jql_search_term = " OR ".join(keywords)
    
    if project_key:
        jql = f'project = "{project_key}" AND text ~ "{jql_search_term}"'
    else:
        jql = f'text ~ "{jql_search_term}"'

    url = f"https://{domain}/rest/api/3/search?jql={urllib.parse.quote(jql)}&maxResults={limit}"

    auth_string = f"{email}:{api_token}"
    auth_header = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    request = urllib.request.Request(
        url=url,
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        logger.exception("Fallo la consulta de solo lectura a Jira.")
        return []

    issues = payload.get("issues", [])
    evidence: list[EvidenceSource] = []
    
    for issue in issues:
        key = issue.get("key", "Jira Issue")
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")
        status = fields.get("status", {}).get("name", "")
        
        # En la API v3 de Jira, la descripción viene como Atlassian Document Format (ADF)
        # Aquí puedes simplificarlo o usar la API v2 si prefieres texto plano.
        
        evidence.append(
            EvidenceSource(
                tipo="jira",
                titulo=f"[{key}] {summary}",
                ubicacion=f"https://{domain}/browse/{key}",
                fragmento=f"Estado en Jira: {status}. Coincidencia encontrada con el problema reportado."
            )
        )

    return evidence
