/**
 * Pricing — credits-based, ultra-simple cards.
 *   Each plan: price → credits. No feature lists, no refunds, no promises.
 *   Once purchased, credits are added to the user's balance and consumed
 *   automatically by AI calls / image / video generation.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Flame, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import ZenrexBrand from '../components/ZenrexBrand';

const API = process.env.REACT_APP_BACKEND_URL;

const formatPoints = (n) => n.toLocaleString('en-US');

function TierCard({ pkg, onBuy, busy }) {
  const isMonthly = pkg.subscription_type === 'tier_upgrade' && pkg.duration_days >= 28 && pkg.id !== 'project_pack';
  const period = pkg.id === 'project_pack' ? 'مرّة واحدة' : 'شهرياً';

  // Color theme per tier
  const themes = {
    project_pack:        { border: 'border-cyan-500/40',   bg: 'bg-gradient-to-br from-cyan-500/10 to-blue-500/5',     accent: 'text-cyan-300',    btn: 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white' },
    tier_starter_monthly:{ border: 'border-emerald-500/40',bg: 'bg-gradient-to-br from-emerald-500/10 to-teal-500/5',  accent: 'text-emerald-300', btn: 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white' },
    tier_pro_monthly:    { border: 'border-amber-500/60',  bg: 'bg-gradient-to-br from-amber-500/15 to-yellow-500/5',  accent: 'text-amber-300',   btn: 'bg-gradient-to-r from-amber-400 to-yellow-500 text-black' },
    tier_studio_monthly: { border: 'border-purple-500/40', bg: 'bg-gradient-to-br from-purple-500/10 to-fuchsia-500/5',accent: 'text-purple-300',  btn: 'bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white' },
  };
  const t = themes[pkg.id] || themes.tier_starter_monthly;
  const highlighted = pkg.id === 'tier_pro_monthly';

  return (
    <div
      data-testid={`tier-${pkg.id}`}
      className={`relative rounded-2xl border ${t.border} ${t.bg} p-6 ${highlighted ? 'ring-2 ring-amber-500/40 scale-[1.02]' : ''}`}
    >
      {highlighted && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-black px-3 py-1 rounded-full whitespace-nowrap bg-amber-400 text-black">
          الأكثر شعبية
        </div>
      )}

      <h3 className={`text-xl font-black ${t.accent} mb-3`}>{pkg.name}</h3>

      {/* Price */}
      <div className="mb-1">
        {pkg.original_price_usd && (
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm text-zinc-500 line-through">${pkg.original_price_usd}</span>
            {pkg.discount_pct ? (
              <span className="text-[10px] font-black px-1.5 py-0.5 rounded-md bg-rose-500/20 border border-rose-500/40 text-rose-300">
                -{pkg.discount_pct}% عرض الإطلاق
              </span>
            ) : null}
          </div>
        )}
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-black text-white">${pkg.price_usd}</span>
          <span className="text-xs text-zinc-500"> · {period}</span>
        </div>
      </div>

      {/* Credits — the only metric that matters */}
      <div className="mt-5 mb-6 rounded-xl border border-white/10 bg-black/30 p-4 text-center">
        <div className="flex items-center justify-center gap-2 mb-1">
          <Sparkles className={`w-4 h-4 ${t.accent}`} />
          <span className="text-[11px] uppercase tracking-widest text-zinc-400 font-bold">تحصل على</span>
        </div>
        <div className="text-3xl font-black text-white" data-testid={`credits-${pkg.id}`}>
          {formatPoints(pkg.credits || 0)}
        </div>
        <div className="text-xs text-zinc-400 mt-0.5">نقطة</div>
      </div>

      <button
        onClick={() => onBuy(pkg.id, 'paypal')}
        disabled={busy === `${pkg.id}-paypal` || busy === `${pkg.id}-lemon`}
        data-testid={`buy-${pkg.id}-paypal`}
        className="w-full px-4 py-2.5 rounded-xl text-sm font-black bg-[#0070ba] hover:bg-[#005ea6] text-white disabled:opacity-50 transition mb-2"
      >
        {busy === `${pkg.id}-paypal` ? '...' : (
          <><span className="font-extrabold">Pay</span><span className="italic">Pal</span><span className="opacity-80 text-xs"> — ${pkg.price_usd}</span></>
        )}
      </button>
      <button
        onClick={() => onBuy(pkg.id, 'lemon')}
        disabled={busy === `${pkg.id}-paypal` || busy === `${pkg.id}-lemon`}
        data-testid={`buy-${pkg.id}-lemon`}
        className="w-full px-4 py-2.5 rounded-xl text-sm font-black bg-[#FFC233] hover:bg-[#fcd460] text-black disabled:opacity-50 transition"
        title="بطاقات + Klarna + Afterpay"
      >
        {busy === `${pkg.id}-lemon` ? '...' : `LemonSqueezy — $${pkg.price_usd}`}
      </button>
    </div>
  );
}

export default function Pricing() {
  const navigate = useNavigate();
  const [packages, setPackages] = useState([]);
  const [balance, setBalance] = useState(null);
  const [busy, setBusy] = useState(null);
  const isAuthed = !!localStorage.getItem('token');

  useEffect(() => {
    // Public — fetch packages list
    fetch(`${API}/api/billing/packages`)
      .then((r) => r.json())
      .then((d) => setPackages(d.packages || []))
      .catch(() => {});

    // Authenticated — fetch current credits balance
    if (isAuthed) {
      fetch(`${API}/api/usage/credits`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      })
        .then((r) => (r.ok ? r.json() : null))
        .then(setBalance)
        .catch(() => {});
    }
  }, [isAuthed]);

  const buy = async (packageId, method) => {
    if (!isAuthed) { navigate('/login?return=/pricing'); return; }
    setBusy(`${packageId}-${method}`);
    try {
      const url = method === 'paypal'
        ? `${API}/api/payments/paypal/create`
        : `${API}/api/payments/lemonsqueezy/create`;
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token')}` },
        body: JSON.stringify({ package_id: packageId }),
      });
      const d = await r.json();
      const redirect = d.approval_url || d.checkout_url;
      if (!r.ok || !redirect) {
        toast.error(d.detail || 'فشل إنشاء جلسة الدفع');
        return;
      }
      window.location.href = redirect;
    } catch (e) {
      toast.error('فشل الاتصال بالخادم');
    } finally {
      setBusy(null);
    }
  };

  // Re-order so Pro card appears centered/highlighted
  const orderedIds = ['tier_starter_monthly', 'tier_pro_monthly', 'tier_studio_monthly', 'project_pack'];
  const orderedPackages = orderedIds
    .map((id) => packages.find((p) => p.id === id))
    .filter(Boolean);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" dir="rtl" data-testid="pricing-page">
      <header className="sticky top-0 z-30 border-b border-white/10 bg-zinc-950/85 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <a href="/" className="hover:opacity-90"><ZenrexBrand size={26} /></a>
          <a href="/" className="inline-flex items-center gap-1.5 text-zinc-400 hover:text-zinc-200 text-sm" data-testid="back-link">
            <ArrowLeft className="w-4 h-4" /> رجوع
          </a>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-l from-rose-500/20 via-amber-500/20 to-rose-500/20 border border-rose-500/40 text-rose-200 text-xs mb-4 animate-pulse" data-testid="launch-promo-banner">
            <Flame className="w-4 h-4" />
            <span className="font-black">عرض الإطلاق — خصومات حتى 38% لفترة محدودة</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black mb-2">باقات Zenrex AI</h1>
          <p className="text-zinc-400 max-w-2xl mx-auto text-sm">
            ادفع، احصل على النقاط، استخدمها كيف ما تبي.
          </p>
        </div>

        {/* Current balance — only for logged-in users */}
        {balance && !balance.unlimited && (
          <div data-testid="current-balance" className="mb-8 rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 text-center">
            <p className="text-xs text-amber-300 font-bold mb-1">رصيدك الحالي</p>
            <p className="text-3xl font-black text-amber-200">{formatPoints(balance.credits || 0)} <span className="text-sm text-zinc-400 font-normal">نقطة</span></p>
          </div>
        )}
        {balance && balance.unlimited && (
          <div data-testid="current-balance" className="mb-8 rounded-2xl border border-purple-500/30 bg-purple-500/5 p-4 text-center">
            <p className="text-3xl font-black text-purple-200">رصيد لا محدود</p>
          </div>
        )}

        {/* Tier cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-12">
          {orderedPackages.length === 0 && (
            <div className="col-span-full text-center text-zinc-400 py-10">جاري تحميل الباقات...</div>
          )}
          {orderedPackages.map((pkg) => (
            <TierCard key={pkg.id} pkg={pkg} onBuy={buy} busy={busy} />
          ))}
        </div>

        <p className="text-center text-xs text-zinc-500">
          مدفوعات آمنة عبر Stripe · النقاط تُضاف لرصيدك فوراً بعد الدفع
        </p>
      </main>
    </div>
  );
}
