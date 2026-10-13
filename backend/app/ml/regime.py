import numpy as np
import pandas as pd


def detect_regime(
    df: pd.DataFrame,
):
    close = df["close"]

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()

    returns = close.pct_change()

    volatility = (
        returns
        .rolling(20)
        .std()
        * np.sqrt(252)
    )

    latest = df.index[-1]

    price = float(
        close.iloc[-1]
    )

    v20 = float(
        volatility.iloc[-1]
    )

    trend_score = 0

    if price > sma20.iloc[-1]:
        trend_score += 1

    if price > sma50.iloc[-1]:
        trend_score += 1

    if price > sma200.iloc[-1]:
        trend_score += 1

    if trend_score >= 3:
        trend = "bullish"

    elif trend_score <= 1:
        trend = "bearish"

    else:
        trend = "mixed"

    if v20 > 0.45:
        volatility_regime = "high"

    elif v20 < 0.20:
        volatility_regime = "low"

    else:
        volatility_regime = "normal"

    return {
        "timestamp": str(latest),
        "trend": trend,
        "volatility": volatility_regime,
        "annualized_volatility": v20,
    }