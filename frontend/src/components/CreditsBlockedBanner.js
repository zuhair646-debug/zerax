/**
 * CreditsBlockedBanner — drop-in inline UI for "out of credits".
 * Replace your chat input with this when useCreditsGuard().isBlocked is true.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Sparkles, ArrowLeft } from 'lucide-react';

const PACKS = [
  { id: 'tier_starter_monthly', label: 'Starter', price: 19, credits: 2000, color: 'from-emerald-500 to-teal-500' },
  { id: 'project_pack',         label: 'Project Pack', price: 49, credits: 5000, color: 'from-cyan-500 to-blue-500' },
  { id: 'tier_pro_monthly',     label: 'Pro',          price: 69, credits: 8000, color: 'from-amber-400 to-yellow-500' },
];

export default function CreditsBlockedBanner({ compact = false }) {
  const navigate = useNavigate();
  return (
    <div
      data-testid="credits-blocked-banner"
      className="rounded-2xl border border-red-500/50 bg-gradient-to-br from-red-500/15 via-orange-500/10 to-amber-500/10 p-5 sm:p-6"
      dir="rtl"
    >
      <div className="flex items-start gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-red-500/20 border border-red-500/40 flex items-center justify-center flex-shrink-0 animate-pulse">
          <AlertTriangle className="w-5 h-5 text-red-300" />
        </div>
        <div className="flex-1">
          <h3 className="text-base sm:text-lg font-black text-red-200 mb-0.5">رصيد النقاط انتهى</h3>
          <p className="text-xs sm:text-sm text-red-100/80">
            وصلت لـ <span className="font-bold text-red-200">0 نقطة</span>. الكتابة معطّلة لجميع أقسام الذكاء الاصطناعي حتى تشحن باقة جديدة.
          </p>
        </div>
      </div>

      {!compact && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-4">
          {PACKS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => navigate('/pricing')}
              data-testid={`recharge-quick-${p.id}`}
              className={`text-right rounded-xl border border-white/10 bg-black/40 hover:bg-black/60 p-3 transition group`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-zinc-400 uppercase tracking-widest">{p.label}</span>
                <Sparkles className="w-3.5 h-3.5 text-amber-300 opacity-70 group-hover:opacity-100" />
              </div>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-black text-white">${p.price}</span>
              </div>
              <div className={`mt-1 text-xs font-bold bg-gradient-to-r ${p.color} bg-clip-text text-transparent`}>
                {p.credits.toLocaleString('en-US')} نقطة
              </div>
            </button>
          ))}
        </div>
      )}

      <button
        type="button"
        onClick={() => navigate('/pricing')}
        data-testid="recharge-cta"
        className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-amber-400 to-yellow-500 hover:opacity-90 text-black text-sm font-black transition"
      >
        <ArrowLeft className="w-4 h-4" />
        اشحن النقاط الآن
      </button>
    </div>
  );
}
