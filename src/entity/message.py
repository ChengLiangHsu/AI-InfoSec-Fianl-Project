from dataclasses import dataclass
from typing import Literal

Role = Literal["user", "agent"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str
