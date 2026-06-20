/**
 * CreditsBlockedBanner — calm, compact in-chat notice.
 * Replaces the chat input row when credits = 0. Single tappable surface
 * that navigates to /pricing. Designed to feel like a gentle prompt,
 * not an alarm.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, ArrowLeft } from 'lucide-react';

export default function CreditsBlockedBanner({ variant = 'inline' }) {
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() => navigate('/pricing')}
      data-testid="credits-blocked-banner"
      className="w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl border border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10 hover:border-amber-500/50 transition text-right group"
      dir="rtl"
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-8 h-8 rounded-full bg-amber-500/15 border border-amber-500/30 flex items-center justify-center flex-shrink-0">
          <Sparkles className="w-4 h-4 text-amber-300" />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-bold text-amber-200">انتهى رصيد النقاط</p>
          <p className="text-[10px] text-amber-100/60 truncate">اضغط هنا لشحن باقة جديدة وتكمل من نفس النقطة</p>
        </div>
      </div>
      <div className="flex items-center gap-1.5 text-amber-300 text-[11px] font-bold opacity-80 group-hover:opacity-100 transition flex-shrink-0">
        <span>عرض الباقات</span>
        <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
      </div>
    </button>
  );
}
