"""可見光 RGB 植生／色彩指數定義與多光譜參考清單。

本系統僅處理一般消費級無人機之純 RGB（R、G、B 三通道）正射影像，
因此所有可執行之影像計算路徑皆嚴格限制於 `RGB_ALGORITHMS` 中的 5 項可見光 RGB 指標，
不依賴近紅外光（NIR）、紅邊（RedEdge）、熱紅外（Thermal）或 531nm/570nm 等窄波段假設。

`MULTISPECTRAL_REFERENCE_ALGOS` 僅供 AI 助理回答學理與感測器限制問題使用，
不可直接透過 `lookup_formula` 進行影像像素計算。
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

# 純 RGB（R、G、B 三通道，數值歸一化至 0~1）可執行之植生／色彩指標清單。
# 各項皆明確標註 RGB 公式與適用限制，避免與多光譜／窄波段原始指標混淆。
RGB_ALGORITHMS: dict[str, dict[str, Any]] = {
    "NDYI": {
        "expr": "(G - B) / (G + B)",
        "label": "NDYI（歸一化黃度指數）",
        "badge": "RGB 可見光",
        "help": "以可見光綠、藍波段計算之歸一化黃度指數，常用於偵測開花、黃化或葉色轉黃變化。",
        "limitation": "僅使用 G、B 兩通道，易受光照色溫與白平衡偏移影響，屬相對色彩指標。",
        "range": (-1, 1),
    },
    "VARI": {
        "expr": "(G - R) / (G + R - B)",
        "label": "VARI（可見光大氣阻抗指數）",
        "badge": "RGB 可見光",
        "help": "Visible Atmospherically Resistant Index，以可見光 RGB 強調綠色植生覆蓋並降低大氣與光照干擾。",
        "limitation": "高冠層覆蓋度時容易飽和；當 G + R - B 接近 0 時數值會劇烈波動或無定義。",
        "range": (-1, 1),
    },
    "MPRI": {
        "expr": "(G - R) / (G + R)",
        "label": "MPRI（RGB 替代公式／NGRDI）",
        "badge": "RGB 替代",
        "help": "以寬波段可見光綠、紅通道計算之 RGB 替代光化學反射指數（數學上等同 NGRDI），反映葉片綠紅對比。",
        "limitation": "為純 RGB 替代公式，並非使用 531nm／570nm 窄波段之原始光化學反射指數（PRI），無法直接量測葉黃素循環。",
        "range": (-1, 1),
    },
    "EXG": {
        "expr": "(2 * G) - (R + B)",
        "label": "EXG（超綠指數）",
        "badge": "RGB 可見光",
        "help": "Excess Green Index，以歸一化至 0~1 的 RGB 通道強化綠色植生並分離裸土背景。",
        "limitation": "此版本直接以 0~1 RGB 計算（非色度歸一化 2g - r - b），對整體曝光亮度變化較敏感，熱圖顯示範圍採 (-1, 1) 截斷。",
        "range": (-1, 1),
    },
    "GLI": {
        "expr": "((G * 2) - R - B) / ((G * 2) + R + B)",
        "label": "GLI（綠葉指數）",
        "badge": "RGB 可見光",
        "help": "Green Leaf Index，以可見光 RGB 區分綠色葉片與土壤／枯枝背景，數值介於 -1 至 1。",
        "limitation": "僅反映可見光綠度比例，陰影區或高光反射區可能產生雜訊，無法偵測非可見光生理逆境。",
        "range": (-1, 1),
    },
}

# 僅供 AI 助理回答學理差異之多光譜／熱紅外參考清單（本系統純 RGB 影像不可執行）。
MULTISPECTRAL_REFERENCE_ALGOS: dict[str, dict[str, Any]] = {
    "NDVI": {
        "expr": "(N - R) / (N + R)",
        "required_bands": ["N", "R"],
        "help": "歸一化差值植生指標（Normalized Difference Vegetation Index），需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
        "range": (-1, 1),
    },
    "NDRE": {
        "expr": "(N - Re) / (N + Re)",
        "required_bands": ["N", "Re"],
        "help": "歸一化差值紅邊指數，需要近紅外光（NIR）與紅邊（RedEdge）波段，純 RGB 相機無法計算。",
        "range": (-1, 1),
    },
    "NDWI": {
        "expr": "(G - N) / (G + N)",
        "required_bands": ["G", "N"],
        "help": "歸一化差值水體指數，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
        "range": (-1, 1),
    },
    "NDVI (Blue)": {
        "expr": "(N - B) / (N + B)",
        "required_bands": ["N", "B"],
        "help": "藍波段 NDVI，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
        "range": (-1, 1),
    },
    "ENDVI": {
        "expr": "((N + G) - (2 * B)) / ((N + G) + (2 * B))",
        "required_bands": ["N", "G", "B"],
        "help": "增強型歸一化植生指標，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
    },
    "BAI": {
        "expr": "1.0 / (((0.1 - R) ** 2) + ((0.06 - N) ** 2))",
        "required_bands": ["R", "N"],
        "help": "火燒跡地指數，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
    },
    "GNDVI": {
        "expr": "(N - G) / (N + G)",
        "required_bands": ["N", "G"],
        "help": "綠波段歸一化植生指標，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
        "range": (-1, 1),
    },
    "GRVI": {
        "expr": "N / G",
        "required_bands": ["N", "G"],
        "help": "綠光比值植生指標，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
    },
    "SAVI": {
        "expr": "(1.5 * (N - R)) / (N + R + 0.5)",
        "required_bands": ["N", "R"],
        "help": "土壤調整植生指標，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
    },
    "MNLI": {
        "expr": "((N ** 2 - R) * 1.5) / (N ** 2 + R + 0.5)",
        "required_bands": ["N", "R"],
        "help": "修正非線性植生指標，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
    },
    "MSR": {
        "expr": "((N / R) - 1) / (sqrt(N / R) + 1)",
        "required_bands": ["N", "R"],
        "help": "修正簡單比值指標，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
    },
    "RDVI": {
        "expr": "(N - R) / sqrt(N + R)",
        "required_bands": ["N", "R"],
        "help": "重歸一化差值植生指標，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
    },
    "TDVI": {
        "expr": "1.5 * ((N - R) / sqrt(N ** 2 + R + 0.5))",
        "required_bands": ["N", "R"],
        "help": "轉換型差值植生指標，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
    },
    "OSAVI": {
        "expr": "(N - R) / (N + R + 0.16)",
        "required_bands": ["N", "R"],
        "help": "最佳化土壤調整植生指標，需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
    },
    "LAI": {
        "expr": "3.618 * (2.5 * (N - R) / (N + 6*R - 7.5*B + 1)) - 0.118",
        "required_bands": ["N", "R", "B"],
        "help": "葉面積指數（LAI），此公式需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
        "range": (-1, 1),
    },
    "EVI": {
        "expr": "2.5 * (N - R) / (N + 6*R - 7.5*B + 1)",
        "required_bands": ["N", "R", "B"],
        "help": "增強型植生指標（EVI），需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
        "range": (-1, 1),
    },
    "ARVI": {
        "expr": "(N - (2 * R) + B) / (N + (2 * R) + B)",
        "required_bands": ["N", "R", "B"],
        "help": "大氣阻抗植生指標（ARVI），需要近紅外光（NIR）波段，純 RGB 相機無法計算。",
        "range": (-1, 1),
    },
    "PRI": {
        "expr": "(R531 - R570) / (R531 + R570)",
        "required_bands": ["531nm", "570nm"],
        "help": "原始光化學反射指數（Photochemical Reflectance Index），需要 531nm 與 570nm 窄波段感測器；本系統僅支援純 RGB 替代公式 MPRI = (G - R) / (G + R)。",
        "range": (-1, 1),
    },
    "Celsius": {
        "expr": "L",
        "required_bands": ["L"],
        "help": "攝氏溫度，需要熱紅外光（LWIR）感測器，純 RGB 相機無法計算。",
    },
    "Kelvin": {
        "expr": "L * 100 + 27315",
        "required_bands": ["L"],
        "help": "絕對溫度，需要熱紅外光（LWIR）感測器，純 RGB 相機無法計算。",
    },
}

# 向後相容別名：僅暴露純 RGB 可執行演算法，避免非 RGB 公式誤入運算路徑。
algos = RGB_ALGORITHMS

_RGB_BAND_MAP = {"R": "b1", "G": "b2", "B": "b3"}


def normalize_rgb_formula(formula: str) -> str:
    """Resolve a supported pure-RGB algorithm case-insensitively, retaining its canonical ID."""
    target = formula.strip().casefold()
    for algo_id in RGB_ALGORITHMS:
        if algo_id.casefold() == target:
            return algo_id
    raise ValueError(f"不支援的 RGB 光譜演算法：{formula}")


@lru_cache(maxsize=20)
def lookup_formula(algo: str | None, band_order: str | None = "RGB") -> tuple[str | None, tuple[float, float] | None]:
    """將純 RGB 演算法 ID 轉為 b1(R)、b2(G)、b3(B) 運算式與顯示範圍。

    本系統僅接受純 RGB 三通道輸入，拒絕需要 NIR 或窄波段之非 RGB 指標。
    """
    if algo is None:
        return None, None
    if band_order is not None and band_order.upper() != "RGB":
        raise ValueError(f"本系統僅支援純 RGB 三通道輸入，不支援波段配置：{band_order}")

    canonical_id = normalize_rgb_formula(algo)
    spec = RGB_ALGORITHMS[canonical_id]

    def repl(match: re.Match[str]) -> str:
        band = match.group(1)
        if band not in _RGB_BAND_MAP:
            raise ValueError(f"演算法 {canonical_id} 包含非 RGB 波段：{band}")
        return _RGB_BAND_MAP[band]

    expr = re.sub(r"([A-Z]+?[a-z]*)", repl, re.sub(r"\s+", "", spec["expr"]))
    hrange = spec.get("range", (-1, 1))
    return expr, hrange


@lru_cache(maxsize=2)
def get_algorithm_list(max_bands: int = 3) -> list[dict[str, Any]]:
    """回傳系統支援的所有純 RGB 植生／色彩指標清單。"""
    if max_bands < 3:
        return []
    return [
        {
            "id": algo_id,
            "filters": ["RGB"],
            **spec,
        }
        for algo_id, spec in RGB_ALGORITHMS.items()
    ]
