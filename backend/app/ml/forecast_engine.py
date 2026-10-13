from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .features import (
    build_features,
    SUPPORTED_HORIZONS,
)

from .ensemble import (
    train_ensemble,
)

from .gp_model import (
    GP_FEATURES,
    train_gp,
)

from .probability import (
    probability_from_returns,
)

from .regime import (
    detect_regime,
)

from .multi_horizon import (
    build_horizon_summary,
)


# ============================================================
# HORIZON NEUTRAL BANDS
# ============================================================

NEUTRAL_BANDS = {
    "1d": 0.005,
    "5d": 0.010,
    "20d": 0.020,
}


# ============================================================
# HELPERS
# ============================================================

def _safe_float(value):

    if value is None:
        return None

    value = float(value)

    if not math.isfinite(value):
        return None

    return value


# ============================================================
# SINGLE HORIZON
# ============================================================

def _forecast_horizon(
    feature_df: pd.DataFrame,
    horizon: str,
):

    target = (
        f"target_return_{horizon}"
    )

    # --------------------------------------------------------
    # Ensemble
    # --------------------------------------------------------

    ensemble = train_ensemble(
        feature_df,
        target,
    )

    expected_return = float(
        ensemble[
            "ensemble_prediction"
        ]
    )

    model_disagreement = float(
        ensemble[
            "model_disagreement"
        ]
    )

    residual_std = float(
        ensemble[
            "metrics"
        ][
            "residual_std"
        ]
    )

    # --------------------------------------------------------
    # Gaussian Process
    # --------------------------------------------------------

    gp_model, gp_scaler = train_gp(
        feature_df,
        target,
    )

    gp_data = (
        feature_df[GP_FEATURES]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .dropna()
    )

    if gp_data.empty:

        raise ValueError(
            "No valid GP feature row"
        )

    current_gp = gp_data.iloc[[-1]]

    current_gp_scaled = (
        gp_scaler.transform(
            current_gp
        )
    )

    gp_mean, gp_std = (
        gp_model.predict(
            current_gp_scaled,
            return_std=True,
        )
    )

    gp_mean = float(
        gp_mean[0]
    )

    gp_std = float(
        gp_std[0]
    )

    # --------------------------------------------------------
    # Combine uncertainty
    #
    # This is deliberately labelled as an
    # uncalibrated research uncertainty estimate.
    # --------------------------------------------------------

    uncertainty = math.sqrt(
        residual_std ** 2
        + model_disagreement ** 2
        + gp_std ** 2
    )

    # --------------------------------------------------------
    # Probability distribution
    # --------------------------------------------------------

    neutral_band = (
        NEUTRAL_BANDS[horizon]
    )

    probabilities = (
        probability_from_returns(
            predicted_return=expected_return,
            uncertainty=uncertainty,
            neutral_band=neutral_band,
        )
    )

    confidence_ratio = (
        abs(expected_return)
        / max(
            uncertainty,
            1e-8,
        )
    )

    signal_strength = float(
        np.tanh(
            confidence_ratio
        )
    )

    return {

        "expected_return":
            _safe_float(
                expected_return
            ),

        "probability_up":
            _safe_float(
                probabilities["up"]
            ),

        "probability_sideways":
            _safe_float(
                probabilities["sideways"]
            ),

        "probability_down":
            _safe_float(
                probabilities["down"]
            ),

        "uncertainty":
            _safe_float(
                uncertainty
            ),

        "signal_strength":
            _safe_float(
                signal_strength
            ),

        "direction": (
            "up"
            if expected_return > 0
            else "down"
            if expected_return < 0
            else "flat"
        ),

        "components": {

            "ensemble_prediction":
                _safe_float(
                    expected_return
                ),

            "gp_expected_return":
                _safe_float(
                    gp_mean
                ),

            "gp_uncertainty":
                _safe_float(
                    gp_std
                ),

            "model_disagreement":
                _safe_float(
                    model_disagreement
                ),

            "historical_residual_std":
                _safe_float(
                    residual_std
                ),
        },

        "model_quality":
            ensemble["metrics"],
    }


# ============================================================
# FULL FORECAST
# ============================================================

def forecast(
    df: pd.DataFrame,
):

    if len(df) < 350:

        raise ValueError(
            "At least 350 daily observations are recommended "
            "for the multi-horizon research engine."
        )

    feature_df = build_features(
        df
    )

    forecasts = {}

    for horizon in SUPPORTED_HORIZONS:

        forecasts[horizon] = (
            _forecast_horizon(
                feature_df,
                horizon,
            )
        )

    regime = detect_regime(
        df
    )

    summary = (
        build_horizon_summary(
            forecasts
        )
    )

    return {

        "data_frequency":
            "1d",

        "supported_horizons":
            list(
                SUPPORTED_HORIZONS.keys()
            ),

        "regime":
            regime,

        "forecasts":
            forecasts,

        "horizon_summary":
            summary,

        "uncertainty_type":
            "uncalibrated_research_estimate",
    }