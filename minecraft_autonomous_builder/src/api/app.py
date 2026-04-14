from __future__ import annotations

import uuid

from fastapi import FastAPI, Request

from api.routes_builds import router as build_router
from api.routes_health import router as health_router
from api.routes_projects import router as project_router
from common.logging import configure_logging

configure_logging()
app = FastAPI(title="Minecraft Autonomous Builder API", version="0.1.0")


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["x-trace-id"] = trace_id
    return response


app.include_router(health_router)
app.include_router(project_router)
app.include_router(build_router)
