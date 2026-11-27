from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from src.utility.formulas import get_algorithm_list, lookup_formula
from src.utility.spectral import (
    create_spectral_color_lut, evaluate_formula_values, normalize_formula_values,
)


def validate_polygon(points: list[tuple[float, float]]) -> np.ndarray:
    """Accept a finite normalized polygon with nonzero signed area."""
    polygon = np.asarray(points, dtype=np.float64)
    if polygon.ndim != 2 or polygon.shape[1] != 2 or not 3 <= len(polygon) <= 100:
        raise ValueError("框選區域須包含 3 至 100 個頂點")
    if not np.isfinite(polygon).all() or (polygon < 0).any() or (polygon > 1).any():
        raise ValueError("框選座標須介於 0 與 1 之間")
    x, y = polygon.T
    area = abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    if area <= 1e-12:
        raise ValueError("框選區域面積必須大於零")
    return polygon


def _polygon_mask(polygon: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    """Even-odd fill sampled at pixel centers, including concave polygons."""
    left, top, right, bottom = box
    x = np.arange(left, right)[None, :] + 0.5
    y = np.arange(top, bottom)[:, None] + 0.5
    inside = np.zeros((bottom - top, right - left), dtype=bool)
    for (x1, y1), (x2, y2) in zip(polygon, np.roll(polygon, -1, axis=0)):
        if y1 == y2:
            continue
        inside ^= ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1)
    return inside


def _pixel_batches(image: Image.Image, polygon: np.ndarray):
    """Read bounded strips of original pixels; fully transparent pixels are excluded."""
    polygon = polygon * np.array(image.size)
    left, top = np.floor(polygon.min(axis=0)).astype(int)
    right, bottom = np.ceil(polygon.max(axis=0)).astype(int)
    rows = max(1, 262144 // max(1, right - left))
    for start in range(top, bottom, rows):
        box = (left, start, right, min(start + rows, bottom))
        with image.crop(box) as crop, crop.convert("RGBA") as rgba:
            pixels = np.asarray(rgba)
            mask = _polygon_mask(polygon, box) & (pixels[:, :, 3] > 0)
            yield pixels[:, :, :3][mask]


def _accumulate_algorithm(pixels: np.ndarray, algorithm: dict, lut: np.ndarray, totals: dict) -> None:
    """累計未截斷的純 RGB 指數值，以及套用紅→黃→綠假色階（LUT，B 固定為 0）後的輸出 RGB 總和。"""
    expr, hrange = lookup_formula(algorithm["id"])
    values = evaluate_formula_values(pixels, expr)
    finite = np.isfinite(values)
    totals["sum"] += float(values[finite].sum(dtype=np.float64))
    totals["count"] += int(finite.sum())
    colors = lut[normalize_formula_values(values, hrange)]
    totals["rgb"] += colors.sum(axis=(0, 1), dtype=np.float64)


def _mean_rgb(total: np.ndarray, count: int) -> list[float] | None:
    return (total / count).round(2).tolist() if count else None


def _collect_statistics(image: Image.Image, polygon: np.ndarray) -> dict:
    algorithms = get_algorithm_list()
    totals = {a["id"]: {"sum": 0.0, "count": 0, "rgb": np.zeros(3)} for a in algorithms}
    rgb_sum, count = np.zeros(3), 0
    lut = create_spectral_color_lut()
    for batch in _pixel_batches(image, polygon):
        if len(batch) == 0:
            continue
        count += len(batch)
        rgb_sum += batch.sum(axis=0, dtype=np.float64)
        normalized = batch.astype(np.float32).reshape(-1, 1, 3) / 255.0
        for algorithm in algorithms:
            _accumulate_algorithm(normalized, algorithm, lut, totals[algorithm["id"]])
    return _format_statistics(count, rgb_sum, totals)


def _format_statistics(count: int, rgb_sum: np.ndarray, totals: dict) -> dict:
    """輸出統計結果：頂層 rgb_mean 為原始輸入影像 RGB 平均；各演算法 rgb_mean 為紅→黃→綠著色輸出 RGB 平均（B 恆為 0.00）。"""
    return {
        "pixel_count": count,
        "rgb_mean": _mean_rgb(rgb_sum, count),
        "algorithms": [
            {
                "id": key,
                "index_mean": value["sum"] / value["count"] if value["count"] else None,
                "valid_pixel_count": value["count"],
                "rgb_mean": _mean_rgb(value["rgb"], count),
            }
            for key, value in totals.items()
        ],
    }


def calculate_region_statistics(path: Path, points: list[tuple[float, float]]) -> dict:
    """Orchestrate validation, source loading, and region statistics without saving plots."""
    polygon = validate_polygon(points)
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(path) as image:
        return _collect_statistics(image, polygon)
