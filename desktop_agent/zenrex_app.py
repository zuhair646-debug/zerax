"""
Zenrex Farm — Desktop App launcher
═══════════════════════════════════
يشغّل سيرفر FastAPI في الخلفية ويفتح نافذة Native (بدون terminal أسود).
يحط أيقونة في System Tray للسيطرة (open / quit / version).

تشغيل: pythonw zenrex_app.py
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
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
    uvicorn.run(zenrex_farm.app, host="127.0.0.1", port=PORT,
                log_level="warning", access_log=False)


def _wait_for_server(timeout: float = 15.0) -> bool:
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


def _open_with_webview() -> bool:
    """Open a native window via pywebview. Returns True if successful."""
    try:
        import webview  # type: ignore
    except ImportError:
        return False
    try:
        webview.create_window(
            APP_TITLE,
            f"http://127.0.0.1:{PORT}/",
            width=1500,
            height=920,
            min_size=(1100, 700),
            text_select=True,
        )
        webview.start()
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

    # Build a simple purple "Z" icon — replaced by real Travian icon by installer
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
        os._exit(0)  # hard-exit; server thread is daemon

    menu = pystray.Menu(
        pystray.MenuItem("افتح في المتصفح", _open_clicked, default=True),
        pystray.MenuItem(f"الإصدار  v{zenrex_farm.APP_VERSION}",
                         lambda *_: None, enabled=False),
        pystray.MenuItem("خروج", _quit_clicked),
    )
    icon = pystray.Icon("zenrex", img, APP_TITLE, menu)
    icon.run()


def main() -> None:
    # Start server in background daemon thread
    t = threading.Thread(target=_server_thread, daemon=True)
    t.start()
    if not _wait_for_server(timeout=20.0):
        # Fall back to browser even if health check failed
        pass
    # Try native window
    opened = _open_with_webview()
    if opened:
        # webview.start() blocked until window closed → safe to exit
        return
    # No pywebview → fallback to system browser + tray
    _open_in_browser()
    # Tray keeps the process alive. If pystray isn't installed, fall back
    # to a simple block-on-stdin/sleep loop so the server keeps running.
    try:
        import pystray  # noqa: F401
        _start_tray()
    except ImportError:
        # Block forever — server is in daemon thread, this keeps main alive
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
