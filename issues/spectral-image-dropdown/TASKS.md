# 待辦任務清單：成果影像下拉選單切換光譜圖片

- [x] 任務 1：[前端/介面定義] 於 `frontend/src/App.vue` 定義 `Formula` 介面，並引入 shadcn-vue `Select` 相關元件（已完成介面定義與元件導入，通過型別檢查）
- [x] 任務 2：[前端/狀態管理] 於 `frontend/src/App.vue` 宣告 `formulas`、`selectedFormula`、`isImageLoading` 及動態圖片 URL 計算屬性 `currentImageUrl`（已宣告響應式狀態、計算屬性與偵聽器，通過型別檢查）
- [x] 任務 3：[前端/生命週期] 於 `frontend/src/App.vue` 掛載時非同步載入 `/api/odm-task-formulas`，並於切換專案時將選項重設為預設 `'rgb'`（已於 onMounted 載入演算法並於 watch 設置重置與載入狀態）
- [x] 任務 4：[前端/介面佈局] 於成果卡片標題列移除舊有「開啟原圖」與「下載影像」按鈕，加入 `<Select>` 下拉選單並實作影像載入遮罩（已成功替換標題列按鈕為 Select，並於預覽容器實作遮罩與 @load/@error 監聽）
- [x] 任務 5：[建置與驗證] 執行 `npm run build` 驗證 TypeScript 型別與前端生產打包，確保無編譯錯誤（已通過 Vite 與 TypeScript 編譯與打包驗證）
