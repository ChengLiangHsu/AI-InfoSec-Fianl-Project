# 5. Proposed Scheme / Proposed Design

### 5.1 System Architecture

> **核心設計原則**：LLM 擔任 planner，感知與計算交給確定性工具。

#### Clean Architecture 分層

系統程式碼採用 `entity`、`usecase`、`adapter` 三層結構，依賴方向固定為：

```text
adapter → usecase → entity
```

| 層級 | 職責 | 主要內容 | 禁止事項 |
| :--- | :--- | :--- | :--- |
| **Entity** | 表達田間試驗的核心概念與不隨框架改變的領域規則 | Trial、Plot、Treatment、Evidence、Assessment、UTC / CV / 藥效判定規則 | 不得依賴 FastAPI、Pydantic AI、SQLite 或 Rasterio |
| **Usecase** | 編排使用者目標與應用流程，並定義所需的 port | 執行 Agent、匯入資料集、評估試驗、驗證證據、產生與核准報告 | 不得直接建立資料庫連線、讀取 HTTP request 或呼叫特定模型供應商 SDK |
| **Adapter** | 將外部輸入與技術細節轉換成 usecase 可使用的形式，並實作 usecase 定義的 port | FastAPI router、Pydantic AI、SQLite repository、Rasterio 分析、向量檢索、檔案儲存 | 不得自行決定 UTC、CV、藥效門檻等領域規則 |

`usecase/port/` 保存抽象 interface；`adapter/` 保存具體 implementation。`bootstrap.py` 是 composition root，負責建立 adapter 並注入 usecase。只有確實需要正式版與測試版兩種 implementation 的外部依賴才建立 port，避免產生只有轉呼叫功能的淺層模組。

```mermaid
graph LR
    HTTP[HTTP Adapter<br/>FastAPI] --> UC[Usecase<br/>應用流程與 ports]
    WORKER[Worker Adapter<br/>背景工作] --> UC
    UC --> ENTITY[Entity<br/>領域模型與規則]
    AGENT[Agent Adapter<br/>Pydantic AI] -. implements port .-> UC
    REPO[Repository Adapter<br/>SQLite] -. implements port .-> UC
    ANALYSIS[Analysis Adapter<br/>Rasterio / 統計工具] -. implements port .-> UC
    STORAGE[Storage Adapter<br/>本機檔案系統] -. implements port .-> UC
```

#### 功能架構

```mermaid
graph TD
    U["① User Scenario<br>試驗執行者飛行後上傳資料<br>詢問各處理藥效與是否達標"] --> Q["② Query / Input<br>GeoTIFF 正射影像 + GeoJSON 小區<br>Excel 處理表 + 自然語言查詢"]
    Q --> P["③ Planner & Reasoning Agent<br>LLM 解析意圖、拆解子任務<br>選擇工具、處理例外、整合證據"]
    
    P -- tool calls --> D["④ Data Acquisition<br>CRS 對齊、DAA 對齊人工調查<br>rasterio / geopandas / pandas"]
    P -- tool calls --> A["⑤ Analytics Engine<br>小區切割、干擾遮罩、指標計算<br>SAM 2.1 / YOLO-seg、ANOVA、CV"]
    P -- tool calls --> K["⑥ Domain Knowledge<br>TACTRI / EPPO 規範 RAG<br>藥效公式、藥害分級、干擾規則"]
    
    D --> DEC["⑦ Decision / Recommendation<br>試驗有效性 → 防治率 → 排序<br>是否達標、不確定性與限制"]
    A --> DEC
    K --> DEC
    
    DEC --> O["⑧ Output & Interaction<br>標註影像、比較圖表、報告草稿<br>附證據鏈，可追問"]
    O -.->|追問 / 修正| U
```

#### 各模組說明

| 模組 | 內容 | 技術選型（初步） |
| :--- | :--- | :--- |
| **① User/Application Scenario** | 試驗執行者在飛行後上傳正射影像與試驗設計，詢問「各處理對縱捲葉蟲的防治效果如何？是否達登記標準？」 | Web UI + FastAPI HTTP adapter |
| **② Query/Input** | 自然語言查詢 + GeoTIFF 正射影像（RGB/多光譜）+ GeoJSON 小區界線 + Excel 處理表與人工調查資料 | FastAPI schema；rasterio、geopandas、openpyxl adapters |
| **③ Planner & Reasoning Agent** | `run_agent` usecase 解析目標並編排流程；Pydantic AI adapter 實作模型呼叫與 tool calling，領域例外由 entity 規則判定 | Pydantic AI、LLM (Claude / GPT / 本地 Qwen2.5-VL) |
| **④ Data Acquisition / Retrieval** | 讀取影像與向量檔、對齊 CRS、以 DAA 對齊人工調查；向知識庫檢索規範條文 | rasterio / GDAL、pandas；Vector DB (Chroma / FAISS) |
| **⑤ Analytics Engine** | 小區切割與校正（外緣 buffer）、干擾遮罩（青苔/陰影/水面）、指標計算（ExG、VARI、NDRE、brightness）、分割（SAM 2.1 zero-shot $\rightarrow$ YOLO-seg 微調）、模板比對計數、統計（ANOVA / Tukey / CV） | OpenCV、NumPy、scikit-image、Ultralytics、SAM 2.1、statsmodels |
| **⑥ Domain Knowledge Integration** | 規範知識庫：TACTRI 田間試驗準則、EPPO PP 1/152(4)、藥效公式（Abbott、Henderson-Tilton、防治率）、藥害分級、作物生育期、干擾排除規則 | RAG（Markdown / PDF chunk $\rightarrow$ embedding）；規則以 Python 函式確定性執行 |
| **⑦ Decision / Recommendation** | 試驗有效性判定 $\rightarrow$ 各處理防治率與排序 $\rightarrow$ 是否達標 $\rightarrow$ 不確定性與限制說明 | LLM 整合 + 固定模板；證據鏈（ROI、數值、公式、條文） |
| **⑧ Output & Interaction** | 小區級標註影像、處理比較圖表、報告草稿（Markdown / DOCX）、可追問（「為何 T5 排第二？」） | matplotlib / folium、python-docx；對話式追問 |

#### 功能到程式層的對應

| 功能 | 所在位置 |
| :--- | :--- |
| Trial、Plot、Treatment、Evidence 與判定規則 | `src/uav_trial_assessor/entity/` |
| Agent 執行、試驗評估、證據驗證與報告流程 | `src/uav_trial_assessor/usecase/` |
| FastAPI request / response 與串流 | `src/uav_trial_assessor/adapter/http/` |
| Pydantic AI agent、prompt 與 tool adapter | `src/uav_trial_assessor/adapter/agent/` |
| SQLite、影像分析、RAG、檔案與報告輸出 | `src/uav_trial_assessor/adapter/` 下對應模組 |
| 依賴組裝與 ASGI 啟動 | `src/uav_trial_assessor/bootstrap.py`、`main.py` |

---

### 5.2 Flowchart

> **對照組壓力不足或缺少證據鏈，流程就停下來。**

```mermaid
flowchart TD
    Start(["Input: 正射影像 + 小區界線 + 處理表 + 查詢"]) --> Parse["意圖解析 + 規範檢索 (LLM + RAG)"]
    
    subgraph PlotLoop ["for each plot"]
        ProcPlot["小區切割、干擾遮罩、指標與分割"]
    end
    
    Parse --> ProcPlot
    ProcPlot --> Stat["處理彙整與統計 (mean ± SE、ANOVA、CV)"]
    
    Stat --> CondUTC{"UTC 壓力足夠？"}
    CondUTC -- No --> Invalid["試驗無效，回報原因"]
    
    CondUTC -- Yes --> GenCand["藥效公式、排序、候選結論 (LLM 生成)"]
    GenCand --> CondEvidence{"每條結論有證據鏈？"}
    
    CondEvidence -- No --> Drop["丟棄，重新生成"]
    Drop --> GenCand
    
    CondEvidence -- Yes --> Human["人工審核 (Human-in-the-loop)"]
    Human --> FinalOut(["Output: 報告草稿、標註影像、追問"])
```

* **兩個決策點**：對應 Pseudocode 第 13 行（UTC 壓力）與第 21 行（證據鏈驗證）。
* **人工審核**：在輸出前保留 Human-in-the-loop，符合登記試驗的責任歸屬。

---

### 5.3 Pseudocode

```python
Algorithm 1: 無人機田間試驗評估智慧代理人
Input:  User query Q, orthomosaic I (GeoTIFF), plot boundaries P (GeoJSON),
        trial design D (treatments, blocks, DAA), optional ground truth G
Output: Efficacy assessment report R with evidence chain E

01: Receive Q, I, P, D, (G)
02: intent = LLM.parse_intent(Q)                // target: weed | insect | disease; metric asked
03: type = D.trial_type; design = D.layout      // e.g., RCBD, 8 trt × 3 rep
04: rules = KB.retrieve(type, intent)           // TACTRI/EPPO clauses, efficacy formula, CV threshold
05: I, P = align_crs(I, P); check GSD <= 1 cm else warn

06: for each plot p in P:
07:     tile_p = rectify(I, p, buffer = 1 m)
08:     mask_p = interference_mask(tile_p)      // algae/shadow/water; NDRE cross-check if available
09:     seg_p  = segment(tile_p, mask_p, intent)// SAM 2.1 zero-shot -> YOLO-seg if trained
10:     f_p    = features(tile_p, seg_p)        // coverage %, ExG, VARI, NDRE, count, damage ratio
11: end for

12: F = aggregate(f_p by D.treatment, D.block)  // mean ± SE per treatment; block effect
13: if F[UTC].pressure < rules.min_pressure then
14:     return R = "Trial invalid: insufficient pressure in UTC", E
15: end if

16: eff = rules.formula(F, UTC)                 // Abbott / Henderson-Tilton / control %
17: stats = ANOVA(F); posthoc = Tukey(F); cv = CV(F)
18: if cv > rules.max_cv then flag "high variability"
19: if G exists then corr = correlate(F, G by plot, DAA) // r, p, Kendall tau
20: rank = order treatments by eff with posthoc letters

21: cand = LLM.generate_candidates(rank, stats, rules)   // conclusions per treatment
22: for each c in cand: verify(c, E)                     // every claim must cite ROI / value / clause
23: unc = uncertainty(single DAA, mask coverage, segmentation confidence, cv)
24: R = LLM.compose_report(cand, unc, rules.report_template)
25: present(R, annotated_map(I, P, F), charts, E)
26: return R
```

#### 設計重點
* **第 02, 21, 24 行**：是 LLM 的工作（理解、整合、表達）；第 05–20 行全部是確定性工具，LLM 不得自行估算數值。
* **第 13–14 行**：把「對照組決定一切」的思維寫進流程：UTC 壓力不足即停止。
* **第 22 行**：幻覺攔截機制：沒有證據鏈的候選結論會被直接丟棄。
* **第 19 行**：只有在有人工調查資料時執行；proposal 階段以 4RL 的捲葉率作 ground truth。

---

### 5.4 Technical Feasibility

| 項目 | 現況 | 風險 / 對策 |
| :--- | :--- | :--- |
| **資料** | 4RL、Concil、FHB 正射影像與 ground truth 已在手（$\text{GSD } 0.85 \sim 0.9\text{ cm}$） | 資料來源為公司試驗，需去識別化後放 GitHub；或只公開小區級指標 |
| **影像方法** | 小區切割、模板比對、ExG-brightness、ROI 排除已驗證（育苗箱計數 233 vs. 人工） | 捲葉/白穗在 RGB 的可辨識度未知 $\rightarrow$ 先以 42 DAA 影像做可行性評估 |
| **分割模型** | SAM 2.1 zero-shot 可立即使用；YOLO-seg 需標註 | 標註量控制在 24 小區 $\times$ 2 時點，以 SAM 預標註加速 |
| **LLM / Agent** | 本地 RTX 3060 12 GB 可跑 Qwen2.5-VL 7B / 8B；雲端 API 作對照 | 本地模型推理能力不足 $\rightarrow$ planner 用 API，工具保持本地運行 |
| **統計** | statsmodels ANOVA / Tukey 成熟 | 3 重複檢定力低 $\rightarrow$ 報告中明示限制與不確定性 |
| **時程** | 10 月 proposal $\rightarrow$ 11 月工具鏈 $\rightarrow$ 12 月 agent 整合與實驗 $\rightarrow$ 1 月 handover | 兩人分工明確（見第 6 節） |
