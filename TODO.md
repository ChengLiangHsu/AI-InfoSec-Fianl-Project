# 專案實作待辦事項清單 (Project TODO)

> 依據 [REQUIREMENT.md](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/REQUIREMENT.md) 與 [docs/06_execution_plan.md](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/docs/06_execution_plan.md) 解析之具體實作任務。

---

## 階段一：Proposal 與文件整備 (Phase 1: Proposal & Docs)

- [ ] **文獻補正與驗證**
  - [ ] 補齊 [docs/07_references.md](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/docs/07_references.md) 中標記 `※` 的 9 篇文獻完整作者、出處與年份（如 Ref [3, 5, 6, 7, 9, 11, 14, 15, 17, 19, 21, 22]）。
  - [ ] 取得 TACTRI 水稻害蟲/雜草試驗準則與 EPPO PP 1/152(4) 原始文字檔備用。
- [ ] **建立專案規格書初稿**
  - [ ] 依 [REQUIREMENT.md:L190-191](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/REQUIREMENT.md#L190-191) 建立根目錄 `DESIGN.md`，設定核心說明路徑架構骨架。
- [ ] **修正專案導引文件**
  - [ ] 修正 [README.md:L29](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/README.md#L29) 連結至 `docs/07_references.md`（原 `REFERENCE.md` 斷鏈）。
  - [ ] 對齊提案成員名單（郭乃瑋、許承諒）與分工。
- [ ] **Proposal PPT 製作**
  - [ ] 依 [REQUIREMENT.md:L172](file:///c:/Users/2024h/Downloads/AI-InfoSec-Fianl-Project/REQUIREMENT.md#L172) 製作提案簡報（動機、文獻、Research Gap、架構圖、Flowchart、Pseudocode）。

---

## 階段二：核心系統與演算法實作 (Phase 2: Core System Implementation)

### 1. 資料處理模組 (`data/` & `tools/`)
- [ ] **真實試驗資料去識別化**：整理 4RL (水稻捲葉蟲) 與 Concil (水田雜草) 之正射影像、小區 GeoJSON 與調查表。
- [ ] **座標與幾何對齊模組** (`tools/geo_align.py`)：
  - [ ] 讀取 GeoTIFF 正射影像與 GeoJSON 小區邊界，對齊座標參考系統 (CRS)。
  - [ ] 檢查地面解析度 $\text{GSD} \le 1\text{ cm/px}$，不符合則發出警示。
- [ ] **小區切割與邊緣校正** (`tools/plot_segmentation.py`)：
  - [ ] 實現依小區多邊形裁切 GeoTIFF 並保留 $1\text{ m}$ 外緣緩衝區 (`rectify`)。

### 2. 確定性影像分析引擎 (`tools/`)
- [ ] **干擾遮罩產生器** (`tools/interference_mask.py`)：
  - [ ] 建立青苔、水面反光、深色陰影與鄰區飄移遮罩。
- [ ] **植生與特徵指標計算** (`tools/indices.py`)：
  - [ ] 實作 ExG, VARI, NDRE 與亮度分離演算法。
- [ ] **目標物分割與計數** (`tools/segment_sam.py` & `tools/count_template.py`)：
  - [ ] 串接 SAM 2.1 zero-shot 分割推論。
  - [ ] 兩方向模板比對計數（針對育苗箱/特定受害特徵）。
- [ ] **統計與藥效計算工具** (`tools/stats.py`)：
  - [ ] 實作 Abbott 與 Henderson-Tilton 防治率公式。
  - [ ] 實作單因子/雙因子 ANOVA、Tukey HSD 事後檢定與變異係數 (CV) 檢核。

### 3. 領域知識庫與 RAG 模組 (`knowledge_base/`)
- [ ] 整理 TACTRI 登記試驗規範、EPPO 判定門檻為結構化 Markdown/JSON。
- [ ] 建立檢索器（向量檢索或基於規則的條文檢索），供 Agent 查詢法規依據。

### 4. 智慧代理人與決策引擎 (`agent/`)
- [ ] **Planner Agent** (`agent/planner.py`)：
  - [ ] 解析自然語言查詢與試驗設計參數，決定工具呼叫順序 (Tool Calling)。
- [ ] **例外處理與審查邏輯**：
  - [ ] 實作「UTC 對照組壓力檢核」：壓力不足立即中止並回報試驗無效。
  - [ ] 實作「CV 變異門檻檢核」：變異過大時標記警告。
- [ ] **證據鏈驗證機制** (`agent/evidence.py`)：
  - [ ] 檢查每項候選結論是否皆具備對應之小區 ROI 影像、指標數據與法規條文。
- [ ] **報告生成器** (`agent/report.py`)：
  - [ ] 自動彙整推論結果、圖表與統計值，產出 Markdown/DOCX 試驗報告草稿。

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
