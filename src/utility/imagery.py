from __future__ import annotations

import io
import logging
import shutil
from pathlib import Path
from zipfile import ZipFile

from PIL import Image
from src.utility.image_export import atomic_output

logger = logging.getLogger("imagery")


def _convert_tif_to_png(target_file: io.BufferedReader, output_path: Path) -> None:
    """將 GeoTIFF 影像串流轉存為 PNG 格式並寫入目標路徑（採用快速壓縮 compress_level=1）。"""
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(target_file) as im, atomic_output(output_path) as temporary:
        im.save(temporary, "PNG", compress_level=1)


def extract_orthophoto_tiff(zip_bytes: bytes, output_path: Path) -> None:
    """Preserve the original GeoTIFF bytes and spatial metadata from NodeODM."""
    with ZipFile(io.BytesIO(zip_bytes)) as archive, atomic_output(output_path) as temporary:
        with archive.open("odm_orthophoto/odm_orthophoto.tif") as source, temporary.open("wb") as target:
            shutil.copyfileobj(source, target)


def create_orthophoto_preview(source: Path, output: Path) -> None:
    """Create the browser preview without modifying the original TIFF."""
    with source.open("rb") as stream:
        _convert_tif_to_png(stream, output)


def extract_orthophoto_from_zip(zip_bytes: bytes, output_path: Path) -> bool:
    """從成果壓縮包二進位位元組中提煉正射圖 GeoTIFF 並轉存為 PNG。"""
    if not zip_bytes:
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        tiff_path = output_path.with_suffix(".tif")
        extract_orthophoto_tiff(zip_bytes, tiff_path)
        create_orthophoto_preview(tiff_path, output_path)
        return output_path.exists()
    except Exception as e:
        logger.error(f"正射圖解壓轉換失敗: {e}")
        return False

