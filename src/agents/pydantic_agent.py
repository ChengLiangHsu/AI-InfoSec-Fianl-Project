from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
import json
import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv

load_dotenv()

import numpy as np
from PIL import Image
from pydantic import BaseModel, Field
from pydantic_ai import (
    Agent,
    BinaryContent,
    RunContext,
)
from pydantic_ai.usage import UsageLimits

from src.usecases.ports.task import TaskPort
from src.usecases.task import _normalize_scenario_data
from src.config import ODM_DIR
from src.utility.formulas import (
    MULTISPECTRAL_REFERENCE_ALGOS,
    RGB_ALGORITHMS,
    get_algorithm_list,
    lookup_formula,
    normalize_rgb_formula,
)
from src.utility.spectral import generate_spectral_image

@dataclass
class ChatDeps:
    project_id: str
    task_port: TaskPort
    scenario_events: list[dict[str, Any]] = field(default_factory=list)


model = os.getenv("PYDANTIC_AI_MODEL", "google:gemini-3.7-flash")
agent = Agent(model, deps_type=ChatDeps, defer_model_check=True)
scenario_agent = Agent(model, deps_type=ChatDeps, defer_model_check=True)
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


@scenario_agent.system_prompt
async def scenario_system_prompt(ctx: RunContext[ChatDeps]) -> str:
    base_prompt = (
        "你是『田間試驗情境規劃助手』，專門在步驟 2 透過親切自然的繁體中文對話，協助使用者釐清這次無人機空拍的田間試驗情境，並動態生成下一步『框選實驗小區』要用的多型態紀錄表單。\n\n"
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
        "4. **訪談節奏與呼叫工具時機**：\n"
        "   - 若使用者的描述還太簡略（例如只點了「農藥藥效試驗」或只說「我想做試驗」），先親切回應並提出 1~2 個最關鍵的釐清問題（例如作物是什麼、預計比較哪幾種藥劑／倍數或哪幾個品種），字數精簡好讀。\n"
        "   - 一旦使用者提供了足夠建立表單草稿的資訊（例如已知道試驗類型與至少 1 個處理方向或組別，或使用者明確要求先建表單／套用建議模板），請**立即呼叫 `upsert_trial_scenario_form` 工具**產出並自動儲存表單，然後在回覆中簡要說明已生成哪些欄位與組別，並邀請使用者在右側微調或繼續用對話修改。\n"
        "   - 若目前專案已經有表單，使用者要求新增／修改／刪除欄位或組別時，務必**保留既有未要求改動的共通資訊與組別（含既有 id 與 color）**，再呼叫 `upsert_trial_scenario_form` 更新。\n"
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
) -> dict[str, Any]:
    """依據對話內容建立或更新步驟 2 的多型態動態試驗表單，並立即自動儲存至資料庫。"""
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

    raw_scenario: dict[str, Any] = {
        "version": 2,
        "type": (scenario_type or "custom").strip() or "custom",
        "title": (title or "試驗情境設定").strip() or "試驗情境設定",
        "description": (description or "").strip(),
        "metadata_fields": [f.model_dump() for f in (metadata_fields or [])],
        "metadata_values": dict(metadata_values or {}),
        "group_fields": [f.model_dump() for f in (group_fields or [])],
        "categories": raw_categories,
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
    }
