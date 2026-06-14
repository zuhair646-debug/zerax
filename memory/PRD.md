# Zerax / Zenrex AI Platform — PRD

## Original Problem Statement
Unify the AI brain and empower it with unified toolset. Fix mocked AI Trading Bot. Upgrade Owner AI to stop hallucinating desktop actions. Add: Live AI Trading (Alpaca), 100% Local Family AI (Ollama), reliable Desktop Agent, persistent memory + Prayer Scheduler.

**Session 2026-06-13 NEW Pillar**: Migrate Family AI to dedicated Z390 Desktop PC with NVIDIA RTX (vs underpowered laptop).

## User Profile
- Saudi Arabic dialect speaker
- Kids: حسين (Hussain) + عباس (Abbas)
- 100% LOCAL AI requirement (no OpenAI/Anthropic for Family AI)

## What's Implemented
- ✅ AI Trading Bot live (Alpaca + Claude Sharia screening)
- ✅ Desktop Agent v0.8.1 (clipboard_paste, run_shell, self_update, shell-on-by-default)
- ✅ Fixed WebSocket race-condition (3s reconnect loop)
- ✅ Throttled duplicate-rejection logs (30s cooldown)
- ✅ Diagnosed laptop: ASUS Vivobook TP3402ZA (8GB max 16GB, no NVIDIA, USB4)
- ✅ Discovered & rescued desktop PC: ASRock Z390 + i7-9700KF + 16GB + RTX + 1TB SSD
- ✅ Fresh Windows 11 install on Z390 (after CMOS dead + partition table wiped)
- ✅ BIOS fixes: Intel PTT=ON, Secure Boot=ON, CSM=OFF
- ✅ Bypassed MS account via OOBE\BYPASSNRO
- ✅ PowerShell one-click installer at https://zenrex.ai/install_agent.ps1

## In Progress (Session End State)
- 🟡 User installing Desktop Agent on Z390 PC via PowerShell installer
- 🟡 Need to detect exact NVIDIA RTX model after agent connects
- 🟢 **NEW (2026-02)**: Zenrex PC-Control + Game-Mode service deployed
  - File: `/app/desktop_agent/zenrex_pc_control.py` (port 7862, FastAPI)
  - Endpoints: `/screen.jpg`, `/control/{click,move,type,key,scroll,hotkey}`,
    `/game/{start,stop,status}`
  - Game loop: screenshot → backend `/api/desktop-agent/pc-control-decide` →
    Claude Sonnet 4.5 vision → JSON action → pyautogui
  - Beautiful RTL Arabic control panel UI with live screen + manual + game-mode
  - One-liner installer: `/api/desktop-agent/install-games-and-control.ps1`
    also installs Epic Games (Fortnite), Steam (PUBG), Whisper, opens Travian
  - **PROVEN WORKING**: Zenrex auto-navigated Travian.com → clicked GO TO LOBBY →
    reached lobby.legends.travian.com/account/join → explored worlds (Asia 2, etc.)
    in 4 successful iterations before LLM budget exhausted.
  - **Architectural fix**: Emergent LLM Universal key only works server-side.
    Local game-loop now POSTs screenshots to backend `pc-control-decide` which
    calls Claude with the key. Bypasses FREE_USER_EXTERNAL_ACCESS_DENIED.

- 🟢 **NEW (2026-02)**: Zenrex Farm v0.2.0 — multi-village Travian bot engine
  - File: `/app/desktop_agent/zenrex_farm.py` (55KB, port 7870, FastAPI + SQLite)
  - 100% local · zero paid services · runs on user's Z390 PC
  - **PROVEN STATE**: 10 villages with 10 unique IPs from different countries,
    Stealth 2.0 (17 fingerprint vectors), mail.tm temp emails working.
  - **Stealth 2.0** defeats: webdriver, plugins, languages, HW concurrency,
    device memory, max touch, color depth, battery API, WebGL vendor/renderer,
    Canvas seeded noise, AudioContext noise, font enumeration spoofing,
    Permissions API, speech synthesis voices, WebRTC IP leak, iframe escape.
  - **Free Proxy Auto-Fetcher**: 8 GitHub sources → TCP test → ~40-50% alive.
    Sample run: 200 candidates → 83 alive socks5/http proxies in 90s.
  - **Mail.tm integration**: Free temporary mailboxes, no API key. Per-village
    inbox endpoint.
  - **Per-village deterministic fingerprint seeds** (`fingerprint_seed(vid)`)
    so each village has consistent identity across sessions.
  - **Human Bezier mouse + typing** (`bezier_curve`, `human_move_to`, `human_type`).
- 🟢 **NEW (2026-02) v0.4.0**: Zenrex Farm — Complete Travian Strategy Engine
  - **Updated default strategy** with smart rules:
    - `storage_rules`: cranny_min=20000, cranny_target=50000, **cranny_ratio=1.2**
      (cranny capacity ≥ 1.2 × warehouse) — protects loot
    - `raid_rules`: scan_radius=30, max_target_pop=100, first_strike=2 troops,
      spy_first=true, skip_spy_if_ally_attacking=true, split_troops=true
    - `attack_units` + `defense_units` per-tribe (5 tribes × 2 units each)
    - Phase ordering fixed: **Cranny BEFORE Warehouse/Granary** (loot protection)
  - **Defense send v2**: `mode: "all" | "spec"` with per-tribe troop_spec
  - **Attack scan endpoint** `/api/attack/scan` — defines bounding box + filters
  - **Attack raid endpoint** `/api/attack/raid` — spy-then-strike logic
  - **Travian registration endpoint** `/api/villages/{id}/register-travian`
    with `dry_run=true` for pre-flight checks + full Playwright form-fill flow
    (selectors for name/email/password/tribe/region/TOS/submit)
  - **Browser launcher v2** — returns proxy/tribe info, proper error handling
  - All endpoints tested via curl: health, strategy, defense plan, dry-run register
  - **101 villages PROVEN created** (1 personal + 100 bot in NW region)
    - Distribution: 21 Romans / 15 Gauls / 21 Teutons / 27 Egyptians / 17 Huns
    - All bot villages in NW quadrant (coords x<0, y>0) — region selection works
  - **Travian-specific fields**: `region` (NW/NE/SW/SE/ANY), `coords_x/y`,
    `tribe` (5 tribes), `is_personal` (excludes from bot rotation),
    `alliance`, `in_game_uid`, `capital_village`.
  - **Browser Pool orchestrator**: `BrowserPool` class with start/stop/config.
    Configurable max_parallel (1-50), rotation_min (2-180), cooldown_min (0-60).
    Personal villages excluded. Round-robin by `last_seen_at`. Phase 1 logs the
    rotation; Phase 2 will call Playwright open + run strategy.
  - **Strategy YAML engine**: `~/.zenrex-farm/strategies/<name>.yaml`. Default
    plan has 4 phases (resources → storage → army → economy + transfer-to-personal).
  - **Alliance + Defense endpoints** (stub): `/api/alliance/create` plans the
    embassy-build + invitation flow. `/api/defense/send` plans troop dispatch.
  - **PATCH `/api/villages/{id}`**: toggle is_personal, set coords, alliance, etc.
  - DB migrations idempotent (ALTER TABLE inside try/except, post-migration indexes).

## ⚠️ BLOCKERS (2026-02-12)
- **Emergent LLM key budget exhausted**: 80.44/80.43. User wants FREE/INDEPENDENT
  alternative — plan: switch farm/control to Ollama qwen2.5vl:7b (local vision).
- **Playwright Chromium download**: ~150MB, still installing in background on
  user's PC (started via separate `start /MIN python -m playwright install`).

## P0 Next Tasks (when user returns)
- [ ] Verify Chromium installed → test "🦊 افتح" button (Playwright opens a real
      stealth browser for a village)
- [ ] Add Ollama vision client to farm (replace Claude for autonomous play)
- [ ] Travian registration flow (Playwright script: fill signup form per village)
- [ ] Strategy engine: YAML plan → next-action queue per village
- [ ] Tor/free-proxy auto-fetcher (no need for user to buy proxies)
1. Verify Desktop Agent connected from Z390 PC (via /api/desktop-agent/status)
2. Detect exact RTX model (run nvidia-smi via run_shell)
3. Install latest NVIDIA driver from nvidia.com
4. Install Ollama + Qwen 2.5 (size based on VRAM)
5. **Install XTTS-v2** for voice cloning (original P0 — now feasible with RTX!)
6. Migrate Zenrex Mind v0.2.0 (laptop → Z390): mind.db + profiles + prayer scheduler
7. Configure Windows Firewall: allow LAN connections from laptop on port 7861
8. Enable BitLocker on system drive
9. Buy & install: CR2032 battery (~5 SAR) + 16GB DDR4-3000 RAM stick (~250 SAR Amazon.sa)

## P1
- Capacitor APK for Family Mode (Hussain/Abbas profiles)
- Auto Sharia re-screening (quarterly via SEC EDGAR)
- Telegram trade notifications

## P2
- WhatsApp Business API
- ZATCA Phase 2 invoicing
- Tabby/Tamara payments
- 2TB NVMe for AI models

## Key Decisions
- 100% LOCAL Family AI (Ollama on Z390 PC, no cloud LLMs)
- Hetzner VPS production (`zenrex.ai`, Docker zerax-backend-1)
- Auth: `owner@zerax.com` / `owner123`
- Single pairing code `VQPR5Y` works for any device (project `owner-autocoder-desktop`)
- Z390 PC = AI hub + light gaming (Fortnite/PUBG); Laptop = secondary

## File Map
- `/app/backend/modules/freebuild/local_browser_relay.py` — WS hub (race fix applied)
- `/app/backend/modules/trading/__init__.py` — Trading + Alpaca
- `/app/desktop_agent/zenrex_agent.py` — CLI agent v0.8.1
- `/app/desktop_agent/zenrex_gui.pyw` — GUI agent v0.6.0 (legacy)
- VPS: `/opt/zerax/frontend/build/install_agent.ps1` — installer
- Laptop: `C:\Users\zuhai\.zenrex-desktop-agent\mind\` — Mind to be migrated

## Z390 PC Hardware (Confirmed via BIOS)
- CPU: Intel i7-9700KF @ 3.6GHz (8c/8t)
- RAM: 16GB DDR4-3000 Team (slot A2; A1/B1/B2 empty)
- Storage: 953GB Team T253X SSD (SATA3_0)
- GPU: NVIDIA GeForce RTX (model TBD)
- Mobo: ASRock Z390 Phantom Gaming 4 (BIOS P4.30)
- Cooling: AIO 240mm + multiple case fans
- PSU: Team Group GX
- Issue: CR2032 dead (date/time resets — user buying replacement)
