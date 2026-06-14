"""
Zenrex Farm - Desktop App launcher (v0.8.1)
═══════════════════════════════════════════════
- Hides the console window
- Starts FastAPI server in a daemon thread
- Opens a Native window via pywebview (Edge WebView2 on Windows)
- Falls back to system browser + tray if pywebview unavailable
- HARD EXIT on window close (X button works correctly)
- Auto-restart support: /api/self-update/apply re-spawns this launcher

Run: pythonw zenrex_app.py
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
import signal
from pathlib import Path

# Hide console window on Windows immediately
try:
    if os.name == "nt":
        import ctypes
        _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if _hwnd:
            ctypes.windll.user32.ShowWindow(_hwnd, 0)
except Exception:
    pass


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import zenrex_farm  # noqa: E402

APP_TITLE = f"Zenrex Farm — مزرعة قرى Travian (v{zenrex_farm.APP_VERSION})"
PORT = zenrex_farm.PORT


def _server_thread() -> None:
    """Run the FastAPI server in this process (background thread)."""
    import uvicorn
    zenrex_farm.init_db()
    config = uvicorn.Config(zenrex_farm.app, host="127.0.0.1", port=PORT,
                            log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    # Mark server as known to outer scope so we can ask it to stop
    globals()["_UVICORN"] = server
    server.run()


def _wait_for_server(timeout: float = 20.0) -> bool:
    """Block until the local server responds on /health."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health",
                                        timeout=1.5):
                return True
        except Exception:
            time.sleep(0.3)
    return False


def _hard_exit(code: int = 0) -> None:
    """Kill the entire process. Use this when the user wants to quit so we
    don't get stuck on stuck threads, pending Playwright cleanups, etc."""
    try:
        srv = globals().get("_UVICORN")
        if srv is not None:
            srv.should_exit = True
    except Exception:
        pass
    # Give the server a tiny moment to flush, then force exit
    try:
        time.sleep(0.2)
    except Exception:
        pass
    # On Windows, os._exit bypasses atexit / threads / open browsers
    try:
        os._exit(code)
    except Exception:
        sys.exit(code)


def _open_with_webview() -> bool:
    """Open a native window via pywebview. Returns True if successful.
    Critically: forces a HARD exit when the window is closed so the X button
    actually terminates everything (otherwise daemon threads, Playwright
    subprocesses, and uvicorn can keep the process alive)."""
    try:
        import webview  # type: ignore
    except ImportError:
        return False
    try:
        window = webview.create_window(
            APP_TITLE,
            f"http://127.0.0.1:{PORT}/",
            width=1500,
            height=920,
            min_size=(1100, 700),
            text_select=True,
        )

        def _on_closed():
            # Fires when the user clicks the X / OS closes the window
            _hard_exit(0)

        # pywebview API varies by version; attach safely
        try:
            window.events.closed += _on_closed
        except Exception:
            try:
                window.closed += _on_closed
            except Exception:
                pass

        webview.start()
        # If webview.start returned for any reason → exit anyway
        _hard_exit(0)
        return True
    except Exception as e:
        try:
            import logging
            logging.warning(f"pywebview failed: {e}")
        except Exception:
            pass
        return False


def _open_in_browser() -> None:
    """Fallback: open the dashboard in the default browser."""
    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
    except Exception:
        pass


def _start_tray() -> None:
    """Optional system-tray icon. Best-effort; ignored if pystray missing."""
    try:
        import pystray  # type: ignore
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError:
        return
    icon_path = HERE / "zenrex_icon.png"
    if icon_path.exists():
        img = Image.open(str(icon_path))
    else:
        img = Image.new("RGBA", (64, 64), (167, 139, 250, 255))
        d = ImageDraw.Draw(img)
        d.rectangle([8, 8, 56, 56], outline=(255, 255, 255, 255), width=3)
        d.text((22, 22), "Z", fill=(255, 255, 255, 255))

    def _open_clicked(_icon, _item):
        _open_in_browser()

    def _quit_clicked(icon, _item):
        icon.stop()
        _hard_exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("افتح في المتصفح", _open_clicked, default=True),
        pystray.MenuItem(f"الإصدار  v{zenrex_farm.APP_VERSION}",
                         lambda *_: None, enabled=False),
        pystray.MenuItem("خروج", _quit_clicked),
    )
    icon = pystray.Icon("zenrex", img, APP_TITLE, menu)
    icon.run()


def _install_signal_handlers() -> None:
    """Make Ctrl+C / kill cleanly hard-exit the app."""
    def _handler(_sig, _frame):
        _hard_exit(0)
    try:
        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)
    except Exception:
        pass


def main() -> None:
    _install_signal_handlers()
    t = threading.Thread(target=_server_thread, daemon=True)
    t.start()
    _wait_for_server(timeout=25.0)
    opened = _open_with_webview()
    if opened:
        # _open_with_webview already calls _hard_exit on close
        return
    _open_in_browser()
    try:
        import pystray  # noqa: F401
        _start_tray()
    except ImportError:
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            _hard_exit(0)


if __name__ == "__main__":
    main()
