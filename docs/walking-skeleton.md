# Walking Skeleton 決策紀錄

來源：grill-with-docs 討論。詞彙定義見 [GLOSSARY.md](../GLOSSARY.md)。

| 項目 | 結論 |
| :--- | :--- |
| 範圍 | 前後端最小聊天介面，**不串接 AI**，只驗證能聊天；程式碼越少越好；暫不處理田間試驗領域 |
| 回應 | 固定一句話的假回應，由假 gateway 產生；一次回傳 JSON，不串流 |
| 實作順序 | 由內往外：entity → usecase → adapter → CORS → 前端（#2 到 #7） |
| Entity | `Message`、`Conversation` 為實際的 frozen dataclass（`src/entity/`） |
| 分層 | port 放 `usecase/`；`adapter/` 下有 gateway（實作 port）、controller（呼叫 usecase）、presenter（回應格式） |
| 狀態 | 後端無狀態，前端每次送出完整訊息，不存資料庫 |
| 前端 | 一個聊天頁，AI Elements + `fetch`，取代 `HelloWorld`（不串流，不用 `ai` 的 `Chat`） |
| CORS | FastAPI `CORSMiddleware`，只允許 `http://localhost:5173` |
| 現有程式 | `src/main.py` 範本可直接取代 |
| 測試 | 暫不寫自動化測試，以 `curl` 與瀏覽器手動驗證 |

## 完成標準

1. 後端啟動後，`POST /api/conversation` 回傳假回應。
2. 瀏覽器可送出問題並看到假回應，可持續追問，重新整理後清空。

## 延後至 #8

- Gemini（`GEMINI_MODEL`、`GOOGLE_API_KEY`、`load_dotenv()`、`.env` 不被追蹤）、`TestModel`、Tool `add_numbers`、串流（Vercel AI 協定）。
- 規則：Agent 只能引用 Tool 的回傳結果，不能自行產生數值。
- 待決：是否使用 `VercelAIAdapter`（尚未決定）。

## ADR

暫不建立。
