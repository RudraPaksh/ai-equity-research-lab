from __future__ import annotations

import numpy as np


HORIZONS = [
    "1d",
    "5d",
    "20d",
]


def build_horizon_summary(
    forecasts: dict,
):
    result = {}

    for horizon in HORIZONS:

        forecast = forecasts.get(
            horizon
        )

        if not forecast:
            continue

        expected_return = float(
            forecast["expected_return"]
        )

        uncertainty = float(
            forecast["uncertainty"]
        )

        confidence_ratio = (
            abs(expected_return) /
            max(uncertainty, 1e-8)
        )

        result[horizon] = {
            "expected_return":
                expected_return,

            "uncertainty":
                uncertainty,

            "signal_strength":
                float(
                    np.tanh(
                        confidence_ratio
                    )
                ),

            "direction": (
                "up"
                if expected_return > 0
                else "down"
                if expected_return < 0
                else "flat"
            ),
        }

    return result