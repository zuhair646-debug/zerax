import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Sparkles, Check, Zap, Crown, Rocket, Building2, Tag, CreditCard } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const PAYPAL_CLIENT_ID = 'ATLgrd23Yei2wrCUaJTsS2jY8CirmvDOtb3U9uRN7K7p9um7sBrpQ-uUP_b2uU6K05OMhzFa-U9fhupN';

const PLAN_ICONS = {
  free: <Sparkles className="w-6 h-6" />,
  starter: <Zap className="w-6 h-6" />,
  indie: <Rocket className="w-6 h-6" />,
  studio: <Crown className="w-6 h-6" />,
  pro_studio: <Crown className="w-6 h-6" />,
  enterprise: <Building2 className="w-6 h-6" />,
};

export default function Pricing({ user }) {
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [packs, setPacks] = useState([]);
  const [cycle, setCycle] = useState('monthly');
  const [tab, setTab] = useState('plans');
  const [promoCode, setPromoCode] = useState('');
  const [promoResult, setPromoResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [checkingOut, setCheckingOut] = useState(null);

  useEffect(() => {
    (async () => {
      const [p, k] = await Promise.all([
        axios.get(`${API}/api/pricing/plans`),
        axios.get(`${API}/api/pricing/packs`),
      ]);
      setPlans(p.data.plans);
      setPacks(k.data.packs);
    })();
  }, []);

  // Load PayPal SDK with messaging component (Pay in 4 / Pay Monthly badges)
  useEffect(() => {
    if (window.paypal) return;
    const script = document.createElement('script');
    script.src = `https://www.paypal.com/sdk/js?client-id=${PAYPAL_CLIENT_ID}&components=messages&currency=USD`;
    script.async = true;
    script.onload = () => {
      // Re-render messages after script loads
      if (window.paypal && window.paypal.Messages) {
        document.querySelectorAll('[data-pp-message]').forEach(el => {
          try { window.paypal.Messages({ amount: el.dataset.ppAmount, placement: 'product' }).render(el); } catch {}
        });
      }
    };
    document.body.appendChild(script);
  }, []);

  const validatePromo = async (baseAmount, itemType) => {
    if (!promoCode || !user) return null;
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(
        `${API}/api/pricing/promo/check`,
        { code: promoCode, item_type: itemType, base_amount_usd: baseAmount },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      return r.data;
    } catch {
      return null;
    }
  };

  const checkout = async (itemType, itemId, billingCycle = 'monthly') => {
    if (!user) {
      navigate('/login?redirect=/pricing');
      return;
    }
    setCheckingOut(`${itemType}-${itemId}`);
    try {
      const token = localStorage.getItem('token');
      const origin = window.location.origin;
      const r = await axios.post(
        `${API}/api/pricing/checkout`,
        {
          item_type: itemType,
          item_id: itemId,
          billing_cycle: billingCycle,
          promo_code: promoCode || null,
          return_url: `${origin}/pricing/success`,
          cancel_url: `${origin}/pricing`,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      // Save order locally so success page can capture it
      localStorage.setItem('pending_order_id', r.data.order_id);
      window.location.href = r.data.approval_url;
    } catch (e) {
      alert(e.response?.data?.detail || 'فشل بدء الدفع');
      setCheckingOut(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-zinc-900 to-black text-white" dir="rtl">
      {/* Hero */}
      <div className="max-w-6xl mx-auto px-6 pt-20 pb-12 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm mb-6">
          <Sparkles className="w-4 h-4" />
          عرض الإطلاق — 50% خصم لفترة محدودة
        </div>
        <h1 className="text-5xl md:text-6xl font-bold mb-4">
          ابنِ، أنشئ، أبدع
          <span className="bg-gradient-to-r from-amber-400 to-rose-400 bg-clip-text text-transparent"> بدون حدود</span>
        </h1>
        <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
          اختر الباقة اللي تناسب طموحك. كل دولار = 1000 شعلة تستخدمها في الصور والفيديوهات والألعاب والمواقع.
        </p>

        {/* Cycle toggle */}
        <div className="mt-10 inline-flex bg-zinc-900 border border-zinc-800 rounded-full p-1" data-testid="cycle-toggle">
          <button
            onClick={() => setCycle('monthly')}
            data-testid="cycle-monthly"
            className={`px-6 py-2 rounded-full text-sm font-bold transition ${cycle === 'monthly' ? 'bg-amber-500 text-zinc-900' : 'text-zinc-400'}`}
          >
            شهري
          </button>
          <button
            onClick={() => setCycle('yearly')}
            data-testid="cycle-yearly"
            className={`px-6 py-2 rounded-full text-sm font-bold transition ${cycle === 'yearly' ? 'bg-amber-500 text-zinc-900' : 'text-zinc-400'}`}
          >
            سنوي <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded ms-1">- شهرين مجاناً</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="max-w-6xl mx-auto px-6 flex justify-center gap-3 mb-8">
        <button
          onClick={() => setTab('plans')}
          data-testid="tab-plans"
          className={`px-5 py-2.5 rounded-lg font-bold transition ${tab === 'plans' ? 'bg-amber-500 text-zinc-900' : 'bg-zinc-900 text-zinc-400 hover:bg-zinc-800'}`}
        >
          باقات الاشتراك الشهرية
        </button>
        <button
          onClick={() => setTab('packs')}
          data-testid="tab-packs"
          className={`px-5 py-2.5 rounded-lg font-bold transition ${tab === 'packs' ? 'bg-amber-500 text-zinc-900' : 'bg-zinc-900 text-zinc-400 hover:bg-zinc-800'}`}
        >
          حزم الشحن (دفعة واحدة)
        </button>
      </div>

      {/* Promo input */}
      <div className="max-w-md mx-auto px-6 mb-12 flex gap-2">
        <div className="flex-1 relative">
          <Tag className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            value={promoCode}
            onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
            placeholder="عندك كود خصم؟"
            data-testid="promo-input"
            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pe-10 ps-4 py-2.5 text-sm focus:border-amber-500 focus:outline-none"
          />
        </div>
        <button
          onClick={() => setPromoCode('LAUNCH50')}
          data-testid="apply-launch50"
          className="px-4 py-2.5 bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-lg text-sm font-bold hover:bg-amber-500/20"
        >
          LAUNCH50
        </button>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-6 pb-20">
        {tab === 'plans' ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {plans.map((plan) => {
              const price = cycle === 'yearly' ? plan.price_yearly_usd : plan.price_monthly_usd;
              const isFree = plan.price_monthly_usd === 0;
              const isEnt = plan.price_monthly_usd === -1;
              const highlight = plan.highlight;
              return (
                <div
                  key={plan.id}
                  data-testid={`plan-card-${plan.id}`}
                  className={`relative bg-zinc-900 border rounded-2xl p-8 flex flex-col ${
                    highlight ? 'border-amber-500 shadow-2xl shadow-amber-500/10 scale-105' : 'border-zinc-800'
                  }`}
                >
                  {highlight && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-500 text-zinc-900 px-3 py-1 rounded-full text-xs font-bold">
                      الأكثر شعبية
                    </div>
                  )}
                  <div className={`inline-flex w-12 h-12 rounded-xl items-center justify-center mb-4 ${highlight ? 'bg-amber-500/20 text-amber-400' : 'bg-zinc-800 text-zinc-400'}`}>
                    {PLAN_ICONS[plan.id] || <Sparkles className="w-6 h-6" />}
                  </div>
                  <h3 className="text-2xl font-bold">{plan.name_ar}</h3>
                  <p className="text-zinc-500 text-sm mb-6">{plan.name}</p>

                  <div className="mb-6">
                    {isEnt ? (
                      <div className="text-3xl font-bold">تواصل معنا</div>
                    ) : isFree ? (
                      <div className="text-4xl font-bold">$0</div>
                    ) : (
                      <div>
                        <div className="flex items-baseline gap-1">
                          <span className="text-4xl font-bold">${price}</span>
                          <span className="text-zinc-500 text-sm">/{cycle === 'yearly' ? 'سنة' : 'شهر'}</span>
                        </div>
                        {!isFree && cycle === 'monthly' && (
                          <div className="text-xs text-emerald-400 mt-1">
                            {plan.credits_per_month.toLocaleString()} شعلة/شهر = ${(plan.credits_per_month / 1000).toFixed(0)} قيمة
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <ul className="space-y-3 mb-6 flex-1">
                    {(plan.features_ar || []).map((f, i) => (
                      <li key={i} className="flex gap-2 text-sm text-zinc-300">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>

                  {plan.pay_later_eligible && !isFree && !isEnt && (
                    <div className="mb-4 p-3 rounded-lg bg-blue-500/10 border border-blue-500/30 text-xs">
                      <div className="flex items-center gap-2 text-blue-300 font-bold mb-1">
                        <CreditCard className="w-3.5 h-3.5" /> ادفع على 4 دفعات بدون فوائد
                      </div>
                      <div className="text-blue-200/80">
                        4 × ${(price / 4).toFixed(2)} • مع PayPal • للعملاء في 🇺🇸 🇬🇧 🇪🇺 🇦🇺
                      </div>
                      {/* PayPal-rendered messaging badge (shown only to supported regions) */}
                      <div data-pp-message data-pp-amount={price} className="mt-2 hidden" />
                    </div>
                  )}

                  <button
                    disabled={isFree || isEnt || checkingOut === `subscription-${plan.id}`}
                    onClick={() => isEnt ? window.location.href = 'mailto:zitex.zx0@gmail.com' : checkout('subscription', plan.id, cycle)}
                    data-testid={`subscribe-${plan.id}-btn`}
                    className={`w-full py-3 rounded-lg font-bold transition ${
                      isFree
                        ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                        : highlight
                        ? 'bg-amber-500 text-zinc-900 hover:bg-amber-400'
                        : 'bg-zinc-800 text-white hover:bg-zinc-700'
                    }`}
                  >
                    {checkingOut === `subscription-${plan.id}`
                      ? 'جاري التحويل...'
                      : isFree ? 'الباقة الحالية'
                      : isEnt ? 'تواصل معنا'
                      : 'اشترك الآن'}
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {packs.map((pack) => (
              <div
                key={pack.id}
                data-testid={`pack-card-${pack.id}`}
                className={`relative bg-zinc-900 border rounded-2xl p-8 ${pack.popular ? 'border-amber-500 shadow-2xl shadow-amber-500/10' : 'border-zinc-800'}`}
              >
                {pack.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-500 text-zinc-900 px-3 py-1 rounded-full text-xs font-bold">
                    الأكثر طلباً
                  </div>
                )}
                <h3 className="text-2xl font-bold mb-1">{pack.name_ar}</h3>
                <div className="text-4xl font-bold text-amber-400 my-4">${pack.price_usd}</div>
                <div className="space-y-2 text-sm mb-6">
                  <div className="flex justify-between">
                    <span className="text-zinc-400">الشعلات:</span>
                    <span className="font-bold">{pack.credits.toLocaleString()}</span>
                  </div>
                  {pack.bonus_pct > 0 && (
                    <div className="flex justify-between text-emerald-400">
                      <span>بونص:</span>
                      <span className="font-bold">+{pack.bonus_pct}%</span>
                    </div>
                  )}
                </div>
                {pack.pay_later_eligible && (
                  <div className="mb-4 p-3 rounded-lg bg-blue-500/10 border border-blue-500/30 text-xs">
                    <div className="flex items-center gap-2 text-blue-300 font-bold mb-1">
                      <CreditCard className="w-3.5 h-3.5" /> أو 4 دفعات × ${(pack.price_usd / 4).toFixed(2)}
                    </div>
                    <div className="text-blue-200/80">بدون فوائد • PayPal • مدعومة في 🇺🇸 🇬🇧 🇪🇺 🇦🇺</div>
                  </div>
                )}
                <button
                  onClick={() => checkout('pack', pack.id)}
                  disabled={checkingOut === `pack-${pack.id}`}
                  data-testid={`buy-${pack.id}-btn`}
                  className="w-full py-3 bg-amber-500 text-zinc-900 rounded-lg font-bold hover:bg-amber-400 transition disabled:opacity-50"
                >
                  {checkingOut === `pack-${pack.id}` ? 'جاري التحويل...' : 'اشترِ الآن'}
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Trust strip */}
        <div className="mt-16 text-center">
          <div className="inline-flex flex-wrap justify-center gap-6 text-sm text-zinc-500">
            <div className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-400" /> دفع آمن عبر PayPal</div>
            <div className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-400" /> فاتورة PDF تلقائية</div>
            <div className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-400" /> +25% بونص لأول شحن</div>
            <div className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-400" /> إلغاء في أي وقت</div>
          </div>
        </div>
      </div>
    </div>
  );
}
