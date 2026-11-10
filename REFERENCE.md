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
- [OpenDroneMap 命令行與調校參數 (ODM Arguments Reference)](https://docs.opendronemap.org/arguments/)
- [NodeODM REST API 規範與容器架構](https://github.com/OpenDroneMap/NodeODM)
- [OpenDroneMap 航拍攝影測量採集指南](https://docs.opendronemap.org/flying/)
- [HTTPX 官方文件 (Async Client & Multipart Uploads)](https://www.python-httpx.org/async/)
- **採用架構**：以 NodeODM 容器作為正射拼圖引擎，透過 `src/requesters/odm.py` 之 `OdmRequester` 封裝 HTTP 通訊與任務監控，將成果解壓為 GeoTIFF 與高解析度 PNG 底圖。透過 `--skip-3dmodel` 與 `--skip-report` 裁剪非必要 3D 模型與報表生成，並以 `pc-quality: low` 與 `feature-quality: high` 達成兼具高精度幾何對齊與最低資源損耗之 2D 正射圖專用管線。

### Pillow 影像壓縮與轉換優化 (Pillow Fast PNG Compression)
- [Pillow (PIL Fork) 官方文件 - PNG 格式存檔參數](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#png)
- [zlib 壓縮等級與效能基準分析](https://www.zlib.net/)
- [W3C Portable Network Graphics (PNG) Specification (Second Edition)](https://www.w3.org/TR/png/)
- **採用架構**：在 GeoTIFF 轉存為 PNG 與光譜熱圖產出流程中，將 Pillow `save` 參數明確設定為 `compress_level=1`，避免預設 level 6 在單執行緒處理超大像素點陣圖時發生長時間 CPU 佔用與使用者介面等待，在保有完全無損像素色彩的前提下實現 3~5 倍轉檔提速。

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
- [VueUse useElementBounding 官方文件](https://vueuse.org/core/useElementBounding/)
- [Vue 3 範本引用 (Template Refs) 指引](https://vuejs.org/guide/essentials/template-refs.html)
- **採用架構**：採用 Obsidian 變體約 48px 動態吸附互動球體，動畫狀態與 Agent 推論生命週期連動，透過 `useElementBounding` 計算當前步驟之目標按鈕邊界，平滑吸附伴隨並附帶引導氣泡，點擊可就地展開自適應避障之 AskAgent 對話面板。

### Web APIs & 請求中斷架構 (Request Abort & Cancellation)
- [MDN Fetch API - AbortController 官方文件](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)
- [NodeODM REST API 規範與任務移除](https://github.com/OpenDroneMap/NodeODM)
- **採用架構**：前端使用 `AbortController` 實作非同步上傳連線中斷，安全終止進行中之 HTTP POST Multipart 傳輸且保留選取相片；後端在拼接階段提供任務取消機制調度 NodeODM 容器終止，形成全流程雙階中斷機制。

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

### 步驟式工作流與嚮導架構 (Wizard & Stepper Pattern)
- [W3C WAI-ARIA 步進式嚮導設計指引 (Wizard Pattern)](https://www.w3.org/WAI/ARIA/apg/patterns/landmarks/)
- [Vue.js 官方文件 - 條件渲染與動態組件 (Conditional Rendering & Dynamic Components)](https://vuejs.org/guide/essentials/conditional.html)
- [Vue.js 官方文件 - 轉場與動畫 (Transition & Animation)](https://vuejs.org/guide/built-ins/transition.html)
- **採用架構**：以三步驟循序引導模式重構專案工作區；頂部採用狀態感知之 Stepper 步進指示條，底部配置常駐「上一頁 / 下一頁」導航條；結合條件鎖定防呆與未儲存狀態守衛（Dirty Guard），使正射檢視、情境設定與小區標註各自職責專一且操作簡潔。

### 畫布快捷操作與幾何放樣 (Canvas Shortcuts & Computational Geometry)
- [MDN KeyboardEvent 官方文件](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent)
- [MDN MouseEvent: dblclick 官方文件](https://developer.mozilla.org/en-US/docs/Web/API/Element/dblclick_event)
- [MDN MouseEvent: clientX / clientY 與 BoundingClientRect 規範](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/clientX)
- **採用架構**：於 `PlotCanvasOverlay.vue` 監聽鍵盤與滑鼠事件；透過 `Ctrl + C` 緩存選取小區，按下 `Ctrl + V` 時計算原小區左上角外接頂點（$\min(x), \min(y)$），求得相對於滑鼠游標之偏移量並執行正規化平移；畫布交互全面改為「單擊純選取、雙擊才開啟特徵標記對話框」，確保操作專一精準。

### 純手動工作流驗證與無代理人調度 (Manual Workflow Verification)
- [Vue.js 官方文件 - 響應式基礎 (Reactivity Fundamentals)](https://vuejs.org/guide/essentials/reactivity-fundamentals.html)
- [Vue.js 官方文件 - 表單輸入綁定 (Form Input Bindings)](https://vuejs.org/guide/essentials/forms.html)
- **採用架構**：在暫時停用 FloatingPersona 期間，透過純前端響應式狀態驅動完整三步驟工作流；步驟 2 依賴純手動表單綁定與模板設定，消除對外部 AI Agent 的即時依賴，驗證核心業務邏輯的獨立性與可用性。

### shadcn-vue & Reka UI (Sidebar 狀態管理與佈局)
- [shadcn-vue Sidebar 組件官方文件](https://www.shadcn-vue.com/docs/components/sidebar.html)
- [Reka UI createContext 官方指引](https://reka-ui.com/)
- [Vue.js 官方文件 - 依賴注入 (Provide / Inject)](https://vuejs.org/guide/components/provide-inject.html)
- [VueUse useMediaQuery 官方文件](https://vueuse.org/core/useMediaQuery/)
- **採用架構**：使用 shadcn-vue 的 `SidebarProvider` 與 `useSidebar` 上下文管理機制，在點選 Task 卡片或新建專案時調用 `setOpen(false)` 與 `setOpenMobile(false)` 自動閉合側邊欄，釋放最大工作區畫布空間。

### 狀態感知整合卡片架構 (State-Aware Consolidated Card Pattern)
- [shadcn-vue Card 組件官方文件](https://www.shadcn-vue.com/docs/components/card.html)
- [shadcn-vue Progress 組件官方文件](https://www.shadcn-vue.com/docs/components/progress.html)
- [Vue.js 官方文件 - 條件渲染與列表渲染 (Conditional & List Rendering)](https://vuejs.org/guide/essentials/conditional.html)
- [Radix Vue 官方文件 - 狀態無縫切換無障礙規範](https://www.radix-vue.com/)
- **採用架構**：將專案元資料、拼接進度反饋與正射成果檢視收斂於單一動態卡片；卡片 Header 維持「專案名稱＋ID＋狀態與光譜徽章」跨步驟一致性外觀；卡片 Body 依 `progress` 狀態在「運算進度條與中斷按鈕」與「正射影像高解析度畫布」間無縫切換，徹底消除多卡片上下堆疊造成的視覺噪音與垂直空間浪費。

### 步驟專屬條件渲染與狀態隔離架構 (Step-Isolated Conditional Rendering)
- [Vue.js 官方文件 - 條件渲染 (Conditional Rendering v-if / v-show)](https://vuejs.org/guide/essentials/conditional.html)
- [Vue.js 官方文件 - 響應式狀態重置與監聽 (Watchers & Reactivity)](https://vuejs.org/guide/essentials/watchers.html)
- **採用架構**：依據步驟職責落實純淨單一職責分離；步驟 1 與步驟 3 徹底隔離光譜演算法懸浮面板與 Header 光譜模式徽章，僅於步驟 4（各小區光譜分析）專屬解鎖；於 `handleStepChange` 步進切換機制中，切換離開步驟 4 時自動觸發 `selectedFormula = 'rgb'` 響應式重置，杜絕跨步驟濾鏡殘留。

### 全域置底懸浮導航膠囊架構 (Floating Step Navigation HUD Pattern)
- [Vue.js 官方文件 - 事件處理 (Event Handling)](https://vuejs.org/guide/essentials/event-handling.html)
- [Vue.js 官方文件 - 元件 Props 驗證 (Props Declaration)](https://vuejs.org/guide/components/props.html)
- [Tailwind CSS 官方文件 - Backdrop Blur 與模糊特效](https://tailwindcss.com/docs/backdrop-blur)
- [Tailwind CSS 官方文件 - Positioning (絕對與固定定位)](https://tailwindcss.com/docs/position)
- [shadcn-vue Tooltip 官方文件](https://www.shadcn-vue.com/docs/components/tooltip.html)
- **採用架構**：將四步驟切換職責由頂部 Stepper 轉移至單一職責子組件 `StepNavigationHUD.vue`，以固定定位常駐於專案工作區底部中央（`absolute bottom-4 left-1/2 -translate-x-1/2 z-30`）；採用統一之深色毛玻璃（`bg-zinc-950/85 backdrop-blur-md border-white/15`）風格貫穿步驟 1 至 4，步驟 2 捲動內容容器配合 `pb-20` 達成無縫避障；具備條件鎖定 Tooltip 提示，於步驟 4 時隱藏下一步按鈕，達成沉浸式極簡導覽。

### Tailwind CSS 寬幅排版與四步驟向導架構 (Responsive Wide Container & Four-Step Wizard)
- [Tailwind CSS 官方文件 - Max-Width 尺寸規範](https://tailwindcss.com/docs/max-width)
- [Tailwind CSS 官方文件 - Flexbox 與 Grid 佈局](https://tailwindcss.com/docs/flex)
- [W3C WAI-ARIA 步進式嚮導設計指引 (Wizard Pattern)](https://www.w3.org/WAI/ARIA/apg/patterns/landmarks/)
- [Lucide Icons 官方圖示庫](https://lucide.dev/icons/)
- **採用架構**：專案主工作區由 `max-w-4xl`（896px）加寬至 `max-w-7xl`（1280px），使「步驟 1：航拍與正射結果」、「步驟 2：試驗情境設定」、「步驟 3：試驗小區標註」與「步驟 4：各小區光譜分析」四個步驟指示卡片以均衡寬度展開，消除文字緊湊換行問題，並為大螢幕環境下的正射空拍影像畫布提供最大化可視操作面積。

### Google 地圖式滿版暗場圖資架構與直列工具列 (Google Maps Full-Bleed Viewport & Vertical Toolbar)
- [Google Maps JavaScript API UI 控制項規範 (Controls & Overlays)](https://developers.google.com/maps/documentation/javascript/controls)
- [OpenLayers 滿版視圖範例 (Full Screen / Viewport Map)](https://openlayers.org/en/latest/examples/full-screen.html)
- [MDN CSS Layout - Viewport & Flexbox 填滿視窗規範](https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout)
- [Tailwind CSS 佈局與尺寸規範 (Layout & Sizing)](https://tailwindcss.com/docs/size)
- [Figma 工具列與調色盤佈局指南 (Toolbar & Palette Patterns)](https://help.figma.com/hc/en-us/articles/360041068294-Get-started-with-the-toolbar-and-left-sidebar)
- **採用架構**：將步驟 1、步驟 3 與步驟 4 之正射影像底圖與 Canvas 標註層提升為 Google 地圖式滿版視窗（Zero-Scroll，無外層頁面滾動條）；背景採用純黑暗場（`#000000`），專案名稱與狀態以左上角懸浮膠囊 HUD 呈現；縮放 HUD 調整至左下角避免遮擋；步驟 3 小區工具列改採右側直列式圖示膠囊（小畫家樣式），啟用網格生成時向左側平滑展開屬性面板，兼顧沉浸式地圖視野與直覺繪製體驗。

### 極簡試驗情境特徵與多標的獨立組別架構 (Minimalist Scenario & Multi-Target Treatment Architecture)
- [Vue.js 官方文件 - 列表渲染與雙向綁定 (List Rendering & v-model)](https://vuejs.org/guide/essentials/forms.html)
- [shadcn-vue Card 組件官方文件](https://www.shadcn-vue.com/docs/components/card.html)
- [shadcn-vue Input 組件官方文件](https://www.shadcn-vue.com/docs/components/input.html)
- [Nielsen Norman Group - Minimalism in UI Design (簡約介面設計準則)](https://www.nngroup.com/articles/simplicity-vs-choice/)
- **採用架構**：徹底剔除試驗情境卡片之冗餘引導長文、副標題說明與鍵盤快捷鍵提示；各組別卡片獨立維護「藥劑/標的名稱」與「劑量/稀釋倍數」，不再綁定全域單一農藥欄位與重複字串，未設定專案預設給予「1 對照組 (CK) ＋ 1 空白處理組」極簡初始骨架，支援多藥劑混合評估與純粹直覺的手動配置。

### 固定對照組與靜態狀態標籤防呆架構 (Fixed Control Group & Static Status Badge Architecture)
- [Vue.js 官方文件 - 列表渲染 (List Rendering)](https://vuejs.org/guide/essentials/list.html)
- [W3C WAI-ARIA 狀態標籤與徽章指引 (Badge & Status Indicators)](https://www.w3.org/WAI/ARIA/apg/)
- [EPPO Standard PP 1/152(4)：植保產品藥效評估試驗設計與分析標準指南 (對照組基準要求)](https://pp1.eppo.int/standards/pp1-152-4)
- [Nielsen Norman Group - Preventing User Errors (防呆設計原則)](https://www.nngroup.com/articles/user-interface-errors/)
- **採用架構**：推翻原有之處理組點擊切換為對照組機制，首組恆為「對照組 (CK)」，所有組別徽章改為唯讀靜態徽章（Static Badge，無 click 事件、無 hover 偽類、無切換 tooltip），對照組卡片鎖定為固定灰白色（`#94a3b8`）且不渲染選色器，後續新增組別一律固定為「處理組」，杜絕角色誤觸發反轉並確立唯一的試驗基準。

### 表單驗證與無縫焦點跳轉架構 (Form Validation & Seamless Focus Management)
- [Vue.js 官方文件 - 表單輸入綁定 (Form Input Bindings)](https://vuejs.org/guide/essentials/forms.html)
- [Vue.js 官方文件 - 計算屬性 (Computed Properties)](https://vuejs.org/guide/essentials/computed.html)
- [MDN Web Docs - HTML 表單驗證與約束 API (Constraint Validation)](https://developer.mozilla.org/en-US/docs/Learn/Forms/Form_validation)
- [W3C WAI-ARIA 鍵盤導航與焦點管理指引 (Keyboard Navigation & Focus Management)](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/)
- [Nielsen Norman Group - Form Design Best Practices (表單設計與即時驗證準則)](https://www.nngroup.com/articles/web-form-design/)
- **採用架構**：在 `ProjectScenarioCard.vue` 透過 `computed` 即時計算組別完整性（`isFormValid`），對處理組之藥劑與劑量、對照組之名稱進行嚴格非空校驗，雙向連動「新增組別」與「儲存」按鈕之禁用狀態；結合 Vue `nextTick` 與 DOM Focus API 實作新增組別自動聚焦與 Enter 鍵跳格導引，並以 Tailwind `border-destructive/50` 實現零排版位移之極簡警示樣式。

### 工具列絕對定位與樣式隔離架構 (Absolute Positioning & Style Isolation Pattern)
- [Tailwind CSS 官方文件 - Positioning (絕對定位與定位上下文)](https://tailwindcss.com/docs/position)
- [Vue.js 官方文件 - 透傳 Attributes (Fallthrough Attributes)](https://vuejs.org/guide/components/attrs.html)
- [MDN CSS Layout - Containing Block (絕對定位包含塊規範)](https://developer.mozilla.org/en-US/docs/Web/CSS/Containing_block)
- [W3C CSS Transforms 規範 (Transform Translate Y 居中技巧)](https://www.w3.org/TR/css-transforms-1/)
- **採用架構**：小區繪製工具列根節點移除內嵌之 `relative` 樣式，改由外部統一傳遞或內部純粹聲明 `absolute top-1/2 -translate-y-1/2 right-4 z-20`，杜絕 CSS 類別權重覆蓋造成工具列脫軌居中；網格生成抽屜子面板維持 `absolute right-full mr-3 top-1/2 -translate-y-1/2` 對稱對齊並加入 `max-h-[calc(100vh-6rem)] overflow-y-auto` 視窗邊界保護，確保各種螢幕尺寸下皆精準停靠於畫布右側垂直中央。

### 小區選取與特徵對話框雙階分離交互架構 (Two-Stage Selection & Double-Click Modal Architecture)
- [MDN Web Docs - Element dblclick event](https://developer.mozilla.org/en-US/docs/Web/API/Element/dblclick_event)
- [MDN Web Docs - MouseEvent API](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent)
- [Vue.js 官方文件 - 事件處理 (Event Handling)](https://vuejs.org/guide/essentials/event-handling.html)
- [W3C 網頁圖形與幾何命中測試規範 (Hit Testing & Path2D)](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/isPointInPath)
- [Nielsen Norman Group - Direct Manipulation and Selection in GUI](https://www.nngroup.com/articles/direct-manipulation/)
- **採用架構**：將小區交互分離為「選取」與「開啟特徵設定」兩階段。在「選取與檢視模式」下，透過 `mousedown`/`mouseup` 單擊命中判定（`isPointInPath`）僅觸發純幾何選取（高亮框與把手）或空白處取消選取；透過原生 DOM `@dblclick` 雙擊事件直接完成選取並開啟 `PlotTreatmentDialog` 特徵設定對話框。而在「繪圖模式」（矩形拉框、多邊形逐點、橡皮擦）下徹底阻斷與既有小區的選取和彈窗交互，避免繪製新幾何或擦除時發生誤觸發。

### 小區處理設定單擊套用與垂直卡片架構 (Plot Treatment Single-Click Apply & Vertical Card Architecture)
- [shadcn-vue Dialog 組件官方文件](https://www.shadcn-vue.com/docs/components/dialog.html)
- [W3C WAI-ARIA Dialog (Modal) Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
- [Nielsen Norman Group - Selection Controls & Direct Manipulation (選取替代輸入準則)](https://www.nngroup.com/articles/selection-controls/)
- [Material Design 3 - Lists & Selection Controls](https://m3.material.io/components/lists/overview)
- **採用架構**：小區處理設定彈窗徹底淘汰手動輸入框與頂部切換頁籤，將步驟 2 情境設定之組別作為唯一資料事實來源。介面採用垂直卡片清單（Vertical Card List），直觀展示各組代表色彩、組別名稱與劑量標籤，並標示當前指派狀態（Checkmark）。使用者單擊卡片即透過事件觸發直接套用並關閉彈窗，新繪製與網格生成之小區全面預設為「未施藥對照 (CK)」，杜絕繁瑣輸入與多餘點擊確認。

### 浮動面板自由拖曳與圓形浮動收合架構 (Draggable Floating Panel & Circle Collapse Architecture)
- [MDN Web Docs - Pointer Events API](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events)
- [Vue.js 官方文件 - 響應式基礎 (Reactivity Fundamentals)](https://vuejs.org/guide/essentials/reactivity-fundamentals.html)
- [Vue.js 官方文件 - 內建組件 Transition (Transitions)](https://vuejs.org/guide/built-ins/transition.html)
- [W3C CSS Transforms 規範 (Translate 2D)](https://www.w3.org/TR/css-transforms-1/)
- [Nielsen Norman Group - Window and Panel Management in Web Applications](https://www.nngroup.com/articles/modal-nonmodal-dialog/)
- **採用架構**：在 `PlotToolbar.vue` 中將網格配置面板設計為非模態自由浮動視窗，透過 Pointer Events (`pointerdown`, `pointermove`, `pointerup`) 實作標題列平滑拖曳，結合 `Math.min`/`Math.max` 嚴格限制於瀏覽器視窗可視範圍（Viewport Clamping）；提供最小化切換狀態，收合時平滑縮小為紫色網格圓形按鈕（Floating Action Pill/Button），點擊可就地展開還原；網格模式重新開啟時自動重置回工具列左側初始停靠位置。

### 情境卡片極簡整合與色彩選擇器偽裝架構 (Scenario Card Streamlining & Disguised Color Swatch Architecture)
- [MDN Web Docs - input type="color" 規範與自訂樣式](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/color)
- [Vue.js 官方文件 - 表單輸入綁定 (Form Input Bindings)](https://vuejs.org/guide/essentials/forms.html)
- [Tailwind CSS 官方文件 - Arbitrary Variants 與偽元素樣式](https://tailwindcss.com/docs/hover-focus-and-other-states#pseudo-elements)
- [Tailwind CSS 官方文件 - Border Radius 與 Sizing](https://tailwindcss.com/docs/border-radius)
- [Nielsen Norman Group - Form Design Guidelines (減少表單冗贅元素)](https://www.nngroup.com/articles/form-design-placeholders/)
- **採用架構**：在 `ProjectScenarioCard.vue` 徹底移除卡片頂部無操作價值的靜態組別徽章標籤（「對照組 (CK)」與「處理組」），將輸入欄位直接上提與色塊並列，減少卡片高度與版面雜訊；針對 HTML5 原生 `<input type="color">` 於不同瀏覽器之內部陰影、邊框與黑邊差異，採用外層自訂色塊封裝（`size-4 rounded shadow-xs border border-border/50 relative overflow-hidden cursor-pointer`）並疊加透明原生選色器（`absolute inset-0 opacity-0`），達成處理組與對照組色塊外觀完全一致的無縫選色體驗。

### 小區幾何縮放與頂點控制把手架構 (Plot Geometry Resizing & Vertex Handle Control Architecture)
- [W3C Canvas 2D 渲染規範 (CanvasRenderingContext2D: arc, stroke, fill)](https://www.w3.org/TR/2dcontext/)
- [MDN Web Docs - MouseEvent 與座標轉換](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent)
- [Nielsen Norman Group - Direct Manipulation and Handle Affordances](https://www.nngroup.com/articles/direct-manipulation/)
- **採用架構**：在 `PlotCanvasOverlay.vue` 中將小區幾何縮放與頂點微調控制收斂於「選取與檢視模式」。選取小區時繪製高對比之圓形頂點把手（白色填充圓配藍色描邊），透過歐幾里得距離命中判定（`Math.hypot`）捕捉頂點拖曳動作（`draggingVertexIndex`），即時計算正規化相對座標（0.0 ~ 1.0）並發送更新事件；切換至「手動繪製模式」或網格時自動隱藏把手並清空選取，確保模式職責解耦且避免交互誤觸。

### 雙線性網格整體平移與剛體邊界約束架構 (Bilinear Grid Rigid Translation & Boundary Clamping Architecture)
- [W3C Canvas 2D 規範 - CanvasRenderingContext2D.isPointInPath()](https://www.w3.org/TR/2dcontext/#dom-context-2d-ispointinpath)
- [MDN Web Docs - CanvasRenderingContext2D.isPointInPath() 幾何命中判定](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/isPointInPath)
- [MDN Web Docs - CSS cursor 樣式與使用者反饋 (cursor: move / grabbing)](https://developer.mozilla.org/en-US/docs/Web/CSS/cursor)
- [W. Randolph Franklin - PNPOLY: Point Inclusion in Polygon Test](https://wrfranklin.org/Research/Short_Notes/pnpoly.html)
- [MDN Web Docs - Math.min / Math.max 數值區間夾持 (Clamping)](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Math/min)
- **採用架構**：在 `PlotCanvasOverlay.vue` 與 `usePlots.ts` 實現雙線性網格整體平移與剛體邊界保護。在網格配置模式下（非消除單元格狀態），透過 `Path2D` 建立母框多邊形並以 `isPointInPath` 判定滑鼠是否位於四角母框內部；當非角點命中時啟用整體拖曳（`isDraggingWholeGrid`），將滑鼠懸停游標設為 `move`、拖曳中設為 `grabbing`。平移量透過全網格 4 角點之極值座標（minX, maxX, minY, maxY）進行剛體平移量約束（`-minX <= dx <= 1 - maxX` 與 `-minY <= dy <= 1 - maxY`），觸及邊界時停止該軸向移動，防止網格幾何變形扭曲或逸出影像，滑鼠移動時實時動態重算渲染雙線性網格。

### 跨站請求防護與輕量安全中介層 (CSRF Protection & Sec-Fetch Metadata)
- [W3C Fetch Metadata Request Headers](https://www.w3.org/TR/fetch-metadata/)
- [MDN Web Docs - Sec-Fetch-Site 標頭規範](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Sec-Fetch-Site)
- [OWASP Cross-Site Request Forgery (CSRF) Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Starlette Middleware 官方文件](https://www.starlette.io/middleware/)
- [FastAPI 依賴注入 (Dependencies)](https://fastapi.tiangolo.com/tutorial/dependencies/)
- **採用架構**：以無狀態的 `SecurityMiddleware` 替代原先複雜的訪客狀態中介層，依據 `Sec-Fetch-Site` 與 `Origin` 標頭驗證請求來源，在零 Cookie、無 Session 狀態開銷下防範跨站惡意寫入；後端 `TaskRepository` 與用例注入徹底解耦 `owner_id`，達成全站專案全域共享。

### Element Plus 風格暗黑行內編輯資料表格架構 (Element Plus Dark Theme Inline Editable Table Architecture)
- [Element Plus Table 組件官方文件 (Table Component)](https://element-plus.org/en-US/component/table.html)
- [Tailwind CSS 官方文件 - Tables (Border Collapse & Table Layout)](https://tailwindcss.com/docs/table-layout)
- [W3C WAI-ARIA 表格設計模式 (Table Design Pattern)](https://www.w3.org/WAI/ARIA/apg/patterns/table/)
- [Nielsen Norman Group - Table Design UX Patterns (資料表格與行內編輯最佳實踐)](https://www.nngroup.com/articles/table-design/)
- **採用架構**：在 `ProjectScenarioCard.vue` 推翻原卡片網格佈局，採用 Element Plus 暗黑極簡資料表格規範。規劃標準四欄架構（色彩標記、藥劑名稱、施用劑量、操作），首列永久固定為「對照組 (CK)」，劑量欄顯示「— (不適用)」且操作欄無按鈕；處理組支援行內直接輸入與 Enter/Tab 鍵自動聚焦跳格；操作欄提供紅色實心/微淡紅底「刪除」按鈕（Destructive Action）；視覺上採用深色底搭配極簡水平細底線分隔（`border-b border-border/40`）與行懸停微光高亮（`hover:bg-muted/20`），杜絕垂直格線與斑馬紋雜訊，達成緊湊專業的田間試驗情境設定體驗。

### 雙線性網格行列數上限擴展與 Canvas 渲染架構 (Bilinear Grid Capacity & Canvas Rendering Architecture)
- [MDN Web Docs - <input type="number"> 元素與限制規範](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/number)
- [Vue.js 官方文件 - 表單輸入綁定 (Form Input Bindings)](https://vuejs.org/guide/essentials/forms.html)
- [W3C HTML5 Specification - The number state (type=number)](https://www.w3.org/TR/html52/sec-forms.html#number-state-typenumber)
- [W3C Canvas 2D Context - Path rendering performance](https://www.w3.org/TR/2dcontext/)
- **採用架構**：在 `PlotToolbar.vue` 中將網格配置的「列數 (Rows)」與「行數 (Cols)」之 HTML5 `<input type="number">` 之 `max` 屬性與 `@input` 邊界限制（`Math.min`）同步由 20 提高至 50（允許區間 1 ~ 50）；在 50 × 50（最高 2,500 單元格）配置下，利用 HTML5 Canvas 2D 輕量逐路徑渲染與雙線性插值演算法完成純前端即時預覽與批次建立，免除繁瑣警告彈窗中斷，兼顧操作彈性與高吞吐交互效能。

### 畫布小區多選、框選與批次特徵套用架構 (Canvas Multi-Selection & Batch Feature Application Architecture)
- [W3C Pointer Events 規範](https://www.w3.org/TR/pointerevents/)
- [MDN MouseEvent: shiftKey & ctrlKey 屬性](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent)
- [MDN Canvas API 幾何圖形與碰撞檢測 (2D Collision Detection)](https://developer.mozilla.org/en-US/docs/Games/Techniques/2D_collision_detection)
- [計算幾何：多邊形質心演算法 (Centroid of Polygon)](https://en.wikipedia.org/wiki/Centroid#Of_a_polygon)
- [Vue 3 官方文件 - 響應式基礎 (Reactivity Fundamentals)](https://vuejs.org/guide/essentials/reactivity-fundamentals.html)
- **採用架構**：
  1. **多選狀態收斂**：在 `usePlots.ts` 將原 `selectedPlotNumber: number | null` 擴展為支援複數小區的 `selectedPlotNumbers: number[]`，在單選與多選間保持無縫向後相容。
  2. **空白處橡皮筋框選 (Rubber-band Box Selection)**：在檢視模式下，滑鼠左鍵於畫布空白處拖曳時動態繪製半透明虛線選取框；計算各小區之多邊形質心（Centroid），中心點落入框選矩形者即納入選取。
  3. **組合鍵增量選取 (Modifier Key Toggle)**：支援按住 `Shift` 或 `Ctrl` 鍵點選個別小區，動態增減選取集合；單擊空白處則快速清空選取集合。
  4. **視覺降噪與頂點把手抑制**：單選時保留頂點拖曳手柄供精細調整；多選時自動隱藏把手、僅維持亮色外框，並支援批次平移、批次複製與批次刪除。
  5. **零冗餘批次特徵套用**：雙擊任一已選小區直接開啟 `PlotTreatmentDialog`，標題感知多選小區個數；若多小區組別一致則預設勾選，異組別不勾選；點選任意目標組別立即一次將所有選中小區之處理組別與劑量更新完成並自動關閉彈窗。

### 全步驟左上角全域常駐 HUD 與極簡情境卡片架構 (Global Step HUD & Non-Collapsible Scenario Architecture)
- [Tailwind CSS 官方文件 - Top / Right / Bottom / Left 定位規範](https://tailwindcss.com/docs/top-right-bottom-left)
- [Tailwind CSS 官方文件 - Backdrop Filter / Blur (毛玻璃特效)](https://tailwindcss.com/docs/backdrop-blur)
- [Tailwind CSS 官方文件 - Typography & Font Size (字級階層)](https://tailwindcss.com/docs/font-size)
- [Radix Vue 官方文件 - Card 組件規範](https://www.radix-vue.com/)
- [Vue.js 官方文件 - 計算屬性 (Computed Properties)](https://vuejs.org/guide/essentials/computed.html)
- **採用架構**：
  1. **全步驟全域常駐 HUD**：將原步驟 1/3/4 的懸浮專案資訊膠囊提升至專案工作區頂層父層（`top-4 left-4 z-20`），各步驟動態渲染一致之「步驟名稱徽章」（步驟 1：航拍正射、步驟 2：試驗情境、步驟 3：小區標註、步驟 4：光譜分析），徹底杜絕跨步驟切換時標題文字與專案資訊之位置跳動與字級割裂。
  2. **情境特徵卡片永久展開與極簡操作列**：廢除 `Collapsible` 折疊組件與收合開關，移除「專案試驗情境特徵」重複標題列，頂部直接整合為組別操作列（左側「試驗組別」標籤與「已儲存特徵/未儲存變更」狀態徽章，右側「+ 新增組別」按鈕）；步驟 2 容器配置 `pt-20` 上方內距，確保卡片內容與左上角常駐 HUD 完美避障。











