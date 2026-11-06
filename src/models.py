"""Baselines and the LightGBM model.

Baselines (all fitted on TRAINING data only):
  AlwaysOff       predicts 0 W
  TrainMean       predicts the mean washing-machine power of the training data (right energy, no timing)
  HourlyProfile   predicts the mean power for each (weekday, hour) of the training data
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

# newer LightGBM versions print a harmless deprecation notice about `eval_set`; older ones need it
warnings.filterwarnings("ignore", message=".*eval_set.*")


class AlwaysOff:
    name = "always_off"

    def fit(self, frames):
        return self

    def predict(self, index):
        return np.zeros(len(index), dtype="float64")


class TrainMean:
    name = "train_mean"

    def fit(self, frames):
        y = pd.concat([f["wm"] for f in frames]).dropna()
        self.mean_ = float(y.mean())
        return self

    def predict(self, index):
        return np.full(len(index), self.mean_, dtype="float64")


class HourlyProfile:
    name = "hourly_profile"

    def fit(self, frames):
        y = pd.concat([f["wm"] for f in frames]).dropna()
        self.global_mean_ = float(y.mean())
        grid = np.full((7, 24), self.global_mean_)
        means = y.groupby([y.index.day_of_week, y.index.hour]).mean()
        for (d, h), v in means.items():
            grid[int(d), int(h)] = v
        self.grid_ = grid
        return self

    def predict(self, index):
        return self.grid_[np.asarray(index.day_of_week), np.asarray(index.hour)].astype("float64")


DEFAULT_LGBM = dict(
    n_estimators=2000,
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=50,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    tweedie_variance_power=1.5,
    early_stopping_rounds=100,
)


def fit_lgbm(X_train, y_train, X_val, y_val, objective: str, params: dict | None = None, seed: int = 0):
    """objective: 'tweedie' or 'regression' (L2). Early stopping on validation MAE. Returns the fitted model."""
    import lightgbm as lgb

    p = {**DEFAULT_LGBM, **(params or {})}
    stop = p.pop("early_stopping_rounds")
    if objective != "tweedie":
        p.pop("tweedie_variance_power", None)
    model = lgb.LGBMRegressor(objective=objective, metric="l1", random_state=seed, n_jobs=-1, verbose=-1, **p)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(stop, verbose=False)],
    )
    return model


def predict_lgbm(model, X) -> np.ndarray:
    return np.clip(model.predict(X), 0, None)