import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Conversation:
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    data: dict = field(default_factory=dict)
