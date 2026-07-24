import os
from microsoft_agents.hosting.core import AgentApplication, AgentAuthConfiguration
from microsoft_agents.hosting.aiohttp import (
    start_agent_process,
    jwt_authorization_middleware,
    CloudAdapter,
)
from aiohttp.web import Request, Response, Application, json_response, middleware, run_app

from agent import agent_app, config, connection_manager
from runtime_health import readiness_payload

async def entry_point(req: Request) -> Response:
    agent: AgentApplication = req.app["agent_app"]
    adapter: CloudAdapter = req.app["adapter"]
    return await start_agent_process(
        req,
        agent,
        adapter,
    )


async def healthz(_req: Request) -> Response:
    """Liveness probe: the web host is able to accept requests."""
    return json_response({"status": "ok"})


async def readyz(req: Request) -> Response:
    """Readiness probe: the configured runtime can serve its intended mode."""
    payload = readiness_payload(req.app["runtime_config"])
    return json_response(payload, status=200 if payload["status"] == "ready" else 503)


@middleware
async def authorization_middleware(request: Request, handler):
    """Allow unauthenticated health probes while protecting bot activities."""
    if request.path in {"/healthz", "/readyz"}:
        return await handler(request)
    return await jwt_authorization_middleware(request, handler)


app = Application(middlewares=[authorization_middleware])
app.router.add_post("/api/messages", entry_point)
app.router.add_get("/healthz", healthz)
app.router.add_get("/readyz", readyz)
app["agent_configuration"] = connection_manager.get_default_connection_configuration()
app["agent_app"] = agent_app
app["adapter"] = agent_app.adapter
app["runtime_config"] = config

if __name__ == "__main__":
    run_app(app, host="localhost", port=os.environ.get("PORT", 3978))
