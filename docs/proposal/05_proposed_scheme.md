# 5. Proposed Scheme / Proposed Design

> **第一版目標**：先完成農藥試驗的影像指標比較流程，以畫布著色與數值比較表呈現結果，流程跑通後才開始實作收穫分析。
> **後續範圍**：AI 結果摘要、報告生成與匯出延後，人工調查、正式藥效百分比及法定效力判定另行確認。

### 5.1 System Architecture

#### 系統分層架構

- **介面層**：使用 [Vue.js](https://vuejs.org/) 與 [Canvas API](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API) 操作影像，透過 [FastAPI](https://fastapi.tiangolo.com/) 傳遞小區與分析設定。
- **AI 協調層**：使用 [Pydantic AI](https://ai.pydantic.dev/tools/) 推薦可用指標並說明理由，使用者可修改，明確確認後才啟動分析。
- **確定性運算層**：使用 [NodeODM](https://github.com/OpenDroneMap/NodeODM) 合併照片，以 [NumPy](https://numpy.org/doc/stable/)、[Rasterio](https://rasterio.readthedocs.io/en/stable/) 與 [rasterstats](https://pythonhosted.org/rasterstats/) 完成網格、指標及分區比較。
- **儲存層**：以 [SQLite](https://www.sqlite.org/docs.html) 保存小區、處理設定與計算結果，影像另外存為檔案。

```mermaid
graph TD
    UI["① 操作介面<br/>上傳 / 網格 / 處理套用 / 指標確認"]
    ODM["② 影像合併<br/>NodeODM"]
    GRID["③ 小區與處理管理<br/>試驗田範圍 / 行列數 / 農藥與劑量 / 對照組"]
    AI["④ AI 指標推薦<br/>RGB 指標與選擇理由"]
    CONFIRM{"使用者確認指標？"}
    ANALYSIS["⑤ 指標計算與比較<br/>各小區 / 各處理組 / 對照組差異"]
    STORE["⑥ 儲存<br/>SQLite / 影像檔案"]
    VIEW["⑦ 結果畫面<br/>畫布著色 / 數值比較表"]
    UI --> ODM
    ODM --> GRID
    UI --> GRID
    GRID --> AI
    AI --> CONFIRM
    CONFIRM -- 修改或等待 --> UI
    CONFIRM -- 確認 --> ANALYSIS
    ODM --> STORE
    GRID --> STORE
    ANALYSIS --> STORE
    ANALYSIS --> VIEW
    STORE --> VIEW
```

#### 各模組職責

| 模組 | 第一版責任 | 參考 |
| :--- | :--- | :--- |
| **① 操作介面** | 接收多張 RGB 照片，提供網格設定、處理套用與指標確認操作 | [Vue.js](https://vuejs.org/)、[Canvas](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API) |
| **② 影像合併** | 將照片交給 NodeODM 拼接，取得正射影像後進入小區設定 | [NodeODM API](https://github.com/OpenDroneMap/NodeODM)、[ODM 輸出](https://docs.opendronemap.org/outputs/) |
| **③ 小區與處理管理** | 依試驗田範圍及行列數生成網格，允許微調，再以點選方式套用農藥與劑量或未施藥對照 | [等距分點](https://numpy.org/doc/stable/reference/generated/numpy.linspace.html)、[點選範圍判斷](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/isPointInPath) |
| **④ AI 指標推薦** | 依使用者從選單指定的評估目的，推薦 RGB 可計算的指標與理由，使用者可修改後確認 | [Pydantic AI 工具](https://ai.pydantic.dev/tools/)、[VARI](https://step.esa.int/main/wp-content/help/versions/13.0.0/snap-toolboxes/eu.esa.opt.opttbx.radiometric.indices.ui/vari/VariAlgorithmSpecification.html)、[ExG 文獻](https://elibrary.asabe.org/abstract.asp?aid=27838) |
| **⑤ 指標計算與比較** | 計算各小區指標，依「農藥＋劑量」分組並計算重複小區平均值（典型為 3 重複），並比較明確指定對照組的指標差異 | [Rasterio](https://rasterio.readthedocs.io/en/stable/)、[分區統計](https://pythonhosted.org/rasterstats/) |
| **⑥ 儲存** | 保存網格、小區處理設定、確認的指標及計算結果，保留小區編號與數值來源 | [SQLite](https://www.sqlite.org/docs.html) |
| **⑦ 結果畫面** | 在同一結果頁提供依指標數值著色的畫布及數值比較表 | [Canvas](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API) |

#### 操作規則

- **輸入規格**：上傳多張 RGB 空拍照片，格式限定為 JPG、PNG 或 JPEG，GSD < 1 cm/px 作為由使用者確認的資料準備規範，第一版不以系統自動檢核 GSD 作為拒絕分析的條件（[GSD 定義](https://en.wikipedia.org/wiki/Ground_sample_distance)）。
- **網格切割**：使用者框出試驗田並輸入行列數，系統生成小區網格後允許手動微調與確認。
- **處理套用**：先選好農藥與施用劑量，再依序點選不同小區套用，以「農藥＋劑量」區分處理組；系統彈性支援多小區重複（建議與典型為 3 重複配置）。
- **未施藥對照**：對照組與處理組採用相同的小區規劃及點選套用方式，以 CK 或 UTC 明確標記未施藥對照且不填農藥與劑量，空白僅代表尚未設定。
- **指標確認**：使用者從選單指定評估目的（例如殺蟲劑或除草劑），AI 顯示推薦指標與理由，使用者可修改，明確確認後才計算。
- **比較依據**：第一版僅比較 RGB 影像指標，例如 [VARI](https://step.esa.int/main/wp-content/help/versions/13.0.0/snap-toolboxes/eu.esa.opt.opttbx.radiometric.indices.ui/vari/VariAlgorithmSpecification.html) 與 [ExG](https://elibrary.asabe.org/abstract.asp?aid=27838)，原列 NDRE 移出本階段範圍。
- **結果內容**：比較表列出各小區編號、農藥、劑量、對照狀態及指標數值（保留完整明細），並提供各處理組去平均計算之平均值（Treatment Mean）與對照組差異，畫布顏色代表指標數值高低。
- **差異核對**：採雙軌解讀機制。相同農藥與劑量的小區出現明顯指標差異時，總體表現以 3 重複平均值為基準以平抑田間自然變異，同時保留各小區原始結果，由使用者回看影像與設定以釐清局部干擾原因，不擅自剔除異常小區（[NIST 異常觀測處理原則](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm)；[田間試驗設計指南](https://extension.umn.edu/courses-and-events/for-professionals/on-farm-research/how-to-do-research-on-your-farm)）。

#### 功能與程式模組對應

以下是依現有目錄安排的責任規劃，不表示各功能已完成實作。

| 功能 | 模組位置 | 規劃責任 |
| :--- | :--- | :--- |
| 應用程式入口 | `src/main.py` | 僅建立應用程式、管理生命週期與掛載控制器 |
| 上傳與拼接任務 | `src/controllers/odm.py`、`src/utility/nodeodm.py` | 分別處理請求與 NodeODM 任務協調 |
| AI 指標推薦 | `src/agents/pydantic_agent.py` | 推薦指標、提供理由與來源，遵守使用者確認流程 |
| 網格與處理對應 | `src/utility/plots.py`（規劃新增） | 生成小區座標與維護小區處理對應所需的純運算 |
| 指標與影像運算 | `src/utility/formulas.py`、`src/utility/spectral.py` | 管理公式及執行影像指標運算，擴充分區統計與處理組比較 |
| 資料存取 | `src/database.py` | 集中保存任務、小區、處理設定與分析結果 |
| 前端畫面 | `frontend/src/` | 提供網格與點選操作、指標確認、畫布著色及比較表 |

---

### 5.2 Flowchart

```mermaid
flowchart TD
    INPUT["輸入：多張 RGB 空拍照片<br/>JPG / PNG / JPEG，使用者確認 GSD 規範"] --> S1["① 合併影像"]
    S1 --> READY{"拼接成功？"}
    READY -- 否 --> ERROR["顯示任務錯誤並保留重新處理入口"]
    READY -- 是 --> S2["② 切割小區<br/>框試驗田 → 輸入行列數 → 生成網格 → 手動微調確認"]
    S2 --> ASSIGN["先選農藥與劑量，或選未施藥對照<br/>再點選不同小區套用，空白維持未設定"]
    ASSIGN --> PURPOSE["選單指定評估目的"]
    PURPOSE --> S3["③ AI 推薦 RGB 指標並說明理由"]
    S3 --> EDIT["使用者檢視並可修改指標"]
    EDIT --> CONFIRM{"確認開始分析？"}
    CONFIRM -- 尚未確認 / 修改 --> EDIT
    CONFIRM -- 確認 --> CHECK["檢查分析設定與小區資料"]
    CHECK --> VALID{"資料可計算？"}
    VALID -- 否 --> FIX["提示需補充或修正的設定"]
    FIX --> ASSIGN
    VALID -- 是 --> EACH["逐一處理各分析小區"]
    EACH --> METRICS["裁切影像、排除無效像素並計算確認的指標"]
    METRICS --> MORE{"仍有小區？"}
    MORE -- 是 --> EACH
    MORE -- 否 --> COMPARE["④ 比較小區與處理組<br/>依農藥＋劑量彙整（計算重複平均），計算對照差異"]
    COMPARE --> SAVE["保存小區與比較數值"]
    SAVE --> VIEW["⑤ 結果畫面<br/>畫布著色＋數值比較表"]
```

- **人工確認**：指標推薦與指標計算之間保留明確確認點，未確認時不執行小區分析。
- **資料區分**：未設定小區與未施藥對照分開記錄，缺少必要資料時顯示待補充原因，不自動補成對照組或捏造數值。
- **數值來源**：畫布與比較表使用同一批計算結果，保留小區編號、處理設定及指標名稱以便核對。

---

### 5.3 Pseudocode

```text
Algorithm 1: RGB 空拍小區指標比較
Input : RGB photos H, trial boundary B, grid dimensions G,
        treatment options T (pesticide, dose), explicit control option UTC,
        assessment purpose S
Output: Colored plot canvas V, plot and treatment comparison tables C

01: I = stitch_rgb_photos(H)
02: P = generate_plot_grid(B, G)
03: P = edit_and_confirm_grid(I, P)
04: D = assign_treatments_by_click(P, T, UTC)
05: K = get_supported_rgb_indices_with_references()
06: A = Agent.recommend_indices(S, K)
07: J = wait_for_user_index_confirmation(A)  // 顯示指標與理由，允許修改
08: validate_analysis_inputs(I, P, D, J)
09: F = calculate_plot_metrics(I, P, J)
10: C = compare_plot_and_treatment_metrics(F, D)  // 依處理組計算重複平均值，保留小區明細
11: save_analysis_results(P, D, J, F, C)
12: V = build_plot_color_overlay(P, F, J)
13: present_comparison_view(V, F, C)
14: return V, C
```

- **主流程**：只協調子函式，各自負責拼接、網格、處理指定、AI 推薦、人工確認、計算、存取或呈現。
- **第 04 行**：使用者選取「農藥＋劑量」或「未施藥對照」後點選小區，保留未設定狀態。
- **第 06–08 行**：AI 推薦範圍限於可用的 RGB 指標，取得使用者明確確認後才驗證分析輸入並進入計算。
- **第 09 行**：子流程再分成影像裁切、有效像素遮罩、指標矩陣計算及小區統計等單一職責函式，實作依據為 [Rasterio](https://rasterio.readthedocs.io/en/stable/) 與 [分區統計文件](https://pythonhosted.org/rasterstats/)。
- **第 10–13 行**：依農藥與劑量彙整小區指標（計算重複平均值，典型為 3 重複）、比較明確指定對照組並呈現畫布與表格，AI 不生成比較摘要或報告。

---

### 5.4 Technical Feasibility

| 項目 | 可行性依據 | 待驗證事項 |
| :--- | :--- | :--- |
| **影像輸入與合併** | 已有多張 RGB 空拍照片，可透過 [NodeODM](https://github.com/OpenDroneMap/NodeODM) 產生 [正射影像](https://docs.opendronemap.org/outputs/) | 以實際照片確認 GPS 資訊、拼接成功率與處理時間 |
| **網格與點選操作** | [Canvas](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API) 與 [等距座標](https://numpy.org/doc/stable/reference/generated/numpy.linspace.html) 可作為畫布及網格的實作基礎 | 驗證網格微調、農藥與劑量套用、未施藥對照及空白狀態 |
| **AI 指標推薦** | [Pydantic AI](https://ai.pydantic.dev/tools/) 可連接指標查詢工具，搭配固定的公式與參考來源 | 驗證推薦可計算、理由有來源、使用者修改及確認流程 |
| **指標與比較運算** | [VARI](https://step.esa.int/main/wp-content/help/versions/13.0.0/snap-toolboxes/eu.esa.opt.opttbx.radiometric.indices.ui/vari/VariAlgorithmSpecification.html)、[ExG](https://elibrary.asabe.org/abstract.asp?aid=27838) 與 [分區統計](https://pythonhosted.org/rasterstats/) 提供公式及計算依據 | 以實際影像核對小區數值、有效像素與對照差異，量測執行時間 |
| **結果保存與呈現** | [SQLite](https://www.sqlite.org/docs.html) 保存結果，由前端共用同一批數值呈現畫布及表格 | 核對小區編號、處理組、著色圖例與表格數值一致 |

- **第一版完成條件**：使用實際照片走完「合併 → 網格切割與處理套用 → AI 推薦並人工確認 → 指標比較 → 畫布與表格」流程。
- **後續擴充順序**：AI 摘要與報告延後，收穫分析須等農藥影像比較流程完整跑通後才開始，人工調查與正式藥效判定另行討論。
- **完整參考**：工具、公式及背景資料集中於根目錄 [REFERENCE.md](../../REFERENCE.md)。
