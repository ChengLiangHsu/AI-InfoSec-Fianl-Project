# UAV Trial Assessor

AI Agent 對話平台：使用者與 Agent 交談，Agent 透過確定性工具取得結果後回覆。

## Language

**Message**:
對話中的一則發言，具有角色（使用者或 Agent）與內容。
_Avoid_: Chat, prompt, utterance

**Conversation**:
Message 的有序列表。
_Avoid_: Session, thread, chat history

**Tool**:
Agent 可呼叫、輸出確定的外部能力；Agent 回覆中的數值只能引用 Tool 的回傳結果。
_Avoid_: Function, plugin, skill
