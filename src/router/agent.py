import os
from dotenv import load_dotenv

load_dotenv()

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent, ModelResponse, TextPart

from src.adapter.controller.conversation import (
    CreateConversationController,
    ReadConversationController,
    UpdateConversationController,
)
from src.adapter.gateway import SQLiteConversationRepository
from src.usecase.conversation import CreateConversationUsecase, ReadConversationUsecase
from src.entity import (
    MessageReasoning,
    MessageSource,
    MessageTool,
    MessageVersion,
    Sender,
)

model = os.getenv("PYDANTIC_AI_MODEL", "google:gemini-3.7-flash")
agent = Agent(model)
# SessionDep = Annotated[Session, Depends(get_session, scope="function")]


router = APIRouter(prefix="/agent", tags=["代理人"])


# create_conversation_controller = CreateConversationController(
#     usecase=CreateConversationUsecase(
#         repo=SQLiteConversationRepository(get_session())
#     )
# )

# read_conversation_controller = ReadConversationController(
#     usecase=ReadConversationUsecase(
#         repo=SQLiteConversationRepository(get_session())
#     )
# )

# update_conversation_controller = UpdateConversationController(
#     usecase=UpdateConversationUsecase(
#         repo=SQLiteConversationRepository(get_session())
#     )
# )


class AskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    key: str
    from_: Sender = Field(alias="from")
    versions: list[MessageVersion]
    sources: list[MessageSource] | None = None
    reasoning: MessageReasoning | None = None
    tools: list[MessageTool] | None = None


# @router.post("/ask", response_class=StreamingResponse)
# async def ask(request: AskRequest) -> AsyncIterable[str]:
#     async def stream_messages(conversation_id: str):
#         """串流 JSON 格式訊息，以利前端即時顯示"""


#         # 取得對話歷史，作為上下文傳入代理人

#         conversation = await read_conversation_controller.handle(conversation_id)
#         history = conversation.data["context"] or []

#         # 執行代理人，並傳入使用者訊息與對話歷史

#         async with agent.run_stream(prompt, message_history=history) as result:
#             async for text in result.stream_output(debounce_by=0.01):
#                 # 轉換為 JSON 格式的回應

#                 m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp)

#                 yield json.dumps(to_chat_message(m)).encode("utf-8") + b"\n"

#         # 新增新訊息（例如使用者訊息和代理人回應）到資料庫中

#         history.append(result.new_messages_json())
#         update_conversation_controller.handle(conversation_id=conversation_id, data={"context": history})

#     conversation_id = create_conversation_controller.handle()
#     return StreamingResponse(stream_messages(conversation_id), media_type="text/plain")
