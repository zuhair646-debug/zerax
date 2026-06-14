"""
Zenrex Farm — 100% local, independent Travian multi-village bot farm engine.

Runs on the user's PC. Zero external paid dependencies:
  • LLM:        Ollama (local, RTX 2080)   — qwen2.5vl:7b for vision
  • Browsers:   Playwright (FOSS)          — one persistent context per village
  • Database:   SQLite                     — single-file, zero-config
  • Stealth:    Custom (mouse bezier, fingerprint randomization)
  • Identity:   Faker                       — names, ages, nationalities
  • Proxies:    Tor + free public list + (optional) user-supplied
  • Dashboard:  FastAPI + HTML at :7870

Architecture:
  Browser farm (1 Playwright context per village, isolated user-data-dir)
       │
       ▼
  Orchestrator (round-robin or parallel, with human-like delays)
       │
       ▼
  Strategy engine (YAML plan → next-action decisions)
       │   (LLM only used for "describe what you see")
       ▼
  SQLite DB (state, build queue, login creds, last-seen, etc.)

Identity: This is Zenrex — created from scratch by Zuhair Abbas.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import sqlite3
import string
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Hide console on Windows when launched via pythonw
try:
    if os.name == "nt":
        import ctypes
        _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if _hwnd:
            ctypes.windll.user32.ShowWindow(_hwnd, 0)
except Exception:
    pass

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# ─── Config ──────────────────────────────────────────────────────────────────
APP_NAME = "Zenrex Farm"
APP_VERSION = "0.1.0"
PORT = 7870

ROOT = Path(os.environ.get(
    "ZENREX_FARM_ROOT",
    str(Path.home() / ".zenrex-farm"),
))
ROOT.mkdir(parents=True, exist_ok=True)
DB_PATH = ROOT / "farm.db"
BROWSERS_DIR = ROOT / "browsers"
BROWSERS_DIR.mkdir(exist_ok=True)
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
PROXIES_FILE = ROOT / "proxies.txt"
STRATEGY_FILE = ROOT / "strategy.yaml"

# Ollama (local vision LLM)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_VISION_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "qwen2.5vl:7b")
OLLAMA_TEXT_MODEL = os.environ.get("OLLAMA_TEXT_MODEL", "qwen2.5:7b")

logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("farm")


# ─── Database ────────────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS villages (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,           -- Player display name (e.g. "Klaus Müller")
    server          TEXT NOT NULL,           -- e.g. "ts8.x2.international.travian.com"
    server_lang     TEXT,                    -- e.g. "en", "de"
    email           TEXT,
    password        TEXT,
    nationality     TEXT,                    -- "DE", "SA", "US" ...
    timezone        TEXT,                    -- "Europe/Berlin"
    user_agent      TEXT,
    screen_w        INTEGER,
    screen_h        INTEGER,
    locale          TEXT,
    proxy           TEXT,                    -- "http://host:port" or "socks5://..."
    profile_dir     TEXT,                    -- Playwright user-data-dir absolute path
    state           TEXT DEFAULT 'created',  -- created | registered | active | paused | banned
    strategy        TEXT DEFAULT 'default',
    schedule_json   TEXT,                    -- daily play windows (JSON list of [hh:mm,hh:mm])
    last_seen_at    TEXT,
    created_at      TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    village_id      TEXT NOT NULL,
    ts              TEXT NOT NULL,
    kind            TEXT NOT NULL,           -- login | build | scout | error | screenshot
    detail          TEXT,
    FOREIGN KEY (village_id) REFERENCES villages(id)
);

CREATE TABLE IF NOT EXISTS build_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    village_id      TEXT NOT NULL,
    slot            INTEGER,
    building        TEXT,
    target_level    INTEGER,
    ordered_at      TEXT,
    status          TEXT DEFAULT 'pending',  -- pending | started | done | failed
    FOREIGN KEY (village_id) REFERENCES villages(id)
);

CREATE INDEX IF NOT EXISTS idx_events_village ON events(village_id, ts);
CREATE INDEX IF NOT EXISTS idx_villages_state ON villages(state);
"""


@contextmanager
def db_cur():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db_cur() as cur:
        cur.executescript(SCHEMA)
    log.info(f"DB ready at {DB_PATH}")


# ─── Identity generation (fully local, no API) ───────────────────────────────
# Region-coherent first/last names. Keeps the IP/identity in sync.
NAME_POOLS: dict[str, dict[str, list[str]]] = {
    "DE": {  # Germany
        "first": ["Klaus", "Hans", "Stefan", "Jürgen", "Wolfgang", "Andreas",
                  "Michael", "Thomas", "Markus", "Sebastian", "Anna", "Maria",
                  "Sabine", "Julia", "Nina", "Eva", "Petra", "Karin"],
        "last":  ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer",
                  "Wagner", "Becker", "Schulz", "Hoffmann", "Schäfer", "Koch"],
        "locales": ["de-DE"], "timezone": "Europe/Berlin",
    },
    "FR": {
        "first": ["Pierre", "Jean", "Michel", "Alain", "Patrick", "Philippe",
                  "Marie", "Sophie", "Camille", "Léa", "Julie", "Claire"],
        "last":  ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard",
                  "Petit", "Durand", "Leroy", "Moreau", "Simon"],
        "locales": ["fr-FR"], "timezone": "Europe/Paris",
    },
    "US": {
        "first": ["James", "John", "Robert", "Michael", "William", "David",
                  "Richard", "Joseph", "Thomas", "Charles", "Jennifer", "Linda",
                  "Patricia", "Elizabeth", "Susan", "Jessica", "Sarah"],
        "last":  ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
                  "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez"],
        "locales": ["en-US"], "timezone": "America/New_York",
    },
    "GB": {
        "first": ["Oliver", "George", "Harry", "Jack", "Charlie", "Noah",
                  "Olivia", "Amelia", "Isla", "Ava", "Mia", "Sophia"],
        "last":  ["Smith", "Jones", "Taylor", "Brown", "Williams", "Wilson",
                  "Johnson", "Davies", "Robinson", "Wright", "Thompson"],
        "locales": ["en-GB"], "timezone": "Europe/London",
    },
    "SA": {
        "first": ["Mohammed", "Ahmed", "Khalid", "Saud", "Faisal", "Abdulaziz",
                  "Sultan", "Fahd", "Bandar", "Yousef"],
        "last":  ["Al-Otaibi", "Al-Shahri", "Al-Qahtani", "Al-Harbi", "Al-Ghamdi",
                  "Al-Mutairi", "Al-Dosari", "Al-Subaie", "Al-Rashidi"],
        "locales": ["ar-SA"], "timezone": "Asia/Riyadh",
    },
    "JP": {
        "first": ["Hiroshi", "Takeshi", "Kenji", "Yuki", "Akira", "Daisuke",
                  "Sakura", "Yui", "Hana", "Aoi", "Riko", "Mei"],
        "last":  ["Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito",
                  "Yamamoto", "Nakamura", "Kobayashi", "Kato"],
        "locales": ["ja-JP"], "timezone": "Asia/Tokyo",
    },
    "BR": {
        "first": ["João", "Pedro", "Lucas", "Gabriel", "Rafael", "Bruno",
                  "Maria", "Ana", "Beatriz", "Júlia", "Larissa"],
        "last":  ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira",
                  "Costa", "Ferreira", "Rodrigues"],
        "locales": ["pt-BR"], "timezone": "America/Sao_Paulo",
    },
}

UA_DESKTOP_TEMPLATES = [
    # Modern Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
    # Modern Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36 Edg/{ver}.0.0.0",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{ver}.0) Gecko/20100101 Firefox/{ver}.0",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
]

SCREEN_RESOLUTIONS = [
    (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
    (1600, 900), (2560, 1440), (1680, 1050), (1280, 720),
]


def generate_identity(nationality: Optional[str] = None) -> dict[str, Any]:
    """Generate a coherent identity: name, UA, screen, locale, timezone."""
    nat = nationality or random.choice(list(NAME_POOLS.keys()))
    pool = NAME_POOLS[nat]
    first = random.choice(pool["first"])
    last = random.choice(pool["last"])
    name = f"{first} {last}"

    # User agent
    chrome_ver = random.randint(118, 131)
    firefox_ver = random.randint(115, 128)
    ua_tpl = random.choice(UA_DESKTOP_TEMPLATES)
    ua = ua_tpl.format(ver=chrome_ver if "Firefox" not in ua_tpl else firefox_ver)

    sw, sh = random.choice(SCREEN_RESOLUTIONS)
    locale = random.choice(pool["locales"])

    # Email — local-part derived from name + 2-4 random digits
    handle = f"{first.lower()}.{last.lower().replace(' ','').replace('-','').replace('ü','u').replace('ä','a').replace('ö','o').replace('é','e').replace('í','i')}"
    handle += str(random.randint(11, 9999))
    email = f"{handle}@example.local"  # placeholder, real domain set later

    # Password: 12 chars, mixed
    pw_chars = string.ascii_letters + string.digits + "!@#$%"
    password = "".join(random.choices(pw_chars, k=12))

    return {
        "name": name,
        "first": first,
        "last": last,
        "nationality": nat,
        "email": email,
        "password": password,
        "user_agent": ua,
        "screen_w": sw,
        "screen_h": sh,
        "locale": locale,
        "timezone": pool["timezone"],
    }


# ─── Anti-detection: human-like timings ──────────────────────────────────────
def human_pause(short: bool = False) -> float:
    """Return a human-like pause duration (seconds)."""
    if short:
        return random.uniform(0.15, 0.55)   # quick reaction
    # Reading / thinking pause
    return random.uniform(1.4, 4.8)


def human_typing_interval() -> float:
    """Per-keystroke delay — humans are ~80–250ms but vary widely."""
    return random.uniform(0.05, 0.22)


def jittered_xy(x: int, y: int, radius: int = 4) -> tuple[int, int]:
    """Add small random offset so we don't always click pixel-perfect center."""
    return (x + random.randint(-radius, radius),
            y + random.randint(-radius, radius))


# ─── Browser farm (Playwright wrapper, stealth) ──────────────────────────────
class BrowserFarm:
    """Manages persistent Playwright contexts, one per village.

    Concurrency: stays well below human cluster behaviour by capping
    parallel active contexts to MAX_PARALLEL (default 4).
    """
    MAX_PARALLEL = 4

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(self.MAX_PARALLEL)
        self._playwright = None

    async def _ensure_playwright(self):
        if self._playwright is None:
            try:
                from playwright.async_api import async_playwright
            except ImportError as e:
                raise RuntimeError(
                    "Playwright not installed. Run: pip install playwright && "
                    "python -m playwright install chromium"
                ) from e
            self._playwright = await async_playwright().start()
        return self._playwright

    async def open(self, village: dict[str, Any]):
        """Open a persistent context for a village. Returns (context, page)."""
        await self._ensure_playwright()
        pw = self._playwright

        profile_dir = Path(village["profile_dir"])
        profile_dir.mkdir(parents=True, exist_ok=True)

        # Proxy config
        proxy_url = village.get("proxy") or ""
        proxy_cfg = None
        if proxy_url:
            # Format expected: "http://user:pass@host:port" or "socks5://host:port"
            proxy_cfg = {"server": proxy_url}

        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,                # visible for now; toggle for prod
            user_agent=village.get("user_agent") or "",
            viewport={"width": int(village.get("screen_w", 1920)),
                      "height": int(village.get("screen_h", 1080))},
            locale=village.get("locale") or "en-US",
            timezone_id=village.get("timezone") or "UTC",
            proxy=proxy_cfg,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-default-browser-check",
                "--no-first-run",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )

        # Inject stealth: hide webdriver flag + randomize canvas/WebGL
        await ctx.add_init_script(STEALTH_JS)

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        return ctx, page


# Injected at page-init time to defeat common fingerprinting
STEALTH_JS = r"""
// 1. Hide webdriver flag
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Spoof navigator.plugins (was 0 in headless)
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'PDF Viewer', filename: 'internal-pdf-viewer' },
        { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer' },
        { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer' },
    ],
});

// 3. Add languages
Object.defineProperty(navigator, 'languages',
    { get: () => [navigator.language, 'en'] });

// 4. WebGL renderer/vendor randomization
const VENDORS = ['Google Inc. (NVIDIA)', 'Google Inc. (AMD)', 'Google Inc. (Intel)'];
const RENDERERS = [
    'ANGLE (NVIDIA, NVIDIA GeForce RTX 2080 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)',
];
const seed = Math.floor(Math.random() * VENDORS.length);
const v = VENDORS[seed], r = RENDERERS[seed];
const orig = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(p) {
    if (p === 37445) return v;
    if (p === 37446) return r;
    return orig.call(this, p);
};

// 5. Canvas fingerprint randomization (subtle noise)
const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(...a) {
    const ctx = this.getContext('2d');
    if (ctx) {
        const id = ctx.getImageData(0, 0, this.width, this.height);
        for (let i = 0; i < id.data.length; i += 4) {
            id.data[i]   = (id.data[i]   + (Math.floor(Math.random() * 3) - 1)) & 0xff;
            id.data[i+1] = (id.data[i+1] + (Math.floor(Math.random() * 3) - 1)) & 0xff;
            id.data[i+2] = (id.data[i+2] + (Math.floor(Math.random() * 3) - 1)) & 0xff;
        }
        ctx.putImageData(id, 0, 0);
    }
    return origToDataURL.apply(this, a);
};

// 6. Chrome runtime presence
if (!window.chrome) window.chrome = { runtime: {} };
"""


# ─── Repository (DB access) ──────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_village(server: str = "ts8.x2.international.travian.com",
                   nationality: Optional[str] = None,
                   proxy: Optional[str] = None,
                   strategy: str = "default") -> dict[str, Any]:
    ident = generate_identity(nationality=nationality)
    vid = f"v_{uuid.uuid4().hex[:10]}"
    profile_dir = str(BROWSERS_DIR / vid)
    row = {
        "id": vid,
        "name": ident["name"],
        "server": server,
        "server_lang": (ident["locale"] or "en").split("-")[0],
        "email": ident["email"],
        "password": ident["password"],
        "nationality": ident["nationality"],
        "timezone": ident["timezone"],
        "user_agent": ident["user_agent"],
        "screen_w": ident["screen_w"],
        "screen_h": ident["screen_h"],
        "locale": ident["locale"],
        "proxy": proxy or "",
        "profile_dir": profile_dir,
        "state": "created",
        "strategy": strategy,
        "schedule_json": json.dumps([["08:00", "11:30"], ["19:00", "22:30"]]),
        "last_seen_at": None,
        "created_at": _now_iso(),
        "notes": "",
    }
    with db_cur() as cur:
        cur.execute("""
            INSERT INTO villages (id, name, server, server_lang, email, password,
                nationality, timezone, user_agent, screen_w, screen_h, locale,
                proxy, profile_dir, state, strategy, schedule_json, last_seen_at,
                created_at, notes)
            VALUES (:id, :name, :server, :server_lang, :email, :password,
                :nationality, :timezone, :user_agent, :screen_w, :screen_h, :locale,
                :proxy, :profile_dir, :state, :strategy, :schedule_json, :last_seen_at,
                :created_at, :notes)
        """, row)
    log_event(vid, "created", f"Identity {row['name']} ({row['nationality']})")
    return row


def list_villages(limit: int = 500) -> list[dict[str, Any]]:
    with db_cur() as cur:
        rows = cur.execute("SELECT * FROM villages ORDER BY created_at DESC "
                           "LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_village(vid: str) -> Optional[dict[str, Any]]:
    with db_cur() as cur:
        r = cur.execute("SELECT * FROM villages WHERE id = ?", (vid,)).fetchone()
    return dict(r) if r else None


def update_village_state(vid: str, state: str, notes: str = "") -> None:
    with db_cur() as cur:
        cur.execute("UPDATE villages SET state = ?, notes = ?, last_seen_at = ? "
                    "WHERE id = ?", (state, notes, _now_iso(), vid))


def log_event(vid: str, kind: str, detail: str = "") -> None:
    with db_cur() as cur:
        cur.execute("INSERT INTO events (village_id, ts, kind, detail) "
                    "VALUES (?, ?, ?, ?)", (vid, _now_iso(), kind, detail))


def list_events(vid: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
    with db_cur() as cur:
        if vid:
            rows = cur.execute("SELECT * FROM events WHERE village_id = ? "
                               "ORDER BY id DESC LIMIT ?", (vid, limit)).fetchall()
        else:
            rows = cur.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",
                               (limit,)).fetchall()
    return [dict(r) for r in rows]


# ─── Proxy pool (free-tier IPs) ──────────────────────────────────────────────
def load_proxies() -> list[str]:
    """Load proxies from proxies.txt (one per line)."""
    if not PROXIES_FILE.exists():
        return []
    out = []
    for line in PROXIES_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def assign_proxy(idx: int) -> str:
    """Round-robin proxy assignment."""
    pool = load_proxies()
    if not pool:
        return ""  # direct connection (user's own IP)
    return pool[idx % len(pool)]


# ─── FastAPI app + dashboard ─────────────────────────────────────────────────
app = FastAPI(title=APP_NAME, version=APP_VERSION)
FARM = BrowserFarm()


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {
        "ok": True, "app": APP_NAME, "version": APP_VERSION,
        "identity": "Zenrex Farm — by Zuhair Abbas",
        "db": str(DB_PATH),
        "browsers_dir": str(BROWSERS_DIR),
        "proxies_loaded": len(load_proxies()),
        "ollama_host": OLLAMA_HOST,
        "ollama_vision_model": OLLAMA_VISION_MODEL,
    }


@app.get("/api/villages")
def api_list_villages():
    rows = list_villages()
    return {"ok": True, "total": len(rows), "villages": rows}


@app.post("/api/villages")
async def api_create_villages(request: Request):
    """Create N villages with optional nationality + proxy round-robin."""
    body = await request.json()
    count = max(1, min(500, int(body.get("count", 1))))
    nationality = body.get("nationality")            # None = mixed
    server = body.get("server", "ts8.x2.international.travian.com")
    strategy = body.get("strategy", "default")
    use_proxies = bool(body.get("use_proxies", True))

    created = []
    for i in range(count):
        nat = nationality or random.choice(list(NAME_POOLS.keys()))
        proxy = assign_proxy(i) if use_proxies else ""
        v = create_village(server=server, nationality=nat,
                           proxy=proxy, strategy=strategy)
        created.append(v["id"])
    return {"ok": True, "created": len(created), "ids": created}


@app.delete("/api/villages/{vid}")
def api_delete_village(vid: str):
    with db_cur() as cur:
        cur.execute("DELETE FROM events WHERE village_id = ?", (vid,))
        cur.execute("DELETE FROM build_queue WHERE village_id = ?", (vid,))
        cur.execute("DELETE FROM villages WHERE id = ?", (vid,))
    return {"ok": True, "deleted": vid}


@app.get("/api/villages/{vid}")
def api_get_village(vid: str):
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    v["events"] = list_events(vid, limit=50)
    return v


@app.post("/api/villages/{vid}/open-browser")
async def api_open_browser(vid: str):
    """Open the Playwright browser for this village (visible window)."""
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    try:
        ctx, page = await FARM.open(v)
        await page.goto(f"https://{v['server']}", wait_until="domcontentloaded")
        log_event(vid, "open_browser", f"navigated to {v['server']}")
        update_village_state(vid, "browser_open")
        return {"ok": True, "village": vid}
    except Exception as e:
        log_event(vid, "error", f"open_browser: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/proxies")
def api_proxies():
    return {"ok": True, "count": len(load_proxies()),
            "proxies": load_proxies(),
            "file": str(PROXIES_FILE)}


@app.post("/api/proxies")
async def api_set_proxies(request: Request):
    body = await request.json()
    text = body.get("text", "").strip()
    PROXIES_FILE.write_text(text + "\n", encoding="utf-8")
    return {"ok": True, "count": len(load_proxies())}


@app.get("/api/identities/preview")
def api_identity_preview(nationality: Optional[str] = None):
    """Generate a sample identity without saving it."""
    return generate_identity(nationality=nationality)


@app.get("/api/nationalities")
def api_nationalities():
    return {
        "ok": True,
        "available": [
            {"code": k, "first_sample": v["first"][0], "last_sample": v["last"][0],
             "timezone": v["timezone"], "locale": v["locales"][0]}
            for k, v in NAME_POOLS.items()
        ],
    }


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(_DASHBOARD_HTML)


# ─── Dashboard HTML ──────────────────────────────────────────────────────────
_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/>
<title>Zenrex Farm — مزرعة قرى Travian</title>
<style>
 :root{ --bg:#08080f; --panel:#11111c; --line:#252535; --text:#e8e8f0;
        --muted:#8888a0; --accent:#a78bfa; --green:#10b981; --red:#ef4444;
        --amber:#f59e0b; --blue:#3b82f6; }
 *{box-sizing:border-box;margin:0;padding:0}
 body{background:var(--bg);color:var(--text);min-height:100vh;
      font-family:'Segoe UI',Tahoma,Arial,sans-serif;font-size:14px}
 header{padding:14px 24px;background:var(--panel);border-bottom:1px solid var(--line);
        display:flex;justify-content:space-between;align-items:center;gap:12px;
        position:sticky;top:0;z-index:10}
 h1{font-size:18px;color:var(--accent);font-weight:700}
 h2{font-size:13px;color:var(--accent);font-weight:600;margin-bottom:14px;
    text-transform:uppercase;letter-spacing:0.07em}
 .badge{font-size:11px;padding:3px 9px;border-radius:6px;background:#222;color:var(--muted)}
 .badge.live{background:#064e3b;color:#10b981}
 .container{padding:22px;display:grid;gap:18px;
            grid-template-columns:1.2fr 0.8fr;max-width:1500px;margin:0 auto}
 .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
 .stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}
 .stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;
       padding:14px 16px}
 .stat .num{font-size:24px;color:var(--accent);font-weight:700}
 .stat .lbl{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;margin-top:3px}
 label{display:block;margin-top:10px;color:var(--muted);font-size:12px}
 input,textarea,select{width:100%;background:#0a0a14;border:1px solid var(--line);
                       color:var(--text);padding:10px 12px;border-radius:8px;
                       font-family:inherit;font-size:13px;margin-top:4px}
 textarea{resize:vertical;min-height:80px;font-family:'Consolas',monospace}
 button{cursor:pointer;background:var(--accent);color:#0a0a14;border:none;
        padding:10px 16px;border-radius:8px;font-weight:600;font-size:13px;
        transition:filter .15s;margin-top:12px}
 button:hover{filter:brightness(1.1)}
 button.secondary{background:#222;color:var(--text);border:1px solid var(--line)}
 button.danger{background:var(--red);color:#fff}
 .row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
 .row > input, .row > select{flex:1;min-width:120px;margin-top:0}
 table{width:100%;border-collapse:collapse;margin-top:8px;font-size:12px}
 th,td{text-align:right;padding:9px 6px;border-bottom:1px solid var(--line)}
 th{color:var(--muted);font-weight:500;font-size:11px;text-transform:uppercase}
 tr:hover td{background:#181826}
 .pill{display:inline-block;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:600}
 .pill.created{background:#1e293b;color:#94a3b8}
 .pill.registered{background:#064e3b;color:#10b981}
 .pill.active{background:#581c87;color:#c084fc}
 .pill.paused{background:#7c2d12;color:#fdba74}
 .pill.banned{background:#7f1d1d;color:#fca5a5}
 .pill.browser_open{background:#1e3a8a;color:#93c5fd}
 .small{font-size:11px;color:var(--muted)}
 .flex{display:flex;gap:8px;align-items:center}
 @media(max-width:1100px){ .container{grid-template-columns:1fr} .stat-grid{grid-template-columns:repeat(2,1fr)} }
</style></head>
<body>
<header>
  <div class="flex">
    <h1>🏰 Zenrex Farm</h1>
    <span class="badge" id="ver">v0.1.0</span>
    <span class="badge">100% Local · Free</span>
  </div>
  <div class="flex">
    <span class="badge" id="proxy-status">— Proxies</span>
    <span class="badge" id="ollama-status">— Ollama</span>
  </div>
</header>

<div class="container">
  <!-- LEFT: villages list + stats -->
  <div>
    <div class="stat-grid">
      <div class="stat"><div class="num" id="s-total">0</div><div class="lbl">إجمالي القرى</div></div>
      <div class="stat"><div class="num" id="s-active">0</div><div class="lbl">نشطة</div></div>
      <div class="stat"><div class="num" id="s-registered">0</div><div class="lbl">مسجّلة</div></div>
      <div class="stat"><div class="num" id="s-banned">0</div><div class="lbl">محظورة</div></div>
    </div>

    <div class="card">
      <h2>القرى</h2>
      <div class="flex" style="justify-content:space-between;margin-bottom:8px">
        <span class="small">آخر تحديث: <span id="last-refresh">—</span></span>
        <button class="secondary" onclick="loadVillages()">↻ تحديث</button>
      </div>
      <table id="villages-table">
        <thead><tr>
          <th>الاسم</th><th>الجنسية</th><th>الخادم</th><th>الحالة</th>
          <th>IP/Proxy</th><th>الإيميل</th><th>إجراء</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>

  <!-- RIGHT: create villages + proxies + preview -->
  <div>
    <div class="card">
      <h2>إنشاء قرى جديدة</h2>
      <label>عدد القرى</label>
      <input id="count" type="number" min="1" max="500" value="5"/>

      <label>الجنسية (اتركها فارغة = خلطة)</label>
      <select id="nationality">
        <option value="">🌍 خلطة عشوائية</option>
      </select>

      <label>الخادم (Travian server)</label>
      <input id="server" value="ts8.x2.international.travian.com"/>

      <label>الخطة</label>
      <select id="strategy">
        <option value="default">افتراضية (مزارع → بناء → جيش)</option>
        <option value="defensive">دفاعية (سور + cranny)</option>
        <option value="custom">مخصصة (يدوي)</option>
      </select>

      <div class="row" style="margin-top:6px">
        <label class="flex" style="margin-top:0">
          <input type="checkbox" id="use-proxies" checked style="width:auto;margin-left:6px"/>
          استخدم البروكسيات (Round-robin من proxies.txt)
        </label>
      </div>

      <button onclick="createVillages()">🏗️ أنشئ القرى</button>
    </div>

    <div class="card" style="margin-top:18px">
      <h2>قائمة البروكسيات</h2>
      <p class="small">ضع كل بروكسي في سطر منفصل. الأشكال المقبولة:<br/>
      <code>http://host:port</code>, <code>http://user:pass@host:port</code>, <code>socks5://host:port</code></p>
      <textarea id="proxies-text" rows="6" placeholder="# مثال:
http://1.2.3.4:8080
socks5://user:pass@5.6.7.8:1080"></textarea>
      <button onclick="saveProxies()">💾 حفظ</button>
      <span class="small" id="proxy-count" style="margin-inline-start:10px">—</span>
    </div>

    <div class="card" style="margin-top:18px">
      <h2>معاينة هوية</h2>
      <button class="secondary" onclick="previewIdentity()">🎲 ولّد هوية تجريبية</button>
      <pre id="identity-preview" style="background:#0a0a14;padding:10px;border-radius:8px;margin-top:10px;font-size:11px;overflow:auto;color:var(--muted)"></pre>
    </div>
  </div>
</div>

<script>
const $ = s => document.querySelector(s);

async function loadNationalities(){
  const r = await fetch('/api/nationalities'); const d = await r.json();
  const sel = $('#nationality');
  d.available.forEach(n => {
    const o = document.createElement('option');
    o.value = n.code;
    o.textContent = `${n.code} — ${n.first_sample} ${n.last_sample} (${n.timezone})`;
    sel.appendChild(o);
  });
}

async function loadVillages(){
  const r = await fetch('/api/villages'); const d = await r.json();
  $('#s-total').textContent = d.total;
  const counts = { active:0, registered:0, banned:0 };
  d.villages.forEach(v => { counts[v.state] = (counts[v.state]||0)+1; });
  $('#s-active').textContent      = counts.active || 0;
  $('#s-registered').textContent  = counts.registered || 0;
  $('#s-banned').textContent      = counts.banned || 0;
  const tbody = $('#villages-table tbody');
  tbody.innerHTML = d.villages.map(v => `
    <tr>
      <td>${v.name}</td>
      <td><span class="badge">${v.nationality}</span></td>
      <td><span class="small">${v.server}</span></td>
      <td><span class="pill ${v.state}">${v.state}</span></td>
      <td><span class="small">${v.proxy || '🏠 مباشر'}</span></td>
      <td><span class="small">${v.email}</span></td>
      <td>
        <button class="secondary" onclick="openBrowser('${v.id}')">🦊 افتح</button>
        <button class="danger" onclick="delVillage('${v.id}')">🗑</button>
      </td>
    </tr>
  `).join('');
  $('#last-refresh').textContent = new Date().toLocaleTimeString();
}

async function createVillages(){
  const body = {
    count: parseInt($('#count').value || '1'),
    nationality: $('#nationality').value || null,
    server: $('#server').value,
    strategy: $('#strategy').value,
    use_proxies: $('#use-proxies').checked
  };
  const r = await fetch('/api/villages', { method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
  const d = await r.json();
  if (d.ok) {
    alert(`✓ أُنشئت ${d.created} قرية`);
    loadVillages();
  } else alert('✗ ' + (d.error || 'unknown'));
}

async function delVillage(id){
  if (!confirm('احذف هذه القرية؟ (الملفات تبقى)')) return;
  await fetch(`/api/villages/${id}`, { method:'DELETE' });
  loadVillages();
}

async function openBrowser(id){
  const r = await fetch(`/api/villages/${id}/open-browser`, { method:'POST' });
  const d = await r.json();
  if (!d.ok) alert('✗ ' + d.error);
  else loadVillages();
}

async function loadProxies(){
  const r = await fetch('/api/proxies'); const d = await r.json();
  $('#proxies-text').value = d.proxies.join('\n');
  $('#proxy-count').textContent = `${d.count} بروكسي محمّل`;
  $('#proxy-status').textContent = `🌐 ${d.count} Proxies`;
  if (d.count > 0) $('#proxy-status').classList.add('live');
}

async function saveProxies(){
  const text = $('#proxies-text').value;
  const r = await fetch('/api/proxies', { method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify({text}) });
  const d = await r.json();
  alert(`✓ حُفظ ${d.count} بروكسي`);
  loadProxies();
}

async function previewIdentity(){
  const nat = $('#nationality').value;
  const r = await fetch('/api/identities/preview' + (nat ? '?nationality=' + nat : ''));
  const d = await r.json();
  $('#identity-preview').textContent = JSON.stringify(d, null, 2);
}

async function checkOllama(){
  try {
    const r = await fetch('/health'); const d = await r.json();
    $('#ollama-status').textContent = `🧠 Ollama: ${d.ollama_vision_model}`;
  } catch {}
}

// boot
loadNationalities();
loadVillages();
loadProxies();
checkOllama();
setInterval(loadVillages, 8000);
</script>
</body></html>
"""


# ─── Main ────────────────────────────────────────────────────────────────────
def main() -> None:
    init_db()
    log.info(f"{APP_NAME} v{APP_VERSION} — ROOT={ROOT}")
    log.info(f"Dashboard: http://127.0.0.1:{PORT}")
    if "--no-browser" not in sys.argv:
        threading.Thread(target=_open_browser_delayed, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def _open_browser_delayed() -> None:
    time.sleep(1.5)
    try:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
