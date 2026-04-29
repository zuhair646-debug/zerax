"""Games module — owns game engine static assets, templates, and (future) game generation routes.

Migration status: 🟡 IN PROGRESS
Currently owned:
  • GET /api/game-engine.js     — serves the runtime game engine
  • GET /api/game-test          — internal QA page
  • GET /api/iframe-test        — iframe sandbox test
  • GET /api/image-backed-test  — image-backed game test

Pending migration from server.py:
  • Admin training game-template ingestion (~line 2625-2880)
  • Design-to-game converter (line 2978+)
"""
