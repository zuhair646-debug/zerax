import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, X } from 'lucide-react';

/**
 * PromoStrip — Persistent gold bar at the very top of every page.
 * Shows the current active promo / discount / urgency message.
 * Dismissible (per-session). Subtle shimmer (NOT a glow — a one-time shine).
 */
const PROMO = {
  text: 'خصم 20% على باقة Premium الأسبوع · استخدم الكود',
  code: 'ZITEX20',
  cta: 'اشتري الآن',
  href: '/pricing?promo=ZITEX20',
};

export const PromoStrip = () => {
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setDismissed(sessionStorage.getItem('zitex_promo_dismissed') === '1');
  }, []);

  if (dismissed) return null;

  const close = (e) => {
    e.stopPropagation();
    sessionStorage.setItem('zitex_promo_dismissed', '1');
    setDismissed(true);
  };

  return (
    <div
      className="promo-strip fixed top-0 left-0 right-0 z-[60] cursor-pointer"
      onClick={() => navigate(PROMO.href)}
      data-testid="promo-strip"
    >
      <div className="promo-shine" />
      <div className="relative flex items-center justify-center gap-2 sm:gap-3 px-4 py-1.5 text-black">
        <Sparkles className="w-3.5 h-3.5 flex-shrink-0" />
        <span className="text-[11px] sm:text-xs font-black tracking-tight truncate">
          {PROMO.text}
          <span className="mx-1.5 px-2 py-0.5 rounded bg-black/15 font-mono font-black">
            {PROMO.code}
          </span>
          <span className="hidden sm:inline">· {PROMO.cta} ←</span>
        </span>
        <button
          type="button"
          onClick={close}
          className="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-black/15 hover:bg-black/30 flex items-center justify-center"
          aria-label="إغلاق"
          data-testid="promo-close"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
};

export default PromoStrip;
