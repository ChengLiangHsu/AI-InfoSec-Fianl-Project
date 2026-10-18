# 需求規格書：成果影像下拉選單切換光譜圖片

- **Issue 主題**：`spectral-image-dropdown`
- **狀態**：訪談完成已對齊 (Aligned)
- **建立日期**：2026-10-18

---

## 1. 需求背景 (Background)
目前航拍影像成果卡片僅固定展示拼接完成之 RGB 正射影像 (`/api/odm-task-orthophoto/{id}`)。後端系統已經實作多光譜植生演算法計算接口：
- `GET /api/odm-task-formulas`：回傳系統支援的 3 波段 RGB 植生指標清單（包含公式 ID、表達式、說明等）。
- `GET /api/odm-task-spectral/{id}?formula={algo_id}`：依選定指標動態產生或回傳光譜分析圖。

為了讓使用者能直接在專案成果頁面即時切換、對比不同植生指標（如 VARI 等）之航拍分析結果，需在成果卡片標題列加入下拉選單，並優化介面排版。

---

## 2. 訪談對齊結論 (Interview Alignment & Decisions)
經由 `/grill-me` 互動訪談，與使用者確認之關鍵決策如下：

| 項次 | 決策項目 | 決策結果 | 補充說明 |
| :--- | :--- | :--- | :--- |
| 1 | **選單擺放位置** | 成果卡片標題列（右上角） | 替換原有動作按鈕位置，保持版面緊湊俐落 |
| 2 | **原有功能按鈕處置** | **完全移除** | 移除「開啟原圖」與「下載影像」兩個按鈕 |
| 3 | **選項資料來源** | 動態呼叫後端 API | 呼叫 `GET /api/odm-task-formulas` 取得所有 RGB 演算法 |
| 4 | **預設選項** | 「原始正射影像 (RGB)」 | 進入專案或切換專案時，預設顯示原始 RGB 影像 |
| 5 | **選單元件風格** | 使用現有 `Select` 元件 | 採用 `@/components/ui/select` (shadcn-vue)，符合現有設計語彙 |

---

## 3. 功能規格與技術細節 (Functional Specifications)

### 3.1 下拉選單資料來源與選項格式
1. 於元件載入或掛載時（`onMounted`），呼叫 `/api/odm-task-formulas`。
2. 選單選項（Options）資料結構：
   - 第一個固定選項：
     - `id`: `""` 或 `"rgb"`
     - `name`: `"原始正射影像 (RGB)"`
   - 後端回傳之演算法清單：
     - `id`: 演算法代碼（如 `"VARI"`, `"GLI"` 等）
     - `name`: 顯示演算法 ID 或搭配說明（如 `"VARI"`）
3. 預設選取：`"rgb"`（原始正射影像）。

### 3.2 影像網址動態切換
- 當 `currentFormula === 'rgb'` 時：
  - 影像 URL：`/api/odm-task-orthophoto/${selectedProject.id}`
- 當 `currentFormula !== 'rgb'` 時：
  - 影像 URL：`/api/odm-task-spectral/${selectedProject.id}?formula=${currentFormula}`

### 3.3 介面調整 (UI/UX)
1. **移除舊按鈕**：
   - 移除卡片 Header 右側之「開啟原圖」按鈕 (`<Button as-child variant="outline">`)。
   - 移除卡片 Header 右側之「下載影像」按鈕 (`<Button as-child variant="default">`)。
2. **新增 Select 下拉選單**：
   - 擺放於 CardHeader 右側操作區。
   - 寬度設定適中（例如 `w-[200px]` 或 `w-[220px]`），兼顧行動端/桌機版面。
3. **載入狀態 (Loading State)**：
   - 由於光譜圖可能需要後端即時計算，切換選項或圖片載入期間，需有 Loading 指示（如微型 Spinner 或透明度轉場），避免畫面閃爍或使用者以為點擊無效。

### 3.4 生命週期與專案切換連動 (Project Switch)
- 當使用者在側邊欄切換選取的專案 (`selectedProject`) 時，自動將 `currentFormula` 重設為 `"rgb"`。

---

## 4. 驗收標準 (Definition of Done)
- [ ] 成果卡片標題列成功移除「開啟原圖」與「下載影像」按鈕。
- [ ] 標題列右側成功呈現下拉選單（Select），並包含「原始正射影像 (RGB)」與後端 API 回傳之演算法。
- [ ] 切換至各光譜演算法時，影像預覽區能正確載入並顯示對應光譜圖檔。
- [ ] 切換回「原始正射影像 (RGB)」時，正確還原顯示原始正射圖。
- [ ] 切換不同專案時，下拉選單自動重設為預設的原始 RGB 影像。
- [ ] 前端 TypeScript 型別無錯誤，介面樣式無跑版。
