from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class ProviderResult:
    provider: str
    endpoint: str
    fetched_at: str
    source_timestamp: str | None
    data: Any
    cached: bool = False

    def to_dict(self):
        return asdict(self)
