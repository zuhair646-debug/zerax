/**
 * StorageIndicator — small pill + click-to-toggle popover.
 *
 * Unified storage display: shows actual MB/GB used vs subscribed quota.
 * Surfaces subscription health (active/past_due/archived) and routes to
 * /billing/storage for plan management.
 *
 * Visual rules:
 *  - 0–69% used  → emerald
 *  - 70–94%      → amber
 *  - 95%+        → red
 *  - past_due    → amber + grace countdown
 *  - archived    → red + recovery CTA
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { HardDrive, AlertTriangle, X, Clock, Archive } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Pretty-print MB/GB
const fmtSize = (mb) => {
  if (mb == null) return '0 MB';
  if (mb < 1) return `${Math.round(mb * 1024)} KB`;
  if (mb < 1024) return `${mb.toFixed(mb < 10 ? 2 : 1)} MB`;
  return `${(mb / 1024).toFixed(mb >= 10240 ? 0 : 1)} GB`;
};

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
  const isArchived = usage.archived;
  const isPastDue = usage.subscription_status === 'past_due';

  // Color logic — purely based on storage % + subscription health
  let color;
  if (isArchived || pct >= 95) color = 'red';
  else if (isPastDue || pct >= 70) color = 'amber';
  else color = 'emerald';

  const colorMap = {
    emerald: { ring: 'border-emerald-400/40', dot: 'bg-emerald-400', text: 'text-emerald-300', bar: 'bg-emerald-400' },
    amber:   { ring: 'border-amber-400/40',   dot: 'bg-amber-400',   text: 'text-amber-300',   bar: 'bg-amber-400' },
    red:     { ring: 'border-red-500/50',     dot: 'bg-red-500 animate-pulse', text: 'text-red-300', bar: 'bg-red-500' },
  };
  const c = colorMap[color];

  // Build a context-specific warning message instead of the old generic "تجاوزت الحد"
  let warningTitle = null;
  let warningBody = null;
  let warningIcon = AlertTriangle;
  if (isArchived) {
    warningTitle = 'تم أرشفة ملفاتك';
    warningBody = 'انتهت فترة السماح. ملفاتك محفوظة لدينا — استردها بدفع رسم الاسترداد + تجديد الاشتراك.';
    warningIcon = Archive;
  } else if (isPastDue) {
    const days = usage.grace_days_left;
    warningTitle = days != null ? `متبقي ${days} أيام قبل الأرشفة` : 'فشل تجديد الاشتراك';
    warningBody = 'جدّد اشتراكك الآن لتفادي أرشفة ملفاتك. سنرسل لك تذكيرات على بريدك.';
    warningIcon = Clock;
  } else if (pct >= 95) {
    warningTitle = 'تخزينك على وشك الامتلاء';
    warningBody = `استخدمت ${pct.toFixed(0)}% من ${fmtSize(usage.quota_mb)}. رقّ خطتك قبل امتلاء المساحة.`;
  } else if (pct >= 70) {
    warningTitle = `تخزين ${pct.toFixed(0)}% مستخدم`;
    warningBody = 'لا توجد مشكلة الآن، لكن فكّر بالترقية إذا كنت ستضيف ملفات كبيرة.';
  }
  const showWarning = !!warningTitle;
  const WarnIcon = warningIcon;

  return (
    <div ref={wrapRef} className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        data-testid="storage-indicator"
        className={`inline-flex items-center gap-2 px-2.5 py-1.5 rounded-full border ${c.ring} bg-black/30 hover:bg-black/50 transition`}
        title={`${fmtSize(usage.used_mb)} / ${fmtSize(usage.quota_mb)}`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
        <HardDrive className={`w-3.5 h-3.5 ${c.text}`} />
        {/* Storage text is ALWAYS shown — even in compact (mobile) mode —
            so the user sees how much room they have at a glance without
            having to tap. The remaining MB is the source of truth. */}
        <span className={`text-[10px] sm:text-[11px] font-bold ${c.text} whitespace-nowrap`}>
          {fmtSize(usage.used_mb)}
          <span className="opacity-60"> / {fmtSize(usage.quota_mb)}</span>
        </span>
        {(isArchived || isPastDue) && (
          <span className="text-[10px] font-black bg-red-500 text-white px-1.5 py-0.5 rounded-full">
            {isArchived ? 'مؤرشف' : 'تجديد'}
          </span>
        )}
      </button>

      {/* Popover rendered via React PORTAL into document.body so it escapes
          any parent stacking context (backdrop-blur in the navbar etc.)
          which was previously clipping the fixed-positioned overlay. */}
      {open && createPortal(
        <>
          <div
            className="fixed inset-0 z-[9998]"
            style={{ backgroundColor: '#09090b' }}
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div
            data-testid="storage-upgrade-popover"
            className="fixed z-[9999] left-1/2 -translate-x-1/2 top-[72px] sm:top-[80px] w-[calc(100vw-1rem)] sm:w-[26rem] max-w-[26rem] rounded-2xl border-2 border-amber-400 shadow-2xl shadow-amber-500/40 p-5 animate-in fade-in slide-in-from-top-3 duration-200"
            style={{ backgroundColor: '#1a1a1d' }}
            role="dialog"
            onClick={(e) => e.stopPropagation()}
          >
          <div className="flex items-start justify-between mb-3">
            <div>
              <div className="flex items-center gap-1.5 mb-0.5">
                <HardDrive className="w-4 h-4 text-amber-300" />
                <h3 className="text-sm font-black text-amber-200">سعة التخزين</h3>
              </div>
              <p className="text-[10px] text-zinc-400">
                باقتك: <span className="text-amber-300 font-bold">{usage.tier_label}</span>
                {usage.project_count > 0 && (
                  <span className="opacity-70"> · {usage.project_count} مشروع</span>
                )}
              </p>
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
                {fmtSize(usage.used_mb)} / {fmtSize(usage.quota_mb)} <span className="opacity-60">({pct.toFixed(1)}%)</span>
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
              <div className={`h-full ${c.bar} transition-all`} style={{ width: `${pct}%` }} />
            </div>
          </div>

          {/* Context-aware warning */}
          {showWarning && (
            <div className={`rounded-lg border p-2.5 flex items-start gap-2 mb-3 ${
              color === 'red'
                ? 'border-red-500/40 bg-red-500/10'
                : 'border-amber-500/40 bg-amber-500/10'
            }`}>
              <WarnIcon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${color === 'red' ? 'text-red-400' : 'text-amber-400'}`} />
              <div className="text-[11px] leading-relaxed">
                <p className={`font-bold mb-0.5 ${color === 'red' ? 'text-red-100' : 'text-amber-100'}`}>{warningTitle}</p>
                <p className={color === 'red' ? 'text-red-100/80' : 'text-amber-100/80'}>{warningBody}</p>
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <a
              href="/billing/storage"
              data-testid="storage-plans-cta"
              className="flex-1 text-center px-3 py-2 rounded-lg bg-gradient-to-r from-amber-400 to-yellow-500 hover:opacity-90 text-black text-xs font-black"
            >
              {isArchived ? 'استرداد الملفات' : isPastDue ? 'جدّد الاشتراك' : 'باقات التخزين'}
            </a>
            <a
              href="/pricing"
              data-testid="storage-pricing-cta"
              className="px-3 py-2 rounded-lg border border-amber-500/40 text-amber-200 text-xs font-bold hover:bg-amber-500/10"
            >
              النقاط
            </a>
          </div>
        </div>
        </>,
        document.body
      )}
    </div>
  );
}
