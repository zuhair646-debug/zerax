"""Videos module — generation, upload, history.

Migration status: 🟡 SKELETON ONLY (server.py still owns the live routes)
Pending migration from server.py:
  • POST /api/generate/video        (line 934 in server.py)
  • POST /api/videos/upload         (line 1014 in server.py)
  • GET  /api/generate/videos/history (line 1036 in server.py)

Why not yet migrated: these endpoints depend tightly on server.py-private
helpers (check_user_subscription, log_user_activity, RUNWAY/Sora SDK init).
The migration plan is to first extract those helpers into shared util modules,
then move the routes here.
"""
