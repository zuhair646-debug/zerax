"""
Credentials Vault — unified storage for API keys / credentials needed by
the 300+ tools the Auto-Coder can activate.

Resolution order for ANY credential lookup:
  1. process environment variable (always wins — production Railway env)
  2. JSON vault at /root/.zitex/credentials.json
  3. None  →  the tool surfaces a "needs_key" hint to the AI / owner

The JSON vault lets the owner add keys at runtime without redeploy. It is
NEVER committed (lives outside /app). The Auto-Coder can read+write it via
`vault_get` / `vault_set` exposed as AI tools.
"""
from __future__ import annotations
import os
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

VAULT_DIR = Path(os.environ.get("ZERAX_VAULT_DIR", "/root/.zitex"))
VAULT_FILE = VAULT_DIR / "credentials.json"
_LOCK = threading.Lock()
_CACHE: Optional[Dict[str, str]] = None


def _load() -> Dict[str, str]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    try:
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        if VAULT_FILE.exists():
            _CACHE = json.loads(VAULT_FILE.read_text(encoding="utf-8") or "{}")
        else:
            _CACHE = {}
    except Exception:
        _CACHE = {}
    return _CACHE


def _save() -> None:
    if _CACHE is None:
        return
    try:
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        tmp = VAULT_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_CACHE, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(VAULT_FILE)
        try:
            os.chmod(VAULT_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass


def vault_get(key: str) -> Optional[str]:
    """Return the credential value (env → vault → None)."""
    if not key:
        return None
    env_v = os.environ.get(key)
    if env_v:
        return env_v
    with _LOCK:
        v = _load().get(key)
    return v or None


def vault_set(key: str, value: str) -> bool:
    if not key:
        return False
    with _LOCK:
        data = _load()
        data[key] = value
        _save()
    return True


def vault_delete(key: str) -> bool:
    with _LOCK:
        data = _load()
        if key in data:
            del data[key]
            _save()
            return True
    return False


def vault_list() -> List[Dict[str, Any]]:
    """List all known keys with `source` (env|vault) and `set` flag.
    Never returns the raw value — only existence + length for UI."""
    out: List[Dict[str, Any]] = []
    seen = set()
    with _LOCK:
        vault_data = dict(_load())
    # vault entries
    for k, v in vault_data.items():
        out.append({
            "key": k,
            "source": "vault",
            "set": bool(v),
            "length": len(v or ""),
        })
        seen.add(k)
    # env entries that aren't in vault — only include those likely to be API keys
    for k in os.environ:
        if k in seen:
            continue
        if any(s in k for s in ("_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "API_")):
            v = os.environ.get(k, "")
            out.append({
                "key": k,
                "source": "env",
                "set": bool(v),
                "length": len(v),
            })
    return sorted(out, key=lambda x: x["key"])


def vault_has(*keys: str) -> bool:
    """True iff ALL keys resolve (env or vault)."""
    return all(vault_get(k) for k in keys if k)
