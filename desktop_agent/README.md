# Zenrex Desktop Agent 🤖

**Full native control of your Mac / Windows / Linux by the Zenrex AI.**

Unlike a Chrome Extension (browser-only), this agent lets the AI **see your whole screen** and control your **mouse + keyboard + downloads + apps** — exactly like a colleague sharing their desktop with you.

---

## 🚀 Quick start

### Mac / Linux
```bash
./install.sh   # one-time setup
./run.sh       # starts the agent and asks for the pairing code
```

### Windows
```
install.bat    # one-time setup
run.bat        # starts the agent and asks for the pairing code
```

> **Get the pairing code first**: in any Zenrex chat say **"اربط جهازي للتحكم الكامل"** and the AI will return a 6-character code.

---

## 🔒 Safety

| | |
|---|---|
| 🛑 **FAILSAFE** | Slam your mouse to the **top-left corner** of the screen → any AI-driven action is instantly aborted. |
| 🔌 **Stop anytime** | `Ctrl+C` in the terminal |
| 🚫 **Shell disabled by default** | Add `--allow-shell` (or edit run.sh / run.bat) only if you trust the AI to run terminal commands. |
| 🔐 **Encrypted** | All commands travel over `wss://` (TLS) |
| ⏱️ **Pairing expires** | Codes are valid for 10 minutes only |

---

## 🛠 What the AI can do

| Action | Description |
|---|---|
| `screenshot` | Capture your primary screen as JPEG |
| `move_mouse(x,y)` | Move cursor |
| `click / double_click / right_click` | Click at coordinates |
| `type(text)` | Type text (supports Arabic via clipboard fallback) |
| `press_key(key)` | Press combo, e.g. `cmd+space`, `enter`, `ctrl+c` |
| `scroll(amount)` | + up, − down |
| `download_file(url, filename?)` | Save URL → `~/Downloads/` |
| `open_app(name)` | Open a native app (VS Code, Safari, …) |
| `open_url(url)` | Open URL in default browser |
| `list_dir(path)` | List a folder |
| `read_file(path)` | Read a text/binary file (limited bytes) |
| `write_file(path, content)` | Save text to a file |
| `make_dir(path)` | Create a folder |
| `run_shell(command)` | Terminal command (needs `--allow-shell`) |

---

## 🆘 Troubleshooting

**macOS** – the script can't move the mouse?
1. System Settings → Privacy & Security → **Accessibility** → enable Terminal.
2. Same panel → **Screen Recording** → enable Terminal.
3. Restart the agent.

**Windows** – pip errors?
- Re-install Python and tick **“Add Python to PATH”**.

**Linux** – `pyautogui` complains about Xlib?
```
sudo apt install python3-tk python3-dev scrot
```

---

Source is open in `/app/desktop_agent/`. No telemetry. No keylogger. Stop the script and you're disconnected — the AI loses all access.
