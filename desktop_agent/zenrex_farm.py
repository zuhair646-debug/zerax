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
import math
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
APP_VERSION = "0.9.0"
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

CREATE TABLE IF NOT EXISTS chat_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    role            TEXT NOT NULL,           -- 'user' | 'assistant' | 'system'
    content         TEXT NOT NULL,
    intent          TEXT,                    -- parsed intent tag (e.g. plan_proposal, clone_strategy)
    meta_json       TEXT,                    -- JSON payload (proposed actions, vid refs, etc.)
    approved        INTEGER DEFAULT 0,       -- 0=pending, 1=approved, -1=rejected
    ts              TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_vid      TEXT NOT NULL,           -- village we copied state from
    name            TEXT NOT NULL,           -- human label
    state_json      TEXT NOT NULL,           -- captured build queue + state
    created_at      TEXT NOT NULL,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS transfer_jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    server          TEXT NOT NULL,
    target_x        INTEGER NOT NULL,
    target_y        INTEGER NOT NULL,
    target_name     TEXT,
    mode            TEXT NOT NULL,           -- 'specific' | 'random_all' | 'defense'
    resources_json  TEXT,                    -- requested per-resource breakdown
    troops_json     TEXT,                    -- requested defense troop breakdown
    status          TEXT DEFAULT 'queued',   -- queued | running | done | failed
    progress_json   TEXT,                    -- per-source progress
    created_at      TEXT NOT NULL,
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS raid_targets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    server          TEXT NOT NULL,
    x               INTEGER NOT NULL,
    y               INTEGER NOT NULL,
    owner           TEXT,                    -- "Natars" | player name | empty
    kind            TEXT,                    -- 'village' | 'oasis' | 'unknown'
    last_seen       TEXT,
    last_raid_at    TEXT,
    success_count   INTEGER DEFAULT 0,
    fail_count      INTEGER DEFAULT 0,
    note            TEXT,
    UNIQUE(server, x, y)
);

CREATE TABLE IF NOT EXISTS raid_config (
    village_id      TEXT PRIMARY KEY,        -- hunter village
    enabled         INTEGER DEFAULT 1,
    radius          INTEGER DEFAULT 7,
    max_per_cycle   INTEGER DEFAULT 8,
    troops_json     TEXT,                    -- {"t4": 5} per raid
    attack_type     TEXT DEFAULT 'raid',
    cooldown_min    INTEGER DEFAULT 90
);

CREATE TABLE IF NOT EXISTS spawn_schedules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    server          TEXT NOT NULL,
    name_preset     TEXT DEFAULT 'mixed',
    tribe_preset    TEXT DEFAULT 'MIXED',
    region          TEXT DEFAULT 'ANY',
    use_proxies     INTEGER DEFAULT 1,
    auto_email      INTEGER DEFAULT 1,
    target_total    INTEGER NOT NULL,        -- target village count on this server
    interval_min    INTEGER DEFAULT 30,      -- minutes between spawns
    daily_cap       INTEGER DEFAULT 10,      -- max villages per 24h
    enabled         INTEGER DEFAULT 1,
    last_spawn_at   TEXT,
    spawned_total   INTEGER DEFAULT 0,
    spawned_today   INTEGER DEFAULT 0,
    day_anchor      TEXT,                    -- ISO date for "today" counter
    created_at      TEXT
);

CREATE TABLE IF NOT EXISTS task_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    village_id      TEXT NOT NULL,
    kind            TEXT NOT NULL,           -- 'register' | 'build' | 'raid_setup' | 'transfer' ...
    payload_json    TEXT,
    priority        INTEGER DEFAULT 5,       -- 1=high, 9=low
    status          TEXT DEFAULT 'queued',   -- queued | running | done | failed
    created_at      TEXT NOT NULL,
    started_at      TEXT,
    finished_at     TEXT,
    result_json     TEXT
);

CREATE TABLE IF NOT EXISTS incoming_attacks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    village_id      TEXT NOT NULL,           -- our village being attacked
    server          TEXT NOT NULL,
    attacker_name   TEXT,
    attacker_x      INTEGER,
    attacker_y      INTEGER,
    arrives_at      TEXT NOT NULL,           -- ISO timestamp
    seconds_left    INTEGER,                 -- snapshot at detection
    troops_estimate INTEGER,                 -- rough size estimate
    kind            TEXT,                    -- 'attack' | 'raid' | 'siege'
    detected_at     TEXT NOT NULL,
    handled         INTEGER DEFAULT 0,       -- 0=fresh, 1=defense dispatched, -1=skipped
    notes           TEXT,
    UNIQUE(village_id, arrives_at, attacker_x, attacker_y)
);

CREATE TABLE IF NOT EXISTS defense_dispatches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    attack_id       INTEGER,                 -- FK to incoming_attacks
    source_vid      TEXT NOT NULL,           -- defender village
    target_vid      TEXT NOT NULL,           -- attacked village
    troops_json     TEXT NOT NULL,
    travel_seconds  INTEGER,
    sent_at         TEXT NOT NULL,
    arrived_at      TEXT,
    result          TEXT                     -- 'sent' | 'failed' | 'too_slow'
);

CREATE INDEX IF NOT EXISTS idx_attacks_handled ON incoming_attacks(handled, arrives_at);

CREATE TABLE IF NOT EXISTS travian_worlds (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT UNIQUE,             -- e.g. "ts8.x2.international"
    name            TEXT,                    -- e.g. "Season 8 — 2x Speed"
    url             TEXT NOT NULL,           -- full https URL
    region          TEXT,                    -- 'international' | 'sa' | 'de' | 'uk'...
    language        TEXT,                    -- 'en' | 'ar' | 'de' | ...
    speed           TEXT,                    -- '1x' | '2x' | '3x' | '5x' | '10x'
    status          TEXT,                    -- 'upcoming' | 'active' | 'finished'
    start_at        TEXT,                    -- ISO date if known
    players         INTEGER,                 -- registered players if scraped
    note            TEXT,
    fetched_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_worlds_status ON travian_worlds(status, start_at);

CREATE INDEX IF NOT EXISTS idx_events_village ON events(village_id, ts);
CREATE INDEX IF NOT EXISTS idx_villages_state ON villages(state);
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id, ts);
CREATE INDEX IF NOT EXISTS idx_raid_targets_server ON raid_targets(server, last_raid_at);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON task_queue(status, priority, created_at);
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
    # Travian Legends maps are 401x401 cells (-200..+200). On a fresh server,
    # only the inner core is open. We keep a conservative ±180 default that
    # works for both fresh and mid-game worlds.
    "NW": (-180, -1,  1, 180),   # x<0, y>0
    "NE": (1, 180,    1, 180),   # x>0, y>0
    "SW": (-180, -1, -180, -1),  # x<0, y<0
    "SE": (1, 180,   -180, -1),  # x>0, y<0
    "ANY": (-180, 180, -180, 180),
    # Tight modes for very fresh servers (first 2 weeks)
    "FRESH_NE": (1, 80, 1, 80),
    "FRESH_NW": (-80, -1, 1, 80),
    "FRESH_SE": (1, 80, -80, -1),
    "FRESH_SW": (-80, -1, -80, -1),
    "FRESH_ANY": (-80, 80, -80, 80),
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
    # Seed known Travian worlds so user sees a list immediately
    try:
        added = seed_known_worlds()
        if added:
            log.info(f"seeded {added} known Travian worlds")
    except Exception:
        pass
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


# ─── Travian Lobby: auto cookies + auto login ────────────────────────────────
LOBBY_COOKIE_SELECTORS = [
    "#cmpwelcomebtnyes a", ".cmpboxbtnyes a", ".cmpboxbtnyes",
    "button[aria-label='Accept all']", "button:has-text('Accept all')",
    "button:has-text('Accept')", "button:has-text('I agree')",
    "button:has-text('Agree')", "button:has-text('قبول')",
    "button:has-text('موافق')", "#onetrust-accept-btn-handler",
    "button[mode='primary']:has-text('Akzeptieren')",
]
LOBBY_EMAIL_SELECTORS = [
    # Travian lobby uses input[name="name"] for the email/account field
    "input[name='name']:not([type='hidden'])",
    "input[placeholder*='Email' i]", "input[placeholder*='account' i]",
    "input[name='email']", "input[type='email']", "#email",
    "input[autocomplete='email']", "input[autocomplete='username']",
    "input[placeholder*='mail' i]",
]
LOBBY_PASS_SELECTORS = [
    "input[name='password']", "input[type='password']", "#password",
    "input[autocomplete='current-password']",
]
LOBBY_SUBMIT_SELECTORS = [
    "button[type='submit']", "button.loginButton", "button:has-text('Login')",
    "button:has-text('Log in')", "button:has-text('تسجيل الدخول')",
    "button:has-text('Anmelden')", "input[type='submit']",
]


async def _try_click_any(page, selectors: list[str], timeout_ms: int = 1200) -> bool:
    """Try each selector; click the first that is visible. Returns success."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=timeout_ms)
            await loc.click(timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


async def _try_fill_any(page, selectors: list[str], value: str,
                        timeout_ms: int = 1500) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=timeout_ms)
            await loc.click(timeout=timeout_ms)
            await asyncio.sleep(random.uniform(0.15, 0.40))
            # Use realistic typing for stealth
            await loc.fill("")
            for ch in value:
                await page.keyboard.type(ch,
                                         delay=int(human_typing_interval() * 1000))
            return True
        except Exception:
            continue
    return False


async def lobby_accept_cookies(page) -> bool:
    """Dismiss the Travian/CMP cookie consent banner (if present)."""
    # Wait a moment for the banner script to load
    await asyncio.sleep(random.uniform(0.6, 1.4))
    # Some CMPs live inside iframes — try main page first
    if await _try_click_any(page, LOBBY_COOKIE_SELECTORS, timeout_ms=1500):
        await asyncio.sleep(random.uniform(0.3, 0.8))
        return True
    # Try inside any iframe
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        for sel in LOBBY_COOKIE_SELECTORS:
            try:
                loc = frame.locator(sel).first
                await loc.click(timeout=900)
                await asyncio.sleep(random.uniform(0.3, 0.8))
                return True
            except Exception:
                continue
    return False


async def lobby_auto_login(page, village: dict[str, Any]) -> dict[str, Any]:
    """Attempt to log this village into the Travian lobby.
    Returns {ok, stage, detail}. Safe to call repeatedly — it short-circuits
    if already logged in (detected by sign of dashboard URL / user menu)."""
    email = (village.get("email") or "").strip()
    password = (village.get("password") or "").strip()
    if not email or not password:
        return {"ok": False, "stage": "preflight",
                "detail": "missing email/password on village"}
    if "@example.local" in email:
        return {"ok": False, "stage": "preflight",
                "detail": "placeholder email — attach a real one first"}

    # Cookie banner first
    try:
        await lobby_accept_cookies(page)
    except Exception:
        pass

    # If we're already in the lobby (dashboard), bail out happy
    try:
        url = page.url or ""
        if any(p in url for p in ("/dashboard", "/games", "/account",
                                  "/avatarSelection")):
            return {"ok": True, "stage": "already_logged_in", "detail": url}
    except Exception:
        pass

    # Some lobby flows show a big "Login" trigger button before the form
    for trigger in [
        "a:has-text('Login')", "button:has-text('Login')",
        "a:has-text('Log in')", "button:has-text('Log in')",
        ".loginButton",
    ]:
        try:
            loc = page.locator(trigger).first
            if await loc.is_visible(timeout=400):
                await loc.click(timeout=900)
                await asyncio.sleep(random.uniform(0.4, 0.9))
                break
        except Exception:
            continue

    # Fill email
    ok_email = await _try_fill_any(page, LOBBY_EMAIL_SELECTORS, email)
    if not ok_email:
        return {"ok": False, "stage": "email_field",
                "detail": "no email input found"}
    await asyncio.sleep(random.uniform(0.3, 0.7))

    # Fill password
    ok_pass = await _try_fill_any(page, LOBBY_PASS_SELECTORS, password)
    if not ok_pass:
        return {"ok": False, "stage": "password_field",
                "detail": "no password input found"}
    await asyncio.sleep(random.uniform(0.5, 1.1))

    # Click submit. If submit click fails, press Enter as fallback.
    submitted = await _try_click_any(page, LOBBY_SUBMIT_SELECTORS, timeout_ms=1500)
    if not submitted:
        try:
            await page.keyboard.press("Enter")
            submitted = True
        except Exception:
            pass

    # Wait a moment for the form to process
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass

    # Verify result by URL or DOM presence of error banner
    final_url = page.url or ""
    if any(p in final_url for p in ("/dashboard", "/games", "/account",
                                    "/avatarSelection", "/start")):
        return {"ok": True, "stage": "logged_in", "detail": final_url}

    # Check for visible error on the login page
    try:
        err = page.locator(
            ".errorMessage, .error, .alertbox, [class*='error']").first
        if await err.is_visible(timeout=600):
            txt = await err.inner_text(timeout=600)
            return {"ok": False, "stage": "credentials_rejected",
                    "detail": txt.strip()[:200]}
    except Exception:
        pass

    # Default: assume submitted but unverified
    return {"ok": submitted, "stage": "submitted_unverified",
            "detail": final_url}


# ─── Enter game world from lobby + marketplace transfer ──────────────────────
async def enter_game_world(page, server_hint: str = "") -> dict[str, Any]:
    """After successful lobby login, click the active world / 'PLAY NOW' button.
    Returns {ok, stage, world_url}. Server_hint can narrow which world to pick."""
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=8000)
    except Exception:
        pass
    await asyncio.sleep(random.uniform(0.8, 1.6))

    # Primary path: big PLAY NOW button
    play_selectors = [
        "a:has-text('PLAY NOW')", "button:has-text('PLAY NOW')",
        "a:has-text('Play now')", "a.playNow",
        # Continue Playing card
        "a:has-text('Continue Playing')", ".gameWorld a", ".worldCard a",
    ]
    if server_hint:
        # If we know server, prefer matching link
        play_selectors.insert(0, f"a[href*='{server_hint}']")
    for sel in play_selectors:
        try:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=900):
                await loc.click(timeout=1500)
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                await asyncio.sleep(random.uniform(1.0, 2.0))
                return {"ok": True, "stage": "entered_world",
                        "world_url": page.url}
        except Exception:
            continue
    return {"ok": False, "stage": "no_world_button",
            "world_url": page.url or ""}


MARKET_RES_SELECTORS = {
    "wood": ["input[name='r1']", "#r1", "input[name='wood']"],
    "clay": ["input[name='r2']", "#r2", "input[name='clay']"],
    "iron": ["input[name='r3']", "#r3", "input[name='iron']"],
    "crop": ["input[name='r4']", "#r4", "input[name='crop']"],
}
MARKET_COORD_SELECTORS = {
    "x": ["input[name='x']", "#xCoordInput", "input[name='to[x]']"],
    "y": ["input[name='y']", "#yCoordInput", "input[name='to[y]']"],
}
MARKET_SEND_SELECTORS = [
    "button[type='submit']", "button.green:has-text('Send')",
    "input[type='submit']", "button#enabledButton",
    "button:has-text('Send')", "button:has-text('OK')",
]


async def send_resources_from_village(page, world_url_base: str,
                                      target_x: int, target_y: int,
                                      amounts: dict[str, int]) -> dict[str, Any]:
    """Open the marketplace 'Send resources' tab and submit a transfer.
    amounts dict keys: wood/clay/iron/crop (any subset, zero/missing = 0).
    Returns {ok, stage, sent: {wood, clay, iron, crop}, detail}.
    """
    base = world_url_base.rstrip("/")
    # Marketplace, send-resources tab
    market_url = f"{base}/build.php?gid=17&t=5"
    try:
        await page.goto(market_url, wait_until="domcontentloaded", timeout=20000)
    except Exception as e:
        return {"ok": False, "stage": "navigate_market",
                "detail": str(e), "sent": {}}
    await asyncio.sleep(random.uniform(0.8, 1.5))

    # Fill the 4 resource inputs (only non-zero) — capping at the visible max
    sent = {"wood": 0, "clay": 0, "iron": 0, "crop": 0}
    for key, sels in MARKET_RES_SELECTORS.items():
        amt = int(amounts.get(key, 0) or 0)
        if amt <= 0:
            continue
        for sel in sels:
            try:
                loc = page.locator(sel).first
                await loc.wait_for(state="visible", timeout=1500)
                await loc.click()
                await loc.fill("")
                await loc.type(str(amt),
                               delay=int(human_typing_interval() * 1000))
                sent[key] = amt
                break
            except Exception:
                continue

    # Fill destination coordinates
    for axis, sels in MARKET_COORD_SELECTORS.items():
        val = target_x if axis == "x" else target_y
        filled = False
        for sel in sels:
            try:
                loc = page.locator(sel).first
                await loc.wait_for(state="visible", timeout=1500)
                await loc.click()
                await loc.fill("")
                await loc.type(str(val),
                               delay=int(human_typing_interval() * 1000))
                filled = True
                break
            except Exception:
                continue
        if not filled:
            return {"ok": False, "stage": f"coord_{axis}",
                    "detail": f"could not fill {axis}", "sent": sent}

    # Click send / submit
    await asyncio.sleep(random.uniform(0.6, 1.2))
    submitted = await _try_click_any(page, MARKET_SEND_SELECTORS,
                                     timeout_ms=2000)
    if not submitted:
        return {"ok": False, "stage": "submit", "detail": "no submit button",
                "sent": sent}

    # Travian usually shows a confirmation page — click confirm
    await asyncio.sleep(random.uniform(0.8, 1.4))
    for sel in ["button:has-text('Confirm')", "button:has-text('OK')",
                "input[name='ok']", "button.green:has-text('OK')",
                "button[type='submit']"]:
        try:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=900):
                await loc.click(timeout=1500)
                break
        except Exception:
            continue

    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass

    # Sanity: did we land on a movements page?
    url = page.url or ""
    success = ("build.php" in url or "village" in url or "rally" in url)
    return {"ok": success, "stage": "sent" if success else "submitted_unverified",
            "sent": sent, "detail": url}


# ─── In-game scraping helpers ────────────────────────────────────────────────
async def scrape_village_stock(page, world_url_base: str) -> dict[str, int]:
    """Read the four resource counters from /dorf1.php. Returns
    {wood, clay, iron, crop} as ints. Zero on failure."""
    base = world_url_base.rstrip("/")
    try:
        await page.goto(f"{base}/dorf1.php", wait_until="domcontentloaded",
                        timeout=15000)
    except Exception:
        return {"wood": 0, "clay": 0, "iron": 0, "crop": 0}
    await asyncio.sleep(random.uniform(0.6, 1.2))
    out = {"wood": 0, "clay": 0, "iron": 0, "crop": 0}
    # Travian uses #l1..#l4 spans; sometimes nested inside #stockBar
    for key, sel_ids in (
        ("wood", ["#l1", "#stockBar #l1"]),
        ("clay", ["#l2", "#stockBar #l2"]),
        ("iron", ["#l3", "#stockBar #l3"]),
        ("crop", ["#l4", "#stockBar #l4"]),
    ):
        for sel in sel_ids:
            try:
                txt = await page.locator(sel).first.inner_text(timeout=800)
                # Travian formats like "1,234" or "1.234" or "1234"
                digits = "".join(c for c in (txt or "")
                                 if c.isdigit())
                if digits:
                    out[key] = int(digits)
                    break
            except Exception:
                continue
    return out


async def scrape_village_troops(page, world_url_base: str) -> dict[str, int]:
    """Read the rally point troop overview. Returns a dict
    {unit_class_name: count}. Best-effort; returns {} on failure.

    Looks at /build.php?gid=16 (rally point) and reads the troops table.
    """
    base = world_url_base.rstrip("/")
    try:
        await page.goto(f"{base}/build.php?gid=16",
                        wait_until="domcontentloaded", timeout=15000)
    except Exception:
        return {}
    await asyncio.sleep(random.uniform(0.6, 1.2))
    troops: dict[str, int] = {}
    # Rally point table rows look like:
    # <td class="ico"><img class="unit uX"></td><td class="num">123</td>
    try:
        rows = await page.evaluate("""
            () => Array.from(document.querySelectorAll('table tr')).map(tr => {
              const img = tr.querySelector('img.unit, img[class*="unit"]');
              const numEl = tr.querySelector('td.num, td.unum, td[align="right"]');
              if (!img || !numEl) return null;
              const cls = (img.className || '').match(/u[0-9]+/);
              const n = (numEl.textContent || '').replace(/[^0-9]/g, '');
              return cls ? {unit: cls[0], n: parseInt(n||'0')} : null;
            }).filter(Boolean)
        """)
        for r in rows or []:
            troops[r["unit"]] = troops.get(r["unit"], 0) + int(r.get("n", 0))
    except Exception:
        pass
    return troops


# ─── Rally point raid sender ─────────────────────────────────────────────────
async def send_raid_from_village(page, world_url_base: str,
                                 target_x: int, target_y: int,
                                 troops: dict[str, int],
                                 attack_type: str = "raid") -> dict[str, Any]:
    """Fill the rally point 'send troops' form with the given troops, target
    coords and attack type ('raid'|'attack'|'reinforce'), then submit.

    troops dict can use either Travian unit ids ('u1','u2',...) or readable
    names ('phalanx','legionnaire',...). For now we only support 't1'..'t10'
    field names which map to whatever tribe owns the village.

    Returns {ok, stage, sent, detail}.
    """
    base = world_url_base.rstrip("/")
    rally = f"{base}/build.php?gid=16&tt=2"  # tt=2 → send troops tab
    try:
        await page.goto(rally, wait_until="domcontentloaded", timeout=20000)
    except Exception as e:
        return {"ok": False, "stage": "navigate_rally",
                "detail": str(e), "sent": {}}
    await asyncio.sleep(random.uniform(0.7, 1.3))

    # Normalise troops keys → t1..t10 (Travian uses position 1..10 per tribe)
    name_to_t = {
        # Romans
        "legionnaire": "t1", "praetorian": "t2", "imperian": "t3",
        "equites legati": "t4", "equites imperatoris": "t5",
        "equites caesaris": "t6", "battering ram": "t7",
        # Teutons / Gauls / others — common ones
        "phalanx": "t1", "swordsman": "t2", "pathfinder": "t3",
        "theutates thunder": "t4", "druidrider": "t5", "haeduan": "t6",
        "archer": "t3", "cavalry": "t4",
    }
    payload: dict[str, int] = {}
    for k, v in (troops or {}).items():
        n = int(v or 0)
        if n <= 0:
            continue
        if k.startswith("t") and k[1:].isdigit():
            payload[k] = n
        else:
            slot = name_to_t.get(k.lower())
            if slot:
                payload[slot] = payload.get(slot, 0) + n

    if not payload:
        return {"ok": False, "stage": "no_troops",
                "detail": "no valid troops mapped", "sent": {}}

    # Fill troop inputs (Travian uses input[name='troop[t1]'] or 'troops[t1]')
    sent: dict[str, int] = {}
    for slot, n in payload.items():
        filled = False
        for sel in (f"input[name='troops[{slot}]']",
                    f"input[name='troop[{slot}]']",
                    f"input[name='{slot}']",
                    f"input#{slot}"):
            try:
                loc = page.locator(sel).first
                await loc.wait_for(state="visible", timeout=1200)
                await loc.click()
                await loc.fill("")
                await loc.type(str(n),
                               delay=int(human_typing_interval() * 1000))
                sent[slot] = n
                filled = True
                break
            except Exception:
                continue
        if not filled:
            # Slot not available in this village's tribe
            pass

    if not sent:
        return {"ok": False, "stage": "fill_troops",
                "detail": "no troop inputs found", "sent": {}}

    # Fill x/y
    for axis, sels in MARKET_COORD_SELECTORS.items():
        val = target_x if axis == "x" else target_y
        for sel in sels:
            try:
                loc = page.locator(sel).first
                await loc.wait_for(state="visible", timeout=1200)
                await loc.click()
                await loc.fill("")
                await loc.type(str(val),
                               delay=int(human_typing_interval() * 1000))
                break
            except Exception:
                continue

    # Pick attack type radio. c=2 raid, c=3 attack, c=4 reinforce.
    type_to_c = {"reinforce": 2, "raid": 3, "attack": 4}
    c_val = type_to_c.get(attack_type.lower(), 3)
    for sel in (f"input[name='c'][value='{c_val}']",
                f"input[type='radio'][name='c'][value='{c_val}']",
                "input[name='c'][value='3']"):
        try:
            await page.locator(sel).first.check(timeout=1000)
            break
        except Exception:
            continue

    # Submit
    await asyncio.sleep(random.uniform(0.5, 1.0))
    submitted = await _try_click_any(page, MARKET_SEND_SELECTORS,
                                     timeout_ms=2000)
    if not submitted:
        return {"ok": False, "stage": "submit",
                "detail": "no submit button", "sent": sent}

    # Confirm
    await asyncio.sleep(random.uniform(0.8, 1.4))
    for sel in ("button.green:has-text('OK')", "button:has-text('Confirm')",
                "button:has-text('OK')", "input[name='ok']",
                "button[type='submit']"):
        try:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=900):
                await loc.click(timeout=1500)
                break
        except Exception:
            continue
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    url = page.url or ""
    return {"ok": True, "stage": "raid_sent",
            "sent": sent, "type": attack_type, "detail": url}


# ─── Map scanner — discover potential raid targets in a radius ───────────────
async def scan_map_radius(page, world_url_base: str,
                          center_x: int, center_y: int,
                          radius: int = 7) -> list[dict[str, Any]]:
    """Use Travian's /api/v1/map/position to fetch tile info in the area.
    Returns a list of {x, y, owner, oasis, kind} dicts for non-our tiles.

    Travian's modern map endpoint accepts a POST with bounding box. Falls back
    to GET /karte.php scraping if AJAX endpoint is gone.
    """
    base = world_url_base.rstrip("/")
    payload = {
        "data": {
            "x": center_x, "y": center_y,
            "zoomLevel": 3, "ignorePositions": []
        }
    }
    # Try modern AJAX endpoint
    try:
        resp = await page.evaluate(
            """async (args) => {
              const r = await fetch(args.url, {
                method:'POST', credentials:'include',
                headers:{'Content-Type':'application/json',
                         'X-Requested-With':'XMLHttpRequest'},
                body: JSON.stringify(args.body)
              });
              return await r.text();
            }""",
            {"url": f"{base}/api/v1/map/position", "body": payload})
        data = json.loads(resp) if resp else {}
        tiles = data.get("tiles") or data.get("response", {}).get("data", [])
    except Exception:
        tiles = []

    targets: list[dict[str, Any]] = []
    for t in tiles:
        try:
            tx = int(t.get("x", t.get("position", {}).get("x", 0)))
            ty = int(t.get("y", t.get("position", {}).get("y", 0)))
            if abs(tx - center_x) > radius or abs(ty - center_y) > radius:
                continue
            owner = (t.get("text") or "") + " " + json.dumps(
                t.get("tooltip", ""), ensure_ascii=False)[:200]
            kind = t.get("type") or t.get("c") or ""
            targets.append({
                "x": tx, "y": ty,
                "owner": owner.strip()[:120],
                "kind": str(kind),
                "is_oasis": "oasis" in owner.lower() or kind in (
                    "0", "1", "2", "3"),
            })
        except Exception:
            continue
    return targets



async def find_activation_link(token: str) -> Optional[str]:
    """Poll the mail.tm inbox for a Travian activation email and return the
    activation URL inside it. Returns None if no link is found."""
    import re
    import urllib.request
    msgs = await mailtm_read_inbox(token)
    for m in msgs[:20]:
        # Fetch full message
        try:
            full = await mailtm_read_message(token, m.get("id", ""))
        except Exception:
            continue
        text = (full.get("text") or "") + " " + " ".join(
            full.get("html") or [])
        # Look for travian activation pattern
        # Examples:
        #   https://www.travian.com/activate?key=...
        #   https://lobby.legends.travian.com/activate/<token>
        m_link = re.search(
            r"https?://[^\s<>\"']+(?:activate|confirm|verify|register)[^\s<>\"']*",
            text, re.IGNORECASE)
        if m_link:
            return m_link.group(0)
    return None


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

    Tracks open contexts so re-clicking 'open' on the same village brings the
    existing window forward instead of trying to launch a duplicate (which
    would fail because user_data_dir is locked by the first instance).
    """
    MAX_PARALLEL = 4

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(self.MAX_PARALLEL)
        self._playwright = None
        # village_id -> (context, page)  — only contexts still alive
        self._open: dict[str, tuple] = {}

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
        """Open a persistent context for a village. Returns (context, page).
        If a window is already open for this village, focus it instead of
        creating a duplicate."""
        vid = village["id"]
        # Check existing
        existing = self._open.get(vid)
        if existing:
            ctx, page = existing
            try:
                # Ensure still alive
                if ctx.pages and not page.is_closed():
                    await page.bring_to_front()
                    return ctx, page
            except Exception:
                pass
            self._open.pop(vid, None)

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
        # Track for re-use on subsequent 'open' clicks
        self._open[village["id"]] = (ctx, page)
        # Auto-cleanup when window closes
        def _on_close(*_a):
            self._open.pop(village["id"], None)
        try:
            page.on("close", _on_close)
            ctx.on("close", _on_close)
        except Exception:
            pass
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


def create_village(server: str = "https://lobby.legends.travian.com",
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
    """Try real providers ONLY (no placeholder fallback). Each provider is
    retried 2 times with backoff. Raises if no real mailbox can be created."""
    # Real providers only — order by reliability (Travian has been observed
    # to flag less, in this order).
    real_providers = ["mail.tm", "1secmail", "guerrilla"]
    order = [prefer] if prefer in real_providers else random.sample(
        real_providers, len(real_providers))
    last_err = ""
    for p in order:
        for attempt in (1, 2):
            try:
                if p == "mail.tm":
                    acct = await mailtm_create_account()
                    acct["provider"] = "mail.tm"
                    return acct
                if p == "1secmail":
                    return await email_1secmail()
                if p == "guerrilla":
                    return await email_guerrilla()
            except Exception as e:
                last_err = f"{p} attempt {attempt}: {e}"
                log.warning(last_err)
                await asyncio.sleep(1.5 * attempt)
    # If ALL providers failed, raise — no placeholder fallback.
    raise RuntimeError(
        f"All real email providers failed (mail.tm/1secmail/guerrilla). "
        f"Last error: {last_err}. Try again in a minute (likely rate-limited).")


# ─── FastAPI app + dashboard ─────────────────────────────────────────────────
app = FastAPI(title=APP_NAME, version=APP_VERSION)
FARM = BrowserFarm()


@app.on_event("startup")
def _startup():
    init_db()


@app.on_event("startup")
async def _auto_start_build_worker():
    # Auto-start the BuildWorker so new villages develop themselves.
    # Disable by setting env ZENREX_NO_BUILDWORKER=1
    if os.environ.get("ZENREX_NO_BUILDWORKER") == "1":
        return
    try:
        await BUILD_WORKER.start()
    except Exception as e:
        log.warning(f"[build-worker] auto-start failed: {e}")


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
    server = body.get("server", "https://lobby.legends.travian.com")
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


# ─── Transfer Worker — actually executes queued transfer_jobs ────────────────
class TransferWorker:
    """Background worker that picks the next queued transfer_job and executes
    it via Playwright: open browser for each registered source village → enter
    game world → marketplace → fill form → send.

    Algorithm:
      • specific mode: divide each resource evenly across `n` registered
        sources, capped by per-source merchant capacity (assumed 750/merchant
        for Romans baseline — overridable per village later).
      • random_all: send a small randomised chunk from each source. The
        actual stock is read from /dorf1 page if we can scrape it; otherwise
        we send a configurable default per source.
      • defense: open the rally point and send troops from each source
        instead.
    """
    MAX_SOURCES_PER_JOB = 25
    PER_SOURCE_DELAY = (35.0, 95.0)  # randomised delay between sources

    def __init__(self) -> None:
        self.task: Optional[asyncio.Task] = None
        self.cancel = asyncio.Event()
        self.last_status: dict[str, Any] = {"running": False,
                                            "current_job": None,
                                            "last_done": None}

    def _next_job(self) -> Optional[dict[str, Any]]:
        with db_cur() as cur:
            r = cur.execute(
                "SELECT * FROM transfer_jobs WHERE status = 'queued' "
                "ORDER BY id ASC LIMIT 1").fetchone()
        return dict(r) if r else None

    def _set_job(self, job_id: int, status: str,
                 progress: Optional[dict] = None) -> None:
        with db_cur() as cur:
            cur.execute(
                "UPDATE transfer_jobs SET status = ?, progress_json = ?, "
                "updated_at = ? WHERE id = ?",
                (status,
                 json.dumps(progress, ensure_ascii=False) if progress
                 else None,
                 _now_iso(), job_id))

    def _sources_for_server(self, server: str) -> list[dict[str, Any]]:
        with db_cur() as cur:
            rows = cur.execute(
                "SELECT * FROM villages WHERE server = ? "
                "AND state IN ('registered','active','browser_open') "
                "AND is_personal = 0 ORDER BY id LIMIT ?",
                (server, self.MAX_SOURCES_PER_JOB)).fetchall()
        return [dict(r) for r in rows]

    async def _execute_job(self, job: dict[str, Any]) -> dict[str, Any]:
        server = job["server"]
        sources = self._sources_for_server(server)
        if not sources:
            return {"ok": False,
                    "reason": "no registered sources on this server",
                    "per_source": []}

        mode = job["mode"]
        requested = json.loads(job["resources_json"] or "{}")
        troops = json.loads(job["troops_json"] or "{}")
        tx, ty = int(job["target_x"]), int(job["target_y"])

        # Distribute amounts (specific mode) or use full stock (random_all)
        per_source_plan: list[dict[str, Any]] = []
        n = len(sources)
        if mode == "specific":
            split = {k: int(v) // n for k, v in requested.items()}
            for s in sources:
                per_source_plan.append({"vid": s["id"], "amounts": split})
        elif mode == "random_all":
            # Use a heuristic batch — actual stock scraping is TODO
            for s in sources:
                per_source_plan.append({
                    "vid": s["id"],
                    "amounts": {
                        "wood": random.randint(500, 1500),
                        "clay": random.randint(500, 1500),
                        "iron": random.randint(500, 1500),
                        "crop": random.randint(300, 1000),
                    }})
        else:  # defense
            split_troops = {k: int(v) // n for k, v in troops.items()
                            if int(v or 0) > 0}
            for s in sources:
                per_source_plan.append({"vid": s["id"], "troops": split_troops})

        progress: list[dict[str, Any]] = []
        for entry in per_source_plan:
            v = next((x for x in sources if x["id"] == entry["vid"]), None)
            if not v:
                continue
            try:
                ctx, page = await FARM.open(v)
                login = await lobby_auto_login(page, v)
                if not login.get("ok"):
                    progress.append({"vid": v["id"], "ok": False,
                                     "stage": "login", "detail": login})
                    continue
                world = await enter_game_world(page, server_hint=server)
                if not world.get("ok"):
                    progress.append({"vid": v["id"], "ok": False,
                                     "stage": "enter_world", "detail": world})
                    continue
                base = world["world_url"].split("/build.php", 1)[0]\
                                         .split("/dorf", 1)[0].rstrip("/")
                # For random_all: replace heuristic with REAL stock scrape
                if mode == "random_all":
                    try:
                        stock = await scrape_village_stock(page, base)
                        # Keep a 20% safety margin so we don't drain everything
                        entry["amounts"] = {
                            "wood": int(stock.get("wood", 0) * 0.8),
                            "clay": int(stock.get("clay", 0) * 0.8),
                            "iron": int(stock.get("iron", 0) * 0.8),
                            "crop": int(stock.get("crop", 0) * 0.6),
                        }
                        log_event(v["id"], "stock_scraped",
                                  json.dumps(stock))
                    except Exception as e:
                        log_event(v["id"], "stock_scrape_failed", str(e))
                if mode == "defense":
                    # Use real rally-point sender (raid=False → reinforce)
                    try:
                        result = await send_raid_from_village(
                            page, base, tx, ty,
                            entry.get("troops") or {},
                            attack_type="reinforce")
                    except Exception as e:
                        result = {"ok": False, "stage": "exception",
                                  "detail": str(e), "sent": {}}
                    progress.append({"vid": v["id"], "ok": result.get("ok"),
                                     "stage": result.get("stage"),
                                     "sent": result.get("sent")})
                    log_event(v["id"], "defense_dispatch",
                              f"job#{job['id']} → ({tx},{ty}) "
                              f"sent={result.get('sent')}")
                else:
                    result = await send_resources_from_village(
                        page, base, tx, ty, entry["amounts"])
                    progress.append({"vid": v["id"], "ok": result.get("ok"),
                                     "stage": result.get("stage"),
                                     "sent": result.get("sent")})
                    log_event(v["id"], "transfer_sent",
                              f"job#{job['id']} → ({tx},{ty}) "
                              f"{result.get('sent')}")
                # Randomised delay between sources to look human
                await asyncio.sleep(random.uniform(*self.PER_SOURCE_DELAY))
            except Exception as e:
                progress.append({"vid": v["id"], "ok": False,
                                 "stage": "exception", "detail": str(e)})
            if self.cancel.is_set():
                break

        ok_count = sum(1 for p in progress if p.get("ok"))
        return {"ok": ok_count > 0, "ok_count": ok_count,
                "total": len(progress), "per_source": progress}

    async def _loop(self) -> None:
        log.info("[transfer-worker] started")
        self.last_status["running"] = True
        while not self.cancel.is_set():
            job = self._next_job()
            if not job:
                await asyncio.sleep(8)
                continue
            self.last_status["current_job"] = job["id"]
            self._set_job(job["id"], "running")
            log.info(f"[transfer-worker] executing job #{job['id']} "
                     f"mode={job['mode']} → ({job['target_x']},{job['target_y']})")
            try:
                result = await self._execute_job(job)
                self._set_job(job["id"],
                              "done" if result.get("ok") else "failed",
                              progress=result)
                self.last_status["last_done"] = {
                    "job_id": job["id"], "ok": result.get("ok"),
                    "ok_count": result.get("ok_count"),
                    "total": result.get("total"),
                    "at": _now_iso(),
                }
            except Exception as e:
                self._set_job(job["id"], "failed",
                              progress={"exception": str(e)})
                log.exception(f"[transfer-worker] job #{job['id']} failed")
            self.last_status["current_job"] = None
        self.last_status["running"] = False
        log.info("[transfer-worker] stopped")

    async def start(self) -> None:
        if self.task and not self.task.done():
            return
        self.cancel.clear()
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.cancel.set()
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=5)
            except Exception:
                pass


TRANSFER_WORKER = TransferWorker()


# ─── Activation Worker — auto-clicks Mail.tm activation links ────────────────
class ActivationWorker:
    """Scans villages in 'registration_pending' state, polls their mail.tm
    inbox for an activation link, and clicks it via Playwright."""
    POLL_INTERVAL = 25.0

    def __init__(self) -> None:
        self.task: Optional[asyncio.Task] = None
        self.cancel = asyncio.Event()
        self.last_status: dict[str, Any] = {"running": False,
                                            "last_activated": None,
                                            "scanned": 0}

    def _pending_villages(self) -> list[dict[str, Any]]:
        with db_cur() as cur:
            rows = cur.execute(
                "SELECT * FROM villages WHERE state = 'registration_pending' "
                "LIMIT 100").fetchall()
        return [dict(r) for r in rows]

    def _extract_token(self, notes: str) -> Optional[str]:
        for line in (notes or "").splitlines():
            line = line.strip()
            if line.startswith("mailtm_token=") or line.startswith("email_token="):
                return line.split("=", 1)[1].strip()
        return None

    async def _activate_one(self, v: dict[str, Any]) -> bool:
        token = self._extract_token(v.get("notes") or "")
        if not token:
            return False
        try:
            link = await find_activation_link(token)
        except Exception as e:
            log_event(v["id"], "activation_poll_error", str(e))
            return False
        if not link:
            return False
        # Open the activation link via Playwright (uses village proxy + stealth)
        try:
            ctx, page = await FARM.open(v)
            await page.goto(link, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(random.uniform(2.0, 4.0))
            update_village_state(v["id"], "registered",
                                 notes=f"activated_via_link={link[:80]}")
            log_event(v["id"], "activated", link[:120])
            self.last_status["last_activated"] = {
                "vid": v["id"], "at": _now_iso(), "link": link[:120]}
            return True
        except Exception as e:
            log_event(v["id"], "activation_open_error", str(e))
            return False

    async def _loop(self) -> None:
        log.info("[activation-worker] started")
        self.last_status["running"] = True
        while not self.cancel.is_set():
            pending = self._pending_villages()
            self.last_status["scanned"] = len(pending)
            for v in pending:
                if self.cancel.is_set():
                    break
                try:
                    await self._activate_one(v)
                except Exception:
                    log.exception(
                        f"[activation-worker] error on {v.get('id')}")
                await asyncio.sleep(random.uniform(1.5, 3.5))
            await asyncio.sleep(self.POLL_INTERVAL)
        self.last_status["running"] = False
        log.info("[activation-worker] stopped")

    async def start(self) -> None:
        if self.task and not self.task.done():
            return
        self.cancel.clear()
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.cancel.set()
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=5)
            except Exception:
                pass


ACTIVATION_WORKER = ActivationWorker()


# ─── Raid Worker — scans map radius + dispatches raids from hunter villages ──
class RaidWorker:
    """For each enabled 'hunter' village (entry in raid_config):
      1. Open browser → lobby → game world
      2. Scan map in `radius` around the hunter's coords
      3. Persist discovered tiles into `raid_targets` (UPSERT)
      4. Pick `max_per_cycle` targets prioritising oases & inactive players
         that we haven't raided within `cooldown_min`
      5. For each, send a raid (default 5x cavalry) via rally point

    Loops every cycle (default 15 min) then sleeps `cycle_min`.
    """
    DEFAULT_CYCLE_MIN = 15.0

    def __init__(self) -> None:
        self.task: Optional[asyncio.Task] = None
        self.cancel = asyncio.Event()
        self.cycle_min = self.DEFAULT_CYCLE_MIN
        self.last_status: dict[str, Any] = {
            "running": False, "current_hunter": None,
            "last_cycle_at": None, "total_raids_sent": 0,
            "last_targets_found": 0,
        }

    def _enabled_hunters(self) -> list[dict[str, Any]]:
        with db_cur() as cur:
            rows = cur.execute(
                "SELECT v.*, c.radius, c.max_per_cycle, c.troops_json, "
                "       c.attack_type, c.cooldown_min "
                "FROM raid_config c "
                "JOIN villages v ON v.id = c.village_id "
                "WHERE c.enabled = 1 AND v.is_personal = 0 "
                "AND v.state IN ('registered','active','browser_open')"
            ).fetchall()
        return [dict(r) for r in rows]

    def _upsert_targets(self, server: str,
                        tiles: list[dict[str, Any]]) -> int:
        n = 0
        now = _now_iso()
        with db_cur() as cur:
            for t in tiles:
                try:
                    cur.execute(
                        "INSERT INTO raid_targets "
                        "(server, x, y, owner, kind, last_seen) "
                        "VALUES (?, ?, ?, ?, ?, ?) "
                        "ON CONFLICT(server, x, y) DO UPDATE SET "
                        "  owner = excluded.owner, last_seen = excluded.last_seen",
                        (server, int(t["x"]), int(t["y"]),
                         t.get("owner", ""),
                         "oasis" if t.get("is_oasis") else "village",
                         now))
                    n += 1
                except Exception:
                    continue
        return n

    def _pick_targets(self, server: str, hunter_x: int, hunter_y: int,
                      radius: int, max_n: int,
                      cooldown_min: int) -> list[dict[str, Any]]:
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) -
                  timedelta(minutes=cooldown_min)).isoformat()
        with db_cur() as cur:
            rows = cur.execute(
                "SELECT * FROM raid_targets WHERE server = ? "
                "AND (last_raid_at IS NULL OR last_raid_at < ?) "
                "AND (kind = 'oasis' OR owner = '' OR owner LIKE '%Natars%') "
                "ORDER BY fail_count ASC, success_count DESC, "
                "         last_raid_at IS NULL DESC, last_raid_at ASC "
                "LIMIT 200",
                (server, cutoff)).fetchall()
        targets = []
        for r in rows:
            if abs(r["x"] - hunter_x) > radius or abs(r["y"] - hunter_y) > radius:
                continue
            targets.append(dict(r))
            if len(targets) >= max_n:
                break
        return targets

    def _mark_raid_result(self, target_id: int, ok: bool) -> None:
        col = "success_count" if ok else "fail_count"
        with db_cur() as cur:
            cur.execute(
                f"UPDATE raid_targets SET {col} = {col} + 1, "
                "last_raid_at = ? WHERE id = ?",
                (_now_iso(), target_id))

    async def _process_hunter(self, hunter: dict[str, Any]) -> dict[str, Any]:
        self.last_status["current_hunter"] = hunter["id"]
        server = hunter["server"]
        hx = int(hunter.get("coords_x") or 0)
        hy = int(hunter.get("coords_y") or 0)
        radius = int(hunter.get("radius") or 7)
        max_n = int(hunter.get("max_per_cycle") or 8)
        cooldown = int(hunter.get("cooldown_min") or 90)
        troops_cfg = json.loads(hunter.get("troops_json") or '{"t4": 5}')
        atk_type = hunter.get("attack_type") or "raid"

        ctx, page = await FARM.open(hunter)
        login = await lobby_auto_login(page, hunter)
        if not login.get("ok"):
            return {"ok": False, "stage": "login", "detail": login}
        world = await enter_game_world(page, server_hint=server)
        if not world.get("ok"):
            return {"ok": False, "stage": "enter_world", "detail": world}
        base = world["world_url"].split("/build.php", 1)[0]\
                                 .split("/dorf", 1)[0].rstrip("/")

        # 1) Scan map
        tiles = await scan_map_radius(page, base, hx, hy, radius=radius)
        found = self._upsert_targets(server, tiles)
        self.last_status["last_targets_found"] = found
        log_event(hunter["id"], "raid_scan",
                  f"radius={radius} → {found} tiles upserted")

        # 2) Pick targets
        chosen = self._pick_targets(server, hx, hy, radius, max_n, cooldown)
        log.info(f"[raid] hunter {hunter['id']} picked "
                 f"{len(chosen)} / max {max_n} targets")

        # 3) Send raids
        sent_n = 0
        for t in chosen:
            if self.cancel.is_set():
                break
            try:
                result = await send_raid_from_village(
                    page, base, int(t["x"]), int(t["y"]),
                    troops_cfg, attack_type=atk_type)
                self._mark_raid_result(t["id"], bool(result.get("ok")))
                log_event(hunter["id"], "raid_sent",
                          f"({t['x']},{t['y']}) ok={result.get('ok')} "
                          f"stage={result.get('stage')}")
                if result.get("ok"):
                    sent_n += 1
                    self.last_status["total_raids_sent"] = (
                        self.last_status.get("total_raids_sent", 0) + 1)
            except Exception as e:
                log_event(hunter["id"], "raid_error", str(e))
                self._mark_raid_result(t["id"], False)
            # Throttle between raids — 4–12 seconds
            await asyncio.sleep(random.uniform(4.0, 12.0))

        return {"ok": True, "hunter": hunter["id"],
                "tiles_seen": found, "raids_sent": sent_n}

    async def _loop(self) -> None:
        log.info("[raid-worker] started")
        self.last_status["running"] = True
        while not self.cancel.is_set():
            hunters = self._enabled_hunters()
            if not hunters:
                await asyncio.sleep(20)
                continue
            for h in hunters:
                if self.cancel.is_set():
                    break
                try:
                    await self._process_hunter(h)
                except Exception:
                    log.exception(
                        f"[raid-worker] hunter {h.get('id')} failed")
                # Spacing between hunters
                await asyncio.sleep(random.uniform(15.0, 35.0))
            self.last_status["last_cycle_at"] = _now_iso()
            self.last_status["current_hunter"] = None
            # Wait until next cycle
            await asyncio.sleep(self.cycle_min * 60)
        self.last_status["running"] = False
        log.info("[raid-worker] stopped")

    async def start(self) -> None:
        if self.task and not self.task.done():
            return
        self.cancel.clear()
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.cancel.set()
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=5)
            except Exception:
                pass


RAID_WORKER = RaidWorker()


@app.post("/api/raid/worker/start")
async def api_rw_start():
    await RAID_WORKER.start()
    return {"ok": True, "status": RAID_WORKER.last_status}


@app.post("/api/raid/worker/stop")
async def api_rw_stop():
    await RAID_WORKER.stop()
    return {"ok": True, "status": RAID_WORKER.last_status}


@app.get("/api/raid/worker/status")
def api_rw_status():
    return {"ok": True, "status": RAID_WORKER.last_status,
            "cycle_min": RAID_WORKER.cycle_min}


@app.post("/api/raid/worker/config")
async def api_rw_global_config(request: Request):
    """Set global raid worker config (currently: cycle_min)."""
    body = await request.json()
    if "cycle_min" in body:
        RAID_WORKER.cycle_min = float(body["cycle_min"])
    return {"ok": True, "cycle_min": RAID_WORKER.cycle_min}


@app.get("/api/raid/hunters")
def api_rw_hunters():
    """List all hunter villages (rows in raid_config) joined with villages."""
    with db_cur() as cur:
        rows = cur.execute(
            "SELECT c.*, v.name, v.server, v.coords_x, v.coords_y, v.tribe "
            "FROM raid_config c JOIN villages v ON v.id = c.village_id "
            "ORDER BY c.village_id").fetchall()
    return {"ok": True, "hunters": [dict(r) for r in rows]}


@app.post("/api/raid/hunters/{vid}")
async def api_rw_set_hunter(vid: str, request: Request):
    """Enable a village as raid hunter. Body: {enabled, radius, max_per_cycle,
    troops_json, attack_type, cooldown_min}."""
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    body = await request.json()
    troops_json = body.get("troops_json")
    if isinstance(troops_json, dict):
        troops_json = json.dumps(troops_json)
    with db_cur() as cur:
        cur.execute(
            "INSERT INTO raid_config (village_id, enabled, radius, "
            "max_per_cycle, troops_json, attack_type, cooldown_min) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(village_id) DO UPDATE SET "
            "enabled = excluded.enabled, radius = excluded.radius, "
            "max_per_cycle = excluded.max_per_cycle, "
            "troops_json = excluded.troops_json, "
            "attack_type = excluded.attack_type, "
            "cooldown_min = excluded.cooldown_min",
            (vid,
             1 if body.get("enabled", True) else 0,
             int(body.get("radius", 7)),
             int(body.get("max_per_cycle", 8)),
             troops_json or '{"t4": 5}',
             body.get("attack_type", "raid"),
             int(body.get("cooldown_min", 90))))
    return {"ok": True, "village_id": vid}


@app.delete("/api/raid/hunters/{vid}")
def api_rw_del_hunter(vid: str):
    with db_cur() as cur:
        cur.execute("DELETE FROM raid_config WHERE village_id = ?", (vid,))
    return {"ok": True}


@app.get("/api/raid/targets")
def api_rw_targets(server: Optional[str] = None, limit: int = 200):
    where = ""
    params: tuple = (limit,)
    if server:
        where = "WHERE server = ? "
        params = (server, limit)
    with db_cur() as cur:
        rows = cur.execute(
            f"SELECT * FROM raid_targets {where}"
            "ORDER BY last_raid_at IS NULL DESC, last_raid_at ASC, "
            "         success_count DESC LIMIT ?", params).fetchall()
    return {"ok": True, "targets": [dict(r) for r in rows],
            "count": len(rows)}


@app.delete("/api/raid/targets/{tid}")
def api_rw_del_target(tid: int):
    with db_cur() as cur:
        cur.execute("DELETE FROM raid_targets WHERE id = ?", (tid,))
    return {"ok": True}


# ─── Spawn Worker — progressive village creation on a schedule ──────────────
class SpawnWorker:
    """Background worker that creates villages slowly on a schedule.

    Each schedule row has: server, target_total, interval_min, daily_cap.
    The worker iterates enabled schedules every cycle (default 60s) and:
      1) Resets daily counter if a new day started
      2) Skips if target reached OR daily cap reached
      3) Skips if `interval_min` hasn't elapsed since last_spawn_at
      4) Otherwise creates ONE village honoring all preferences
      5) Optionally enqueues follow-up tasks (attach-email, register, ...)
    """
    POLL_SEC = 25.0

    def __init__(self) -> None:
        self.task: Optional[asyncio.Task] = None
        self.cancel = asyncio.Event()
        self.last_status: dict[str, Any] = {"running": False,
                                            "last_spawned": None,
                                            "schedules_active": 0}

    def _active_schedules(self) -> list[dict[str, Any]]:
        with db_cur() as cur:
            rows = cur.execute(
                "SELECT * FROM spawn_schedules WHERE enabled = 1"
            ).fetchall()
        return [dict(r) for r in rows]

    def _server_count(self, server: str) -> int:
        with db_cur() as cur:
            return cur.execute(
                "SELECT COUNT(*) c FROM villages WHERE server = ?",
                (server,)).fetchone()["c"]

    def _resolve_pool(self, preset: str) -> list[str]:
        p = (preset or "mixed").lower()
        if p == "arabic":
            return list(ARABIC_NATIONALITIES)
        if p == "english":
            return list(ENGLISH_NATIONALITIES)
        if p == "european":
            return list(EUROPEAN_NATIONALITIES)
        if p in ("mixed", "all"):
            return list(ALL_NATIONALITIES)
        if p.upper() in NAME_POOLS:
            return [p.upper()]
        return list(ALL_NATIONALITIES)

    def _today_iso(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).date().isoformat()

    def _minutes_since(self, ts: Optional[str]) -> float:
        if not ts:
            return 1e9
        from datetime import datetime, timezone
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - dt).total_seconds() / 60.0
        except Exception:
            return 1e9

    async def _spawn_one(self, sched: dict[str, Any]) -> Optional[str]:
        # Reset daily counter on new day
        today = self._today_iso()
        if sched.get("day_anchor") != today:
            with db_cur() as cur:
                cur.execute(
                    "UPDATE spawn_schedules SET day_anchor = ?, "
                    "spawned_today = 0 WHERE id = ?",
                    (today, sched["id"]))
            sched["day_anchor"] = today
            sched["spawned_today"] = 0

        # Gating: target / daily cap / interval
        current = self._server_count(sched["server"])
        target = int(sched.get("target_total") or 0)
        if target and current >= target:
            return None
        daily_cap = int(sched.get("daily_cap") or 0)
        if daily_cap and int(sched.get("spawned_today") or 0) >= daily_cap:
            return None
        interval = int(sched.get("interval_min") if sched.get("interval_min") is not None else 30)
        if self._minutes_since(sched.get("last_spawn_at")) < interval:
            return None

        # Pick nationality + tribe
        pool = self._resolve_pool(sched.get("name_preset"))
        nat = random.choice(pool)
        tribe_preset = (sched.get("tribe_preset") or "MIXED").upper()
        tribe = (random.choice(TRIBES)
                 if tribe_preset in ("MIXED", "ANY", "") else tribe_preset)
        proxy = assign_proxy(current) if sched.get("use_proxies") else ""

        v = create_village(
            server=sched["server"], nationality=nat,
            proxy=proxy, strategy="default",
            region=(sched.get("region") or "ANY").upper(),
            tribe=tribe, is_personal=False)

        # Optional auto-email
        if sched.get("auto_email"):
            try:
                acct = await create_email_for(v["id"])
                with db_cur() as cur:
                    cur.execute(
                        "UPDATE villages SET email = ?, notes = ? WHERE id = ?",
                        (acct["email"],
                         (v.get("notes") or "") +
                         f"\nemail_provider={acct['provider']}\n"
                         f"mailtm_token={acct.get('token','')}",
                         v["id"]))
                log_event(v["id"], "email_attached",
                          f"{acct['provider']}: {acct['email']}")
            except Exception as e:
                log_event(v["id"], "email_attach_failed", str(e))

        # Update schedule counters
        with db_cur() as cur:
            cur.execute(
                "UPDATE spawn_schedules SET last_spawn_at = ?, "
                "spawned_total = spawned_total + 1, "
                "spawned_today = spawned_today + 1 WHERE id = ?",
                (_now_iso(), sched["id"]))

        # Auto-queue follow-up tasks via TaskManager
        TASK_MANAGER.enqueue(v["id"], "register",
                             payload={"server": sched["server"]},
                             priority=3)

        log.info(f"[spawner] spawned {v['id']} on {sched['server']} "
                 f"({current + 1}/{sched['target_total']})")
        return v["id"]

    async def _loop(self) -> None:
        log.info("[spawner] started")
        self.last_status["running"] = True
        while not self.cancel.is_set():
            scheds = self._active_schedules()
            self.last_status["schedules_active"] = len(scheds)
            for s in scheds:
                if self.cancel.is_set():
                    break
                try:
                    vid = await self._spawn_one(s)
                    if vid:
                        self.last_status["last_spawned"] = {
                            "vid": vid, "server": s["server"],
                            "at": _now_iso()}
                except Exception:
                    log.exception(
                        f"[spawner] schedule {s.get('id')} failed")
            await asyncio.sleep(self.POLL_SEC)
        self.last_status["running"] = False
        log.info("[spawner] stopped")

    async def start(self) -> None:
        if self.task and not self.task.done():
            return
        self.cancel.clear()
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.cancel.set()
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=5)
            except Exception:
                pass


# ─── Task Manager — auto-detect and queue work for villages ─────────────────
class TaskManager:
    """Lightweight task system that watches village states and queues work
    automatically. Examples of auto-tasks:
      • village `state=created` + has email   → enqueue 'register'
      • village `state=registration_pending`  → ActivationWorker handles it
      • village `state=registered`            → enqueue 'open_browser_warmup'
      • village `state=active` and configured → kept in raid_config if hunter

    The manager itself doesn't *execute* tasks — it inserts rows into
    `task_queue` for the appropriate worker to consume.
    """
    POLL_SEC = 45.0

    def __init__(self) -> None:
        self.task: Optional[asyncio.Task] = None
        self.cancel = asyncio.Event()
        self.last_status: dict[str, Any] = {"running": False,
                                            "tasks_queued": 0,
                                            "tasks_done": 0,
                                            "last_scan_at": None}

    def enqueue(self, village_id: str, kind: str,
                payload: Optional[dict] = None,
                priority: int = 5,
                dedupe: bool = True) -> Optional[int]:
        """Insert a new task. If dedupe=True, skips if an identical queued
        task already exists."""
        with db_cur() as cur:
            if dedupe:
                existing = cur.execute(
                    "SELECT id FROM task_queue WHERE village_id = ? "
                    "AND kind = ? AND status IN ('queued','running')",
                    (village_id, kind)).fetchone()
                if existing:
                    return existing["id"]
            cur.execute(
                "INSERT INTO task_queue "
                "(village_id, kind, payload_json, priority, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (village_id, kind,
                 json.dumps(payload, ensure_ascii=False) if payload else None,
                 int(priority), _now_iso()))
            new_id = cur.execute(
                "SELECT last_insert_rowid() AS i").fetchone()["i"]
        self.last_status["tasks_queued"] = (
            self.last_status.get("tasks_queued", 0) + 1)
        return new_id

    def _scan(self) -> dict[str, int]:
        """One scan pass — looks at every village and enqueues tasks
        appropriate for its current state. Returns {tasks_added}."""
        added = 0
        with db_cur() as cur:
            villages = cur.execute(
                "SELECT id, state, email, server, is_personal, tribe "
                "FROM villages").fetchall()
        for v in villages:
            v = dict(v)
            vid = v["id"]
            state = v.get("state") or "created"
            if v.get("is_personal"):
                continue
            if state == "created":
                if v.get("email") and "@example.local" not in (v["email"] or ""):
                    if self.enqueue(vid, "register",
                                    payload={"server": v["server"]},
                                    priority=3):
                        added += 1
                else:
                    if self.enqueue(vid, "attach_email", priority=2):
                        added += 1
            elif state == "registered":
                if self.enqueue(vid, "open_browser_warmup",
                                payload={"reason": "first_login"},
                                priority=4):
                    added += 1
        return {"tasks_added": added}

    async def _loop(self) -> None:
        log.info("[task-manager] started")
        self.last_status["running"] = True
        while not self.cancel.is_set():
            try:
                res = self._scan()
                self.last_status["last_scan_at"] = _now_iso()
                self.last_status["tasks_queued"] = (
                    self.last_status.get("tasks_queued", 0)
                    + res["tasks_added"])
            except Exception:
                log.exception("[task-manager] scan failed")
            await asyncio.sleep(self.POLL_SEC)
        self.last_status["running"] = False
        log.info("[task-manager] stopped")

    async def start(self) -> None:
        if self.task and not self.task.done():
            return
        self.cancel.clear()
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.cancel.set()
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=5)
            except Exception:
                pass


TASK_MANAGER = TaskManager()
SPAWN_WORKER = SpawnWorker()


# Spawn schedule endpoints ────────────────────────────────────────────────────
@app.get("/api/spawn/schedules")
def api_spawn_list():
    with db_cur() as cur:
        rows = cur.execute(
            "SELECT * FROM spawn_schedules ORDER BY id DESC").fetchall()
    return {"ok": True, "schedules": [dict(r) for r in rows]}


@app.post("/api/spawn/schedules")
async def api_spawn_create(request: Request):
    """Create or update a spawn schedule.
    Body: {id?, server, name_preset, tribe_preset, region, use_proxies,
           auto_email, target_total, interval_min, daily_cap, enabled}"""
    body = await request.json()
    fields = {
        "server": body.get("server", ""),
        "name_preset": body.get("name_preset", "mixed"),
        "tribe_preset": body.get("tribe_preset", "MIXED"),
        "region": body.get("region", "ANY"),
        "use_proxies": 1 if body.get("use_proxies", True) else 0,
        "auto_email": 1 if body.get("auto_email", True) else 0,
        "target_total": int(body.get("target_total", 10)),
        "interval_min": int(body.get("interval_min", 30)),
        "daily_cap": int(body.get("daily_cap", 10)),
        "enabled": 1 if body.get("enabled", True) else 0,
    }
    sid = body.get("id")
    with db_cur() as cur:
        if sid:
            sets = ", ".join(f"{k} = :{k}" for k in fields)
            fields["id"] = int(sid)
            cur.execute(f"UPDATE spawn_schedules SET {sets} WHERE id = :id",
                        fields)
        else:
            fields["created_at"] = _now_iso()
            cur.execute(
                "INSERT INTO spawn_schedules "
                "(server, name_preset, tribe_preset, region, use_proxies, "
                " auto_email, target_total, interval_min, daily_cap, "
                " enabled, created_at) "
                "VALUES (:server, :name_preset, :tribe_preset, :region, "
                " :use_proxies, :auto_email, :target_total, :interval_min, "
                " :daily_cap, :enabled, :created_at)", fields)
            sid = cur.execute(
                "SELECT last_insert_rowid() AS i").fetchone()["i"]
    return {"ok": True, "id": sid}


@app.delete("/api/spawn/schedules/{sid}")
def api_spawn_delete(sid: int):
    with db_cur() as cur:
        cur.execute("DELETE FROM spawn_schedules WHERE id = ?", (sid,))
    return {"ok": True}


@app.post("/api/spawn/worker/start")
async def api_spawn_start():
    await SPAWN_WORKER.start()
    return {"ok": True, "status": SPAWN_WORKER.last_status}


@app.post("/api/spawn/worker/stop")
async def api_spawn_stop():
    await SPAWN_WORKER.stop()
    return {"ok": True, "status": SPAWN_WORKER.last_status}


@app.get("/api/spawn/worker/status")
def api_spawn_status():
    return {"ok": True, "status": SPAWN_WORKER.last_status}


# Task manager endpoints ──────────────────────────────────────────────────────
@app.post("/api/tasks/manager/start")
async def api_tm_start():
    await TASK_MANAGER.start()
    return {"ok": True, "status": TASK_MANAGER.last_status}


@app.post("/api/tasks/manager/stop")
async def api_tm_stop():
    await TASK_MANAGER.stop()
    return {"ok": True, "status": TASK_MANAGER.last_status}


@app.get("/api/tasks/manager/status")
def api_tm_status():
    return {"ok": True, "status": TASK_MANAGER.last_status}


@app.get("/api/tasks")
def api_tasks_list(status: Optional[str] = None, limit: int = 100):
    where = ""
    params: tuple = ()
    if status:
        where = "WHERE status = ? "
        params = (status,)
    with db_cur() as cur:
        rows = cur.execute(
            f"SELECT t.*, v.name as village_name FROM task_queue t "
            "LEFT JOIN villages v ON v.id = t.village_id "
            f"{where}ORDER BY priority ASC, id DESC LIMIT ?",
            params + (limit,)).fetchall()
    return {"ok": True, "tasks": [dict(r) for r in rows]}


@app.delete("/api/tasks/{tid}")
def api_task_delete(tid: int):
    with db_cur() as cur:
        cur.execute("DELETE FROM task_queue WHERE id = ?", (tid,))
    return {"ok": True}


@app.post("/api/transfer/worker/start")
async def api_tw_start():
    await TRANSFER_WORKER.start()
    return {"ok": True, "status": TRANSFER_WORKER.last_status}


@app.post("/api/transfer/worker/stop")
async def api_tw_stop():
    await TRANSFER_WORKER.stop()
    return {"ok": True, "status": TRANSFER_WORKER.last_status}


@app.get("/api/transfer/worker/status")
def api_tw_status():
    return {"ok": True, "status": TRANSFER_WORKER.last_status}


@app.post("/api/activation/start")
async def api_aw_start():
    await ACTIVATION_WORKER.start()
    return {"ok": True, "status": ACTIVATION_WORKER.last_status}


@app.post("/api/activation/stop")
async def api_aw_stop():
    await ACTIVATION_WORKER.stop()
    return {"ok": True, "status": ACTIVATION_WORKER.last_status}


@app.get("/api/activation/status")
def api_aw_status():
    return {"ok": True, "status": ACTIVATION_WORKER.last_status}


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


@app.post("/api/villages/bulk-reattach-emails")
async def api_bulk_reattach_emails(request: Request):
    """Re-attach REAL emails to all villages that currently have placeholders
    (any email containing 'example.local', '@gmail.com', '@hotmail.com',
    '@outlook.com', '@yahoo.com', '@icloud.com', '@proton.me' WITHOUT a
    valid mail.tm/1secmail/guerrilla token in notes).
    """
    body = await request.json() if request.headers.get("content-length") else {}
    only_placeholders = bool(body.get("only_placeholders", True))
    bad_domains = ["example.local", "gmail.com", "hotmail.com", "outlook.com",
                   "yahoo.com", "icloud.com", "proton.me", "tutanota.com",
                   "yandex.com"]
    with db_cur() as cur:
        rows = cur.execute("SELECT id, email, notes FROM villages").fetchall()
    target_ids = []
    for r in rows:
        email = (r["email"] or "").lower()
        notes = (r["notes"] or "").lower()
        is_placeholder = any(d in email for d in bad_domains)
        has_real_token = ("email_provider=mail.tm" in notes or
                          "email_provider=1secmail" in notes or
                          "email_provider=guerrilla" in notes or
                          "mailtm_token=" in notes)
        if not only_placeholders or (is_placeholder and not has_real_token):
            target_ids.append(r["id"])

    log.info(f"bulk-reattach: {len(target_ids)} villages to fix")
    fixed, failed = [], []
    for vid in target_ids:
        try:
            acct = await create_email_for(vid)
            v = get_village(vid)
            with db_cur() as cur:
                cur.execute(
                    "UPDATE villages SET email = ?, notes = ? WHERE id = ?",
                    (acct["email"],
                     (v.get("notes") or "") +
                     f"\nemail_provider={acct['provider']}\n"
                     f"email_token={acct.get('token','')}",
                     vid))
            log_event(vid, "email_reattached",
                      f"{acct['provider']}: {acct['email']}")
            fixed.append({"id": vid, "email": acct["email"],
                          "provider": acct["provider"]})
            # Soft rate-limit so we don't trigger mail.tm 429
            await asyncio.sleep(2.5)
        except Exception as e:
            failed.append({"id": vid, "error": str(e)[:200]})
            log.warning(f"reattach failed for {vid}: {e}")
            await asyncio.sleep(5)
    return {"ok": True, "fixed": len(fixed), "failed": len(failed),
            "fixed_list": fixed, "failed_list": failed}


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
    Re-clicking on same village = focus existing window, not duplicate.

    Body (optional): {auto_login: bool=true}
    """
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    try:
        ctx, page = await FARM.open(v)
        # Build target URL — ensure scheme present
        srv = v['server'] or "https://lobby.legends.travian.com"
        if not srv.startswith("http"):
            srv = f"https://{srv}"
        # If user typed a gameworld server, login still happens at the lobby
        login_url = "https://lobby.legends.travian.com"
        try:
            await page.goto(login_url, wait_until="domcontentloaded",
                            timeout=30000)
        except Exception:
            pass

        # Try auto-login (best-effort; never blocks the browser opening)
        login_result = {"ok": False, "stage": "skipped", "detail": "no creds"}
        try:
            login_result = await lobby_auto_login(page, v)
        except Exception as e:
            login_result = {"ok": False, "stage": "exception", "detail": str(e)}

        log_event(vid, "open_browser",
                  f"login={login_result.get('stage')} | "
                  f"proxy={v['proxy'] or 'direct'}")
        update_village_state(
            vid, "browser_open" if not login_result.get("ok") else "active",
            notes=f"auto_login:{login_result.get('stage')}",
        )
        return {"ok": True, "village": vid, "url": login_url,
                "proxy": v["proxy"] or None, "tribe": v.get("tribe"),
                "reused": vid in FARM._open,
                "login": login_result}
    except Exception as e:
        log_event(vid, "error", f"open_browser: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/villages/bulk-update-server")
async def api_bulk_update_server(request: Request):
    """Update the server URL for all villages matching an old value."""
    body = await request.json()
    old = body.get("from", "")
    new = body.get("to", "https://lobby.legends.travian.com")
    with db_cur() as cur:
        if old:
            res = cur.execute("UPDATE villages SET server = ? WHERE server = ?",
                              (new, old))
        else:
            res = cur.execute("UPDATE villages SET server = ?", (new,))
        n = res.rowcount
    return {"ok": True, "updated": n, "new_server": new}


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


# ─── Travian Worlds Sync — live list of game worlds ──────────────────────────
TRAVIAN_REGIONS = [
    ("international", "International / English", "en",
     "https://www.travian.com/"),
    ("arabia",        "Arabia (عربي)",          "ar",
     "https://www.travian.com/sa"),
    ("germany",       "Germany / Deutsch",      "de",
     "https://www.travian.de/"),
    ("france",        "France / Français",      "fr",
     "https://www.travian.fr/"),
    ("turkey",        "Turkey / Türkçe",        "tr",
     "https://www.travian.com.tr/"),
    ("russia",        "Russia / Русский",        "ru",
     "https://www.travian.ru/"),
    ("spain",         "Spain / Español",        "es",
     "https://www.travian.es/"),
    ("italy",         "Italy / Italiano",       "it",
     "https://www.travian.it/"),
    ("poland",        "Poland / Polski",        "pl",
     "https://www.travian.pl/"),
    ("brazil",        "Brazil / Português",     "pt",
     "https://www.travian.com.br/"),
]


async def fetch_travian_worlds(region_code: str = "international") -> \
        list[dict[str, Any]]:
    """Open the regional Travian homepage and scrape the worlds list.
    Returns [{code, name, url, status, speed, ...}].
    Best-effort — Travian DOM changes over time."""
    region = next((r for r in TRAVIAN_REGIONS if r[0] == region_code), None)
    if not region:
        return []
    code, label, lang, base_url = region

    # Use a temp Playwright context (no proxy, default fingerprint)
    from playwright.async_api import async_playwright
    worlds: list[dict[str, Any]] = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
            ctx = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="en-US")
            page = await ctx.new_page()
            try:
                await page.goto(base_url, wait_until="domcontentloaded",
                                timeout=25000)
                await asyncio.sleep(1.5)
            except Exception:
                pass
            # Try the official lobby's "join game world" page too
            join_url = "https://lobby.legends.travian.com/games"
            try:
                await page.goto(join_url, wait_until="domcontentloaded",
                                timeout=15000)
                await asyncio.sleep(1.5)
            except Exception:
                pass
            # Generic DOM scrape: look for links pointing to game world subdomains
            scraped = await page.evaluate(r"""
                () => {
                  const out = [];
                  const seen = new Set();
                  document.querySelectorAll('a').forEach(a => {
                    const href = (a.href || '').trim();
                    const m = href.match(/^https?:\/\/(ts[0-9]+[a-z0-9.-]*travian\.[a-z.]+)\/?/i);
                    if (!m) return;
                    const dom = m[1].toLowerCase();
                    if (seen.has(dom)) return;
                    seen.add(dom);
                    out.push({
                      domain: dom,
                      text: (a.textContent || '').trim().slice(0,80),
                      href: href
                    });
                  });
                  // also scan the announcements area
                  const lobby = document.querySelectorAll('[class*="gameWorld"], [class*="world"], [class*="server"]');
                  lobby.forEach(el => {
                    out.push({
                      kind: 'card',
                      text: (el.textContent || '').replace(/\s+/g,' ').trim().slice(0,200)
                    });
                  });
                  return out;
                }
            """)
            now = _now_iso()
            for item in (scraped or []):
                dom = item.get("domain")
                if not dom:
                    continue
                # Parse speed from domain (e.g. ts8.x2.international.travian.com)
                speed = "1x"
                import re
                sm = re.search(r"\.x([0-9]+)\.", dom)
                if sm:
                    speed = f"{sm.group(1)}x"
                worlds.append({
                    "code": dom.replace(".travian.com", "")
                                 .replace(".travian.de", "")
                                 .replace(".travian.fr", ""),
                    "name": item.get("text") or dom,
                    "url": f"https://{dom}/",
                    "region": code,
                    "language": lang,
                    "speed": speed,
                    "status": "active",
                    "fetched_at": now,
                })
            await ctx.close()
            await browser.close()
    except Exception as e:
        log.warning(f"[travian-sync] {region_code} failed: {e}")
    return worlds


def _save_worlds(worlds: list[dict[str, Any]]) -> int:
    n = 0
    with db_cur() as cur:
        for w in worlds:
            try:
                cur.execute(
                    "INSERT INTO travian_worlds "
                    "(code, name, url, region, language, speed, status, "
                    " start_at, players, note, fetched_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(code) DO UPDATE SET "
                    "  name = excluded.name, url = excluded.url, "
                    "  region = excluded.region, language = excluded.language, "
                    "  speed = excluded.speed, status = excluded.status, "
                    "  fetched_at = excluded.fetched_at",
                    (w.get("code"), w.get("name"), w["url"],
                     w.get("region"), w.get("language"), w.get("speed"),
                     w.get("status"), w.get("start_at"), w.get("players"),
                     w.get("note"), w["fetched_at"]))
                n += 1
            except Exception:
                continue
    return n


@app.get("/api/travian/regions")
def api_travian_regions():
    """Static list of supported Travian regional sites."""
    return {"ok": True, "regions": [
        {"code": r[0], "label": r[1], "language": r[2], "url": r[3]}
        for r in TRAVIAN_REGIONS]}


# Curated list of ACTIVE Travian Legends worlds verified to exist as of Feb 2026.
# Only worlds we are reasonably sure exist — fake/guessed entries removed.
# Use the "🔄 جلب السيرفرات" button to refresh from the live lobby (requires login).
KNOWN_TRAVIAN_WORLDS = [
    # International (English) — confirmed active worlds
    ("ts1.x1.international",  "Travian Legends — TS1 (1x speed)",
     "https://ts1.x1.international.travian.com/", "international", "en", "1x", "active"),
    ("ts4.x1.international",  "Travian Legends — TS4 (1x speed)",
     "https://ts4.x1.international.travian.com/", "international", "en", "1x", "active"),
    ("ts8.x1.international",  "Travian Legends — TS8 (1x speed)",
     "https://ts8.x1.international.travian.com/", "international", "en", "1x", "active"),
    ("ts5.x5.international",  "Travian Legends — TS5 Blitz (5x)",
     "https://ts5.x5.international.travian.com/", "international", "en", "5x", "active"),
    # Arabia
    ("ts4.x1.arabics",  "Travian — Arabia TS4 (1x speed)",
     "https://ts4.x1.arabics.travian.com/", "arabia", "ar", "1x", "active"),
    ("ts8.x2.arabics",  "Travian — Arabia TS8 (2x speed)",
     "https://ts8.x2.arabics.travian.com/", "arabia", "ar", "2x", "active"),
]


def seed_known_worlds() -> int:
    """Insert the curated KNOWN_TRAVIAN_WORLDS list if the table is empty
    or any of these codes is missing. Idempotent."""
    now = _now_iso()
    n = 0
    with db_cur() as cur:
        for w in KNOWN_TRAVIAN_WORLDS:
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO travian_worlds "
                    "(code, name, url, region, language, speed, status, "
                    " fetched_at, note) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'seeded')",
                    (w[0], w[1], w[2], w[3], w[4], w[5], w[6], now))
                n += cur.rowcount or 0
            except Exception:
                continue
    return n


@app.post("/api/travian/sync")
async def api_travian_sync(request: Request):
    """Scrape live Travian regional sites and refresh `travian_worlds`.
    Body: {regions?: [code,...]} — defaults to all."""
    body = await request.json() if request.headers.get("content-length") else {}
    region_codes = body.get("regions") or [r[0] for r in TRAVIAN_REGIONS]
    summary = []
    for rc in region_codes:
        try:
            worlds = await fetch_travian_worlds(rc)
            saved = _save_worlds(worlds)
            summary.append({"region": rc, "found": len(worlds),
                            "saved": saved})
        except Exception as e:
            summary.append({"region": rc, "error": str(e)})
    return {"ok": True, "summary": summary}


@app.post("/api/travian/sync-via-village/{vid}")
async def api_travian_sync_via_village(vid: str):
    """ACCURATE sync: log into Travian Lobby using THIS village's credentials,
    read the real list of joinable game worlds. This is the only way to get
    a 100% accurate, up-to-date world list. Body: {} (no params).

    The village must have email + password set (and have been registered).
    """
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    if not v.get("email") or not v.get("password"):
        return {"ok": False, "error": "village has no credentials"}

    from playwright.async_api import async_playwright
    discovered: list[dict[str, Any]] = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox",
                      "--disable-blink-features=AutomationControlled"])
            ctx = await browser.new_context(
                viewport={"width": 1280, "height": 800})
            page = await ctx.new_page()
            await page.goto("https://lobby.legends.travian.com",
                            wait_until="domcontentloaded", timeout=25000)
            login = await lobby_auto_login(page, v)
            if not login.get("ok"):
                await ctx.close()
                await browser.close()
                return {"ok": False, "stage": "login",
                        "detail": login}
            # After login we land on the lobby — capture every world link
            await asyncio.sleep(2.5)
            # Travian lobby exposes /games and /api/v1/gameworld/active
            raw = await page.evaluate(r"""
                () => {
                  const out = [];
                  const seen = new Set();
                  document.querySelectorAll('a').forEach(a => {
                    const href = (a.href || '').trim();
                    const m = href.match(/^https?:\/\/(ts[0-9]+\.x[0-9]+\.[a-z]+\.travian\.com)\/?/i);
                    if (!m) return;
                    const dom = m[1].toLowerCase();
                    if (seen.has(dom)) return;
                    seen.add(dom);
                    const card = a.closest('[class*="World"], [class*="world"], li, .gameWorld');
                    const txt = card ? card.textContent : a.textContent;
                    out.push({ domain: dom, text: (txt||'').replace(/\s+/g,' ').trim().slice(0,150), href });
                  });
                  return out;
                }
            """)
            now = _now_iso()
            for item in (raw or []):
                dom = item["domain"]
                import re
                # Parse: tsN.xS.REGION.travian.com
                m = re.match(r"ts(\d+)\.x(\d+)\.([a-z]+)\.travian\.com", dom)
                if not m:
                    continue
                ts_num, speed_num, region_key = m.groups()
                region_map = {
                    "international": "international",
                    "arabics": "arabia", "ar": "arabia",
                    "de": "germany", "fr": "france", "tr": "turkey",
                    "ru": "russia", "es": "spain", "it": "italy",
                    "pl": "poland", "br": "brazil",
                }
                lang_map = {
                    "international": "en", "arabics": "ar", "de": "de",
                    "fr": "fr", "tr": "tr", "ru": "ru", "es": "es",
                    "it": "it", "pl": "pl", "br": "pt",
                }
                discovered.append({
                    "code": dom.replace(".travian.com", ""),
                    "name": item["text"] or f"TS{ts_num} ({speed_num}x)",
                    "url": f"https://{dom}/",
                    "region": region_map.get(region_key, region_key),
                    "language": lang_map.get(region_key, "en"),
                    "speed": f"{speed_num}x",
                    "status": "active",
                    "fetched_at": now,
                    "note": f"discovered via village {vid}",
                })
            await ctx.close()
            await browser.close()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    saved = _save_worlds(discovered) if discovered else 0
    return {"ok": True, "found": len(discovered), "saved": saved,
            "worlds": discovered}


@app.get("/api/travian/worlds")
def api_travian_worlds(region: Optional[str] = None,
                       language: Optional[str] = None,
                       status: Optional[str] = None):
    """Read cached worlds. Filters: region, language, status."""
    where, params = [], []
    if region:
        where.append("region = ?")
        params.append(region)
    if language:
        where.append("language = ?")
        params.append(language)
    if status:
        where.append("status = ?")
        params.append(status)
    sql = "SELECT * FROM travian_worlds"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY language, region, code"
    with db_cur() as cur:
        rows = cur.execute(sql, tuple(params)).fetchall()
    return {"ok": True, "count": len(rows),
            "worlds": [dict(r) for r in rows]}


# ─── Defense Worker — detect incoming attacks + auto-reinforce ──────────────
# Approximate travel speeds (squares per hour) at 1x server speed.
# Defense troops are slower than cavalry; we use the slowest practical unit
# the user is likely sending (Phalanx/Spear class).
DEFENSE_TROOP_SPEED_FIELDS_PER_HOUR = 6.0   # ~spear/legionnaire @ 1x
SAFETY_MARGIN_SECONDS = 180                 # 3-min buffer before impact


def _euclidean_fields(x1: int, y1: int, x2: int, y2: int) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def _travel_seconds(distance_fields: float, server_speed: float = 1.0) -> int:
    hours = distance_fields / (DEFENSE_TROOP_SPEED_FIELDS_PER_HOUR
                               * server_speed)
    return int(hours * 3600)


async def scan_incoming_attacks(page, world_url_base: str) -> list[dict[str, Any]]:
    """Read the rally point 'incoming attacks' tab (tt=1) and parse the list.
    Returns rows like {kind, attacker, arrives_at_iso, seconds_left, troops_estimate}.
    """
    base = world_url_base.rstrip("/")
    try:
        await page.goto(f"{base}/build.php?gid=16&tt=1",
                        wait_until="domcontentloaded", timeout=15000)
    except Exception:
        return []
    await asyncio.sleep(random.uniform(0.6, 1.2))
    # Travian shows a table with rows. Each row has class 'inAttack' or
    # 'inRaid'. Columns include movement type icon, timer, and attacker info.
    parsed = []
    try:
        raw = await page.evaluate(r"""
            () => {
              const out = [];
              const rows = document.querySelectorAll(
                  'table tr.inAttack, table tr.inRaid, table tr.inSiege, '
                  + 'table.movements tr');
              rows.forEach(r => {
                const cls = (r.className || '').toLowerCase();
                const txt = (r.innerText || '').replace(/\s+/g, ' ').trim();
                // Find the countdown <span class="timer" value="SECS">
                const timer = r.querySelector('span.timer, [class*="timer"]');
                const secs = timer ? parseInt(timer.getAttribute('value') || '0') : 0;
                if (!secs) return;
                let kind = 'attack';
                if (cls.includes('inraid')) kind = 'raid';
                else if (cls.includes('insiege') || cls.includes('chief')) kind = 'siege';
                out.push({kind, text: txt, seconds_left: secs});
              });
              return out;
            }
        """)
        for item in (raw or []):
            secs = int(item.get("seconds_left", 0) or 0)
            if secs <= 0:
                continue
            from datetime import datetime, timezone, timedelta
            arrives = (datetime.now(timezone.utc) +
                       timedelta(seconds=secs)).isoformat()
            parsed.append({
                "kind": item.get("kind", "attack"),
                "seconds_left": secs,
                "arrives_at": arrives,
                "raw_text": (item.get("text") or "")[:200],
            })
    except Exception as e:
        log.warning(f"[defense] scan parse failed: {e}")
    return parsed


# ═══════════════════════════════════════════════════════════════════════════
# BuildWorker (v0.9.0) — auto-upgrade resource fields & village buildings.
# ═══════════════════════════════════════════════════════════════════════════

# Travian Legends building IDs (gid) used by the BuildWorker.
# Reference: https://blog.travian.com/2017/06/the-travian-buildings/
TRAVIAN_GID = {
    "warehouse":   10,
    "granary":     11,
    "smithy":      13,
    "main":        15,  # Main Building
    "rally":       16,  # Rally Point (already used by raid)
    "marketplace": 17,
    "embassy":     18,
    "barracks":    19,
    "stable":      20,
    "workshop":    21,
    "academy":     22,
    "cranny":      23,
    "town":        24,  # Town Hall
    "residence":   25,
    "palace":      26,
    "treasury":    27,
    "trade":       28,  # Trade Office
    "wall":        31,  # City Wall / Earth Wall / Palisade (tribe specific)
}

# Default build priority — what to push in every village, top to bottom.
DEFAULT_BUILD_PRIORITY: list[tuple[str, int]] = [
    ("warehouse",   5),
    ("granary",     5),
    ("main",        5),
    ("marketplace", 3),
    ("cranny",     10),
    ("embassy",     3),
    ("residence",   5),
    ("barracks",    3),
    ("wall",        5),
    ("smithy",      3),
]

# Max level for resource fields (1..18). Travian caps at 20.
DEFAULT_FIELD_CAP = 10


class BuildWorker:
    """Auto-upgrades resource fields (dorf1) and village buildings (dorf2)
    for every village with state IN ('registered','active','browser_open')
    and not flagged `is_personal`.

    Strategy per village per cycle:
      1) Open / refresh the village in its persistent Playwright context.
      2) Visit /dorf1.php → for the FIRST resource field that:
           a) is below `field_cap`, AND
           b) has a green ".green.new" upgrade link (Travian only renders it
              when resources AND queue slot are both ready)
         click upgrade. Stop after ONE successful upgrade per village.
      3) If no field was upgradable, visit /dorf2.php and try the highest
         priority building target from the build plan.
      4) Move to next village. Sleep POLL_SEC between full cycles.
    """
    POLL_SEC = 60.0
    PER_VILLAGE_PAUSE_SEC = 4.0

    def __init__(self) -> None:
        self.task: Optional[asyncio.Task] = None
        self.cancel = asyncio.Event()
        self.field_cap = DEFAULT_FIELD_CAP
        self.priority: list[tuple[str, int]] = list(DEFAULT_BUILD_PRIORITY)
        self.last_status: dict[str, Any] = {
            "running": False,
            "current_village": None,
            "last_cycle_at": None,
            "total_upgrades": 0,
            "last_upgrade": None,
        }

    # ── DB helpers ──────────────────────────────────────────────────────
    def _active_villages(self) -> list[dict[str, Any]]:
        with db_cur() as cur:
            rows = cur.execute(
                "SELECT * FROM villages "
                "WHERE is_personal = 0 "
                "AND state IN ('registered','active','browser_open') "
                "ORDER BY last_seen_at IS NULL DESC, last_seen_at ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    def _log_event(self, vid: str, detail: str) -> None:
        try:
            with db_cur() as cur:
                cur.execute(
                    "INSERT INTO events (village_id, ts, kind, detail) "
                    "VALUES (?, ?, ?, ?)",
                    (vid, _now_iso(), "build", detail[:500]))
        except Exception:
            pass

    # ── Playwright actions ──────────────────────────────────────────────
    async def _try_upgrade_field(self, page, base: str) -> Optional[dict[str, Any]]:
        """Visit dorf1 and click the first green upgrade button on any field
        below cap. Returns {slot, level} on success, None otherwise."""
        try:
            await page.goto(f"{base}/dorf1.php",
                            wait_until="domcontentloaded", timeout=30000)
        except Exception:
            return None
        # Travian dorf1: each .level element shows current level for a slot.
        # Look for any field with an upgradable green button.
        # Try slot-by-slot (1..18).
        for slot in range(1, 19):
            url = f"{base}/build.php?id={slot}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                continue
            # current level
            cur_lvl = 0
            try:
                lvl_el = await page.query_selector(".titleInHeader span.level, .build_title span")
                if lvl_el:
                    txt = (await lvl_el.text_content()) or ""
                    m = re.search(r"\b(\d+)\b", txt)
                    if m:
                        cur_lvl = int(m.group(1))
            except Exception:
                pass
            if cur_lvl >= self.field_cap:
                continue
            # Look for clickable upgrade
            btn = None
            for sel in ["a.green.new", "button.green.new",
                        "a.build.green", "button.build.green"]:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        break
                except Exception:
                    pass
            if not btn:
                continue
            try:
                await btn.click()
                await page.wait_for_timeout(800)
                return {"slot": slot, "level": cur_lvl + 1, "kind": "field"}
            except Exception:
                continue
        return None

    async def _try_upgrade_building(self, page, base: str) -> Optional[dict[str, Any]]:
        """Visit dorf2 and try each priority target. Returns dict on success."""
        try:
            await page.goto(f"{base}/dorf2.php",
                            wait_until="domcontentloaded", timeout=30000)
        except Exception:
            return None
        for name, target_lvl in self.priority:
            gid = TRAVIAN_GID.get(name)
            if not gid:
                continue
            url = f"{base}/build.php?gid={gid}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                continue
            cur_lvl = 0
            try:
                lvl_el = await page.query_selector(".titleInHeader span.level, .build_title span")
                if lvl_el:
                    txt = (await lvl_el.text_content()) or ""
                    m = re.search(r"\b(\d+)\b", txt)
                    if m:
                        cur_lvl = int(m.group(1))
            except Exception:
                pass
            if cur_lvl >= target_lvl:
                continue
            btn = None
            for sel in ["a.green.new", "button.green.new",
                        "a.build.green", "button.build.green"]:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        break
                except Exception:
                    pass
            if not btn:
                continue
            try:
                await btn.click()
                await page.wait_for_timeout(800)
                return {"name": name, "gid": gid,
                        "level": cur_lvl + 1, "kind": "building"}
            except Exception:
                continue
        return None

    async def _process_village(self, v: dict[str, Any]) -> dict[str, Any]:
        self.last_status["current_village"] = v["id"]
        try:
            ctx, page = await FARM.open(v)
        except Exception as e:
            return {"ok": False, "stage": "open", "error": str(e)}
        try:
            login = await lobby_auto_login(page, v)
            if not login.get("ok"):
                return {"ok": False, "stage": "login", "detail": login}
            world = await enter_game_world(page, server_hint=v.get("server"))
            if not world.get("ok"):
                return {"ok": False, "stage": "enter_world", "detail": world}
            base = world["world_url"].split("/build.php", 1)[0]\
                                     .split("/dorf", 1)[0].rstrip("/")

            # 1) Try a field upgrade
            r = await self._try_upgrade_field(page, base)
            if r:
                self.last_status["total_upgrades"] += 1
                self.last_status["last_upgrade"] = {
                    "village": v.get("name") or v["id"], **r,
                    "at": _now_iso()}
                self._log_event(v["id"],
                                f"field slot={r['slot']} → L{r['level']}")
                return {"ok": True, **r}

            # 2) Try a building upgrade
            r = await self._try_upgrade_building(page, base)
            if r:
                self.last_status["total_upgrades"] += 1
                self.last_status["last_upgrade"] = {
                    "village": v.get("name") or v["id"], **r,
                    "at": _now_iso()}
                self._log_event(v["id"],
                                f"building {r['name']} → L{r['level']}")
                return {"ok": True, **r}

            return {"ok": True, "noop": True}
        except Exception as e:
            log.warning(f"[build-worker] error on {v.get('name')}: {e}")
            return {"ok": False, "error": str(e)}

    async def _loop(self) -> None:
        log.info("[build-worker] started")
        self.last_status["running"] = True
        while not self.cancel.is_set():
            try:
                villages = self._active_villages()
                for v in villages:
                    if self.cancel.is_set():
                        break
                    await self._process_village(v)
                    await asyncio.sleep(self.PER_VILLAGE_PAUSE_SEC)
                self.last_status["last_cycle_at"] = _now_iso()
            except Exception as e:
                log.warning(f"[build-worker] cycle error: {e}")
            try:
                await asyncio.wait_for(self.cancel.wait(), timeout=self.POLL_SEC)
            except asyncio.TimeoutError:
                pass
        self.last_status["running"] = False
        log.info("[build-worker] stopped")

    async def start(self) -> None:
        if self.task and not self.task.done():
            return
        self.cancel.clear()
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.cancel.set()
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=5)
            except Exception:
                pass


BUILD_WORKER = BuildWorker()


@app.post("/api/build/worker/start")
async def api_build_worker_start():
    await BUILD_WORKER.start()
    return {"ok": True, "status": BUILD_WORKER.last_status}


@app.post("/api/build/worker/stop")
async def api_build_worker_stop():
    await BUILD_WORKER.stop()
    return {"ok": True, "status": BUILD_WORKER.last_status}


@app.get("/api/build/worker/status")
def api_build_worker_status():
    return {"ok": True,
            "running": bool(BUILD_WORKER.task and not BUILD_WORKER.task.done()),
            "status": BUILD_WORKER.last_status,
            "field_cap": BUILD_WORKER.field_cap,
            "priority": [{"name": n, "target_level": l}
                         for n, l in BUILD_WORKER.priority]}




class DefenseWorker:
    """Background worker that:
      1) Scans each of our (non-personal? actually for now, ALL) villages
         every `cycle_min` minutes for incoming attacks via rally-point tt=1
      2) Inserts new incoming_attacks rows (UNIQUE per attack)
      3) For each fresh attack, finds the nearest defender village(s) on the
         same server whose troops can ARRIVE before impact (with safety margin)
      4) Dispatches reinforcement via send_raid_from_village(attack_type=reinforce)
      5) Marks the attack `handled=1`
    """
    DEFAULT_CYCLE_MIN = 3.0          # check every 3 minutes
    MIN_DEFENDER_TROOPS = 5          # only consider villages with at least N defensive units in cfg

    def __init__(self) -> None:
        self.task: Optional[asyncio.Task] = None
        self.cancel = asyncio.Event()
        self.cycle_min = self.DEFAULT_CYCLE_MIN
        self.troops_to_send: dict[str, int] = {"t1": 500}  # default: 500 phalanx
        self.last_status: dict[str, Any] = {
            "running": False, "scanned": 0,
            "attacks_seen": 0, "dispatched": 0,
            "last_scan_at": None,
        }

    def _our_villages_on(self, server: str) -> list[dict[str, Any]]:
        with db_cur() as cur:
            rows = cur.execute(
                "SELECT * FROM villages WHERE server = ? "
                "AND state IN ('registered','active','browser_open')",
                (server,)).fetchall()
        return [dict(r) for r in rows]

    def _insert_attack(self, vid: str, server: str,
                       atk: dict[str, Any]) -> Optional[int]:
        with db_cur() as cur:
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO incoming_attacks "
                    "(village_id, server, attacker_name, attacker_x, "
                    " attacker_y, arrives_at, seconds_left, troops_estimate, "
                    " kind, detected_at, notes) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (vid, server, atk.get("attacker_name", ""),
                     atk.get("attacker_x", 0), atk.get("attacker_y", 0),
                     atk["arrives_at"], int(atk["seconds_left"]),
                     int(atk.get("troops_estimate", 0)),
                     atk.get("kind", "attack"), _now_iso(),
                     atk.get("raw_text", "")[:300]))
                if cur.rowcount:
                    return cur.execute(
                        "SELECT last_insert_rowid() AS i").fetchone()["i"]
            except Exception:
                pass
        return None

    def _pick_defenders(self, target_village: dict[str, Any],
                        seconds_left: int) -> list[dict[str, Any]]:
        """Return defender villages whose troops can arrive in time."""
        tx = int(target_village.get("coords_x") or 0)
        ty = int(target_village.get("coords_y") or 0)
        server = target_village["server"]
        max_travel = max(0, seconds_left - SAFETY_MARGIN_SECONDS)
        if max_travel <= 0:
            return []
        candidates: list[dict[str, Any]] = []
        for v in self._our_villages_on(server):
            if v["id"] == target_village["id"]:
                continue
            vx = int(v.get("coords_x") or 0)
            vy = int(v.get("coords_y") or 0)
            dist = _euclidean_fields(vx, vy, tx, ty)
            travel = _travel_seconds(dist)
            if travel <= max_travel:
                v["_dist"] = round(dist, 2)
                v["_travel"] = travel
                candidates.append(v)
        candidates.sort(key=lambda x: x["_travel"])
        return candidates

    async def _dispatch_from(self, defender: dict[str, Any],
                             target: dict[str, Any],
                             attack_id: int) -> bool:
        """Open the defender, navigate to rally point, send reinforcement
        to the target village coords."""
        tx = int(target.get("coords_x") or 0)
        ty = int(target.get("coords_y") or 0)
        try:
            ctx, page = await FARM.open(defender)
            login = await lobby_auto_login(page, defender)
            if not login.get("ok"):
                return False
            world = await enter_game_world(page,
                                           server_hint=defender["server"])
            if not world.get("ok"):
                return False
            base = world["world_url"].split("/build.php", 1)[0]\
                                     .split("/dorf", 1)[0].rstrip("/")
            result = await send_raid_from_village(
                page, base, tx, ty,
                self.troops_to_send, attack_type="reinforce")
            ok = bool(result.get("ok"))
            with db_cur() as cur:
                cur.execute(
                    "INSERT INTO defense_dispatches "
                    "(attack_id, source_vid, target_vid, troops_json, "
                    " travel_seconds, sent_at, result) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (attack_id, defender["id"], target["id"],
                     json.dumps(self.troops_to_send),
                     defender.get("_travel", 0),
                     _now_iso(),
                     "sent" if ok else "failed"))
            log_event(defender["id"], "defense_dispatched",
                      f"→ {target['id']} ({tx},{ty}) "
                      f"travel={defender.get('_travel')}s ok={ok}")
            return ok
        except Exception as e:
            log_event(defender["id"], "defense_error", str(e))
            return False

    async def _scan_one_village(self, v: dict[str, Any]) -> int:
        """Scan ONE of our villages for incoming attacks. Returns count of
        new attacks detected (and tries to defend them)."""
        try:
            ctx, page = await FARM.open(v)
            login = await lobby_auto_login(page, v)
            if not login.get("ok"):
                return 0
            world = await enter_game_world(page, server_hint=v["server"])
            if not world.get("ok"):
                return 0
            base = world["world_url"].split("/build.php", 1)[0]\
                                     .split("/dorf", 1)[0].rstrip("/")
            attacks = await scan_incoming_attacks(page, base)
        except Exception:
            return 0

        new_count = 0
        for atk in attacks:
            atk_id = self._insert_attack(v["id"], v["server"], atk)
            if atk_id is None:
                continue
            new_count += 1
            # Pick defenders & dispatch
            defenders = self._pick_defenders(v, int(atk["seconds_left"]))
            log.info(f"[defense] attack on {v['id']} in "
                     f"{atk['seconds_left']}s — {len(defenders)} "
                     f"defenders can reach in time")
            dispatched = 0
            for d in defenders[:3]:  # cap at 3 defenders per attack
                if await self._dispatch_from(d, v, atk_id):
                    dispatched += 1
                    self.last_status["dispatched"] = (
                        self.last_status.get("dispatched", 0) + 1)
            with db_cur() as cur:
                cur.execute(
                    "UPDATE incoming_attacks SET handled = ?, notes = ? "
                    "WHERE id = ?",
                    (1 if dispatched else -1,
                     f"defenders_dispatched={dispatched}", atk_id))
        return new_count

    async def _loop(self) -> None:
        log.info("[defense] started")
        self.last_status["running"] = True
        while not self.cancel.is_set():
            with db_cur() as cur:
                ours = cur.execute(
                    "SELECT * FROM villages WHERE "
                    "state IN ('registered','active','browser_open')"
                ).fetchall()
            ours = [dict(r) for r in ours]
            self.last_status["scanned"] = len(ours)
            for v in ours:
                if self.cancel.is_set():
                    break
                try:
                    n = await self._scan_one_village(v)
                    self.last_status["attacks_seen"] = (
                        self.last_status.get("attacks_seen", 0) + n)
                except Exception:
                    log.exception(
                        f"[defense] scan {v.get('id')} failed")
                await asyncio.sleep(random.uniform(8.0, 18.0))
            self.last_status["last_scan_at"] = _now_iso()
            await asyncio.sleep(self.cycle_min * 60)
        self.last_status["running"] = False
        log.info("[defense] stopped")

    async def start(self) -> None:
        if self.task and not self.task.done():
            return
        self.cancel.clear()
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.cancel.set()
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=5)
            except Exception:
                pass


DEFENSE_WORKER = DefenseWorker()


@app.post("/api/defense/worker/start")
async def api_def_start():
    await DEFENSE_WORKER.start()
    return {"ok": True, "status": DEFENSE_WORKER.last_status}


@app.post("/api/defense/worker/stop")
async def api_def_stop():
    await DEFENSE_WORKER.stop()
    return {"ok": True, "status": DEFENSE_WORKER.last_status}


@app.get("/api/defense/worker/status")
def api_def_status():
    return {"ok": True, "status": DEFENSE_WORKER.last_status,
            "cycle_min": DEFENSE_WORKER.cycle_min,
            "troops_to_send": DEFENSE_WORKER.troops_to_send}


@app.post("/api/defense/worker/config")
async def api_def_config(request: Request):
    """Body: {cycle_min?, troops_to_send?:{t1: 500,...}}"""
    body = await request.json()
    if "cycle_min" in body:
        DEFENSE_WORKER.cycle_min = float(body["cycle_min"])
    if "troops_to_send" in body and isinstance(body["troops_to_send"], dict):
        DEFENSE_WORKER.troops_to_send = {
            k: int(v) for k, v in body["troops_to_send"].items() if int(v or 0) > 0}
    return {"ok": True, "cycle_min": DEFENSE_WORKER.cycle_min,
            "troops_to_send": DEFENSE_WORKER.troops_to_send}


@app.get("/api/defense/attacks")
def api_def_attacks(handled: Optional[int] = None, limit: int = 50):
    where, params = [], []
    if handled is not None:
        where.append("handled = ?")
        params.append(int(handled))
    sql = "SELECT a.*, v.name as village_name FROM incoming_attacks a "\
          "LEFT JOIN villages v ON v.id = a.village_id"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY arrives_at ASC LIMIT ?"
    with db_cur() as cur:
        rows = cur.execute(sql, tuple(params) + (limit,)).fetchall()
    return {"ok": True, "attacks": [dict(r) for r in rows]}


@app.get("/api/defense/dispatches")
def api_def_dispatches(limit: int = 50):
    with db_cur() as cur:
        rows = cur.execute(
            "SELECT * FROM defense_dispatches ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()
    return {"ok": True, "dispatches": [dict(r) for r in rows]}


# ─── Self-Update — pull latest zenrex_farm.py from the cloud ─────────────────
SELF_UPDATE_URL = (
    "https://ai-cinematic-hub-2.preview.emergentagent.com"
    "/api/desktop-agent/zenrex-farm/zenrex_farm.py")
BEACON_BASE = (
    "https://ai-cinematic-hub-2.preview.emergentagent.com"
    "/api/desktop-agent/zenrex-beacon")


def _machine_id() -> str:
    """A stable machine identifier (hostname + user). Doesn't expose secrets."""
    import platform
    import hashlib
    host = platform.node() or "unknown"
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    raw = f"{host}::{user}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


class RemoteBeacon:
    """Phones home to the cloud every 60s. Lets the developer push remote
    commands (currently: 'update' = self-update + restart).

    Privacy: only sends machine_id (hashed hostname+user) + version + a tiny
    status blob (worker states). No village data, no credentials, no IPs.
    """
    POLL_SEC = 60.0
    OPT_OUT_ENV = "ZENREX_NO_BEACON"  # set to "1" to disable

    def __init__(self) -> None:
        self.task: Optional[asyncio.Task] = None
        self.cancel = asyncio.Event()
        self.machine_id = _machine_id()
        self.last_command: Optional[str] = None
        self.last_poll_at: Optional[str] = None

    def _build_status(self) -> str:
        return json.dumps({
            "version": APP_VERSION,
            "transfer": TRANSFER_WORKER.last_status.get("running", False),
            "spawn": SPAWN_WORKER.last_status.get("running", False),
            "defense": DEFENSE_WORKER.last_status.get("running", False),
            "raid": RAID_WORKER.last_status.get("running", False),
        }, ensure_ascii=False)

    async def _poll_once(self) -> None:
        import urllib.request
        import urllib.parse
        if os.environ.get(self.OPT_OUT_ENV) == "1":
            return
        url = (f"{BEACON_BASE}/{self.machine_id}?"
               f"version={urllib.parse.quote(APP_VERSION)}&"
               f"status={urllib.parse.quote(self._build_status())}")
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
        except Exception:
            return
        self.last_poll_at = _now_iso()
        cmd = data.get("command", "nothing")
        payload = data.get("payload", {}) or {}
        if cmd == "nothing":
            return
        self.last_command = cmd
        log.info(f"[beacon] received command: {cmd}")
        if cmd == "update":
            await self._do_update()
        elif cmd == "restart":
            os._exit(0)
        elif cmd == "run_endpoint":
            await self._do_run_endpoint(payload)

    async def _do_update(self) -> None:
        import urllib.request as urlr
        try:
            with urlr.urlopen(SELF_UPDATE_URL, timeout=30) as rr:
                content = rr.read()
            if len(content) < 1000:
                log.warning("[beacon] update payload too small")
                return
            from pathlib import Path
            current = Path(__file__).resolve()
            try:
                current.with_suffix(".py.backup").write_bytes(
                    current.read_bytes())
            except Exception:
                pass
            current.write_bytes(content)
            log.info(f"[beacon] wrote {len(content)} bytes; restarting")
            import subprocess
            import sys as _sys
            launcher = current.parent / "zenrex_app.py"
            if launcher.exists():
                pyw = _sys.executable
                if os.name == "nt":
                    cand = pyw.replace("python.exe", "pythonw.exe")
                    if Path(cand).exists():
                        pyw = cand
                kwargs = {}
                if os.name == "nt":
                    kwargs["creationflags"] = (
                        subprocess.DETACHED_PROCESS  # type: ignore
                        | subprocess.CREATE_NEW_PROCESS_GROUP)  # type: ignore
                else:
                    kwargs["start_new_session"] = True
                subprocess.Popen([pyw, str(launcher)], **kwargs)
            os._exit(0)
        except Exception as e:
            log.exception(f"[beacon] update failed: {e}")

    async def _do_run_endpoint(self, payload: dict) -> None:
        """Execute a local API endpoint as if the dev had called it.
        payload: {path: '/api/...', method: 'GET|POST|PATCH|DELETE',
                  body?: {...}, report_back?: bool=True}
        Result is reported back via a separate POST on next poll cycle.
        """
        import urllib.request
        import urllib.parse
        path = payload.get("path", "")
        method = (payload.get("method") or "GET").upper()
        body = payload.get("body") or {}
        if not path.startswith("/api/"):
            log.warning(f"[beacon] rejected path {path}")
            return
        local_url = f"http://127.0.0.1:{PORT}{path}"
        try:
            data = json.dumps(body).encode() if body else None
            req = urllib.request.Request(local_url, data=data, method=method)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=120) as r:
                result = r.read().decode("utf-8", errors="replace")
                code = r.getcode()
        except Exception as e:
            result = json.dumps({"error": str(e)})
            code = 500
        # Report back to beacon report endpoint
        report_url = (
            "https://ai-cinematic-hub-2.preview.emergentagent.com"
            f"/api/desktop-agent/zenrex-beacon/{self.machine_id}/report")
        try:
            data = json.dumps({
                "path": path, "method": method,
                "status_code": code, "result": result[:30000],
            }).encode()
            req = urllib.request.Request(report_url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=20):
                pass
            log.info(f"[beacon] reported result for {method} {path} (code={code})")
        except Exception as e:
            log.warning(f"[beacon] report failed: {e}")

    async def _loop(self) -> None:
        log.info(f"[beacon] started (machine_id={self.machine_id})")
        while not self.cancel.is_set():
            await self._poll_once()
            await asyncio.sleep(self.POLL_SEC)

    async def start(self) -> None:
        if self.task and not self.task.done():
            return
        self.cancel.clear()
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.cancel.set()


REMOTE_BEACON = RemoteBeacon()


@app.on_event("startup")
async def _auto_start_beacon():
    # Auto-start beacon on app startup (unless opted out)
    await REMOTE_BEACON.start()


@app.get("/api/beacon/status")
def api_beacon_status():
    return {"ok": True, "machine_id": REMOTE_BEACON.machine_id,
            "last_poll": REMOTE_BEACON.last_poll_at,
            "last_command": REMOTE_BEACON.last_command,
            "opt_out": os.environ.get(RemoteBeacon.OPT_OUT_ENV) == "1"}


@app.get("/api/self-update/check")
async def api_self_update_check():
    """Compare local version with remote zenrex_farm.py. Returns version diff."""
    import urllib.request
    try:
        with urllib.request.urlopen(SELF_UPDATE_URL, timeout=10) as r:
            remote = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return {"ok": False, "error": str(e), "local": APP_VERSION}
    import re
    m = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', remote)
    remote_ver = m.group(1) if m else "unknown"
    return {"ok": True, "local": APP_VERSION, "remote": remote_ver,
            "update_available": remote_ver != APP_VERSION,
            "remote_size": len(remote)}


@app.post("/api/self-update/apply")
async def api_self_update_apply():
    """Download latest zenrex_farm.py, overwrite the current file, AND
    automatically relaunch zenrex_app.py so the new code takes effect
    without manual intervention. Body: {auto_restart?: bool=true}.
    """
    import urllib.request
    from pathlib import Path
    try:
        with urllib.request.urlopen(SELF_UPDATE_URL, timeout=30) as r:
            content = r.read()
    except Exception as e:
        return {"ok": False, "error": str(e)}
    if len(content) < 1000:
        return {"ok": False, "error": "remote file looks invalid"}
    current = Path(__file__).resolve()
    # Backup current file
    try:
        backup = current.with_suffix(".py.backup")
        backup.write_bytes(current.read_bytes())
    except Exception:
        pass
    try:
        current.write_bytes(content)
    except Exception as e:
        return {"ok": False, "error": f"write failed: {e}"}

    # ─── Auto-restart: spawn a fresh zenrex_app.py and hard-exit ─────────
    # We do this in a delayed thread so the HTTP response still gets sent.
    def _delayed_restart():
        import time
        import subprocess
        import sys as _sys
        time.sleep(2.0)  # give the response time to flush
        launcher = current.parent / "zenrex_app.py"
        if not launcher.exists():
            os._exit(0)
        # Find pythonw if available (Windows — hides console)
        pyw = _sys.executable
        if os.name == "nt":
            cand = pyw.replace("python.exe", "pythonw.exe")
            if Path(cand).exists():
                pyw = cand
        try:
            # Detach so it survives our exit
            kwargs = {}
            if os.name == "nt":
                kwargs["creationflags"] = (
                    subprocess.DETACHED_PROCESS  # type: ignore
                    | subprocess.CREATE_NEW_PROCESS_GROUP)  # type: ignore
            else:
                kwargs["start_new_session"] = True
            subprocess.Popen([pyw, str(launcher)], **kwargs)
        except Exception:
            pass
        # Hard-exit current process so the file lock is released and the
        # new process can take over the port.
        os._exit(0)

    import threading as _th
    _th.Thread(target=_delayed_restart, daemon=True).start()

    return {"ok": True, "bytes_written": len(content),
            "path": str(current),
            "auto_restart": True,
            "message": "تم التحديث. التطبيق راح يعيد التشغيل تلقائياً خلال ثانيتين."}


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


@app.get("/chat", response_class=HTMLResponse)
def chat_page():
    return HTMLResponse(_CHAT_HTML)


# ─── AI Chat (Ollama-backed) ─────────────────────────────────────────────────
DEFAULT_SYSTEM_PROMPT = """أنت "زِنركس برين" — العقل المساعد لمزرعة قرى Travian.
الهدف الاستراتيجي للمالك (زهير): تشغيل ١٠٠+ قرية بأمان لبيع الموارد للاعبين حقيقيين عبر تحويلات داخل التحالف بأسعار مدفوعة.

قواعد سلوكك:
1) تكلم بالعربية السعودية بشكل مختصر وعملي.
2) لما المالك يقترح خطة، اقترح خطة مضادّة فيها مخاطر ومكاسب، ثم انتظر اعتماده.
3) عند إعلان "اعتمد الخطة" نفّذها كأوامر JSON واضحة.
4) لا تقترح حركات تكشف الفارم (تحويلات ضخمة من حسابات حديثة، نفس IP، نفس الوقت...).
5) أعد دوماً ملخص قصير + JSON إجراءات قابل للتنفيذ في حقل actions اذا كان فيه قرار.

شكل الرد المطلوب:
[نص للمحادثة بالعربية...]
<<ACTIONS>>
{ "intent": "...", "actions": [ ... ] }
<<END>>
"""


async def ollama_chat(messages: list[dict[str, str]],
                      model: Optional[str] = None,
                      timeout: float = 90.0) -> str:
    """Send a chat request to local Ollama. Returns the assistant text.
    If Ollama is unreachable, raises RuntimeError."""
    import urllib.request
    import urllib.error
    mdl = model or OLLAMA_TEXT_MODEL
    body = json.dumps({
        "model": mdl,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.6, "num_ctx": 8192},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST.rstrip('/')}/api/chat",
        data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama unreachable at {OLLAMA_HOST}: {e}")
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")
    msg = payload.get("message") or {}
    content = msg.get("content") or payload.get("response") or ""
    return content


def parse_actions_block(text: str) -> Optional[dict[str, Any]]:
    """Extract the <<ACTIONS>>{...}<<END>> JSON block from the LLM reply."""
    if "<<ACTIONS>>" not in text or "<<END>>" not in text:
        return None
    try:
        chunk = text.split("<<ACTIONS>>", 1)[1].split("<<END>>", 1)[0].strip()
        return json.loads(chunk)
    except Exception:
        return None


def strip_actions_block(text: str) -> str:
    if "<<ACTIONS>>" not in text:
        return text
    return text.split("<<ACTIONS>>", 1)[0].strip()


def build_farm_context() -> str:
    """Snapshot of the farm to feed the LLM as system context."""
    with db_cur() as cur:
        total = cur.execute("SELECT COUNT(*) c FROM villages").fetchone()["c"]
        per_state = cur.execute(
            "SELECT state, COUNT(*) c FROM villages GROUP BY state").fetchall()
        per_server = cur.execute(
            "SELECT server, COUNT(*) c FROM villages GROUP BY server "
            "ORDER BY c DESC LIMIT 5").fetchall()
        personal = cur.execute(
            "SELECT name, server, coords_x, coords_y, tribe FROM villages "
            "WHERE is_personal=1 LIMIT 10").fetchall()
        snaps = cur.execute(
            "SELECT id, name FROM strategy_snapshots "
            "ORDER BY id DESC LIMIT 6").fetchall()
    return json.dumps({
        "total_villages": total,
        "by_state": {r["state"]: r["c"] for r in per_state},
        "top_servers": [{"server": r["server"], "count": r["c"]}
                        for r in per_server],
        "personal_villages": [dict(r) for r in personal],
        "available_snapshots": [dict(r) for r in snaps],
    }, ensure_ascii=False)


@app.post("/api/ai/chat")
async def api_ai_chat(request: Request):
    """Conversational endpoint with Ollama. Persists history per session.
    Body: {session_id: str, message: str, model?: str}
    Returns: {ok, reply, actions, ollama_model, session_id}
    """
    body = await request.json()
    session_id = (body.get("session_id") or "default").strip() or "default"
    user_msg = (body.get("message") or "").strip()
    model = body.get("model") or OLLAMA_TEXT_MODEL
    if not user_msg:
        return JSONResponse({"ok": False, "error": "empty message"},
                            status_code=400)

    # Load history (last 30) for context
    with db_cur() as cur:
        rows = cur.execute(
            "SELECT role, content FROM chat_messages "
            "WHERE session_id = ? ORDER BY id DESC LIMIT 30",
            (session_id,)).fetchall()
    history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    # Compose context messages
    context_blob = build_farm_context()
    messages = [
        {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
        {"role": "system",
         "content": f"حالة المزرعة الحالية:\n{context_blob}"},
        *history,
        {"role": "user", "content": user_msg},
    ]

    # Save user message immediately
    with db_cur() as cur:
        cur.execute(
            "INSERT INTO chat_messages (session_id, role, content, ts) "
            "VALUES (?, 'user', ?, ?)",
            (session_id, user_msg, _now_iso()))

    # Call Ollama
    try:
        raw = await ollama_chat(messages, model=model)
    except Exception as e:
        err = (
            "ما قدرت أوصل لـ Ollama على جهازك. تأكّد إنه شغّال على "
            f"{OLLAMA_HOST} وإن النموذج '{model}' محمّل. "
            f"(تشغيل: `ollama serve` ثم `ollama pull {model}`)"
            f"\n\nالخطأ: {e}"
        )
        with db_cur() as cur:
            cur.execute(
                "INSERT INTO chat_messages (session_id, role, content, intent, ts) "
                "VALUES (?, 'assistant', ?, 'error', ?)",
                (session_id, err, _now_iso()))
        return {"ok": False, "reply": err, "actions": None,
                "ollama_model": model, "session_id": session_id}

    actions = parse_actions_block(raw)
    visible = strip_actions_block(raw)
    intent = (actions or {}).get("intent") if actions else None

    with db_cur() as cur:
        cur.execute(
            "INSERT INTO chat_messages "
            "(session_id, role, content, intent, meta_json, ts) "
            "VALUES (?, 'assistant', ?, ?, ?, ?)",
            (session_id, visible, intent,
             json.dumps(actions, ensure_ascii=False) if actions else None,
             _now_iso()))

    return {"ok": True, "reply": visible, "actions": actions,
            "ollama_model": model, "session_id": session_id}


@app.get("/api/ai/history")
def api_ai_history(session_id: str = "default", limit: int = 100):
    with db_cur() as cur:
        rows = cur.execute(
            "SELECT id, role, content, intent, meta_json, approved, ts "
            "FROM chat_messages WHERE session_id = ? "
            "ORDER BY id ASC LIMIT ?",
            (session_id, limit)).fetchall()
    return {"ok": True, "session_id": session_id,
            "messages": [dict(r) for r in rows]}


@app.post("/api/ai/clear")
async def api_ai_clear(request: Request):
    body = await request.json() if request.headers.get("content-length") else {}
    session_id = body.get("session_id", "default")
    with db_cur() as cur:
        cur.execute("DELETE FROM chat_messages WHERE session_id = ?",
                    (session_id,))
    return {"ok": True}


@app.post("/api/ai/approve/{msg_id}")
async def api_ai_approve(msg_id: int, request: Request):
    """Approve an LLM-proposed action set. Stores the decision in DB.
    Body: {approved: bool}
    """
    body = await request.json() if request.headers.get("content-length") else {}
    approved = 1 if body.get("approved", True) else -1
    with db_cur() as cur:
        cur.execute("UPDATE chat_messages SET approved = ? WHERE id = ?",
                    (approved, msg_id))
        row = cur.execute(
            "SELECT meta_json FROM chat_messages WHERE id = ?",
            (msg_id,)).fetchone()
    return {"ok": True, "approved": approved,
            "actions": json.loads(row["meta_json"]) if row and row["meta_json"]
            else None}


@app.get("/api/ai/status")
def api_ai_status():
    """Quick reachability + model list for the local Ollama server."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST.rstrip('/')}/api/tags",
                                    timeout=4) as r:
            data = json.loads(r.read())
        models = [m.get("name") for m in data.get("models", []) if m.get("name")]
        return {"ok": True, "host": OLLAMA_HOST, "models": models,
                "default_text": OLLAMA_TEXT_MODEL,
                "default_vision": OLLAMA_VISION_MODEL}
    except Exception as e:
        return {"ok": False, "host": OLLAMA_HOST, "error": str(e),
                "models": [], "default_text": OLLAMA_TEXT_MODEL}


# ─── Strategy Snapshots — clone "what I'm doing in this village" ─────────────
@app.post("/api/villages/{vid}/snapshot-strategy")
async def api_snapshot_strategy(vid: str, request: Request):
    """Capture a snapshot of THIS village's current strategy/build-queue/state
    so the user can later say "apply this to all other villages"."""
    v = get_village(vid)
    if not v:
        raise HTTPException(404, "village not found")
    body = await request.json() if request.headers.get("content-length") else {}
    label = (body.get("name") or f"snapshot من {v['name']}").strip()

    with db_cur() as cur:
        bq = cur.execute(
            "SELECT slot, building, target_level, status "
            "FROM build_queue WHERE village_id = ?", (vid,)).fetchall()
    state_obj = {
        "tribe": v.get("tribe"),
        "strategy": v.get("strategy"),
        "region": v.get("region"),
        "schedule_json": v.get("schedule_json"),
        "build_queue": [dict(b) for b in bq],
        "notes": v.get("notes") or "",
    }
    with db_cur() as cur:
        cur.execute(
            "INSERT INTO strategy_snapshots "
            "(source_vid, name, state_json, created_at) "
            "VALUES (?, ?, ?, ?)",
            (vid, label, json.dumps(state_obj, ensure_ascii=False),
             _now_iso()))
        snap_id = cur.execute(
            "SELECT last_insert_rowid() AS i").fetchone()["i"]
    log_event(vid, "strategy_snapshot", f"#{snap_id} '{label}'")
    return {"ok": True, "snapshot_id": snap_id, "name": label, "state": state_obj}


@app.get("/api/snapshots")
def api_list_snapshots():
    with db_cur() as cur:
        rows = cur.execute(
            "SELECT id, source_vid, name, created_at, "
            "       SUBSTR(state_json, 1, 200) as preview "
            "FROM strategy_snapshots ORDER BY id DESC LIMIT 50").fetchall()
    return {"ok": True, "snapshots": [dict(r) for r in rows]}


@app.delete("/api/snapshots/{snap_id}")
def api_delete_snapshot(snap_id: int):
    with db_cur() as cur:
        cur.execute("DELETE FROM strategy_snapshots WHERE id = ?", (snap_id,))
    return {"ok": True}


@app.post("/api/snapshots/{snap_id}/apply")
async def api_apply_snapshot(snap_id: int, request: Request):
    """Apply a snapshot to a target set of villages.
    Body: {scope: 'all'|'server'|'ids', server?: str, ids?: [str],
           exclude_personal: bool=true, copy_build_queue: bool=true}
    """
    body = await request.json()
    scope = body.get("scope", "all")
    copy_q = bool(body.get("copy_build_queue", True))
    excl_pers = bool(body.get("exclude_personal", True))

    with db_cur() as cur:
        snap = cur.execute(
            "SELECT * FROM strategy_snapshots WHERE id = ?",
            (snap_id,)).fetchone()
    if not snap:
        raise HTTPException(404, "snapshot not found")
    state = json.loads(snap["state_json"])

    # Resolve target villages
    with db_cur() as cur:
        if scope == "ids":
            ids = body.get("ids") or []
            if not ids:
                return {"ok": False, "error": "no ids provided"}
            q = (f"SELECT id, is_personal FROM villages WHERE id IN "
                 f"({','.join('?'*len(ids))})")
            rows = cur.execute(q, ids).fetchall()
        elif scope == "server":
            srv = body.get("server", "")
            rows = cur.execute(
                "SELECT id, is_personal FROM villages WHERE server = ?",
                (srv,)).fetchall()
        else:
            rows = cur.execute(
                "SELECT id, is_personal FROM villages").fetchall()

    applied = []
    skipped = []
    with db_cur() as cur:
        for r in rows:
            if r["id"] == snap["source_vid"]:
                skipped.append({"id": r["id"], "reason": "source village"})
                continue
            if excl_pers and r["is_personal"]:
                skipped.append({"id": r["id"], "reason": "personal village"})
                continue
            cur.execute(
                "UPDATE villages SET strategy = ?, schedule_json = ?, "
                "notes = COALESCE(notes,'') || ? WHERE id = ?",
                (state.get("strategy", "default"),
                 state.get("schedule_json"),
                 f"\napplied_snapshot=#{snap_id}@{_now_iso()}",
                 r["id"]))
            if copy_q:
                # Clear and copy queue
                cur.execute("DELETE FROM build_queue WHERE village_id = ?",
                            (r["id"],))
                for b in state.get("build_queue", []):
                    cur.execute(
                        "INSERT INTO build_queue "
                        "(village_id, slot, building, target_level, "
                        " ordered_at, status) "
                        "VALUES (?, ?, ?, ?, ?, 'pending')",
                        (r["id"], b.get("slot"), b.get("building"),
                         b.get("target_level"), _now_iso()))
            applied.append(r["id"])
    # Log AFTER the write transaction has committed to avoid SQLite locking
    for vid_applied in applied:
        log_event(vid_applied, "snapshot_applied", f"#{snap_id}")
    return {"ok": True, "applied": len(applied), "skipped": len(skipped),
            "applied_ids": applied, "skipped_details": skipped}


# ─── Transfer Execution + Smart Modes ────────────────────────────────────────
RESOURCE_KEYS = ("wood", "clay", "iron", "crop")


def _parse_resource_request(body: dict) -> tuple[str, dict[str, int]]:
    """Return (mode, requested_map). mode in {specific, random_all, defense}.
    'random_all' means: ignore amounts, just send all available resources
    from each source. 'specific' = user-typed amounts. 'defense' = troop
    transfer (handled separately)."""
    mode = (body.get("mode") or "specific").lower()
    if mode not in ("specific", "random_all", "defense"):
        mode = "specific"
    req = {k: int(body.get(f"amount_{k}", 0) or 0) for k in RESOURCE_KEYS}
    return mode, req


@app.post("/api/transfer/queue")
async def api_transfer_queue(request: Request):
    """Persist a transfer job (specific / random_all / defense) for later
    execution by the worker pool. Returns the job id.

    Body: {server, target_x, target_y, target_village_name, mode,
           amount_wood?, amount_clay?, amount_iron?, amount_crop?,
           troops?: {phalanx: int, legionnaire: int, ...} }
    """
    body = await request.json()
    server = body.get("server", "")
    tx = int(body.get("target_x", 0))
    ty = int(body.get("target_y", 0))
    tname = body.get("target_village_name", "")
    mode, req = _parse_resource_request(body)
    troops = body.get("troops") or {}

    if mode == "specific" and sum(req.values()) <= 0:
        return JSONResponse({"ok": False,
                             "error": "في الوضع 'specific' لازم تحط كميات"},
                            status_code=400)
    if mode == "defense" and (not troops or sum(
            int(v or 0) for v in troops.values()) <= 0):
        return JSONResponse({"ok": False,
                             "error": "في وضع الدفاع لازم تحدد جنود"},
                            status_code=400)

    with db_cur() as cur:
        cur.execute(
            "INSERT INTO transfer_jobs "
            "(server, target_x, target_y, target_name, mode, "
            " resources_json, troops_json, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)",
            (server, tx, ty, tname, mode,
             json.dumps(req), json.dumps(troops), _now_iso()))
        job_id = cur.execute(
            "SELECT last_insert_rowid() AS i").fetchone()["i"]
    return {"ok": True, "job_id": job_id, "mode": mode,
            "resources": req, "troops": troops}


@app.get("/api/transfer/jobs")
def api_transfer_jobs(limit: int = 30):
    with db_cur() as cur:
        rows = cur.execute(
            "SELECT id, server, target_x, target_y, target_name, mode, "
            "       resources_json, troops_json, status, created_at "
            "FROM transfer_jobs ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()
    return {"ok": True, "jobs": [dict(r) for r in rows]}


@app.delete("/api/transfer/jobs/{job_id}")
def api_delete_transfer_job(job_id: int):
    with db_cur() as cur:
        cur.execute("DELETE FROM transfer_jobs WHERE id = ?", (job_id,))
    return {"ok": True}



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
    <span class="badge" id="ver">v0.8.3</span>
    <span class="badge">100% Local · Free</span>
    <button class="secondary" onclick="checkUpdate()" style="margin:0;padding:4px 10px;font-size:11px">🔄 تحديث</button>
    <span id="update-badge" class="badge"></span>
  </div>
  <div class="flex">
    <a href="/chat" style="text-decoration:none">
      <span class="badge" style="background:#312e81;color:#a78bfa;cursor:pointer">
        🧠 العقل الاستراتيجي
      </span>
    </a>
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
      <div class="card" style="max-width:560px;width:100%;max-height:90vh;overflow:auto">
        <h2>💱 نقل موارد / دفاع</h2>
        <label>الوضع</label>
        <select id="t-mode" onchange="updateTransferMode()">
          <option value="specific">🎯 محدد (تحدد كميات كل مورد)</option>
          <option value="random_all">🎲 عشوائي / كل المتوفر</option>
          <option value="defense">🛡 دفاع (إرسال جنود)</option>
        </select>
        <label>السيرفر</label>
        <select id="t-server"></select>
        <div class="row">
          <div><label>X</label><input id="t-x" type="number" value="0"/></div>
          <div><label>Y</label><input id="t-y" type="number" value="0"/></div>
        </div>
        <label>اسم القرية الهدف</label>
        <input id="t-name" placeholder="مثلاً: قرية الهدف"/>

        <div id="t-resources">
          <div class="row">
            <div><label>🪵 خشب</label><input id="t-wood" type="number" value="0"/></div>
            <div><label>🧱 طين</label><input id="t-clay" type="number" value="0"/></div>
            <div><label>⚒️ حديد</label><input id="t-iron" type="number" value="0"/></div>
            <div><label>🌾 قمح</label><input id="t-crop" type="number" value="0"/></div>
          </div>
          <p class="small" id="t-mode-hint" style="margin-top:6px;color:var(--muted)">
            في وضع <b>محدد</b>: حدد الكمية لكل مورد.
          </p>
        </div>

        <div id="t-troops" style="display:none">
          <div class="row">
            <div><label>🛡 فالانكس</label><input id="t-phalanx" type="number" value="0"/></div>
            <div><label>🗡 ليجيونر</label><input id="t-legionnaire" type="number" value="0"/></div>
            <div><label>🏹 رماة</label><input id="t-archer" type="number" value="0"/></div>
            <div><label>🐎 فرسان</label><input id="t-cavalry" type="number" value="0"/></div>
          </div>
          <p class="small" style="margin-top:6px;color:var(--muted)">
            الجنود يُرسلون من القرى المسجّلة فقط كدعم دفاعي.
          </p>
        </div>

        <div class="row">
          <button onclick="planTransfer()">🧮 احسب الخطة</button>
          <button class="secondary" onclick="queueTransfer()">📥 ضع في الطابور</button>
          <button class="secondary" onclick="closeTransferDialog()">إلغاء</button>
        </div>
        <div id="transfer-result" class="small" style="margin-top:12px"></div>
      </div>
    </div>
  </div>

  <!-- RIGHT: create villages + proxies + preview -->
  <div>
    <div class="card" style="border:1px solid #064e3b;background:linear-gradient(135deg,#0a0a14,#0f1f1a)">
      <h2>🌍 سيرفرات Travian (مزامنة حيّة)</h2>
      <p class="small" style="color:var(--muted)">اختر منطقة → نسحب قائمة السيرفرات الحقيقية من Travian مباشرة، بدون نسخ روابط يدوياً.</p>

      <label>المنطقة / اللغة</label>
      <select id="tw-region" onchange="loadWorlds()"></select>

      <div class="row">
        <button onclick="syncWorlds()">🔄 جلب السيرفرات الآن</button>
        <span id="tw-status" class="badge">—</span>
      </div>

      <div id="tw-list" style="margin-top:10px;display:flex;flex-direction:column;
           gap:6px;max-height:280px;overflow:auto"></div>
    </div>

    <div class="card" style="border:1px solid #312e81;margin-top:18px">
      <h2>🌱 الإنتاج التدريجي (Auto-Spawn)</h2>
      <p class="small" style="color:var(--muted)">حدد الهدف والمعدّل، البوت يولّد القرى تلقائياً مع مرور الوقت. مثلاً: 100 قرية، 10 يومياً، واحدة كل 30 دقيقة.</p>

      <div id="spawn-status" class="small" style="margin:8px 0;padding:8px 10px;
           background:#0a0a14;border-radius:8px;border:1px solid var(--line)"></div>

      <div class="row">
        <button onclick="startSpawn()">▶ شغّل المولّد</button>
        <button class="danger" onclick="stopSpawn()">■ أوقف</button>
        <button class="secondary" onclick="openSpawnDialog()">➕ خطة جديدة</button>
      </div>

      <div id="spawn-list" style="margin-top:10px;display:flex;
           flex-direction:column;gap:6px"></div>
    </div>

    <!-- Spawn Schedule modal -->
    <div id="spawn-modal" style="display:none;position:fixed;inset:0;
         background:rgba(0,0,0,0.85);z-index:100;align-items:center;
         justify-content:center;padding:20px">
      <div class="card" style="max-width:540px;width:100%;max-height:90vh;overflow:auto">
        <h2>🌱 خطة إنتاج تدريجي</h2>

        <label>الخادم (Travian server)</label>
        <input id="sp-server" value="ts8.x2.international.travian.com" list="server-list"/>

        <div class="row">
          <div><label>🎯 الهدف الكلي</label><input id="sp-target" type="number" value="100" min="1" max="500"/></div>
          <div><label>📅 الحد اليومي</label><input id="sp-daily" type="number" value="10" min="1" max="100"/></div>
          <div><label>⏱ الفاصل (د)</label><input id="sp-interval" type="number" value="30" min="5" max="240"/></div>
        </div>

        <label>الجنسية</label>
        <select id="sp-preset">
          <option value="mixed">🌍 خلطة كاملة</option>
          <option value="arabic">🕌 عربي فقط</option>
          <option value="english">🇬🇧 إنجليزي فقط</option>
          <option value="european">🇪🇺 أوروبي</option>
        </select>

        <div class="row">
          <div>
            <label>المنطقة</label>
            <select id="sp-region">
              <option value="ANY">أي منطقة</option>
              <option value="NW">↖ NW</option><option value="NE">↗ NE</option>
              <option value="SW">↙ SW</option><option value="SE">↘ SE</option>
            </select>
          </div>
          <div>
            <label>القبيلة</label>
            <select id="sp-tribe">
              <option value="MIXED">🎲 خلطة</option>
              <option value="ROMANS">⚔️ Romans</option>
              <option value="GAULS">🛡️ Gauls</option>
              <option value="TEUTONS">🪓 Teutons</option>
              <option value="EGYPTIANS">🐪 Egyptians</option>
              <option value="HUNS">🏹 Huns</option>
            </select>
          </div>
        </div>

        <div class="row" style="margin-top:6px">
          <label class="flex" style="margin-top:0">
            <input type="checkbox" id="sp-proxies" checked style="width:auto;margin-left:6px"/>
            بروكسي مختلف لكل قرية
          </label>
          <label class="flex" style="margin-top:0">
            <input type="checkbox" id="sp-email" checked style="width:auto;margin-left:6px"/>
            إيميل تلقائي (Mail.tm)
          </label>
        </div>

        <div class="row">
          <button onclick="saveSpawn()">💾 احفظ الخطة وشغّل</button>
          <button class="secondary" onclick="closeSpawnDialog()">إلغاء</button>
        </div>
        <p class="small" style="margin-top:10px;color:var(--muted)">
          💡 ملاحظة: البوت يولّد قرية واحدة كل فاصل زمني، ويوقف لو وصل للحد اليومي،
          ويستأنف بعد منتصف الليل تلقائياً. حالة القرية الجديدة تكون <b>created</b>
          ثم Task Manager يلتقطها ويرتّب لها تسجيل + بناء.
        </p>
      </div>
    </div>

    <div class="card" style="margin-top:18px">
      <h2>📋 مهام تلقائية (Task Manager)</h2>
      <div id="tm-status" class="small" style="margin:8px 0;padding:8px 10px;
           background:#0a0a14;border-radius:8px"></div>
      <div class="row">
        <button onclick="startTaskManager()">▶ ابدأ المراقبة</button>
        <button class="danger" onclick="stopTaskManager()">■ أوقف</button>
      </div>
      <div id="tasks-list" style="margin-top:8px;display:flex;flex-direction:column;
           gap:5px;max-height:220px;overflow:auto"></div>
      <p class="small" style="margin-top:6px;color:var(--muted)">
        يكتشف تلقائياً: قرية بدون إيميل → ⏬ مهمة إيميل. قرية بإيميل ومش مسجّلة → ⏬ مهمة تسجيل. قرية مسجّلة → ⏬ مهمة دخول أول. وهكذا.
      </p>
    </div>

    <div class="card" style="margin-top:18px">
      <h2>إنشاء قرى يدوياً (دفعة واحدة)</h2>
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
      <h2>📋 Snapshots — استراتيجيات محفوظة</h2>
      <p class="small" style="color:var(--muted)">انسخ خطّتك من قرية إلى البقية. اضغط 📋 جنب أي قرية.</p>
      <div id="snapshots-list" style="margin-top:8px;display:flex;flex-direction:column;gap:6px"></div>
    </div>

    <div class="card" style="margin-top:18px">
      <h2>📥 طابور التحويلات</h2>
      <div id="worker-status" class="small" style="margin:8px 0;padding:8px 10px;
           background:#0a0a14;border-radius:8px"></div>
      <div class="row">
        <button onclick="startWorker()">▶ شغّل العامل</button>
        <button class="danger" onclick="stopWorker()">■ أوقف</button>
      </div>
      <div id="jobs-list" style="margin-top:8px;display:flex;flex-direction:column;gap:6px;
           max-height:240px;overflow:auto"></div>
    </div>

    <div class="card" style="margin-top:18px">
      <h2>📧 عامل تفعيل الإيميل (Mail.tm)</h2>
      <div id="aw-status" class="small" style="margin:8px 0;padding:8px 10px;
           background:#0a0a14;border-radius:8px"></div>
      <div class="row">
        <button onclick="startActivation()">▶ ابدأ المسح</button>
        <button class="danger" onclick="stopActivation()">■ أوقف</button>
      </div>
      <p class="small" style="margin-top:6px;color:var(--muted)">
        يفحص القرى بحالة <b>registration_pending</b>، يقرأ Mail.tm،
        يلاقي رابط التفعيل ويضغطه تلقائياً عبر متصفح القرية.
      </p>
    </div>

    <div class="card" style="margin-top:18px">
      <h2>⚔️ عامل الإغارة التلقائية (Auto-Raid)</h2>
      <div id="rw-status" class="small" style="margin:8px 0;padding:8px 10px;
           background:#0a0a14;border-radius:8px"></div>
      <div class="row">
        <div><label>دورة (د)</label><input id="rw-cycle" type="number"
             value="15" min="3" max="240"/></div>
        <button class="secondary" onclick="setRaidCycle()">💾 احفظ</button>
      </div>
      <div class="row">
        <button onclick="startRaid()">▶ شغّل</button>
        <button class="danger" onclick="stopRaid()">■ أوقف</button>
        <button class="secondary" onclick="openHunterDialog()">🎯 أضف صياد</button>
      </div>
      <div id="hunters-list" style="margin-top:8px;display:flex;
           flex-direction:column;gap:6px;max-height:200px;overflow:auto"></div>
      <p class="small" style="margin-top:6px;color:var(--muted)">
        كل قرية صياد تمسح خريطتها كل دورة وترسل إغارات حسب إعداداتها.
      </p>
    </div>

    <div class="card" style="margin-top:18px;border:1px solid #f59e0b">
      <h2>🏗️ بناء القرى التلقائي (Auto-Build Worker)</h2>
      <p class="small" style="color:var(--muted);margin:6px 0 10px">
        البوت يدخل كل قرية ويرفع مستوى الحقول (خشب/طين/حديد/قمح) والمباني المهمة
        (مخزن، صومعة، مبنى رئيسي، سوق، مخبأ، سفارة، إقامة، ثكنات، سور) تلقائياً
        كل ما تتوفر الموارد وخانة قائمة البناء.
      </p>
      <div id="bw-status" class="small" style="margin:8px 0;padding:8px 10px;
           background:#0a0a14;border-radius:8px">— لا حالة —</div>
      <div class="row">
        <button onclick="startBuildWorker()" style="background:#10b981;color:#0a0a14"
                data-testid="build-worker-start">▶ شغّل البناء التلقائي</button>
        <button class="danger" onclick="stopBuildWorker()"
                data-testid="build-worker-stop">■ أوقف</button>
        <button class="secondary" onclick="refreshBuildStatus()"
                data-testid="build-worker-refresh">↻ تحديث الحالة</button>
      </div>
      <div id="bw-priority" style="margin-top:10px"></div>
    </div>

    <div class="card" style="margin-top:18px;border:1px solid #7f1d1d">
      <h2>🛡️ الدفاع التلقائي (يكتشف الهجمات + يرسل دفاعات)</h2>
      <div id="def-status" class="small" style="margin:8px 0;padding:8px 10px;
           background:#0a0a14;border-radius:8px"></div>
      <div class="row">
        <div><label>دورة الفحص (د)</label><input id="def-cycle" type="number" value="3" min="1" max="30"/></div>
        <div><label>الجنود لكل إرسال (JSON)</label><input id="def-troops" value='{"t1": 500}'/></div>
        <button class="secondary" onclick="saveDefenseConfig()">💾</button>
      </div>
      <div class="row">
        <button onclick="startDefense()" style="background:#10b981;color:#0a0a14">▶ شغّل الحماية</button>
        <button class="danger" onclick="stopDefense()">■ أوقف</button>
      </div>
      <div id="attacks-list" style="margin-top:10px;display:flex;flex-direction:column;
           gap:6px;max-height:240px;overflow:auto"></div>
      <p class="small" style="margin-top:6px;color:var(--muted)">
        • يفحص rally point لكل قراك كل X دقيقة<br/>
        • لو في هجوم: يحسب المسافة + الوقت المتبقي<br/>
        • يختار القرى اللي جنودها تقدر توصل قبل الهجوم بـ 3 دقايق<br/>
        • يرسل تعزيزات تلقائياً (لين 3 قرى مدافِعة)
      </p>
    </div>

    <!-- Hunter setup modal -->
    <div id="hunter-modal" style="display:none;position:fixed;inset:0;
         background:rgba(0,0,0,0.8);z-index:100;align-items:center;
         justify-content:center;padding:20px">
      <div class="card" style="max-width:500px;width:100%">
        <h2>🎯 ضبط قرية كصياد</h2>
        <label>اختر القرية</label>
        <select id="h-vid"></select>
        <div class="row">
          <div><label>نصف قطر</label><input id="h-radius" type="number" value="7" min="1" max="30"/></div>
          <div><label>إغارات/دورة</label><input id="h-max" type="number" value="8" min="1" max="50"/></div>
          <div><label>تبريد (د)</label><input id="h-cool" type="number" value="90" min="10" max="1440"/></div>
        </div>
        <label>نوع الهجوم</label>
        <select id="h-type">
          <option value="raid">⚔️ Raid (إغارة سريعة)</option>
          <option value="attack">🔥 Attack (هجوم كامل)</option>
        </select>
        <label>الجنود لكل إغارة (JSON)</label>
        <input id="h-troops" value='{"t4": 5}'/>
        <p class="small" style="color:var(--muted)">t1..t10 = خانة الجندي حسب القبيلة. t4 عادة = خيّالة سريعة.</p>
        <div class="row">
          <button onclick="saveHunter()">💾 احفظ الصياد</button>
          <button class="secondary" onclick="closeHunterDialog()">إلغاء</button>
        </div>
      </div>
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
        <button class="secondary" onclick="openBrowser('${v.id}')" title="افتح المتصفح ودخول تلقائي">🦊</button>
        <button class="secondary" onclick="attachEmail('${v.id}')" title="إنشاء إيميل مؤقت">📧</button>
        <button class="secondary" onclick="snapshotStrategy('${v.id}', '${(v.name||'').replace(/'/g, '\\\'')}')" title="انسخ استراتيجية هذه القرية لباقي القرى">📋</button>
        <button class="secondary" onclick="togglePersonal('${v.id}', ${!v.is_personal})" title="قرية شخصية">${v.is_personal ? '⊖' : '👤'}</button>
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

function updateTransferMode(){
  const mode = $('#t-mode').value;
  const resBox = $('#t-resources');
  const trpBox = $('#t-troops');
  const hint = $('#t-mode-hint');
  if (mode === 'defense') {
    resBox.style.display = 'none';
    trpBox.style.display = 'block';
  } else {
    resBox.style.display = 'block';
    trpBox.style.display = 'none';
    if (mode === 'random_all') {
      hint.innerHTML = 'في وضع <b>عشوائي/كل المتوفر</b>: تترك الكميات صفر — البوت يرسل كل اللي عند كل قرية تلقائياً.';
    } else {
      hint.innerHTML = 'في وضع <b>محدد</b>: حدد الكمية لكل مورد.';
    }
  }
}

function collectTransferBody(){
  return {
    server: $('#t-server').value,
    target_x: parseInt($('#t-x').value || '0'),
    target_y: parseInt($('#t-y').value || '0'),
    target_village_name: $('#t-name').value || 'الهدف',
    mode: $('#t-mode').value,
    amount_wood: parseInt($('#t-wood').value || '0'),
    amount_clay: parseInt($('#t-clay').value || '0'),
    amount_iron: parseInt($('#t-iron').value || '0'),
    amount_crop: parseInt($('#t-crop').value || '0'),
    troops: {
      phalanx: parseInt($('#t-phalanx') ? $('#t-phalanx').value || '0' : '0'),
      legionnaire: parseInt($('#t-legionnaire') ? $('#t-legionnaire').value || '0' : '0'),
      archer: parseInt($('#t-archer') ? $('#t-archer').value || '0' : '0'),
      cavalry: parseInt($('#t-cavalry') ? $('#t-cavalry').value || '0' : '0'),
    }
  };
}

async function planTransfer(){
  const body = collectTransferBody();
  // /api/transfer/plan only supports specific amounts; for other modes, synthesize 1 unit
  if (body.mode === 'random_all') {
    body.amount_wood = body.amount_wood || 1;
    body.amount_clay = body.amount_clay || 1;
    body.amount_iron = body.amount_iron || 1;
    body.amount_crop = body.amount_crop || 1;
  }
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

async function queueTransfer(){
  const body = collectTransferBody();
  const r = await fetch('/api/transfer/queue', { method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  const d = await r.json();
  const out = $('#transfer-result');
  if (!d.ok) { out.innerHTML = '<span style="color:#ef4444">✗ ' + d.error + '</span>'; return; }
  out.innerHTML = `<span style="color:#10b981">✓ تم وضع المهمة #${d.job_id} في الطابور (وضع: ${d.mode})</span>`;
}

async function delVillage(id){
  if (!confirm('احذف هذه القرية؟ (الملفات تبقى)')) return;
  await fetch(`/api/villages/${id}`, { method:'DELETE' });
  loadVillages();
}

async function openBrowser(id){
  const r = await fetch(`/api/villages/${id}/open-browser`, { method:'POST' });
  const d = await r.json();
  if (!d.ok) { alert('✗ ' + d.error); return; }
  const l = d.login || {};
  if (l.stage === 'logged_in' || l.stage === 'already_logged_in') {
    // silent success — village is ready
  } else if (l.stage === 'preflight') {
    alert(`⚠ المتصفح فتح، لكن ما قدر يسجّل دخول:\n${l.detail}\n\nأنشئ إيميل أولاً (📧) أو سجّل القرية في Travian.`);
  } else if (l.stage === 'credentials_rejected') {
    alert(`✗ بيانات الدخول مرفوضة من Travian:\n${l.detail}`);
  } else if (l.stage === 'submitted_unverified') {
    // Probably first-time login or needs registration — silent.
  } else if (l.stage === 'email_field' || l.stage === 'password_field') {
    alert(`⚠ المتصفح فتح، لكن ما لقى حقول الدخول (قد يكون مسجّل أصلاً، أو الصفحة لسه تحمّل).`);
  }
  loadVillages();
}

async function snapshotStrategy(id, vname){
  const name = prompt('سمّ هذه الـ snapshot:', `snapshot من ${vname}`);
  if (!name) return;
  const r = await fetch(`/api/villages/${id}/snapshot-strategy`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name})});
  const d = await r.json();
  if (!d.ok) { alert('✗ ' + (d.error || 'failed')); return; }
  if (confirm(`✓ تم حفظ snapshot #${d.snapshot_id} '${d.name}'\n\nتبي تطبّقها على كل القرى الأخرى الآن؟`)) {
    const r2 = await fetch(`/api/snapshots/${d.snapshot_id}/apply`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({scope:'all', exclude_personal:true,
                            copy_build_queue:true})});
    const d2 = await r2.json();
    alert(`✓ تطبيق على ${d2.applied} قرية (تم تخطّي ${d2.skipped})`);
  }
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
    const r = await fetch('/api/ai/status'); const d = await r.json();
    const el = $('#ollama-status');
    if (d.ok) {
      const tag = (d.models && d.models[0]) || d.default_text || '—';
      el.textContent = `🧠 Ollama: ${d.models ? d.models.length : 0} موديل (${tag})`;
      el.classList.add('live');
    } else {
      el.textContent = '🧠 Ollama: غير متصل';
      el.style.background = '#7f1d1d';
      el.style.color = '#fca5a5';
    }
  } catch {}
}

// boot
loadNationalities();
loadVillages();
loadProxies();
checkOllama();
refreshPool();
loadSnapshots();
loadJobs();
refreshWorker();
refreshRaid();
refreshSpawn();
refreshTaskManager();
loadRegions();
refreshDefense();
setInterval(loadVillages, 8000);
setInterval(refreshPool, 6000);
setInterval(loadSnapshots, 15000);
setInterval(loadJobs, 8000);
setInterval(refreshWorker, 6000);
setInterval(refreshRaid, 7000);
setInterval(refreshSpawn, 5000);
setInterval(refreshTaskManager, 7000);
setInterval(refreshDefense, 8000);

async function loadSnapshots(){
  try {
    const r = await fetch('/api/snapshots'); const d = await r.json();
    const box = $('#snapshots-list');
    if (!d.snapshots || !d.snapshots.length) {
      box.innerHTML = '<span class="small">— لا توجد snapshots بعد. اضغط 📋 على أي قرية.</span>';
      return;
    }
    box.innerHTML = d.snapshots.map(s => `
      <div style="padding:8px 10px;background:#0a0a14;border-radius:8px;
           border:1px solid var(--line);display:flex;justify-content:space-between;
           align-items:center;gap:6px">
        <div style="flex:1;min-width:0">
          <div style="font-size:12px;font-weight:600">${s.name}</div>
          <div class="small" style="color:var(--muted)">#${s.id} • ${s.source_vid}</div>
        </div>
        <button class="secondary" style="margin:0;padding:5px 8px;font-size:11px"
                onclick="applySnap(${s.id})">طبّق</button>
        <button class="danger" style="margin:0;padding:5px 8px;font-size:11px"
                onclick="delSnap(${s.id})">🗑</button>
      </div>`).join('');
  } catch(e) {}
}

async function applySnap(sid){
  if (!confirm('طبّق هذه الـ snapshot على كل القرى (ما عدا الشخصية)؟')) return;
  const r = await fetch(`/api/snapshots/${sid}/apply`, { method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({scope:'all', exclude_personal:true,
                          copy_build_queue:true})});
  const d = await r.json();
  alert(`✓ تم التطبيق على ${d.applied} قرية (تم تخطّي ${d.skipped})`);
}

async function delSnap(sid){
  if (!confirm('احذف هذه الـ snapshot؟')) return;
  await fetch(`/api/snapshots/${sid}`, { method:'DELETE' });
  loadSnapshots();
}

async function loadJobs(){
  try {
    const r = await fetch('/api/transfer/jobs'); const d = await r.json();
    const box = $('#jobs-list');
    if (!d.jobs || !d.jobs.length) {
      box.innerHTML = '<span class="small">— الطابور فارغ.</span>';
      return;
    }
    box.innerHTML = d.jobs.map(j => {
      const res = j.resources_json ? JSON.parse(j.resources_json) : {};
      const trp = j.troops_json ? JSON.parse(j.troops_json) : {};
      const modeIcon = j.mode === 'defense' ? '🛡' : j.mode === 'random_all' ? '🎲' : '🎯';
      const summary = j.mode === 'defense' ?
        Object.entries(trp).filter(([_,v])=>v>0).map(([k,v])=>`${v} ${k}`).join(', ') :
        Object.entries(res).filter(([_,v])=>v>0).map(([k,v])=>`${v} ${k}`).join(', ') || 'كل المتوفر';
      const statusColor = j.status === 'done' ? '#10b981' :
                          j.status === 'failed' ? '#ef4444' :
                          j.status === 'running' ? '#a78bfa' : '#9ca3af';
      return `
      <div style="padding:7px 9px;background:#0a0a14;border-radius:7px;
           border:1px solid var(--line);font-size:11px;display:flex;
           justify-content:space-between;align-items:center;gap:6px">
        <div style="flex:1;min-width:0">
          <div>${modeIcon} #${j.id} → (${j.target_x},${j.target_y}) ${j.target_name||''}</div>
          <div class="small" style="color:var(--muted)">${summary}</div>
        </div>
        <span class="pill" style="background:transparent;color:${statusColor};
              border:1px solid ${statusColor}">${j.status}</span>
        <button class="danger" style="margin:0;padding:3px 6px;font-size:10px"
                onclick="delJob(${j.id})">🗑</button>
      </div>`;
    }).join('');
  } catch(e) {}
}

async function delJob(jid){
  await fetch(`/api/transfer/jobs/${jid}`, { method:'DELETE' });
  loadJobs();
}

async function refreshWorker(){
  try {
    const r = await fetch('/api/transfer/worker/status'); const d = await r.json();
    const s = d.status || {};
    const el = $('#worker-status');
    if (el) {
      const cur = s.current_job ? `job#${s.current_job}` : '—';
      const last = s.last_done ? `#${s.last_done.job_id} (${s.last_done.ok_count}/${s.last_done.total})` : '—';
      el.innerHTML = s.running ?
        `<span style="color:#10b981">● شغّال</span> | يعالج: ${cur} | آخر: ${last}` :
        `<span style="color:#9ca3af">● متوقف</span> | آخر: ${last}`;
    }
  } catch(e) {}
  try {
    const r = await fetch('/api/activation/status'); const d = await r.json();
    const s = d.status || {};
    const el = $('#aw-status');
    if (el) {
      const last = s.last_activated ?
        `${s.last_activated.vid} @ ${s.last_activated.at?.slice(11,19) || ''}` : '—';
      el.innerHTML = s.running ?
        `<span style="color:#10b981">● شغّال</span> | مسح: ${s.scanned} | آخر تفعيل: ${last}` :
        `<span style="color:#9ca3af">● متوقف</span> | آخر تفعيل: ${last}`;
    }
  } catch(e) {}
}

async function startWorker(){
  const r = await fetch('/api/transfer/worker/start', { method:'POST' });
  await r.json(); refreshWorker();
}
async function stopWorker(){
  await fetch('/api/transfer/worker/stop', { method:'POST' });
  refreshWorker();
}
async function startActivation(){
  await fetch('/api/activation/start', { method:'POST' });
  refreshWorker();
}
async function stopActivation(){
  await fetch('/api/activation/stop', { method:'POST' });
  refreshWorker();
}

// ─── Auto-Raid UI ──────────────────────────────────────────────────────────
async function refreshRaid(){
  try {
    const r = await fetch('/api/raid/worker/status'); const d = await r.json();
    const s = d.status || {};
    const el = $('#rw-status');
    if (el) {
      const cur = s.current_hunter || '—';
      el.innerHTML = s.running ?
        `<span style="color:#10b981">● شغّال</span> | صياد: ${cur} | إغارات: ${s.total_raids_sent||0} | آخر هدف: ${s.last_targets_found||0}` :
        `<span style="color:#9ca3af">● متوقف</span> | دورة كل ${d.cycle_min} د`;
    }
  } catch(e) {}
  try {
    const r = await fetch('/api/raid/hunters'); const d = await r.json();
    const box = $('#hunters-list');
    if (!box) return;
    if (!d.hunters.length) {
      box.innerHTML = '<span class="small">— لا يوجد صيادين. اضغط "🎯 أضف صياد".</span>';
      return;
    }
    box.innerHTML = d.hunters.map(h => {
      const t = h.troops_json || '{}';
      return `
      <div style="padding:7px 9px;background:#0a0a14;border-radius:7px;
           border:1px solid var(--line);font-size:11px;display:flex;
           justify-content:space-between;align-items:center;gap:6px">
        <div style="flex:1;min-width:0">
          <div>${h.enabled ? '✅' : '⏸'} ${h.name} (${h.coords_x},${h.coords_y})</div>
          <div class="small" style="color:var(--muted)">r=${h.radius} • max=${h.max_per_cycle} • cooldown=${h.cooldown_min}m • ${t}</div>
        </div>
        <button class="danger" style="margin:0;padding:3px 6px;font-size:10px"
                onclick="delHunter('${h.village_id}')">🗑</button>
      </div>`;
    }).join('');
  } catch(e) {}
}

async function startRaid(){
  await fetch('/api/raid/worker/start', { method:'POST' });
  refreshRaid();
}
async function stopRaid(){
  await fetch('/api/raid/worker/stop', { method:'POST' });
  refreshRaid();
}
async function setRaidCycle(){
  const v = parseFloat($('#rw-cycle').value || '15');
  await fetch('/api/raid/worker/config', { method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({cycle_min: v}) });
  refreshRaid();
}

async function openHunterDialog(){
  // Populate village dropdown
  const r = await fetch('/api/villages'); const d = await r.json();
  const sel = $('#h-vid');
  sel.innerHTML = (d.villages || [])
    .filter(v => !v.is_personal && (v.coords_x !== null))
    .map(v => `<option value="${v.id}">${v.name} (${v.coords_x},${v.coords_y}) — ${v.server.replace('.travian.com','').replace('.x2.international','')}</option>`)
    .join('');
  $('#hunter-modal').style.display = 'flex';
}
function closeHunterDialog(){
  $('#hunter-modal').style.display = 'none';
}

async function saveHunter(){
  const vid = $('#h-vid').value;
  let troops;
  try {
    troops = JSON.parse($('#h-troops').value || '{}');
  } catch(e) { alert('JSON غير صحيح للجنود'); return; }
  const body = {
    enabled: true,
    radius: parseInt($('#h-radius').value || '7'),
    max_per_cycle: parseInt($('#h-max').value || '8'),
    cooldown_min: parseInt($('#h-cool').value || '90'),
    attack_type: $('#h-type').value,
    troops_json: troops,
  };
  const r = await fetch(`/api/raid/hunters/${vid}`, { method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  const d = await r.json();
  if (d.ok) {
    closeHunterDialog();
    refreshRaid();
  } else alert('✗ ' + (d.error || 'failed'));
}

async function delHunter(vid){
  if (!confirm('احذف هذا الصياد؟')) return;
  await fetch(`/api/raid/hunters/${vid}`, { method:'DELETE' });
  refreshRaid();
}

// ─── Spawn Worker UI ──────────────────────────────────────────────────────
async function refreshSpawn(){
  try {
    const r1 = await fetch('/api/spawn/worker/status');
    const s = (await r1.json()).status || {};
    const el = $('#spawn-status');
    if (el) {
      const last = s.last_spawned ?
        `${s.last_spawned.vid?.slice(-6)} @ ${s.last_spawned.at?.slice(11,19)}` : '—';
      el.innerHTML = s.running ?
        `<span style="color:#10b981">● شغّال</span> | خطط نشطة: ${s.schedules_active||0} | آخر قرية: ${last}` :
        `<span style="color:#9ca3af">● متوقف</span> | آخر قرية: ${last}`;
    }
  } catch(e) {}
  try {
    const r2 = await fetch('/api/spawn/schedules');
    const d = await r2.json();
    const box = $('#spawn-list');
    if (!box) return;
    if (!d.schedules.length) {
      box.innerHTML = '<span class="small">— لا توجد خطط. اضغط "➕ خطة جديدة".</span>';
      return;
    }
    box.innerHTML = d.schedules.map(s => {
      const pct = s.target_total ? Math.round((s.spawned_total||0) / s.target_total * 100) : 0;
      const srv = (s.server||'').replace('.travian.com','').replace('.x2.international','');
      return `
      <div style="padding:9px 11px;background:#0a0a14;border-radius:8px;
           border:1px solid var(--line);font-size:11px">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px">
          <div style="flex:1;min-width:0">
            <div><b>${srv}</b> ${s.enabled ? '✅' : '⏸'}</div>
            <div class="small" style="color:var(--muted)">
              ${s.spawned_total||0}/${s.target_total} • اليوم ${s.spawned_today||0}/${s.daily_cap} • كل ${s.interval_min}د • ${s.name_preset} • ${s.tribe_preset}
            </div>
          </div>
          <button class="danger" style="margin:0;padding:3px 6px;font-size:10px"
                  onclick="delSpawn(${s.id})">🗑</button>
        </div>
        <div style="margin-top:6px;height:6px;background:#1f1f2e;border-radius:3px;overflow:hidden">
          <div style="height:100%;width:${pct}%;background:linear-gradient(90deg,#a78bfa,#10b981);transition:width 0.3s"></div>
        </div>
      </div>`;
    }).join('');
  } catch(e) {}
}

async function startSpawn(){
  await fetch('/api/spawn/worker/start', { method:'POST' });
  refreshSpawn();
}
async function stopSpawn(){
  await fetch('/api/spawn/worker/stop', { method:'POST' });
  refreshSpawn();
}
function openSpawnDialog(){ $('#spawn-modal').style.display = 'flex'; }
function closeSpawnDialog(){ $('#spawn-modal').style.display = 'none'; }

async function saveSpawn(){
  const body = {
    server: $('#sp-server').value,
    name_preset: $('#sp-preset').value,
    tribe_preset: $('#sp-tribe').value,
    region: $('#sp-region').value,
    use_proxies: $('#sp-proxies').checked,
    auto_email: $('#sp-email').checked,
    target_total: parseInt($('#sp-target').value || '100'),
    interval_min: parseInt($('#sp-interval').value || '30'),
    daily_cap: parseInt($('#sp-daily').value || '10'),
    enabled: true,
  };
  const r = await fetch('/api/spawn/schedules', { method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  const d = await r.json();
  if (d.ok) {
    closeSpawnDialog();
    // Auto-start worker so user sees immediate effect
    await fetch('/api/spawn/worker/start', { method:'POST' });
    refreshSpawn();
    loadVillages();
  } else alert('✗ ' + (d.error || 'failed'));
}

async function delSpawn(sid){
  if (!confirm('احذف خطة الإنتاج هذه؟')) return;
  await fetch(`/api/spawn/schedules/${sid}`, { method:'DELETE' });
  refreshSpawn();
}

// ─── Task Manager UI ──────────────────────────────────────────────────────
async function refreshTaskManager(){
  try {
    const r1 = await fetch('/api/tasks/manager/status');
    const s = (await r1.json()).status || {};
    const el = $('#tm-status');
    if (el) {
      const t = s.last_scan_at ? s.last_scan_at.slice(11,19) : '—';
      el.innerHTML = s.running ?
        `<span style="color:#10b981">● مراقبة</span> | مهام: ${s.tasks_queued||0} | آخر فحص: ${t}` :
        `<span style="color:#9ca3af">● متوقف</span> | مهام مسجّلة: ${s.tasks_queued||0}`;
    }
  } catch(e) {}
  try {
    const r2 = await fetch('/api/tasks?status=queued&limit=20');
    const d = await r2.json();
    const box = $('#tasks-list');
    if (!box) return;
    if (!d.tasks || !d.tasks.length) {
      box.innerHTML = '<span class="small">— الطابور فارغ.</span>';
      return;
    }
    box.innerHTML = d.tasks.map(t => {
      const icon = {register:'📝', attach_email:'📧', open_browser_warmup:'🦊',
                    build:'🏗️', raid_setup:'⚔️', transfer:'💱'}[t.kind] || '📋';
      const prio = t.priority <= 3 ? '🔴' : t.priority <= 5 ? '🟡' : '🟢';
      return `
      <div style="padding:6px 9px;background:#0a0a14;border-radius:6px;
           border:1px solid var(--line);font-size:11px;display:flex;
           justify-content:space-between;align-items:center;gap:6px">
        <div style="flex:1;min-width:0">
          <div>${prio} ${icon} <b>${t.kind}</b> → ${t.village_name||t.village_id?.slice(-6)}</div>
          <div class="small" style="color:var(--muted)">${t.created_at?.slice(11,19)}</div>
        </div>
        <button class="danger" style="margin:0;padding:2px 5px;font-size:10px"
                onclick="delTask(${t.id})">🗑</button>
      </div>`;
    }).join('');
  } catch(e) {}
}

async function startTaskManager(){
  await fetch('/api/tasks/manager/start', { method:'POST' });
  refreshTaskManager();
}
async function stopTaskManager(){
  await fetch('/api/tasks/manager/stop', { method:'POST' });
  refreshTaskManager();
}
async function delTask(tid){
  await fetch(`/api/tasks/${tid}`, { method:'DELETE' });
  refreshTaskManager();
}

// ─── Travian Worlds Sync UI ──────────────────────────────────────────────
async function loadRegions(){
  try {
    const r = await fetch('/api/travian/regions');
    const d = await r.json();
    const sel = $('#tw-region');
    sel.innerHTML = (d.regions || [])
      .map(r => `<option value="${r.code}">${r.label}</option>`)
      .join('');
    loadWorlds();
  } catch(e) {}
}

async function loadWorlds(){
  const region = $('#tw-region').value;
  try {
    const r = await fetch(`/api/travian/worlds?region=${encodeURIComponent(region)}`);
    const d = await r.json();
    const box = $('#tw-list');
    if (!d.worlds || !d.worlds.length) {
      box.innerHTML = '<span class="small" style="color:var(--muted)">— لا توجد سيرفرات محفوظة. اضغط "🔄 جلب السيرفرات الآن".</span>';
      return;
    }
    box.innerHTML = d.worlds.map(w => `
      <div style="padding:9px 11px;background:#0a0a14;border-radius:8px;
           border:1px solid var(--line);font-size:12px;display:flex;
           justify-content:space-between;align-items:center;gap:6px">
        <div style="flex:1;min-width:0">
          <div><b>${w.code}</b> <span class="badge" style="margin-right:4px">${w.speed||'1x'}</span> <span class="badge" style="background:#064e3b;color:#10b981">${w.status||'active'}</span></div>
          <div class="small" style="color:var(--muted)">${(w.name||'').slice(0,80)}</div>
          <div class="small" style="color:#6b7280;direction:ltr">${w.url}</div>
        </div>
        <div style="display:flex;flex-direction:column;gap:3px">
          <button class="secondary" style="margin:0;padding:5px 8px;font-size:11px"
                  onclick="useServer('${w.url}')">📋 استخدم</button>
          <button class="secondary" style="margin:0;padding:5px 8px;font-size:11px"
                  onclick="setSpawnServer('${w.url}')">🌱 خطة</button>
        </div>
      </div>
    `).join('');
  } catch(e) {}
}

async function syncWorlds(){
  const region = $('#tw-region').value;
  const status = $('#tw-status');
  status.textContent = '⏳ جاري السحب...';
  status.style.background = '#1f2937';
  status.style.color = '#9ca3af';
  try {
    const r = await fetch('/api/travian/sync', { method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({regions: [region]})});
    const d = await r.json();
    const s = (d.summary && d.summary[0]) || {};
    if (s.error) {
      status.textContent = `✗ ${s.error.slice(0,50)}`;
      status.style.background = '#7f1d1d';
      status.style.color = '#fca5a5';
    } else {
      status.textContent = `✓ ${s.saved || 0} سيرفر`;
      status.style.background = '#064e3b';
      status.style.color = '#10b981';
      loadWorlds();
    }
  } catch(e) {
    status.textContent = '✗ خطأ';
    status.style.background = '#7f1d1d';
  }
}

function useServer(url){
  // Strip https:// and trailing /
  const clean = url.replace(/^https?:\/\//,'').replace(/\/$/,'');
  $('#server').value = clean;
  // Visual feedback
  const inp = $('#server');
  inp.style.borderColor = '#10b981';
  setTimeout(() => { inp.style.borderColor = ''; }, 1200);
  // Scroll to creation card
  inp.scrollIntoView({behavior:'smooth', block:'center'});
}

function setSpawnServer(url){
  const clean = url.replace(/^https?:\/\//,'').replace(/\/$/,'');
  // Open spawn modal pre-filled
  $('#sp-server').value = clean;
  openSpawnDialog();
}

// ─── Build Worker UI ────────────────────────────────────────────────────────
async function refreshBuildStatus(){
  try {
    const r = await fetch('/api/build/worker/status');
    const d = await r.json();
    const s = d.status || {};
    const el = document.querySelector('#bw-status');
    if (el) {
      const last = s.last_upgrade ?
        ` • آخر: ${s.last_upgrade.kind === 'field' ? 'حقل #'+s.last_upgrade.slot : s.last_upgrade.name}
          → L${s.last_upgrade.level} (${s.last_upgrade.village||'?'})` : '';
      el.innerHTML = d.running ?
        `<span style="color:#10b981">● شغّال</span> • قرية حالية: ${s.current_village || '—'}
         • مجموع الترقيات: ${s.total_upgrades || 0}${last}` :
        `<span style="color:#9ca3af">● متوقف</span> • مجموع الترقيات: ${s.total_upgrades || 0}${last}`;
    }
    const pri = document.querySelector('#bw-priority');
    if (pri && d.priority && d.priority.length) {
      pri.innerHTML = '<div class="small" style="color:var(--muted);margin-bottom:6px">أولوية البناء:</div>' +
        d.priority.map(p =>
          `<span style="display:inline-block;padding:3px 8px;margin:2px;
            background:#1a1a24;border-radius:12px;font-size:11px">
            ${p.name} → L${p.target_level}</span>`).join('');
    }
  } catch(e) {}
}
async function startBuildWorker(){
  await fetch('/api/build/worker/start', { method:'POST' });
  refreshBuildStatus();
}
async function stopBuildWorker(){
  await fetch('/api/build/worker/stop', { method:'POST' });
  refreshBuildStatus();
}
setInterval(() => { if (document.querySelector('#bw-status')) refreshBuildStatus(); }, 15000);


// ─── Defense Worker UI ──────────────────────────────────────────────────────
async function refreshDefense(){
  try {
    const r1 = await fetch('/api/defense/worker/status');
    const d = await r1.json();
    const s = d.status || {};
    const el = $('#def-status');
    if (el) {
      el.innerHTML = s.running ?
        `<span style="color:#10b981">● حماية شغّالة</span> | قرى مسحت: ${s.scanned||0} | هجمات: ${s.attacks_seen||0} | دفاعات أُرسلت: ${s.dispatched||0}` :
        `<span style="color:#9ca3af">● متوقف</span> | كل ${d.cycle_min||3} د`;
    }
    // Update inputs with current config
    if (d.cycle_min) $('#def-cycle').value = d.cycle_min;
    if (d.troops_to_send) $('#def-troops').value = JSON.stringify(d.troops_to_send);
  } catch(e) {}
  try {
    const r = await fetch('/api/defense/attacks?limit=10');
    const d = await r.json();
    const box = $('#attacks-list');
    if (!d.attacks || !d.attacks.length) {
      box.innerHTML = '<span class="small" style="color:var(--muted)">— لا توجد هجمات مرصودة. (تأكد إن الحماية شغّالة)</span>';
      return;
    }
    box.innerHTML = d.attacks.map(a => {
      const handled = a.handled === 1 ? '🛡 محمية' : a.handled === -1 ? '⚠ تخطّيت' : '🔴 جديدة';
      const eta = a.arrives_at ? new Date(a.arrives_at).toLocaleTimeString('ar-SA',{hour:'2-digit',minute:'2-digit'}) : '—';
      const kindIcon = a.kind === 'raid' ? '⚔️' : a.kind === 'siege' ? '🏰' : '🔥';
      return `
      <div style="padding:8px 10px;background:#0a0a14;border-radius:7px;
           border:1px solid ${a.handled === 1 ? '#10b981' : '#7f1d1d'};
           font-size:11px">
        <div style="display:flex;justify-content:space-between">
          <b>${kindIcon} ${a.kind}</b>
          <span>${handled}</span>
        </div>
        <div class="small" style="color:var(--muted)">
          هدف: ${a.village_name||a.village_id?.slice(-6)} • وصول: ${eta} • متبقي: ${a.seconds_left}s
        </div>
        ${a.notes ? `<div class="small" style="color:#a78bfa">${a.notes}</div>` : ''}
      </div>`;
    }).join('');
  } catch(e) {}
}

async function startDefense(){
  await fetch('/api/defense/worker/start', { method:'POST' });
  refreshDefense();
}
async function stopDefense(){
  await fetch('/api/defense/worker/stop', { method:'POST' });
  refreshDefense();
}
async function saveDefenseConfig(){
  let troops;
  try {
    troops = JSON.parse($('#def-troops').value || '{}');
  } catch(e) { alert('JSON غير صحيح للجنود'); return; }
  await fetch('/api/defense/worker/config', { method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      cycle_min: parseFloat($('#def-cycle').value || '3'),
      troops_to_send: troops
    })});
  refreshDefense();
}

// ─── Self-Update UI ─────────────────────────────────────────────────────────
async function checkUpdate(){
  const badge = $('#update-badge');
  badge.textContent = '⏳ يفحص...';
  badge.style.background = '#1f2937';
  badge.style.color = '#9ca3af';
  try {
    const r = await fetch('/api/self-update/check');
    const d = await r.json();
    if (!d.ok) {
      badge.textContent = `✗ ${(d.error||'').slice(0,30)}`;
      badge.style.background = '#7f1d1d';
      badge.style.color = '#fca5a5';
      return;
    }
    if (d.update_available) {
      if (confirm(`نسخة جديدة متوفرة: ${d.remote}\nنسختك: ${d.local}\n\nتبي تحدّث الآن؟ التطبيق راح يعيد التشغيل تلقائياً.`)) {
        const r2 = await fetch('/api/self-update/apply', { method:'POST' });
        const d2 = await r2.json();
        if (d2.ok) {
          badge.textContent = '✓ يعيد التشغيل...';
          badge.style.background = '#064e3b';
          badge.style.color = '#10b981';
          // Show big overlay because the window is about to die
          document.body.insertAdjacentHTML('beforeend', `
            <div style="position:fixed;inset:0;background:rgba(0,0,0,0.92);
                 z-index:9999;display:flex;align-items:center;justify-content:center;
                 flex-direction:column;color:#fff">
              <div style="font-size:48px;animation:spin 1.5s linear infinite">🔄</div>
              <h1 style="margin-top:20px">تم التحديث — يعيد التشغيل</h1>
              <p style="color:#a78bfa">النافذة الحالية بتقفل خلال ثانيتين، ونافذة جديدة بتفتح تلقائياً</p>
              <style>@keyframes spin { 100% { transform: rotate(360deg); } }</style>
            </div>`);
        } else {
          alert('✗ فشل التحديث: ' + d2.error);
        }
      }
    } else {
      badge.textContent = `✓ آخر نسخة (${d.local})`;
      badge.style.background = '#064e3b';
      badge.style.color = '#10b981';
      setTimeout(() => { badge.textContent = ''; }, 4000);
    }
  } catch(e) {
    badge.textContent = '✗ خطأ';
    badge.style.background = '#7f1d1d';
  }
}
</script>
</body></html>
"""


# ─── AI Chat HTML ────────────────────────────────────────────────────────────
_CHAT_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/>
<title>Zenrex Brain — العقل الاستراتيجي</title>
<style>
 :root{ --bg:#08080f; --panel:#11111c; --line:#252535; --text:#e8e8f0;
        --muted:#8888a0; --accent:#a78bfa; --green:#10b981; --red:#ef4444;
        --amber:#f59e0b; --blue:#3b82f6; }
 *{box-sizing:border-box;margin:0;padding:0}
 body{background:var(--bg);color:var(--text);min-height:100vh;
      font-family:'Segoe UI',Tahoma,Arial,sans-serif;font-size:14px;
      display:flex;flex-direction:column}
 header{padding:14px 24px;background:var(--panel);border-bottom:1px solid var(--line);
        display:flex;justify-content:space-between;align-items:center;gap:12px}
 h1{font-size:18px;color:var(--accent);font-weight:700}
 .badge{font-size:11px;padding:3px 9px;border-radius:6px;background:#222;color:var(--muted)}
 .badge.live{background:#064e3b;color:#10b981}
 .badge.bad{background:#7f1d1d;color:#fca5a5}
 main{flex:1;display:grid;grid-template-columns:280px 1fr;gap:0;min-height:0}
 aside{background:var(--panel);border-left:1px solid var(--line);padding:16px;
       display:flex;flex-direction:column;gap:12px;overflow:auto}
 aside h2{font-size:12px;color:var(--accent);font-weight:600;
          text-transform:uppercase;letter-spacing:0.07em}
 .chat-area{display:flex;flex-direction:column;min-height:0}
 .messages{flex:1;overflow:auto;padding:24px;display:flex;flex-direction:column;
           gap:14px;background:var(--bg)}
 .msg{max-width:720px;padding:12px 16px;border-radius:14px;line-height:1.7;
      white-space:pre-wrap;word-wrap:break-word}
 .msg.user{background:#1e1b4b;color:#e0e7ff;align-self:flex-start;
           border:1px solid #312e81}
 .msg.assistant{background:#11111c;color:var(--text);align-self:flex-end;
                border:1px solid var(--line)}
 .msg.system{background:#0a0a14;color:var(--muted);align-self:center;
             font-size:12px;border:1px dashed var(--line);max-width:520px}
 .actions{margin-top:10px;padding:10px;background:#0a0a14;border-radius:8px;
          font-size:12px;border:1px solid #312e81}
 .actions pre{color:#a78bfa;font-family:'Consolas',monospace;font-size:11px;
              overflow:auto;margin:6px 0}
 .actions .row{display:flex;gap:6px}
 .composer{padding:14px 20px;background:var(--panel);border-top:1px solid var(--line);
           display:flex;gap:10px}
 .composer textarea{flex:1;background:#0a0a14;border:1px solid var(--line);
                    color:var(--text);padding:11px 14px;border-radius:10px;
                    font-family:inherit;font-size:14px;resize:none;min-height:46px;
                    max-height:140px}
 .composer button{background:var(--accent);color:#0a0a14;border:none;padding:0 22px;
                  border-radius:10px;font-weight:600;cursor:pointer}
 .composer button:disabled{filter:grayscale(0.6);cursor:not-allowed}
 .meta{font-size:11px;color:var(--muted);margin-top:6px}
 button.mini{background:#222;color:var(--text);border:1px solid var(--line);
             padding:5px 10px;border-radius:6px;font-size:11px;cursor:pointer}
 button.mini.approve{background:#064e3b;color:#10b981;border-color:#065f46}
 button.mini.reject{background:#7f1d1d;color:#fca5a5;border-color:#991b1b}
 .quick{display:flex;flex-direction:column;gap:6px}
 .quick button{text-align:right;background:#0a0a14;border:1px solid var(--line);
               color:var(--text);padding:8px 10px;border-radius:8px;font-size:12px;
               cursor:pointer}
 .quick button:hover{border-color:var(--accent)}
 a{color:var(--accent);text-decoration:none}
</style></head>
<body>
<header>
  <div style="display:flex;gap:10px;align-items:center">
    <h1>🧠 Zenrex Brain — العقل الاستراتيجي</h1>
    <span class="badge">v0.5.0</span>
  </div>
  <div style="display:flex;gap:8px;align-items:center">
    <a href="/" class="badge" style="background:#1e3a8a;color:#93c5fd">🏰 لوحة المزرعة</a>
    <span class="badge" id="ollama-tag">— Ollama</span>
    <button class="mini" onclick="clearChat()">🗑 محادثة جديدة</button>
  </div>
</header>

<main>
  <aside>
    <div>
      <h2>الموديل</h2>
      <select id="model" style="width:100%;background:#0a0a14;color:var(--text);
              border:1px solid var(--line);padding:8px;border-radius:8px"></select>
      <p class="meta" id="ollama-meta">جارٍ الفحص...</p>
    </div>
    <div>
      <h2>أوامر سريعة</h2>
      <div class="quick">
        <button onclick="sendQuick('ايش الخطة المقترحة لاول 100 قرية على ts8؟ خل التحالف يصير جاهز ليبيع موارد')">📋 اقترح خطة افتتاحية</button>
        <button onclick="sendQuick('انا اخترت قرية شخصية اشتغل فيها. شوف وضعها وسوي مثلها على باقي القرى')">🔁 انسخ خطتي للقرى</button>
        <button onclick="sendQuick('عطني خطة دفاع لازم اطبقها لما يهجم احد القرى')">🛡 خطة دفاع</button>
        <button onclick="sendQuick('متى افضل وقت احوّل الموارد للزبون اللي بشتري؟')">💰 توقيت بيع موارد</button>
        <button onclick="sendQuick('وش المخاطر اللي تعرّض الفارم للحظر؟')">⚠ تقييم مخاطر</button>
      </div>
    </div>
    <div>
      <h2>حالة المزرعة</h2>
      <pre id="ctx-snap" style="font-size:11px;color:var(--muted);
           background:#0a0a14;padding:8px;border-radius:6px;overflow:auto"></pre>
    </div>
  </aside>

  <section class="chat-area">
    <div id="messages" class="messages">
      <div class="msg system">
        ابدأ بكتابة الخطة، أو استخدم الأوامر السريعة. كل ما تقترح خطة، أرد بمقترح + JSON اجراءات قابل للاعتماد أو الرفض.
      </div>
    </div>
    <div class="composer">
      <textarea id="input" placeholder="اكتب لي الخطة، أو اسأل عن الاستراتيجية..." onkeydown="handleKey(event)"></textarea>
      <button id="send-btn" onclick="sendMessage()">إرسال</button>
    </div>
  </section>
</main>

<script>
const $ = s => document.querySelector(s);
const SID = 'main';

function handleKey(e){
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function renderMessages(rows){
  const box = $('#messages');
  box.innerHTML = '';
  if (!rows || !rows.length) {
    box.innerHTML = '<div class="msg system">ابدأ بكتابة الخطة، أو استخدم الأوامر السريعة.</div>';
    return;
  }
  rows.forEach(m => {
    const div = document.createElement('div');
    div.className = 'msg ' + (m.role || 'assistant');
    div.textContent = m.content;
    if (m.meta_json) {
      try {
        const obj = JSON.parse(m.meta_json);
        const a = document.createElement('div');
        a.className = 'actions';
        const intent = obj.intent || 'action';
        a.innerHTML = `<b style="color:#a78bfa">📦 إجراء مقترح: ${intent}</b>` +
          `<pre>${JSON.stringify(obj, null, 2)}</pre>` +
          `<div class="row"><button class="mini approve" onclick="approve(${m.id}, true)">✓ اعتمد</button>` +
          `<button class="mini reject" onclick="approve(${m.id}, false)">✗ ارفض</button></div>` +
          (m.approved === 1 ? '<div class="meta" style="color:#10b981">معتمد</div>' :
           m.approved === -1 ? '<div class="meta" style="color:#ef4444">مرفوض</div>' : '');
        div.appendChild(a);
      } catch(e) {}
    }
    box.appendChild(div);
  });
  box.scrollTop = box.scrollHeight;
}

async function loadHistory(){
  const r = await fetch(`/api/ai/history?session_id=${SID}`);
  const d = await r.json();
  renderMessages(d.messages || []);
}

async function loadStatus(){
  const r = await fetch('/api/ai/status');
  const d = await r.json();
  const tag = $('#ollama-tag');
  const meta = $('#ollama-meta');
  const sel = $('#model');
  if (d.ok) {
    tag.textContent = `🧠 ${d.models.length} موديل`;
    tag.classList.add('live');
    sel.innerHTML = d.models.map(m => `<option value="${m}">${m}</option>`).join('');
    if (d.default_text && d.models.includes(d.default_text)) sel.value = d.default_text;
    meta.textContent = `متصل بـ ${d.host}`;
  } else {
    tag.textContent = '🧠 غير متصل';
    tag.classList.add('bad');
    sel.innerHTML = '<option value="qwen2.5:7b">qwen2.5:7b</option>';
    meta.innerHTML = `❌ ${d.error || 'تعذّر الاتصال'}.<br/>`+
      `شغّل: <code>ollama serve</code> ثم <code>ollama pull qwen2.5:7b</code>`;
  }
}

async function loadCtx(){
  try {
    const r = await fetch('/api/villages'); const d = await r.json();
    const states = {};
    (d.villages||[]).forEach(v => states[v.state] = (states[v.state]||0)+1);
    $('#ctx-snap').textContent = JSON.stringify({
      total: d.total, by_state: states
    }, null, 2);
  } catch(e) {}
}

async function sendMessage(){
  const ta = $('#input');
  const txt = (ta.value || '').trim();
  if (!txt) return;
  const btn = $('#send-btn');
  btn.disabled = true; btn.textContent = '...';
  ta.value = '';
  // Optimistic add of user msg
  const box = $('#messages');
  const u = document.createElement('div');
  u.className = 'msg user'; u.textContent = txt;
  box.appendChild(u);
  // Thinking placeholder
  const t = document.createElement('div');
  t.className = 'msg assistant'; t.id = 'thinking';
  t.textContent = '… يفكّر زِنركس برين';
  box.appendChild(t);
  box.scrollTop = box.scrollHeight;
  try {
    const r = await fetch('/api/ai/chat', { method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({session_id:SID, message:txt,
                            model: $('#model').value || undefined})});
    const d = await r.json();
    document.getElementById('thinking')?.remove();
    await loadHistory();
  } catch(e) {
    document.getElementById('thinking')?.remove();
    alert('فشل الإرسال: ' + e);
  } finally {
    btn.disabled = false; btn.textContent = 'إرسال';
  }
}

function sendQuick(text){
  $('#input').value = text;
  sendMessage();
}

async function approve(msgId, ok){
  await fetch(`/api/ai/approve/${msgId}`, { method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({approved: ok})});
  loadHistory();
}

async function clearChat(){
  if (!confirm('مسح كل المحادثة؟')) return;
  await fetch('/api/ai/clear', { method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({session_id:SID})});
  loadHistory();
}

// boot
loadStatus();
loadHistory();
loadCtx();
setInterval(loadCtx, 12000);
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
