#!/usr/bin/env bash
# Zenrex Desktop Agent — installer for Mac & Linux.
set -e

cd "$(dirname "$0")"

echo "═══════════════════════════════════════════════════════════"
echo "  🤖 Zenrex Desktop Agent — Installer"
echo "═══════════════════════════════════════════════════════════"

# 1. Check Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 not found."
    echo "   Mac:    brew install python3"
    echo "   Linux:  sudo apt install python3 python3-pip python3-tk"
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "✓ Python ${PY_VER} found"

# 2. Create virtualenv (so we don't pollute system python)
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment in .venv ..."
    python3 -m venv .venv
fi

# 3. Install deps
echo "→ Installing Python dependencies ..."
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "   1. In your Zenrex chat ask: \"اربط جهازي\" — you'll get a 6-char code."
echo "   2. Run: ./run.sh"
echo "   3. Paste the code when prompted."
echo ""
echo "macOS users: System Settings → Privacy → Accessibility / Screen Recording"
echo "             → enable Terminal (or whichever app runs this script)."
echo ""
