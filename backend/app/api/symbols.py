from fastapi import APIRouter, HTTPException, Query

from ..core.symbols import format_symbol_result
from ..providers.twelve_data import search_symbols


router = APIRouter(
    prefix="/api/symbol",
    tags=["Symbol Search"],
)


@router.get("/search")
async def symbol_search(
    q: str = Query(
        ...,
        min_length=1,
        description="Ticker or company name",
    ),
    limit: int = Query(
        20,
        ge=1,
        le=50,
    ),
):

    try:
        results = await search_symbols(
            q,
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

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )