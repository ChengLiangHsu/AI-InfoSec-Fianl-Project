from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image

from src.utility.formulas import lookup_formula
from src.utility.image_export import atomic_output


def create_spectral_color_lut() -> np.ndarray:
    """建立紅 (低) -> 黃 (中) -> 綠 (高) 的 256 階假色對照表 (LUT)。

    注意：此色階僅由紅 [255, 0, 0] 漸變至黃 [255, 255, 0] 再至綠 [0, 255, 0]，
    藍色通道 (B) 在所有階度皆固定為 0；因此統計熱圖著色後之平均 RGB 時，B 通道必然為 0.00。
    """
    lut = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        if i < 128:
            lut[i] = [255, int(255 * (i / 128.0)), 0]
        else:
            lut[i] = [int(255 * (1.0 - (i - 128) / 128.0)), 255, 0]
    return lut


def evaluate_formula_values(arr: np.ndarray, expr: str) -> np.ndarray:
    """以純 RGB 三通道（0~1 歸一化之 b1=R, b2=G, b3=B）逐像素計算指數值；無定義處保留為非有限值。"""
    b1, b2, b3 = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        return eval(expr, {"sqrt": np.sqrt}, {"b1": b1, "b2": b2, "b3": b3})


def normalize_formula_values(val: np.ndarray, hrange: tuple[float, float] | None) -> np.ndarray:
    """Map index values to the shared display palette, preserving existing rendering."""
    val = np.nan_to_num(val, nan=0.0, posinf=1.0, neginf=-1.0)
    vmin, vmax = hrange if hrange else (-1.0, 1.0)
    return np.clip((val - vmin) / (vmax - vmin) * 255.0, 0, 255).astype(np.uint8)


def calculate_formula_matrix(
    arr: np.ndarray, expr: str, hrange: tuple[float, float] | None
) -> tuple[np.ndarray, np.ndarray | None]:
    """執行光譜公式矩陣運算並歸一化為 0~255 的整數影像陣列。"""
    has_alpha = arr.shape[2] == 4
    alpha = (arr[:, :, 3] * 255).astype(np.uint8) if has_alpha else None

    norm = normalize_formula_values(evaluate_formula_values(arr, expr), hrange)
    return norm, alpha


def generate_spectral_image(input_path: Path, output_path: Path, formula: str = "VARI") -> bool:
    """依據指定光譜公式（預設 VARI）計算並產生著色熱圖。"""
    expr, hrange = lookup_formula(formula, "RGB")
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(input_path) as img:
        arr = np.asarray(img, dtype=np.float32) / 255.0

    norm, alpha = calculate_formula_matrix(arr, expr, hrange)
    lut = create_spectral_color_lut()
    rgb_colored = lut[norm]

    if alpha is not None:
        rgba = np.dstack([rgb_colored, alpha])
        out_img = Image.fromarray(rgba, mode="RGBA")
    else:
        out_img = Image.fromarray(rgb_colored, mode="RGB")

    with out_img, atomic_output(output_path) as temporary:
        out_img.save(temporary, "PNG", compress_level=1)
    return True
