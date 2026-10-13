from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.ensemble import (
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
)

from xgboost import XGBRegressor

from .features import FEATURE_COLUMNS


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_data(
    df: pd.DataFrame,
    target: str,
):
    columns = (
        FEATURE_COLUMNS
        + [target]
    )

    data = (
        df[columns]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .dropna()
    )

    X = data[FEATURE_COLUMNS]

    y = data[target]

    return X, y


# ============================================================
# MODEL FACTORY
# ============================================================

def create_models():

    return {

        "xgboost": XGBRegressor(
            n_estimators=400,
            max_depth=4,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=-1,
        ),

        "hist_gradient_boosting":
            HistGradientBoostingRegressor(
                max_iter=250,
                learning_rate=0.05,
                max_leaf_nodes=31,
                random_state=42,
            ),

        "random_forest":
            RandomForestRegressor(
                n_estimators=300,
                max_depth=10,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1,
            ),
    }


# ============================================================
# ENSEMBLE TRAINING
# ============================================================

def train_ensemble(
    df: pd.DataFrame,
    target: str,
):

    X, y = prepare_data(
        df,
        target,
    )

    MIN_OBSERVATIONS = 200

    if len(X) < MIN_OBSERVATIONS:
        raise ValueError(
            f"Not enough observations: {len(X)}. "
            f"Minimum required: {MIN_OBSERVATIONS}"
        )

    # --------------------------------------------------------
    # Chronological holdout
    # --------------------------------------------------------

    split = int(
        len(X) * 0.8
    )

    X_train = X.iloc[:split]

    X_test = X.iloc[split:]

    y_train = y.iloc[:split]

    y_test = y.iloc[split:]

    # --------------------------------------------------------
    # Evaluation models
    # --------------------------------------------------------

    evaluation_models = create_models()

    test_predictions = {}

    for name, model in evaluation_models.items():

        model.fit(
            X_train,
            y_train,
        )

        test_predictions[name] = (
            model.predict(X_test)
        )

    ensemble_test_prediction = np.mean(
        list(
            test_predictions.values()
        ),
        axis=0,
    )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    residuals = (
        y_test.values
        - ensemble_test_prediction
    )

    mae = mean_absolute_error(
        y_test,
        ensemble_test_prediction,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            ensemble_test_prediction,
        )
    )

    residual_std = float(
        np.std(
            residuals,
            ddof=1,
        )
    )

    model_disagreement_test = float(
        np.mean(
            np.std(
                np.column_stack(
                    list(
                        test_predictions.values()
                    )
                ),
                axis=1,
            )
        )
    )

    # --------------------------------------------------------
    # FINAL MODELS
    #
    # Retrain using ALL historical observations.
    # --------------------------------------------------------

    final_models = create_models()

    for name, model in final_models.items():

        model.fit(
            X,
            y,
        )

    # --------------------------------------------------------
    # Current feature row
    # --------------------------------------------------------

    current = (
        df[FEATURE_COLUMNS]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .dropna()
    )

    if current.empty:

        raise ValueError(
            "No valid current feature row"
        )

    current_row = current.iloc[[-1]]

    current_predictions = {}

    for name, model in final_models.items():

        current_predictions[name] = float(
            model.predict(
                current_row
            )[0]
        )

    current_ensemble_prediction = float(
        np.mean(
            list(
                current_predictions.values()
            )
        )
    )

    current_model_disagreement = float(
        np.std(
            list(
                current_predictions.values()
            ),
            ddof=1,
        )
    )

    return {

        "models": final_models,

        "features": FEATURE_COLUMNS,

        "metrics": {

            "mae": float(mae),

            "rmse": float(rmse),

            "residual_std":
                residual_std,

            "test_model_disagreement":
                model_disagreement_test,

            "train_rows":
                int(len(X_train)),

            "test_rows":
                int(len(X_test)),
        },

        "test_predictions":
            ensemble_test_prediction,

        "y_test":
            y_test,

        "model_predictions":
            current_predictions,

        "ensemble_prediction":
            current_ensemble_prediction,

        "model_disagreement":
            current_model_disagreement,
    }