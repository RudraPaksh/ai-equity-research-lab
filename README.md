# AI Equity Research Lab — V0.2 + V0.3

Personal, local-first equity research platform built with **Python/FastAPI + ML + quantitative valuation + Angular**. No Spring Boot.

## What was added

### V0.2 — Data layer
- Provider abstraction and centralized HTTP client
- SQLite response cache with TTL
- Retry/backoff for temporary provider failures
- Twelve Data market prices
- FMP profile, income, balance sheet, cash flow, ratios and key metrics
- SEC company-facts ingestion with ticker → CIK lookup
- GDELT news search (no API key required)
- Source/provider errors are surfaced instead of silently fabricating data

### V0.3 — Quant + valuation
- Expanded technical indicators: SMA/EMA, RSI, MACD, ATR, volatility, volume ratio, multi-horizon returns
- Risk snapshot and factor snapshot
- Three-model ML baseline: Logistic Regression, HistGradientBoosting and Random Forest
- Chronological 80/20 holdout
- Accuracy, ROC-AUC, precision, recall, Brier score and confusion matrix
- Fixed future-target tail leakage bug
- Scenario DCF: Bear/Base/Bull
- DCF sensitivity matrix across WACC and terminal growth
- Multiples helper for P/E, FCF yield and P/S

## Run

```bash
cd backend
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows CMD
# cp .env.example .env  # macOS/Linux
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

### Configure
Set at least:
- `TWELVE_DATA_API_KEY`
- `FMP_API_KEY`
- `SEC_USER_AGENT` with a real contact address

GDELT news does not require a key.

## Test

```bash
cd backend
pytest -q
```

The included tests cover the V0.2/V0.3 calculation modules without requiring live market APIs.

## Next upgrade after V0.3
V0.4 should add point-in-time feature engineering, walk-forward validation, calibration, SHAP/explainability, transaction-cost-aware backtesting, model persistence, regime detection, and then TensorFlow LSTM/GRU as an additional model rather than replacing the simpler baselines.

## Research-use note
This application produces research signals and valuation scenarios, not guaranteed forecasts or investment advice. Any probability should be interpreted with its out-of-sample validation statistics, data freshness, and uncertainty. Respect provider licensing and display restrictions before distributing the application.
