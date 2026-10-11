# UAV Trial Assessor

AI Agent 對話平台：使用者與 Agent 交談，Agent 透過確定性工具取得結果後回覆。

## Language

**Message**:
一則發言，欄位同前端 `MessageType`：`key`、發話者 `from`（`user` 或 `assistant`）、`versions`（每版含 `id`、`content`），以及僅 assistant 才有的選填 `sources`、`reasoning`、`tools`。`key` 與 `id` 為 nanoid：user Message 由前端產生，assistant Message 由後端產生。
Python 欄位名為 `from_`（`from` 為保留字），對外 JSON key 為 `from`。
最小目標為單次問答：前端送出一則 user Message，後端回傳一則 assistant Message。
_Avoid_: Chat, prompt, utterance, role, Conversation（暫不採用）

**Tool**:
Agent 可呼叫、輸出確定的外部能力；Agent 回覆中的數值只能引用 Tool 的回傳結果。
_Avoid_: Function, plugin, skill
