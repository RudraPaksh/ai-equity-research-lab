import yfinance as yf
import pandas as pd


def get_daily(symbol: str, outputsize: int = 500) -> pd.DataFrame:
    symbol = symbol.strip().upper()

    ticker = yf.Ticker(symbol)

    df = ticker.history(
        period="2y",
        interval="1d",
        auto_adjust=False,
    )

    if df.empty:
        raise RuntimeError(
            f"No Yahoo Finance market data found for {symbol}"
        )

    df = df.reset_index()

    # Normalize column names
    df.columns = [
        str(column).lower().replace(" ", "_")
        for column in df.columns
    ]

    rename_map = {
        "date": "datetime",
        "datetime": "datetime",
    }

    df = df.rename(columns=rename_map)

    required = [
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise RuntimeError(
            f"Yahoo Finance missing columns: {missing}"
        )

    df["datetime"] = pd.to_datetime(df["datetime"])

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(subset=["close"])

    return df.tail(outputsize).copy()