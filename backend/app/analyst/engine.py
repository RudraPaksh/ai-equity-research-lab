from __future__ import annotations

from typing import Any
import math


def _num(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
        if math.isfinite(value):
            return value
    except (TypeError, ValueError):
        pass
    return default


def _pct(value: Any) -> float:
    value = _num(value)
    if abs(value) <= 1:
        return value * 100
    return value


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _direction_label(value: Any) -> str:
    value = _clean_text(value).lower()

    if value in {"up", "bullish", "positive"}:
        return "UP"

    if value in {"down", "bearish", "negative"}:
        return "DOWN"

    return "NEUTRAL"


def _forecast_horizon(forecast: dict, horizon: str) -> dict:
    forecasts = forecast.get("forecasts", {})
    item = forecasts.get(horizon, {})

    return {
        "horizon": horizon,
        "expected_return": _pct(item.get("expected_return")),
        "probability_up": _pct(item.get("probability_up")),
        "probability_sideways": _pct(item.get("probability_sideways")),
        "probability_down": _pct(item.get("probability_down")),
        "uncertainty": _pct(item.get("uncertainty")),
        "signal_strength": _num(item.get("signal_strength")),
        "direction": _direction_label(item.get("direction")),
        "components": item.get("components", {}),
        "model_quality": item.get("model_quality", {}),
    }


def _technical_evidence(stock: dict) -> list[dict]:
    factors = stock.get("factors", {})
    evidence = []

    for key, raw_value in factors.items():
        value = _num(raw_value)

        label = key.replace("_", " ").title()

        if value >= 70:
            evidence.append({
                "type": "technical",
                "impact": "positive",
                "title": f"{label} is supportive",
                "detail": f"Factor score is {value:.1f}/100.",
            })
        elif value <= 35:
            evidence.append({
                "type": "technical",
                "impact": "negative",
                "title": f"{label} is weak",
                "detail": f"Factor score is {value:.1f}/100.",
            })

    prediction = stock.get("prediction", {})

    signal = _clean_text(prediction.get("signal"))

    if signal:
        evidence.append({
            "type": "model",
            "impact": "neutral",
            "title": "Baseline model signal",
            "detail": signal,
        })

    return evidence


def _risk_evidence(stock: dict) -> list[dict]:
    risk = stock.get("risk", {})
    result = []

    volatility = _pct(risk.get("annualized_volatility"))
    drawdown = _pct(risk.get("max_drawdown"))
    sharpe = _num(risk.get("sharpe_approx"))

    if volatility:
        impact = "negative" if volatility >= 40 else "neutral"

        result.append({
            "type": "risk",
            "impact": impact,
            "title": "Annualized volatility",
            "detail": f"Approximately {volatility:.1f}%.",
        })

    if drawdown:
        result.append({
            "type": "risk",
            "impact": "negative" if abs(drawdown) >= 20 else "neutral",
            "title": "Historical drawdown",
            "detail": f"Maximum observed drawdown is approximately {drawdown:.1f}%.",
        })

    if sharpe:
        result.append({
            "type": "risk",
            "impact": "positive" if sharpe > 1 else "neutral",
            "title": "Risk-adjusted return",
            "detail": f"Approximate Sharpe ratio: {sharpe:.2f}.",
        })

    return result


def _forecast_evidence(forecast: dict) -> list[dict]:
    result = []

    for horizon in ("1d", "5d", "20d"):
        f = _forecast_horizon(forecast, horizon)

        direction = f["direction"]
        expected = f["expected_return"]

        if direction == "DOWN":
            impact = "negative"
        elif direction == "UP":
            impact = "positive"
        else:
            impact = "neutral"

        result.append({
            "type": "forecast",
            "impact": impact,
            "title": f"{horizon.upper()} model outlook",
            "detail": (
                f"{direction}; expected return {expected:+.2f}%; "
                f"up {f['probability_up']:.1f}%, "
                f"sideways {f['probability_sideways']:.1f}%, "
                f"down {f['probability_down']:.1f}%."
            ),
        })

    return result


def _news_evidence(news: dict) -> list[dict]:
    articles = _safe_list(news.get("articles"))

    result = []

    for article in articles[:8]:
        if not isinstance(article, dict):
            continue

        title = (
            article.get("title")
            or article.get("headline")
            or article.get("name")
            or "Recent company/market news"
        )

        source = (
            article.get("source")
            or article.get("domain")
            or article.get("url")
            or "News source"
        )

        result.append({
            "type": "news",
            "impact": "unknown",
            "title": _clean_text(title),
            "detail": _clean_text(source),
            "url": article.get("url"),
        })

    return result


def _sec_evidence(sec_data: dict) -> list[dict]:
    facts = sec_data.get("facts")

    if not facts:
        return [{
            "type": "sec",
            "impact": "unknown",
            "title": "SEC evidence unavailable",
            "detail": "No SEC company facts were returned for this security.",
        }]

    return [{
        "type": "sec",
        "impact": "positive",
        "title": "SEC company facts available",
        "detail": "Regulatory financial facts are available for evidence retrieval.",
    }]


def _fundamental_evidence(fundamentals: dict) -> list[dict]:
    result = []

    if not fundamentals:
        return [{
            "type": "fundamental",
            "impact": "unknown",
            "title": "Fundamental data unavailable",
            "detail": "The configured fundamentals provider did not return usable data.",
        }]

    profile = fundamentals.get("profile", {})
    ratios = fundamentals.get("ratios", {})
    key_metrics = fundamentals.get("key_metrics", {})

    if isinstance(profile, list) and profile:
        profile = profile[0]

    if isinstance(ratios, list) and ratios:
        ratios = ratios[0]

    if isinstance(key_metrics, list) and key_metrics:
        key_metrics = key_metrics[0]

    if isinstance(profile, dict):
        description = profile.get("description")

        if description:
            result.append({
                "type": "fundamental",
                "impact": "neutral",
                "title": "Company profile",
                "detail": _clean_text(description)[:500],
            })

    for key in (
        "peRatio",
        "priceToBookRatio",
        "roe",
        "returnOnEquity",
        "debtToEquity",
        "netProfitMargin",
    ):
        value = None

        if isinstance(ratios, dict):
            value = ratios.get(key)

        if value is None and isinstance(key_metrics, dict):
            value = key_metrics.get(key)

        if value is not None:
            result.append({
                "type": "fundamental",
                "impact": "neutral",
                "title": key,
                "detail": f"{_num(value):.3f}",
            })

    return result


def _build_bull_case(
    forecast: dict,
    fundamentals: dict,
    news: dict,
) -> list[str]:
    points = []

    f1 = _forecast_horizon(forecast, "1d")
    f5 = _forecast_horizon(forecast, "5d")
    f20 = _forecast_horizon(forecast, "20d")

    if f1["direction"] == "UP":
        points.append("Short-term model momentum is positive.")

    if f5["direction"] == "UP":
        points.append("The 5-day model outlook is positive.")

    if f20["probability_up"] > f20["probability_down"]:
        points.append("The longer-horizon model assigns greater probability to an upside outcome.")

    if fundamentals:
        points.append("Fundamental evidence can provide additional support if earnings, cash flow and margins remain resilient.")

    if _safe_list(news.get("articles")):
        points.append("Positive company or sector catalysts could invalidate a weak technical setup.")

    if not points:
        points.append("A stronger earnings trajectory, improving fundamentals or a positive regime shift could support the bull case.")

    return points


def _build_bear_case(
    forecast: dict,
    stock: dict,
) -> list[str]:
    points = []

    f1 = _forecast_horizon(forecast, "1d")
    f5 = _forecast_horizon(forecast, "5d")
    f20 = _forecast_horizon(forecast, "20d")

    if f20["direction"] == "DOWN":
        points.append(
            f"The 20-day model outlook is negative at approximately {f20['expected_return']:+.2f}%."
        )

    if f20["probability_down"] > 60:
        points.append(
            f"The 20-day downside probability is elevated at {f20['probability_down']:.1f}%."
        )

    if f5["direction"] == "DOWN":
        points.append("The 5-day model also points downward.")

    risk = stock.get("risk", {})
    volatility = _pct(risk.get("annualized_volatility"))

    if volatility >= 30:
        points.append(
            f"Annualized volatility is elevated at approximately {volatility:.1f}%."
        )

    if not points:
        points.append("Weakening momentum, deteriorating earnings or a negative market regime could strengthen the bear case.")

    return points


def _build_thesis_breakers(
    forecast: dict,
    stock: dict,
) -> list[str]:
    breakers = [
        "A material earnings or guidance surprise in the opposite direction.",
        "A sustained change in revenue, margin or free-cash-flow trajectory.",
        "A regime change that invalidates the historical relationship used by the model.",
        "A major company-specific event not represented in the training data.",
    ]

    f20 = _forecast_horizon(forecast, "20d")

    if f20["direction"] == "DOWN":
        breakers.insert(
            0,
            "A sustained price recovery accompanied by improving momentum would weaken the current bearish model evidence.",
        )

    return breakers


def _build_questions() -> list[str]:
    return [
        "Are the latest earnings and management guidance consistent with the current valuation?",
        "Is the current price move supported by fundamentals or primarily by momentum?",
        "What upcoming catalyst could materially change the thesis?",
        "Which assumption has the largest impact on intrinsic value?",
        "What evidence would invalidate the current model signal?",
    ]


def _confidence(
    forecast: dict,
    stock: dict,
    evidence_count: int,
) -> dict:
    f20 = _forecast_horizon(forecast, "20d")

    score = 0

    if abs(f20["signal_strength"]) >= 0.5:
        score += 2
    elif abs(f20["signal_strength"]) >= 0.2:
        score += 1

    if evidence_count >= 8:
        score += 1

    volatility = _pct(stock.get("risk", {}).get("annualized_volatility"))

    if volatility < 60:
        score += 1

    if score >= 3:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "level": level,
        "score": score,
        "max_score": 4,
        "explanation": (
            "Research confidence reflects evidence availability and model "
            "signal strength. It is not a probability of being correct."
        ),
    }


def build_analyst_report(
    symbol: str,
    security: dict,
    stock: dict,
    forecast: dict,
    fundamentals: dict | None,
    news: dict | None,
    sec_data: dict | None,
    rag_results: list | None = None,
) -> dict:

    fundamentals = fundamentals or {}
    news = news or {}
    sec_data = sec_data or {}
    rag_results = rag_results or []

    evidence = []

    evidence.extend(_technical_evidence(stock))
    evidence.extend(_risk_evidence(stock))
    evidence.extend(_forecast_evidence(forecast))
    evidence.extend(_fundamental_evidence(fundamentals))
    evidence.extend(_news_evidence(news))
    evidence.extend(_sec_evidence(sec_data))

    f20 = _forecast_horizon(forecast, "20d")

    supporting = [
        item for item in evidence
        if item.get("impact") == "positive"
    ]

    negative = [
        item for item in evidence
        if item.get("impact") == "negative"
    ]

    return {
        "symbol": symbol,
        "security": security,

        "research_summary": {
            "headline": (
                f"{symbol} currently has a {f20['direction'].lower()} "
                f"20-day quantitative outlook."
            ),
            "expected_return_20d": f20["expected_return"],
            "probability_up_20d": f20["probability_up"],
            "probability_sideways_20d": f20["probability_sideways"],
            "probability_down_20d": f20["probability_down"],
            "uncertainty_20d": f20["uncertainty"],
            "regime": forecast.get("regime", {}),
            "uncertainty_type": forecast.get(
                "uncertainty_type",
                "uncalibrated_research_estimate",
            ),
        },

        "confidence": _confidence(
            forecast,
            stock,
            len(evidence),
        ),

        "why": {
            "supporting_evidence": supporting[:8],
            "negative_evidence": negative[:8],
        },

        "bull_case": _build_bull_case(
            forecast,
            fundamentals,
            news,
        ),

        "base_case": [
            "The stock remains range-bound while the market digests earnings, valuation and macro information.",
            "Short-term signals remain noisy and should be interpreted alongside fundamental evidence.",
            "The model signal becomes more informative if supported by independent fundamental or event evidence.",
        ],

        "bear_case": _build_bear_case(
            forecast,
            stock,
        ),

        "catalysts": [
            "Quarterly earnings and management guidance",
            "Revenue and margin trajectory",
            "Free cash flow development",
            "Major company or sector announcements",
            "Change in broader market regime",
        ],

        "risks": [
            "Model uncertainty and historical regime changes",
            "Unexpected company-specific events",
            "Earnings or guidance surprises",
            "Valuation compression",
            "Broader market volatility",
        ],

        "thesis_breakers": _build_thesis_breakers(
            forecast,
            stock,
        ),

        "what_could_make_me_wrong": [
            "The historical relationships learned by the model may not persist.",
            "The latest company information may not yet be reflected in the numerical features.",
            "A new fundamental catalyst could overwhelm technical signals.",
            "The probabilities are currently uncalibrated research estimates.",
        ],

        "research_questions": _build_questions(),

        "evidence": evidence[:40],

        "rag": {
            "available": len(rag_results) > 0,
            "count": len(rag_results),
            "results": rag_results[:8],
        },

        "data_quality": {
            "market_data": bool(stock),
            "forecast": bool(forecast),
            "fundamentals": bool(fundamentals),
            "news": bool(_safe_list(news.get("articles"))),
            "sec": bool(sec_data.get("facts")),
            "rag": len(rag_results) > 0,
            "warnings": [
                "Forecast probabilities are not calibrated.",
                "Quantitative forecasts are historical-model estimates, not guaranteed outcomes.",
            ],
        },
    }