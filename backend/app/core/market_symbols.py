def yahoo_symbol(
    symbol: str,
    exchange: str | None = None,
    country: str | None = None,
) -> str:

    symbol = symbol.strip().upper()

    exchange = (
        exchange.strip().upper()
        if exchange
        else ""
    )

    country = (
        country.strip().upper()
        if country
        else ""
    )

    # Indian NSE equities
    if exchange == "NSE" or country == "INDIA":
        return f"{symbol}.NS"

    # Indian BSE
    if exchange == "BSE":
        return f"{symbol}.BO"

    # Otherwise assume US/standard Yahoo symbol
    return symbol