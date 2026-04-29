"""Realtime WebSocket connection manager for the Websites module.

One pool per site (slug) with two audience types:
- `client`: client-dashboard viewers (ClientToken)
- `driver`: individual drivers (DriverToken)

Messages are JSON objects with shape:
    { "type": "<event>", "data": {...} }

Supported outgoing event types:
    - "location"       — a driver pushed a new GPS fix
    - "order_status"   — an order status/driver assignment changed
    - "order_created"  — a new order was placed on the public site
    - "ping"           — keepalive
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Set

from fastapi import WebSocket

log = logging.getLogger(__name__)


class RealtimeManager:
    def __init__(self) -> None:
        # slug → set of active WebSocket connections
        self._client_pools: Dict[str, Set[WebSocket]] = {}
        self._driver_pools: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, audience: str, slug: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            pool = self._pool(audience).setdefault(slug, set())
            pool.add(ws)
        log.info(f"[ws] +{audience}@{slug}  ({len(self._pool(audience).get(slug, set()))} total)")

    async def disconnect(self, audience: str, slug: str, ws: WebSocket) -> None:
        async with self._lock:
            pool = self._pool(audience).get(slug)
            if pool and ws in pool:
                pool.discard(ws)
                if not pool:
                    self._pool(audience).pop(slug, None)
        log.info(f"[ws] -{audience}@{slug}")

    def _pool(self, audience: str) -> Dict[str, Set[WebSocket]]:
        return self._client_pools if audience == "client" else self._driver_pools

    async def _broadcast(self, pools: Set[WebSocket], payload: Dict[str, Any]) -> None:
        if not pools:
            return
        dead = []
        for ws in list(pools):
            try:
                await ws.send_json(payload)
            except Exception as e:
                log.debug(f"[ws] dead conn removed: {e}")
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    pools.discard(ws)

    async def broadcast_to_clients(self, slug: str, event: str, data: Dict[str, Any]) -> None:
        pool = self._client_pools.get(slug)
        if pool:
            await self._broadcast(pool, {"type": event, "data": data})

    async def broadcast_to_drivers(self, slug: str, event: str, data: Dict[str, Any]) -> None:
        pool = self._driver_pools.get(slug)
        if pool:
            await self._broadcast(pool, {"type": event, "data": data})

    async def broadcast_all(self, slug: str, event: str, data: Dict[str, Any]) -> None:
        """Broadcast to both clients and drivers of a given slug."""
        await asyncio.gather(
            self.broadcast_to_clients(slug, event, data),
            self.broadcast_to_drivers(slug, event, data),
        )


# module-level singleton
realtime = RealtimeManager()
