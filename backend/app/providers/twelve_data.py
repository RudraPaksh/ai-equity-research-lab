from typing import Any

from ..config import settings
from .http import get_json


BASE = "https://api.twelvedata.com"


async def search_symbols(
    query: str,
    outputsize: int = 20,
) -> list[dict[str, Any]]:

    if not settings.twelve_data_api_key:
        raise RuntimeError(
            "TWELVE_DATA_API_KEY is not configured"
        )

    query = query.strip()

    if not query:
        return []

    data, _ = await get_json(
        f"{BASE}/symbol_search",
        {
            "symbol": query,
            "outputsize": min(outputsize, 120),
            "apikey": settings.twelve_data_api_key,
        },
        provider="twelve_data",
        ttl=3600,
    )

    if data.get("status") == "error":
        raise RuntimeError(
            data.get(
                "message",
                "Twelve Data symbol search error",
            )
        )

    return data.get("data", [])


async def get_daily(
    symbol: str,
    exchange: str | None = None,
    mic_code: str | None = None,
    outputsize: int = 500,
):
    if not settings.twelve_data_api_key:
        raise RuntimeError(
            "TWELVE_DATA_API_KEY is not configured"
        )

    params = {
        "symbol": str(symbol).strip().upper(),
        "interval": "1day",
        "outputsize": int(outputsize),
        "apikey": settings.twelve_data_api_key,
    }

    if exchange is not None:
        params["exchange"] = str(exchange).strip().upper()

    if mic_code is not None:
        params["mic_code"] = str(mic_code).strip().upper()

    print(
        "Twelve Data request:",
        {
            "symbol": params["symbol"],
            "exchange": params.get("exchange"),
            "mic_code": params.get("mic_code"),
            "interval": params["interval"],
            "outputsize": params["outputsize"],
        }
    )

    data, _ = await get_json(
        f"{BASE}/time_series",
        params,
        provider="twelve_data",
        ttl=300,
    )

    if data.get("status") == "error":
        raise RuntimeError(
            data.get(
                "message",
                "Twelve Data error",
            )
        )

    return data