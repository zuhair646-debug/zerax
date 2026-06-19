/**
 * StorageIndicator — small pill that surfaces a user's storage quota.
 * Polls /api/freebuild-chat/storage/usage every 60s. Shows:
 *   - 🟢 plenty of room      (< 70%)
 *   - 🟡 nearing the limit   (70-90%)
 *   - 🔴 over the limit      (>= 100%) — clicking opens upgrade dialog
 */
import React, { useState, useEffect, useCallback } from 'react';
import { HardDrive, AlertTriangle, Sparkles, X } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function StorageIndicator({ compact = false }) {
  const [usage, setUsage] = useState(null);
  const [showUpgrade, setShowUpgrade] = useState(false);

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
    <>
      <button
        type="button"
        onClick={() => setShowUpgrade(true)}
        data-testid="storage-indicator"
        className={`inline-flex items-center gap-2 px-2.5 py-1.5 rounded-full border ${c.ring} bg-black/30 hover:bg-black/50 transition`}
        title={`${usage.used_mb} MB / ${usage.quota_mb} MB — ${usage.project_count} مشروع من أصل ${usage.quota_projects}`}
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

      {showUpgrade && (
        <div
          className="fixed inset-0 z-[80] bg-black/85 backdrop-blur-md flex items-center justify-center p-4"
          onClick={() => setShowUpgrade(false)}
          data-testid="storage-upgrade-modal"
        >
          <div
            className="bg-zinc-900 border border-amber-500/40 rounded-2xl max-w-lg w-full p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <HardDrive className="w-5 h-5 text-amber-300" />
                  <h3 className="text-lg font-black text-amber-200">سعة التخزين</h3>
                </div>
                <p className="text-xs text-zinc-400">باقتك الحالية: <span className="text-amber-300 font-bold">{usage.tier_label}</span></p>
              </div>
              <button type="button" onClick={() => setShowUpgrade(false)} className="text-zinc-400 hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Usage bars */}
            <div className="space-y-3 mb-5">
              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span className="text-zinc-400">المساحة المستخدمة</span>
                  <span className={c.text}>
                    {usage.used_mb.toFixed(2)} MB / {usage.quota_mb >= 1024 ? `${(usage.quota_mb/1024).toFixed(0)} GB` : `${usage.quota_mb} MB`}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-zinc-800 overflow-hidden">
                  <div className={`h-full ${c.bar} transition-all`} style={{ width: `${pct}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span className="text-zinc-400">عدد المشاريع</span>
                  <span className={c.text}>{usage.project_count} / {usage.quota_projects >= 999 ? '∞' : usage.quota_projects}</span>
                </div>
                <div className="h-2 rounded-full bg-zinc-800 overflow-hidden">
                  <div
                    className={`h-full ${c.bar} transition-all`}
                    style={{ width: `${Math.min((usage.project_count / Math.max(1, usage.quota_projects)) * 100, 100)}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Upgrade options */}
            {usage.next_tier_label ? (
              <div className="space-y-3">
                {usage.needs_upgrade && (
                  <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-3 flex items-start gap-2.5">
                    <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-bold text-red-200">تجاوزت الحد المسموح</p>
                      <p className="text-xs text-red-100/80 mt-0.5">
                        ما راح تقدر تنشئ مشاريع جديدة لحد ما تحذف أو ترقّي باقتك.
                      </p>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="rounded-xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-teal-500/5 p-4">
                    <div className="text-[10px] uppercase tracking-wider text-emerald-400 font-black mb-1">Pro</div>
                    <div className="text-2xl font-black text-emerald-200">$9<span className="text-xs text-zinc-400 font-normal"> / شهر</span></div>
                    <ul className="text-[11px] text-zinc-300 mt-2 space-y-1">
                      <li>✓ 20 مشروع</li>
                      <li>✓ 5 GB تخزين</li>
                      <li>✓ Visual Guardian</li>
                    </ul>
                    <a
                      href="/pricing"
                      data-testid="storage-upgrade-pro"
                      className="block text-center mt-3 px-3 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-black"
                    >
                      ترقّي لـ Pro
                    </a>
                  </div>
                  <div className="rounded-xl border border-amber-500/40 bg-gradient-to-br from-amber-500/15 to-yellow-500/5 p-4">
                    <div className="text-[10px] uppercase tracking-wider text-amber-400 font-black mb-1 flex items-center gap-1">
                      <Sparkles className="w-3 h-3" /> Studio
                    </div>
                    <div className="text-2xl font-black text-amber-200">$29<span className="text-xs text-zinc-400 font-normal"> / شهر</span></div>
                    <ul className="text-[11px] text-zinc-300 mt-2 space-y-1">
                      <li>✓ مشاريع غير محدودة</li>
                      <li>✓ 50 GB تخزين</li>
                      <li>✓ كل ميزات Pro + دعم أولوية</li>
                    </ul>
                    <a
                      href="/pricing"
                      data-testid="storage-upgrade-studio"
                      className="block text-center mt-3 px-3 py-2 rounded-lg bg-amber-400 hover:bg-amber-300 text-black text-xs font-black"
                    >
                      ترقّي لـ Studio
                    </a>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-center text-xs text-zinc-500">أنت في أعلى باقة — استمتع 🎉</p>
            )}
          </div>
        </div>
      )}
    </>
  );
}
