"""文件存储层接口契约与实现占位"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class UploadResult:
    bucket: str
    object_key: str
    etag: str
    presigned_url: str | None = None


class FileStorage(Protocol):
    """文件存储契约"""

    async def upload(self, bucket: str, key: str, data: bytes) -> UploadResult:
        ...

    async def generate_presigned_url(self, bucket: str, key: str, expires: int = 3600) -> str:
        ...

    async def complete_multipart_upload(
        self, bucket: str, key: str, upload_id: str, parts: list[dict]
    ) -> UploadResult:
        ...
