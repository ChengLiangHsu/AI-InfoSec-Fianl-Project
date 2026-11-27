from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
import json
import os
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

import numpy as np
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field
from pydantic_ai import (
    Agent,
    BinaryContent,
    RunContext,
)
from pydantic_ai.usage import UsageLimits

from src.usecases.ports.task import TaskPort
from src.usecases.task import _normalize_recommended_formulas, _normalize_scenario_data
from src.config import ODM_DIR
from src.utility.formulas import (
    MULTISPECTRAL_REFERENCE_ALGOS,
    RGB_ALGORITHMS,
    get_algorithm_list,
    lookup_formula,
    normalize_rgb_formula,
)
from src.utility.region_statistics import calculate_plots_statistics
from src.utility.spectral import generate_spectral_image

@dataclass
class ChatDeps:
    project_id: str
    task_port: TaskPort
    scenario_events: list[dict[str, Any]] = field(default_factory=list)
    question_events: list[dict[str, Any]] = field(default_factory=list)
    selected_plot_numbers: list[int] = field(default_factory=list)
    current_formula: str = "rgb"


model = os.getenv("PYDANTIC_AI_MODEL", "google:gemini-3.7-flash")
agent = Agent(model, deps_type=ChatDeps, defer_model_check=True)
scenario_agent = Agent(model, deps_type=ChatDeps, defer_model_check=True)
spectral_agent = Agent(model, deps_type=ChatDeps, defer_model_check=True)
vision_agent = Agent(model, defer_model_check=True)


@agent.system_prompt
async def system_prompt(ctx: RunContext[ChatDeps]) -> str:
    base_prompt = (
        "你是使用者的田間試驗好夥伴兼智慧評估代理人（Agricultural Drone Field Trial Buddy）。\n"
        "【溝通風格核心約束 - 極為重要，最嚴格執行】：\n"
        "1. 極短句朋友聊天：每次回覆嚴格限制在 1 到 2 句親切口語短句以內（總字數在 50 字以內），說完重點立刻停止，絕不多說一句廢話！\n"
        "2. 嚴禁任何形式的編號或項目符號清單（如 1. 2. 3.、-、*）、嚴禁粗體、嚴禁大標題！純粹像朋友在 LINE 或傳訊息一樣口語自然。\n"
        "3. 當進行光譜統計或影像判讀時，依然給出精確數值或觀察，但純粹用 1~2 句白話短句說出結論。\n\n"
        "【簡潔指令意圖對照】：\n"
        "- 使用者傳「系統功能介紹」時，回覆：「這套系統能把空拍照片自動拼成正射圖，還能算植生指標比對藥效喔！把照片拖進來就能開始了～」\n"
        "- 使用者傳「空拍拍攝建議」時，回覆：「建議航拍重疊率 70%~80%、垂直向下拍且光線均勻，照片記得要有 GPS 經緯度喔！」\n"
        "- 使用者傳「支援植生指標」時，回覆：「我們支援 VARI、GLI、EXG 等 RGB 指標，看受害葉片變色、雜草跟長勢都很清楚喔！」\n"
        "- 使用者傳「殺蟲劑藥效評估」時，回覆：「殺蟲劑試驗推薦看 VARI 或 GLI，能清楚看出受害葉片變色！接下來請點上方『繪製小區』標註田區吧！」\n"
        "- 使用者傳「除草劑防除試驗」時，回覆：「除草劑試驗推薦看 VARI 或 EXG，能明顯分辨雜草覆蓋與枯死！接下來可以開始畫小區囉！」\n"
        "- 使用者傳「長勢與缺株監測」時，回覆：「長勢監測推薦看 VARI 或 GLI，能清楚看出植株均勻度與空洞！接著點上方『繪製小區』標註吧！」\n\n"
        "【核心工具能力】：\n"
        "當使用者傳送「視覺診斷光譜」、「光譜數值統計」或「正射全景檢查」，或詢問具體田區數據時，調用相應工具並用 1~2 句極簡口語短句告知重點：\n"
        "1. `get_current_project_info`：確認專案基本資訊、正射圖生成狀態與可用光譜指標。\n"
        "2. `calculate_spectral_statistics`：獲取光譜指標數值與健康植生比例。\n"
        "3. `inspect_field_imagery`：視覺判讀田間正射圖或光譜圖中的行株距、缺株空洞、變色斑塊。\n"
        "4. `query_vegetation_index`：查詢植生指標公式與學理依據。"
    )
    pid = ctx.deps.project_id
    if pid and pid != "home":
        try:
            proj = await ctx.deps.task_port.get_task(pid)
            ortho_exists = (ODM_DIR / f"{pid}.png").exists()
            plots_count = len(proj.plots) if hasattr(proj, "plots") and proj.plots else 0
            scenario_desc = "尚未設定"
            if proj.scenario and isinstance(proj.scenario, dict):
                s_title = proj.scenario.get("title") or proj.scenario.get("type", "已設定")
                s_target = proj.scenario.get("target", "")
                scenario_desc = f"{s_title}{f'（{s_target}）' if s_target else ''}"

            base_prompt += (
                f"\n\n【當前專案資訊】\n"
                f"- 專案：{proj.name} (ID: {proj.id})\n"
                f"- 進度：{proj.progress}%，正射圖：{'已就緒' if ortho_exists else '生成中'}\n"
                f"- 試驗情境：{scenario_desc}\n"
                f"- 當前劃分小區：{plots_count} 區\n"
                f"請以 1~2 句親切短句協助使用者進行診斷或推薦下一步。"
            )
            if proj.progress < 100 and not proj.scenario:
                base_prompt += (
                    f"\n【運算等待期指引】：正射圖正在拼接中，專案尚未設定情境。"
                    f"若使用者打招呼或詢問，請用 1~2 句親切短句主動詢問試驗情境（如農藥或劑量），"
                    f"並提示可在上方卡片快速建立輸入欄位。"
                )
        except Exception:
            pass
    else:
        base_prompt += (
            "\n\n【首頁導引模式】：\n"
            "使用者目前位於首頁。以 1~2 句朋友口吻親切招呼並引導拖曳相片上傳。"
        )
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
        proj = await ctx.deps.task_port.get_task(pid)
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
    all_rgb_algos = [a["id"] for a in get_algorithm_list()]

    return {
        "status": "success",
        "project_id": pid,
        "project_name": proj.name,
        "images_count": proj.images,
        "progress": proj.progress,
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
    """計算並取得當前專案在指定光譜植生指標（如 VARI, GLI, EXG, MPRI, NDYI 等）下的田間數值統計資料。"""
    pid = ctx.deps.project_id
    if not pid or pid == "home":
        return {"status": "error", "message": "目前未選擇具體專案，無法計算田間光譜統計。"}

    await ctx.deps.task_port.get_task(pid)

    ortho_path = ODM_DIR / f"{pid}.png"
    if not ortho_path.exists():
            return {"status": "error", "message": "尚未找到該專案的正射圖，航拍拼接可能尚未完成。"}

    try:
        formula_id = normalize_rgb_formula(formula)
        expr, hrange = lookup_formula(formula_id)
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
    classification = _classify_vegetation(formula_id, valid_vals, vmin, vmax)
    homogeneity = _evaluate_field_homogeneity(stats["std_deviation"])

    return {
        "status": "success",
        "formula": formula_id,
        "formula_expression": RGB_ALGORITHMS[formula_id]["expr"],
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

    await ctx.deps.task_port.get_task(pid)

    ortho_path = ODM_DIR / f"{pid}.png"
    if not ortho_path.exists():
            return "正射圖檔案不存在，請確認空拍拼接任務是否已完成。"

    if image_target == "spectral":
        try:
            formula_id = normalize_rgb_formula(formula)
            lookup_formula(formula_id)
        except Exception as e:
            return f"不支援的 RGB 光譜指標 '{formula}': {e}"
        target_img_path = ODM_DIR / f"{pid}_{formula_id}.png"
        if not target_img_path.exists():
            try:
                generate_spectral_image(ortho_path, target_img_path, formula_id)
            except Exception as e:
                return f"生成光譜圖 {formula_id} 失敗: {e}"
        image_desc = f"專案 {pid} 的 {formula_id} 植生指標光譜圖（綠色為高活力植被、黃色為中度活力、紅/黑色為低活力或土壤）"
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
        vision_result = await vision_agent.run(
            [vision_prompt, binary_content], usage=ctx.usage,
            usage_limits=UsageLimits(request_limit=6, output_tokens_limit=6000),
        )
        return f"【多模態視覺判讀成果 - {image_desc}】\n{vision_result.output}"
    except Exception as e:
        return f"影像多模態視覺判讀時發生錯誤: {e}"


@agent.tool_plain
def query_vegetation_index(name_or_keyword: str = "") -> dict:
    """查詢農業無人機植生指標（Vegetation Indices）的數學公式、說明、適用限制與波段需求。"""
    query = (name_or_keyword or "").strip()

    # 1. 精確或大小寫比對（優先查純 RGB 可執行指標，再查多光譜參考清單）
    for k, item in RGB_ALGORITHMS.items():
        if k.lower() == query.lower():
            return {
                "status": "success",
                "name": k,
                "label": item.get("label", k),
                "formula_expr": item.get("expr"),
                "description": str(item.get("help", "")),
                "limitation": str(item.get("limitation", "")),
                "range": item.get("range", (-1, 1)),
                "supported_bands": ["RGB"],
                "is_rgb_compatible": True,
                "note": "本系統可直接以純 RGB 三通道計算；請留意該指標的適用限制。",
            }

    for k, item in MULTISPECTRAL_REFERENCE_ALGOS.items():
        if k.lower() == query.lower():
            return {
                "status": "success",
                "name": k,
                "formula_expr": item.get("expr"),
                "description": str(item.get("help", "")),
                "required_bands": item.get("required_bands", []),
                "range": item.get("range", (-1, 1)),
                "supported_bands": [],
                "is_rgb_compatible": False,
                "note": "此指標需要近紅外光（NIR）、窄波段或熱紅外感測器，本系統純 RGB 影像無法計算。",
            }

    # 2. 關鍵字搜尋或清單查詢
    if query.lower() in ["rgb", "list", "all", ""]:
        rgb_list = [
            {
                "name": a["id"],
                "label": a.get("label", a["id"]),
                "expr": a["expr"],
                "description": str(a.get("help", "")),
                "limitation": str(a.get("limitation", "")),
            }
            for a in get_algorithm_list()
        ]
        return {
            "status": "list",
            "total_rgb_indices": len(rgb_list),
            "recommended_rgb_indices": rgb_list,
            "message": "已列出本系統支援的 5 項純 RGB 植生／色彩指標（MPRI 為 RGB 替代公式）。",
        }

    # 3. 模糊搜尋（涵蓋純 RGB 與多光譜參考清單）
    all_reference = {**RGB_ALGORITHMS, **MULTISPECTRAL_REFERENCE_ALGOS}
    matches = [
        {
            "name": k,
            "expr": v["expr"],
            "description": str(v.get("help", "")),
            "is_rgb_compatible": k in RGB_ALGORITHMS,
        }
        for k, v in all_reference.items()
        if query.lower() in k.lower() or query.lower() in str(v.get("help", "")).lower()
    ]
    if matches:
        return {
            "status": "matches",
            "matches": matches[:5],
        }

    return {
        "status": "not_found",
        "message": f"未找到名稱為「{query}」的植生指標。本系統支援的純 RGB 指標為：NDYI、VARI、MPRI、EXG、GLI；多光譜參考指標包括：NDVI、NDRE、PRI、SAVI。",
    }


@agent.tool
async def recommend_trial_scenario(
    ctx: RunContext[ChatDeps],
    scenario_type: str = "pesticide",
    target_name: str = "",
) -> dict[str, Any]:
    """依據使用者試驗類別（pesticide 農藥、fertilizer 肥料、variety 品種）推薦標準輸入欄位、組別與高對比分類色彩。"""
    stype = scenario_type.lower()
    if "pesticide" in stype or "藥" in stype or "蟲" in stype or "草" in stype:
        return {
            "status": "success",
            "type": "pesticide",
            "title": "農藥藥效試驗",
            "target": target_name or "快得寧",
            "target_label": "農藥名稱",
            "categories": [
                {"name": "未施藥對照 (CK)", "dose": "", "color": "#64748b", "is_control": True},
                {"name": "500x", "dose": "500x", "color": "#10b981", "is_control": False},
                {"name": "1000x", "dose": "1000x", "color": "#8b5cf6", "is_control": False},
                {"name": "2000x", "dose": "2000x", "color": "#f59e0b", "is_control": False},
            ],
            "message": "已推薦農藥藥效試驗模板，包含未施藥對照 (CK) 與三組倍數劑量及專屬高對比色彩標籤。",
        }
    if "fertilizer" in stype or "肥" in stype:
        return {
            "status": "success",
            "type": "fertilizer",
            "title": "肥料肥力試驗",
            "target": target_name or "特肥一號",
            "target_label": "肥料品項",
            "categories": [
                {"name": "不施肥對照 (CK)", "dose": "", "color": "#64748b", "is_control": True},
                {"name": "減量組 (50%)", "dose": "50%", "color": "#0ea5e9", "is_control": False},
                {"name": "標準量 (100%)", "dose": "100%", "color": "#10b981", "is_control": False},
                {"name": "倍量組 (200%)", "dose": "200%", "color": "#8b5cf6", "is_control": False},
            ],
            "message": "已推薦肥料試驗模板，包含不施肥對照 (CK) 與三組施用量及色彩標籤。",
        }
    return {
        "status": "success",
        "type": "custom",
        "title": "自訂田間試驗",
        "target": target_name or "處理品項",
        "target_label": "試驗品項名稱",
        "categories": [
            {"name": "對照組 (CK)", "dose": "", "color": "#64748b", "is_control": True},
            {"name": "處理組 A", "dose": "處理 A", "color": "#10b981", "is_control": False},
            {"name": "處理組 B", "dose": "處理 B", "color": "#8b5cf6", "is_control": False},
        ],
        "message": "已推薦自訂試驗模板與色彩標籤。",
    }


# ============================================================================
# 步驟 2 專用：田間試驗情境訪談與動態多型態表單建構 Agent (scenario_agent)
# ============================================================================


class DynamicFieldInput(BaseModel):
    """單一動態表單欄位定義。"""
    key: str = Field(description="英文或底線識別鍵，如 treatment、dose、variety、spray_date、method")
    label: str = Field(description="繁體中文欄位顯示名稱，如 藥劑名稱、稀釋倍數、品種名稱、施藥日期")
    type: Literal["text", "number", "select", "date", "boolean"] = Field(
        default="text",
        description="表單輸入元件型態：text 文字、number 數字、select 下拉選單、date 日期、boolean 開關",
    )
    unit: str = Field(default="", description="數字欄位單位（僅 number 需要，如 倍、x、kg/ha、mL/L、%）")
    options: list[str] = Field(default_factory=list, description="下拉選項清單（僅 type='select' 時填寫）")
    placeholder: str = Field(default="", description="輸入框提示文字")
    required: bool = Field(default=False, description="是否為必填欄位")


class TrialGroupInput(BaseModel):
    """單一實驗處理組（不含對照組 CK，對照組會由系統自動鎖定於第 1 列）。"""
    id: str = Field(default="", description="既有組別 ID（修改既有組別時保留原 id，新增可留空）")
    name: str = Field(default="", description="精簡顯示名稱（可留空由系統自動組合主要欄位）")
    color: str = Field(default="", description="十六進位色碼（可留空由系統自動分配高對比色彩）")
    values: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="對應 group_fields 各欄位 key 的預填數值",
    )


class InterviewQuestionOption(BaseModel):
    """互動訪談問題的單一選項。"""
    label: str = Field(description="簡潔明確的繁體中文選項文字（建議 4~18 字）")
    description: str = Field(default="", description="選填：一句話補充說明此選項的意義或對應欄位")
    recommended: bool = Field(default=False, description="是否為最推薦的預設選項（每題最多 1 個 True）")


def _normalize_interview_question(
    question: str,
    options: list[InterviewQuestionOption | dict[str, Any]],
    is_multi_select: bool = False,
    allow_custom: bool = True,
    step_label: str = "",
    can_generate_now: bool = False,
) -> dict[str, Any]:
    """正規化互動訪談問題卡片資料，確保推薦選項置頂且結構安全。"""
    cleaned_options: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    has_recommended = False

    for raw in options:
        if isinstance(raw, InterviewQuestionOption):
            label = raw.label.strip()
            description = raw.description.strip()
            recommended = bool(raw.recommended)
        elif isinstance(raw, dict):
            label = str(raw.get("label") or "").strip()
            description = str(raw.get("description") or "").strip()
            recommended = bool(raw.get("recommended", False))
        else:
            continue

        if not label or label in seen_labels:
            continue
        seen_labels.add(label)

        if recommended and not is_multi_select:
            if has_recommended:
                recommended = False
            else:
                has_recommended = True

        cleaned_options.append(
            {
                "label": label,
                "description": description,
                "recommended": recommended,
            }
        )
        if len(cleaned_options) >= 6:
            break

    # 將推薦選項移至最前面（保留其餘順序）
    cleaned_options.sort(key=lambda item: not item["recommended"])

    return {
        "id": f"q-{uuid4().hex[:8]}",
        "question": (question or "").strip() or "請選擇本次田間試驗的設定方向：",
        "options": cleaned_options,
        "is_multi_select": bool(is_multi_select),
        "allow_custom": bool(allow_custom),
        "step_label": (step_label or "").strip(),
        "can_generate_now": bool(can_generate_now),
    }


@scenario_agent.system_prompt
async def scenario_system_prompt(ctx: RunContext[ChatDeps]) -> str:
    base_prompt = (
        "你是專業的『田間試驗情境規劃引導人』，專門在步驟 2 以專業、簡潔、自然的繁體中文，引導使用者釐清無人機空拍的田間試驗設計，並動態建置或調整下一步『框選實驗小區』要用的多型態紀錄表單。\n"
        "語氣保持專業顧問風格，直接聚焦在試驗本身（作物、處理組、紀錄欄位、施用條件），避免使用「透過問答協助你」「由 AI 主動提問」等生硬的系統後設用語。\n\n"
        "【核心設計原則】：\n"
        "1. **依情境決定欄位，絕不硬塞無關欄位**：\n"
        "   - 用藥／農藥藥效試驗：通常需要藥劑名稱 (`text`)、劑量或稀釋倍數 (`number` 搭配 `unit` 如 `倍` / `mL/ha` 或 `text`)、可搭配施用方式 (`select`) 或施藥日期 (`date`)。\n"
        "   - 肥料／營養試驗：通常需要肥料品項 (`text`)、施用量 (`number` 搭配 `unit` 如 `kg/ha` 或 `%`)。\n"
        "   - 品種比較、長勢與缺株監測、栽培／覆蓋／灌溉方式對比等**非用藥情境**：**不需要**劑量欄位！改生成該情境真正需要的欄位（如品種名稱 `text`、栽培方式 `select`、播種日期 `date`、是否覆膜 `boolean` 等）。\n"
        "2. **兩區塊表單結構**：\n"
        "   - `metadata_fields` + `metadata_values`：整場試驗共通背景資訊（選填，例如試驗作物、試驗日期、田區地點、目標病蟲害），保持精簡（1~4 欄即可）。\n"
        "   - `group_fields` + `groups`：各實驗處理組的動態欄位與組別清單，每列將直接成為步驟 3 框選小區時可點選套用的組別。\n"
        "3. **對照組 (CK) 自動內建且鎖定**：\n"
        "   - 系統會自動在表單第 1 列建立且鎖定對照組 (CK)，不可刪除。\n"
        "   - **不要**問使用者需不需要對照組，也**不要**把對照組放進 `groups` 參數；只要透過 `control_label` 給它一個符合情境的名稱（如「未施藥對照 (CK)」「不施肥對照 (CK)」「標準對照 (CK)」）。\n"
        "4. **主動逐題訪談模式（Grill-me 風格）**：\n"
        "   - 當使用者尚未提供足以建構完整表單的資訊（例如只選了「農藥藥效試驗」、或剛說想做某種試驗但未指定作物／處理組／額外欄位），請沿著設計決策樹**一次只問一個最關鍵的問題**，並**必須呼叫 `ask_clarifying_question` 工具**呈現互動選項卡片：\n"
        "     - 第 1 層：試驗類型與目的（若未知）\n"
        "     - 第 2 層：試驗作物（若未知）\n"
        "     - 第 3 層：依試驗類型分支確認處理組設計（農藥→藥劑與稀釋倍數/劑量設計；肥料→肥料品項與施用比例；品種→比較品種；監測→分區或栽培因子，非用藥切勿問劑量）\n"
        "     - 第 4 層：確認是否需要附加輔助欄位（如施用日期、施用時期、噴施方式、是否覆膜等），此時可用 `is_multi_select=True` 且設定 `can_generate_now=True`。\n"
        "   - **每題務必提供 3~5 個具體好選的選項**，並將你最建議的 1 個選項標記 `recommended=True`（附簡短 `description` 說明推薦原因或對應效果）。\n"
        "   - **每輪最多呼叫一次 `ask_clarifying_question`**。呼叫該工具後，你的文字回覆請保持在 1~2 句簡短親切的承接語（例如「了解，我們來確認這次試驗的作物～」），**絕對不要**在文字中把選項再條列一遍（前端會將工具參數直接渲染為可點選的互動卡片）。\n"
        "   - 若使用者提供的資訊已足以決定表單草稿（例如已點選完整情境範例、或已回答完主要設計問題、或明確說「直接生成表單／套用建議模板」），請**立即呼叫 `upsert_trial_scenario_form` 工具**建立並儲存表單，簡要說明已產出的欄位、組別與選定的步驟 4 適用光譜指標，無須再追問。\n"
        "   - 若目前專案已經有表單，使用者要求新增／修改／刪除欄位、組別或更換步驟 4 適用光譜時，務必**保留既有未要求改動的共通資訊、組別（含既有 id 與 color）與既有 `recommended_formulas`**，直接呼叫 `upsert_trial_scenario_form` 更新；僅在需求存在明顯歧義時才呼叫 `ask_clarifying_question` 確認。\n"
        "5. **自動決定步驟 4 適用光譜指標（`recommended_formulas`）**：\n"
        "   - 呼叫 `upsert_trial_scenario_form` 時，務必從本系統 5 種純 RGB 指標（`VARI`、`GLI`、`EXG`、`NDYI`、`MPRI`）中挑選 2~3 個最適合本次試驗目標的指標填入 `recommended_formulas`，步驟 4 將嚴格只顯示這些光譜選項（加上 RGB 原圖）：\n"
        "     - 農藥／殺蟲劑／病害藥效試驗：推薦 `[\"VARI\", \"GLI\"]`（觀察受害葉片變色與綠葉覆蓋差異；若關注黃化可加 `NDYI`）。\n"
        "     - 除草劑防除試驗：推薦 `[\"EXG\", \"VARI\"]`（強化雜草綠色覆蓋與枯死／裸土對比）。\n"
        "     - 肥料／營養／黃化／開花觀測：推薦 `[\"NDYI\", \"VARI\", \"GLI\"]`（偵測葉色黃綠變化與長勢）。\n"
        "     - 品種比較／田間長勢與缺株監測：推薦 `[\"VARI\", \"GLI\", \"EXG\"]`（評估冠層覆蓋度、綠度均勻度與缺株空洞）。\n"
        "     - 葉色綠紅對比或特別指定光化學替代指標時，可納入 `MPRI`。\n"
    )

    pid = ctx.deps.project_id
    if pid and pid != "home":
        try:
            proj = await ctx.deps.task_port.get_task(pid)
            scenario_json = (
                json.dumps(proj.scenario, ensure_ascii=False)
                if proj.scenario
                else "尚未建立表單"
            )
            base_prompt += (
                f"\n【當前專案狀態】\n"
                f"- 專案名稱：{proj.name}\n"
                f"- 航拍拼接進度：{proj.progress}%\n"
                f"- 目前資料庫中最新的表單 JSON（包含使用者可能在右側手動編輯的內容）：\n"
                f"{scenario_json}\n"
            )
        except Exception:
            pass
    return base_prompt


@scenario_agent.tool
async def ask_clarifying_question(
    ctx: RunContext[ChatDeps],
    question: str,
    options: list[InterviewQuestionOption],
    is_multi_select: bool = False,
    allow_custom: bool = True,
    step_label: str = "",
    can_generate_now: bool = False,
) -> dict[str, Any]:
    """向使用者提出單一結構化選擇題卡片（附推薦選項與自訂輸入），一次一題引導建置試驗表單。"""
    payload = _normalize_interview_question(
        question=question,
        options=options,
        is_multi_select=is_multi_select,
        allow_custom=allow_custom,
        step_label=step_label,
        can_generate_now=can_generate_now,
    )
    ctx.deps.question_events.append(payload)
    return {
        "status": "question_rendered",
        "question_id": payload["id"],
        "question": payload["question"],
        "option_count": len(payload["options"]),
        "note": "前端已顯示互動選項卡片，請僅回覆 1 句簡短親切的引導語，切勿在純文字中重複條列選項。",
    }


def _default_recommended_formulas(scenario_type: str, title: str = "", description: str = "") -> list[str]:
    """依試驗類型與描述推導預設適用的純 RGB 光譜指標清單。"""
    combined = f"{scenario_type} {title} {description}".lower()
    if any(k in combined for k in ("herbicide", "除草", "雜草", "weed")):
        return ["EXG", "VARI"]
    if any(k in combined for k in ("fertilizer", "肥", "營養", "黃化", "開花", "氮")):
        return ["NDYI", "VARI", "GLI"]
    if any(k in combined for k in ("variety", "品種", "monitor", "長勢", "缺株", "growth")):
        return ["VARI", "GLI", "EXG"]
    if any(k in combined for k in ("pesticide", "insecticide", "fungicide", "藥", "蟲", "病")):
        return ["VARI", "GLI"]
    return ["VARI", "GLI", "EXG"]


@scenario_agent.tool
async def upsert_trial_scenario_form(
    ctx: RunContext[ChatDeps],
    scenario_type: str,
    title: str,
    description: str = "",
    control_label: str = "對照組 (CK)",
    metadata_fields: list[DynamicFieldInput] | None = None,
    metadata_values: dict[str, str | int | float | bool | None] | None = None,
    group_fields: list[DynamicFieldInput] | None = None,
    groups: list[TrialGroupInput] | None = None,
    recommended_formulas: list[str] | None = None,
) -> dict[str, Any]:
    """依據對話內容建立或更新步驟 2 的多型態動態試驗表單與步驟 4 適用光譜清單，並立即自動儲存至資料庫。"""
    pid = ctx.deps.project_id
    if not pid or pid == "home":
        return {"status": "error", "message": "目前未選定專案，無法儲存表單。"}

    raw_categories: list[dict[str, Any]] = [
        {
            "id": "ck",
            "name": (control_label or "").strip() or "對照組 (CK)",
            "is_control": True,
            "values": {},
        }
    ]
    for grp in groups or []:
        raw_categories.append(
            {
                "id": grp.id,
                "name": grp.name,
                "color": grp.color,
                "is_control": False,
                "values": dict(grp.values or {}),
            }
        )

    cleaned_formulas = _normalize_recommended_formulas(recommended_formulas)
    if not cleaned_formulas:
        cleaned_formulas = _default_recommended_formulas(scenario_type, title, description)

    raw_scenario: dict[str, Any] = {
        "version": 2,
        "type": (scenario_type or "custom").strip() or "custom",
        "title": (title or "試驗情境設定").strip() or "試驗情境設定",
        "description": (description or "").strip(),
        "metadata_fields": [f.model_dump() for f in (metadata_fields or [])],
        "metadata_values": dict(metadata_values or {}),
        "group_fields": [f.model_dump() for f in (group_fields or [])],
        "categories": raw_categories,
        "recommended_formulas": cleaned_formulas,
    }

    normalized = _normalize_scenario_data(raw_scenario)
    await ctx.deps.task_port.update_scenario(pid, normalized)
    ctx.deps.scenario_events.append(normalized)

    return {
        "status": "saved",
        "title": normalized.get("title"),
        "metadata_field_count": len(normalized.get("metadata_fields", [])),
        "group_field_count": len(normalized.get("group_fields", [])),
        "category_count": len(normalized.get("categories", [])),
        "recommended_formulas": normalized.get("recommended_formulas", []),
    }


# ============================================================================
# 步驟 4 專用：光譜分析與小區評估唯讀顧問 Agent (spectral_agent)
# ============================================================================


def _format_plot_label(plot: Any) -> str:
    if getattr(plot, "is_control", False):
        return f"#{plot.plot_number} 對照組 (CK)"
    parts = [p for p in (getattr(plot, "treatment", ""), getattr(plot, "dose", "")) if p]
    suffix = " ".join(parts) if parts else "未分類處理組"
    return f"#{plot.plot_number} {suffix}"


def _prepare_cropped_plot_bytes(
    image_path: Path,
    coords_str: str,
    padding_ratio: float = 0.15,
    max_size: tuple[int, int] = (768, 768),
) -> bytes:
    """從正射圖或光譜圖依小區多邊形外接框裁切局部影像並描繪輪廓供視覺模型判讀。"""
    Image.MAX_IMAGE_PIXELS = None
    pts = json.loads(coords_str)
    with Image.open(image_path) as im:
        w, h = im.size
        px_pts = [(float(p[0]) * w, float(p[1]) * h) for p in pts]
        xs = [p[0] for p in px_pts]
        ys = [p[1] for p in px_pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        pad_x = max(16.0, (max_x - min_x) * padding_ratio)
        pad_y = max(16.0, (max_y - min_y) * padding_ratio)

        left = max(0, int(np.floor(min_x - pad_x)))
        top = max(0, int(np.floor(min_y - pad_y)))
        right = min(w, int(np.ceil(max_x + pad_x)))
        bottom = min(h, int(np.ceil(max_y + pad_y)))
        if right <= left or bottom <= top:
            return _prepare_thumbnail_bytes(image_path, max_size=max_size)

        cropped = im.crop((left, top, right, bottom)).convert("RGBA")
        draw = ImageDraw.Draw(cropped)
        rel_pts = [(x - left, y - top) for x, y in px_pts]
        if len(rel_pts) >= 3:
            draw.polygon(rel_pts, outline=(56, 189, 248, 230), width=max(2, int(min(cropped.size) * 0.008)))
        cropped.thumbnail(max_size)
        buf = BytesIO()
        cropped.save(buf, format="PNG")
        return buf.getvalue()


@spectral_agent.system_prompt
async def spectral_system_prompt(ctx: RunContext[ChatDeps]) -> str:
    base_prompt = (
        "你是專業的『農業無人機光譜分析顧問（Spectral Agronomist）』，專門在步驟 4 協助使用者解讀田間試驗的光譜指數數值、比較處理組與對照組 (CK) 的差異，並進行小區局部影像的視覺判讀。\n\n"
        "【核心原則】：\n"
        "1. **專業精簡、條理清晰**：使用繁體中文，以簡潔清楚的結構呈現重點結論、量化數據對比（附上相對對照組 CK 的差值或百分比）與農藝建議；避免冗長空話，但也不要過度簡化而遺漏關鍵數值。\n"
        "2. **嚴格唯讀原則**：你僅負責數據與影像分析，**不會也不可宣稱**幫使用者切換右側地圖的光譜演算法或更改小區選取狀態；若建議參考其他已啟用指標，請提醒使用者可於右側地圖自行切換檢視。\n"
        "3. **嚴謹對照實驗設計**：所有解讀皆應對照本專案的試驗情境、處理組與對照組 (CK) 基準，並遵守純 RGB 光譜的物理限制（不可將純 RGB 指標誤稱為需近紅外光的 NDVI／NDRE）。\n"
        "4. **善用工具取得真實數據**：\n"
        "   - 回答數值分析或處理組比較前，務必呼叫 `get_selected_plots_spectral_stats` 取得精確的小區與 CK 統計數據。\n"
        "   - 回答視覺長勢、缺株、變色斑塊或邊界效應問題時，務必呼叫 `inspect_plot_imagery` 檢視裁切後的目標小區影像（或全田區影像）。\n"
        "   - 回答指標學理或公式限制時，可呼叫 `query_vegetation_index`。\n"
    )

    pid = ctx.deps.project_id
    if pid and pid != "home":
        try:
            proj = await ctx.deps.task_port.get_task(pid)
            scenario = proj.scenario if isinstance(proj.scenario, dict) else {}
            s_title = scenario.get("title") or "未命名試驗"
            s_type = scenario.get("type") or "custom"
            rec_formulas = _normalize_recommended_formulas(scenario.get("recommended_formulas"))
            formula_scope = ", ".join(rec_formulas) if rec_formulas else "全部純 RGB 指標 (NDYI, VARI, MPRI, EXG, GLI)"

            plots_by_num = {p.plot_number: p for p in (proj.plots or [])}
            selected_nums = [n for n in ctx.deps.selected_plot_numbers if n in plots_by_num]
            if selected_nums:
                selected_desc = "、".join(_format_plot_label(plots_by_num[n]) for n in selected_nums)
            else:
                selected_desc = f"全田區（共 {len(plots_by_num)} 個小區，目前未指定單一小區）"

            cur_formula = ctx.deps.current_formula or "rgb"
            cur_formula_label = "RGB 原始正射圖" if cur_formula.lower() == "rgb" else cur_formula

            base_prompt += (
                f"\n【當前步驟 4 分析上下文】\n"
                f"- 專案名稱：{proj.name}\n"
                f"- 試驗情境：{s_title}（類型：{s_type}）\n"
                f"- 本試驗適用光譜清單：{formula_scope}\n"
                f"- 目前綁定分析對象：{selected_desc}\n"
                f"- 右側地圖目前檢視圖層：{cur_formula_label}\n"
            )
        except Exception:
            pass
    return base_prompt


@spectral_agent.tool
async def get_selected_plots_spectral_stats(
    ctx: RunContext[ChatDeps],
    plot_numbers: list[int] | None = None,
) -> dict[str, Any]:
    """取得目前選取小區（或指定小區清單；若皆未指定則回傳全田區與各處理組平均）的 RGB 與適用光譜統計，並附上相對對照組 (CK) 的差值。"""
    pid = ctx.deps.project_id
    if not pid or pid == "home":
        return {"status": "error", "message": "目前未選定專案，無法計算小區統計。"}

    proj = await ctx.deps.task_port.get_task(pid)
    ortho_path = ODM_DIR / f"{pid}.png"
    if not ortho_path.exists():
        return {"status": "error", "message": "尚未找到正射圖檔案，請確認航拍拼接是否已完成。"}
    if not proj.plots:
        return {"status": "error", "message": "此專案尚未標註任何實驗小區。"}

    scenario = proj.scenario if isinstance(proj.scenario, dict) else {}
    rec_formulas = _normalize_recommended_formulas(scenario.get("recommended_formulas"))
    allowed_set = set(rec_formulas) if rec_formulas else None

    plots_dicts = [
        {
            "plot_number": p.plot_number,
            "coords": p.coords,
            "is_control": p.is_control,
            "treatment": p.treatment,
            "dose": p.dose,
        }
        for p in proj.plots
    ]
    batch = calculate_plots_statistics(ortho_path, plots_dicts)

    ck_baseline = batch.get("control_baseline")
    ck_means: dict[str, float | None] = {}
    if ck_baseline:
        for row in ck_baseline.get("algorithms", []):
            ck_means[row["id"]] = row.get("index_mean")

    def _enrich_algos(algos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for row in algos:
            aid = row["id"]
            if allowed_set is not None and aid not in allowed_set:
                continue
            mean_val = row.get("index_mean")
            ck_val = ck_means.get(aid)
            delta = (
                round(mean_val - ck_val, 4)
                if mean_val is not None and ck_val is not None
                else None
            )
            pct = (
                round(((mean_val - ck_val) / abs(ck_val)) * 100.0, 2)
                if delta is not None and ck_val is not None and abs(ck_val) > 1e-6
                else None
            )
            enriched.append(
                {
                    "id": aid,
                    "index_mean": round(mean_val, 4) if mean_val is not None else None,
                    "delta_vs_ck": delta,
                    "pct_vs_ck": pct,
                    "valid_pixel_count": row.get("valid_pixel_count", 0),
                }
            )
        return enriched

    target_nums = plot_numbers if plot_numbers is not None else list(ctx.deps.selected_plot_numbers)
    if target_nums:
        target_set = set(target_nums)
        selected_plots = [
            {
                "plot_number": p["plot_number"],
                "is_control": p["is_control"],
                "treatment": p["treatment"],
                "dose": p["dose"],
                "pixel_count": p["pixel_count"],
                "rgb_mean": p["rgb_mean"],
                "algorithms": _enrich_algos(p["algorithms"]),
            }
            for p in batch["plots"]
            if p["plot_number"] in target_set
        ]
        return {
            "status": "success",
            "scope": "selected_plots",
            "recommended_formulas": rec_formulas or [a["id"] for a in get_algorithm_list()],
            "selected_plots": selected_plots,
            "control_baseline": (
                {
                    "plot_count": ck_baseline["plot_count"],
                    "algorithms": _enrich_algos(ck_baseline["algorithms"]),
                }
                if ck_baseline
                else None
            ),
        }

    groups = [
        {
            "label": g["label"],
            "is_control": g["is_control"],
            "plot_count": g["plot_count"],
            "plot_numbers": g["plot_numbers"],
            "rgb_mean": g["rgb_mean"],
            "algorithms": _enrich_algos(g["algorithms"]),
        }
        for g in batch["treatment_groups"]
    ]
    return {
        "status": "success",
        "scope": "whole_field",
        "recommended_formulas": rec_formulas or [a["id"] for a in get_algorithm_list()],
        "total_plots": len(batch["plots"]),
        "treatment_groups": groups,
        "field_summary": {
            "plot_count": batch["field_summary"]["plot_count"],
            "pixel_count": batch["field_summary"]["pixel_count"],
            "rgb_mean": batch["field_summary"]["rgb_mean"],
            "algorithms": _enrich_algos(batch["field_summary"]["algorithms"]),
        },
    }


@spectral_agent.tool
async def inspect_plot_imagery(
    ctx: RunContext[ChatDeps],
    plot_number: int | None = None,
    image_target: Literal["orthophoto", "spectral"] = "spectral",
    formula: str | None = None,
    focus: str = "觀察目標小區作物長勢均勻度、缺株空洞、葉色黃化或局部變色異常",
) -> str:
    """裁切指定（或目前選取之）小區的正射圖或光譜熱圖並以多模態視覺模型判讀；若未指定小區則檢視全田區影像。"""
    pid = ctx.deps.project_id
    if not pid or pid == "home":
        return "目前未選定專案，無法進行視覺判讀。"

    proj = await ctx.deps.task_port.get_task(pid)
    ortho_path = ODM_DIR / f"{pid}.png"
    if not ortho_path.exists():
        return "正射圖檔案不存在，無法進行視覺判讀。"

    scenario = proj.scenario if isinstance(proj.scenario, dict) else {}
    rec_formulas = _normalize_recommended_formulas(scenario.get("recommended_formulas"))
    active_formula = formula
    if not active_formula:
        if ctx.deps.current_formula and ctx.deps.current_formula.lower() != "rgb":
            active_formula = ctx.deps.current_formula
        elif rec_formulas:
            active_formula = rec_formulas[0]
        else:
            active_formula = "VARI"

    if image_target == "spectral":
        try:
            formula_id = normalize_rgb_formula(active_formula)
            lookup_formula(formula_id)
        except Exception as e:
            return f"不支援的 RGB 光譜指標 '{active_formula}': {e}"
        target_img_path = ODM_DIR / f"{pid}_{formula_id}.png"
        if not target_img_path.exists():
            try:
                generate_spectral_image(ortho_path, target_img_path, formula_id)
            except Exception as e:
                return f"生成光譜圖 {formula_id} 失敗: {e}"
        layer_desc = f"{formula_id} 光譜熱圖（綠＝高活力、黃＝中度、紅／黑＝低活力或裸土）"
    else:
        target_img_path = ortho_path
        layer_desc = "原始 RGB 正射影像"

    target_plot_num = plot_number
    if target_plot_num is None and ctx.deps.selected_plot_numbers:
        target_plot_num = ctx.deps.selected_plot_numbers[0]

    target_plot = next((p for p in (proj.plots or []) if p.plot_number == target_plot_num), None)
    try:
        if target_plot is not None:
            img_bytes = _prepare_cropped_plot_bytes(target_img_path, target_plot.coords)
            scope_desc = f"小區 {_format_plot_label(target_plot)} 局部裁切影像（藍色細框內為該小區範圍）"
        else:
            img_bytes = _prepare_thumbnail_bytes(target_img_path)
            scope_desc = "全田區縮圖"

        vision_prompt = (
            f"這是農業無人機田間試驗的 {scope_desc}，圖層為：{layer_desc}。\n"
            f"判讀焦點：{focus}\n"
            "請以專業農藝航拍評估視角，條列 3~4 點具體觀察：\n"
            "1. 冠層覆蓋度與行株排列整齊度\n"
            "2. 區域內是否存在缺株、禿斑、裸土或局部變色／黃化斑塊及其方位\n"
            "3. 顏色分佈均勻性與邊界效應\n"
            "請精簡客觀陳述。"
        )
        binary_content = BinaryContent(data=img_bytes, media_type="image/png")
        vision_result = await vision_agent.run(
            [vision_prompt, binary_content],
            usage=ctx.usage,
            usage_limits=UsageLimits(request_limit=6, output_tokens_limit=6000),
        )
        return f"【多模態視覺判讀 - {scope_desc} / {layer_desc}】\n{vision_result.output}"
    except Exception as e:
        return f"影像多模態視覺判讀時發生錯誤: {e}"


spectral_agent.tool_plain(query_vegetation_index)
