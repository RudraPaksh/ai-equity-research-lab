"""
EquityOS live market feed.

Provider: Upstox Market Data Feed V3.
This module deliberately keeps the broker/feed layer separate from the
research/ML layer. It stores the latest normalized tick in memory and
fan-outs updates to local WebSocket clients.
"""
from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

try:
    import upstox_client
except ImportError:  # pragma: no cover
    upstox_client = None


@dataclass
class LiveTick:
    symbol: str
    instrument_key: str
    price: float | None
    previous_close: float | None
    last_trade_time: str | None
    last_trade_quantity: float | None
    received_at: str
    provider: str = "upstox"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class UpstoxLiveManager:
    def __init__(self, access_token: str | None):
        self.access_token = access_token
        self.streamer = None
        self.thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.RLock()
        self._ticks: dict[str, LiveTick] = {}
        self._queues: dict[str, set[asyncio.Queue]] = {}
        self._symbols: dict[str, str] = {}
        self._started = False
        self._last_error: str | None = None
        self._queue_loops: dict[asyncio.Queue, asyncio.AbstractEventLoop] = {}

    @property
    def configured(self) -> bool:
        return bool(self.access_token and upstox_client)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "provider": "upstox",
                "configured": self.configured,
                "connected": self._started and self.streamer is not None,
                "subscribed_symbols": sorted(self._symbols.keys()),
                "latest_ticks": len(self._ticks),
                "last_error": self._last_error,
            }

    def _find_feed(self, instrument_key: str, message: dict[str, Any]) -> dict[str, Any] | None:
        feeds = message.get("feeds") or {}
        return feeds.get(instrument_key)

    @staticmethod
    def _extract_ltpc(
            feed: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not isinstance(feed, dict):
            return None

        ltpc = feed.get("ltpc")
        if isinstance(ltpc, dict):
            return ltpc

        # Support the V3 full-feed wrappers.
        for parent in (
                "ff",
                "fullFeed",
                "marketFF",
                "indexFF",
                "firstLevelWithGreeks",
        ):
            node = feed.get(parent)

            if not isinstance(node, dict):
                continue

            ltpc = node.get("ltpc")
            if isinstance(ltpc, dict):
                return ltpc

            # Some full-feed structures wrap market data again.
            for nested in ("marketFF", "indexFF"):
                child = node.get(nested)
                if isinstance(child, dict):
                    ltpc = child.get("ltpc")
                    if isinstance(ltpc, dict):
                        return ltpc

        return None

    def _on_message(self, message: dict[str, Any]) -> None:
        if not isinstance(message, dict):
            return

        now = datetime.now(timezone.utc).isoformat()

        for instrument_key, feed in (message.get("feeds") or {}).items():
            ltpc = self._extract_ltpc(feed)
            if not ltpc:
                continue

            with self._lock:
                symbol = self._symbols.get(instrument_key, instrument_key)
                tick = LiveTick(
                    symbol=symbol,
                    instrument_key=instrument_key,
                    price=float(ltpc["ltp"]) if ltpc.get("ltp") is not None else None,
                    previous_close=float(ltpc["cp"]) if ltpc.get("cp") is not None else None,
                    last_trade_time=(
                        datetime.fromtimestamp(
                            int(ltpc["ltt"]) / 1000, tz=timezone.utc
                        ).isoformat()
                        if ltpc.get("ltt") is not None
                        else None
                    ),
                    last_trade_quantity=(
                        float(ltpc["ltq"]) if ltpc.get("ltq") is not None else None
                    ),
                    received_at=now,
                )
                self._ticks[instrument_key] = tick
                queues = list(self._queues.get(instrument_key, set()))

            for queue in queues:
                try:
                    queue.put_nowait(tick.as_dict())
                except asyncio.QueueFull:
                    # Drop stale ticks rather than allowing one slow browser
                    # to block the entire feed.
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        queue.put_nowait(tick.as_dict())
                    except asyncio.QueueFull:
                        pass

    @staticmethod
    def _deliver_tick(
            queue: asyncio.Queue,
            payload: dict[str, Any],
    ) -> None:
        # Keep the newest tick if a consumer is behind.
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass

        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass


    def _on_open(self, *args, **kwargs) -> None:
        self._last_error = None
        if self.streamer:
            with self._lock:
                keys = list(self._symbols.keys())
            if keys:
                self.streamer.subscribe(keys, "ltpc")

    def _on_error(self, error, *args, **kwargs) -> None:
        self._last_error = str(error)

    def _on_close(self, *args, **kwargs) -> None:
        self._started = False

    def _run(self) -> None:
        try:
            configuration = upstox_client.Configuration()
            configuration.access_token = self.access_token

            self.streamer = upstox_client.MarketDataStreamerV3(
                upstox_client.ApiClient(configuration)
            )
            self.streamer.on("open", self._on_open)
            self.streamer.on("message", self._on_message)
            self.streamer.on("error", self._on_error)
            self.streamer.on("close", self._on_close)

            self._started = True
            self.streamer.connect()
        except Exception as exc:  # pragma: no cover - provider/runtime specific
            self._last_error = str(exc)
            self._started = False

    def ensure_started(self) -> None:
        if not self.configured:
            raise RuntimeError(
                "Live market feed is not configured. Set UPSTOX_ACCESS_TOKEN "
                "and install upstox-python-sdk."
            )

        if self.thread and self.thread.is_alive():
            return

        self.thread = threading.Thread(
            target=self._run,
            name="equityos-upstox-feed",
            daemon=True,
        )
        self.thread.start()

    def subscribe(self, symbol: str, instrument_key: str) -> None:
        symbol = symbol.strip().upper()
        instrument_key = instrument_key.strip()

        if not instrument_key:
            raise ValueError("instrument_key is required")

        self.ensure_started()

        with self._lock:
            self._symbols[instrument_key] = symbol

        if self.streamer and self._started:
            self.streamer.subscribe([instrument_key], "ltpc")

    def unsubscribe(self, instrument_key: str) -> None:
        with self._lock:
            self._symbols.pop(instrument_key, None)
            self._ticks.pop(instrument_key, None)
            self._queues.pop(instrument_key, None)

        if self.streamer and self._started:
            try:
                self.streamer.unsubscribe([instrument_key])
            except Exception:
                pass

    def latest(self, instrument_key: str) -> dict[str, Any] | None:
        with self._lock:
            tick = self._ticks.get(instrument_key)
            return tick.as_dict() if tick else None

    def register_queue(
            self,
            instrument_key: str,
    ) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=5)
        loop = asyncio.get_running_loop()

        with self._lock:
            self._queues.setdefault(
                instrument_key, set()
            ).add(queue)
            self._queue_loops[queue] = loop

        return queue

    def unregister_queue(
            self,
            instrument_key: str,
            queue: asyncio.Queue,
    ) -> None:
        with self._lock:
            queues = self._queues.get(instrument_key)

            if queues:
                queues.discard(queue)
                if not queues:
                    self._queues.pop(
                        instrument_key, None
                    )

            self._queue_loops.pop(queue, None)

    def shutdown(self) -> None:
        try:
            if self.streamer:
                self.streamer.disconnect()
        except Exception:
            pass
        self._started = False
