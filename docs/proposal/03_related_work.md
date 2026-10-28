# 3. Related Work 相關研究

### 3.1 AI Technology
* **農業多模態 AI 與 Agent（2025–2026）**：
  * **辨識基準與局限**：AgroBench [1] 與 AgroMind [4] 評測顯示，通用多模態 AI 看農田照片時容易有視角偏差，辨識細小雜草的表現甚至接近隨機猜測。
  * **農業專用 Agent 萌芽**：AgriDoctor [2] 等最新研究首度嘗試以 Agent 架構串接工具診斷作物，但現有系統多針對單株近拍照，缺乏農田小區試驗的結構概念。
  * **AI 可解釋性評估**：無人機雜草研究 [3] 提出讓 AI 輸出可驗證理由（Grounding 與 Non-Hallucination 評分），本專題將其作為報告防幻覺之檢核基準。
* **無人機小區與植生指標分析**：
  * **小區半自動切割**：農田試驗界線過去多依賴人工標註，現行技術可透過幾何邊界與線條偵測實現半自動小區分割 [21]。
  * **光譜指標與干擾排除**：VARI 指標能有效量化作物綠度活力，結合 NDRE 紅邊指標則能進一步排除水田青苔與水面雜訊的干擾。

### 3.2 Domain Know-how
* **田間試驗設計與重複原則（Replications & Trial Design）**：
  * **空間異質性與重複試驗**：田間環境存在土壤肥力、微地形、水分與初始病蟲草害分布的天然異質性，單一小區數值容易受局部干擾偏差影響；依據標準田間試驗規範（如 [EPPO PP 1/152 標準指南][eppo]），標準試驗通常設置 3 至 4 次獨立重複（Replications，業界常態為 3 重複）以平抑田間變異 [18, trial]。
  * **處理組去平均與差異解讀**：相同「農藥＋劑量」的小區需透過計算處理組平均值（Treatment Mean）作為整體藥效代表值；當同處理小區呈現過大差異時，依據異常觀測處理原則 [nist]，需兼採「以重複平均看總體趨勢、保留個別小區數值回查空拍圖與設定」之雙軌解讀，不任意刪除數據。
  * **未施藥對照（UTC / CK）之基準角色**：對照組同樣設置重複小區，用以提供無藥劑干擾下的自然消長基準，作為評估各處理組相對抑制率或生長差異之必要參照。

### 3.3 Article Summary Table

| Ref. | Year | Problem | AI Method | Domain Knowledge | Dataset | Findings | Limitation |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| [[1]][agrobench] | 2025 | 通用多模態大模型於農業場景之理解基準評估 | 多模態基準測試 (VLM Benchmark) | 作物病徵、雜草形態與生長階段農學特徵 | AgroBench (跨視角農田高解析影像集) | 通用多模態 AI 對空拍細小雜草辨識表現接近隨機猜測 | 僅為靜態評測基準，未提供試驗分析與工具調度能力 |
| [[2]][agridoctor] | 2025 | 農業跨領域問答與病蟲害輔助診斷 | 多模態 Agent 架構 + 工具調度 | 作物病理診斷特徵與基礎植保處方知識 | 農業病害圖像與問答資料集 | Agent 架構能顯著提升單株作物多模態診斷之專業度 | 聚焦單株近景特寫，缺乏田間小區試驗網格與藥效公式 |
| [[3]][weed-vlm] | 2025 | 無人機農田雜草零樣本辨識與視覺推理 | 視覺語言模型 (VLM) + Grounding 防幻覺機制 | 雜草光譜與形態特徵、田間空間分佈 | 無人機低空田間高解析空拍影像集 | 視覺錨點 (Grounding) 能有效抑制 AI 判讀幻覺並提供依據 | 僅限個別雜草定位，未結合重複試驗設計與藥效對照組 |
| [[12]][qu2023] | 2023 | 田間試驗人工目測評分的主觀偏見與個體疲勞 | 潛在尺度統計模型 (Latent Scale Model) | 評估者心理計量偏差與田間試驗主觀評分漂移 | NTEP 全美草坪草田間人工目測歷史評分集 | 人工目測評分在不同評價者間存在顯著且不可消除的系統誤差 | 僅對歷史數據建模，未能從源頭提供客觀影像測量 |
| [[18]][eppo] | 2019 | 農藥田間藥效試驗標準化評估與統計規範 | 傳統統計分析 (ANOVA / 處理平均 Treatment Mean) | [EPPO PP 1/152 標準][eppo]、隨機完全區集 (RCBD)、未施藥對照 (UTC) | 拜耳 (Bayer) 田間藥效試驗實測數據 | 3 至 4 次獨立重複是消除田間空間異質性的最低統計標準 | 依賴人工調查紀錄，缺乏正射空拍影像之幾何與數值雙向追溯 |
| [[21]][plot-seg] | 2020 | 無人機空拍試驗田人工標記小區網格費時耗力 | 半自動幾何小區網格分割演算法 | 試驗田邊界、小區行走道與空間排列幾何 | 多試驗田無人機空拍正射影像集 | 半自動幾何網格輔以人工微調兼具標註效率與邊界精度 | 僅完成幾何網格切割，未整合 AI 代理人推薦與試驗指標比較 |

[agrobench]: https://arxiv.org/abs/2412.18432
[agridoctor]: https://arxiv.org/abs/2509.17044
[weed-vlm]: https://doi.org/10.3389/fpls.2025.1735096
[qu2023]: https://doi.org/10.3389/fpls.2023.1135918
[eppo]: https://www.eppo.int/RESOURCES/eppo_standards/standards_pp1
[plot-seg]: https://doi.org/10.3389/fpls.2020.591886

### 3.4 Existing Research $\longrightarrow$ Limitations $\longrightarrow$ Research Gap $\longrightarrow$ Our Project

$$\text{Existing Research} \longrightarrow \text{Limitations} \longrightarrow \text{Research Gap} \longrightarrow \text{Our Project}$$

* **Existing Research (現有研究)**：
  * 多模態農業 AI（如 [AgroBench][agrobench]、[AgriDoctor][agridoctor]）逐步具備影像理解與對話診斷潛力。
  * 無人機遙測與小區網格切割（如 [半自動小區分割][plot-seg]、[VARI 指標][vari]）已證實可客觀量化農田生長活力。
* **Limitations (既有限制)**：
  * 人工田間目測評分存在不可消除的主觀偏差與重複性低之缺陷（[Qu et al.][qu2023]）。
  * 通用多模態 AI 不具備田間試驗設計概念（如 [EPPO PP 1/152][eppo] 規範之重複區與對照組），對空拍細節辨識度低。
  * 既有遙測分析工具多為封閉腳本，缺乏由領域 AI 代理人根據試驗情境推薦合適指標並解說理由之協同機制。
* **Research Gap (研究缺口)**：
  * 目前市場與學界仍缺乏一個整合「高解析無人機正射影像」、「互動式小區試驗網格配置」、「由 AI 代理人依評估目的推薦指標與說明理由」並提供「雙向可追溯影像指標比較」之專用領域智慧代理人（Domain AI Agent）。
* **Our Project (本專題提案)**：
  * 本專題提出**無人機田間試驗評估智慧代理人**：基於無人機高解析 RGB 空拍圖，由使用者在畫布上互動框選並微調小區網格，指定農藥劑量與未施藥對照組（CK/UTC）；透過 Pydantic AI Agent 依試驗目的推薦合適光譜指標（VARI、ExG）並由使用者確認後啟動計算；自動計算 3 重複平均值與對照組差異，並以畫布著色與數值比較表呈現雙向可追溯之客觀分析成果。

[vari]: https://step.esa.int/main/wp-content/help/versions/13.0.0/snap-toolboxes/eu.esa.opt.opttbx.radiometric.indices.ui/vari/VariAlgorithmSpecification.html
