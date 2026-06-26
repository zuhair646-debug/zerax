"""
Sanity tests for the Backend Builder module.

We exercise the deterministic file-generation paths (mock Claude with
a known analysis schema and assert the produced FastAPI project is
syntactically valid Python).
"""
from __future__ import annotations

import ast
import os
import sys

import pytest

# Make the backend modules importable when pytest is invoked from /app
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.join(_ROOT, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "backend"))


_MOVIE_ANALYSIS = {
    "needs_backend": True,
    "needs_auth": True,
    "stack": "fastapi_mongo",
    "entities": [
        {
            "name": "Movie",
            "name_plural": "movies",
            "fields": [
                {"name": "id", "type": "str", "primary": True},
                {"name": "title", "type": "str", "required": True},
                {"name": "year", "type": "int", "required": False},
                {"name": "rating", "type": "float", "required": False},
                {"name": "created_at", "type": "datetime", "auto": True},
            ],
            "endpoints": ["list", "create", "get", "update", "delete"],
            "public_read": True,
        }
    ],
    "auth": {
        "user_fields": ["email", "password_hash", "name"],
        "registration": True,
        "login": True,
        "roles": ["user", "admin"],
    },
    "extra_endpoints": [],
}


@pytest.mark.asyncio
async def test_build_backend_kit_with_movie_entity(monkeypatch):
    from modules.freebuild import backend_builder as bb

    async def _fake_analyze(_blueprint):
        return _MOVIE_ANALYSIS

    monkeypatch.setattr(bb, "analyze_blueprint", _fake_analyze)

    project = {
        "id": "abc",
        "name": "My Movies",
        "discovery": {"vertical": "streaming_movies"},
    }
    files = await bb.build_backend_kit(project)
    # Must have core scaffolding
    must_have = {
        "api/Dockerfile.api",
        "api/requirements.txt",
        "api/app/__init__.py",
        "api/app/server.py",
        "api/app/models.py",
        "api/app/db.py",
        "api/app/auth.py",
        "api/app/routes/__init__.py",
        "api/app/routes/movies.py",
        "api/README.md",
        ".env.example",
        ".github/workflows/deploy.yml",
        "docker-compose.yml",
    }
    missing = must_have - set(files.keys())
    assert not missing, f"Missing files: {missing}"

    # Generated Python must be syntactically valid
    for fname, content in files.items():
        if fname.endswith(".py"):
            try:
                ast.parse(content)
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {fname}: {e}")

    # models.py should declare Movie + UserRegister
    assert "class Movie(" in files["api/app/models.py"]
    assert "class UserRegister(" in files["api/app/models.py"]

    # server.py wires the routers
    assert "movies_router" in files["api/app/server.py"]
    assert "auth_router" in files["api/app/server.py"]

    # auth.py implements JWT
    assert "jwt.encode" in files["api/app/auth.py"]
    assert "bcrypt" in files["api/app/auth.py"]

    # docker-compose is the full-stack version (api + mongo)
    assert "mongo:" in files["docker-compose.yml"]
    assert "Dockerfile.api" in files["docker-compose.yml"]

    # GitHub Actions deploys via SSH
    assert "VPS_HOST" in files[".github/workflows/deploy.yml"]
    assert "docker compose" in files[".github/workflows/deploy.yml"]


@pytest.mark.asyncio
async def test_build_backend_kit_no_backend_path(monkeypatch):
    """For a marketing/brochure site, builder should return only the
    explanatory README and not generate boilerplate."""
    from modules.freebuild import backend_builder as bb

    async def _fake_analyze(_blueprint):
        return {"needs_backend": False, "entities": []}

    monkeypatch.setattr(bb, "analyze_blueprint", _fake_analyze)

    files = await bb.build_backend_kit({"name": "Portfolio", "discovery": {}})
    assert list(files.keys()) == ["api/README.md"]
    assert "تعريفي" in files["api/README.md"] or "تسويقي" in files["api/README.md"]
