from __future__ import annotations

import io
import logging
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

logger = logging.getLogger("imagery")


def _convert_tif_to_png(target_file: io.BufferedReader, output_path: Path) -> None:
    """將 GeoTIFF 影像串流轉存為 PNG 格式並寫入目標路徑。"""
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(target_file) as im:
        im.save(output_path, "PNG")


def extract_orthophoto_from_zip(zip_bytes: bytes, output_path: Path) -> bool:
    """從成果壓縮包二進位位元組中提煉正射圖 GeoTIFF 並轉存為 PNG。"""
    if not zip_bytes:
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(io.BytesIO(zip_bytes)) as z:
            with z.open("odm_orthophoto/odm_orthophoto.tif") as target:
                _convert_tif_to_png(target, output_path)
        return output_path.exists()
    except Exception as e:
        logger.error(f"正射圖解壓轉換失敗: {e}")
        return False

