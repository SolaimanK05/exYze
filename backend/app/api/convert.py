from collections.abc import AsyncGenerator
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from typing import Any

from ezdxf.lldxf.const import DXFError
from fastapi import APIRouter, Request, Response
from PIL import Image
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.requests import ClientDisconnect

from geometry.dxf_parser import parse_dxf

from ..errors import ApiError
from ..geometry import GeometryV1

router = APIRouter()
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_BODY_BYTES = MAX_FILE_BYTES + 64 * 1024
MAX_PHOTO_PIXELS = 32_000_000
PHOTO_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}


class MultipartTooLarge(MultiPartException):
    pass


async def bounded_upload_stream(request: Request) -> AsyncGenerator[bytes, None]:
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > MAX_BODY_BYTES:
            raise MultipartTooLarge("The multipart request exceeds the upload limit.")
        yield chunk


def move_plan_origin(geometry: dict[str, Any]) -> None:
    walls = geometry["walls"]
    origin_x = min(min(wall["x1"], wall["x2"]) for wall in walls)
    origin_y = min(min(wall["y1"], wall["y2"]) for wall in walls)

    for wall in walls:
        for field in ("x1", "x2"):
            wall[field] = round(wall[field] - origin_x, 3)
        for field in ("y1", "y2"):
            wall[field] = round(wall[field] - origin_y, 3)
    for element in [*geometry["labels"], *geometry["items"]]:
        element["x"] = round(element["x"] - origin_x, 3)
        element["y"] = round(element["y"] - origin_y, 3)
    for room in geometry["rooms"]:
        room["polygon"] = [
            [round(x - origin_x, 3), round(y - origin_y, 3)] for x, y in room["polygon"]
        ]


def convert_dxf(upload: UploadFile) -> GeometryV1:
    with TemporaryDirectory(prefix="exyze-convert-") as folder:
        path = Path(folder) / "plan.dxf"
        with path.open("wb") as output:
            copyfileobj(upload.file, output)
        try:
            geometry = parse_dxf(path, provisional_walls=True).geometry
        except (DXFError, UnicodeError, ValueError) as error:
            raise ApiError(422, "INVALID_DXF", "Could not read the uploaded DXF.") from error

    if not geometry["walls"]:
        raise ApiError(422, "NO_PLAN_GEOMETRY", "The DXF contains no supported wall lines.")
    move_plan_origin(geometry)
    return GeometryV1.model_validate(geometry)


def convert_photo(upload: UploadFile, image_format: str) -> GeometryV1:
    try:
        with Image.open(upload.file, formats=[image_format]) as image:
            if image.width * image.height > MAX_PHOTO_PIXELS:
                raise ApiError(413, "PHOTO_TOO_LARGE", "Photos are limited to 32 megapixels.")
            image.load()
    except Image.DecompressionBombError as error:
        raise ApiError(413, "PHOTO_TOO_LARGE", "Photos are limited to 32 megapixels.") from error
    except (OSError, SyntaxError, ValueError) as error:
        raise ApiError(422, "INVALID_PHOTO", "Could not read the photo as the named image type.") from error

    raise ApiError(
        503, "PHOTO_CONVERSION_UNAVAILABLE",
        "Photo conversion needs a processor that turns model masks into metre-scaled geometry.",
    )


@router.post("/convert", response_model=GeometryV1, response_model_exclude_unset=True, openapi_extra={
    "requestBody": {
        "required": True,
        "content": {"multipart/form-data": {"schema": {
            "type": "object",
            "properties": {"file": {"type": "string", "format": "binary"}},
            "required": ["file"],
        }}},
    },
})
async def convert_plan(request: Request, response: Response) -> GeometryV1:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "multipart/form-data":
        raise ApiError(415, "INVALID_UPLOAD_TYPE", "Upload one file using multipart/form-data.")

    parser = MultiPartParser(request.headers, bounded_upload_stream(request), max_files=1, max_fields=0)
    try:
        form = await parser.parse()
    except MultipartTooLarge as error:
        raise ApiError(413, "UPLOAD_TOO_LARGE", "Upload one file of 10 MiB or less.") from error
    except (MultiPartException, ClientDisconnect) as error:
        raise ApiError(400, "INVALID_UPLOAD", "Upload a single file in the file field.") from error

    try:
        upload = form.get("file")
        if not isinstance(upload, UploadFile) or not upload.filename:
            raise ApiError(400, "INVALID_UPLOAD", "Upload a single file in the file field.")
        if not upload.size:
            raise ApiError(422, "EMPTY_UPLOAD", "The uploaded file is empty.")
        if upload.size > MAX_FILE_BYTES:
            raise ApiError(413, "UPLOAD_TOO_LARGE", "Upload one file of 10 MiB or less.")

        suffix = Path(upload.filename).suffix.lower()
        response.headers["Cache-Control"] = "no-store"
        if suffix == ".dxf":
            return await run_in_threadpool(convert_dxf, upload)
        if photo_format := PHOTO_FORMATS.get(suffix):
            return await run_in_threadpool(convert_photo, upload, photo_format)
        raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "Supported formats are DXF, JPEG, and PNG.")
    finally:
        await form.close()
