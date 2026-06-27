"""
🧩 State Management Cortex — picks the right state management strategy.

For React/Next.js projects:
  - useState (simple component state)
  - useReducer (complex local state)
  - Zustand (global client state)
  - React Query / TanStack Query (server state)
  - Jotai (atomic state)
  - Context API (theme/auth global)

Generates ready-to-paste snippets based on the use case.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.state_cortex")


def recommend_state_strategy(use_case: str) -> Dict[str, Any]:
    """Pick the best state lib for a use case description."""
    uc = (use_case or "").lower()
    if any(k in uc for k in ["server data", "fetch api", "cache requests", "بيانات سيرفر"]):
        return {"choice": "tanstack-query", "ar_label": "TanStack Query (server state)", "reason": "أفضل لـ server-state caching + revalidation"}
    if any(k in uc for k in ["global", "shared between routes", "auth state", "user", "theme"]):
        return {"choice": "zustand", "ar_label": "Zustand (global client state)", "reason": "خفيف، بدون boilerplate، يعمل خارج React"}
    if any(k in uc for k in ["atomic", "fine-grained"]):
        return {"choice": "jotai", "ar_label": "Jotai (atomic state)", "reason": "مرن للحقول المنفصلة"}
    if any(k in uc for k in ["form", "wizard", "multi-step"]):
        return {"choice": "use-reducer", "ar_label": "useReducer (form/wizard local)", "reason": "كافي للحالة المحلية المعقدة"}
    return {"choice": "use-state", "ar_label": "useState (simple)", "reason": "كافي لحالة بسيطة"}


def zustand_store_snippet(store_name: str, state_keys: List[str]) -> str:
    """Generate a Zustand store skeleton."""
    sname = store_name.replace(" ", "")
    setters = []
    initial = []
    for k in state_keys:
        initial.append(f"  {k}: null")
        setters.append(f"  set{k.capitalize()}: (v: any) => set({{ {k}: v }})")
    return f"""import {{ create }} from 'zustand';

interface {sname}State {{
{chr(10).join(f"  {k}: any;" for k in state_keys)}
{chr(10).join(f"  set{k.capitalize()}: (v: any) => void;" for k in state_keys)}
}}

export const use{sname} = create<{sname}State>((set) => ({{
{','.join(chr(10) + line for line in initial)},
{','.join(chr(10) + line for line in setters)}
}}));
"""


def react_query_snippet(endpoint: str, key: str) -> str:
    """Generate a React Query hook for an endpoint."""
    return f"""import {{ useQuery, useMutation, useQueryClient }} from '@tanstack/react-query';

export function use{key.capitalize()}() {{
  return useQuery({{
    queryKey: ['{key}'],
    queryFn: async () => {{
      const r = await fetch('{endpoint}');
      if (!r.ok) throw new Error('fetch failed');
      return r.json();
    }},
  }});
}}

export function useUpdate{key.capitalize()}() {{
  const qc = useQueryClient();
  return useMutation({{
    mutationFn: async (data: any) => {{
      const r = await fetch('{endpoint}', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(data),
      }});
      if (!r.ok) throw new Error('mutate failed');
      return r.json();
    }},
    onSuccess: () => qc.invalidateQueries({{ queryKey: ['{key}'] }}),
  }});
}}
"""
