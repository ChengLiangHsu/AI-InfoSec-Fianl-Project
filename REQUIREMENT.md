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
- **核心四大標準流程**：確立「選案例 $\rightarrow$ 選指標 $\rightarrow$ 比小區 $\rightarrow$ 產報告」作為系統端到端之核心工作流。
- **AI 輔助指標推薦（AI Index Recommendation）**：由 AI Agent 依作物場景與可用波段檢索領域依據，動態推薦最適植生指標。
- **泛用田間監測相容**：架構除農藥藥效試驗外，亦相容收穫期成熟度評估與一般作物生理狀況分析。

## 拒絕
- **拒絕非標準專屬 Agent 平台**：不採用 Google Antigravity SDK 等特定生態平台，確保全開源與環境高度可攜性。
- **拒絕 AI 盲切小區邊界**：不使用 AI 模型自動辨識模糊小區邊界，小區範圍依賴人工指定或試驗幾何向量。
- **拒絕 RAG 向量架構**：不使用向量資料庫（Vector DB）與 RAG 檢索流程。
- **拒絕重型分割模型**：不採用 SAM 2.1、YOLO-seg 等深度學習實例分割模型。
- **拒絕複雜統計引擎**：不引入 ANOVA 與 Tukey HSD 等複雜推論統計模型。
- **拒絕邊緣試驗資料**：不納入小麥赤黴病（FHB）與水稻育苗箱計數等非核心資料。
- **拒絕過度工程 Clean Architecture**：不採用 entity/usecase/adapter/port 分層，改採模組化服務導向架構。
- **拒絕冗長學術黑話**：避免晦澀學術名詞與長篇大論。