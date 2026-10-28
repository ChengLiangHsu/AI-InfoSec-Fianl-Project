# 2. Introduction 緒論

> **Why is this project worth doing?**  
> * **解決傳統痛點**：農藥上市前必須經過田間試驗，但傳統靠人工肉眼評分最容易產生主觀偏差，也是整個流程中最難重複驗證的弱點。
> * **專案核心價值**：利用高畫質無人機空拍結合專業 AI，能將肉眼評估轉變為「有照片佐證、客觀可計算、隨時可追溯」的科學數據。

### A. Attention Getter
* **無人機空拍資料暴增**：農業無人機已在農田快速普及，2025 年作業面積大幅成長約 60% 達 1,640 萬英畝，產生了海量的高畫質空拍照片 [17]。
* **農業 AI 能夠看懂照片**：隨著 2025 年 AgroBench [1] 與 AgriDoctor [2] 等技術發表，最新 AI 已突破文字對話，能夠真正讀懂空拍照並分析田間作物狀況。
* **一般 AI 看農田不夠精準**：權威評測顯示一般通用 AI 在田間雜草辨識上的表現接近隨機猜測 [1]，必須設計具備植保專業知識的專用 AI Agent 才能勝任。

### B. Background
* **應用領域**：專注於農藥產品的田間藥效試驗，新農藥在台灣上市前皆須依農業藥物試驗所（TACTRI）準則完成試驗並提交報告 [18]。
* **目標使用者**：主要提供農藥公司研發人員、農業試驗機構（如農改場）與審查人員使用，作為客觀評估藥效的輔助工具。
* **技術背景**：一般消費級無人機在低空即可拍出清晰的高畫質空拍圖，搭配 AI 自動化執行小區切割、植生指標計算與報告撰寫。

### C. Problem
如何將一張高畫質無人機空拍圖與試驗設計資料，自動轉為每塊小區的藥效評估結論與報告？具體解決三大子問題：
1. **小區分析與干擾排除**：如何在超高畫質空拍圖中精準切割出小區界線，並有效排除青苔、水面反光與陰影等環境干擾？
2. **試驗規則與公式整合**：如何讓 AI 正確讀懂田間試驗設計（如對照區與重複區），並依據標準農藥公式精準計算藥效？
3. **結論驗證與照片佐證**：如何確保 AI 產出的每一項結論都有對應的照片區域與具體數值支持，杜絕憑空捏造？

### D. Existing Limitations

| 現有做法 | 限制說明 | 佐證來源 |
| :--- | :--- | :--- |
| **人工目測主觀評分** | 容易受個人疲勞與主觀嚴格度影響，不同人評分結果難以客觀重現 | [12] |
| **單純空拍綠度指標** | 容易受到青苔、水面等環境干擾，且未與田間試驗設計及藥效公式整合 | [19] |
| **通用 AI 直接讀圖** | 欠缺農業試驗概念且對空拍細節辨識度低，無法給出可信的專業結論 | [1, 5] |

### E. Innovation
1. **人機協同互動網格配置（Human-in-the-Loop Grid Layout）**：突破傳統人工標註之繁複與純自動模型邊界辨識之脆弱性，結合「邊界框選＋行列生成＋畫布微調＋點選套用處理」，兼顧標註效率與 100% 邊界幾何正確性。
2. **具備領域理由的 AI 代理人指標推薦（Domain-Aware AI Agent with Physical Reasons）**：採用 [Pydantic AI][pydantic-ai] 代理人，依使用者指定之試驗目的（殺菌、除草等）推薦合適之 RGB 光譜指標（如 [VARI][vari]、[ExG][exg]）並詳述物理現象理由；嚴格遵守「使用者明確確認後才啟動計算」之防誤觸機制。
3. **試驗規範級重複去平均與雙向可追溯性（Standardized Replication & Bi-directional Provenance）**：依循標準田間試驗規範（[EPPO PP 1/152][eppo]），彈性支援 3 重複配置與相同「農藥＋劑量」處理組平均值（Treatment Mean）去平均，並保留所有小區原始數值；畫布著色與比較表點擊即可雙向連動核對原始影像小區，消除數據黑箱。

### F. Contributions
1. **技術貢獻（Technical Contributions）**：
   * 提出開源且可本機部署之農業遙測 Agent 輕量架構（[FastAPI][fastapi] + [Pydantic AI][pydantic-ai] + [NodeODM][nodeodm] + [Canvas API][canvas]），無須高階 GPU 伺服器即可完成空拍拼圖、小區分割與光譜分區統計。
   * 建立多模態 AI 與確定性遙測工具（[Rasterio][rasterio]、[Rasterstats][rasterstats]）之安全調度規範，確保試驗分析數據精確無幻覺。
2. **應用貢獻（Application Contributions）**：
   * 將傳統農藥試驗中高主觀偏差、易疲勞的人工肉眼目測，轉化為「有空拍影像存證、客觀可量化且隨時可追溯」的科學數據（[Qu et al.][qu2023]）。
   * 大幅降低農藥公司研發團隊與農業試驗機構（如農改場、[TACTRI][tactri]）進行田間藥效初篩與比對之技術門檻，僅需平民化消費級 RGB 空拍機即可建立標準化評估流程。

[pydantic-ai]: https://ai.pydantic.dev/
[vari]: https://step.esa.int/main/wp-content/help/versions/13.0.0/snap-toolboxes/eu.esa.opt.opttbx.radiometric.indices.ui/vari/VariAlgorithmSpecification.html
[exg]: https://elibrary.asabe.org/abstract.asp?aid=27838
[eppo]: https://www.eppo.int/RESOURCES/eppo_standards/standards_pp1
[fastapi]: https://fastapi.tiangolo.com/
[nodeodm]: https://github.com/OpenDroneMap/NodeODM
[canvas]: https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API
[rasterio]: https://rasterio.readthedocs.io/en/stable/
[rasterstats]: https://pythonhosted.org/rasterstats/
[qu2023]: https://doi.org/10.3389/fpls.2023.1135918
[tactri]: https://www.tactri.gov.tw/
