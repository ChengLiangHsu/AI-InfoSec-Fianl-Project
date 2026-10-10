# Walking Skeleton 決策紀錄

來源：grill-with-docs 討論。詞彙定義見 [GLOSSARY.md](../GLOSSARY.md)。

| 項目 | 結論 |
| :--- | :--- |
| 範圍 | 前後端最小 AI Agent 聊天介面，程式碼越少越好；暫不處理田間試驗領域 |
| 規則 | Agent 只能引用 Tool 的回傳結果，不能自行產生數值 |
| 分層 | port 放 `usecase/`；`adapter/` 下有 gateway（實作 port）、controller（呼叫 usecase）、presenter（回應格式） |
| 串流 | 加入串流（Vercel AI 協定） |
| 狀態 | 後端無狀態，前端每次送出完整訊息，不存資料庫 |
| 模型 | Gemini；`GEMINI_MODEL`（預設 `gemini-2.5-flash`）與 `GOOGLE_API_KEY` 由 `load_dotenv()` 載入；`.env` 加入 `.gitignore`；沒有 key 時用 `TestModel` |
| 工具 | 一個 `add_numbers(a, b)` |
| 前端 | 一個聊天頁，AI Elements + `ai` 的 `Chat`，取代 `HelloWorld` |
| CORS | FastAPI `CORSMiddleware`，只允許 `http://localhost:5173` |
| 現有程式 | `src/main.py` 範本可直接取代 |

## 完成標準

1. 沒設 key 時，用 `TestModel` 讓後端回應 `/api/chat`。
2. 設了 `GOOGLE_API_KEY` 時，在瀏覽器問「3 加 5 是多少」，畫面顯示工具呼叫與串流回答。
3. `.env` 沒被 git 追蹤。

不寫自動化測試，除非另外要求。

## 待決（實作時提醒）

- 是否以 `VercelAIAdapter` 作為 controller 與 presenter 的實作。
- 若是，`Message` 與 `Conversation` 是否仍需成為實際類別，或只保留為詞彙。
  - 依據：`.venv\Lib\site-packages\pydantic_ai\ui\vercel_ai\_adapter.py` 存在該 adapter。

## ADR

暫不建立。上述待決項決定後再評估。
