/**
 * Pricing — credit packs only (no subscriptions).
 *   • 7 fixed packs ($9 → $1000) with progressive discount
 *   • Custom amount: user enters $ and gets 90 credits per dollar ($5–$10,000)
 *   • Each pack has PayPal + LemonSqueezy buttons
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles, Flame, Calculator } from 'lucide-react';
import { toast } from 'sonner';
import ZenrexBrand from '../components/ZenrexBrand';

const API = process.env.REACT_APP_BACKEND_URL;
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

const PACKS = [
  { id: 'credits_mini',   price: 9,    credits: 1_200,   badge: null },
  { id: 'credits_small',  price: 19,   credits: 2_800,   badge: null },
  { id: 'credits_medium', price: 49,   credits: 7_500,   badge: 'الأكثر شعبية', popular: true },
  { id: 'credits_large',  price: 99,   credits: 16_000,  badge: 'وفّر 10%' },
  { id: 'credits_xl',     price: 199,  credits: 32_000,  badge: 'وفّر 15%' },
  { id: 'credits_pro',    price: 500,  credits: 80_000,  badge: 'وفّر 20%' },
  { id: 'credits_mega',   price: 1000, credits: 160_000, badge: 'وفّر 25%' },
  { id: 'credits_enterprise', price: 3000, credits: 510_000, badge: 'أفضل قيمة' },
];

const fmt = (n) => n.toLocaleString('en-US');

function PackCard({ pack, onBuy, busy }) {
  return (
    <div
      className={`relative rounded-2xl border p-5 ${
        pack.popular ? 'border-amber-400/50 bg-amber-500/10 ring-2 ring-amber-500/30' : 'border-white/10 bg-zinc-900/40'
      }`}
      data-testid={`pack-card-${pack.id}`}
    >
      {pack.badge && (
        <div className={`absolute -top-3 right-4 px-3 py-1 rounded-full text-[10px] font-black ${
          pack.popular ? 'bg-amber-400 text-black' : 'bg-emerald-500 text-white'
        }`}>
          {pack.badge}
        </div>
      )}
      <div className="text-center mb-4">
        <div className="text-xs text-zinc-400 mb-1">${pack.price} USD</div>
        <div className="text-3xl font-black text-white">${pack.price}</div>
        <div className="mt-2 inline-flex items-center gap-1.5 text-amber-300 font-black text-lg">
          <Sparkles className="w-4 h-4" /> {fmt(pack.credits)} نقطة
        </div>
      </div>
      <button
        onClick={() => onBuy(pack.id, 'paypal')}
        disabled={!!busy}
        data-testid={`buy-${pack.id}-paypal`}
        className="w-full px-3 py-2 rounded-lg bg-[#0070ba] hover:bg-[#005ea6] text-white text-xs font-black mb-2 disabled:opacity-50"
      >
        {busy === `${pack.id}-paypal` ? '...' : <><span className="font-extrabold">Pay</span>Pal</>}
      </button>
      <button
        onClick={() => onBuy(pack.id, 'lemon')}
        disabled={!!busy}
        data-testid={`buy-${pack.id}-lemon`}
        className="w-full px-3 py-2 rounded-lg bg-[#FFC233] hover:bg-[#fcd460] text-black text-xs font-black disabled:opacity-50"
      >
        {busy === `${pack.id}-lemon` ? '...' : 'LemonSqueezy'}
      </button>
    </div>
  );
}

export default function Pricing() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(null);
  const [customAmount, setCustomAmount] = useState('');
  const isAuthed = !!localStorage.getItem('token');

  const buy = async (pkgId, method) => {
    if (!isAuthed) { navigate('/login?return=/pricing'); return; }
    setBusy(`${pkgId}-${method}`);
    try {
      const url = method === 'paypal'
        ? `${API}/api/payments/paypal/create`
        : `${API}/api/payments/lemonsqueezy/create`;
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({ package_id: pkgId }),
      });
      const d = await r.json();
      const redirect = d.approval_url || d.checkout_url;
      if (!r.ok || !redirect) {
        toast.error(d.detail || 'فشل إنشاء جلسة الدفع');
        return;
      }
      window.location.href = redirect;
    } catch (_) {
      toast.error('فشل الاتصال بالخادم');
    } finally {
      setBusy(null);
    }
  };

  const buyCustom = async () => {
    if (!isAuthed) { navigate('/login?return=/pricing'); return; }
    const amt = parseFloat(customAmount);
    if (!amt || amt < 5) { toast.error('الحد الأدنى $5'); return; }
    if (amt > 10000) { toast.error('الحد الأعلى $10,000'); return; }
    setBusy('custom-paypal');
    try {
      const r = await fetch(`${API}/api/payments/custom/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({ amount_usd: amt, method: 'paypal' }),
      });
      const d = await r.json();
      if (!r.ok || !d.approval_url) { toast.error(d.detail || 'فشل'); return; }
      window.location.href = d.approval_url;
    } catch (_) {
      toast.error('فشل الاتصال بالخادم');
    } finally { setBusy(null); }
  };

  const customCredits = parseFloat(customAmount) > 0 ? Math.round(parseFloat(customAmount) * 90) : 0;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" dir="rtl" data-testid="pricing-page">
      <header className="border-b border-white/10 bg-zinc-950/85 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <a href="/" className="hover:opacity-90"><ZenrexBrand size={26} /></a>
          <a href="/" className="inline-flex items-center gap-1.5 text-zinc-400 hover:text-zinc-200 text-sm" data-testid="back-link">
            <ArrowLeft className="w-4 h-4" /> رجوع
          </a>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs mb-3" data-testid="launch-promo-banner">
            <Flame className="w-3.5 h-3.5" />
            <span className="font-black">ادفع، احصل على النقاط، استخدمها كما تشاء</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black mb-2">باقات النقاط</h1>
          <p className="text-zinc-400 text-sm">كل النقاط لا تنتهي صلاحيتها · بدون اشتراكات شهرية</p>
        </div>

        {/* Custom amount block */}
        <div className="mb-8 rounded-2xl border border-purple-500/30 bg-gradient-to-br from-purple-500/10 to-fuchsia-500/5 p-5 sm:p-6" data-testid="custom-amount-card">
          <div className="flex items-center gap-2 mb-3">
            <Calculator className="w-5 h-5 text-purple-300" />
            <h3 className="text-base font-black text-purple-200">مبلغ مخصص (90 نقطة لكل دولار)</h3>
          </div>

          {/* Input + Pay button row */}
          <div className="flex flex-col sm:flex-row items-stretch gap-3">
            <div className="relative flex-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 font-bold">$</span>
              <input
                type="number"
                min="5"
                max="10000"
                step="1"
                value={customAmount}
                onChange={(e) => setCustomAmount(e.target.value)}
                placeholder="مثلاً 25"
                data-testid="custom-amount-input"
                className="w-full pl-7 pr-3 py-3 rounded-xl bg-black/40 border border-white/10 focus:border-purple-400 focus:outline-none text-lg font-bold text-white text-center"
              />
            </div>
            <button
              onClick={buyCustom}
              disabled={!customAmount || busy === 'custom-paypal'}
              data-testid="custom-buy-btn"
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-500 to-fuchsia-500 hover:opacity-90 text-white font-black text-sm disabled:opacity-50"
            >
              {busy === 'custom-paypal' ? '...' : 'ادفع عبر PayPal'}
            </button>
          </div>

          {/* Always-visible credits preview block (own row, prominent) */}
          <div
            className="mt-4 rounded-xl border border-amber-400/40 bg-gradient-to-r from-amber-500/10 via-amber-500/15 to-amber-500/10 px-5 py-4 flex items-center justify-between"
            data-testid="custom-credits-preview-block"
          >
            <div className="flex items-center gap-2 text-amber-200 text-sm font-bold">
              <Sparkles className="w-4 h-4" />
              <span>ستحصل على</span>
            </div>
            <div className="text-2xl sm:text-3xl font-black text-amber-300 tabular-nums" data-testid="custom-credits-preview">
              {customCredits > 0 ? `${fmt(customCredits)}` : '0'}
              <span className="text-sm font-bold text-amber-200/70 mr-2">نقطة</span>
            </div>
          </div>

          <p className="text-[11px] text-zinc-500 mt-3 text-center">الحد الأدنى $5 · الحد الأعلى $10,000 · 90 نقطة لكل دولار</p>
        </div>

        {/* Fixed packs */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {PACKS.map((p) => <PackCard key={p.id} pack={p} onBuy={buy} busy={busy} />)}
        </div>

        <p className="text-center text-xs text-zinc-500 mt-8">
          PayPal أو LemonSqueezy · المعاملات بالدولار الأمريكي · النقاط تُضاف فوراً بعد الدفع
        </p>
      </main>
    </div>
  );
}
