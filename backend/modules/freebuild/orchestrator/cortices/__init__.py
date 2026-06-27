"""Cortices package — domain-specialized streaming functions.

Each cortex exports `stream_<name>_cortex(...)` with a uniform signature so
the Orchestrator can call them interchangeably.

All cortices receive the same kwargs:
  project, user_message, history, ctx_holder, user_language, auth_token, db,
  is_owner, max_iterations, inject_workflow_addendum, shared_assets (optional)

And yield SSE-formatted chunks.
"""
