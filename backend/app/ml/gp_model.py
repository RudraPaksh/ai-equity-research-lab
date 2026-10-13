from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.gaussian_process import (
    GaussianProcessRegressor,
)

from sklearn.gaussian_process.kernels import (
    ConstantKernel,
    RBF,
    WhiteKernel,
)

from sklearn.preprocessing import StandardScaler


GP_FEATURES = [
    "return_1",
    "return_5",
    "return_20",
    "volatility_20",
    "volume_ratio",
    "rsi14",
    "macd_hist",
    "drawdown",
]


def train_gp(
    df: pd.DataFrame,
    target: str,
):
    data = df[
        GP_FEATURES + [target]
    ].replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna()

    if len(data) < 200:
        raise ValueError(
            "Not enough observations for GP model"
        )

    # Keep GP manageable.
    data = data.tail(800)

    X = data[GP_FEATURES].values
    y = data[target].values

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(X)

    kernel = (
        ConstantKernel(
            1.0,
            (1e-3, 1e3),
        )
        * RBF(
            length_scale=1.0,
            length_scale_bounds=(
                1e-2,
                1e2,
            ),
        )
        + WhiteKernel(
            noise_level=0.1,
            noise_level_bounds=(
                1e-5,
                10,
            ),
        )
    )

    model = GaussianProcessRegressor(
        kernel=kernel,
        normalize_y=True,
        n_restarts_optimizer=2,
        random_state=42,
    )

    model.fit(
        X_scaled,
        y,
    )

    return model, scaler