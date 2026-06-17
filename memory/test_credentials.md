# Test Credentials

## Owner/Admin — Production (zenrex.ai)
- **Email:** `admin@zenrex.ai`
- **Password:** `owner123`
- **Role:** owner

## Owner/Admin — Preview (preview.emergentagent.com)
- **Email:** `owner@zerax.com`
- **Password:** `owner123`
- **Role:** owner

## Zenrex Kids PWA (https://zenrex.ai/kids)
- **Parent (ولي الأمر)** — `zoheer@zenrex.ai` / `Zenrex@2026` → routes to Parent Dashboard with kid records
- **Child 1 (حسين)** — `hussain@kids.local` / `1234` → routes to restricted child feed (Home + Prayer only)
- **Child 2 (عباس)** — `abbas@kids.local` / `5678` → same child view

**Note:** The two environments have different MongoDBs and different seeded users.
- For preview testing: use `owner@zerax.com`
- For production verification: use `admin@zenrex.ai`

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
