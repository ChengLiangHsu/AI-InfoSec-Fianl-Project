# 需求與決策清單 (REQUIREMENT)

## 同意
- **小區切割（Plot Segmentation）**：使用無人機正射影像結合網格幾何完成試驗小區切割。
- **植生指標計算（Vegetation Index Calculation）**：計算 VARI、NDRE、EXG 等光譜指標並排除背景雜訊。
- **報告草稿生成（AI Draft Report Generation）**：AI Agent 彙整小區計算數值與空拍影像，自動產出具客觀佐證的報告草稿。
- **確定性計算**：藥效公式（Abbott 公式）與指標數值由純 Python 確定性函式計算，確保數值零誤差。
- **通俗單句摘要風格**：文檔採高中生可理解之白話文字，以條列摘要呈現，每項僅一句話。
- **真實試驗資料集**：鎖定廣西 4RL（水稻縱捲葉蟲）與民雄 Concil（水田除草劑）兩大真實試驗。
- **Pydantic AI 協調層**：採用 Pydantic AI 作為 AI Agent 協調層，專注於型別安全工具調度與 FastAPI 服務整合。
- **指定區域像素分析（ROI Pixel Analysis）**：以使用者指定或幾何標記之小區範圍（ROI）為基準進行光譜像素統計，取代缺乏實體邊界的影像分割。
- **小區與處理表對照綁定（Plot-Treatment Mapping）**：建立小區空間座標與試驗藥劑處理表（含無處理對照組 UTC 與重複區）的精準映射對照。
- **核心七階段端到端工作流**：確立「上傳圖片集 $\rightarrow$ 合併正射圖 $\rightarrow$ 小區切割 $\rightarrow$ 選案例（用藥評估、收穫分析） $\rightarrow$ AI Agent 決定評估指標 $\rightarrow$ 各小區比較分析 $\rightarrow$ 產報告」作為系統端到端之完整業務流程。
- **AI 輔助指標推薦與手動覆寫彈性（AI Index Recommendation with Override）**：由 AI Agent 依作物場景與可用光譜波段（RGB/紅邊）動態推薦最適指標並附專業依據，同時畫布頂部保留手動切換選單供使用者自由覆寫。
- **泛用田間監測相容**：架構除農藥藥效試驗外，亦相容收穫期成熟度評估與一般作物生理狀況分析。
- **前端互動式 ROI 框選（Interactive Canvas ROI Annotation）**：使用者直接於前端影像畫布框選小區範圍，並透過彈出選單設定藥劑處理與重複組別。
- **全自主 ReAct 專家工具調度（ReAct Agent Tool-Calling Architecture）**：由 AI Agent 擔任核心指揮官，以 ReAct 循環動態調用像素萃取、指標計算、UTC 檢核與藥效公式等確定性工具，模擬植保專家的分析歷程。
- **對照組低壓雙軌判定（UTC Low Pressure Dual Handling）**：無處理對照組壓力不足時，系統出具「不具法定效力」黃色警示，但仍完整運算相對藥效與排名供內部研究參考。
- **光譜均值差分保護度評估（Zonal Mean Relative Protection）**：直接以各小區植生指標平均值（如 VARI 均值）相對於對照組進行差分計算，客觀評估生長優勢與保護效能。
- **三合一結果聯動呈現（Tripartite Result Interaction）**：聊天窗條列精鍊結論與佐證、畫布小區依保護度等級著色、並提供一鍵預覽匯出 Markdown 完整報告。
- **小區指標持久化快查工具（SQLite Plot Metrics Querying）**：各小區分區統計結果持久化至 SQLite，由 Agent 呼叫專屬查詢工具秒級解答追問與重複區細部差異。
- **main.py 模組化服務導向拆分（Modular Service-Oriented Architecture）**：將單一主程式拆分為獨立路由（Routers）、Agent 服務、影像處理服務與資料存取模組，main.py 僅負責主流程調度與應用程式入口。
- **統一資料存取層至 src/database.py**：將資料庫存取集中管理於 `src/database.py`，維持相容非同步介面以確保測試與現有資料庫平滑銜接。
- **模組分層命名結構（Controllers / Agents / Utility）**：FastAPI 路由統一歸入 `src/controllers/`，Pydantic AI 代理人與工具歸入 `src/agents/`，公式與影像輔助運算歸入 `src/utility/`。
- **Agent 模組命名與組織（src/agents/pydantic_agent.py）**：將 Pydantic AI 代理人核心、System Prompt 與關聯 Tools 集中於 `src/agents/pydantic_agent.py`，並於 `__init__.py` 統一導出。
- **控制器專責拆分（Controllers Division）**：對話歷史與 Agent 串流互動收錄於 `src/controllers/conversation.py`，航拍任務與影像生成收錄於 `src/controllers/odm.py`。
- **公用運算庫整合（Utility Modules）**：植生公式、光譜熱圖生成與 NodeODM 管理收納至 `src/utility/`。
- **嚴格職責純粹之主程式進入點**：`src/main.py` 僅保留 FastAPI 實例、生命週期與控制器掛載，不進行任何非必要的符號 re-export，外部與測試端直接對齊新模組路徑。
- **清理無用過度工程目錄**：移除專案內殘留之空的 `src/adapter` 分層目錄，落實精簡服務導向架構。

## 拒絕
- **拒絕非標準專屬 Agent 平台**：不採用 Google Antigravity SDK 等特定生態平台，確保全開源與環境高度可攜性。
- **拒絕 AI 盲切小區邊界**：不使用 AI 模型自動辨識模糊小區邊界，小區範圍依賴人工指定或試驗幾何向量。
- **拒絕純靜態向量綁定**：不強制依賴外部預製幾何向量檔，賦予使用者在前端畫布自由框選小區邊界之操作彈性。
- **拒絕死板硬編碼流水線**：避免將分析步驟寫死為無彈性的固定程序腳本，保留 Agent 依據試驗情境動態調度工具之自主性。
- **拒絕低壓強制中斷程式**：不因對照組蟲害或草害未達法定門檻而直接終止程式，保留內部研究探索分析之彈性。
- **拒絕脆弱受害二值化閾值**：不使用易受天候光照干擾的單一光譜門檻硬切受害葉片百分比，改採連續光譜統計均值。
- **拒絕割裂式純文字長篇報告**：不採用無畫面聯動的長篇純文字輸出，拒絕缺乏視覺交互之枯燥呈現。
- **拒絕每次追問重複影像重算**：不於對話追問時重新讀取高解析度正射影像，消除冗餘 I/O 與計算開銷。
- **拒絕封閉式指標硬性鎖定**：不強制隱藏公式切換選單，拒絕剝奪使用者手動驗證不同光譜演算法之彈性。
- **拒絕 RAG 向量架構**：不使用向量資料庫（Vector DB）與 RAG 檢索流程。
- **拒絕重型分割模型**：不採用 SAM 2.1、YOLO-seg 等深度學習實例分割模型。
- **拒絕複雜統計引擎**：不引入 ANOVA 與 Tukey HSD 等複雜推論統計模型。
- **拒絕邊緣試驗資料**：不納入小麥赤黴病（FHB）與水稻育苗箱計數等非核心資料。
- **拒絕過度工程 Clean Architecture**：不採用 entity/usecase/adapter/port 分層，改採模組化服務導向架構。
- **拒絕龐大單檔單體架構**：不將路由、Agent 工具、影像演算法與資料庫邏輯混雜於單一 main.py 中。
- **拒絕殘留未使用的空分層目錄**：清理並杜絕在專案中保留無實際業務邏輯的架構模板空目錄。
- **拒絕主程式進入點混合轉導（No Symbol Re-export in main.py）**：拒絕在 `src/main.py` 扮演通用的模組 re-export 轉導層，杜絕偽解耦。
- **拒絕冗長學術黑話**：避免晦澀學術名詞與長篇大論。