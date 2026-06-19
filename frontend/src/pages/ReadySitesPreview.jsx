/**
 * Ready Sites — Step 1.5: Category Preview & Feature Showcase
 *
 * Sits between /ready-sites (category picker) and /ready-sites/purchase
 * (buy / trial). Shows the customer EXACTLY what they're about to buy:
 *
 *   1. Live preview gallery of the 25 ready templates for the category
 *      (rendered from /api/websites/categories/{id}/layouts-gallery as a
 *       single iframe — this is the same official renderer the production
 *       sites use, so what they see here = what they will own).
 *   2. Feature highlights (the full Zenrex package: domain, payments,
 *      PWA app, AI editor, etc.).
 *   3. CTA → continue to purchase / trial.
 *
 * This page is intentionally video-like in feel (auto-rotating featured
 * template + cinematic background) without needing an actual video file.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, Sparkles, Check, Globe, ShieldCheck,
  Smartphone, CreditCard, Bot, Search, ImageIcon, Crown, Loader2,
} from 'lucide-react';
import ZenrexBrand from '../components/ZenrexBrand';
import UsageIndicator from '../components/UsageIndicator';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORY_META = {
  restaurants: { title: 'مطاعم وكافيهات',     emoji: '🍔', accent: 'from-orange-500 via-rose-500 to-amber-500' },
  electronics: { title: 'إلكترونيات وتقنية',  emoji: '📱', accent: 'from-cyan-500 via-blue-500 to-indigo-500' },
  stationery:  { title: 'قرطاسيات ومكتبات',   emoji: '📚', accent: 'from-amber-500 via-orange-500 to-yellow-500' },
  grocery:     { title: 'بقالات وسوبرماركت',  emoji: '🛒', accent: 'from-green-500 via-emerald-500 to-teal-500' },
  pharmacy:    { title: 'صيدليات',           emoji: '💊', accent: 'from-teal-500 via-cyan-500 to-emerald-500' },
  fashion:     { title: 'أزياء وموضة',       emoji: '👗', accent: 'from-pink-500 via-fuchsia-500 to-rose-500' },
  beauty:      { title: 'تجميل وعطور',       emoji: '💄', accent: 'from-rose-500 via-pink-500 to-fuchsia-500' },
  flowers:     { title: 'زهور وهدايا',       emoji: '💐', accent: 'from-violet-500 via-purple-500 to-pink-500' },
};

const FEATURES = [
  { icon: Globe,       title: 'دومين مخصص',         desc: 'سنة كاملة مع SSL آمن وسرعة عالمية', accent: 'emerald' },
  { icon: Smartphone,  title: 'تطبيق جوال PWA',     desc: 'يتثبّت على iPhone و Android بدون متجر',  accent: 'purple' },
  { icon: CreditCard,  title: 'بوابات دفع',         desc: 'Mada, Apple Pay, STC Pay, Visa, Mastercard', accent: 'amber' },
  { icon: Bot,         title: 'محرّر AI داخل الموقع', desc: 'عدّل النصوص والألوان بأمر صوتي/نصي',     accent: 'cyan' },
  { icon: Search,      title: 'SEO جاهز',            desc: 'تظهر في جوجل مع Schema + Sitemap',      accent: 'rose' },
  { icon: ImageIcon,   title: 'صور احترافية',         desc: 'مكتبة صور مرخّصة لتخصصك مدمجة',          accent: 'blue' },
  { icon: ShieldCheck, title: 'دعم AI شامل',         desc: '6 أشهر صيانة وتحديثات تلقائية',          accent: 'green' },
  { icon: Crown,       title: 'ملكية كاملة',         desc: 'الموقع باسمك — انقله متى تشاء',          accent: 'amber' },
];

const ACCENT_MAP = {
  emerald: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
  purple:  'bg-purple-500/10 border-purple-500/30 text-purple-300',
  amber:   'bg-amber-500/10 border-amber-500/30 text-amber-300',
  cyan:    'bg-cyan-500/10 border-cyan-500/30 text-cyan-300',
  rose:    'bg-rose-500/10 border-rose-500/30 text-rose-300',
  blue:    'bg-blue-500/10 border-blue-500/30 text-blue-300',
  green:   'bg-green-500/10 border-green-500/30 text-green-300',
};

export default function ReadySitesPreview({ user }) {
  const navigate = useNavigate();
  const params = useParams();
  const categoryId = params.id || params.category || 'restaurants';
  const meta = CATEGORY_META[categoryId] || CATEGORY_META.restaurants;

  const [layouts, setLayouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [featured, setFeatured] = useState(0);

  // Fetch the official layouts list from the website renderer.
  useEffect(() => {
    setLoading(true);
    fetch(`${API}/api/websites/categories/${categoryId}/layouts`)
      .then((r) => (r.ok ? r.json() : { layouts: [] }))
      .then((d) => setLayouts(d.layouts || d.items || []))
      .catch(() => setLayouts([]))
      .finally(() => setLoading(false));
  }, [categoryId]);

  // Auto-rotate the big featured preview every 6s (video-like cadence).
  useEffect(() => {
    if (layouts.length < 2) return;
    const t = setInterval(() => {
      setFeatured((i) => (i + 1) % Math.min(layouts.length, 12));
    }, 6000);
    return () => clearInterval(t);
  }, [layouts.length]);

  const galleryUrl = useMemo(
    () => `${API}/api/websites/categories/${categoryId}/layouts-gallery`,
    [categoryId],
  );

  const continueToPurchase = () => {
    navigate(`/ready-sites/purchase?category=${categoryId}`);
  };

  const featuredLayout = layouts[featured];
  const featuredPreviewUrl = featuredLayout
    ? `${API}/api/websites/categories/${categoryId}/layouts/${featuredLayout.id}/preview-html-raw`
    : null;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" dir="rtl" data-testid="ready-sites-preview">
      {/* Sticky header */}
      <header className="sticky top-0 z-30 border-b border-white/10 bg-zinc-950/85 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <a href="/" className="hover:opacity-90 shrink-0"><ZenrexBrand size={26} /></a>
            <span className="text-zinc-600 hidden sm:inline">•</span>
            <button
              onClick={() => navigate('/ready-sites')}
              className="inline-flex items-center gap-1 text-zinc-400 hover:text-zinc-200 text-xs"
            >
              <ArrowRight className="w-4 h-4" />
              <span className="hidden sm:inline">المواقع الجاهزة</span>
            </button>
            <span className="text-zinc-600 hidden sm:inline">›</span>
            <span className="text-sm font-bold text-amber-300 truncate">{meta.emoji} {meta.title}</span>
          </div>
          <div className="flex items-center gap-2">
            <UsageIndicator compact />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Hero — featured live preview */}
        <section className="relative mb-12 rounded-3xl overflow-hidden border border-amber-500/20 bg-zinc-900" data-testid="hero-section">
          <div className={`absolute inset-0 bg-gradient-to-br ${meta.accent} opacity-10`} />
          <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-6 p-6 sm:p-10">
            {/* Left: copy */}
            <div className="space-y-5">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] font-bold">
                <Sparkles className="w-3.5 h-3.5" />
                <span>{layouts.length} قالب جاهز للاختيار</span>
              </div>
              <h1 className="text-3xl sm:text-5xl font-black leading-tight">
                موقع <span className={`bg-gradient-to-l ${meta.accent} bg-clip-text text-transparent`}>{meta.title}</span>
                <br/>جاهز في 5 دقائق
              </h1>
              <p className="text-sm sm:text-base text-zinc-300 leading-relaxed max-w-xl">
                اختر القالب → ضع اسمك ولوغوك → موقعك يصير حقيقي على الإنترنت.
                كل التفاصيل التقنية (الدومين، الاستضافة، الدفع، التطبيق، SEO) جاهزة بانتظارك.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={continueToPurchase}
                  data-testid="continue-to-purchase"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-l from-amber-400 to-yellow-500 hover:from-amber-300 hover:to-yellow-400 text-black font-black text-sm shadow-lg shadow-amber-500/30 transition"
                >
                  <span>اعرض خيارات الشراء</span>
                  <ArrowLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => document.getElementById('gallery')?.scrollIntoView({ behavior: 'smooth' })}
                  data-testid="explore-gallery"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-200 text-sm font-bold transition"
                >
                  استعرض الـ{layouts.length} قالب
                </button>
              </div>
              {/* Tier strip */}
              <div className="flex items-center gap-4 text-xs text-zinc-400 pt-3 border-t border-white/5">
                <span className="flex items-center gap-1"><Check className="w-3.5 h-3.5 text-emerald-400" /> شراء مباشر</span>
                <span className="flex items-center gap-1"><Check className="w-3.5 h-3.5 text-emerald-400" /> أو تجربة مدفوعة</span>
                <span className="flex items-center gap-1"><Check className="w-3.5 h-3.5 text-emerald-400" /> استرداد خلال 7 أيام</span>
              </div>
            </div>

            {/* Right: live featured preview (auto-rotating) */}
            <div className="relative">
              <div className="aspect-[4/3] rounded-2xl overflow-hidden bg-zinc-950 border border-white/10 shadow-2xl shadow-black/50">
                {loading || !featuredPreviewUrl ? (
                  <div className="w-full h-full flex items-center justify-center">
                    <Loader2 className="w-7 h-7 animate-spin text-amber-400" />
                  </div>
                ) : (
                  <iframe
                    key={featured}
                    src={featuredPreviewUrl}
                    title={featuredLayout?.name}
                    loading="lazy"
                    sandbox="allow-same-origin"
                    className="w-full h-full bg-white"
                    style={{ pointerEvents: 'none' }}
                    data-testid="hero-preview-iframe"
                  />
                )}
              </div>
              {featuredLayout && (
                <div className="absolute bottom-3 right-3 left-3 sm:right-auto sm:left-auto sm:bottom-4 sm:right-4 bg-black/85 backdrop-blur-md border border-white/15 rounded-xl px-3 py-2 text-xs flex items-center gap-2">
                  <span className="text-amber-400 font-black">#{featured + 1}</span>
                  <span className="text-zinc-200 font-bold truncate">{featuredLayout.name}</span>
                </div>
              )}
              <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 flex gap-1">
                {layouts.slice(0, 6).map((_, i) => (
                  <span
                    key={i}
                    className={`h-1.5 rounded-full transition-all ${i === featured % 6 ? 'w-6 bg-amber-400' : 'w-1.5 bg-zinc-700'}`}
                  />
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Features grid */}
        <section className="mb-12" data-testid="features-section">
          <h2 className="text-2xl font-black mb-2 text-center">كل شي مدمج في الموقع</h2>
          <p className="text-sm text-zinc-400 text-center mb-8">ما تحتاج تشتري أي إضافة — كل شي شامل في السعر</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {FEATURES.map((f, i) => {
              const Icon = f.icon;
              return (
                <div
                  key={i}
                  data-testid={`feature-${i}`}
                  className={`p-4 rounded-2xl border ${ACCENT_MAP[f.accent]} backdrop-blur transition hover:scale-[1.02]`}
                >
                  <Icon className="w-6 h-6 mb-2" />
                  <h3 className="font-black text-sm mb-1 text-white">{f.title}</h3>
                  <p className="text-[11px] opacity-80 leading-relaxed">{f.desc}</p>
                </div>
              );
            })}
          </div>
        </section>

        {/* Gallery — embedded official layouts-gallery iframe */}
        <section id="gallery" className="mb-12" data-testid="gallery-section">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div>
              <h2 className="text-2xl font-black">معرض القوالب الـ{layouts.length}</h2>
              <p className="text-xs text-zinc-400">كل قالب تستطيع تخصيصه كاملاً بعد الشراء</p>
            </div>
            <span className="text-[11px] text-zinc-500">يتم تحميل المعاينة الحية في الإطار التالي</span>
          </div>
          <div className="rounded-2xl overflow-hidden border border-white/10 bg-black/40 shadow-inner" style={{ height: '720px' }}>
            <iframe
              src={galleryUrl}
              title={`معرض قوالب ${meta.title}`}
              className="w-full h-full"
              data-testid="gallery-iframe"
              loading="lazy"
              sandbox="allow-same-origin"
            />
          </div>
        </section>

        {/* Bottom CTA */}
        <section className={`rounded-3xl overflow-hidden border border-amber-500/30 p-8 sm:p-12 text-center bg-gradient-to-br ${meta.accent} bg-opacity-10`} data-testid="bottom-cta">
          <h2 className="text-2xl sm:text-3xl font-black mb-3">جاهز تبدأ {meta.title}؟</h2>
          <p className="text-sm text-zinc-200/90 mb-6 max-w-2xl mx-auto">
            اضغط الزر تحت لاختيار الباقة المناسبة (شراء مباشر أو تجربة مدفوعة) —
            بعد الدفع، يفتح لك زنركس AI ويسألك بس عن اسم متجرك ولوغو.
          </p>
          <button
            onClick={continueToPurchase}
            data-testid="bottom-cta-btn"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl bg-amber-400 hover:bg-amber-300 text-black font-black text-base shadow-2xl shadow-amber-500/40 transition"
          >
            <span>اختر باقتك واشترِ</span>
            <ArrowLeft className="w-5 h-5" />
          </button>
        </section>
      </main>
    </div>
  );
}
