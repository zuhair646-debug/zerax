# Test Credentials

## Owner/Admin (Production: zenrex.ai)
- Email: `owner@zerax.com`
- Password: `owner123`

## Desktop Agent Pairing
- Project ID: `owner-autocoder-desktop`
- Pairing Code: `VQPR5Y`
- WS endpoint: `wss://zenrex.ai/api/desktop-agent/ws?code=VQPR5Y`
- Status endpoint: `https://zenrex.ai/api/desktop-agent/status`

## SSH (Hetzner VPS)
- Host: `zenrex.ai`
- User: `root`
- Key: `~/.ssh/zerax_key`

## Alpaca Trading API
- Stored in `/app/backend/.env` (paper trading)

## Emergent LLM Key
- Stored as `EMERGENT_LLM_KEY` in `/app/backend/.env`

## Desktop Agent Installer (Windows)
- One-click PowerShell:
  ```
  iwr -useb https://zenrex.ai/install_agent.ps1 | iex
  ```
- Agent source: `https://zenrex.ai/api/desktop-agent/agent-source`
