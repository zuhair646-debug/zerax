/**
 * 💎 IndependenceLanding — Premium landing page for the $799 tier.
 *
 * Tells the customer in a single scroll:
 *   1. What they get vs. competitors (Lovable, Bolt, v0).
 *   2. The 4-step journey (Discovery → Build → Backend → Independence).
 *   3. What's literally in the ZIP (24 files visualization).
 *   4. Honest pricing with all 4 tiers compared side-by-side.
 *   5. Single CTA — start building.
 *
 * Design language: dark navy + fuchsia/purple gradient accents,
 * IBM Plex Arabic for headings, asymmetric layout, micro-animations.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles, Check, X, Download, Github, Rocket, Code, Database,
  Lock, Shield, ArrowLeft, FileCode, Crown, Zap, Globe, Server,
  PlayCircle, Cpu, GitBranch, Award,
} from 'lucide-react';

const TIERS = [
  {
    id: 'free',
    name: 'استضافة Zenrex',
    price: 'مجاناً',
    sub: 'سنستضيف موقعك',
    color: 'emerald',
    features: [
      { ok: true, t: 'موقع HTML/CSS/JS كامل' },
      { ok: true, t: 'استضافة على سيرفرات Zenrex' },
      { ok: true, t: 'دومين فرعي zenrex.ai/yourname' },
      { ok: false, t: 'لا تملك الكود' },
      { ok: false, t: 'لا backend' },
      { ok: false, t: 'لا VPS مستقل' },
    ],
  },
  {
    id: 'code',
    name: 'الكود فقط',
    price: '$79',
    sub: 'تنشره بنفسك',
    color: 'cyan',
    features: [
      { ok: true, t: 'كل ملفات HTML/CSS/JS' },
      { ok: true, t: 'صور بحجم Production' },
      { ok: true, t: 'README بتعليمات النشر' },
      { ok: false, t: 'بدون إرشاد للنشر' },
      { ok: false, t: 'لا backend' },
      { ok: false, t: 'لا CI/CD' },
    ],
  },
  {
    id: 'guided',
    name: 'الكود + إرشاد',
    price: '$199',
    sub: 'AI يمشي معك خطوة بخطوة',
    color: 'amber',
    popular: true,
    features: [
      { ok: true, t: 'كل اللي بالباقة السابقة' },
      { ok: true, t: 'الذكاء يربط GitHub repo' },
      { ok: true, t: 'يدفع لـVercel + Cloudflare' },
      { ok: true, t: 'دعم 30 يوم على الكود' },
      { ok: false, t: 'لا backend' },
      { ok: false, t: 'لا VPS مستقل' },
    ],
  },
  {
    id: 'independence',
    name: 'الاستقلال الكامل',
    price: '$799',
    sub: 'تطبيق full-stack مع نقل ملكية كاملة',
    color: 'fuchsia',
    flagship: true,
    features: [
      { ok: true, t: 'Frontend + Backend FastAPI + MongoDB' },
      { ok: true, t: 'JWT Auth (register/login/me)' },
      { ok: true, t: 'CRUD APIs لكل entity' },
      { ok: true, t: 'GitHub Actions CI/CD' },
      { ok: true, t: 'One-click نشر على Hetzner VPS' },
      { ok: true, t: 'نقل ملكية GitHub repo' },
      { ok: true, t: 'ARCHITECTURE.md (5+ صفحات بالعربي)' },
      { ok: true, t: 'خطاب تسليم رسمي + 60 يوم دعم' },
    ],
  },
];

const KIT_FILES = [
  { name: 'index.html', icon: Globe, group: 'frontend' },
  { name: 'Dockerfile', icon: Server, group: 'devops' },
  { name: 'docker-compose.yml', icon: Server, group: 'devops' },
  { name: 'nginx.conf', icon: Shield, group: 'devops' },
  { name: 'deploy.sh', icon: Rocket, group: 'devops' },
  { name: 'ARCHITECTURE.md', icon: FileCode, group: 'docs' },
  { name: 'HANDOVER.md', icon: Award, group: 'docs' },
  { name: 'README.md', icon: FileCode, group: 'docs' },
  { name: 'LICENSE (MIT)', icon: Award, group: 'docs' },
  { name: '.gitignore', icon: FileCode, group: 'docs' },
  { name: 'SECRETS.template.env', icon: Lock, group: 'docs' },
  { name: 'api/Dockerfile.api', icon: Server, group: 'backend' },
  { name: 'api/requirements.txt', icon: Code, group: 'backend' },
  { name: 'api/app/server.py', icon: Code, group: 'backend' },
  { name: 'api/app/models.py', icon: Database, group: 'backend' },
  { name: 'api/app/db.py', icon: Database, group: 'backend' },
  { name: 'api/app/auth.py', icon: Lock, group: 'backend' },
  { name: 'api/app/routes/<entity>.py', icon: Code, group: 'backend' },
  { name: 'api/README.md', icon: FileCode, group: 'backend' },
  { name: '.env.example', icon: Lock, group: 'backend' },
  { name: '.github/workflows/deploy.yml', icon: GitBranch, group: 'cicd' },
];

const GROUP_META = {
  frontend: { label: 'Frontend', color: 'cyan' },
  backend: { label: 'Backend', color: 'emerald' },
  devops: { label: 'DevOps', color: 'fuchsia' },
  docs: { label: 'Docs', color: 'amber' },
  cicd: { label: 'CI/CD', color: 'purple' },
};

function TierCard({ tier, onCta }) {
  const isFlag = tier.flagship;
  return (
    <div
      data-testid={`tier-card-${tier.id}`}
      className={`relative rounded-2xl border p-6 flex flex-col transition-all duration-300 hover:translate-y-[-4px] ${
        isFlag
          ? 'border-fuchsia-400/50 bg-gradient-to-br from-fuchsia-900/40 via-purple-900/30 to-zinc-950 shadow-2xl shadow-fuchsia-500/20'
          : tier.popular
          ? 'border-amber-400/40 bg-gradient-to-br from-amber-900/20 to-zinc-950'
          : 'border-white/10 bg-zinc-950/80'
      }`}
    >
      {isFlag && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white text-[10px] font-black flex items-center gap-1 whitespace-nowrap shadow-lg">
          <Crown className="w-3 h-3" /> الأقوى
        </div>
      )}
      {tier.popular && !isFlag && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-amber-500 text-black text-[10px] font-black whitespace-nowrap shadow-lg">
          ✨ الأكثر طلباً
        </div>
      )}
      <h3 className="text-lg font-black text-white mb-1">{tier.name}</h3>
      <p className="text-[11px] text-zinc-400 mb-4 leading-relaxed">{tier.sub}</p>
      <div className="flex items-baseline gap-1 mb-5">
        <span className={`text-4xl font-black ${
          isFlag ? 'bg-gradient-to-r from-fuchsia-300 to-purple-300 bg-clip-text text-transparent' :
          tier.popular ? 'text-amber-300' :
          tier.id === 'free' ? 'text-emerald-300' : 'text-cyan-300'
        }`}>{tier.price}</span>
        {tier.id !== 'free' && <span className="text-zinc-500 text-xs">/ مرة واحدة</span>}
      </div>
      <ul className="space-y-2 mb-6 flex-1">
        {tier.features.map((f, i) => (
          <li key={i} className={`flex items-start gap-2 text-[12px] leading-relaxed ${
            f.ok ? 'text-zinc-200' : 'text-zinc-600 line-through'
          }`}>
            {f.ok
              ? <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
              : <X className="w-3.5 h-3.5 text-zinc-700 shrink-0 mt-0.5" />}
            <span>{f.t}</span>
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => onCta(tier.id)}
        data-testid={`tier-cta-${tier.id}`}
        className={`w-full py-2.5 rounded-lg font-black text-sm transition-all ${
          isFlag
            ? 'bg-gradient-to-r from-fuchsia-500 via-purple-500 to-violet-600 hover:from-fuchsia-400 hover:to-violet-500 text-white shadow-lg shadow-fuchsia-500/30'
            : tier.popular
            ? 'bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-black'
            : tier.id === 'free'
            ? 'bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-black'
            : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black'
        }`}
      >
        ابدأ
      </button>
    </div>
  );
}

function StepCard({ num, icon: Icon, title, body, accent = 'cyan' }) {
  const colors = {
    cyan:    { grad: 'from-cyan-500 to-sky-600',         shadow: 'shadow-cyan-500/30',    border: 'border-cyan-500/30' },
    fuchsia: { grad: 'from-fuchsia-500 to-purple-600',   shadow: 'shadow-fuchsia-500/30', border: 'border-fuchsia-500/30' },
    emerald: { grad: 'from-emerald-500 to-teal-600',     shadow: 'shadow-emerald-500/30', border: 'border-emerald-500/30' },
    amber:   { grad: 'from-amber-500 to-orange-600',     shadow: 'shadow-amber-500/30',   border: 'border-amber-500/30' },
  }[accent] || { grad: 'from-cyan-500 to-sky-600', shadow: 'shadow-cyan-500/30', border: 'border-cyan-500/30' };
  return (
    <div className={`relative rounded-xl border ${colors.border} bg-gradient-to-br from-zinc-950 to-zinc-900 p-5`}>
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${colors.grad} ${colors.shadow} flex items-center justify-center shadow-lg`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="text-[10px] text-zinc-500 font-bold">المرحلة {num}</div>
          <h4 className="text-base font-black text-white">{title}</h4>
        </div>
      </div>
      <p className="text-[12px] text-zinc-300 leading-relaxed">{body}</p>
    </div>
  );
}

function KitFileChip({ file }) {
  const Icon = file.icon;
  const colorMap = {
    cyan: 'border-cyan-500/30 text-cyan-200 bg-cyan-500/5',
    emerald: 'border-emerald-500/30 text-emerald-200 bg-emerald-500/5',
    fuchsia: 'border-fuchsia-500/30 text-fuchsia-200 bg-fuchsia-500/5',
    amber: 'border-amber-500/30 text-amber-200 bg-amber-500/5',
    purple: 'border-purple-500/30 text-purple-200 bg-purple-500/5',
  };
  const groupColor = colorMap[GROUP_META[file.group]?.color] || colorMap.cyan;
  return (
    <div className={`flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-[11px] font-mono ${groupColor}`}>
      <Icon className="w-3 h-3 shrink-0" />
      <span className="truncate">{file.name}</span>
    </div>
  );
}

export default function IndependenceLanding() {
  const navigate = useNavigate();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    document.title = '💎 الاستقلال الكامل — Zenrex';
    setVisible(true);
  }, []);

  const handleCta = (tierId) => {
    // For now: send everyone to the builder. Stripe checkout for the
    // paid tiers happens inside the chat at the finalize step.
    if (tierId === 'independence') {
      navigate('/freebuild/chat?tier=full_independence');
    } else {
      navigate('/freebuild/chat');
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white" dir="rtl" data-testid="independence-landing">
      {/* Grain texture overlay */}
      <div
        className="fixed inset-0 opacity-[0.025] pointer-events-none mix-blend-overlay"
        style={{ backgroundImage: 'url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIj48ZmlsdGVyIGlkPSJuIj48ZmVUdXJidWxlbmNlIHR5cGU9ImZyYWN0YWxOb2lzZSIgYmFzZUZyZXF1ZW5jeT0iMC44IiBzdGl0Y2hUaWxlcz0ic3RpdGNoIi8+PC9maWx0ZXI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsdGVyPSJ1cmwoI24pIi8+PC9zdmc+")' }}
      />

      {/* Top nav */}
      <nav className="relative z-10 max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate('/')}
          data-testid="back-home-btn"
          className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          الرئيسية
        </button>
        <div className="text-sm font-black bg-gradient-to-r from-fuchsia-300 to-purple-300 bg-clip-text text-transparent">
          💎 Zenrex Independence
        </div>
      </nav>

      {/* HERO */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pt-12 pb-20">
        <div className={`grid lg:grid-cols-12 gap-10 items-center transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-fuchsia-500/15 border border-fuchsia-500/30 mb-6">
              <Sparkles className="w-3.5 h-3.5 text-fuchsia-300" />
              <span className="text-xs font-bold text-fuchsia-200">جديد · باقة الاستقلال الكامل</span>
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black leading-tight mb-6">
              من فكرة في رأسك
              <br />
              إلى <span className="bg-gradient-to-r from-fuchsia-400 via-purple-400 to-violet-400 bg-clip-text text-transparent">تطبيق مستقل</span>
              <br />
              في <span className="text-cyan-300">جلسة واحدة</span>.
            </h1>
            <p className="text-base sm:text-lg text-zinc-300 leading-relaxed mb-8 max-w-2xl">
              بدون اشتراك شهري. بدون قيود. بدون الاعتماد علينا.
              <br />
              <span className="text-fuchsia-200 font-bold">Frontend + Backend FastAPI + MongoDB + JWT + CI/CD</span> — كل شيء بإيدك على VPS خاص بك، بـ GitHub باسمك.
            </p>
            <div className="flex flex-wrap items-center gap-3 mb-8">
              <button
                type="button"
                onClick={() => handleCta('independence')}
                data-testid="hero-cta-primary"
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-fuchsia-500 via-purple-500 to-violet-600 hover:from-fuchsia-400 hover:to-violet-500 text-white font-black text-sm shadow-xl shadow-fuchsia-500/30 transition-all hover:scale-105 flex items-center gap-2"
              >
                <Rocket className="w-4 h-4" />
                ابدأ الآن — $799 مرة واحدة
              </button>
              <button
                type="button"
                onClick={() => {
                  const el = document.getElementById('how-it-works');
                  if (el) el.scrollIntoView({ behavior: 'smooth' });
                }}
                data-testid="hero-cta-secondary"
                className="px-6 py-3 rounded-xl border border-white/20 hover:border-fuchsia-400/50 hover:bg-fuchsia-500/10 text-white font-bold text-sm flex items-center gap-2 transition-all"
              >
                <PlayCircle className="w-4 h-4" />
                كيف يشتغل؟
              </button>
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-[11px] text-zinc-500">
              <span className="flex items-center gap-1"><Check className="w-3 h-3 text-emerald-400" /> ملكية كاملة للكود</span>
              <span className="flex items-center gap-1"><Check className="w-3 h-3 text-emerald-400" /> 24 ملف بالـZIP</span>
              <span className="flex items-center gap-1"><Check className="w-3 h-3 text-emerald-400" /> 60 يوم دعم</span>
              <span className="flex items-center gap-1"><Check className="w-3 h-3 text-emerald-400" /> رخصة MIT</span>
            </div>
          </div>

          {/* Right column — terminal mockup */}
          <div className="lg:col-span-5">
            <div className="rounded-2xl border border-white/10 bg-zinc-900/80 backdrop-blur-xl overflow-hidden shadow-2xl shadow-purple-500/10">
              <div className="flex items-center gap-2 px-4 py-3 bg-zinc-950 border-b border-white/5">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
                </div>
                <span className="ml-3 text-[11px] text-zinc-500 font-mono">zenrex-independence-kit.zip</span>
              </div>
              <div className="p-5 font-mono text-[11px] space-y-1.5 leading-relaxed">
                <div className="text-zinc-500">$ unzip zenrex-independence-my-app.zip</div>
                <div className="text-emerald-400">  ✓ index.html</div>
                <div className="text-fuchsia-300">  ✓ Dockerfile + nginx.conf + deploy.sh</div>
                <div className="text-cyan-300">  ✓ api/app/server.py (FastAPI)</div>
                <div className="text-cyan-300">  ✓ api/app/models.py (Pydantic)</div>
                <div className="text-cyan-300">  ✓ api/app/auth.py (JWT)</div>
                <div className="text-cyan-300">  ✓ api/app/routes/movies.py (CRUD)</div>
                <div className="text-amber-300">  ✓ ARCHITECTURE.md (5+ pages)</div>
                <div className="text-amber-300">  ✓ HANDOVER.md (formal delivery)</div>
                <div className="text-purple-300">  ✓ .github/workflows/deploy.yml</div>
                <div className="text-zinc-500 mt-2">$ ./deploy.sh yourdomain.com</div>
                <div className="text-emerald-300">🚀 Deployed at https://yourdomain.com</div>
                <div className="text-zinc-500 mt-2">$ git remote -v</div>
                <div className="text-zinc-300">origin  git@github.com:<span className="text-fuchsia-300 font-bold">yourname</span>/my-app.git</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* WHY DIFFERENT — comparison strip */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-12 border-y border-white/5">
        <div className="text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-black text-white mb-3">
            لِم Zenrex Independence <span className="text-fuchsia-300">مختلف</span>؟
          </h2>
          <p className="text-sm text-zinc-400">مقارنة صريحة مع المنصات الأخرى</p>
        </div>
        <div className="overflow-x-auto" data-testid="comparison-table">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-right py-3 px-4 text-zinc-500 font-bold">الميزة</th>
                <th className="text-center py-3 px-4 font-black bg-gradient-to-r from-fuchsia-300 to-purple-300 bg-clip-text text-transparent">
                  💎 Zenrex Independence
                </th>
                <th className="text-center py-3 px-4 text-zinc-500 font-bold">Lovable / Bolt / v0</th>
              </tr>
            </thead>
            <tbody className="text-zinc-300">
              {[
                ['نموذج الدفع', 'مرة واحدة $799', 'اشتراك شهري $20-30'],
                ['ملكية الكود', '✅ كاملة (رخصة MIT)', '⚠️ مقيدة بالـTerms'],
                ['Backend جاهز', '✅ FastAPI + MongoDB + JWT', '❌ Frontend فقط'],
                ['Backend API', '✅ CRUD + Auth مولّدة', '❌ تحتاج Supabase/أخرى'],
                ['CI/CD', '✅ GitHub Actions جاهز', '❌ يدوي'],
                ['VPS Provisioning', '✅ One-click Hetzner', '❌ غير متاح'],
                ['نقل ملكية GitHub', '✅ تلقائي بـ PAT', '❌ يدوي'],
                ['دعم باللغة العربية', '✅ كامل بالسعودي', '❌ إنجليزي فقط'],
                ['ARCHITECTURE.md مخصص', '✅ مُولّد بـClaude', '❌ غير موجود'],
              ].map(([feat, ours, theirs], i) => (
                <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="py-3 px-4 font-bold text-zinc-200">{feat}</td>
                  <td className="py-3 px-4 text-center text-fuchsia-200">{ours}</td>
                  <td className="py-3 px-4 text-center text-zinc-500">{theirs}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how-it-works" className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 mb-4">
            <Cpu className="w-3.5 h-3.5 text-cyan-300" />
            <span className="text-[11px] font-bold text-cyan-200">٤ ذكاءات تشتغل بالتوازي</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-white mb-3">من الفكرة للتسليم — <span className="text-cyan-300">٤ مراحل ذكية</span></h2>
          <p className="text-sm text-zinc-400 max-w-2xl mx-auto">كل مرحلة فيها ذكاء مستقل متخصص — Discovery → Builder → Code Reviewer → Browser Engineer</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <StepCard
            num="1"
            icon={Sparkles}
            title="🧠 Discovery Brain"
            body="نسألك ١٥-٢٥ سؤال على دفعات (٥ كل مرة) لنبني خارطة طريق دقيقة لمشروعك. نحدّد نوع الـvertical، الميزات الأساسية، ونوع المستخدمين."
            accent="cyan"
          />
          <StepCard
            num="2"
            icon={Code}
            title="🎨 Builder Agent"
            body="بناءً على الـroadmap، الـAI يبني Frontend بـHTML/CSS/JS أنيق مع Tailwind + animations + responsive design — مرحلة بمرحلة لا يخمّن."
            accent="fuchsia"
          />
          <StepCard
            num="3"
            icon={Database}
            title="🔧 Backend Builder"
            body="يولّد FastAPI + MongoDB + JWT auth + CRUD endpoints لكل entity مكتشف في الـDiscovery. كل ملف Python syntax صحيح مضمون."
            accent="emerald"
          />
          <StepCard
            num="4"
            icon={Rocket}
            title="🚀 Independence Handover"
            body="ZIP فيه 24 ملف، نقل ملكية GitHub repo، نشر تلقائي على Hetzner VPS، خطاب تسليم رسمي، 60 يوم دعم — وفك ارتباط نهائي."
            accent="amber"
          />
        </div>
      </section>

      {/* WHAT'S IN THE KIT */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-20 border-y border-white/5">
        <div className="text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-black text-white mb-3">
            وش يجي في ZIP الـ <span className="bg-gradient-to-r from-fuchsia-300 to-purple-300 bg-clip-text text-transparent">$799</span>؟
          </h2>
          <p className="text-sm text-zinc-400">
            <span className="font-bold text-white">24 ملف</span> · حقيقية · جاهزة للإنتاج · بدون أي وعود فارغة
          </p>
        </div>

        {/* Group filters */}
        <div className="flex flex-wrap justify-center gap-2 mb-6" data-testid="kit-groups">
          {Object.entries(GROUP_META).map(([key, m]) => {
            const styles = {
              cyan: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-200',
              emerald: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200',
              fuchsia: 'bg-fuchsia-500/10 border-fuchsia-500/30 text-fuchsia-200',
              amber: 'bg-amber-500/10 border-amber-500/30 text-amber-200',
              purple: 'bg-purple-500/10 border-purple-500/30 text-purple-200',
            }[m.color] || 'bg-zinc-500/10 border-zinc-500/30 text-zinc-200';
            return (
              <span key={key} className={`px-2.5 py-1 rounded-full text-[11px] font-bold border ${styles}`}>
                {m.label}
              </span>
            );
          })}
        </div>

        {/* File grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5" data-testid="kit-files-grid">
          {KIT_FILES.map((f) => <KitFileChip key={f.name} file={f} />)}
          {/* Sentinel — "+entity routes" */}
          <div className="flex items-center justify-center rounded-lg border border-dashed border-white/15 px-2.5 py-1.5 text-[11px] text-zinc-500">
            + ملفات routes لكل entity
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h2 className="text-2xl sm:text-3xl font-black text-white mb-3">اختر اللي يناسبك</h2>
          <p className="text-sm text-zinc-400">٤ مستويات · دفعة وحدة · بدون اشتراك مخفي</p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5" data-testid="tiers-grid">
          {TIERS.map((t) => <TierCard key={t.id} tier={t} onCta={handleCta} />)}
        </div>
        <p className="text-center text-[11px] text-zinc-500 mt-6 leading-relaxed max-w-2xl mx-auto">
          ⚠️ الباقات المدفوعة <span className="text-zinc-300">للمواقع الستاتيكة + Backend FastAPI/MongoDB</span>. التطبيقات الجوال (iOS/Android) قادمة قريباً.
        </p>
      </section>

      {/* FAQ / Honest disclaimers */}
      <section className="relative z-10 max-w-4xl mx-auto px-6 py-16 border-t border-white/5">
        <h2 className="text-2xl font-black text-white mb-8 text-center">أسئلة شائعة</h2>
        <div className="space-y-3" data-testid="faq-list">
          {[
            {
              q: 'هل أحتاج خبرة برمجية؟',
              a: 'لا. الذكاء يولّد كل شيء. لكن لو عندك خبرة بسيطة بـDocker و GitHub، التسليم بيكون أسرع. ولو ما عندك، الذكاء يمشي معك خطوة بخطوة (60 يوم دعم).',
            },
            {
              q: 'هل أحتاج VPS؟',
              a: 'إن أردت استضافة مستقلة 100%، نعم. ننصح بـHetzner CX22 (€4.5/شهر). لكن المنصة تربطك تلقائياً بـHetzner بكبسة زر — تلصق الـtoken ونحن ننشر السيرفر ونرفع الكود.',
            },
            {
              q: 'هل الكود فعلاً ملكي؟',
              a: 'نعم 100%. رخصة MIT (في ملف LICENSE). تقدر تبيع المشروع، تعدّله، تدمجه في أي شي — بدون استئذاننا. خطاب HANDOVER.md رسمي ينقل الحقوق نهائياً.',
            },
            {
              q: 'وش الفرق بين $199 و $799؟',
              a: '$199 = الـFrontend فقط + إرشاد للنشر على Vercel/GitHub Pages. $799 = Frontend + Backend FastAPI + MongoDB + JWT + CRUD + GitHub Actions + One-click VPS — يعني تطبيق كامل بدل صفحة ستاتيكة.',
            },
            {
              q: 'ماذا لو تعطل المشروع بعد التسليم؟',
              a: '60 يوم دعم عبر support@zenrex.ai — نصلح أي bug في الكود المُسلّم مجاناً. بعد 60 يوم، الكود ملكك بالكامل وتقدر تتعاقد مع أي مبرمج لأن كل شي مفتوح وموثّق.',
            },
            {
              q: 'متى راح ينزل دعم iOS/Android؟',
              a: 'العمل جاري على Apps Mode (PWA + React Native generation). متوقّع في Q2 2026. الباقة الحالية كاملة وحقيقية للمواقع وful-stack APIs.',
            },
          ].map((item, i) => (
            <details key={i} className="group rounded-xl border border-white/10 bg-zinc-950/60 hover:border-fuchsia-500/30 transition-colors" data-testid={`faq-item-${i}`}>
              <summary className="cursor-pointer list-none p-4 flex items-center justify-between gap-3">
                <span className="font-bold text-white text-sm">{item.q}</span>
                <span className="text-fuchsia-400 text-lg group-open:rotate-45 transition-transform">+</span>
              </summary>
              <div className="px-4 pb-4 text-[13px] text-zinc-300 leading-relaxed">{item.a}</div>
            </details>
          ))}
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="relative z-10 max-w-4xl mx-auto px-6 py-20 text-center">
        <div className="rounded-3xl border border-fuchsia-500/30 bg-gradient-to-br from-fuchsia-900/40 via-purple-900/30 to-zinc-950 p-10 shadow-2xl shadow-fuchsia-500/20">
          <Zap className="w-10 h-10 text-fuchsia-300 mx-auto mb-4" />
          <h2 className="text-3xl sm:text-4xl font-black text-white mb-4">
            جاهز تطلق <span className="bg-gradient-to-r from-fuchsia-300 to-purple-300 bg-clip-text text-transparent">مشروعك المستقل</span>؟
          </h2>
          <p className="text-zinc-300 text-sm mb-8 max-w-xl mx-auto leading-relaxed">
            ابدأ بدفعة واحدة، اطلع بتطبيق full-stack حقيقي، على سيرفرك، بـGitHub باسمك. بدون اشتراك. بدون قيود.
          </p>
          <button
            type="button"
            onClick={() => handleCta('independence')}
            data-testid="final-cta-btn"
            className="px-8 py-4 rounded-xl bg-gradient-to-r from-fuchsia-500 via-purple-500 to-violet-600 hover:from-fuchsia-400 hover:to-violet-500 text-white font-black text-base shadow-xl shadow-fuchsia-500/30 transition-all hover:scale-105 inline-flex items-center gap-2"
          >
            <Rocket className="w-5 h-5" />
            ابدأ مشروعك الآن — $799
          </button>
          <p className="text-[10px] text-zinc-500 mt-4">دفع آمن عبر Stripe · ضمان 14 يوم استرداد</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 max-w-7xl mx-auto px-6 py-10 border-t border-white/5 text-center">
        <p className="text-[11px] text-zinc-500">
          © Zenrex.ai — منصة بناء بالذكاء الاصطناعي · صنع بـ ❤️ في السعودية 🇸🇦
        </p>
      </footer>
    </div>
  );
}
