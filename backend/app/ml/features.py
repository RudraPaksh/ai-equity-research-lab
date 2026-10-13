from __future__ import annotations

import numpy as np
import pandas as pd


# ============================================================
# CURRENT DATA FREQUENCY
# ============================================================

DATA_FREQUENCY = "1d"

SUPPORTED_HORIZONS = {
    "1d": 1,
    "5d": 5,
    "20d": 20,
}


# ============================================================
# FEATURE COLUMNS
# ============================================================

FEATURE_COLUMNS = [
    "return_1",
    "return_2",
    "return_5",
    "return_10",
    "return_20",

    "price_vs_sma20",
    "price_vs_sma50",
    "price_vs_sma200",

    "volatility_5",
    "volatility_10",
    "volatility_20",
    "volatility_50",

    "hl_range",
    "oc_range",

    "volume_ratio",

    "momentum_5",
    "momentum_20",

    "rsi14",

    "macd",
    "macd_signal",
    "macd_hist",

    "drawdown",
]


# ============================================================
# FEATURE ENGINEERING
# ============================================================

def build_features(df: pd.DataFrame) -> pd.DataFrame:

    x = df.copy()

    x = x.sort_index()

    close = x["close"].astype(float)
    volume = x["volume"].astype(float)

    # --------------------------------------------------------
    # Returns
    # --------------------------------------------------------

    for n in [1, 2, 3, 5, 10, 20, 50]:

        x[f"return_{n}"] = close.pct_change(n)

    # --------------------------------------------------------
    # Moving averages
    # --------------------------------------------------------

    for n in [5, 10, 20, 50, 100, 200]:

        x[f"sma_{n}"] = close.rolling(n).mean()

        x[f"ema_{n}"] = close.ewm(
            span=n,
            adjust=False,
        ).mean()

    # --------------------------------------------------------
    # Trend positioning
    # --------------------------------------------------------

    x["price_vs_sma20"] = (
        close / x["sma_20"] - 1
    )

    x["price_vs_sma50"] = (
        close / x["sma_50"] - 1
    )

    x["price_vs_sma200"] = (
        close / x["sma_200"] - 1
    )

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    returns = close.pct_change()

    for n in [5, 10, 20, 50]:

        x[f"volatility_{n}"] = (
            returns.rolling(n).std()
            * np.sqrt(252)
        )

    # --------------------------------------------------------
    # Price range
    # --------------------------------------------------------

    x["hl_range"] = (
        (x["high"] - x["low"])
        / close
    )

    x["oc_range"] = (
        (x["close"] - x["open"])
        / x["open"]
    )

    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    x["volume_sma20"] = (
        volume.rolling(20).mean()
    )

    x["volume_ratio"] = (
        volume / x["volume_sma20"]
    )

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    x["momentum_5"] = (
        close / close.shift(5) - 1
    )

    x["momentum_20"] = (
        close / close.shift(20) - 1
    )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()

    avg_loss = loss.rolling(14).mean()

    rs = (
        avg_gain
        / avg_loss.replace(0, np.nan)
    )

    x["rsi14"] = (
        100
        - (100 / (1 + rs))
    )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    ema12 = close.ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False,
    ).mean()

    x["macd"] = ema12 - ema26

    x["macd_signal"] = (
        x["macd"]
        .ewm(
            span=9,
            adjust=False,
        )
        .mean()
    )

    x["macd_hist"] = (
        x["macd"]
        - x["macd_signal"]
    )

    # --------------------------------------------------------
    # Drawdown
    # --------------------------------------------------------

    rolling_max = (
        close.rolling(252).max()
    )

    x["drawdown"] = (
        close / rolling_max - 1
    )

    # --------------------------------------------------------
    # FUTURE RETURN TARGETS
    #
    # IMPORTANT:
    # Current data = DAILY.
    #
    # Therefore these are:
    # 1 trading day
    # 5 trading days
    # 20 trading days
    # --------------------------------------------------------

    for name, periods in SUPPORTED_HORIZONS.items():

        x[f"target_return_{name}"] = (
            close.shift(-periods)
            / close
            - 1
        )

    return x