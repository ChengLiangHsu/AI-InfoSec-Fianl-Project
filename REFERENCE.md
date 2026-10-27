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

### SQLModel & SQLite
- [SQLModel 官方文件](https://sqlmodel.tiangolo.com/)
- [SQLite 官方文件](https://www.sqlite.org/docs.html)

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

### OpenDroneMap & NodeODM (正射拼圖引擎)
- [OpenDroneMap (ODM) 官方文件](https://docs.opendronemap.org/)
- [OpenDroneMap 航拍攝影測量採集指南 (Flight Planning & Overlap Guidelines)](https://docs.opendronemap.org/flying/)
- [NodeODM API 規範與容器架構](https://github.com/OpenDroneMap/NodeODM)
- [OpenDroneMap 輸出檔案與正射影像](https://docs.opendronemap.org/outputs/)

### Vue.js
- [Vue.js 官方文件](https://vuejs.org/)
- [Vue.js 組合式函數 (Composables) 官方指引](https://vuejs.org/guide/reusability/composables.html)

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

### Docker (容器化服務)
- [Docker 官方文件](https://docs.docker.com/)
- [Docker CLI run 規範指南](https://docs.docker.com/reference/cli/docker/container/run/)
