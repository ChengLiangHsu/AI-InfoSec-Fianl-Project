"""Full-resolution image exports; image encoding never changes workflow state."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Iterator

from PIL import Image

EXPORT_MEDIA_TYPES = {"tiff": "image/tiff", "jpg": "image/jpeg", "pdf": "application/pdf"}
GEO_TIFF_TAGS = (33550, 33922, 34264, 34735, 34736, 34737)


@contextmanager
def atomic_output(output_path: Path) -> Iterator[Path]:
    """Publish a complete file only after the writer succeeds."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=output_path.parent, suffix=".part", delete=False) as stream:
        temporary_path = Path(stream.name)
    try:
        yield temporary_path
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def export_filename(project_name: str, task_id: str, formula: str, file_format: str) -> str:
    """Create a portable attachment name while preserving readable Unicode."""
    name = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]', "_", project_name).strip(" .")[:80]
    layer = "orthophoto" if formula == "rgb" else formula
    return f"{name or 'project'}_{task_id[:8]}_{layer}.{file_format}"


def _flatten_on_white(image: Image.Image) -> Image.Image:
    """Composite transparency onto white for JPEG and PDF."""
    rgba = image.convert("RGBA")
    background = Image.new("RGB", image.size, "white")
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


def _read_geo_tags(source: Path | None) -> dict:
    """Copy only spatial tags, never source pixel layout or nodata metadata."""
    if source is None:
        return {}
    with Image.open(source) as image:
        return {tag: image.tag_v2[tag] for tag in GEO_TIFF_TAGS if tag in image.tag_v2}


def _encode_image(image: Image.Image, target: Path, file_format: str, geo_tags: dict) -> None:
    """Encode one full image with format-specific options."""
    if file_format == "tiff":
        image.save(target, "TIFF", compression="tiff_lzw", tiffinfo=geo_tags)
        return
    with _flatten_on_white(image) as flattened:
        if file_format == "jpg":
            flattened.save(target, "JPEG", quality=95, subsampling=0)
        else:
            # A single image page: preserve aspect ratio and all source pixels.
            flattened.save(target, "PDF", resolution=150.0, quality=95)


def convert_image_export(
    source: Path, output: Path, file_format: str, georeference: Path | None = None,
) -> None:
    """Orchestrate metadata reading, image encoding and atomic publication."""
    if file_format not in EXPORT_MEDIA_TYPES:
        raise ValueError("不支援的匯出格式")
    geo_tags = _read_geo_tags(georeference) if file_format == "tiff" else {}
    with Image.open(source) as image, atomic_output(output) as temporary:
        _encode_image(image, temporary, file_format, geo_tags)
