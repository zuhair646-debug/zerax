# Zenrex Assistant — Chrome Extension

Lets the **Zenrex AI** control your local Chrome browser. The AI works on your real, already-signed-in tabs (Gmail, your dashboards, social media) and you watch every action happen live on your screen.

## Installation (Beta — manual)

1. Download the `chrome_extension/` folder (or clone this repo).
2. Open `chrome://extensions/` in Chrome.
3. Enable **Developer mode** (top right).
4. Click **Load unpacked** and select the `chrome_extension/` folder.
5. The Zenrex icon will appear in your toolbar.

## Pairing

1. Go to any Zenrex chat (`/freebuild/chat`) and ask the AI to control your laptop.
2. The AI will call `local_browser_pair()` and return a 6-character code.
3. Click the Zenrex extension icon → paste the code → press **ربط الإضافة**.
4. Done — the extension shows `✅ متصل` and the AI can now drive your browser.

## What the AI can do (via `local_browser_act`)

| Action | What it does |
|---|---|
| `navigate(url)` | Replace the active tab with a new URL |
| `open_tab(url)` | Open a new tab |
| `list_tabs()` | List all your tabs |
| `get_url()` | Read the current URL/title |
| `screenshot()` | Capture the visible viewport (JPEG base64) |
| `click(selector)` | Click an element (CSS selector OR `text="..."`) |
| `type(selector, text)` | Type into an input |
| `scroll(y)` | Scroll the page |
| `eval(code)` | Evaluate a JS expression in page context (read-only) |

## Privacy & Safety

- **Sessions stay on your laptop** — the AI never sees your cookies or passwords. It only sees the rendered screen.
- **You can disconnect anytime** — click the extension → `إلغاء الربط`.
- **No destructive actions without confirmation** — the AI's system prompt forbids it.
- **One pairing per project** — connecting a new project disconnects the old one.

## How it works

```
User's Chrome  ──WS──►  zenrex.ai/api/local-browser/ws
       ▲                        │
       │                        ▼
       │              AI's local_browser_act tool
       │                        │
       └────WS commands ────────┘
```

The extension keeps a persistent WebSocket to Zenrex. The AI sends JSON commands `{ action, params }` and the extension executes them on your active tab via `chrome.scripting.executeScript`.
