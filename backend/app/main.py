import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .providers.yahoo import get_daily as yahoo_get_daily
from .core.market_symbols import yahoo_symbol
from .ml.forecast_engine import forecast as run_forecast
from .analyst.engine import build_analyst_report
from .market.upstox_live import UpstoxLiveManager
from .api.live import router as live_router
from .dependencies import live_manager

from .core.symbols import (
    format_symbol_result,
    choose_best_result,
)

from .config import settings

from .providers.twelve_data import (
    get_daily,
    search_symbols,
)

from .providers import fmp, sec

from .news.gdelt import search_news

from .quant.technical import (
    indicators,
    risk,
    factor_snapshot,
)

from .valuation.dcf import (
    scenario_dcf,
    sensitivity,
)

from .valuation.multiples import (
    valuation_snapshot,
)

from .ml.model import (
    train,
    predict,
    tensorflow_available,
)

from .rag.retriever import (
    Retriever,
    Document,
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="AI Equity Research Lab",
    version="0.4.0",
)

app.include_router(live_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        x.strip()
        for x in settings.cors_origins.split(",")
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(live_router)

rag = Retriever()

# live_manager = UpstoxLiveManager(
#     settings.upstox_access_token
# )
# ============================================================
# MARKET DATA PARSER
# ============================================================

def parse(raw):
    df = pd.DataFrame(
        raw.get("values", [])
    )

    if df.empty:
        raise ValueError(
            "No market data returned"
        )

    df["datetime"] = pd.to_datetime(
        df["datetime"]
    )

    df = (
        df
        .set_index("datetime")
        .sort_index()
    )

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:

        if column in df:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df.dropna(
        subset=["close"]
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "0.4.0",
        "tensorflow_available":
            tensorflow_available(),
    }


# ============================================================
# SYMBOL SEARCH
# ============================================================

@app.get("/api/symbol/search")
async def symbol_search(
        q: str,
        limit: int = 20,
):
    try:

        if not q.strip():
            raise ValueError(
                "Search query cannot be empty"
            )

        limit = max(
            1,
            min(limit, 50)
        )

        results = await search_symbols(
            q.strip(),
            outputsize=limit,
        )

        formatted = [
            format_symbol_result(item)
            for item in results
        ]

        return {
            "query": q,
            "count": len(formatted),
            "results": formatted,
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# ============================================================
# ADVANCED MULTI-HORIZON FORECAST
# ============================================================

@app.get("/api/forecast/{symbol}")
async def advanced_forecast(symbol: str):

    try:

        query = symbol.strip().upper()

        if not query:
            raise ValueError(
                "Symbol cannot be empty"
            )

        # ----------------------------------------------------
        # Resolve security
        # ----------------------------------------------------

        results = await search_symbols(
            query,
            outputsize=20,
        )

        selected = choose_best_result(
            query,
            results,
        )

        if not selected:
            raise ValueError(
                f"Security '{query}' was not found"
            )

        security = format_symbol_result(
            selected
        )

        resolved_symbol = security[
            "symbol"
        ]

        exchange = security.get(
            "exchange"
        )

        country = security.get(
            "country"
        )

        # ----------------------------------------------------
        # Yahoo mapping
        # ----------------------------------------------------

        yahoo_ticker = yahoo_symbol(
            resolved_symbol,
            exchange=exchange,
            country=country,
        )

        # ----------------------------------------------------
        # Market data
        # ----------------------------------------------------

        df = yahoo_get_daily(
            yahoo_ticker,
            outputsize=500,
        )

        # ----------------------------------------------------
        # Advanced ML engine
        # ----------------------------------------------------

        result = run_forecast(
            df
        )

        return {

            "symbol":
                resolved_symbol,

            "security":
                security,

            "market_data_provider":
                "Yahoo Finance",

            "market_data_symbol":
                yahoo_ticker,

            "latest_price":
                float(
                    df["close"].iloc[-1]
                ),

            **result,
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@app.get("/api/analyst/{symbol}")
async def analyst(symbol: str):
    try:
        query = symbol.strip().upper()

        if not query:
            raise ValueError("Symbol cannot be empty")

        # ---------------------------------------------------------
        # 1. Resolve security
        # ---------------------------------------------------------
        results = await search_symbols(
            query,
            outputsize=20
        )

        selected = choose_best_result(
            query,
            results
        )

        if not selected:
            raise ValueError(
                f"Security '{query}' was not found"
            )

        security = format_symbol_result(selected)

        resolved_symbol = security["symbol"]
        exchange = security.get("exchange")
        country = security.get("country")

        yahoo_ticker = yahoo_symbol(
            resolved_symbol,
            exchange=exchange,
            country=country,
        )

        # ---------------------------------------------------------
        # 2. Market data
        # ---------------------------------------------------------
        market_df = yahoo_get_daily(
            yahoo_ticker,
            outputsize=1500
        )

        technical_df = indicators(
            market_df.copy()
        )

        market_risk = risk(
            technical_df
        )

        market_factors = factor_snapshot(
            technical_df
        )

        # Baseline model
        baseline_model, baseline_metrics = train(
            technical_df
        )

        baseline_prediction = predict(
            baseline_model,
            technical_df
        )

        stock_data = {
            "symbol": resolved_symbol,
            "risk": market_risk,
            "factors": market_factors,
            "prediction": baseline_prediction,
            "backtest": baseline_metrics,
            "latest": (
                technical_df
                .tail(1)
                .reset_index()
                .to_dict("records")[0]
            ),
        }

        # ---------------------------------------------------------
        # 3. Advanced forecast
        # ---------------------------------------------------------
        forecast_result = run_forecast(
            market_df
        )

        # ---------------------------------------------------------
        # 4. Fundamentals
        # ---------------------------------------------------------
        fundamentals_data = {}

        try:
            fundamentals_data = {
                "symbol": resolved_symbol,
                "profile": await fmp.profile(resolved_symbol),
                "income": await fmp.income(resolved_symbol),
                "balance": await fmp.balance(resolved_symbol),
                "cashflow": await fmp.cashflow(resolved_symbol),
                "ratios": await fmp.ratios(resolved_symbol),
                "key_metrics": await fmp.key_metrics(resolved_symbol),
            }
        except Exception:
            # Fundamentals are optional.
            fundamentals_data = {}

        # ---------------------------------------------------------
        # 5. News
        # ---------------------------------------------------------
        news_data = {}

        try:
            news_data = {
                "symbol": resolved_symbol,
                "articles": await search_news(
                    resolved_symbol
                ),
            }
        except Exception:
            news_data = {}

        # ---------------------------------------------------------
        # 6. SEC evidence
        # ---------------------------------------------------------
        sec_data = {}

        try:
            sec_data = {
                "symbol": resolved_symbol,
                "facts": await sec.company_facts(
                    resolved_symbol
                ),
            }
        except Exception:
            sec_data = {}

        # ---------------------------------------------------------
        # 7. RAG
        # ---------------------------------------------------------
        rag_results = []

        try:
            rag_results = rag.search(
                f"{resolved_symbol} earnings revenue margin risk valuation guidance",
                8
            )
        except Exception:
            rag_results = []

        # ---------------------------------------------------------
        # 8. Build research report
        # ---------------------------------------------------------
        report = build_analyst_report(
            symbol=resolved_symbol,
            security=security,
            stock=stock_data,
            forecast=forecast_result,
            fundamentals=fundamentals_data,
            news=news_data,
            sec_data=sec_data,
            rag_results=rag_results,
        )

        return report

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
# ============================================================
# STOCK ANALYSIS
# ============================================================

@app.get("/api/stock/{symbol}")
async def stock(symbol: str):
    try:
        query = symbol.strip().upper()

        if not query:
            raise ValueError("Symbol cannot be empty")

        # Resolve security using Twelve Data search
        results = await search_symbols(
            query,
            outputsize=20,
        )

        selected = choose_best_result(
            query,
            results,
        )

        if not selected:
            raise ValueError(
                f"Security '{query}' was not found"
            )

        security = format_symbol_result(selected)

        resolved_symbol = security["symbol"]
        exchange = security.get("exchange")
        country = security.get("country")

        yahoo_ticker = yahoo_symbol(
            resolved_symbol,
            exchange=exchange,
            country=country,
        )

        print("Resolved security:", security)

        print(
            "Yahoo market data:",
            {
                "symbol": resolved_symbol,
                "yahoo_symbol": yahoo_ticker,
            },
        )

        df = yahoo_get_daily(
            yahoo_ticker,
            outputsize=500,
        )

        # Existing quant pipeline
        df = indicators(df)

        model, metrics = train(df)

        return {
            "symbol": resolved_symbol,
            "security": security,
            "market_data_provider": "Yahoo Finance",
            "market_data_symbol": yahoo_ticker,
            "risk": risk(df),
            "factors": factor_snapshot(df),
            "prediction": predict(model, df),
            "backtest": metrics,
            "latest": (
                df.tail(1)
                .reset_index()
                .to_dict("records")[0]
            ),
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
# ============================================================
# FUNDAMENTALS
# ============================================================

@app.get("/api/fundamentals/{symbol}")
async def fundamentals(symbol: str):
    try:

        s = symbol.strip().upper()

        return {
            "symbol": s,

            "profile":
                await fmp.profile(s),

            "income":
                await fmp.income(s),

            "balance":
                await fmp.balance(s),

            "cashflow":
                await fmp.cashflow(s),

            "ratios":
                await fmp.ratios(s),

            "key_metrics":
                await fmp.key_metrics(s),
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# ============================================================
# SEC
# ============================================================

@app.get("/api/sec/{symbol}")
async def sec_facts(symbol: str):
    try:

        s = symbol.strip().upper()

        return {
            "symbol": s,
            "facts":
                await sec.company_facts(s),
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# ============================================================
# NEWS
# ============================================================

@app.get("/api/news/{symbol}")
async def news(
        symbol: str,
        q: str | None = None,
):
    try:

        s = symbol.strip().upper()

        query = (
            q.strip()
            if q
            else s
        )

        articles = await search_news(
            query
        )

        return {
            "symbol": s,
            "query": query,
            "articles": articles,
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# ============================================================
# DCF
# ============================================================

@app.post("/api/dcf")
def dcf(p: dict):
    try:

        args = {
            key: float(p[key])
            for key in [
                "revenue",
                "shares",
                "growth",
                "fcf_margin",
                "wacc",
                "terminal_growth",
            ]
        }

        args.update({
            "net_debt":
                float(
                    p.get(
                        "net_debt",
                        0
                    )
                ),

            "years":
                int(
                    p.get(
                        "years",
                        5
                    )
                ),
        })

        return {
            "scenarios":
                scenario_dcf(**args),

            "sensitivity":
                sensitivity(**args),
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# ============================================================
# MULTIPLES
# ============================================================

@app.post("/api/multiples")
def multiples(p: dict):
    try:

        return valuation_snapshot(
            float(p["price"]),
            **{
                k: float(v)
                for k, v in p.items()
                if k != "price"
            },
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# ============================================================
# RAG DOCUMENTS
# ============================================================

@app.post("/api/rag/documents")
def add_doc(p: dict):
    rag.add(
        Document(
            str(
                p.get(
                    "id",
                    len(rag.docs) + 1,
                )
            ),

            p["title"],

            p["text"],

            p.get(
                "source",
                "local",
            ),
        )
    )

    return {
        "indexed":
            len(rag.docs)
    }


# ============================================================
# RAG SEARCH
# ============================================================

@app.get("/api/rag/search")
def search(
        q: str,
        k: int = 5,
):
    return {
        "results":
            rag.search(q, k)
    }

@app.get("/api/symbol/resolve")
async def symbol_resolve(q: str):

    try:

        if not q.strip():
            raise ValueError(
                "Search query cannot be empty"
            )

        results = await search_symbols(
            q.strip(),
            outputsize=20,
        )

        selected = choose_best_result(
            q,
            results,
        )

        if not selected:
            raise ValueError(
                f"No security found for '{q}'"
            )

        return {
            "query": q,
            "resolved": format_symbol_result(
                selected
            ),
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

@app.on_event("shutdown")
async def shutdown_live_market():
    live_manager.shutdown()