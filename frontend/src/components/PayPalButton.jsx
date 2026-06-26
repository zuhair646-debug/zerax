/**
 * 💳 PayPalButton — single unified payment button used across the app.
 *
 * Visual: PayPal brand-faithful gradient — top-half blue (#0070ba)
 *         seamlessly blending into yellow (#ffc439) with the wordmark
 *         "PayPal" centered. Lifted, rounded, with subtle motion.
 *
 * Behavior: calls /api/payments/paypal/create → opens checkout URL
 *           in a new tab → on return, /paypal/capture is hit by the
 *           landing page (Pricing or wherever the user came from).
 *
 * Props:
 *   amountUsd      number   — final price in USD
 *   pkgId          string   — package identifier (e.g. "starter", "code_only")
 *   meta           object   — extra context (project_id, tier, etc.)
 *   label          string   — text shown above the button (e.g. "اشترك بـ$5")
 *   className      string   — extra wrapper classes
 *   onSuccess      fn       — called after capture
 *   onError        fn       — called on failure
 */
import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function PayPalButton({
  amountUsd,
  pkgId,
  meta = {},
  label = '',
  className = '',
  onSuccess,
  onError,
}) {
  const [busy, setBusy] = useState(false);

  const startCheckout = async () => {
    if (busy) return;
    if (!amountUsd || amountUsd <= 0) {
      toast.error('مبلغ غير صالح');
      return;
    }
    setBusy(true);
    try {
      const token = localStorage.getItem('token');
      const r = await fetch(`${API}/api/payments/paypal/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          pkg_id: pkgId,
          amount_usd: Number(amountUsd),
          meta,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل بدء الدفع');
      if (!d.approval_url) throw new Error('PayPal لم يرد بوابة دفع');
      // Open PayPal checkout in a new tab so the user keeps their state
      window.open(d.approval_url, '_blank', 'noopener,noreferrer,width=600,height=800');
      toast.success('تم فتح PayPal — أكمل الدفع في النافذة الجديدة');
      onSuccess?.(d);
    } catch (e) {
      toast.error(e.message);
      onError?.(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`flex flex-col items-stretch gap-1.5 ${className}`}>
      {label && (
        <div className="text-[11px] text-zinc-400 text-center font-bold">
          {label}
        </div>
      )}
      <button
        type="button"
        onClick={startCheckout}
        disabled={busy}
        data-testid={`paypal-pay-btn-${pkgId}`}
        className="relative group w-full overflow-hidden rounded-xl shadow-lg shadow-blue-900/30 transition-all hover:scale-[1.02] active:scale-[0.99] disabled:opacity-60 disabled:scale-100 disabled:cursor-wait"
        style={{
          background: 'linear-gradient(180deg, #003087 0%, #0070ba 50%, #ffc439 100%)',
        }}
      >
        <div className="absolute inset-0 opacity-30 pointer-events-none bg-gradient-to-br from-white/20 via-transparent to-transparent" />
        <div className="relative flex items-center justify-center gap-2 py-3 px-4">
          {busy ? (
            <Loader2 className="w-5 h-5 animate-spin text-white" />
          ) : (
            <>
              {/* "Pay" in italics white with PayPal styling */}
              <span
                className="text-lg font-black italic"
                style={{ color: '#003087', textShadow: '0 1px 0 rgba(255,255,255,0.5)' }}
              >
                Pay
              </span>
              <span
                className="text-lg font-black italic"
                style={{ color: '#ffffff', textShadow: '0 1px 0 rgba(0,0,0,0.2)' }}
              >
                Pal
              </span>
              <span className="mx-2 h-4 w-px bg-white/40" />
              <span className="text-sm font-bold text-white drop-shadow">
                ${Number(amountUsd).toFixed(amountUsd % 1 === 0 ? 0 : 2)}
              </span>
            </>
          )}
        </div>
        {/* Animated shine on hover */}
        <span className="pointer-events-none absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 bg-gradient-to-r from-transparent via-white/15 to-transparent" />
      </button>
      <p className="text-[10px] text-zinc-500 text-center">
        🔒 دفع آمن عبر PayPal · بدون حفظ بياناتك معنا
      </p>
    </div>
  );
}
