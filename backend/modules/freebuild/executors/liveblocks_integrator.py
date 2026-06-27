"""
👥 Liveblocks Cortex — generates ready-to-paste Liveblocks integration code.

Provides:
  - React/Next.js provider setup
  - Auth endpoint (FastAPI/Node)
  - Pre-built components: LiveCursors, LivePresence, LiveComments
  - Room ID generation strategy

Requires: LIVEBLOCKS_SECRET_KEY from vault.
"""
from __future__ import annotations


def auth_endpoint_fastapi() -> str:
    """Generate the auth endpoint code (FastAPI) that issues Liveblocks tokens."""
    return '''import os
import httpx
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api/liveblocks")
LIVEBLOCKS_SECRET = os.environ["LIVEBLOCKS_SECRET_KEY"]


@router.post("/auth")
async def liveblocks_auth(payload: dict):
    """Issue a Liveblocks token for the current user.
    Frontend calls this with {room: "room-id"}."""
    user_id = payload.get("user_id") or "anonymous"
    room = payload.get("room") or "default"
    async with httpx.AsyncClient(timeout=15) as cl:
        r = await cl.post(
            "https://api.liveblocks.io/v2/authorize-user",
            headers={"Authorization": f"Bearer {LIVEBLOCKS_SECRET}", "Content-Type": "application/json"},
            json={
                "userId": user_id,
                "userInfo": payload.get("user_info") or {},
                "permissions": {room: ["room:write"]},
            },
        )
    if r.status_code != 200:
        raise HTTPException(401, "auth failed")
    return r.json()
'''


def react_provider_snippet() -> str:
    return '''// app/LiveblocksProvider.tsx
'use client';
import { LiveblocksProvider, RoomProvider } from '@liveblocks/react';

export function Live({ roomId, children }: { roomId: string; children: React.ReactNode }) {
  return (
    <LiveblocksProvider
      authEndpoint={async () => {
        const r = await fetch('/api/liveblocks/auth', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ room: roomId, user_id: 'user-' + Math.random().toString(36).slice(2,8) }),
        });
        return await r.json();
      }}
    >
      <RoomProvider id={roomId} initialPresence={{ cursor: null }}>
        {children}
      </RoomProvider>
    </LiveblocksProvider>
  );
}
'''


def live_cursors_component() -> str:
    return '''// components/LiveCursors.tsx
'use client';
import { useOthers, useMyPresence } from '@liveblocks/react';

export function LiveCursors() {
  const others = useOthers();
  const [, updateMyPresence] = useMyPresence();

  return (
    <div
      onPointerMove={(e) => updateMyPresence({ cursor: { x: e.clientX, y: e.clientY } })}
      onPointerLeave={() => updateMyPresence({ cursor: null })}
      style={{ position: 'fixed', inset: 0, pointerEvents: 'auto' }}
    >
      {others.map(({ connectionId, presence }) => {
        if (!presence.cursor) return null;
        const colors = ['#ff006e', '#00f5ff', '#fbbf24', '#a78bfa', '#10b981'];
        const color = colors[connectionId % colors.length];
        return (
          <svg
            key={connectionId}
            style={{ position: 'fixed', left: presence.cursor.x, top: presence.cursor.y, transition: 'left 50ms, top 50ms', pointerEvents: 'none' }}
            width="24" height="36" viewBox="0 0 24 36"
          >
            <path d="M0 0 L0 24 L7 17 L11 26 L14 25 L10 16 L20 16 Z" fill={color} />
          </svg>
        );
      })}
    </div>
  );
}
'''


def live_presence_component() -> str:
    return '''// components/LivePresence.tsx
'use client';
import { useOthers, useSelf } from '@liveblocks/react';

export function LivePresence() {
  const self = useSelf();
  const others = useOthers();
  const all = [self, ...others].filter(Boolean);
  return (
    <div style={{ display:'flex', gap:'-8px' }}>
      {all.map((u, i) => (
        <div key={i} style={{
          width: 32, height: 32, borderRadius: '50%',
          background: '#3b82f6', color:'white',
          display:'flex', alignItems:'center', justifyContent:'center',
          border: '2px solid white', marginLeft: -8,
        }}>
          {(u?.info?.name || 'U').charAt(0)}
        </div>
      ))}
    </div>
  );
}
'''


def package_json_deps() -> dict:
    return {
        "@liveblocks/client": "^2.0.0",
        "@liveblocks/react": "^2.0.0",
        "@liveblocks/node": "^2.0.0",
    }


def render_full_integration_files() -> dict:
    """Return all files needed for Liveblocks integration."""
    return {
        "backend/liveblocks_auth.py": auth_endpoint_fastapi(),
        "app/LiveblocksProvider.tsx": react_provider_snippet(),
        "components/LiveCursors.tsx": live_cursors_component(),
        "components/LivePresence.tsx": live_presence_component(),
    }
