/**
 * Ready Sites — Step 2: Pay First, then Build
 *
 * Two plans displayed in USD:
 *   1. Full Purchase ($79) — ownership + 5,000 credits
 *   2. Paid Trial ($9, 7 days) — try the AI with 500 credits
 *
 * Both buttons redirect to Stripe checkout. After successful payment, the
 * billing webhook auto-creates the FreeBuild project for the chosen
 * category and the user is bounced to /ready-sites/success?session_id=…
 * which polls and finally redirects to /freebuild/chat/{project_id}.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowRight, Check, Sparkles, Clock, ShoppingCart, Info, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

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
    id: 'ready_sites_purchase',
    plan: 'purchase',
    badge: 'الأكثر اختياراً',
    title: 'شراء كامل',
    price: '79',
    currency: '$',
    period: 'مرة واحدة · ملكية كاملة',
    cta: 'اشترِ الآن وابدأ',
    features: [
      'موقع كامل احترافي بتخصصك',
      'دومين مخصص لمدة سنة كاملة',
      'محرر AI داخل الموقع',
      '5,000 نقطة AI تشحن مع الباقة',
      'تطبيق جوال PWA',
      'تكامل بوابات الدفع',
    ],
    primary: true,
  },
  {
    id: 'ready_sites_trial',
    plan: 'trial',
    badge: 'جرّب قبل ما تشتري',
    title: 'تجربة مدفوعة',
    price: '9',
    currency: '$',
    period: '7 أيام · لاختبار التجربة',
    cta: 'ابدأ التجربة',
    features: [
      'موقع كامل لمدة 7 أيام',
      'كل ميزات الذكاء الاصطناعي مفتوحة',
      '500 نقطة AI لتختبر',
      'تقدر تحوّلها لشراء كامل لاحقاً',
      '⚠️ الموقع يُحذف تلقائياً بعد 7 أيام لو ما اشتريت',
    ],
    primary: false,
  },
];

const getQueryParam = (search, key) => {
  try { return new URLSearchParams(search).get(key); } catch (_) { return null; }
};

export default function ReadySitesPurchase({ user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [category, setCategory] = useState(null);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    if (typeof window !== 'undefined') window.scrollTo(0, 0);
    let cat = null;
    try {
      const stored = sessionStorage.getItem('zx_ready_sites_category');
      if (stored) cat = JSON.parse(stored);
    } catch (_) { /* ignore */ }
    const catId = getQueryParam(location.search, 'category');
    if (!cat && catId) {
      cat = { id: catId, title: CATEGORY_LABELS[catId] || catId };
    }
    if (!cat) {
      navigate('/ready-sites', { replace: true });
      return;
    }
    setCategory(cat);
  }, [location.search, navigate]);

  const handleSelect = async (plan) => {
    if (!category || busy) return;
    setBusy(plan.id);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        toast.error('سجّل دخول أولاً عشان تكمل الشراء');
        // Preserve flow: bounce back to login then back here
        sessionStorage.setItem('zx_ready_sites_category', JSON.stringify(category));
        navigate(`/login?return=/ready-sites/purchase?category=${category.id}`);
        return;
      }
      // Persist so we can recover if user navigates back from Stripe
      sessionStorage.setItem('zx_ready_sites_category', JSON.stringify(category));

      const r = await fetch(`${API}/api/billing/checkout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          package_id: plan.id,
          origin_url: window.location.origin,
          extra_metadata: {
            category_id: category.id,
            plan: plan.plan,
            source: 'ready_sites',
          },
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok || !data.url) {
        throw new Error(data.detail || data.message || 'فشل إنشاء جلسة الدفع');
      }
      // Redirect to Stripe Checkout
      window.location.href = data.url;
    } catch (e) {
      toast.error(`فشل الدفع: ${e.message || 'حاول مرة ثانية'}`);
      console.error('checkout err', e);
    } finally {
      setBusy(null);
    }
  };

  if (!category) return null;

  return (
    <div className="min-h-screen bg-[#08070d] text-white" dir="rtl" data-testid="rs-purchase-page">
      <header className="max-w-5xl mx-auto px-6 pt-12 pb-6 text-center">
        <button
          onClick={() => navigate('/ready-sites')}
          className="text-amber-300 hover:text-amber-200 text-sm font-bold mb-4 inline-flex items-center gap-1.5"
          data-testid="back-to-categories-btn"
        >
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
          ادفع أول، يفتح AI ويبني موقعك في دقائق. المدفوعات آمنة عبر Stripe.
        </p>
      </header>

      <main className="max-w-5xl mx-auto px-6 pb-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5" data-testid="plans-grid">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`relative rounded-2xl border p-6 sm:p-8 transition-all duration-300 hover:-translate-y-1 ${
                plan.primary
                  ? 'border-amber-400/40 bg-gradient-to-br from-amber-500/10 to-amber-500/[0.02] hover:border-amber-400/70 hover:shadow-2xl hover:shadow-amber-500/20'
                  : 'border-white/10 bg-white/[0.02] hover:border-sky-400/40 hover:shadow-xl hover:shadow-sky-500/10'
              }`}
              data-testid={`plan-card-${plan.plan}`}
            >
              <div
                className={`absolute -top-3 right-6 px-3 py-1 rounded-full text-[11px] font-black ${
                  plan.primary ? 'bg-amber-400 text-black' : 'bg-sky-500 text-white'
                }`}
              >
                {plan.badge}
              </div>

              <div className="flex items-center gap-3 mb-4">
                <div
                  className={`w-11 h-11 rounded-xl flex items-center justify-center ${
                    plan.primary ? 'bg-amber-400/20 text-amber-300' : 'bg-sky-500/20 text-sky-300'
                  }`}
                >
                  {plan.primary ? <ShoppingCart className="w-5 h-5" /> : <Clock className="w-5 h-5" />}
                </div>
                <h3 className="text-2xl font-black">{plan.title}</h3>
              </div>

              <div className="mb-5">
                <span className="text-base font-bold text-gray-400">{plan.currency}</span>
                <span className="text-5xl font-black">{plan.price}</span>
                <div className="text-xs text-gray-500 mt-1">{plan.period}</div>
              </div>

              <ul className="space-y-2.5 mb-6">
                {plan.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm leading-relaxed">
                    <Check
                      className={`w-4 h-4 flex-shrink-0 mt-0.5 ${
                        plan.primary ? 'text-amber-300' : 'text-sky-300'
                      }`}
                    />
                    <span className="text-white/85">{f}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleSelect(plan)}
                disabled={busy !== null}
                className={`w-full py-3.5 rounded-xl font-black text-base transition-all inline-flex items-center justify-center gap-2 ${
                  plan.primary
                    ? 'bg-amber-400 text-black hover:bg-amber-300 disabled:bg-amber-400/40 disabled:cursor-wait'
                    : 'bg-white/10 text-white hover:bg-white/15 border border-white/10 hover:border-white/20 disabled:opacity-50 disabled:cursor-wait'
                }`}
                data-testid={`select-plan-${plan.plan}-btn`}
              >
                {busy === plan.id ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" /> جاري التحويل لصفحة الدفع...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" /> {plan.cta}
                  </>
                )}
              </button>
            </div>
          ))}
        </div>

        <div className="mt-8 bg-amber-500/5 border border-amber-500/20 rounded-xl px-5 py-4 flex items-start gap-3" data-testid="rs-purchase-disclaimer">
          <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-amber-100/80 leading-relaxed">
            <b className="text-amber-300">آمن:</b> الدفع يتم على Stripe مباشرة. بعد إتمام الدفع
            بنجاح، يفتح AI تلقائياً ويبدأ ببناء موقعك.
          </div>
        </div>
      </main>
    </div>
  );
}
