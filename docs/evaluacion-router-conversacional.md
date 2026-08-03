# Evaluación del router conversacional

El router decide si un mensaje trata sobre Libras mismo, requiere orientación,
necesita más contexto o debe consultar la base documental. Esta evaluación evita
que una pregunta de capacidades o alcance se convierta por error en una búsqueda
RAG.

## Corpus

El conjunto versionado está en
[`tests/fixtures/intent_routing_cases.json`](../tests/fixtures/intent_routing_cases.json).
Contiene 30 frases no sensibles divididas entre:

- capacidades de Libras;
- alcance y fuentes documentales;
- ayuda para formular consultas;
- saludos;
- errores o consultas que requieren aclaración;
- consultas documentales que sí deben llegar a recuperación.

Cada caso declara `intent`, `conversation_purpose` y `requires_context`.
Agregar nuevas frases reales anonimizadas cuando un usuario reciba una ruta
incorrecta; no incluir nombres de clientes, secretos, datos personales ni
fragmentos internos.

## Pruebas locales

La suite automática valida el formato del corpus y las rutas determinísticas:

```powershell
python -m unittest discover -s tests -v
```

## Medición con el LLM real

Con un proveedor compatible con OpenAI configurado, ejecutar:

```powershell
python src/evaluate_intent_router.py
```

El comando llama únicamente al modelo de intención configurado por
`OPENAI_INTENT_MODEL`. No consulta SharePoint, Azure AI Search ni genera
respuestas para el usuario. Devuelve dos métricas:

- **acción correcta**: el comportamiento que recibirá el usuario (`capability`,
  `scope`, `help`, `greeting`, `clarify` o `retrieve`);
- **coincidencia exacta**: los tres campos JSON coinciden literalmente.

Por ejemplo, `reporte_error` y `consulta_ambigua` con
`requiere_contexto=true` producen la misma acción `clarify`. El comando termina
con código 1 solo si la acción difiere. Es útil ejecutarlo antes de cambiar el
prompt, el modelo de intención o las categorías del router.

Para revisar solo una copia del corpus o limitar las discrepancias impresas:

```powershell
python src/evaluate_intent_router.py --cases ruta\al\corpus.json --max-failures 5
```

El timeout por defecto coincide con `INTENT_TIMEOUT_SECONDS`, para medir la
experiencia operativa. Si se desea evaluar únicamente la calidad semántica del
modelo ante una red lenta, se puede ampliar sin cambiar la aplicación:

```powershell
python src/evaluate_intent_router.py --timeout 10
```
