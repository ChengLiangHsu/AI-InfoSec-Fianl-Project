# 1. Abstract 摘要

* **A. Attention Getter (Motivation)**  
  農業無人機已從「噴藥工具」轉為「資料來源」：IMARC 估計全球農業無人機市場 2024 年約 USD 27 億，2025–2033 年 CAGR 約 28% [16]；美國 USDA ERS 統計 2025 年噴藥無人機處理面積達 1,640 萬英畝，一年成長約 60% [17]。另一方面，2025 年起農業多模態 AI 快速成形：ICCV 2025 的 AgroBench [1]、AgroMind [4]、AgroOmni (2026) [5] 先後建立農業 VLM 基準，AgriDoctor [2] 則首度以 agent 架構串接病害分類、病斑偵測與知識檢索。高解析度（$\text{GSD} < 1\text{ cm}$）UAV 正射影像與可推理的 VLM/LLM，正處於交會點。

* **B. But (Challenge)**  
  作物保護產品的田間藥效試驗（Bayer 全球每年約 2 萬場 [18]）至今仍以人工目測評分為主：評分受評分者嚴格程度、疲勞與偏好影響，同一小區不同人可差數個等級 [12]；UAV 影像雖被證實比人工評分更精確、更穩定 [13, 14, 15]，但現有研究多停在「算一個植生指標、做一次相關分析」，缺少與試驗設計（RCBD、處理代碼、調查時點）、藥效公式（Abbott、Henderson-Tilton、防治率）與登記規範（TACTRI / EPPO PP 1/152）的整合。AgroBench 更指出，多數開源 VLM 在雜草辨識上接近隨機 [1]；AgroOmni 指出 MLLM 對 UAV 尺度影像有嚴重的 ground-level bias，甚至把農田誤判為牆面或地板 [5]。  
  **Research gap**：缺少一個能讀懂試驗設計、從高解析度 UAV 影像抽取小區級證據、再依領域規則推理出藥效結論的 Domain AI Agent。

* **C. Cure (Proposed Solution)**  
  為了解決上述問題，本專題提出 **UAV Field-Trial Assessor Agent**：一個以高解析度 UAV 正射影像為輸入、以作物保護試驗領域知識為推理依據的田間試驗評估智慧代理人。

* **D. Development (Method)**  
  系統由 Planner Agent 解析使用者查詢與試驗設計檔（GeoJSON 小區界線 + Excel 處理表），呼叫工具鏈：
  1. 小區切割與幾何校正（GeoTIFF / rasterio）；
  2. 植生與傷害指標計算（ExG、VARI、NDRE、brightness 分離、兩方向模板比對）；
  3. 雜草 / 病斑 / 捲葉分割模型（SAM 2.1 zero-shot + YOLO-seg 微調）；
  4. RAG 知識庫（TACTRI 登記試驗準則、EPPO 標準、藥效公式、作物生育期）；
  5. 統計引擎（ANOVA / Tukey、CV 檢核）；
  6. 以 LLM 整合證據，輸出含不確定性與限制說明的評估報告。

* **E. Experiments (Evaluation)**  
  以兩組真實試驗作 case study：
  1. 4RL 水稻縱捲葉蟲試驗（廣西 2026，RCBD 8 處理 $\times$ 3 重複，$\text{GSD } 0.85\text{ cm}$，具 $0 \sim 50\text{ DAA}$ 人工捲葉率 ground truth）；
  2. Concil 水稻除草劑試驗（民雄，RGB + NDRE，具青苔干擾）。  
  *Baseline*：人工評分、單一 VARI 指標、通用 VLM 直接讀圖（GPT-4o / Gemini 2.5 zero-shot，依 [3] 的 prompt 設定）。  
  *Metrics*：影像指標 vs. ground truth 的 Pearson $r$ / Spearman $\rho$、處理排序一致性（Kendall $\tau$）、分割 mIoU、藥效結論與人工結論的一致率、以及 agent 回答的 Grounding / Non-hallucination 專家評分 [3]。

* **F. Expected Findings**  
  預期：
  * (a) 小區級影像指標與人工捲葉率 / 雜草覆蓋度相關 $r > 0.8$；
  * (b) Agent 推得的處理排序與人工結論 Kendall $\tau > 0.7$；
  * (c) 加入領域知識（試驗設計 + 藥效公式 + 干擾排除規則）後，相較通用 VLM 直接讀圖，結論正確率與可追溯性顯著提升；
  * (d) 整理出一套可重複使用的「UAV 影像 $\rightarrow$ 登記試驗報告草稿」pipeline，並記錄於 `DESIGN.md`。  
  *(本 proposal 尚未完成實驗，以上為 expected outcomes)*
