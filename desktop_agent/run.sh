#!/usr/bin/env bash
# Zenrex Desktop Agent — runner for Mac & Linux.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Virtual environment missing. Run ./install.sh first."
    exit 1
fi

exec ./.venv/bin/python zenrex_agent.py "$@"
