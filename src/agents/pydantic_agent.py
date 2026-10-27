from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

import numpy as np
from PIL import Image
from pydantic_ai import (
    Agent,
    BinaryContent,
    RunContext,
)

from src.database import Database
from src.utility.formulas import algos, get_algorithm_list, get_camera_filters_for, lookup_formula
from src.utility.nodeodm import fetch_orthophoto_from_odm
from src.utility.spectral import generate_spectral_image

SRC_DIR = Path(__file__).resolve().parents[1]
ODM_DIR = SRC_DIR / "odm"
ODM_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ChatDeps:
    project_id: str
    database: Database


model = os.getenv("PYDANTIC_AI_MODEL", "google:gemini-3.7-flash")
agent = Agent(model, deps_type=ChatDeps)
vision_agent = Agent(model)


@agent.system_prompt
async def system_prompt(ctx: RunContext[ChatDeps]) -> str:
    base_prompt = (
        "你是無人機田間試驗智慧評估代理人（Agricultural Drone Field Trial Agent）。\n"
        "你的核心專業是協助農業與植保試驗人員，針對高解析度無人機空拍正射影像進行分析、植生指標計算與藥效評估。\n"
        "你具備直接存取當前專案的正射圖（Orthophoto）與各光譜演算法影像（VARI, GLI, EXG, vNDVI, MPRI 等）的完整能力。\n"
        "當使用者在小視窗（AskAgent）詢問田間狀況、正射圖、光譜圖或作物健康狀況時，請靈活調用以下工具：\n"
        "1. `get_current_project_info`：確認專案基本資訊、正射圖生成狀態與可用光譜指標。\n"
        "2. `calculate_spectral_statistics`：獲取具備統計科學依據的光譜指標數值（平均值、中位數、標準差）與植生健康等級佔比。\n"
        "3. `inspect_field_imagery`：運用多模態視覺判讀田間正射圖或光譜圖中的行株距、缺株空洞、變色斑塊與生長不均現象。\n"
        "4. `query_vegetation_index`：查詢植生指標公式、適用波段與學理依據。\n"
        "請將科學統計數據與多模態視覺判讀深度結合，給予專業、結構化且具可行性的田間試驗評估與農事建議。"
    )
    pid = ctx.deps.project_id
    if pid and pid != "home":
        try:
            proj = await ctx.deps.database.get_project(pid)
            ortho_exists = (ODM_DIR / f"{pid}.png").exists()
            base_prompt += (
                f"\n\n【當前專案資訊】\n"
                f"- 專案名稱：{proj['name']}\n"
                f"- 專案 ID：{proj['id']}\n"
                f"- 航拍相片數：{proj['images']} 張\n"
                f"- 拼接運算進度：{proj['progress']}%\n"
                f"- 正射圖產出狀態：{'已完成就緒 (Ready)' if ortho_exists else '尚未完成或生成中'}\n"
                f"使用者目前在該專案的專屬小視窗（AskAgent）與你對話，你可以直接調用工具存取此專案的正射圖與其光譜圖進行多模態診斷。"
            )
        except Exception:
            pass
    return base_prompt


@agent.tool
async def get_current_project_info(ctx: RunContext[ChatDeps]) -> dict:
    """取得當前使用者正在檢視的田間試驗專案資訊、正射圖檔案狀態與支援的光譜演算法。"""
    pid = ctx.deps.project_id
    if not pid or pid == "home":
        return {
            "status": "not_in_project",
            "message": "目前使用者位於主畫面首頁，尚未進入任何專案。請引導使用者選擇或建立專案後再進行特定田間影像分析。",
        }
    try:
        proj = await ctx.deps.database.get_project(pid)
    except Exception as e:
        return {"status": "error", "message": f"無法載入專案資料: {e}"}

    ortho_path = ODM_DIR / f"{pid}.png"
    has_ortho = ortho_path.exists()
    width, height = 0, 0
    if has_ortho:
        try:
            with Image.open(ortho_path) as im:
                width, height = im.size
        except Exception:
            pass

    cached_spectrals = [
        f.stem.replace(f"{pid}_", "") for f in ODM_DIR.glob(f"{pid}_*.png")
    ]
    all_rgb_algos = [
        a["id"] for a in get_algorithm_list(max_bands=3) if "RGB" in a.get("filters", [])
    ]

    return {
        "status": "success",
        "project_id": pid,
        "project_name": proj["name"],
        "images_count": proj["images"],
        "progress": proj["progress"],
        "has_orthophoto": has_ortho,
        "image_resolution": f"{width} x {height}" if has_ortho else "未知",
        "cached_spectral_maps": cached_spectrals,
        "supported_rgb_formulas": all_rgb_algos,
    }


def _load_ortho_pixels(ortho_path: Path, max_dim: int = 1500) -> tuple[np.ndarray, np.ndarray]:
    """載入正射圖並抽離有效像元遮罩與波段陣列。"""
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(ortho_path) as img:
        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            new_size = (int(w * scale), int(h * scale))
            img_resized = img.resize(new_size, Image.Resampling.BILINEAR)
            arr = np.asarray(img_resized, dtype=np.float32) / 255.0
        else:
            arr = np.asarray(img, dtype=np.float32) / 255.0

    valid_mask = arr[:, :, 3] > 0.1 if arr.shape[2] == 4 else np.ones(arr.shape[:2], dtype=bool)
    return arr, valid_mask


def _calculate_pixel_statistics(valid_vals: np.ndarray) -> dict[str, float]:
    """計算像元分佈數值統計（均值、中位數、標準差、四分位數）。"""
    return {
        "mean": round(float(np.mean(valid_vals)), 4),
        "median": round(float(np.median(valid_vals)), 4),
        "std_deviation": round(float(np.std(valid_vals)), 4),
        "q25": round(float(np.percentile(valid_vals, 25)), 4),
        "q75": round(float(np.percentile(valid_vals, 75)), 4),
        "min": round(float(np.min(valid_vals)), 4),
        "max": round(float(np.max(valid_vals)), 4),
    }


def _classify_vegetation(
    formula: str, valid_vals: np.ndarray, vmin: float, vmax: float
) -> dict[str, float]:
    """依據光譜指標數值切分植生活力等級佔比。"""
    n = len(valid_vals)
    if formula in ["VARI", "GLI"]:
        healthy = float(np.sum(valid_vals > 0.1) / n)
        moderate = float(np.sum((valid_vals >= 0.0) & (valid_vals <= 0.1)) / n)
        low_soil = float(np.sum(valid_vals < 0.0) / n)
    elif formula == "EXG":
        healthy = float(np.sum(valid_vals > 0.05) / n)
        moderate = float(np.sum((valid_vals >= 0.0) & (valid_vals <= 0.05)) / n)
        low_soil = float(np.sum(valid_vals < 0.0) / n)
    else:
        mid = (vmin + vmax) / 2.0
        healthy = float(np.sum(valid_vals > mid) / n)
        moderate = float(
            np.sum((valid_vals >= vmin + (vmax - vmin) * 0.25) & (valid_vals <= mid)) / n
        )
        low_soil = float(np.sum(valid_vals < vmin + (vmax - vmin) * 0.25) / n)

    return {
        "healthy_vegetation_pct": round(healthy * 100, 2),
        "moderate_vegetation_pct": round(moderate * 100, 2),
        "low_vigor_or_soil_pct": round(low_soil * 100, 2),
    }


def _evaluate_field_homogeneity(std_val: float) -> str:
    """依據指標標準差判定田間生長勢均勻度等級。"""
    if std_val < 0.12:
        return "高均勻度 (植株生長整齊一致)"
    if std_val < 0.22:
        return "中等均勻度 (部分區域存在生長勢落差)"
    return "高異質性 (田區長勢不均或存在明顯缺株斑禿)"


@agent.tool
async def calculate_spectral_statistics(
    ctx: RunContext[ChatDeps], formula: str = "VARI"
) -> dict:
    """計算並取得當前專案在指定光譜植生指標（如 VARI, GLI, EXG, vNDVI, MPRI 等）下的田間數值統計資料。"""
    pid = ctx.deps.project_id
    if not pid or pid == "home":
        return {"status": "error", "message": "目前未選擇具體專案，無法計算田間光譜統計。"}

    ortho_path = ODM_DIR / f"{pid}.png"
    if not ortho_path.exists():
        await fetch_orthophoto_from_odm(pid, ortho_path)
        if not ortho_path.exists():
            return {"status": "error", "message": "尚未找到該專案的正射圖，航拍拼接可能尚未完成。"}

    formula_upper = formula.strip().upper()
    try:
        expr, hrange = lookup_formula(formula_upper, "RGB")
    except Exception as e:
        return {"status": "error", "message": f"找不到光譜指標 '{formula}': {e}"}

    arr, valid_mask = _load_ortho_pixels(ortho_path)
    b1, b2, b3 = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    vmin, vmax = hrange if hrange else (-1.0, 1.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        val = eval(expr, {"sqrt": np.sqrt}, {"b1": b1, "b2": b2, "b3": b3})
        val = np.nan_to_num(val, nan=0.0, posinf=vmax, neginf=vmin)

    val_clipped = np.clip(val, vmin, vmax)
    valid_vals = val_clipped[valid_mask]
    if len(valid_vals) == 0:
        return {"status": "error", "message": "影像中無有效農田像素。"}

    stats = _calculate_pixel_statistics(valid_vals)
    classification = _classify_vegetation(formula_upper, valid_vals, vmin, vmax)
    homogeneity = _evaluate_field_homogeneity(stats["std_deviation"])

    return {
        "status": "success",
        "formula": formula_upper,
        "formula_expression": expr,
        "valid_pixel_count": int(len(valid_vals)),
        "statistics": stats,
        "vegetation_classification": classification,
        "field_homogeneity": homogeneity,
    }


def _prepare_thumbnail_bytes(image_path: Path, max_size: tuple[int, int] = (768, 768)) -> bytes:
    """將輸入影像轉為低延遲視覺辨識縮圖 Bytes。"""
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(image_path) as im:
        im_copy = im.copy()
        im_copy.thumbnail(max_size)
        buf = BytesIO()
        im_copy.save(buf, format="PNG")
        return buf.getvalue()


@agent.tool
async def inspect_field_imagery(
    ctx: RunContext[ChatDeps],
    image_target: Literal["orthophoto", "spectral"] = "spectral",
    formula: str = "VARI",
    focus: str = "詳細觀察並診斷田間作物生長勢、行株距整齊度、缺株/斑禿區域或變色異常",
) -> str:
    """使用多模態視覺模型（Gemini Vision）直接讀取並觀察當前專案的正射圖（RGB原圖）或指定光譜熱圖。"""
    pid = ctx.deps.project_id
    if not pid or pid == "home":
        return "目前未選擇具體專案，無法讀取田間影像。"

    ortho_path = ODM_DIR / f"{pid}.png"
    if not ortho_path.exists():
        await fetch_orthophoto_from_odm(pid, ortho_path)
        if not ortho_path.exists():
            return "正射圖檔案不存在，請確認空拍拼接任務是否已完成。"

    formula_upper = formula.strip().upper()
    if image_target == "spectral":
        target_img_path = ODM_DIR / f"{pid}_{formula_upper}.png"
        if not target_img_path.exists():
            try:
                generate_spectral_image(ortho_path, target_img_path, formula_upper)
            except Exception as e:
                return f"生成光譜圖 {formula_upper} 失敗: {e}"
        image_desc = f"專案 {pid} 的 {formula_upper} 植生指標光譜圖（綠色為高活力植被、黃色為中度活力、紅/黑色為低活力或土壤）"
    else:
        target_img_path = ortho_path
        image_desc = f"專案 {pid} 的高解析度無人機原始正射拼接影像 (RGB Orthophoto)"

    try:
        img_bytes = _prepare_thumbnail_bytes(target_img_path)
        vision_prompt = (
            f"這是無人機田間空拍試驗影像：{image_desc}。\n"
            f"分析焦點：{focus}\n"
            "請以專業農業航拍評估人員的視角，客觀列出你觀察到的關鍵視覺特徵：\n"
            "1. 作物行株排列與封壟覆蓋度\n"
            "2. 是否存在明顯缺株、禿斑、生長發育不良或土壤裸露區域及其方位\n"
            "3. 顏色分佈均勻性（植株深淺綠落差或異變斑塊）\n"
            "4. 邊界效應或排水灌溉相關的局部生長差異\n"
            "請精簡扼要以條列重點陳述具體觀察。"
        )
        binary_content = BinaryContent(data=img_bytes, media_type="image/png")
        vision_result = await vision_agent.run([vision_prompt, binary_content])
        return f"【多模態視覺判讀成果 - {image_desc}】\n{vision_result.output}"
    except Exception as e:
        return f"影像多模態視覺判讀時發生錯誤: {e}"


@agent.tool_plain
def query_vegetation_index(name_or_keyword: str = "") -> dict:
    """查詢農業無人機植生指標（Vegetation Indices）的數學公式、說明、支援波段與適用情境。"""
    query = (name_or_keyword or "").strip()

    # 1. 精確或大小寫比對
    for k, item in algos.items():
        if k.lower() == query.lower():
            filters = get_camera_filters_for(item["expr"], max_bands=4)
            is_rgb = "RGB" in filters
            return {
                "status": "success",
                "name": k,
                "formula_expr": item.get("expr"),
                "description": str(item.get("help", "無特別描述")),
                "range": item.get("range", [-1, 1]),
                "supported_bands": filters,
                "is_rgb_compatible": is_rgb,
                "note": "適用於一般無人機 RGB 空拍鏡頭" if is_rgb else "需要近紅外光 (NIR) 或多光譜鏡頭",
            }

    # 2. 關鍵字搜尋或清單查詢
    if query.lower() in ["rgb", "list", "all", ""]:
        rgb_list = [
            {"name": a["id"], "expr": a["expr"], "description": str(a.get("help", ""))}
            for a in get_algorithm_list(max_bands=3)
            if "RGB" in a.get("filters", [])
        ]
        return {
            "status": "list",
            "total_rgb_indices": len(rgb_list),
            "recommended_rgb_indices": rgb_list[:8],
            "message": "已列出無人機常見 RGB 植生指標。如需查詢特定指標細節，可指定指標名稱（例如 VARI、GLI）。",
        }

    # 3. 模糊搜尋
    matches = [
        {"name": k, "expr": v["expr"], "description": str(v.get("help", ""))}
        for k, v in algos.items()
        if query.lower() in k.lower() or query.lower() in str(v.get("help", "")).lower()
    ]
    if matches:
        return {
            "status": "matches",
            "matches": matches[:5],
        }

    return {
        "status": "not_found",
        "message": f"未找到名稱為「{query}」的植生指標。常見 RGB 指標包括：VARI, GLI, EXG, vNDVI, MPRI；NIR 多光譜指標包括：NDVI, GNDVI, SAVI, NDRE。",
    }
