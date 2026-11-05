from pathlib import Path

from fastapi import HTTPException, UploadFile

from src.config import MAX_IMAGE_BYTES, MAX_IMAGES, MAX_UPLOAD_BYTES
from src.entities.upload import UploadImage


def _validate_upload_sizes(files: list[UploadFile]) -> None:
    if not 1 <= len(files) <= MAX_IMAGES:
        raise HTTPException(400, f"每個任務需要 1 至 {MAX_IMAGES} 張照片")
    if any(not file.size or file.size > MAX_IMAGE_BYTES for file in files):
        raise HTTPException(413, f"單張照片不得為空或超過 {MAX_IMAGE_BYTES // 1024 // 1024} MiB")
    if sum(file.size or 0 for file in files) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"每個任務上傳總量不得超過 {MAX_UPLOAD_BYTES // 1024 // 1024} MiB")


async def _describe_image(file: UploadFile) -> UploadImage:
    header = await file.read(12)
    await file.seek(0)
    if header.startswith(b"\xff\xd8\xff"):
        content_type = "image/jpeg"
    elif header.startswith(b"\x89PNG\r\n\x1a\n"):
        content_type = "image/png"
    else:
        raise HTTPException(400, "僅支援 JPG、JPEG 或 PNG 影像")
    filename = Path(file.filename or "image.jpg").name
    return UploadImage(filename, file.file, content_type, file.size or 0)


async def prepare_uploads(files: list[UploadFile]) -> list[UploadImage]:
    """依序驗證上傳大小及格式，回傳可供 HTTP 串流轉送的檔案。"""
    _validate_upload_sizes(files)
    return [await _describe_image(file) for file in files]
