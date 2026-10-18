# 待辦任務清單：新增 AI Agent 語音功能

- [ ] 任務 1：[前端/Composable] 建立 `frontend/src/composables/useWebSpeech.ts`，封裝原生 STT (語音辨識、繁中 zh-TW、停頓偵測、空值防護) 與 TTS (語音朗讀、Markdown 標籤清洗、中斷控制)
- [ ] 任務 2：[前端/元件更新] 修改 `frontend/src/components/AskAgent.vue`，在輸入框操作列整合麥克風按鈕與錄音中脈衝視覺效果
- [ ] 任務 3：[前端/流程串接] 於 `frontend/src/components/AskAgent.vue` 串接停頓自動發送與錄音打斷 (Barge-in) 互斥機制
- [ ] 任務 4：[前端/訊息介面] 於 `frontend/src/components/AskAgent.vue` 實作 AI 串流完成後自動朗讀，並在訊息卡片加入手動朗讀/停止切換按鈕
- [ ] 任務 5：[建置與驗證] 於 `frontend` 執行 `npm run build` 驗證前端打包與 TypeScript 型別無錯誤，確保所有驗收條件均能通過
