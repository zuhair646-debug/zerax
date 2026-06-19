/**
 * UsageIndicator — small pill that shows the user how much AI budget
 * they've consumed today + what's left + an inline "ترقية" CTA when
 * they're close to the limit.
 *
 * Polls /api/usage/me every 30s. Updates instantly if `triggerRefresh`
 * prop changes (e.g. after a chat completion).
 *
 * Color logic mirrors StorageIndicator:
 *   < 60% used  → 🟢 emerald
 *   60-85%      → 🟡 amber
 *   > 85%       → 🔴 red
 *   blocked     → 🔴 + "ترقية" pulse
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Zap, AlertCircle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function UsageIndicator({ compact = false, refreshKey = 0 }) {
  const [usage, setUsage] = useState(null);

  const load = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
      const r = await fetch(`${API}/api/usage/me`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) setUsage(await r.json());
    } catch (_) { /* silent */ }
  }, []);

  useEffect(() => { load(); }, [load, refreshKey]);
  useEffect(() => { const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);

  if (!usage) return null;
  // Admin / owner — quota.reason === 'admin' means unlimited.
  if (usage.quota?.reason === 'admin') return null;

  const used = (usage.today.tokens_in || 0) + (usage.today.tokens_out || 0);
  const cap = usage.quota?.cap || 50000;
  const pct = Math.min((used / cap) * 100, 100);
  const blocked = !usage.quota?.allowed;
  const cost = usage.today.cost_usd || 0;

  let color = 'emerald';
  if (blocked || pct >= 100) color = 'red';
  else if (pct >= 85) color = 'amber-strong';
  else if (pct >= 60) color = 'amber';

  const styles = {
    emerald:       { border: 'border-emerald-500/40', text: 'text-emerald-300', bar: 'bg-emerald-400', dot: 'bg-emerald-400' },
    amber:         { border: 'border-amber-500/40',   text: 'text-amber-300',   bar: 'bg-amber-400',   dot: 'bg-amber-400' },
    'amber-strong':{ border: 'border-amber-500/60',   text: 'text-amber-200',   bar: 'bg-amber-500',   dot: 'bg-amber-400 animate-pulse' },
    red:           { border: 'border-red-500/60',     text: 'text-red-300',     bar: 'bg-red-500',     dot: 'bg-red-500 animate-pulse' },
  };
  const s = styles[color];

  return (
    <a
      href="/pricing/v2"
      data-testid="usage-indicator"
      title={`استخدمت ${used.toLocaleString()} من ${cap.toLocaleString()} رمز اليوم — تكلفة: $${cost.toFixed(3)}`}
      className={`inline-flex items-center gap-2 px-2.5 py-1.5 rounded-full border ${s.border} bg-black/30 hover:bg-black/50 transition relative overflow-hidden`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {blocked ? (
        <>
          <AlertCircle className={`w-3.5 h-3.5 ${s.text}`} />
          <span className={`text-[11px] font-black ${s.text}`}>محجوب · ترقّي</span>
        </>
      ) : (
        <>
          <Zap className={`w-3.5 h-3.5 ${s.text}`} />
          {!compact && (
            <span className={`text-[11px] font-bold ${s.text} tabular-nums`}>
              {Math.round(pct)}%
              <span className="opacity-60 mx-1">·</span>
              ${cost.toFixed(2)}
            </span>
          )}
        </>
      )}
      {/* subtle progress bar at the bottom */}
      {!blocked && !compact && (
        <span
          className={`absolute bottom-0 right-0 h-0.5 ${s.bar} transition-all`}
          style={{ width: `${pct}%` }}
        />
      )}
    </a>
  );
}
