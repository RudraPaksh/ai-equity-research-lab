
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)

from ..dependencies import get_live_manager
from ..market.upstox_live import UpstoxLiveManager

router = APIRouter(
    prefix="/api/live",
    tags=["Live Market"],
)

ManagerDep = Annotated[
    UpstoxLiveManager,
    Depends(get_live_manager),
]


@router.get("/status")
def live_status(manager: ManagerDep):
    return manager.status()


@router.get("/{symbol}")
def latest_tick(
    symbol: str,
    manager: ManagerDep,
    instrument_key: str = Query(
        ...,
        min_length=1,
        description="Upstox instrument key, e.g. NSE_EQ|INE467B01029",
    ),
):
    try:
        manager.subscribe(symbol, instrument_key)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    tick = manager.latest(instrument_key)

    if tick is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Subscribed, but no tick has arrived yet. "
                "Check connection status and market hours."
            ),
        )

    return tick


@router.websocket("/ws/{symbol}")
async def live_websocket(
    websocket: WebSocket,
    symbol: str,
    instrument_key: str = Query(..., min_length=1),
):
    await websocket.accept()

    # Resolve the same shared manager used by REST routes.
    manager = get_live_manager()

    try:
        manager.subscribe(symbol, instrument_key)
        queue = manager.register_queue(instrument_key)

        # Send the cached tick immediately when available.
        cached = manager.latest(instrument_key)
        if cached is not None:
            await websocket.send_json(cached)

        while True:
            tick = await queue.get()
            await websocket.send_json(tick)

    except WebSocketDisconnect:
        pass
    except (RuntimeError, ValueError) as exc:
        try:
            await websocket.send_json({
                "error": str(exc),
                "provider": "upstox",
            })
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        if "queue" in locals():
            manager.unregister_queue(
                instrument_key,
                queue,
            )