/**
 * StorageIndicator — small pill + click-to-toggle popover (no full-screen modal).
 * Shows storage usage; if over the limit, surfaces upgrade options that link to /pricing.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { HardDrive, AlertTriangle, X } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function StorageIndicator({ compact = false }) {
  const [usage, setUsage] = useState(null);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  const load = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
      const r = await fetch(`${API}/api/freebuild-chat/storage/usage`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) {
        const d = await r.json();
        setUsage(d);
      }
    } catch (_) { /* silent */ }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [load]);

  // Close on outside-click
  useEffect(() => {
    if (!open) return;
    const onClick = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  if (!usage) return null;

  const pct = Math.min(usage.used_pct || 0, 100);
  const color =
    usage.needs_upgrade ? 'red' :
    pct >= 70 ? 'amber' : 'emerald';
  const colorMap = {
    emerald: { ring: 'border-emerald-400/40', dot: 'bg-emerald-400', text: 'text-emerald-300', bar: 'bg-emerald-400' },
    amber:   { ring: 'border-amber-400/40',   dot: 'bg-amber-400',   text: 'text-amber-300',   bar: 'bg-amber-400' },
    red:     { ring: 'border-red-500/50',     dot: 'bg-red-500 animate-pulse', text: 'text-red-300', bar: 'bg-red-500' },
  };
  const c = colorMap[color];

  return (
    <div ref={wrapRef} className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        data-testid="storage-indicator"
        className={`inline-flex items-center gap-2 px-2.5 py-1.5 rounded-full border ${c.ring} bg-black/30 hover:bg-black/50 transition`}
        title={`${usage.used_mb} MB / ${usage.quota_mb} MB`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
        <HardDrive className={`w-3.5 h-3.5 ${c.text}`} />
        {!compact && (
          <span className={`text-[11px] font-bold ${c.text}`}>
            {usage.used_mb < 1
              ? `${Math.round(usage.used_mb * 1024)} KB`
              : `${usage.used_mb.toFixed(1)} MB`}
            <span className="opacity-60"> / {usage.quota_mb >= 1024 ? `${(usage.quota_mb/1024).toFixed(0)} GB` : `${usage.quota_mb} MB`}</span>
          </span>
        )}
        {usage.needs_upgrade && (
          <span className="text-[10px] font-black bg-red-500 text-white px-1.5 py-0.5 rounded-full">ترقية</span>
        )}
      </button>

      {/* Small popover anchored under the pill */}
      {open && (
        <div
          data-testid="storage-upgrade-popover"
          className="absolute z-[70] mt-2 left-0 sm:left-auto sm:right-0 w-[min(20rem,calc(100vw-1.5rem))] sm:w-96 rounded-xl border border-amber-500/40 bg-zinc-900 shadow-2xl p-4"
          role="dialog"
        >
          <div className="flex items-start justify-between mb-3">
            <div>
              <div className="flex items-center gap-1.5 mb-0.5">
                <HardDrive className="w-4 h-4 text-amber-300" />
                <h3 className="text-sm font-black text-amber-200">سعة التخزين</h3>
              </div>
              <p className="text-[10px] text-zinc-400">باقتك: <span className="text-amber-300 font-bold">{usage.tier_label}</span></p>
            </div>
            <button type="button" onClick={() => setOpen(false)} className="text-zinc-400 hover:text-white p-0.5" aria-label="إغلاق">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Usage bar */}
          <div className="space-y-2 mb-3">
            <div className="flex justify-between text-[10px]">
              <span className="text-zinc-400">المستخدم</span>
              <span className={c.text}>
                {usage.used_mb.toFixed(2)} MB / {usage.quota_mb >= 1024 ? `${(usage.quota_mb/1024).toFixed(0)} GB` : `${usage.quota_mb} MB`}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
              <div className={`h-full ${c.bar} transition-all`} style={{ width: `${pct}%` }} />
            </div>
          </div>

          {usage.needs_upgrade && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-2 flex items-start gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              <p className="text-[11px] text-red-100/90">تجاوزت الحد — رقّي باقتك لمواصلة إنشاء المشاريع.</p>
            </div>
          )}

          <a
            href="/pricing"
            data-testid="storage-upgrade-cta"
            className="block text-center px-3 py-2 rounded-lg bg-gradient-to-r from-amber-400 to-yellow-500 hover:opacity-90 text-black text-xs font-black"
          >
            عرض الباقات والنقاط
          </a>
        </div>
      )}
    </div>
  );
}
