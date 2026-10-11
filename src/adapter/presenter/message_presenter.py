from dataclasses import asdict

from src.entity.message import Message


def present_reply(message: Message) -> dict:
    data = asdict(message)
    data["from"] = data.pop("from_")
    return {"result": True, "data": {"message": data}}
