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

### 唯一對照組互斥狀態與防呆保護架構 (Mutually Exclusive Single Control Group & Defensive Architecture)
- [Vue.js 官方文件 - 響應式基礎 (Reactivity Fundamentals)](https://vuejs.org/guide/essentials/reactivity-fundamentals.html)
- [W3C WAI-ARIA Radio Group 互斥單選設計模式 (Radio Group Pattern)](https://www.w3.org/WAI/ARIA/apg/patterns/radio/)
- [EPPO Standard PP 1/152(4)：植保產品藥效評估試驗設計與分析標準指南 (對照組基準要求)](https://pp1.eppo.int/standards/pp1-152-4)
- [Nielsen Norman Group - Preventing User Errors (防呆設計原則)](https://www.nngroup.com/articles/user-interface-errors/)
- **採用架構**：在 `ProjectScenarioCard.vue` 實作單選互斥模式（Radio-like Mutually Exclusive Pattern），將處理組切換為對照組時自動降級原對照組，確保全專案情境始終維持唯一 CK 基準；對照組卡片條件隱藏刪除按鈕（`v-if="!cat.is_control"`）杜絕誤刪；載入與後端儲存時加入資料歸一化校正，符合 EPPO 田間試驗唯一基準規範與防呆防禦架構。



