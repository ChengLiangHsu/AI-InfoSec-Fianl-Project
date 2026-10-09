# 3. Related Work 相關研究

### 3.1 AI Technology
* **農業 VLM 與 Agent (2025–2026)**：  
  * AgroBench [1] 由農藝專家標註，涵蓋 203 作物、682 病害，發現 VLM 在細粒度辨識仍弱、開源模型雜草辨識近乎隨機。
  * AgroMind [4] 建立 13 類農業遙測任務（27,247 QA），指出 LMM 在空間感知與場景推理上仍有落差。
  * AgroOmni [5] 進一步指出 MLLM 的 ground-level bias：缺少 UAV / 衛星尺度訓練資料時，模型會把農田影像誤讀成牆或地板。
  * AgriDoctor [2] 提出 router $\rightarrow$ 分類器 $\rightarrow$ 病斑偵測 $\rightarrow$ 知識檢索 $\rightarrow$ LLM 的 agent pipeline，並建 AgriMM benchmark（40 萬張影像、831 條專家知識）。
  * UAV 雜草 VLM 研究 [3] 以 6 個商用 VLM zero-shot 偵測大豆田雜草，提出 Error-Probing Prompting 與五項可解釋性評分（Grounding, Specificity, Plausibility, Non-Hallucination, Actionability）——本組直接沿用作為 agent 輸出評分。
* **分割與偵測模型**：  
  * SAM 2.1 可對 UAV RGB 做 label-free 個體分割，但會把雜草與土壤一併切出，需後處理 [7]；Bonn 團隊以 SAM 做 zero-shot 作物/雜草分割，將雜草視為異常 [20]。
  * 改良 YOLOv11-seg 在大豆田雜草分割並產生變量噴藥處方圖 [6]。
  * 輕量 Transformer-CNN 混合模型用於多光譜 UAV 作物/雜草分割 [9]。
  * WeedsGalore [8] 提供玉米田多光譜、多時相 UAV 分割資料集（RGB + Red-Edge + NIR）。
* **UAV 植生指標與小區分析**：  
  * 小區切割長期依賴人工參數化；邊緣偵測 + Hough 線偵測是半自動方案 [21]。
  * 本組既有方法：ExG-brightness 判別式分離育苗箱與雜草、兩方向模板比對 +計數、ROI 排除雜草干擾、VARI vs. 亮度類指標（Luma, $L^*$, HSV-V）比較、NDRE 區分青苔與雜草。

### 3.2 Domain Know-how
* **藥效試驗設計與評分**：  
  * EPPO PP 1/152(4) 規範藥效試驗的設計與分析，要求以 CV 檢核試驗變異；Bayer 歷史試驗（2016–2019 共 4,937 場）顯示 CV 範圍依作物/目標/評估方式而異 [18]。
  * 目測評分的主觀性有量化證據：NTEP 草皮評分研究以潛在尺度模型估計評分者嚴格度與場內空間變異，並建議多評分者 [12]。
  * 台灣登記試驗依 TACTRI 準則執行，報告需呈現處理、重複、調查時點、防治率與統計檢定（本組熟悉；準則條文納入 RAG）。
* **UAV 藥效 / 藥害評估**：  
  * 多光譜 UAV（$\text{GSD } 1.2\text{ cm}$）對蠶豆除草劑藥害的評估比人工目測更精確 [14]；UAV 可評估大豆萌前除草劑藥害 [13]。
  * 昆士蘭 DPI 以 UAV RGB + 多光譜評估水生雜草與甘蔗除草劑藥效，分區 zonal statistics 後做 Fisher LSD（$\alpha = 0.05$）[15]。這些研究證實 UAV 可替代或補強目測，但皆未整合試驗設計推理或自動報告。
* **水稻害蟲與雜草遙測**：  
  * 縱捲葉蟲（*Cnaphalocrocis medinalis*）：UAV 高光譜 + XGBoost 以 8 個植生指標偵測捲葉 [11]；早期研究提出 $(R_{550} - R_{531}) / (R_{550} + R_{531})$ 等專用指標 [22]。
  * 白葉枯病：2026 年 ISPRS 以多時相、多模態 UAV + ML 做早期偵測 [10]。
  * 水田雜草：Yu et al. 2022 以 $\text{WDVI}_{\text{NIR}}$ 辨識水田雜草 [19]——本組 Concil 試驗的方法參考。

### 3.3 Article Summary Table

| Ref. | Year | Problem / AI Method | Domain Knowledge | Dataset | Findings | Limitation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **[1] AgroBench** | 2025 | 評估 VLM 農業能力 / VLM benchmark (7 主題) | 203 作物、682 病害，專家標註 | AgroBench | VLM 細粒度辨識弱；開源 VLM 雜草辨識近隨機 | 近拍影像為主，無 UAV 尺度 |
| **[2] AgriDoctor** | 2025 | 多模態病害診斷 Agent / Router + classifier + detector + RAG + LLM | 831 條專家病蟲害知識 | AgriMM (40 萬影像) | 領域適配與模組化推理顯著優於單一模型 | 單株影像；無試驗設計、無小區概念 |
| **[3] UAV weed VLM** | 2025 | UAV 雜草偵測 / 6 個商用 zero-shot VLM + Error-Probing Prompting | 大豆生育期、雜草種類 | 大豆田 UAV + GT boxes | VLM 可給出可解釋推理；EPP 可自我修正 | 僅 presence / 粗定位，無定量覆蓋度 |
| **[4] AgroMind** | 2025 | 農業遙測 LMM / 13 任務、27,247 QA benchmark | 作物辨識、健康監測、環境分析 | 8 公開 + 1 私有農田 | LMM 在空間感知與推理仍有落差 | 評測為主，未提出系統 |
| **[5] AgroOmni** | 2026 | MLLM 跨尺度農業推理 / 多視角指令微調資料集 | 地面 / UAV / 衛星三尺度 | AgroOmni | 揭露 ground-level bias（農田誤判為牆面） | 仍以辨識 / QA 為主 |
| **[6] YOLOv11-seg weed** | 2025 | 大豆田 UAV 雜草分割 / 改良 YOLOv11-seg | 變量噴藥處方圖 | 自建實田資料集 | 高精度分割 + 處方圖 | 需大量標註；跨田區泛化未驗證 |
| **[7] SAM 2.1 traits** | 2025 | UAV RGB 植株性狀抽取 / SAM 2.1 zero-shot 分割 | 木本觀賞植物性狀 | ILVO 苗圃 UAV | 無標註即可分割個體 | 會把雜草、土壤一起切出，需後處理 |
| **[8] WeedsGalore** | 2025 | 作物/雜草分割資料集 / 語意 + 實例分割 | 玉米 + 4 類雜草，多時相 | 多光譜 UAV (RGB/RE/NIR) | 公開資料集與 code | 僅玉米；非水田 |
| **[10] Rice BLB UAV** | 2026 | 水稻白葉枯病早期偵測 / 多時相多模態 UAV + ML | 病害發展與時相 | IRRI 田區 | 多時相可提早偵測 | 病害非害蟲；未做藥效 |
| **[11] Leaf folder UAV** | 2024 | 水稻縱捲葉蟲偵測 / XGBoost, 8 個 VI | 捲葉率調查，222 小區 | UAV 高光譜 | 8-VI XGBoost 可靠偵測捲葉 | 高光譜成本高；非 RGB |
| **[12] NTEP rating** | 2023 | 目測評分主觀性 / Bayesian 潛在尺度模型 (Stan) | 評分者嚴格度、空間變異 | 2017 NTEP 7 地點 | 可估計並校正評分者偏差 | 需多評分者與評分者 ID |
| **[14] UAV vs manual** | 2020 | 除草劑藥害評估 / 多光譜 VI (OSAVI) | 蠶豆 9 種除草劑 | GSD 1.2 cm | UAV 比目測更精確一致 | 單一時點、單一指標 |
| **[15] DPI UAV efficacy** | 2025 | UAV 除草劑藥效評估 / zonal statistics + Fisher LSD | 甘蔗 / 水生雜草 | RGB + 多光譜，多次飛行 | UAV 可追蹤處理效果隨時間變化 | 無自動化、無報告生成 |
| **[18] Bayer / EPPO** | 2019 | 藥效試驗統計檢核 / CV 計算 (Scout 系統) | EPPO PP 1/152(4) | 4,937 場 Bayer 試驗 | CV 範圍依作物/目標/評估方式而異 | 內部系統，不處理影像 |

### 3.4 Existing Research $\rightarrow$ Limitations $\rightarrow$ Research Gap $\rightarrow$ Our Project
* **Existing Research**: UAV 影像可比目測更精確地評估藥效/藥害 [13, 14, 15]；SAM / YOLO-seg 可分割雜草與植株 [6, 7, 20]；農業 VLM 與 agent 架構已出現 [1, 2, 3]。
* **Limitations**: 影像研究停在指標與相關分析，不處理試驗設計與規範；分割模型需標註且不可解釋；VLM 對 UAV 尺度與雜草辨識仍弱，且不懂試驗結構；agent 研究集中於單株病害診斷。
* **Research Gap**: 沒有一個系統同時做到「讀懂試驗設計 $\rightarrow$ 從 $< 1\text{ cm}$ GSD 影像抽取小區級證據 $\rightarrow$ 依藥效規範推理 $\rightarrow$ 輸出可追溯結論」。
* **Our Project**: UAV Field-Trial Assessor Agent，以工具化的影像分析鏈 + 規範知識庫 + LLM 推理，填補上述缺口，並以兩個真實試驗驗證。
