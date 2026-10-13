from ..config import settings
from .http import get_json

BASE = "https://financialmodelingprep.com/stable"


def _params(symbol):
    if not settings.fmp_api_key:
        raise RuntimeError("FMP_API_KEY is not configured")

    return {
        "symbol": symbol.strip().upper(),
        "apikey": settings.fmp_api_key,
    }


async def _get(path, symbol):
    data, _ = await get_json(
        f"{BASE}/{path}",
        _params(symbol),
        provider="fmp",
        ttl=3600,
    )

    if isinstance(data, dict):
        error_message = (
            data.get("Error Message")
            or data.get("error")
            or data.get("message")
        )

        if error_message:
            raise RuntimeError(
                f"FMP {path} error: {error_message}"
            )

    if data is None:
        raise RuntimeError(
            f"FMP {path} returned no data for {symbol}"
        )

    return data


async def profile(symbol):
    return await _get("profile", symbol)


async def income(symbol):
    return await _get("income-statement", symbol)


async def balance(symbol):
    return await _get("balance-sheet-statement", symbol)


async def cashflow(symbol):
    return await _get("cash-flow-statement", symbol)


async def ratios(symbol):
    return await _get("ratios", symbol)


async def key_metrics(symbol):
    return await _get("key-metrics", symbol)