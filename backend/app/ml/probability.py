from __future__ import annotations

import numpy as np


def probability_from_returns(
    predicted_return: float,
    uncertainty: float,
    neutral_band: float = 0.001,
):
    """
    Converts a predicted return distribution
    into up / sideways / down probabilities.

    This is NOT a guarantee of future movement.
    """

    sigma = max(
        abs(uncertainty),
        1e-8,
    )

    mu = predicted_return

    # Approximate probability using
    # a normal distribution.

    from math import erf, sqrt

    def normal_cdf(x):
        return 0.5 * (
            1 +
            erf(
                x / sqrt(2)
            )
        )

    p_down = normal_cdf(
        (-neutral_band - mu) / sigma
    )

    p_up = 1 - normal_cdf(
        (neutral_band - mu) / sigma
    )

    p_sideways = max(
        0.0,
        1.0 -
        p_down -
        p_up,
    )

    total = (
        p_up +
        p_sideways +
        p_down
    )

    return {
        "up": p_up / total,
        "sideways": p_sideways / total,
        "down": p_down / total,
    }