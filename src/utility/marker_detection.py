from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

logger = logging.getLogger("marker_detection")


# ============================================================================
# 內部影像處理解析子函式 (Private Processing Helpers)
# ============================================================================

def _read_bgr_image(image_path: Path | str) -> np.ndarray:
    """安全載入 BGR 格式之影像。"""
    path_obj = Path(image_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"找不到正射影像檔案: {path_obj}")
    img = cv2.imread(str(path_obj))
    if img is None:
        raise ValueError(f"無法解碼正射影像: {path_obj}")
    return img


def _extract_white_binary_mask(bgr_img: np.ndarray) -> np.ndarray:
    """將 BGR 影像轉換至 HSV 空間並提取高亮度、低飽和度之白色標記遮罩。"""
    hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    # 白色在 HSV: 低飽和度 (S < 55) 且極高明度 (V > 215)
    lower_white = np.array([0, 0, 215], dtype=np.uint8)
    upper_white = np.array([180, 55, 255], dtype=np.uint8)
    return cv2.inRange(hsv, lower_white, upper_white)


def _extract_marker_centroids(
    binary_mask: np.ndarray,
    min_area: float = 3.0,
    max_area: float = 700.0,
) -> list[tuple[float, float]]:
    """自二值遮罩中萃取符合標記牌面積尺寸之連通輪廓質心（以像素為單位）。"""
    contours, _ = cv2.findContours(
        binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    centroids: list[tuple[float, float]] = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if min_area <= area <= max_area:
            m = cv2.moments(cnt)
            if m["m00"] > 0:
                cx = float(m["m10"] / m["m00"])
                cy = float(m["m01"] / m["m00"])
                centroids.append((cx, cy))
    return centroids


def _filter_centroids_by_roi(
    centroids: list[tuple[float, float]],
    roi: Sequence[float] | None,
    width: int,
    height: int,
) -> list[tuple[float, float]]:
    """依據指定之 ROI 正規化邊界（[min_x, min_y, max_x, max_y]）篩選標記點。"""
    if not roi or len(roi) < 4:
        return centroids
    min_x, min_y, max_x, max_y = (
        float(roi[0]),
        float(roi[1]),
        float(roi[2]),
        float(roi[3]),
    )
    filtered = []
    for px, py in centroids:
        nx = px / width
        ny = py / height
        if min_x <= nx <= max_x and min_y <= ny <= max_y:
            filtered.append((px, py))
    return filtered


def _find_extreme_four_corners(
    points: np.ndarray, width: int, height: int
) -> list[list[float]]:
    """自二維點群中提取形成四邊形外框之四個極端角點（TL, TR, BR, BL），並轉為正規化座標。"""
    if len(points) < 4:
        return _get_fallback_corners()

    # 計算極值投影以辨識四個頂點
    # TL: 最小 (x + y), BR: 最大 (x + y)
    # TR: 最大 (x - y), BL: 最小 (x - y)
    sum_xy = points[:, 0] + points[:, 1]
    diff_xy = points[:, 0] - points[:, 1]

    tl = points[np.argmin(sum_xy)]
    tr = points[np.argmax(diff_xy)]
    br = points[np.argmax(sum_xy)]
    bl = points[np.argmin(diff_xy)]

    raw_corners = [tl, tr, br, bl]
    normalized: list[list[float]] = []
    for pt in raw_corners:
        nx = round(float(pt[0]) / width, 5)
        ny = round(float(pt[1]) / height, 5)
        # 邊界箝制
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))
        normalized.append([nx, ny])

    return normalized


def _get_fallback_corners() -> list[list[float]]:
    """當標記點數量不足或無明顯四角時，回傳位於畫面中心 40% 視野之預設基準四邊形。"""
    return [
        [0.30, 0.25],  # TL (左上)
        [0.55, 0.25],  # TR (右上)
        [0.55, 0.38],  # BR (右下)
        [0.30, 0.38],  # BL (左下)
    ]


# ============================================================================
# 主流程調度函式 (Orchestrators)
# ============================================================================

def detect_white_marker_corners(
    image_path: Path | str,
    roi: Sequence[float] | None = None,
) -> list[list[float]]:
    """主流程：自動偵測正射影像中田區最外圍 4 個白色定位牌之正規化座標。
    
    回傳格式為四個角點之浮點數陣列：
    [[tl_x, tl_y], [tr_x, tr_y], [br_x, br_y], [bl_x, bl_y]]
    """
    bgr = _read_bgr_image(image_path)
    height, width = bgr.shape[:2]

    # 1. 色彩分割二值化
    mask = _extract_white_binary_mask(bgr)

    # 2. 斑點輪廓提取質心
    centroids = _extract_marker_centroids(mask)

    # 3. 視情況依據 ROI 篩選
    if roi:
        centroids = _filter_centroids_by_roi(centroids, roi, width, height)
    elif len(centroids) > 200:
        # 若未指定 ROI 且全田高光雜點極多，優先聚焦於中段常見農作試驗區
        central_roi = [0.20, 0.15, 0.80, 0.70]
        central_points = _filter_centroids_by_roi(
            centroids, central_roi, width, height
        )
        if len(central_points) >= 4:
            centroids = central_points

    if len(centroids) < 4:
        logger.warning("田區白色定位牌數量不足 (< 4)，使用預設基準四邊形")
        return _get_fallback_corners()

    pts_arr = np.array(centroids, dtype=np.float32)
    return _find_extreme_four_corners(pts_arr, width, height)


def bilinear_subdivide_quad(
    corners: Sequence[Sequence[float]],
    rows: int,
    cols: int,
    margin_ratio: float = 0.08,
) -> list[list[list[float]]]:
    """主流程：基於雙線性插值演算法將四邊形母框等分為 rows x cols 個小區多邊形。
    
    支援依 margin_ratio 比例向內收縮排除走道間距。
    corners 依序必須為 [TL, TR, BR, BL]。
    """
    if len(corners) < 4 or rows <= 0 or cols <= 0:
        return []

    p00 = np.array(corners[0], dtype=np.float32)  # TL (u=0, v=0)
    p10 = np.array(corners[1], dtype=np.float32)  # TR (u=1, v=0)
    p11 = np.array(corners[2], dtype=np.float32)  # BR (u=1, v=1)
    p01 = np.array(corners[3], dtype=np.float32)  # BL (u=0, v=1)

    def interp(u: float, v: float) -> list[float]:
        pt = (
            (1.0 - u) * (1.0 - v) * p00
            + u * (1.0 - v) * p10
            + u * v * p11
            + (1.0 - u) * v * p01
        )
        return [round(float(pt[0]), 5), round(float(pt[1]), 5)]

    margin_u = (1.0 / cols) * margin_ratio
    margin_v = (1.0 / rows) * margin_ratio

    plots: list[list[list[float]]] = []
    for r in range(rows):
        for c in range(cols):
            u_min = c / cols + margin_u
            u_max = (c + 1) / cols - margin_u
            v_min = r / rows + margin_v
            v_max = (r + 1) / rows - margin_v

            # 小區四頂點：TL, TR, BR, BL
            plot_poly = [
                interp(u_min, v_min),
                interp(u_max, v_min),
                interp(u_max, v_max),
                interp(u_min, v_max),
            ]
            plots.append(plot_poly)

    return plots

