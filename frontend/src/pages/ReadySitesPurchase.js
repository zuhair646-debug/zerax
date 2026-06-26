/**
 * Ready Sites — Step 2: Pay First (PayPal only)
 *
 * Two USD plans:
 *   • Paid Trial — $9 / 7 days / 500 credits
 *   • Full Purchase — $79 / 5,000 credits / ownership
 *
 * Payment processor: PayPal (Lemon Squeezy removed Feb 2026).
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowRight, Check, Clock, ShoppingCart, Info, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

const CATEGORY_LABELS = {
  restaurants: 'مطاعم وكافيهات',
  electronics: 'إلكترونيات وتقنية',
  stationery: 'قرطاسيات ومكتبات',
  grocery: 'بقالات وسوبرماركت',
  pharmacy: 'صيدليات',
  fashion: 'أزياء وموضة',
  beauty: 'تجميل وعطور',
  flowers: 'زهور وهدايا',
};

const PLANS = [
  {
    id: 'purchase',
    badge: 'الأكثر اختياراً',
    title: 'شراء كامل',
    price: '79',
    period: 'مرة واحدة · ملكية كاملة',
    features: [
      'موقع كامل احترافي بتخصصك',
      'ملكية كاملة + دومين سنة',
      'محرر AI داخل الموقع',
      '5,000 نقطة AI',
      'تطبيق جوال PWA',
    ],
    primary: true,
  },
  {
    id: 'trial',
    badge: 'جرّب قبل ما تشتري',
    title: 'تجربة مدفوعة',
    price: '9',
    period: '7 أيام · 500 نقطة',
    features: [
      'موقع كامل لمدة 7 أيام',
      'كل ميزات AI مفتوحة',
      '500 نقطة AI لاختبار',
      '⚠️ الموقع يُحذف بعد 7 أيام لو ما اشتريت',
    ],
    primary: false,
  },
];

const getQuery = (search, key) => {
  try { return new URLSearchParams(search).get(key); } catch (_) { return null; }
};

export default function ReadySitesPurchase({ user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [category, setCategory] = useState(null);
  const [busy, setBusy] = useState(null); // 'trial-paypal' | 'full-paypal'

  useEffect(() => {
    if (typeof window !== 'undefined') window.scrollTo(0, 0);
    let cat = null;
    try {
      const stored = sessionStorage.getItem('zx_ready_sites_category');
      if (stored) cat = JSON.parse(stored);
    } catch (_) { /* ignore */ }
    const catId = getQuery(location.search, 'category');
    if (!cat && catId) cat = { id: catId, title: CATEGORY_LABELS[catId] || catId };
    if (!cat) { navigate('/ready-sites', { replace: true }); return; }
    setCategory(cat);
  }, [location.search, navigate]);

  const requireAuth = () => {
    if (!localStorage.getItem('token')) {
      sessionStorage.setItem('zx_ready_sites_category', JSON.stringify(category));
      toast.error('سجّل دخول أولاً عشان تكمل الشراء');
      navigate(`/login?return=/ready-sites/purchase?category=${category.id}`);
      return false;
    }
    return true;
  };

  const payPayPal = async (planId) => {
    if (!category || !requireAuth()) return;
    setBusy(`${planId}-paypal`);
    try {
      const r = await fetch(`${API}/api/ready-sites/paypal/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({ category_id: category.id, plan: planId }),
      });
      const d = await r.json();
      if (!r.ok || !d.approval_url) throw new Error(d.detail || 'فشل PayPal');
      window.location.href = d.approval_url;
    } catch (e) {
      toast.error(e.message || 'فشل الاتصال بـ PayPal');
    } finally { setBusy(null); }
  };

  // payLemon kept as no-op stub to avoid breaking any cached references.
  // Lemon Squeezy was fully removed in Feb 2026.

  if (!category) return null;

  return (
    <div className="min-h-screen bg-[#08070d] text-white" dir="rtl" data-testid="rs-purchase-page">
      <header className="max-w-5xl mx-auto px-6 pt-12 pb-6 text-center">
        <button onClick={() => navigate('/ready-sites')}
          className="text-amber-300 hover:text-amber-200 text-sm font-bold mb-4 inline-flex items-center gap-1.5"
          data-testid="back-to-categories-btn">
          <ArrowRight className="w-3.5 h-3.5" /> رجوع للتخصصات
        </button>
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-white/70 text-xs font-bold mb-4">
          <Check className="w-3.5 h-3.5 text-emerald-400" />
          اخترت: <b className="text-amber-300">{category.title}</b>
        </div>
        <h1 className="text-4xl sm:text-5xl font-black mb-3 bg-gradient-to-b from-white to-amber-200 bg-clip-text text-transparent">
          خطوة قبل ما يبدأ AI ✨
        </h1>
        <p className="text-base text-gray-400 max-w-xl mx-auto leading-relaxed">
          اختر طريقة الدفع المناسبة لك. بعد إتمام الدفع، AI يفتح ويبني موقعك في دقائق.
        </p>
      </header>

      <main className="max-w-5xl mx-auto px-6 pb-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5" data-testid="plans-grid">
          {PLANS.map((plan) => (
            <div key={plan.id}
              className={`relative rounded-2xl border p-6 sm:p-8 transition-all ${
                plan.primary
                  ? 'border-amber-400/40 bg-gradient-to-br from-amber-500/10 to-amber-500/[0.02]'
                  : 'border-white/10 bg-white/[0.02]'
              }`}
              data-testid={`plan-card-${plan.id}`}>
              <div className={`absolute -top-3 right-6 px-3 py-1 rounded-full text-[11px] font-black ${
                plan.primary ? 'bg-amber-400 text-black' : 'bg-sky-500 text-white'
              }`}>
                {plan.badge}
              </div>

              <div className="flex items-center gap-3 mb-4">
                <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${
                  plan.primary ? 'bg-amber-400/20 text-amber-300' : 'bg-sky-500/20 text-sky-300'
                }`}>
                  {plan.primary ? <ShoppingCart className="w-5 h-5" /> : <Clock className="w-5 h-5" />}
                </div>
                <h3 className="text-2xl font-black">{plan.title}</h3>
              </div>

              <div className="mb-5">
                <span className="text-base font-bold text-gray-400">$</span>
                <span className="text-5xl font-black">{plan.price}</span>
                <div className="text-xs text-gray-500 mt-1">{plan.period}</div>
              </div>

              <ul className="space-y-2 mb-6">
                {plan.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <Check className={`w-4 h-4 flex-shrink-0 mt-0.5 ${plan.primary ? 'text-amber-300' : 'text-sky-300'}`} />
                    <span className="text-white/85">{f}</span>
                  </li>
                ))}
              </ul>

              {/* Payment button — PayPal only (Lemon Squeezy removed Feb 2026) */}
              <div className="space-y-2.5">
                <button
                  onClick={() => payPayPal(plan.id)}
                  disabled={busy !== null}
                  className="w-full py-3 rounded-xl font-black text-sm transition-all inline-flex items-center justify-center gap-2 bg-[#0070ba] hover:bg-[#005ea6] text-white disabled:opacity-50 disabled:cursor-wait"
                  data-testid={`paypal-${plan.id}-btn`}
                >
                  {busy === `${plan.id}-paypal` ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> جاري التحويل...</>
                  ) : (
                    <><span className="font-extrabold">Pay</span><span className="italic font-bold">Pal</span><span className="text-xs opacity-80">— ${plan.price}</span></>
                  )}
                </button>
                <p className="text-[10px] text-zinc-500 text-center">
                  ادفع بأمان عبر PayPal (بطاقة أو رصيد PayPal)
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 bg-amber-500/5 border border-amber-500/20 rounded-xl px-5 py-4 flex items-start gap-3" data-testid="rs-purchase-disclaimer">
          <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-amber-100/80 leading-relaxed">
            <b className="text-amber-300">آمن:</b> الدفع يتم مباشرة عبر PayPal. بعد إتمام الدفع
            بنجاح، يفتح AI تلقائياً ويبدأ ببناء موقعك.
          </div>
        </div>
      </main>
    </div>
  );
}
