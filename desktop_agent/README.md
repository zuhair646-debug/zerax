# Zenrex Desktop Agent

**Full remote control of your Mac / Windows / Linux by the Zenrex AI.**

Unlike the Chrome Extension (which controls only browser tabs), the Desktop Agent
lets the AI see your **whole screen** and control your **mouse + keyboard +
downloads + apps** — exactly like sitting next to you.

## Installation

```bash
# 1. Install Python 3.10+ if you don't have it.
#    Mac:    brew install python3
#    Win:    https://www.python.org/downloads/
#    Linux:  sudo apt install python3-pip python3-tk

# 2. Install dependencies
pip install -r requirements.txt

# 3. macOS only: grant Accessibility + Screen Recording permission to your Terminal
#    System Settings → Privacy & Security → Accessibility / Screen Recording
#    → enable Terminal (or iTerm)
```

## Pair with Zenrex

1. In any Zenrex chat, ask the AI: **"اربط جهازي للتحكم الكامل"**
2. The AI returns a 6-character code (e.g. `MQBQFB`).
3. Run the agent with that code:

```bash
python zenrex_agent.py --code MQBQFB
```

4. The terminal will show `✅ Connected.` — you're paired.

5. Now ask the AI things like:
   - `"نزّل ملف هذا الـ ZIP في مجلد Downloads عندي"`
   - `"افتح VS Code وأنشئ ملف جديد"`
   - `"خذ سكرين شوت للشاشة كاملة"`
   - `"اكتب لي تغريدة في تويتر"` (يفتح Chrome ويكتب)

## Safety

- 🛑 **FAILSAFE**: Move your mouse to the **top-left corner** of the screen to instantly abort whatever the AI is doing.
- 🔒 **Shell disabled by default.** Add `--allow-shell` only if you trust the AI to run terminal commands.
- 🔌 Stop the agent anytime with **Ctrl+C** in the terminal.

## What the AI can do

| Action | Description |
|---|---|
| `screenshot` | Capture full primary screen as JPEG |
| `move_mouse(x, y)` | Move cursor |
| `click(x, y, button, clicks)` | Click at coordinates |
| `type(text)` | Type text at cursor |
| `press_key(key)` | Press key/combo, e.g. `cmd+space`, `enter`, `cmd+c` |
| `scroll(amount)` | Scroll up (+) or down (-) |
| `download_file(url, filename)` | Download URL → `~/Downloads/` |
| `open_app(name)` | Open native app |
| `run_shell(command)` | Run terminal command (needs `--allow-shell`) |

## Privacy

- All commands and screenshots travel encrypted over WebSocket (`wss://`)
- Pairing codes expire in 10 minutes
- One agent connection per project
- No keylogger, no telemetry — source is open at `/app/desktop_agent/`
