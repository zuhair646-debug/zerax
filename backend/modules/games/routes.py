"""Games routes — static asset serving + (future) generation."""
import os
from fastapi import APIRouter, Response


def init_routes() -> APIRouter:
    r = APIRouter(tags=["games"])
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")

    def _serve_static(filename: str, media_type: str):
        p = os.path.join(static_dir, filename)
        if not os.path.exists(p):
            return Response(content="not found", media_type="text/plain", status_code=404)
        with open(p, "r", encoding="utf-8") as f:
            return Response(
                content=f.read(),
                media_type=media_type,
                headers={"Cache-Control": "no-cache"},
            )

    @r.get("/game-engine.js")
    async def _engine():
        return _serve_static("game-engine.js", "application/javascript")

    @r.get("/game-test")
    async def _gtest():
        return _serve_static("game-test.html", "text/html")

    @r.get("/iframe-test")
    async def _iframe():
        return _serve_static("iframe-test.html", "text/html")

    @r.get("/image-backed-test")
    async def _imgtest():
        return _serve_static("image-backed-test.html", "text/html")

    return r
