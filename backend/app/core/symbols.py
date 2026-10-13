from typing import Any


def normalize_query(query: str) -> str:
    return " ".join(
        query.strip().upper().split()
    )


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def format_symbol_result(
    item: dict[str, Any]
) -> dict[str, Any]:

    return {
        "symbol": normalize_symbol(
            str(item.get("symbol", ""))
        ),
        "name": item.get(
            "instrument_name",
            ""
        ),
        "exchange": item.get(
            "exchange",
            ""
        ),
        "mic_code": item.get(
            "mic_code",
            ""
        ),
        "country": item.get(
            "country",
            ""
        ),
        "currency": item.get(
            "currency",
            ""
        ),
        "instrument_type": item.get(
            "instrument_type",
            ""
        ),
    }


def choose_best_result(
    query: str,
    results: list[dict[str, Any]],
) -> dict[str, Any] | None:

    if not results:
        return None

    q = normalize_query(query)

    # 1. Exact symbol match
    for item in results:
        symbol = normalize_symbol(
            str(item.get("symbol", ""))
        )

        if symbol == q:
            return item

    # 2. Exact company-name match
    for item in results:
        name = normalize_query(
            str(
                item.get(
                    "instrument_name",
                    ""
                )
            )
        )

        if name == q:
            return item

    # 3. Prefer common stock
    common_stocks = [
        item
        for item in results
        if str(
            item.get(
                "instrument_type",
                ""
            )
        ).lower()
        == "common stock"
    ]

    if common_stocks:
        return common_stocks[0]

    # 4. Fallback
    return results[0]