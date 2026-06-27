"""
Execution backends — runtime layer for the Concierge.

  - webcontainer_executor: browser Node.js (WASM, free)
  - pyodide_executor: browser Python (WASM, free)
  - eas_build: Expo cloud-built APK/IPA
  - liveblocks_integrator: real-time SDK injection
  - e2b_executor: cloud VM sandbox (paid per-second)
  - ssh_executor: connect to user's own VPS

All execute REMOTELY (browser, cloud, or user VPS) — never in our container.
"""
