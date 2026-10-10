from src.entity.message import Message


def present_reply(message: Message) -> dict:
    return {"result": True, "data": {"message": {"role": message.role, "content": message.content}}}
