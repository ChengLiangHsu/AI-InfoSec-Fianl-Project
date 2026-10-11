from dataclasses import dataclass


@dataclass(frozen=True)
class AIModel:
    name: str
    provider: str
