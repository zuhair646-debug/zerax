/**
 * Pricing — fully transparent page showing every cost the user can incur:
 *   • Subscription tiers (Free / Pro / Studio)
 *   • Per-action cost transparency (AI tokens, image gen, video gen)
 *   • Live "what does it cost today?" widget for logged-in users
 *
 * Click "ترقّي لـ Pro/Studio" → Stripe Checkout.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, Sparkles, ShieldCheck, ArrowLeft, Zap, Image, Video, ExternalLink, Crown, Flame } from 'lucide-react';
import { toast } from 'sonner';
import ZenrexBrand from '../components/ZenrexBrand';

const API = process.env.REACT_APP_BACKEND_URL;

const TIERS = [
  {
    id: 'project_pack',
    name: 'Project Pack',
    price: 49,
    originalPrice: 79,
    discountPct: 38,
    period: 'مرّة واحدة',
    cta: 'اشترِ مشروع واحد',
    badge: 'الأفضل لتجربة واحدة',
    perks: [
      'مشروع كامل واحد (موقع أو تطبيق)',
      'حتى 30 رسالة مع AI لإنهائه',
      '1 GB تخزين',
      '30 يوم لإكماله',
      'نشر فوري على نطاق فرعي مجاني',
      'دعم AI أثناء الإنشاء',
    ],
    color: 'cyan',
  },
  {
    id: 'tier_starter_monthly',
    name: 'Starter',
    price: 19,
    originalPrice: 29,
    discountPct: 35,
    period: 'شهرياً',
    cta: 'اشترك في Starter',
    perks: [
      '3 مشاريع شهرياً',
      '600,000 رمز AI يومياً',
      '1 GB تخزين',
      'تطبيق PWA مدمج',
      'نشر على نطاق Zenrex مجاني',
      'دعم بريد إلكتروني',
    ],
    color: 'emerald',
  },
  {
    id: 'tier_pro_monthly',
    name: 'Pro',
    price: 69,
    originalPrice: 99,
    discountPct: 30,
    period: 'شهرياً',
    cta: 'اشترك في Pro',
    badge: 'الأكثر شعبية',
    perks: [
      '12 مشروع شهرياً',
      '3,000,000 رمز AI يومياً',
      '5 GB تخزين',
      'Visual Guardian (مراجعة بصرية)',
      'دومين مخصص',
      'دعم واتساب أولوية',
      'تذكيرات + تقارير شهرية',
    ],
    color: 'amber',
    highlighted: true,
  },
  {
    id: 'tier_studio_monthly',
    name: 'Studio',
    price: 199,
    originalPrice: 299,
    discountPct: 33,
    period: 'شهرياً',
    cta: 'اشترك في Studio',
    badge: 'للوكالات والمحترفين',
    perks: [
      '60 مشروع شهرياً',
      '18,000,000 رمز AI يومياً',
      '50 GB تخزين',
      'تصدير كود + GitHub تلقائي',
      'كل ميزات Pro',
      'دعم فوري 24/7',
      'مدير حساب مخصص',
    ],
    color: 'purple',
  },
];

const TRANSPARENCY = [
  { icon: Zap,   label: 'محادثة AI', cost: '≈ $0.05 - $0.10 لكل رسالة (يعتمد على الطول)' },
  { icon: Image, label: 'توليد صورة', cost: '≈ $0.02 لكل صورة 1024×1024' },
  { icon: Video, label: 'توليد فيديو 10 ثوانٍ', cost: '≈ $0.40 لكل فيديو (يستهلك credits)' },
  { icon: Sparkles, label: 'فحص موقع (محوّل)', cost: 'مجاني — لا يستهلك tokens' },
];

function TierCard({ tier, onUpgrade, currentTier }) {
  const styles = {
    zinc:    { border: 'border-zinc-700', bg: 'bg-zinc-950', accent: 'text-zinc-300', btn: 'bg-zinc-800 text-zinc-300' },
    cyan:    { border: 'border-cyan-500/40', bg: 'bg-gradient-to-br from-cyan-500/10 to-blue-500/5', accent: 'text-cyan-300', btn: 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white' },
    emerald: { border: 'border-emerald-500/40', bg: 'bg-gradient-to-br from-emerald-500/10 to-teal-500/5', accent: 'text-emerald-300', btn: 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white' },
    amber:   { border: 'border-amber-500/60', bg: 'bg-gradient-to-br from-amber-500/15 to-yellow-500/5', accent: 'text-amber-300', btn: 'bg-gradient-to-r from-amber-400 to-yellow-500 text-black' },
    purple:  { border: 'border-purple-500/40', bg: 'bg-gradient-to-br from-purple-500/10 to-fuchsia-500/5', accent: 'text-purple-300', btn: 'bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white' },
  };
  const s = styles[tier.color] || styles.zinc;
  const tierKey = tier.id.replace('tier_', '').replace('_monthly', '');
  const isCurrent = currentTier === tierKey;
  return (
    <div
      data-testid={`tier-${tier.id}`}
      className={`relative rounded-2xl border ${s.border} ${s.bg} p-6 ${tier.highlighted ? 'ring-2 ring-amber-500/40 scale-[1.02]' : ''}`}
    >
      {tier.badge && (
        <div className={`absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-black px-3 py-1 rounded-full whitespace-nowrap ${tier.highlighted ? 'bg-amber-400 text-black' : 'bg-zinc-800 text-zinc-300 border border-zinc-700'}`}>
          {tier.badge}
        </div>
      )}
      <h3 className={`text-xl font-black ${s.accent} mb-1`}>{tier.name}</h3>
      {/* Price block with strikethrough launch promo */}
      <div className="mb-1">
        {tier.originalPrice && (
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm text-zinc-500 line-through">${tier.originalPrice}</span>
            <span className="text-[10px] font-black px-1.5 py-0.5 rounded-md bg-rose-500/20 border border-rose-500/40 text-rose-300">
              -{tier.discountPct}% خصم الإطلاق
            </span>
          </div>
        )}
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-black">${tier.price}</span>
          {tier.period && <span className="text-xs text-zinc-500"> · {tier.period}</span>}
        </div>
        {tier.originalPrice && (
          <p className="text-[10px] text-emerald-400 font-bold mt-1">
            توفير ${tier.originalPrice - tier.price}{tier.period === 'شهرياً' ? ' كل شهر' : ''}
          </p>
        )}
      </div>
      <ul className="space-y-2 mb-6 mt-3">
        {tier.perks.map((p, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-zinc-200">
            <Check className={`w-4 h-4 ${s.accent} flex-shrink-0 mt-0.5`} />
            <span>{p}</span>
          </li>
        ))}
      </ul>
      {isCurrent ? (
        <button disabled className="w-full px-4 py-3 rounded-xl bg-zinc-800 text-zinc-500 text-sm font-black cursor-not-allowed">
          ✓ الباقة الحالية
        </button>
      ) : (
        <button
          onClick={() => onUpgrade(tier.id)}
          data-testid={`upgrade-${tier.id}`}
          className={`w-full px-4 py-3 rounded-xl text-sm font-black ${s.btn} hover:opacity-90 transition`}
        >
          {tier.cta}
        </button>
      )}
    </div>
  );
}

export default function Pricing() {
  const navigate = useNavigate();
  const [usage, setUsage] = useState(null);
  const [busy, setBusy] = useState(null);
  const isAuthed = !!localStorage.getItem('token');

  useEffect(() => {
    if (!isAuthed) return;
    fetch(`${API}/api/usage/me`, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
      .then((r) => (r.ok ? r.json() : null))
      .then(setUsage)
      .catch(() => {});
  }, [isAuthed]);

  const upgrade = async (packageId) => {
    if (!isAuthed) { navigate('/login?return=/pricing'); return; }
    setBusy(packageId);
    try {
      const r = await fetch(`${API}/api/billing/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token')}` },
        body: JSON.stringify({ package_id: packageId, origin_url: window.location.origin }),
      });
      const d = await r.json();
      if (!r.ok || !d.url) {
        toast.error(d.detail || 'فشل إنشاء جلسة الدفع');
        return;
      }
      window.location.href = d.url;
    } catch (e) {
      toast.error('فشل الاتصال بالخادم');
    } finally {
      setBusy(null);
    }
  };

  const currentTier = (usage?.quota?.reason === 'admin') ? 'admin'
                    : (usage ? (
                        usage.quota.cap >= 18_000_000 ? 'studio' :
                        usage.quota.cap >= 3_000_000 ? 'pro' :
                        usage.quota.cap >= 600_000 ? 'starter' : 'free'
                      ) : 'free');

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" dir="rtl" data-testid="pricing-page">
      <header className="sticky top-0 z-30 border-b border-white/10 bg-zinc-950/85 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <a href="/" className="hover:opacity-90"><ZenrexBrand size={26} /></a>
          <a href="/freebuild/chat" className="inline-flex items-center gap-1.5 text-zinc-400 hover:text-zinc-200 text-sm">
            <ArrowLeft className="w-4 h-4" /> رجوع
          </a>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-l from-rose-500/20 via-amber-500/20 to-rose-500/20 border border-rose-500/40 text-rose-200 text-xs mb-4 animate-pulse" data-testid="launch-promo-banner">
            <Flame className="w-4 h-4" />
            <span className="font-black">🔥 عرض الإطلاق — خصومات حتى 38% لفترة محدودة</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs mb-4">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>شفافية كاملة في الأسعار</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black mb-2">باقات Zenrex AI</h1>
          <p className="text-zinc-400 max-w-2xl mx-auto text-sm">
            ادفع شهرياً فقط. لا رسوم خفية. لا التزام طويل. ألغِ في أي وقت.
          </p>
        </div>

        {/* Live usage banner for logged-in users */}
        {usage && usage.quota?.reason !== 'admin' && (
          <div data-testid="live-usage-banner" className="mb-8 rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 flex items-center justify-between flex-wrap gap-3">
            <div>
              <p className="text-xs text-amber-300 font-bold mb-1">استهلاكك اليوم</p>
              <p className="text-sm">
                <span className="text-2xl font-black text-amber-200">${usage.today.cost_usd.toFixed(3)}</span>
                <span className="text-zinc-400 mx-2">•</span>
                <span className="text-zinc-300">{((usage.today.tokens_in||0)+(usage.today.tokens_out||0)).toLocaleString()} رمز</span>
                <span className="text-zinc-400 mx-2">•</span>
                <span className="text-zinc-300">{usage.today.calls} طلب</span>
              </p>
            </div>
            <div className="text-xs text-zinc-400">
              متبقي: <b className="text-emerald-300">{(usage.quota.cap - usage.quota.used).toLocaleString()}</b> رمز اليوم
            </div>
          </div>
        )}

        {/* Tier cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-12">
          {TIERS.map((t) => (
            <TierCard key={t.id} tier={t} onUpgrade={upgrade} currentTier={currentTier} />
          ))}
        </div>

        {/* Cost transparency */}
        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6 mb-8" data-testid="transparency-section">
          <h2 className="text-lg font-black mb-1 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            شفافية التكاليف الفعلية
          </h2>
          <p className="text-xs text-zinc-400 mb-4">هذي تكاليفنا الفعلية على كل عملية — نعرضها لك بدون رتوش.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {TRANSPARENCY.map((t, i) => {
              const Icon = t.icon;
              return (
                <div key={i} className="flex items-start gap-3 p-3 rounded-xl border border-zinc-800 bg-black/30">
                  <Icon className="w-5 h-5 text-amber-300 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="text-sm font-bold text-zinc-200">{t.label}</div>
                    <div className="text-xs text-zinc-400 mt-0.5">{t.cost}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <p className="text-center text-xs text-zinc-500">
          مدفوعات آمنة عبر Stripe · لا نخزّن بيانات بطاقتك أبداً · ضمان استرداد خلال 7 أيام لو ما استخدمت الميزات المدفوعة
        </p>
      </main>
    </div>
  );
}
