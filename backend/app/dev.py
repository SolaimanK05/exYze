"""Standalone Sprint 2 geometry demo. Run locally with no database."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response

from .api.revisions import revision_document, router
from .db import ResourceId
from .errors import ApiError, register_error_handlers
from .geometry import GeometryV1

FIXTURE_PATH = Path(__file__).with_name("fixtures") / "dev_revision_v1.json"
DEMO_REVISION_ID = 1


@asynccontextmanager
async def load_fixture(app: FastAPI):
    app.state.geometry = GeometryV1.model_validate_json(FIXTURE_PATH.read_bytes())
    yield


def fixture_document(id: ResourceId, request: Request, response: Response) -> GeometryV1:
    if id != DEMO_REVISION_ID:
        raise ApiError(404, "NOT_FOUND", "Revision not found.")
    response.headers["X-Exyze-Geometry"] = "dev-fixture"
    return request.app.state.geometry


app = FastAPI(title="exYze dev geometry fixture", lifespan=load_fixture)
register_error_handlers(app)
app.include_router(router, prefix="/api")
app.dependency_overrides[revision_document] = fixture_document
