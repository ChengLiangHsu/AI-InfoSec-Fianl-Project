# 技術與架構參考依據 (REFERENCE)

### Python
- [Python 官方文件](https://docs.python.org/3/)

### Astral uv
- [uv 官方文件](https://docs.astral.sh/uv/)

### FastAPI
- [FastAPI 官方文件](https://fastapi.tiangolo.com/)
- [FastAPI APIRouter 模組化架構指引](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [FastAPI StreamingResponse 官方文件](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)

### Pydantic AI
- [Pydantic AI 官方文件](https://ai.pydantic.dev/)
- [Pydantic AI 工具調度機制 (Function Tools)](https://ai.pydantic.dev/tools/)
- [Pydantic 核心文件](https://docs.pydantic.dev/)
- [ReAct 代理人架構論文 (Yao et al., 2022)](https://arxiv.org/abs/2210.03629)

### 五個核心思維（Q1 三面向與高中生科學語境）
- **採用方法**：以「核心意義」、「具體佐證」、「系統行為」三面向呈現五項思維模式（理解指標、確認輸入、保留差異、配置比較、結果追溯），並採高中生基礎自然科學與資訊認知層次進行精簡描述。
- [第四章課程規範：核心思維三大面向要求](docs/proposal/COURSE.md#L87-L90)

### 小區差異核對與雙軌解讀
- **採用方法**：相同農藥與劑量的小區出現明顯指標差異時，以 3 重複平均代表處理組總體表現以平抑田間自然變異，同時保留個別小區結果並回看影像與設定排查局部干擾原因，不擅自刪除離群小區。
- [NIST 異常觀測處理原則：差異可能來自錯誤或真實變異，應先調查而非直接刪除](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm)

### 依試驗配置比較與重複去平均（Replications & Treatment Mean）
- **採用方法**：以小區為單位保存結果，彈性支援重複小區配置（典型為 3 重複），依相同「農藥＋劑量」計算去平均數值（Treatment Mean）作為處理組代表值，並與明確指定對照組進行差異比較；比較表完整保留個別小區明細。
- [明尼蘇達大學田間研究指南：對照、重複、配置與小區內取樣的區別](https://extension.umn.edu/courses-and-events/for-professionals/on-farm-research/how-to-do-research-on-your-farm)
- [EPPO Standard PP 1/152(4)：植保產品藥效評估試驗設計與分析標準指南（重複試驗規範）](https://www.eppo.int/RESOURCES/eppo_standards/standards_pp1)


### 結果可追溯
- **採用方法**：保存小區、影像對應範圍、處理與指標設定及計算結果，讓畫布與比較表能核對數值來源。
- [FAIR 資料原則：R1.2 的詳細來源紀錄要求](https://www.nature.com/articles/sdata201618)

### SQLModel & SQLite
- [SQLModel 官方文件](https://sqlmodel.tiangolo.com/)
- [SQLite 官方文件](https://www.sqlite.org/docs.html)
- [SQLite Single-file Architecture：適用於本地代理人應用與中繼資料持久化之獨立儲存規範](https://www.sqlite.org/about.html)
- **採用架構**：以本機 SQLite 作為專案任務中繼資料、對話歷史與小區指標之單一事實來源，將運算引擎（NodeODM）與業務資料生命週期解耦。

### Rasterio & GeoTIFF
- [Rasterio 官方文件](https://rasterio.readthedocs.io/en/stable/)
- [OGC GeoTIFF 標準規範](https://www.ogc.org/standard/geotiff/)

### NumPy & Pillow
- [NumPy 官方文件](https://numpy.org/doc/stable/)
- [NumPy 等距分點：網格座標生成參考](https://numpy.org/doc/stable/reference/generated/numpy.linspace.html)
- [Pillow (PIL Fork) 官方文件](https://pillow.readthedocs.io/en/stable/)

### 空間分區統計 (Zonal Statistics)
- [Rasterstats / Zonal Statistics 規範與演算法](https://pythonhosted.org/rasterstats/)

### Exifr
- [exifr 影像 GPS/EXIF 讀取工具](https://github.com/MikeKovarik/exifr)

### 地面取樣距離與影像輸入標準化
- **專案規格**：使用空拍機拍攝的高解析度 RGB JPG、PNG 或 JPEG 影像，GSD < 1 cm/px 作為資料準備規範，由使用者確認，第一版不以系統自動檢核 GSD 作為拒絕分析的條件。
- [Ground sample distance：使用者提供的 GSD 定義參考](https://en.wikipedia.org/wiki/Ground_sample_distance)
- [OpenDroneMap 航拍採集指南：拍攝規劃與照片重疊條件](https://docs.opendronemap.org/flying/)

### OpenDroneMap & NodeODM (正射拼圖引擎)
- [OpenDroneMap (ODM) 官方文件](https://docs.opendronemap.org/)
- [OpenDroneMap 航拍攝影測量採集指南 (Flight Planning & Overlap Guidelines)](https://docs.opendronemap.org/flying/)
- [NodeODM API 規範與容器架構](https://github.com/OpenDroneMap/NodeODM)
- [OpenDroneMap 輸出檔案與正射影像](https://docs.opendronemap.org/outputs/)

### Vue.js & Vite 前端架構
- [Vue.js 官方文件](https://vuejs.org/)
- [Vue.js 組合式函數 (Composables) 官方指引](https://vuejs.org/guide/reusability/composables.html)
- [Vite 官方文件](https://vite.dev/)
- [Lucide Icons 官方文件](https://lucide.dev/)

### Server-Sent Events (SSE) 與串流傳輸
- [MDN Server-Sent Events (SSE) 官方規範](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [MDN EventSource API 官方文件](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [WHATWG HTML Server-Sent Events 標準](https://html.spec.whatwg.org/multipage/server-sent-events.html)

### 前端互動介面 (HTML5 Canvas & Drag-and-Drop)
- [MDN Canvas API 官方文件](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)
- [MDN click 事件：選取農藥與點選小區的互動參考](https://developer.mozilla.org/en-US/docs/Web/API/Element/click_event)
- [MDN Canvas isPointInPath：小區點選範圍判斷參考](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/isPointInPath)
- [MDN HTML5 Drag and Drop API 官方文件](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API)

### 農業植保與藥效評估背景（正式藥效與法定判定為後續待確認範圍）
- [EPPO PP 1 植保產品藥效評估標準指南](https://www.eppo.int/RESOURCES/eppo_standards/standards_pp1)
- [Abbott's Formula 藥效計算公式文獻](https://academic.oup.com/jee/article-abstract/18/2/265/891391)
- [農業部農業藥物試驗所 (TACTRI) 官網與技術指引](https://www.tactri.gov.tw/)

### 植生指標計算 (Vegetation Indices)
- [VARI 植生指標研究文獻 (Gitelson et al., 2002)](https://doi.org/10.1016/S0034-4257(01)00318-2)
- [ESA SNAP VARI 公式與 RGB 波段定義](https://step.esa.int/main/wp-content/help/versions/13.0.0/snap-toolboxes/eu.esa.opt.opttbx.radiometric.indices.ui/vari/VariAlgorithmSpecification.html)
- [Esri VARI 文件：適用 RGB 彩色影像](https://pro.arcgis.com/en/pro-app/3.4/arcpy/spatial-analyst/vari.htm)
- [ExG RGB 色彩指標原始文獻 (Woebbecke et al., 1995)](https://elibrary.asabe.org/abstract.asp?aid=27838)

### 影像與人工調查（Q2 研究依據）
- [Duddu et al.（2019）：High-Throughput UAV Image-Based Method Is More Precise Than Manual Rating of Herbicide Tolerance](https://doi.org/10.34133/2019/6036453)
- [Jay et al.（2020）：Scoring Cercospora Leaf Spot on Sugar Beet: Comparison of UGV and UAV Phenotyping Systems](https://doi.org/10.34133/2020/9452123)

### RGB 與多光譜（Q2 研究依據）
- [Betitame et al.（2025）：Comparing the efficiency of RGB and multispectral sensors for broadleaf and grass weeds identification in soybean fields using UAV（USDA 研究摘要）](https://www.ars.usda.gov/research/publications/publication/?seqNo115=418513)
- [Xia et al.（2022）：Identification and Comprehensive Evaluation of Resistant Weeds Using Unmanned Aerial Vehicle-Based Multispectral Imagery](https://doi.org/10.3389/fpls.2022.938604)

### 小區整體與細部分辨（Q2 研究依據）
- [Peña et al.（2013）：Weed Mapping in Early-Season Maize Fields Using Object-Based Analysis of Unmanned Aerial Vehicle (UAV) Images](https://doi.org/10.1371/journal.pone.0077151)
- [Semi-supervised Learning for Weed and Crop Segmentation Using UAV Imagery（2022）](https://doi.org/10.3389/fpls.2022.927368)
- **使用範圍**：上述文獻用於提案的專業取捨討論，第一版維持 RGB 指標比較，未採用研究中的多光譜設備、完整細分類或重型分割模型。

### 深度理解問題（Q3 學理與規範依據）
- [第四章課程規範：10 個深度理解問題檢核標準](docs/proposal/COURSE.md#L97-L100)
- [VARI 植生指標研究文獻 (Gitelson et al., 2002)：高植被覆蓋下光譜飽和機理](https://doi.org/10.1016/S0034-4257(01)00318-2)
- [Xia et al.（2022）：作物感染初期光學響應與多光譜/RGB 差異](https://doi.org/10.3389/fpls.2022.938604)
- [Peña et al.（2013）：小區雜草覆蓋與土壤背景對光譜訊號之干擾](https://doi.org/10.1371/journal.pone.0077151)
- [OpenDroneMap 航拍採集指南：超低空旋翼下洗流、拼接畸變與太陽角度 BRDF 光影梯度](https://docs.opendronemap.org/flying/)
- [EPPO Standard PP 1/152(4)：小區邊際效應（Border Effect）與獨立重複避免偽重複規範](https://www.eppo.int/RESOURCES/eppo_standards/standards_pp1)
- [明尼蘇達大學田間研究指南：小區緩衝區設定與空間異質性平抑](https://extension.umn.edu/courses-and-events/for-professionals/on-farm-research/how-to-do-research-on-your-farm)
- [NIST 異常觀測處理原則：保留異常數據以排查微環境與施藥偏差](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm)
- [農業部農業藥物試驗所 (TACTRI)：田間藥效試驗規範與法定藥效判定標準](https://www.tactri.gov.tw/)

### Docker (容器化服務)
- [Docker 官方文件](https://docs.docker.com/)
- [Docker CLI run 規範指南](https://docs.docker.com/reference/cli/docker/container/run/)

### 第三章相關文獻與研究缺口佐證 (Related Work References)
- [Shinoda et al.（2025）：AgroBench: Vision-Language Model Benchmark in Agriculture (ICCV 2025)](https://arxiv.org/abs/2412.18432)
- [Zhang et al.（2025）：AgriDoctor: A Multimodal Intelligent Assistant for Agriculture (arXiv:2509.17044)](https://arxiv.org/abs/2509.17044)
- [Vision-language models for zero-shot weed detection and visual reasoning in UAV-based precision agriculture (Front. Plant Sci. 2025)](https://doi.org/10.3389/fpls.2025.1735096)
- [Qu et al.（2023）：A latent scale model to minimize subjectivity in the analysis of visual rating data (Front. Plant Sci.)](https://doi.org/10.3389/fpls.2023.1135918)
- [EPPO Standard PP 1/152(4)：Design and analysis of efficacy evaluation trials](https://www.eppo.int/RESOURCES/eppo_standards/standards_pp1)
- [Semi-Automated Field Plot Segmentation From UAS Imagery for Experimental Agriculture (Front. Plant Sci. 2020)](https://doi.org/10.3389/fpls.2020.591886)

### Clean Architecture (整潔架構)
- [The Clean Architecture by Robert C. Martin (Uncle Bob)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Martin Fowler - Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Single Responsibility Principle (SRP)](https://en.wikipedia.org/wiki/Single-responsibility_principle)
- **採用架構**：後端嚴格落實 Entities（領域純實體）、UseCases（應用業務流程）、Repositories（SQLModel 持久化倉儲）與 Controllers（FastAPI 路由協調）四層架構。

### Python Dataclasses & Asyncio Concurrency
- [Python 官方文件 - dataclasses (Data Classes)](https://docs.python.org/3/library/dataclasses.html)
- [Python 官方文件 - asyncio.to_thread (Running in Threads)](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
- **非同步策略**：Entity 層以純 dataclass 實現零依賴；倉儲層以 Python 內建 `asyncio.to_thread` 調度同步 SQLModel Session 操作，達成無阻塞非同步介面。



- [Python 官方文件 - typing.Protocol (PEP 544 結構化子型別)](https://docs.python.org/3/library/typing.html#typing.Protocol)
- **採用架構**：UseCase 業務層以 `TaskUseCase` 作為聚合核心，透過 `TaskPort` 宣告倉儲契約；倉儲實作類別（`TaskRepository`）實作對應 Port 並由建構子注入 `Session`，落實依賴反轉與資源生命週期解耦。

### DDD 聚合根與資料對應 (Aggregate Root & Data Mapper)
- [Martin Fowler - Aggregate](https://martinfowler.com/bliki/DDD_Aggregate.html)
- [Martin Fowler - Data Mapper Pattern](https://martinfowler.com/eaaCatalog/dataMapper.html)
- [Python dataclasses - field default_factory](https://docs.python.org/3/library/dataclasses.html#dataclasses.field)
- [SQLite JSON1 擴充與純文字儲存規範](https://www.sqlite.org/json1.html)
- **採用架構**：將 `Plot` 作為內嵌實體收錄於 `Task` 聚合根中，領域層透過 `Task.plots: list[Plot]` 呈現強型別結構，倉儲層（`TaskRepository`）以純文字 JSON 字串映射至 SQLite `tasks.plots` 欄位，消除多表關聯負擔並維持聚合完整性。



