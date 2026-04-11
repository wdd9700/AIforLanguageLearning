"""文件存储路由"""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from app.infrastructure.storage.minio_storage import get_minio_storage

router = APIRouter(prefix="/api/v1/upload", tags=["storage"])


class PresignedUrlRequest(BaseModel):
    bucket: str
    key: str
    expires: int = 3600


class PresignedUrlResponse(BaseModel):
    url: str


class MultipartInitRequest(BaseModel):
    bucket: str
    key: str
    content_type: str = "application/octet-stream"


class MultipartInitResponse(BaseModel):
    upload_id: str


class MultipartCompleteRequest(BaseModel):
    bucket: str
    key: str
    upload_id: str
    parts: list[dict]


class UploadResponse(BaseModel):
    bucket: str
    object_key: str
    etag: str
    presigned_url: str | None = None


@router.post("", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    storage = get_minio_storage()
    bucket = "aifl-uploads"
    key = file.filename or "unnamed"
    data = await file.read()
    result = await storage.upload(
        bucket, key, data, content_type=file.content_type or "application/octet-stream"
    )
    presigned = await storage.generate_presigned_url(bucket, key, expires=3600)
    return UploadResponse(
        bucket=result.bucket,
        object_key=result.object_key,
        etag=result.etag,
        presigned_url=presigned,
    )


@router.post("/multipart/init", response_model=MultipartInitResponse)
async def init_multipart(req: MultipartInitRequest) -> MultipartInitResponse:
    storage = get_minio_storage()
    upload_id = await storage.initiate_multipart_upload(req.bucket, req.key, req.content_type)
    return MultipartInitResponse(upload_id=upload_id)


@router.post("/multipart/complete", response_model=UploadResponse)
async def complete_multipart(req: MultipartCompleteRequest) -> UploadResponse:
    storage = get_minio_storage()
    result = await storage.complete_multipart_upload(req.bucket, req.key, req.upload_id, req.parts)
    return UploadResponse(
        bucket=result.bucket,
        object_key=result.object_key,
        etag=result.etag,
    )


@router.post("/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_url(req: PresignedUrlRequest) -> PresignedUrlResponse:
    storage = get_minio_storage()
    url = await storage.generate_presigned_url(req.bucket, req.key, req.expires)
    return PresignedUrlResponse(url=url)
