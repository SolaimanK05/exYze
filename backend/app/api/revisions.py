from typing import Annotated

from fastapi import APIRouter, Depends, Response

from ..db import RequestDB, ResourceId, require_project_reader, require_row_security
from ..errors import ApiError
from ..geometry import GeometryV1

router = APIRouter()


def revision_document(
    id: ResourceId, _reader: Annotated[None, Depends(require_project_reader)], db: RequestDB
) -> GeometryV1:
    require_row_security(db, "project", "floor", "revision")
    revision = db.execute("""
        SELECT r.revision_id
        FROM revision AS r
        JOIN floor AS f USING (floor_id)
        JOIN project AS p USING (project_id)
        WHERE r.revision_id = %s
          AND (current_user = 'exyze_admin' OR p.owner_id = current_setting('app.user_id')::bigint)
        """, (id,)).fetchone()
    if revision is None:
        raise ApiError(404, "NOT_FOUND", "Revision not found.")
    raise ApiError(503, "GEOMETRY_UNAVAILABLE", "Stored revision geometry is unavailable.")


@router.get("/revisions/{id}", response_model=GeometryV1, response_model_exclude_unset=True)
def get_revision(
    document: Annotated[GeometryV1, Depends(revision_document)], response: Response
) -> GeometryV1:
    response.headers["Cache-Control"] = "no-store"
    return document
