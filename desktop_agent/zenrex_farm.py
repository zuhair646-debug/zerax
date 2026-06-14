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
APP_VERSION = "0.4.0"
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
    notes           TEXT,
    -- Travian-specific fields
    region          TEXT DEFAULT 'ANY',      -- NW | NE | SW | SE | ANY
    coords_x        INTEGER,                 -- map x coordinate (set after registration)
    coords_y        INTEGER,                 -- map y coordinate
    tribe           TEXT,                    -- ROMANS | GAULS | TEUTONS | EGYPTIANS | HUNS
    is_personal     INTEGER DEFAULT 0,       -- 1 = user's own village, excluded from bot ops
    alliance        TEXT,                    -- alliance tag
    in_game_uid     TEXT,                    -- Travian internal player id
    capital_village TEXT                     -- name of the capital village in game
);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    village_id      TEXT NOT NULL,
    ts              TEXT NOT NULL,
    kind            TEXT NOT NULL,
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
    status          TEXT DEFAULT 'pending',
    FOREIGN KEY (village_id) REFERENCES villages(id)
);

CREATE TABLE IF NOT EXISTS pool_state (
    id              INTEGER PRIMARY KEY CHECK (id=1),
    running         INTEGER DEFAULT 0,
    max_parallel    INTEGER DEFAULT 10,
    rotation_min    INTEGER DEFAULT 15,
    cooldown_min    INTEGER DEFAULT 5,
    current_batch   TEXT,                    -- JSON list of village ids active now
    last_rotate_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_village ON events(village_id, ts);
CREATE INDEX IF NOT EXISTS idx_villages_state ON villages(state);
"""

# Indexes that reference newly-added columns (must run AFTER ALTER TABLE migrations)
POST_MIGRATION_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_villages_region ON villages(region)",
    "CREATE INDEX IF NOT EXISTS idx_villages_personal ON villages(is_personal)",
]

# Travian tribes — picked at registration time, affects play style
TRIBES = ["ROMANS", "GAULS", "TEUTONS", "EGYPTIANS", "HUNS"]
# Map regions — Travian world is divided into 4 quadrants by 0,0
REGIONS = ["NW", "NE", "SW", "SE", "ANY"]

# Coord ranges per region (Travian standard map -400..400)
REGION_BOUNDS = {
    "NW": (-400, -1,  1, 400),   # x<0, y>0
    "NE": (1, 400,    1, 400),   # x>0, y>0
    "SW": (-400, -1, -400, -1),  # x<0, y<0
    "SE": (1, 400,   -400, -1),  # x>0, y<0
    "ANY": (-400, 400, -400, 400),
}


def pick_region_coords(region: str) -> tuple[int, int]:
    """Return a random (x, y) tuple inside the chosen region — Travian
    registration usually lets you specify a preferred quadrant."""
    if region not in REGION_BOUNDS:
        region = "ANY"
    x_lo, x_hi, y_lo, y_hi = REGION_BOUNDS[region]
    return random.randint(x_lo, x_hi), random.randint(y_lo, y_hi)


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
        # Migrations for existing DBs (idempotent — ignore errors if column exists)
        for col_sql in [
            "ALTER TABLE villages ADD COLUMN region TEXT DEFAULT 'ANY'",
            "ALTER TABLE villages ADD COLUMN coords_x INTEGER",
            "ALTER TABLE villages ADD COLUMN coords_y INTEGER",
            "ALTER TABLE villages ADD COLUMN tribe TEXT",
            "ALTER TABLE villages ADD COLUMN is_personal INTEGER DEFAULT 0",
            "ALTER TABLE villages ADD COLUMN alliance TEXT",
            "ALTER TABLE villages ADD COLUMN in_game_uid TEXT",
            "ALTER TABLE villages ADD COLUMN capital_village TEXT",
        ]:
            try:
                cur.execute(col_sql)
            except sqlite3.OperationalError:
                pass
        # Indexes that depend on migrated columns
        for idx_sql in POST_MIGRATION_INDEXES:
            try:
                cur.execute(idx_sql)
            except sqlite3.OperationalError:
                pass
        # Seed pool_state row
        cur.execute("INSERT OR IGNORE INTO pool_state (id, running, max_parallel, "
                    "rotation_min, cooldown_min) VALUES (1, 0, 10, 15, 5)")
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
                  "Sultan", "Fahd", "Bandar", "Yousef", "Ali", "Omar", "Salman",
                  "Turki", "Nawaf", "Majed", "Bader", "Waleed"],
        "last":  ["Al-Otaibi", "Al-Shahri", "Al-Qahtani", "Al-Harbi", "Al-Ghamdi",
                  "Al-Mutairi", "Al-Dosari", "Al-Subaie", "Al-Rashidi",
                  "Al-Anazi", "Al-Zahrani", "Al-Shamri", "Al-Juhani"],
        "locales": ["ar-SA"], "timezone": "Asia/Riyadh",
    },
    "EG": {  # Egypt
        "first": ["Ahmed", "Mohamed", "Mahmoud", "Mostafa", "Omar", "Karim",
                  "Hassan", "Hossam", "Tarek", "Sherif", "Yasmin", "Nour",
                  "Salma", "Mariam", "Hana", "Farida"],
        "last":  ["El-Masry", "Hassan", "Mahmoud", "Ali", "Ibrahim", "Said",
                  "Abdelrahman", "El-Sayed", "Mostafa", "Khalil", "Fouad"],
        "locales": ["ar-EG"], "timezone": "Africa/Cairo",
    },
    "AE": {  # UAE
        "first": ["Hamdan", "Mansour", "Saif", "Hamad", "Rashid", "Khalifa",
                  "Sultan", "Mohammed", "Latifa", "Fatima", "Mariam", "Reem"],
        "last":  ["Al-Maktoum", "Al-Nahyan", "Al-Marri", "Al-Ali", "Al-Hashimi",
                  "Al-Suwaidi", "Al-Falasi", "Al-Mazrouei"],
        "locales": ["ar-AE"], "timezone": "Asia/Dubai",
    },
    "KW": {  # Kuwait
        "first": ["Nasser", "Jaber", "Saad", "Mishal", "Sabah", "Anwar",
                  "Mohammed", "Yousef", "Dana", "Reem", "Latifa"],
        "last":  ["Al-Sabah", "Al-Mutawa", "Al-Rashed", "Al-Adwani",
                  "Al-Khaled", "Al-Mubarak", "Al-Saqr"],
        "locales": ["ar-KW"], "timezone": "Asia/Kuwait",
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
    "TR": {  # Turkey
        "first": ["Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin", "Hasan",
                  "İbrahim", "Yusuf", "Emre", "Ayşe", "Fatma", "Zeynep"],
        "last":  ["Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız",
                  "Yıldırım", "Öztürk", "Aydın"],
        "locales": ["tr-TR"], "timezone": "Europe/Istanbul",
    },
    "RU": {
        "first": ["Alexander", "Sergei", "Dmitri", "Andrei", "Mikhail", "Ivan",
                  "Nikolai", "Vladimir", "Anna", "Elena", "Maria", "Olga"],
        "last":  ["Ivanov", "Smirnov", "Kuznetsov", "Popov", "Vasiliev",
                  "Petrov", "Sokolov", "Mikhailov"],
        "locales": ["ru-RU"], "timezone": "Europe/Moscow",
    },
}

# Convenience presets
ARABIC_NATIONALITIES = ["SA", "EG", "AE", "KW"]
ENGLISH_NATIONALITIES = ["US", "GB"]
EUROPEAN_NATIONALITIES = ["DE", "FR", "GB", "RU", "TR"]
ALL_NATIONALITIES = list(NAME_POOLS.keys())

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


def bezier_curve(start: tuple[int, int], end: tuple[int, int],
                 n_points: int = 25) -> list[tuple[int, int]]:
    """Generate a quadratic-bezier path between two points with a random
    control point — produces human-looking curved mouse motion (not linear)."""
    sx, sy = start
    ex, ey = end
    # Control point is offset perpendicular to the line by a random amount
    mx, my = (sx + ex) / 2, (sy + ey) / 2
    dx, dy = ex - sx, ey - sy
    perp = (-dy, dx)
    length = max(1.0, (perp[0] ** 2 + perp[1] ** 2) ** 0.5)
    norm = (perp[0] / length, perp[1] / length)
    offset = random.uniform(-0.20, 0.20) * length * 0.5
    cx, cy = mx + norm[0] * offset, my + norm[1] * offset
    pts: list[tuple[int, int]] = []
    for i in range(n_points + 1):
        t = i / n_points
        # add micro-jitter every step
        jx = random.uniform(-0.4, 0.4)
        jy = random.uniform(-0.4, 0.4)
        x = (1 - t) * (1 - t) * sx + 2 * (1 - t) * t * cx + t * t * ex + jx
        y = (1 - t) * (1 - t) * sy + 2 * (1 - t) * t * cy + t * t * ey + jy
        pts.append((int(round(x)), int(round(y))))
    return pts


async def human_move_to(page, x: int, y: int, *, steps: int = 25) -> None:
    """Bezier-curve mouse movement that mimics human motion."""
    # Current mouse position is unknown via Playwright; use start ~ center
    start = (page.viewport_size.get("width", 1280) // 2,
             page.viewport_size.get("height", 720) // 2)
    end = jittered_xy(x, y, radius=3)
    path = bezier_curve(start, end, n_points=steps)
    for px, py in path:
        await page.mouse.move(px, py, steps=1)
        # Variable speed: faster in middle, slower at start/end
        await asyncio.sleep(random.uniform(0.005, 0.025))


async def human_type(page, selector: str, text: str) -> None:
    """Type text with realistic per-key delays + occasional "thinking" pauses."""
    await page.click(selector)
    await asyncio.sleep(random.uniform(0.2, 0.6))
    for i, ch in enumerate(text):
        await page.keyboard.type(ch, delay=int(human_typing_interval() * 1000))
        # Every 8-15 chars, "think" briefly
        if i and i % random.randint(8, 15) == 0:
            await asyncio.sleep(random.uniform(0.25, 0.95))


# ─── Per-village fingerprint seed (deterministic per village) ────────────────
def fingerprint_seed(village_id: str) -> dict[str, Any]:
    """Generate a deterministic but unique fingerprint profile per village.
    Same village always gets the same seed — important for consistency
    across sessions (otherwise Travian would see a "new device" every login)."""
    rng = random.Random(village_id)
    return {
        "hw_concurrency": rng.choice([2, 4, 6, 8, 8, 12, 16]),
        "device_memory":  rng.choice([4, 8, 8, 16, 16, 32]),
        "color_depth":    rng.choice([24, 24, 24, 30]),
        "max_touch":      rng.choice([0, 0, 0, 5, 10]),  # mostly desktop
        "battery":        rng.uniform(0.21, 0.97),
        "charging":       rng.choice([True, False]),
        "audio_seed":     rng.random(),
        "fonts_seed":     rng.random(),
        "canvas_seed":    rng.random(),
    }


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
                # Block WebRTC IP leak (browser will not expose real IP via STUN)
                "--disable-features=WebRtcHideLocalIpsWithMdns",
                "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
                "--disable-web-security",   # only inside isolated profile
            ],
        )

        # Inject stealth 2.0 with village-specific seeds
        fp = fingerprint_seed(village["id"])
        stealth_js = build_stealth_js(fp, village)
        await ctx.add_init_script(stealth_js)

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        return ctx, page


# ── Stealth 2.0 — defeats 17 fingerprinting vectors ─────────────────────────
def build_stealth_js(fp: dict[str, Any], village: dict[str, Any]) -> str:
    """Compose the full stealth JS payload using per-village seeds."""
    hw = fp["hw_concurrency"]
    dm = fp["device_memory"]
    cd = fp["color_depth"]
    mt = fp["max_touch"]
    bat = fp["battery"]
    ch = "true" if fp["charging"] else "false"
    audio_s = fp["audio_seed"]
    fonts_s = fp["fonts_seed"]
    canvas_s = fp["canvas_seed"]
    locale = village.get("locale") or "en-US"
    lang = locale.split("-")[0]

    return f"""(() => {{
// ═══ STEALTH 2.0 — village fingerprint isolation ═══
// 1. Hide webdriver flag (basic)
Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});

// 2. Plugins spoofing
Object.defineProperty(navigator, 'plugins', {{
  get: () => [
    {{ name: 'PDF Viewer',          filename: 'internal-pdf-viewer' }},
    {{ name: 'Chrome PDF Viewer',   filename: 'internal-pdf-viewer' }},
    {{ name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer' }},
    {{ name: 'Microsoft Edge PDF Viewer', filename: 'internal-pdf-viewer' }},
    {{ name: 'WebKit built-in PDF', filename: 'internal-pdf-viewer' }},
  ],
}});

// 3. Languages
Object.defineProperty(navigator, 'languages', {{ get: () => ['{locale}','{lang}','en'] }});

// 4. Hardware concurrency (CPU cores)
Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {hw} }});

// 5. Device memory
Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {dm} }});

// 6. Max touch points
Object.defineProperty(navigator, 'maxTouchPoints', {{ get: () => {mt} }});

// 7. Screen color depth
Object.defineProperty(screen, 'colorDepth', {{ get: () => {cd} }});
Object.defineProperty(screen, 'pixelDepth', {{ get: () => {cd} }});

// 8. Battery API spoofing
if (navigator.getBattery) {{
  navigator.getBattery = async () => ({{
    charging: {ch},
    chargingTime: {ch} ? Infinity : 0,
    dischargingTime: Math.floor({bat} * 14400),
    level: {bat:.4f},
    addEventListener: () => {{}},
    removeEventListener: () => {{}},
    dispatchEvent: () => true,
  }});
}}

// 9. WebGL vendor + renderer (must look plausible)
const _WEBGL_VENDOR = 'Google Inc. (NVIDIA)';
const _WEBGL_RENDERER = 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0, D3D11)';
const _origGetParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(p) {{
  if (p === 37445) return _WEBGL_VENDOR;
  if (p === 37446) return _WEBGL_RENDERER;
  return _origGetParameter.call(this, p);
}};
if (typeof WebGL2RenderingContext !== 'undefined') {{
  const _orig2 = WebGL2RenderingContext.prototype.getParameter;
  WebGL2RenderingContext.prototype.getParameter = function(p) {{
    if (p === 37445) return _WEBGL_VENDOR;
    if (p === 37446) return _WEBGL_RENDERER;
    return _orig2.call(this, p);
  }};
}}

// 10. Canvas fingerprint noise (deterministic per village)
const _CANVAS_NOISE_SEED = {canvas_s};
let _canvasRng = 0;
const _seedRand = (s) => {{ _canvasRng = (s * 9301 + 49297) % 233280; return _canvasRng / 233280; }};
const _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(...args) {{
  const ctx = this.getContext('2d');
  if (ctx) {{
    try {{
      const id = ctx.getImageData(0, 0, this.width, this.height);
      let s = _CANVAS_NOISE_SEED * 1000000;
      for (let i = 0; i < id.data.length; i += 4) {{
        s = _seedRand(s + i);
        id.data[i]   = (id.data[i]   + (Math.floor(s * 3) - 1)) & 0xff;
        id.data[i+1] = (id.data[i+1] + (Math.floor(_seedRand(s+1) * 3) - 1)) & 0xff;
        id.data[i+2] = (id.data[i+2] + (Math.floor(_seedRand(s+2) * 3) - 1)) & 0xff;
      }}
      ctx.putImageData(id, 0, 0);
    }} catch (e) {{}}
  }}
  return _origToDataURL.apply(this, args);
}};

// 11. AudioContext fingerprint noise
const _AUDIO_NOISE = {audio_s};
const _patchAudio = (AC) => {{
  if (!AC || !AC.prototype || !AC.prototype.createOscillator) return;
  const _origGetChannelData = AudioBuffer.prototype.getChannelData;
  AudioBuffer.prototype.getChannelData = function(...args) {{
    const data = _origGetChannelData.apply(this, args);
    for (let i = 0; i < data.length; i += 100) {{
      data[i] += (_AUDIO_NOISE - 0.5) * 1e-7;
    }}
    return data;
  }};
}};
_patchAudio(window.AudioContext);
_patchAudio(window.webkitAudioContext);

// 12. Font enumeration spoofing (Font Detection via document.fonts)
const _FONTS_SEED = {fonts_s};
if (document.fonts && document.fonts.check) {{
  const _origCheck = document.fonts.check.bind(document.fonts);
  // Decide which "system" fonts this village pretends to have
  const _AVAILABLE = new Set();
  const _ALL_FONTS = ['Arial','Verdana','Tahoma','Courier New','Times New Roman',
    'Georgia','Trebuchet MS','Lucida Sans Unicode','Comic Sans MS','Impact',
    'Calibri','Cambria','Consolas','Segoe UI','Helvetica','Roboto','Open Sans',
    'Noto Sans','Source Sans Pro','Ubuntu','Liberation Sans'];
  _ALL_FONTS.forEach((f, i) => {{
    if (((_FONTS_SEED * 1000 + i) * 9301 % 233280) / 233280 < 0.6) {{
      _AVAILABLE.add(f.toLowerCase());
    }}
  }});
  document.fonts.check = function(spec, text) {{
    const m = String(spec).match(/['"]([^'"]+)['"]/);
    if (m && !_AVAILABLE.has(m[1].toLowerCase())) return false;
    return _origCheck(spec, text);
  }};
}}

// 13. Permissions API spoofing (notifications, geolocation, etc.)
const _origQuery = navigator.permissions && navigator.permissions.query;
if (_origQuery) {{
  navigator.permissions.query = (params) => {{
    if (params && params.name === 'notifications') {{
      return Promise.resolve({{ state: 'prompt' }});
    }}
    return _origQuery.call(navigator.permissions, params);
  }};
}}

// 14. Speech synthesis voices fake (some sites fingerprint this)
const _origVoices = window.speechSynthesis && window.speechSynthesis.getVoices;
if (_origVoices) {{
  window.speechSynthesis.getVoices = () => [
    {{ name: 'Google US English', lang: '{lang}-US', default: true, voiceURI: 'Google US English' }},
    {{ name: 'Microsoft David',   lang: '{lang}-US', default: false, voiceURI: 'Microsoft David Desktop' }},
  ];
}}

// 15. Chrome runtime
if (!window.chrome) window.chrome = {{ runtime: {{}} }};
if (!window.chrome.runtime) window.chrome.runtime = {{}};

// 16. WebRTC: prevent stun-based IP leak
const _origRTC = window.RTCPeerConnection;
if (_origRTC) {{
  window.RTCPeerConnection = function(...a) {{
    if (a[0] && a[0].iceServers) a[0].iceServers = [];
    return new _origRTC(...a);
  }};
  window.RTCPeerConnection.prototype = _origRTC.prototype;
}}

// 17. iframe contentWindow defence
try {{
  const _origIframe = HTMLIFrameElement.prototype;
  const _origContentWin = Object.getOwnPropertyDescriptor(_origIframe, 'contentWindow');
  if (_origContentWin) {{
    Object.defineProperty(_origIframe, 'contentWindow', {{
      get: function() {{
        const w = _origContentWin.get.call(this);
        if (w) {{
          try {{ Object.defineProperty(w.navigator, 'webdriver', {{ get: () => undefined }}); }} catch(e) {{}}
        }}
        return w;
      }},
    }});
  }}
}} catch(e) {{}}

// 18. Outerwidth/outerheight match window (some bots leave at 0)
Object.defineProperty(window, 'outerWidth',  {{ get: () => window.innerWidth }});
Object.defineProperty(window, 'outerHeight', {{ get: () => window.innerHeight + 75 }});

}})();
"""


# Placeholder kept for backward-compat (legacy use)
STEALTH_JS = "/* stealth-1 deprecated, replaced by build_stealth_js() */"


# ─── Repository (DB access) ──────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_village(server: str = "ts8.x2.international.travian.com",
                   nationality: Optional[str] = None,
                   proxy: Optional[str] = None,
                   strategy: str = "default",
                   region: str = "ANY",
                   tribe: Optional[str] = None,
                   is_personal: bool = False) -> dict[str, Any]:
    ident = generate_identity(nationality=nationality)
    vid = f"v_{uuid.uuid4().hex[:10]}"
    profile_dir = str(BROWSERS_DIR / vid)
    cx, cy = pick_region_coords(region)
    chosen_tribe = tribe or random.choice(TRIBES)
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
        "region": region,
        "coords_x": cx,
        "coords_y": cy,
        "tribe": chosen_tribe,
        "is_personal": 1 if is_personal else 0,
        "alliance": None,
        "in_game_uid": None,
        "capital_village": None,
    }
    with db_cur() as cur:
        cur.execute("""
            INSERT INTO villages (id, name, server, server_lang, email, password,
                nationality, timezone, user_agent, screen_w, screen_h, locale,
                proxy, profile_dir, state, strategy, schedule_json, last_seen_at,
                created_at, notes, region, coords_x, coords_y, tribe, is_personal,
                alliance, in_game_uid, capital_village)
            VALUES (:id, :name, :server, :server_lang, :email, :password,
                :nationality, :timezone, :user_agent, :screen_w, :screen_h, :locale,
                :proxy, :profile_dir, :state, :strategy, :schedule_json, :last_seen_at,
                :created_at, :notes, :region, :coords_x, :coords_y, :tribe, :is_personal,
                :alliance, :in_game_uid, :capital_village)
        """, row)
    log_event(vid, "created",
              f"{row['name']} ({row['nationality']}, {chosen_tribe}, "
              f"region={region}, ({cx},{cy})"
              f"{' [PERSONAL]' if is_personal else ''})")
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


# ─── Free proxy auto-fetcher (scrape + test) ─────────────────────────────────
FREE_PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks5.txt",
    "https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt",
]


async def fetch_free_proxies(max_total: int = 500,
                             test_concurrency: int = 30,
                             timeout_s: float = 4.0) -> list[str]:
    """Pull proxies from multiple free sources, dedupe, then live-test them.
    Returns only the ones that successfully reach https://httpbin.org/ip
    within `timeout_s`. Heavy operation — call at most once per hour."""
    import urllib.request
    import urllib.error

    candidates: set[str] = set()
    for url in FREE_PROXY_SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ZenrexFarm/0.1"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
            scheme = "socks5" if "socks5" in url.lower() else "http"
            for line in body.splitlines():
                line = line.strip().split("#")[0].strip()
                if not line:
                    continue
                if "://" in line:
                    candidates.add(line)
                elif ":" in line:
                    candidates.add(f"{scheme}://{line}")
                if len(candidates) >= max_total * 3:
                    break
        except Exception as e:
            log.warning(f"proxy source failed: {url}: {e}")

    log.info(f"fetched {len(candidates)} candidate proxies, now testing…")
    # NOTE: Free proxies are mostly dead. We test by simply opening a TCP socket
    # — full HTTPS handshake test takes 30+ s for 1000 proxies.
    import socket

    def quick_check(addr: str) -> Optional[str]:
        try:
            from urllib.parse import urlparse
            u = urlparse(addr)
            host, port = u.hostname, u.port or 1080
            if not host:
                return None
            with socket.create_connection((host, int(port)), timeout=timeout_s):
                return addr
        except Exception:
            return None

    # Thread-pool for parallel testing
    from concurrent.futures import ThreadPoolExecutor
    alive: list[str] = []
    with ThreadPoolExecutor(max_workers=test_concurrency) as ex:
        for result in ex.map(quick_check, list(candidates)[:max_total]):
            if result:
                alive.append(result)

    log.info(f"alive proxies: {len(alive)} / {min(max_total, len(candidates))}")
    return alive


# ─── Free email via Mail.tm (no signup, no API key) ─────────────────────────
async def mailtm_create_account() -> dict[str, str]:
    """Create a temporary email + password via mail.tm. Returns
    {email, password, token, account_id}. Mailbox lasts ~7 days idle."""
    import urllib.request
    import urllib.error

    # 1) Pick a domain
    try:
        with urllib.request.urlopen("https://api.mail.tm/domains?page=1",
                                    timeout=8) as resp:
            domains = json.loads(resp.read())
        domain = (domains.get("hydra:member") or [{}])[0].get("domain")
    except Exception as e:
        raise RuntimeError(f"mail.tm domains: {e}")
    if not domain:
        raise RuntimeError("no mail.tm domain available")

    # 2) Random local-part
    local = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
    email = f"{local}@{domain}"
    password = "".join(random.choices(string.ascii_letters + string.digits, k=14))

    # 3) Create account
    body = json.dumps({"address": email, "password": password}).encode()
    req = urllib.request.Request(
        "https://api.mail.tm/accounts", data=body,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            acct = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"mail.tm create failed: {e.read()[:120]}")

    # 4) Token
    tok_body = json.dumps({"address": email, "password": password}).encode()
    req = urllib.request.Request(
        "https://api.mail.tm/token", data=tok_body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        tok = json.loads(resp.read())

    return {
        "email": email,
        "password": password,
        "token": tok.get("token", ""),
        "account_id": acct.get("id", ""),
    }


async def mailtm_read_inbox(token: str) -> list[dict[str, Any]]:
    """List messages in the inbox (newest first)."""
    import urllib.request
    req = urllib.request.Request(
        "https://api.mail.tm/messages?page=1",
        headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        return data.get("hydra:member") or []
    except Exception:
        return []


async def mailtm_read_message(token: str, msg_id: str) -> dict[str, Any]:
    import urllib.request
    req = urllib.request.Request(
        f"https://api.mail.tm/messages/{msg_id}",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read())


# ─── Multi-provider email rotation (no signup, all free) ─────────────────────
EMAIL_PROVIDERS = ["mail.tm", "1secmail", "guerrilla", "internal"]


async def email_1secmail() -> dict[str, str]:
    """1secmail.com — no registration, just GET endpoints."""
    import urllib.request
    # 1) Get available domains
    try:
        with urllib.request.urlopen(
            "https://www.1secmail.com/api/v1/?action=getDomainList",
            timeout=6) as r:
            domains = json.loads(r.read())
    except Exception:
        domains = ["1secmail.com", "1secmail.org", "1secmail.net"]
    domain = random.choice(domains)
    local = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
    email = f"{local}@{domain}"
    password = "".join(random.choices(string.ascii_letters + string.digits, k=14))
    # 1secmail doesn't need creation — mailbox is created on first poll
    return {"email": email, "password": password, "token": f"1sec:{local}:{domain}",
            "account_id": local, "provider": "1secmail"}


async def email_guerrilla() -> dict[str, str]:
    """Guerrilla Mail — free, no signup."""
    import urllib.request
    try:
        with urllib.request.urlopen(
            "https://api.guerrillamail.com/ajax.php?f=get_email_address",
            timeout=6) as r:
            d = json.loads(r.read())
        email = d.get("email_addr", "")
        sid = d.get("sid_token", "")
        if not email:
            raise RuntimeError("no email returned")
    except Exception as e:
        raise RuntimeError(f"guerrilla failed: {e}")
    password = "".join(random.choices(string.ascii_letters + string.digits, k=14))
    return {"email": email, "password": password,
            "token": f"guerrilla:{sid}", "account_id": sid,
            "provider": "guerrilla"}


async def email_internal(village_id: str) -> dict[str, str]:
    """Last-resort: generate a plausible-looking email using village id +
    a popular free-email domain. NOT a real mailbox — only useful when the
    target site doesn't verify."""
    handle = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    domain = random.choice([
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
        "icloud.com", "yandex.com", "proton.me", "tutanota.com",
    ])
    email = f"{handle}{village_id[-4:]}@{domain}"
    password = "".join(random.choices(string.ascii_letters + string.digits, k=14))
    return {"email": email, "password": password,
            "token": "", "account_id": "", "provider": "internal-placeholder"}


async def create_email_for(village_id: str,
                           prefer: Optional[str] = None) -> dict[str, str]:
    """Round-robin/fall-through across providers. `prefer` = mail.tm | 1secmail |
    guerrilla | internal. None = random."""
    order = [prefer] if prefer else random.sample(EMAIL_PROVIDERS, len(EMAIL_PROVIDERS))
    last_err = ""
    for p in order:
        try:
            if p == "mail.tm":
                acct = await mailtm_create_account()
                acct["provider"] = "mail.tm"
                return acct
            if p == "1secmail":
                return await email_1secmail()
            if p == "guerrilla":
                return await email_guerrilla()
            if p == "internal":
                return await email_internal(village_id)
        except Exception as e:
            last_err = f"{p}: {e}"
            log.warning(f"email provider {p} failed: {e}")
    raise RuntimeError(f"all email providers failed. last: {last_err}")


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
def api_list_villages(server: Optional[str] = None):
    rows = list_villages()
    if server:
        rows = [r for r in rows if r.get("server") == server]
    return {"ok": True, "total": len(rows), "villages": rows}


@app.post("/api/villages")
async def api_create_villages(request: Request):
    """Create N villages with name preset, region, tribe, optional auto-email."""
    body = await request.json()
    count = max(1, min(500, int(body.get("count", 1))))
    server = body.get("server", "ts8.x2.international.travian.com")
    strategy = body.get("strategy", "default")
    use_proxies = bool(body.get("use_proxies", True))
    auto_email = bool(body.get("auto_email", False))
    region = (body.get("region") or "ANY").upper()
    tribe_preset = (body.get("tribe") or "MIXED").upper()
    is_personal = bool(body.get("is_personal", False))

    preset = (body.get("name_preset") or "mixed").lower()
    if preset == "arabic":
        pool = ARABIC_NATIONALITIES
    elif preset == "english":
        pool = ENGLISH_NATIONALITIES
    elif preset == "european":
        pool = EUROPEAN_NATIONALITIES
    elif preset in ("mixed", "all"):
        pool = ALL_NATIONALITIES
    elif preset.upper() in NAME_POOLS:
        pool = [preset.upper()]
    else:
        pool = ALL_NATIONALITIES

    created = []
    for i in range(count):
        nat = random.choice(pool)
        proxy = assign_proxy(i) if use_proxies else ""
        tribe = (random.choice(TRIBES)
                 if tribe_preset in ("MIXED", "ANY", "") else tribe_preset)
        v = create_village(server=server, nationality=nat,
                           proxy=proxy, strategy=strategy,
                           region=region, tribe=tribe,
                           is_personal=is_personal)
        if auto_email:
            try:
                acct = await create_email_for(v["id"])
                with db_cur() as cur:
                    cur.execute("UPDATE villages SET email = ?, notes = ? WHERE id = ?",
                                (acct["email"],
                                 (v.get("notes") or "") +
                                 f"\nemail_provider={acct['provider']}",
                                 v["id"]))
                log_event(v["id"], "email_attached",
                          f"{acct['provider']}: {acct['email']}")
            except Exception as e:
                log_event(v["id"], "email_failed", str(e))
        created.append(v["id"])
    return {"ok": True, "created": len(created), "ids": created}


@app.patch("/api/villages/{vid}")
async def api_update_village(vid: str, request: Request):
    """Update fields (region, tribe, is_personal, coords, alliance, state...)."""
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    body = await request.json()
    allowed = ["region", "tribe", "is_personal", "coords_x", "coords_y",
               "alliance", "state", "strategy", "notes", "proxy", "email"]
    updates = {k: body[k] for k in allowed if k in body}
    if not updates:
        return {"ok": True, "updated": 0}
    if "is_personal" in updates:
        updates["is_personal"] = 1 if updates["is_personal"] else 0
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = vid
    with db_cur() as cur:
        cur.execute(f"UPDATE villages SET {set_clause} WHERE id = :id", updates)
    return {"ok": True, "updated": len(updates) - 1}


# ─── Browser Pool Manager — concurrent slots + rotation ──────────────────────
class BrowserPool:
    """Cycles N villages through active browser slots.

    Logic:
      • At any time, max_parallel villages are 'active' (logged-in).
      • Every rotation_min minutes: log-out current batch, wait cooldown_min,
        log-in next batch (round-robin by last_seen_at).
      • Personal villages (is_personal=1) are NEVER included.
      • Goal: cover 100 villages in ~10 cycles × 15 min = 2.5 h per cycle.
    """
    def __init__(self) -> None:
        self.task: Optional[asyncio.Task] = None
        self.cancel_event = asyncio.Event()

    def _read_config(self) -> dict[str, Any]:
        with db_cur() as cur:
            r = cur.execute("SELECT * FROM pool_state WHERE id=1").fetchone()
        return dict(r) if r else {}

    def _write_config(self, **kw) -> None:
        if not kw:
            return
        sets = ", ".join(f"{k} = :{k}" for k in kw)
        kw["id"] = 1
        with db_cur() as cur:
            cur.execute(f"UPDATE pool_state SET {sets} WHERE id = 1", kw)

    async def _login_batch(self, vids: list[str]) -> None:
        log.info(f"[pool] login batch ({len(vids)}): {vids}")
        for vid in vids:
            log_event(vid, "pool_login", "slot active for next rotation")
            # TODO: real implementation — open Playwright browser + run strategy
            #   ctx, page = await FARM.open(get_village(vid))
            #   await execute_strategy(get_village(vid), ctx, page)
        self._write_config(current_batch=json.dumps(vids),
                           last_rotate_at=_now_iso())

    async def _logout_batch(self, vids: list[str]) -> None:
        log.info(f"[pool] logout batch ({len(vids)})")
        for vid in vids:
            log_event(vid, "pool_logout", "slot freed")

    async def _loop(self) -> None:
        log.info("[pool] orchestrator started")
        cycle = 0
        while not self.cancel_event.is_set():
            cfg = self._read_config()
            max_par = int(cfg.get("max_parallel", 10))
            rot_min = int(cfg.get("rotation_min", 15))
            cool_min = int(cfg.get("cooldown_min", 5))

            with db_cur() as cur:
                rows = cur.execute(
                    "SELECT id FROM villages WHERE is_personal = 0 "
                    "AND state IN ('registered','active','created') "
                    "ORDER BY COALESCE(last_seen_at,'') ASC"
                ).fetchall()
            all_ids = [r["id"] for r in rows]
            if not all_ids:
                log.info("[pool] no villages — sleeping 30s")
                try:
                    await asyncio.wait_for(self.cancel_event.wait(), timeout=30)
                except asyncio.TimeoutError:
                    continue
                break

            batch = all_ids[:max_par]
            await self._login_batch(batch)
            with db_cur() as cur:
                cur.executemany(
                    "UPDATE villages SET last_seen_at = ? WHERE id = ?",
                    [(_now_iso(), vid) for vid in batch],
                )

            try:
                await asyncio.wait_for(self.cancel_event.wait(),
                                       timeout=rot_min * 60)
                break
            except asyncio.TimeoutError:
                pass

            await self._logout_batch(batch)
            cycle += 1
            log.info(f"[pool] cycle {cycle} — cooling down {cool_min}m")
            try:
                await asyncio.wait_for(self.cancel_event.wait(),
                                       timeout=cool_min * 60)
                break
            except asyncio.TimeoutError:
                continue
        self._write_config(running=0, current_batch="[]")
        log.info("[pool] orchestrator stopped")

    async def start(self) -> None:
        if self.task and not self.task.done():
            return
        self.cancel_event.clear()
        self._write_config(running=1)
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.cancel_event.set()
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=3)
            except asyncio.TimeoutError:
                pass
        self._write_config(running=0)


POOL = BrowserPool()


@app.post("/api/pool/start")
async def api_pool_start():
    await POOL.start()
    return {"ok": True, "running": True}


@app.post("/api/pool/stop")
async def api_pool_stop():
    await POOL.stop()
    return {"ok": True, "running": False}


@app.get("/api/pool/status")
async def api_pool_status():
    cfg = POOL._read_config()
    return {"ok": True, "config": cfg}


@app.post("/api/pool/config")
async def api_pool_config(request: Request):
    body = await request.json()
    upd = {}
    if "max_parallel" in body:
        upd["max_parallel"] = max(1, min(50, int(body["max_parallel"])))
    if "rotation_min" in body:
        upd["rotation_min"] = max(2, min(180, int(body["rotation_min"])))
    if "cooldown_min" in body:
        upd["cooldown_min"] = max(0, min(60, int(body["cooldown_min"])))
    if upd:
        POOL._write_config(**upd)
    return {"ok": True, "config": upd}


# ─── Strategy YAML engine ───────────────────────────────────────────────────
DEFAULT_STRATEGY = {
    "name": "default",
    "description": "ابني الإنتاج + المخابئ + قمح أولاً، ثم خلّص المهمات وخذ المكافآت",
    # Smart storage rule: cranny must always cover stockpile (loot protection)
    "storage_rules": {
        "cranny_min_capacity":    20000,   # min loot-protection per village
        "cranny_target_capacity": 50000,
        "warehouse_target_level": 10,      # caps at level 20 (80k/120k)
        "granary_target_level":   10,
        "cranny_ratio":           1.2,     # cranny capacity ≥ 1.2 × warehouse
    },
    "raid_rules": {
        "enabled":            True,
        "scan_radius":        30,            # fields N/S/E/W from village
        "max_target_pop":     100,           # only farm small villages
        "first_strike_units": 2,             # send 2 troops to probe
        "spy_first":          True,          # send a scout first
        "skip_spy_if_ally_attacking": True,  # piggy-back on ally attacks
        "split_troops":       True,          # divide forces among multiple targets
    },
    "attack_units": {
        "ROMANS":    ["Equites Imperatoris", "Imperian"],
        "GAULS":     ["Theutates Thunder", "Swordsman"],
        "TEUTONS":   ["Paladin", "Clubswinger"],
        "EGYPTIANS": ["Sopdu Explorer", "Ash Warden"],
        "HUNS":      ["Steppe Rider", "Bowman"],
    },
    "defense_units": {
        "ROMANS":    ["Praetorian", "Legionnaire"],
        "GAULS":     ["Phalanx", "Druidrider"],
        "TEUTONS":   ["Spearman", "Paladin"],
        "EGYPTIANS": ["Ash Warden", "Khopesh Warrior"],
        "HUNS":      ["Spotter", "Bowman"],
    },
    "phases": [
        {"name": "phase-1-resources", "until_day": 3, "actions": [
            {"build": "Woodcutter", "to_level": 5},
            {"build": "Claypit",    "to_level": 5},
            {"build": "Ironmine",   "to_level": 4},
            {"build": "Cropland",   "to_level": 5},
            {"quest": "complete_all_tutorial"},
        ]},
        {"name": "phase-2-storage", "until_day": 5, "actions": [
            {"build": "Cranny",     "to_level": 10},   # FIRST (loot protection)
            {"build": "Warehouse",  "to_level": 5},
            {"build": "Granary",    "to_level": 5},
            {"quest": "collect_all_rewards"},
        ]},
        {"name": "phase-3-army", "until_day": 10, "actions": [
            {"build": "Barracks",   "to_level": 3},
            {"build": "Wall",       "to_level": 5},
            {"build": "Embassy",    "to_level": 1},
            {"train": "defense_units", "count_per_day": 20},
        ]},
        {"name": "phase-4-economy", "until_day": 20, "actions": [
            {"build": "Marketplace","to_level": 5},
            {"build": "MainBuilding","to_level": 10},
            {"raid": {"enabled": True, "frequency_hours": 2}},
            {"transfer_to_personal": {"enabled": True, "min_resource": 5000}},
        ]},
    ],
}


def load_strategy(name: str = "default") -> dict[str, Any]:
    path = ROOT / "strategies" / f"{name}.yaml"
    if path.exists():
        try:
            import yaml
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"failed to load {path}: {e}")
    return DEFAULT_STRATEGY


def save_strategy(name: str, data: dict[str, Any]) -> Path:
    path = ROOT / "strategies" / f"{name}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
    except ImportError:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    return path


@app.get("/api/strategies")
def api_list_strategies():
    sdir = ROOT / "strategies"
    sdir.mkdir(parents=True, exist_ok=True)
    files = [p.stem for p in sdir.glob("*.yaml")]
    if "default" not in files:
        files.insert(0, "default")
    return {"ok": True, "strategies": files}


@app.get("/api/strategy/{name}")
def api_get_strategy(name: str):
    return {"ok": True, "name": name, "data": load_strategy(name)}


@app.post("/api/strategy/{name}")
async def api_save_strategy(name: str, request: Request):
    body = await request.json()
    save_strategy(name, body)
    return {"ok": True}


# ─── Alliance + Defense stubs ───────────────────────────────────────────────
@app.post("/api/alliance/create")
async def api_alliance_create(request: Request):
    """Create an alliance via personal village's embassy, invite all bot villages."""
    body = await request.json()
    tag = (body.get("tag") or "ZNX").upper()[:8]
    name = body.get("name") or "Zenrex Alliance"
    server = body.get("server", "")
    with db_cur() as cur:
        personal = cur.execute(
            "SELECT * FROM villages WHERE is_personal = 1 AND server = ? LIMIT 1",
            (server,)).fetchone()
        members = cur.execute(
            "SELECT id, name, tribe, coords_x, coords_y FROM villages "
            "WHERE is_personal = 0 AND server = ?", (server,)).fetchall()
    if not personal:
        return {"ok": False,
                "error": "no personal village on this server — mark one with PATCH is_personal=true"}
    return {
        "ok": True, "feasible": True, "executable": False,
        "tag": tag, "name": name, "server": server,
        "personal_village": dict(personal),
        "members_count": len(members),
        "plan": [
            f"1. Personal village '{personal['name']}' builds Embassy lvl1",
            f"2. Personal creates alliance [{tag}] '{name}'",
            f"3. Personal sends invitations to {len(members)} bot villages",
            "4. Each bot village builds Embassy lvl1 then auto-accepts",
            "5. (Optional) Split into 2 alliances + confederation pact",
        ],
        "executable_reason": "needs Playwright in-game automation (Phase 2)",
    }


@app.post("/api/defense/send")
async def api_defense_send(request: Request):
    """Send defensive troops from all bot villages to a target (usually personal).

    Body: {
      server: str,
      target_x: int, target_y: int,
      mode: "all" | "spec",                # all = send everything, spec = use troop_spec
      troop_spec: {ROMANS: {Praetorian: 50, Legionnaire: 20}, GAULS: {...}, ...}
    }
    """
    body = await request.json()
    server = body.get("server", "")
    target_x = int(body.get("target_x", 0))
    target_y = int(body.get("target_y", 0))
    mode = body.get("mode", "all")
    troop_spec = body.get("troop_spec", {})
    with db_cur() as cur:
        sources = cur.execute(
            "SELECT id, name, tribe, coords_x, coords_y FROM villages "
            "WHERE server = ? AND is_personal = 0 "
            "AND state IN ('registered','active')", (server,)).fetchall()
    dispatch = []
    for s in sources:
        s = dict(s)
        tribe = s.get("tribe", "ROMANS")
        if mode == "all":
            s["plan"] = "send_all_defense_units"
        else:
            s["plan"] = troop_spec.get(tribe, {})
        dispatch.append(s)
    return {
        "ok": True, "feasible": bool(sources), "executable": False,
        "target": {"x": target_x, "y": target_y},
        "mode": mode,
        "sources_count": len(sources),
        "dispatch": dispatch[:20],
        "executable_reason": "needs registered villages + Playwright (Phase 2)",
    }


@app.post("/api/attack/scan")
async def api_attack_scan(request: Request):
    """Scan the map around a village for small target villages to raid.

    Body: {village_id, radius=30, max_pop=100}
    Returns candidate targets (Phase 2 will scrape /karte.php from in-game).
    """
    body = await request.json()
    vid = body.get("village_id", "")
    radius = int(body.get("radius", 30))
    max_pop = int(body.get("max_pop", 100))
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    cx, cy = v.get("coords_x") or 0, v.get("coords_y") or 0
    return {
        "ok": True, "executable": False,
        "village": {"id": vid, "name": v["name"], "coords": (cx, cy)},
        "scan_area": {
            "x_range": [cx - radius, cx + radius],
            "y_range": [cy - radius, cy + radius],
            "fields_count": (2 * radius + 1) ** 2,
        },
        "filters": {"max_pop": max_pop},
        "executable_reason": "needs Playwright + Travian map API scraping",
    }


@app.post("/api/attack/raid")
async def api_attack_raid(request: Request):
    """Plan a raid: scout first (unless ally is attacking), then dispatch troops
    based on the spy report. Phase-2 stub."""
    body = await request.json()
    return {
        "ok": True, "executable": False,
        "village_id": body.get("village_id"),
        "target": {"x": body.get("target_x"), "y": body.get("target_y")},
        "plan": [
            "1. send_spy(level_3_scout) → wait 30s for report",
            "2. parse_report() → get enemy_troops + resources",
            "3. if ally_pre_attacking(target) → skip spy, attack directly",
            "4. calculate_troops_needed(enemy_defense, target_loot)",
            "5. send_raid(units=calculated)",
            "6. log_loot_to_db()",
        ],
        "executable_reason": "needs registered village + Playwright (Phase 2)",
    }


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


@app.post("/api/proxies/refresh-free")
async def api_refresh_free_proxies(request: Request):
    """Pull fresh free proxies from public sources, test them, save the live ones."""
    body = await request.json() if request.headers.get("content-length") else {}
    max_total = int(body.get("max_total", 300))
    alive = await fetch_free_proxies(max_total=max_total)
    if alive:
        # Append to existing (don't wipe user-provided proxies)
        existing = set(load_proxies())
        merged = sorted(existing.union(alive))
        PROXIES_FILE.write_text("\n".join(merged) + "\n", encoding="utf-8")
    return {"ok": True, "found_alive": len(alive),
            "total_now": len(load_proxies())}


@app.post("/api/villages/{vid}/open-browser")
async def api_open_browser(vid: str):
    """Open the Playwright browser for this village (visible window).
    The browser stays open until the user closes it manually.
    """
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    try:
        ctx, page = await FARM.open(v)
        # Navigate to server homepage (login form)
        url = (f"https://{v['server']}" if not v['server'].startswith("http")
               else v['server'])
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            pass
        log_event(vid, "open_browser",
                  f"navigated to {url} | proxy={v['proxy'] or 'direct'}")
        update_village_state(vid, "browser_open")
        return {"ok": True, "village": vid, "url": url,
                "proxy": v["proxy"] or None, "tribe": v.get("tribe")}
    except Exception as e:
        log_event(vid, "error", f"open_browser: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/villages/{vid}/register-travian")
async def api_register_travian(vid: str, request: Request):
    """Auto-register this village in Travian. Phase 2 — uses Playwright to fill
    the signup form + verify email via mail.tm.

    Body: {dry_run: bool}  — when True, only validates pre-conditions.
    """
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    body = await request.json() if request.headers.get("content-length") else {}
    dry_run = bool(body.get("dry_run", True))

    # Pre-flight checks
    issues = []
    if not v.get("email"):
        issues.append("no email attached — call attach-email first")
    if "@example.local" in (v.get("email") or ""):
        issues.append("placeholder email — needs real mailbox")
    if not v.get("tribe"):
        issues.append("tribe not set")
    if v.get("state") != "created":
        issues.append(f"state must be 'created' (is '{v.get('state')}')")

    if dry_run or issues:
        return {
            "ok": not issues, "dry_run": True, "village": vid,
            "village_name": v["name"], "tribe": v.get("tribe"),
            "email": v.get("email"), "region": v.get("region"),
            "coords": (v.get("coords_x"), v.get("coords_y")),
            "issues": issues,
            "ready": not issues,
        }

    # Real execution (Phase 2 — requires testing on ONE village first)
    try:
        ctx, page = await FARM.open(v)
        url = f"https://{v['server']}/register.php"
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(human_pause())

        # Fill form (selectors may need adjusting per Travian version)
        await human_type(page, "input[name='name']", v["name"])
        await human_type(page, "input[name='email']", v["email"])
        await human_type(page, "input[name='password']", v["password"])
        await human_type(page, "input[name='password2']", v["password"])

        # Pick tribe (1=Romans, 2=Teutons, 3=Gauls, 6=Egyptians, 7=Huns)
        tribe_map = {"ROMANS": 1, "TEUTONS": 2, "GAULS": 3,
                     "EGYPTIANS": 6, "HUNS": 7}
        tribe_id = tribe_map.get(v.get("tribe", "ROMANS"), 1)
        await page.click(f"input[name='tribe'][value='{tribe_id}']")
        await asyncio.sleep(human_pause())

        # Pick region (NW=1, NE=2, SW=3, SE=4 — approximate, may vary)
        region_map = {"NW": 1, "NE": 2, "SW": 3, "SE": 4, "ANY": 5}
        region_id = region_map.get(v.get("region", "ANY"), 5)
        try:
            await page.click(f"input[name='start'][value='{region_id}']")
        except Exception:
            pass

        # Accept TOS
        for tos_sel in ["input[name='agb']", "input[name='tos']",
                        "input#agb", "input[type='checkbox']"]:
            try:
                await page.check(tos_sel)
                break
            except Exception:
                continue

        # Submit
        await asyncio.sleep(human_pause())
        for submit_sel in ["button[type='submit']", "input[type='submit']",
                           "button#registerSubmit", "button.green"]:
            try:
                await page.click(submit_sel)
                break
            except Exception:
                continue

        await asyncio.sleep(5)
        log_event(vid, "register_submitted",
                  f"form submitted at {url} — waiting for activation email")
        update_village_state(vid, "registration_pending")

        return {
            "ok": True, "dry_run": False, "village": vid,
            "status": "form_submitted",
            "next_step": "poll mail.tm inbox for activation link",
        }
    except Exception as e:
        log_event(vid, "register_failed", str(e))
        return JSONResponse({"ok": False, "error": str(e),
                             "village": vid}, status_code=500)


@app.post("/api/villages/{vid}/attach-email")
async def api_attach_email(vid: str, request: Request):
    """Create a fresh temporary mailbox (any provider) and attach it to a village."""
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    try:
        body = await request.json() if request.headers.get("content-length") else {}
    except Exception:
        body = {}
    prefer = body.get("provider")
    try:
        acct = await create_email_for(vid, prefer=prefer)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    with db_cur() as cur:
        cur.execute("UPDATE villages SET email = ?, notes = ? WHERE id = ?",
                    (acct["email"],
                     (v.get("notes") or "") +
                     f"\nemail_provider={acct['provider']}\nemail_token={acct['token']}\n"
                     f"email_id={acct['account_id']}",
                     vid))
    log_event(vid, "email_attached", f"{acct['provider']}: {acct['email']}")
    return {"ok": True, "email": acct["email"], "provider": acct["provider"]}


@app.post("/api/villages/{vid}/inbox")
async def api_inbox(vid: str):
    """Read the village's mail.tm inbox."""
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    notes = v.get("notes") or ""
    token = ""
    for line in notes.splitlines():
        if line.startswith("mailtm_token="):
            token = line.split("=", 1)[1].strip()
            break
    if not token:
        return JSONResponse({"ok": False,
                             "error": "no mailtm token; call /attach-email first"},
                            status_code=400)
    msgs = await mailtm_read_inbox(token)
    return {"ok": True, "count": len(msgs), "messages": msgs[:20]}


@app.get("/api/servers")
def api_servers():
    """List all unique servers with village counts."""
    with db_cur() as cur:
        rows = cur.execute(
            "SELECT server, COUNT(*) as n FROM villages GROUP BY server "
            "ORDER BY n DESC"
        ).fetchall()
    return {"ok": True, "servers": [dict(r) for r in rows]}


@app.post("/api/transfer/plan")
async def api_transfer_plan(request: Request):
    """Plan a resource transfer to a target coords from all our villages on a server.

    Body: {server, target_x, target_y, target_village_name,
           amount_wood, amount_clay, amount_iron, amount_crop}
    Returns a plan: which villages contribute what, how many merchants needed.

    NOTE: This only PLANS — actual execution requires registered villages
    with active Travian sessions (next phase).
    """
    body = await request.json()
    server = body.get("server", "")
    target_x = int(body.get("target_x", 0))
    target_y = int(body.get("target_y", 0))
    target_name = body.get("target_village_name", "Unknown")
    requested = {
        "wood":  int(body.get("amount_wood", 0)),
        "clay":  int(body.get("amount_clay", 0)),
        "iron":  int(body.get("amount_iron", 0)),
        "crop":  int(body.get("amount_crop", 0)),
    }
    total_requested = sum(requested.values())
    if total_requested <= 0:
        return JSONResponse({"ok": False, "error": "no resources requested"},
                            status_code=400)

    with db_cur() as cur:
        sources = cur.execute(
            "SELECT * FROM villages WHERE server = ? AND state IN ('registered','active') "
            "ORDER BY id",
            (server,)
        ).fetchall()

    if not sources:
        return {"ok": True, "plan": [], "feasible": False,
                "reason": "no registered villages on this server (need to register first)"}

    # Round-robin even split across sources (real implementation will query
    # each village's actual stockpile + merchants).
    n = len(sources)
    per = {k: total_requested // n for k in requested}
    plan = []
    for s in sources:
        plan.append({
            "village_id": s["id"],
            "village_name": s["name"],
            "wood":  per["wood"]  if requested["wood"]  else 0,
            "clay":  per["clay"]  if requested["clay"]  else 0,
            "iron":  per["iron"]  if requested["iron"]  else 0,
            "crop":  per["crop"]  if requested["crop"]  else 0,
            "merchants_estimated": max(1, total_requested // (n * 1000)),
        })
    return {
        "ok": True, "feasible": True, "plan": plan,
        "target": {"x": target_x, "y": target_y, "name": target_name},
        "server": server,
        "total_requested": total_requested,
        "sources_count": n,
        "executable": False,
        "executable_reason": (
            "Resource transfer execution requires villages registered in Travian "
            "with active sessions. Currently villages exist only as local "
            "identities. Run /api/villages/{id}/register first (next phase)."
        ),
    }


@app.get("/api/fingerprint-test/{vid}")
def api_fingerprint(vid: str):
    """Return the fingerprint seed for a village (for debugging)."""
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    return {"ok": True, "village_id": vid,
            "fingerprint": fingerprint_seed(vid),
            "user_agent": v["user_agent"],
            "screen": [v["screen_w"], v["screen_h"]],
            "locale": v["locale"],
            "timezone": v["timezone"],
            "proxy": v["proxy"] or "🏠 direct"}


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
      <div class="flex" style="justify-content:space-between;margin-bottom:8px;flex-wrap:wrap;gap:8px">
        <div class="flex" style="gap:8px">
          <label style="margin:0;color:var(--text)">السيرفر:</label>
          <select id="server-filter" onchange="loadVillages()" style="margin:0;width:auto">
            <option value="">📡 الكل</option>
          </select>
        </div>
        <div class="flex" style="gap:8px">
          <button class="secondary" onclick="loadVillages()">↻ تحديث</button>
          <button onclick="openTransferDialog()">💱 نقل موارد</button>
        </div>
      </div>
      <span class="small">آخر تحديث: <span id="last-refresh">—</span></span>
      <table id="villages-table">
        <thead><tr>
          <th>الاسم</th><th>الجنسية</th><th>القبيلة</th><th>المنطقة</th>
          <th>السيرفر</th><th>الحالة</th><th>IP</th><th>الإيميل</th><th>إجراء</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>

    <!-- Resource Transfer Modal -->
    <div id="transfer-modal" style="display:none;position:fixed;inset:0;
         background:rgba(0,0,0,0.8);z-index:100;align-items:center;
         justify-content:center;padding:20px">
      <div class="card" style="max-width:520px;width:100%;max-height:90vh;overflow:auto">
        <h2>💱 نقل موارد للوجهة</h2>
        <label>السيرفر</label>
        <select id="t-server"></select>
        <div class="row">
          <div><label>X</label><input id="t-x" type="number" value="0"/></div>
          <div><label>Y</label><input id="t-y" type="number" value="0"/></div>
        </div>
        <label>اسم القرية الهدف</label>
        <input id="t-name" placeholder="مثلاً: قرية الهدف"/>
        <div class="row">
          <div><label>🪵 خشب</label><input id="t-wood" type="number" value="0"/></div>
          <div><label>🧱 طين</label><input id="t-clay" type="number" value="0"/></div>
          <div><label>⚒️ حديد</label><input id="t-iron" type="number" value="0"/></div>
          <div><label>🌾 قمح</label><input id="t-crop" type="number" value="0"/></div>
        </div>
        <div class="row">
          <button onclick="planTransfer()">🧮 احسب الخطة</button>
          <button class="secondary" onclick="closeTransferDialog()">إلغاء</button>
        </div>
        <div id="transfer-result" class="small" style="margin-top:12px"></div>
      </div>
    </div>
  </div>

  <!-- RIGHT: create villages + proxies + preview -->
  <div>
    <div class="card">
      <h2>إنشاء قرى جديدة</h2>
      <label>عدد القرى</label>
      <input id="count" type="number" min="1" max="500" value="5"/>

      <label>الجنسية / الأسماء</label>
      <select id="name-preset">
        <option value="mixed">🌍 خلطة كاملة (كل الجنسيات)</option>
        <option value="arabic">🕌 عربي فقط (SA/EG/AE/KW)</option>
        <option value="english">🇬🇧 إنجليزي فقط (US/GB)</option>
        <option value="european">🇪🇺 أوروبي (DE/FR/GB/RU/TR)</option>
        <option value="SA">🇸🇦 سعودي فقط</option>
        <option value="EG">🇪🇬 مصري فقط</option>
        <option value="DE">🇩🇪 ألماني فقط</option>
        <option value="US">🇺🇸 أمريكي فقط</option>
        <option value="JP">🇯🇵 ياباني فقط</option>
      </select>

      <div class="row">
        <div>
          <label>المنطقة (Map Region)</label>
          <select id="region">
            <option value="ANY">🌐 أي منطقة</option>
            <option value="NW">↖ شمال غربي</option>
            <option value="NE">↗ شمال شرقي</option>
            <option value="SW">↙ جنوب غربي</option>
            <option value="SE">↘ جنوب شرقي</option>
          </select>
        </div>
        <div>
          <label>القبيلة (Tribe)</label>
          <select id="tribe">
            <option value="MIXED">🎲 خلطة</option>
            <option value="ROMANS">⚔️ Romans</option>
            <option value="GAULS">🛡️ Gauls</option>
            <option value="TEUTONS">🪓 Teutons</option>
            <option value="EGYPTIANS">🐪 Egyptians</option>
            <option value="HUNS">🏹 Huns</option>
          </select>
        </div>
      </div>

      <label>الخادم (Travian server)</label>
      <input id="server" value="ts8.x2.international.travian.com" list="server-list"/>
      <datalist id="server-list">
        <option value="ts8.x2.international.travian.com"></option>
        <option value="ts7.travian.com"></option>
        <option value="ts4.travian.sa"></option>
        <option value="ts5.travian.com"></option>
      </datalist>

      <label>الخطة</label>
      <select id="strategy">
        <option value="default">افتراضية (مزارع → بناء → جيش)</option>
        <option value="defensive">دفاعية (سور + cranny)</option>
        <option value="custom">مخصصة (يدوي)</option>
      </select>

      <div class="row" style="margin-top:6px">
        <label class="flex" style="margin-top:0">
          <input type="checkbox" id="use-proxies" checked style="width:auto;margin-left:6px"/>
          استخدم البروكسيات
        </label>
        <label class="flex" style="margin-top:0">
          <input type="checkbox" id="auto-email" checked style="width:auto;margin-left:6px"/>
          إيميل تلقائي (مزوّدات متعددة)
        </label>
      </div>

      <button onclick="createVillages()">🏗️ أنشئ القرى</button>
    </div>

    <div class="card" style="margin-top:18px">
      <h2>🔄 Browser Pool (تشغيل القرى بالتناوب)</h2>
      <p class="small">يدير N قرى متوازية، يستبدلهم كل X دقيقة. القرى الشخصية مستثناة.</p>
      <div id="pool-status" class="small" style="margin:8px 0;padding:8px 10px;background:#0a0a14;border-radius:8px"></div>
      <div class="row">
        <div><label>عدد متوازي</label><input id="pool-max" type="number" value="10" min="1" max="50"/></div>
        <div><label>تناوب (د)</label><input id="pool-rot" type="number" value="15" min="2" max="180"/></div>
        <div><label>تبريد (د)</label><input id="pool-cool" type="number" value="5" min="0" max="60"/></div>
      </div>
      <div class="row">
        <button onclick="startPool()">▶ تشغيل</button>
        <button class="danger" onclick="stopPool()">■ إيقاف</button>
        <button class="secondary" onclick="savePoolConfig()">💾 احفظ</button>
      </div>
      <p class="small" style="margin-top:8px;color:#f59e0b">
        ⚠ Phase 1: التناوب يعمل كـ log فقط. تنفيذ Playwright يحتاج تسجيل القرى أولاً.
      </p>
    </div>

    <div class="card" style="margin-top:18px">
      <h2>🤝 التحالف والدفاع</h2>
      <div class="row">
        <button onclick="createAlliance()">🤝 أنشئ تحالف</button>
        <button class="secondary" onclick="openTransferDialog()">💱 نقل موارد</button>
      </div>
      <p class="small" style="margin-top:8px;color:var(--muted)">
        ضع 👤 على قرية لجعلها <b>شخصية</b> — تُستثنى من التناوب وتُستخدم
        كمستودع موارد + قاعدة التحالف.
      </p>
    </div>

    <div class="card" style="margin-top:18px">
      <h2>قائمة البروكسيات</h2>
      <p class="small">ضع كل بروكسي في سطر منفصل. الأشكال المقبولة:<br/>
      <code>http://host:port</code>, <code>http://user:pass@host:port</code>, <code>socks5://host:port</code></p>
      <textarea id="proxies-text" rows="6" placeholder="# مثال:
http://1.2.3.4:8080
socks5://user:pass@5.6.7.8:1080"></textarea>
      <div class="row">
        <button onclick="saveProxies()">💾 حفظ</button>
        <button class="secondary" onclick="refreshFreeProxies()">🌐 اسحب 300 بروكسي مجاني</button>
      </div>
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
  const r = await fetch('/api/servers'); const d = await r.json();
  const sel = $('#server-filter');
  sel.innerHTML = '<option value="">📡 الكل</option>';
  (d.servers || []).forEach(s => {
    const o = document.createElement('option');
    o.value = s.server;
    o.textContent = `${s.server} (${s.n})`;
    sel.appendChild(o);
  });
  // Mirror server list to transfer modal
  const tsel = $('#t-server');
  if (tsel) {
    tsel.innerHTML = '';
    (d.servers || []).forEach(s => {
      const o = document.createElement('option');
      o.value = s.server;
      o.textContent = `${s.server} (${s.n} قرية)`;
      tsel.appendChild(o);
    });
  }
}

async function loadVillages(){
  const f = $('#server-filter').value;
  const url = f ? `/api/villages?server=${encodeURIComponent(f)}` : '/api/villages';
  const r = await fetch(url); const d = await r.json();
  $('#s-total').textContent = d.total;
  const counts = { active:0, registered:0, banned:0 };
  d.villages.forEach(v => { counts[v.state] = (counts[v.state]||0)+1; });
  $('#s-active').textContent      = counts.active || 0;
  $('#s-registered').textContent  = counts.registered || 0;
  $('#s-banned').textContent      = counts.banned || 0;
  const tbody = $('#villages-table tbody');
  tbody.innerHTML = d.villages.map(v => `
    <tr style="${v.is_personal ? 'background:#0f3a16' : ''}">
      <td>${v.is_personal ? '👤 ' : ''}${v.name}</td>
      <td><span class="badge">${v.nationality}</span></td>
      <td><span class="small">${v.tribe || '-'}</span></td>
      <td><span class="badge">${v.region || 'ANY'}${v.coords_x!==null && v.coords_x!==undefined ? ` (${v.coords_x},${v.coords_y})` : ''}</span></td>
      <td><span class="small">${(v.server||'').replace('.travian.com','').replace('.x2.international','')}</span></td>
      <td><span class="pill ${v.state}">${v.state}</span></td>
      <td><span class="small">${v.proxy ? v.proxy.substring(0,22) : '🏠 مباشر'}</span></td>
      <td><span class="small">${v.email || '—'}</span></td>
      <td>
        <button class="secondary" onclick="openBrowser('${v.id}')">🦊</button>
        <button class="secondary" onclick="attachEmail('${v.id}')">📧</button>
        <button class="secondary" onclick="togglePersonal('${v.id}', ${!v.is_personal})">${v.is_personal ? '⊖' : '👤'}</button>
        <button class="danger" onclick="delVillage('${v.id}')">🗑</button>
      </td>
    </tr>
  `).join('');
  $('#last-refresh').textContent = new Date().toLocaleTimeString();
}

async function createVillages(){
  const body = {
    count: parseInt($('#count').value || '1'),
    name_preset: $('#name-preset').value,
    server: $('#server').value,
    strategy: $('#strategy').value,
    use_proxies: $('#use-proxies').checked,
    auto_email: $('#auto-email').checked,
    region: $('#region') ? $('#region').value : 'ANY',
    tribe:  $('#tribe')  ? $('#tribe').value  : 'MIXED',
  };
  const btn = event.target;
  btn.disabled = true; btn.textContent = '⏳ يُنشئ...';
  try {
    const r = await fetch('/api/villages', { method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    const d = await r.json();
    if (d.ok) {
      alert(`✓ أُنشئت ${d.created} قرية`);
      loadNationalities();
      loadVillages();
    } else alert('✗ ' + (d.error || 'unknown'));
  } finally {
    btn.disabled = false; btn.textContent = '🏗️ أنشئ القرى';
  }
}

function openTransferDialog(){
  $('#transfer-modal').style.display = 'flex';
}
function closeTransferDialog(){
  $('#transfer-modal').style.display = 'none';
}

async function togglePersonal(id, makePersonal){
  const r = await fetch(`/api/villages/${id}`, { method:'PATCH',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({is_personal: makePersonal})});
  await r.json();
  loadVillages();
}

async function startPool(){
  const r = await fetch('/api/pool/start', { method:'POST' });
  const d = await r.json();
  alert(d.ok ? '✓ Pool started' : '✗ failed');
  refreshPool();
}
async function stopPool(){
  const r = await fetch('/api/pool/stop', { method:'POST' });
  await r.json();
  refreshPool();
}
async function refreshPool(){
  try {
    const r = await fetch('/api/pool/status'); const d = await r.json();
    const c = d.config || {};
    const el = $('#pool-status');
    if (el) {
      el.innerHTML = c.running
        ? `<span style="color:#10b981">● شغّال</span> | ${c.max_parallel} متوازي | rotation ${c.rotation_min}m | cooldown ${c.cooldown_min}m`
        : `<span style="color:#9ca3af">● متوقف</span> | ${c.max_parallel||10} متوازي`;
    }
  } catch(e) {}
}
async function savePoolConfig(){
  const body = {
    max_parallel: parseInt($('#pool-max').value || '10'),
    rotation_min: parseInt($('#pool-rot').value || '15'),
    cooldown_min: parseInt($('#pool-cool').value || '5'),
  };
  await fetch('/api/pool/config', { method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
  refreshPool();
}

async function createAlliance(){
  const tag = prompt('Alliance tag (e.g. ZNX):', 'ZNX');
  if (!tag) return;
  const name = prompt('Alliance name:', 'Zenrex Alliance') || 'Zenrex Alliance';
  const server = $('#server-filter').value || $('#server').value;
  const r = await fetch('/api/alliance/create', { method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({tag, name, server})});
  const d = await r.json();
  if (!d.ok) { alert('✗ ' + d.error); return; }
  let txt = `Alliance Plan [${d.tag}] '${d.name}'\nServer: ${d.server}\n\n`;
  d.plan.forEach(p => txt += p + '\n');
  if (!d.executable) txt += '\n⚠ ' + d.executable_reason;
  alert(txt);
}

async function planTransfer(){
  const body = {
    server: $('#t-server').value,
    target_x: parseInt($('#t-x').value || '0'),
    target_y: parseInt($('#t-y').value || '0'),
    target_village_name: $('#t-name').value || 'الهدف',
    amount_wood: parseInt($('#t-wood').value || '0'),
    amount_clay: parseInt($('#t-clay').value || '0'),
    amount_iron: parseInt($('#t-iron').value || '0'),
    amount_crop: parseInt($('#t-crop').value || '0'),
  };
  const r = await fetch('/api/transfer/plan', { method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
  const d = await r.json();
  const out = $('#transfer-result');
  if (!d.ok) { out.innerHTML = '<span style="color:#ef4444">✗ ' + d.error + '</span>'; return; }
  if (!d.feasible) {
    out.innerHTML = '<span style="color:#f59e0b">⚠ ' + d.reason + '</span>';
    return;
  }
  let html = `<b>الخطة (${d.sources_count} قرية مصدر):</b><br/>`;
  d.plan.forEach(p => {
    html += `• ${p.village_name}: ${p.wood}🪵 ${p.clay}🧱 ${p.iron}⚒️ ${p.crop}🌾 (${p.merchants_estimated} تاجر)<br/>`;
  });
  if (!d.executable) html += '<br/><span style="color:#f59e0b">⚠ ' + d.executable_reason + '</span>';
  out.innerHTML = html;
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

async function attachEmail(id){
  if (!confirm('أنشئ صندوق بريد مؤقت (mail.tm) لهذه القرية؟')) return;
  const r = await fetch(`/api/villages/${id}/attach-email`, { method:'POST' });
  const d = await r.json();
  if (d.ok) {
    alert('✓ تم إنشاء الإيميل:\n' + d.email);
    loadVillages();
  } else alert('✗ ' + (d.error || 'failed'));
}

async function refreshFreeProxies(){
  if (!confirm('سيتم سحب 300 بروكسي مجاني واختبارها (قد تستغرق 60 ثانية). تابع؟')) return;
  const btn = event.target;
  btn.disabled = true; btn.textContent = '⏳ يبحث...';
  try {
    const r = await fetch('/api/proxies/refresh-free', { method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({max_total:300}) });
    const d = await r.json();
    alert(`✓ وُجد ${d.found_alive} بروكسي حي\nالمجموع الآن: ${d.total_now}`);
    loadProxies();
  } finally {
    btn.disabled = false; btn.textContent = '🌐 اسحب 300 بروكسي مجاني';
  }
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
refreshPool();
setInterval(loadVillages, 8000);
setInterval(refreshPool, 6000);
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
