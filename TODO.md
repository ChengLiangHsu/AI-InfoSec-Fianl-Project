# 專案實作待辦事項清單 (Project TODO)

> 依據 [REQUIREMENT.md](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/REQUIREMENT.md) 與 [docs/06_execution_plan.md](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/docs/06_execution_plan.md) 解析之具體實作任務。

---

## 階段一：Proposal、可行性原型與文件整備 (Phase 1: Proposal, PoC & Docs)

- [ ] **AI 代理可行性驗證與對話平台原型 (Walking Skeleton PoC)**
  - [ ] 建立 `src/uav_trial_assessor/{entity,usecase,adapter}` 與 `bootstrap.py` 的最小套件骨架。
  - [ ] 實作 `src/uav_trial_assessor/usecase/run_agent.py` 與 `src/uav_trial_assessor/usecase/port/agent.py`：建立基礎對話流程與 Agent port。
  - [ ] 實作 `src/uav_trial_assessor/adapter/agent/pydantic_ai_agent.py`：以 Pydantic AI 串接 Mock 工具呼叫 (Tool Calling)。
  - [ ] 架設 FastAPI HTTP adapter (`src/uav_trial_assessor/adapter/http/app.py`、`src/uav_trial_assessor/adapter/http/router/chat.py`)：提供 `/api/chat` 對話端點與 Swagger 測試介面。
  - [ ] 驗證端到端連通性：使用者提問 $\rightarrow$ FastAPI adapter $\rightarrow$ `run_agent` usecase $\rightarrow$ Agent adapter $\rightarrow$ 模擬工具回傳 $\rightarrow$ 產出回應閉環。
- [ ] **文獻補正與驗證**
  - [ ] 補齊 [docs/07_references.md](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/docs/07_references.md) 中標記 `※` 的 9 篇文獻完整作者、出處與年份（如 Ref [3, 5, 6, 7, 9, 11, 14, 15, 17, 19, 21, 22]）。
  - [ ] 取得 TACTRI 水稻害蟲/雜草試驗準則與 EPPO PP 1/152(4) 原始文字檔備用。
- [ ] **建立專案規格書初稿**
  - [ ] 依 [REQUIREMENT.md:L190-191](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/REQUIREMENT.md#L190-191) 建立根目錄 `DESIGN.md`，設定核心說明路徑架構骨架。
- [ ] **修正專案導引文件**
  - [ ] 修正 [README.md:L29](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/README.md#L29) 連結至 `docs/07_references.md`（原 `REFERENCE.md` 斷鏈）。
  - [x] 對齊提案成員名單（[@Kuonaiwei1126](https://github.com/Kuonaiwei1126)、[@ChengLiangHsu](https://github.com/ChengLiangHsu)）與分工。
- [ ] **Proposal PPT 製作**
  - [ ] 依 [REQUIREMENT.md:L172](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/REQUIREMENT.md#L172) 製作提案簡報（動機、文獻、Research Gap、架構圖、Flowchart、Pseudocode、原型展示）。

---

## 階段二：核心系統與演算法實作 (Phase 2: Core System Implementation)

### 1. 資料處理模組 (`data/` 與 `src/uav_trial_assessor/adapter/analysis/`)
- [ ] **真實試驗資料去識別化**：整理 4RL (水稻捲葉蟲) 與 Concil (水田雜草) 之正射影像、小區 GeoJSON 與調查表。
- [ ] **座標與幾何對齊模組** (`src/uav_trial_assessor/adapter/analysis/geo_align.py`)：
  - [ ] 讀取 GeoTIFF 正射影像與 GeoJSON 小區邊界，對齊座標參考系統 (CRS)。
  - [ ] 檢查地面解析度 $\text{GSD} \le 1\text{ cm/px}$，不符合則發出警示。
- [ ] **小區切割與邊緣校正** (`src/uav_trial_assessor/adapter/analysis/plot_segmentation.py`)：
  - [ ] 實現依小區多邊形裁切 GeoTIFF 並保留 $1\text{ m}$ 外緣緩衝區 (`rectify`)。

### 2. 確定性影像分析引擎 (`src/uav_trial_assessor/adapter/analysis/`)
- [ ] **干擾遮罩產生器** (`src/uav_trial_assessor/adapter/analysis/interference_mask.py`)：
  - [ ] 建立青苔、水面反光、深色陰影與鄰區飄移遮罩。
- [ ] **植生與特徵指標計算** (`src/uav_trial_assessor/adapter/analysis/vegetation_indices.py`)：
  - [ ] 實作 ExG, VARI, NDRE 與亮度分離演算法。
- [ ] **目標物分割與計數** (`src/uav_trial_assessor/adapter/analysis/rasterio_analysis_engine.py`)：
  - [ ] 串接 SAM 2.1 zero-shot 分割推論。
  - [ ] 兩方向模板比對計數（針對育苗箱/特定受害特徵）。
- [ ] **領域藥效計算規則** (`src/uav_trial_assessor/entity/assessment.py`)：
  - [ ] 實作 Abbott 與 Henderson-Tilton 防治率公式。
- [ ] **統計分析 adapter** (`src/uav_trial_assessor/adapter/analysis/statistics.py`)：
  - [ ] 實作單因子/雙因子 ANOVA、Tukey HSD 事後檢定與變異係數 (CV) 檢核。

### 3. 領域知識庫與 RAG 模組 (`knowledge_base/`)
- [ ] 整理 TACTRI 登記試驗規範、EPPO 判定門檻為結構化 Markdown/JSON。
- [ ] 建立 `src/uav_trial_assessor/adapter/knowledge/vector_retriever.py`（向量檢索或規則檢索），實作 usecase 所需的知識檢索 port。

### 4. 智慧代理人與決策引擎 (`src/uav_trial_assessor/usecase/` 與 `src/uav_trial_assessor/adapter/agent/`)
- [ ] **Planner Agent 整合真實工具** (`src/uav_trial_assessor/usecase/run_agent.py`、`src/uav_trial_assessor/adapter/agent/pydantic_ai_agent.py`)：
  - [ ] 將 Phase 1 之 Mock 工具替換為真實影像分析工具與 RAG 檢索器。
  - [ ] 解析自然語言查詢與試驗設計參數，決定工具呼叫順序 (Tool Calling)。
- [ ] **例外處理與審查邏輯**：
  - [ ] 在 `src/uav_trial_assessor/entity/assessment.py` 實作「UTC 對照組壓力檢核」：壓力不足立即中止並回報試驗無效。
  - [ ] 在 `src/uav_trial_assessor/entity/assessment.py` 實作「CV 變異門檻檢核」：變異過大時標記警告。
- [ ] **證據鏈驗證機制** (`src/uav_trial_assessor/usecase/verify_evidence.py`)：
  - [ ] 檢查每項候選結論是否皆具備對應之小區 ROI 影像、指標數據與法規條文。
- [ ] **報告生成器** (`src/uav_trial_assessor/usecase/generate_report.py`、`src/uav_trial_assessor/adapter/report/docx_renderer.py`)：
  - [ ] 自動彙整推論結果、圖表與統計值，產出 Markdown/DOCX 試驗報告草稿。

### 5. 資訊安全與資料可信防護模組 (InfoSec & Trustworthy AI)
> 契合「人工智慧與資訊安全」課程主軸之安全機制與可信 AI 實作
- [ ] **試驗資料去識別化與營業秘密保護**：
  - [ ] 實作座標模糊化/平移與敏感代碼（未上市藥劑編號、試驗地敏感 GPS）脫敏保護腳本。
  - [ ] 確保公開於 GitHub 或測試環境之資料集不洩漏機敏商業資訊。
- [ ] **影像資料完整性與防偽校驗 (Data Integrity)**：
  - [ ] 實作 GeoTIFF 原始正射影像與標註檔之雜湊簽章 (SHA-256) 檢驗，防止數據被非授權竄改或污染。
- [ ] **模型對抗防禦與幻覺攔截 (Security & Anti-Hallucination)**：
  - [ ] 防禦 Prompt Injection（惡意偽造試驗指令）與異常影像輸入檢測。
  - [ ] 強制執行「可審查證據鏈繫結」：無對應影像 ROI 與公式數據之結論強制拒絕輸出，確保報告具備不可否認性 (Non-repudiation) 與真實性。

---

## 階段三：實驗驗證與基準對照 (Phase 3: Experiments & Benchmarking)

- [ ] **Case Study 1 驗證 (4RL 資料集)**：
  - [ ] 計算小區影像指標與人工捲葉率調查值之 Pearson $r$ 與 Spearman $\rho$。
  - [ ] 評估各處理藥效排序一致性 (Kendall $\tau$)。
- [ ] **Case Study 2 驗證 (Concil 資料集)**：
  - [ ] 評估青苔干擾排除前後之雜草覆蓋度評估準確率。
- [ ] **Baseline 對照實驗**：
  - [ ] 人工評分基準對照。
  - [ ] 單一植生指標 (VARI) 對照。
  - [ ] 通用多模態模型 (GPT-4o / Gemini zero-shot) 直接讀圖對照。
- [ ] **Agent 輸出品質評分**：
  - [ ] 依據 Grounding, Specificity, Plausibility, Non-Hallucination, Actionability 進行專家評分。

---

## 階段四：期末交付標準整備 (Phase 4: Final Handover Package)

- [ ] **程式碼驗收**：
  - [ ] 確保環境設定腳本 (`requirements.txt` / `environment.yml`) 完整可執行。
  - [ ] 單元測試與範例執行腳本 (How to Run 驗證)。
- [ ] **文件齊備**：
  - [ ] 更新 [README.md](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/README.md)：專題介紹、Installation 指南、How to Run 步驟、Demo 展示。
  - [ ] 完善 `DESIGN.md`：依規範撰寫 Problem、Requirements、Architecture、Components、Data Flow、AI Model、Domain Knowledge、Algorithm、Implementation Mapping、Results、Limitations。
- [ ] **影音與簡報交付**：
  - [ ] Final PPT（大於 20 頁）。
  - [ ] Final Video（上傳 YouTube，片長大於 10 分鐘之報告與 Demo 影片）。
