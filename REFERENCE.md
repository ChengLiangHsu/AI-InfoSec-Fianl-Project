# 技術與架構參考依據 (REFERENCE)

### Python
- [Python 官方文件](https://docs.python.org/3/)
- [Python 官方文件 - dataclasses (Data Classes)](https://docs.python.org/3/library/dataclasses.html)
- [Python 官方文件 - asyncio.to_thread (Running in Threads)](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
- [Python 官方文件 - typing.Protocol (PEP 544 結構化子型別)](https://docs.python.org/3/library/typing.html#typing.Protocol)
- [Python 官方文件 - 內建異常 (Built-in Exceptions)](https://docs.python.org/3/library/exceptions.html)
- **採用架構**：領域層以純 `dataclass` 定義純粹實體；以 `Protocol` 宣告倉儲與通訊契約；倉儲層以原生 `asyncio.to_thread` 調度同步 Session 達成無阻塞非同步介面；用例層僅拋出原生例外維持核心領域純粹性。

### FastAPI
- [FastAPI 官方文件](https://fastapi.tiangolo.com/)
- [FastAPI APIRouter 模組化架構指引](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [FastAPI 依賴注入 (Dependencies with yield)](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)
- [FastAPI 全域異常處理器 (Handling Errors)](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- **採用架構**：以單一控制器 `src/controllers/task.py` 整合航拍任務生命週期與對話歷程，透過 `Depends` 動態注入具備請求生命週期的倉儲與用例，並由全域異常處理器統一轉譯回應。

### Clean Architecture (整潔架構) 與 DDD
- [The Clean Architecture (Robert C. Martin / Uncle Bob)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Martin Fowler - Aggregate Pattern](https://martinfowler.com/bliki/DDD_Aggregate.html)
- [Martin Fowler - Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- **採用架構**：後端嚴格遵循 Entities（領域實體）、UseCases（應用業務流程）、Repositories（持久化倉儲）與 Controllers（路由調度）四層架構；以 `Task` 作為聚合根內嵌 `Plot`；用例強制透過抽象 Port 依賴反轉，落實職責分離。

### Pydantic AI
- [Pydantic AI 官方文件](https://ai.pydantic.dev/)
- [Pydantic AI 工具調度機制 (Function Tools)](https://ai.pydantic.dev/tools/)
- [Pydantic AI 結構化輸出與型別驗證 (Structured Results)](https://ai.pydantic.dev/results/#structured-result-validation)
- [Pydantic 核心文件](https://docs.pydantic.dev/)
- [ReAct 代理人架構論文 (Yao et al., 2022)](https://arxiv.org/abs/2210.03629)
- **採用架構**：作為後端 AI 協調層，依使用者選定目的進行結構化情境推估與植生指標推薦，經使用者明確確認後動態調度確定性運算工具。

### SQLModel & SQLite
- [SQLModel 官方文件](https://sqlmodel.tiangolo.com/)
- [SQLite 官方文件](https://www.sqlite.org/docs.html)
- [SQLite Single-file Architecture 規範](https://www.sqlite.org/about.html)
- [SQLite JSON1 擴充規範](https://www.sqlite.org/json1.html)
- **採用架構**：以本機 SQLite 作為專案任務中繼資料、對話歷史與小區指標之單一事實來源，將複雜小區清單以 JSON1 扁平化字串儲存，達成運算引擎與業務資料生命週期解耦。

### OpenDroneMap & NodeODM (正射拼圖引擎)
- [OpenDroneMap (ODM) 官方文件](https://docs.opendronemap.org/)
- [NodeODM REST API 規範與容器架構](https://github.com/OpenDroneMap/NodeODM)
- [OpenDroneMap 航拍攝影測量採集指南](https://docs.opendronemap.org/flying/)
- [HTTPX 官方文件 (Async Client & Multipart Uploads)](https://www.python-httpx.org/async/)
- **採用架構**：以 NodeODM 容器作為正射拼圖引擎，透過 `src/requesters/odm.py` 之 `OdmRequester` 封裝 HTTP 通訊與任務監控，將成果解壓為 GeoTIFF 與高解析度 PNG 底圖。

### OpenCV 影像處理
- [OpenCV 官方文件](https://docs.opencv.org/4.x/)
- [OpenCV 影像二值化與閥值處理 (Thresholding)](https://docs.opencv.org/4.x/d7/4d/tutorial_py_thresholding.html)
- [OpenCV 輪廓特徵與凸包 (Contours & Convex Hull)](https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html)
- **採用方法**：於 `src/utility/marker_detection.py` 運用亮度閥值、輪廓特徵幾何過濾與凸包逼近演算法，一鍵精準自動定位試驗田最外圍 4 個白色定位插牌角點。

### 植生指標與光譜遙測 (Vegetation Indices & Zonal Statistics)
- [VARI 植生指標研究文獻 (Gitelson et al., 2002)](https://doi.org/10.1016/S0034-4257(01)00318-2)
- [ExG 綠度色彩指標原始文獻 (Woebbecke et al., 1995)](https://elibrary.asabe.org/abstract.asp?aid=27838)
- [Rasterstats / Zonal Statistics 空間分區統計規範](https://pythonhosted.org/rasterstats/)
- [Bilinear Interpolation 雙線性插值數學原理 (Wikipedia)](https://en.wikipedia.org/wiki/Bilinear_interpolation)
- **採用方法**：以確定性 Python 公式計算 VARI/ExG 等 RGB 植生指標，結合雙線性插值演算法生成小區網格，透過空間分區統計萃取各小區像素均值並排除裸土背景雜訊。

### 田間試驗設計與重複分析 (Field Trial Design & EPPO Standards)
- [EPPO Standard PP 1/152(4)：植保產品藥效評估試驗設計與分析標準指南](https://pp1.eppo.int/standards/pp1-152-4)
- [NIST 異常觀測處理原則 (EDA Guidelines)](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm)
- [FAIR 資料原則 (FAIR Data Principles)](https://www.nature.com/articles/sdata201618)
- **採用方法**：彈性支援多小區重複配置（如 3 重複），計算去平均值（Treatment Mean）平抑田間自然變異，同時依 NIST 與 FAIR 原則完整保留各重複小區數值以供追溯排查。

### Vue.js & Vite 前端架構
- [Vue.js 官方文件](https://vuejs.org/)
- [Vue.js 組合式函數 (Composables) 指引](https://vuejs.org/guide/reusability/composables.html)
- [Vite 官方文件](https://vite.dev/)
- [Vite Server Proxy 官方設定指引](https://vite.dev/config/server-options#server-proxy)
- **採用架構**：前端基於 Vue 3 Composition API 與 Vite 建置，抽出 `useOdmProgress` 等 composables，並由 Vite Proxy 統一重寫 `/api` 通道導向後端控制器。

### HTML5 Canvas & 前端互動介面
- [MDN Canvas API 官方文件](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)
- [MDN Path2D 官方文件](https://developer.mozilla.org/en-US/docs/Web/API/Path2D)
- [MDN Server-Sent Events (SSE) 官方規範](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Tailwind CSS 官方文件](https://tailwindcss.com/)
- **採用架構**：於正射影像上疊加透明 Canvas 進行 0.0 ~ 1.0 正規化多邊形與矩形小區標註，搭配 GPU 硬體加速 Transform 實現滑鼠右鍵平移與滾輪縮放。

### AI Elements Vue & Persona 組件
- [AI Elements Vue - Persona 組件官方文件](https://www.ai-elements-vue.com/components/voice/persona#obsidian-default)
- [Rive Runtime WebGL2 官方文件](https://help.rive.app/runtimes/overview/web-js)
- [VueUse useDraggable 官方文件](https://vueuse.org/core/useDraggable/)
- **採用架構**：採用 Obsidian 變體 64px 懸浮互動球體，動畫狀態與 Agent 推論生命週期連動，透過 `useDraggable` 與視窗邊界箝制演算法實現防誤觸拖曳與自適應避障視窗展開。

### Exifr (影像中繼資料解析)
- [exifr 影像 EXIF/GPS 讀取工具官方文件](https://github.com/MikeKovarik/exifr)
- **採用方法**：前端於上傳階段輕量提取相片檔名清單與 EXIF 拍攝時間/GPS，供 AI 代理人即時推估試驗情境特徵。

### Google Cloud Platform (GCP)
- [Google Cloud Compute Engine 官方文件](https://cloud.google.com/compute/docs)
- [Google Cloud IAP TCP 轉送（TCP Forwarding）官方指南](https://cloud.google.com/iap/docs/using-tcp-forwarding)
- [Google Cloud VPC 防火牆規則設定規範](https://cloud.google.com/firewall/docs/firewalls-overview)
- [Google Cloud CLI 指令參考手冊](https://cloud.google.com/sdk/gcloud/reference)
- **採用架構**：以台灣彰化機房 `asia-east1-b` 之 `e2-highmem-4` 主機運行容器服務，SSH 連線嚴格限制由 GCP IAP 安全通道代理，管理金鑰保留於本機受控環境。

### Docker & Caddy
- [Docker Compose 官方規範與部署指南](https://docs.docker.com/compose/)
- [Docker Volumes 持久化存儲指南](https://docs.docker.com/engine/storage/volumes/)
- [Caddy 2 官方文件：Automatic HTTPS 全自動憑證](https://caddyserver.com/docs/automatic-https)
- [DuckDNS 官方規範與 HTTP API 規格](https://www.duckdns.org/spec.jsp)
- **採用架構**：以 Docker Compose 編排 FastAPI、NodeODM 與 Caddy 反向代理，透過具名資料卷 `app_data` 無縫保留 SQLite 資料庫與航拍快取，並由 Caddy 結合 DuckDNS 全自動申請維護 HTTPS 憑證。
