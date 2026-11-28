from pathlib import Path
import re

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from src.config import MAX_IMAGE_BYTES, MAX_IMAGES, MAX_UPLOAD_BYTES
from src.entities.upload import UploadImage

# 單張上傳圖片最大像素上限（防止解壓炸彈耗盡伺服器記憶體）
MAX_UPLOAD_IMAGE_PIXELS = 150_000_000
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+")


def _validate_upload_sizes(files: list[UploadFile]) -> None:
    """驗證上傳檔案數量、單檔大小與總大小上限。"""
    if not 1 <= len(files) <= MAX_IMAGES:
        raise HTTPException(400, f"每個任務需要 1 至 {MAX_IMAGES} 張照片")
    if any(not file.size or file.size > MAX_IMAGE_BYTES for file in files):
        raise HTTPException(413, f"單張照片不得為空或超過 {MAX_IMAGE_BYTES // 1024 // 1024} MiB")
    if sum(file.size or 0 for file in files) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"每個任務上傳總量不得超過 {MAX_UPLOAD_BYTES // 1024 // 1024} MiB")


def _sanitize_image_filename(raw_name: str | None, default_ext: str) -> str:
    """清理上傳檔名，移除跨平台路徑穿越字元與控制字元並補齊正確副檔名。"""
    candidate = (raw_name or "").replace("\\", "/").split("/")[-1]
    candidate = candidate.replace("\x00", "").strip().lstrip(".")
    stem = Path(candidate).stem if candidate else "image"
    cleaned_stem = _SAFE_FILENAME_RE.sub("_", stem).strip("._") or "image"
    cleaned_stem = cleaned_stem[:100]
    return f"{cleaned_stem}{default_ext}"


def _verify_image_integrity(file: UploadFile, expected_format: str) -> None:
    """以 Pillow 驗證影像結構完整性並防範解壓炸彈，檢查完畢後重設檔案游標。"""
    prev_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_UPLOAD_IMAGE_PIXELS
    try:
        file.file.seek(0)
        with Image.open(file.file) as img:
            if (img.format or "").upper() != expected_format:
                raise HTTPException(400, "影像檔案實際格式與檔頭不符，已拒絕上傳")
            img.verify()
    except HTTPException:
        raise
    except Image.DecompressionBombError as exc:
        raise HTTPException(413, "影像解析度過高，疑似解壓炸彈，已拒絕上傳") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, "影像檔案已損毀或包含非標準結構，僅支援有效的 JPG、JPEG 或 PNG 影像") from exc
    finally:
        Image.MAX_IMAGE_PIXELS = prev_limit
        file.file.seek(0)


async def _describe_image(file: UploadFile) -> UploadImage:
    """驗證影像 Magic Bytes、結構完整性與安全檔名後封裝為上傳實體。"""
    header = await file.read(12)
    await file.seek(0)
    if header.startswith(b"\xff\xd8\xff"):
        content_type = "image/jpeg"
        expected_format = "JPEG"
        default_ext = ".jpg"
    elif header.startswith(b"\x89PNG\r\n\x1a\n"):
        content_type = "image/png"
        expected_format = "PNG"
        default_ext = ".png"
    else:
        raise HTTPException(400, "僅支援 JPG、JPEG 或 PNG 影像")

    _verify_image_integrity(file, expected_format)
    filename = _sanitize_image_filename(file.filename, default_ext)
    return UploadImage(filename, file.file, content_type, file.size or 0)


async def prepare_uploads(files: list[UploadFile]) -> list[UploadImage]:
    """依序驗證上傳大小及格式，回傳可供 HTTP 串流轉送的檔案。"""
    _validate_upload_sizes(files)
    return [await _describe_image(file) for file in files]
