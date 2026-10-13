from abc import ABC, abstractmethod

class ProviderError(RuntimeError):
    pass

class MarketProvider(ABC):
    name = "base"
    @abstractmethod
    async def daily(self, symbol: str, outputsize: int = 500): ...
