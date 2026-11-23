import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from .api import floors, projects, revisions
from .db import make_pool
from .errors import register_error_handlers


def create_app(dsn: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pool = make_pool(dsn) if dsn else None
        pool = app.state.pool
        try:
            if pool is not None:
                await run_in_threadpool(pool.open, wait=True, timeout=5)
            yield
        finally:
            if pool is not None:
                await run_in_threadpool(pool.close)

    app = FastAPI(title="exYze API", lifespan=lifespan)
    register_error_handlers(app)
    for router in (projects.router, floors.router, revisions.router):
        app.include_router(router, prefix="/api")
    return app


app = create_app(os.environ.get("EXYZE_DATABASE_URL"))
