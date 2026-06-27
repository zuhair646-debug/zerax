// FreeBuildContinue.jsx — Project Continuation v2.
// Honest, safety-first onboarding for existing projects. The actual repo
// connection (Git/SSH/FTP/credentials) happens INSIDE the chat with the AI
// acting as Engineering Manager — this page is just the consent/entry gate.
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowRight, ShieldCheck, GitBranch, Eye, Microscope,
  Wrench, Sparkles, AlertTriangle, CheckCircle2, Database,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function FreeBuildContinue() {
  const navigate = useNavigate();
  const [projectName, setProjectName] = useState('');
  const [briefDescription, setBriefDescription] = useState('');
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/login?return=/freebuild/continue'); return; }
    if (!projectName.trim()) { toast.error('اكتب اسم المشروع'); return; }
    if (briefDescription.trim().length < 30) {
      toast.error('وصف موجز للمشروع ٣٠ حرف على الأقل');
      return;
    }
    if (!accepted) { toast.error('لازم تقرأ وتقبل الشروط'); return; }
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/freebuild-chat/projects/continuation/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          source_type: 'description',
          description: `**${projectName}**\n\n${briefDescription}`,
        }),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        toast.error(e.detail || 'فشل إنشاء المشروع');
        return;
      }
      const d = await r.json();
      toast.success('بدأنا — اذهب للشات وأكمل مع المدير الهندسي');
      navigate(`/freebuild/chat/${d.project_id}`);
    } catch (e) {
      toast.error('خطأ في الاتصال');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div dir="rtl" data-testid="freebuild-continue-page" className="min-h-screen bg-gradient-to-br from-[#0a0a1a] via-[#0f0a1f] to-[#1a0a1f] text-white">
      {/* Hero banner */}
      <div className="relative h-72 sm:h-96 overflow-hidden">
        <img src="https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=1920&q=80"
             alt="Project Maintenance" className="absolute inset-0 w-full h-full object-cover opacity-25" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a1a] via-[#0a0a1a]/80 to-transparent" />
        <div className="relative h-full max-w-6xl mx-auto px-6 flex flex-col justify-end pb-10">
          <button onClick={() => navigate('/')} className="self-end text-xs text-fuchsia-300 hover:text-fuchsia-100 mb-3 flex items-center gap-1" data-testid="back-home-btn">
            <ArrowRight className="w-3.5 h-3.5" />
            رجوع
          </button>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-fuchsia-500/20 border border-fuchsia-400/40 text-fuchsia-200">جديد</span>
            <span className="text-[11px] text-zinc-400">مدير هندسي ذكي لمشاريعك القائمة</span>
          </div>
          <h1 className="text-4xl sm:text-6xl font-black bg-gradient-to-r from-fuchsia-300 via-rose-300 to-amber-300 bg-clip-text text-transparent">
            تكملة مشروع
          </h1>
          <p className="text-sm sm:text-lg text-zinc-300 mt-3 max-w-3xl leading-relaxed">
            عندك موقع/تطبيق شغّال وتبيه يتطوّر، يصير له صيانة، أو يتضاف له ميزات جديدة؟
            خلّي <strong className="text-fuchsia-200">مدير هندسي ذكي</strong> يأخذ المشروع، يفهمه عميقاً،
            ويشتغل عليه بطريقة احترافية — <strong className="text-amber-300">بدون أي مساس بالنسخة الأصلية</strong>
            حتى توافق على كل تغيير.
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-10">

        {/* ─── How it works (the REAL flow) ─── */}
        <section className="mb-12" data-testid="how-it-works-section">
          <h2 className="text-xl font-black text-zinc-100 mb-2">كيف يشتغل؟ (٤ مراحل آمنة)</h2>
          <p className="text-xs text-zinc-500 mb-6">ما يلمس مشروعك الأصلي — يشتغل على نسخة معزولة عندنا.</p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                icon: <GitBranch className="w-6 h-6" />, num: '1', title: 'الاستلام الآمن',
                desc: 'الذكاء يسألك في الشات عن نوع المستودع (Git / SSH / FTP) ومفاتيح الوصول. تُحفظ في خزنة مشفّرة (Concierge Vault).',
                color: 'fuchsia',
              },
              {
                icon: <Database className="w-6 h-6" />, num: '2', title: 'النسخ والعزل',
                desc: 'يستنسخ مشروعك إلى sandbox خاص على سيرفر zenrex (نسخة طبق الأصل). الأصل لا يُلمَس أبداً في هذي المرحلة.',
                color: 'rose',
              },
              {
                icon: <Microscope className="w-6 h-6" />, num: '3', title: 'التشخيص والإصلاح',
                desc: 'يحلّل البنية، التصاميم، الأداء، الثغرات. يصلح المشاكل ويضيف الميزات على النسخة. معاينة مباشرة على رابط خاص.',
                color: 'amber',
              },
              {
                icon: <CheckCircle2 className="w-6 h-6" />, num: '4', title: 'التطبيق على الأصل',
                desc: 'تشوف النسخة المُحسَّنة، توافق، ومن ثم تتم "الجراحة الدقيقة" على مشروعك الأصلي — بـ commits منظّمة وعودة فورية لو احتجت.',
                color: 'emerald',
              },
            ].map((s, i) => (
              <div key={i} data-testid={`phase-card-${s.num}`}
                   className={`rounded-2xl border border-${s.color}-500/20 bg-${s.color}-500/5 p-5 hover:bg-${s.color}-500/10 transition`}>
                <div className={`text-${s.color}-300 mb-3`}>{s.icon}</div>
                <div className={`text-[10px] font-black text-${s.color}-200 mb-1`}>المرحلة {s.num}</div>
                <h3 className="text-sm font-bold text-zinc-100 mb-2">{s.title}</h3>
                <p className="text-[11px] text-zinc-400 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ─── Safety Guarantees ─── */}
        <section className="mb-12 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6" data-testid="safety-section">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-5 h-5 text-emerald-300" />
            <h2 className="text-base font-black text-emerald-100">ضمانات السلامة الصارمة</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-zinc-300">
            {[
              'الذكاء يبدأ بـ read-only — يقرأ ولا يكتب حتى يفهم المشروع كاملاً',
              'كل تغيير يصير في Git branch منفصل + diff واضح قبل التطبيق',
              'موافقتك صريحة قبل أي ملف يتعدّل في الأصل',
              'Backup تلقائي قبل أي عملية على المشروع الأصلي',
              'زر "تراجع فوري" لأي تغيير تم — يرجع لحظياً للحالة السابقة',
              'مراقبة بشرية من فريق Zenrex لكل المشاريع — لو حدث خلل، نتدخّل فوراً',
            ].map((g, i) => (
              <div key={i} className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>{g}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ─── Pricing ─── */}
        <section className="mb-12" data-testid="pricing-section">
          <h2 className="text-xl font-black text-zinc-100 mb-2">التسعير الواضح</h2>
          <p className="text-xs text-zinc-500 mb-6">شفّاف — صفر مفاجآت في الفاتورة.</p>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-6" data-testid="pricing-trial">
              <div className="text-[10px] font-black text-emerald-300 mb-1">المرحلة ١ — مجاناً</div>
              <div className="text-3xl font-black text-emerald-200 mb-2">$0</div>
              <div className="text-xs text-zinc-300 leading-relaxed">
                الاستلام + التشخيص + أول تحديث ملموس على النسخة المعزولة. تشوف الجودة قبل ما تدفع أي شي.
              </div>
            </div>
            <div className="rounded-2xl border-2 border-fuchsia-500/50 bg-gradient-to-br from-fuchsia-500/15 to-rose-500/10 p-6 relative" data-testid="pricing-monthly">
              <span className="absolute -top-2 right-4 text-[9px] font-black px-2 py-0.5 rounded-full bg-fuchsia-500 text-white">الأشهر</span>
              <div className="text-[10px] font-black text-fuchsia-300 mb-1">الاشتراك الشهري</div>
              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-3xl font-black text-fuchsia-200">$150</span>
                <span className="text-xs text-fuchsia-300">/ شهر</span>
              </div>
              <ul className="text-[11px] text-zinc-300 space-y-1.5 leading-relaxed">
                <li>✓ دعم فني + صيانة مستمرة</li>
                <li>✓ مساحة sandbox للنسخة المعزولة</li>
                <li>✓ Backup تلقائي يومي</li>
                <li>✓ مراقبة فريق Zenrex</li>
                <li>✓ إلغاء في أي وقت</li>
              </ul>
            </div>
            <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-6" data-testid="pricing-credits">
              <div className="text-[10px] font-black text-amber-300 mb-1">التطوير والإضافات</div>
              <div className="text-3xl font-black text-amber-200 mb-2">نقاط</div>
              <div className="text-xs text-zinc-300 leading-relaxed">
                أي تعديل/إضافة/ميزة جديدة = خصم نقاط حسب الحجم.
                <span className="block text-[10px] text-amber-200/80 mt-2">منفصل تماماً عن الاشتراك الشهري — تدفع فقط لما تطلب.</span>
              </div>
            </div>
          </div>
        </section>

        {/* ─── CTA Form ─── */}
        <section className="rounded-2xl border border-fuchsia-500/30 bg-black/40 backdrop-blur-sm p-6 sm:p-8" data-testid="cta-section">
          <h2 className="text-xl font-black text-zinc-100 mb-2">جاهز نبدأ؟</h2>
          <p className="text-xs text-zinc-500 mb-6">عرّفنا على مشروعك. تفاصيل الوصول يطلبها الذكاء منك بأمان في الشات.</p>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-zinc-400 mb-2">اسم المشروع / الشركة</label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="مثلاً: متجر القهوة العُمانية"
                data-testid="project-name-input"
                className="w-full px-4 py-3 rounded-lg bg-black/50 border border-white/10 text-sm focus:border-fuchsia-400/50 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-zinc-400 mb-2">
                وصف موجز — أيش المشروع؟ وأيش تبي تطوّر أو تصلح؟
              </label>
              <textarea
                value={briefDescription}
                onChange={(e) => setBriefDescription(e.target.value)}
                placeholder="مثلاً: متجر إلكتروني على WordPress منذ ٢٠٢١. أبي أحسن السرعة، أضيف نظام نقاط ولاء، وأربط دفع Mada. التقنيات: WP + WooCommerce + Yoast SEO. حجم تقريبي: ٥٠٠ منتج."
                rows={5}
                data-testid="brief-description-input"
                className="w-full px-4 py-3 rounded-lg bg-black/50 border border-white/10 text-sm focus:border-fuchsia-400/50 focus:outline-none resize-none leading-relaxed"
              />
              <p className="text-[10px] text-zinc-500 mt-2">
                💡 ما تشارك مفاتيح/كلمات سر هنا. الذكاء يسألك بطريقة آمنة داخل الشات ويحفظها مشفّرة.
              </p>
            </div>

            {/* Sensitive consent */}
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4" data-testid="consent-block">
              <div className="flex items-start gap-3 mb-3">
                <AlertTriangle className="w-5 h-5 text-amber-300 flex-shrink-0 mt-0.5" />
                <div className="text-xs text-amber-100/90 leading-relaxed">
                  <strong className="text-amber-200">إقرار وموافقة:</strong>
                  <ul className="mt-2 space-y-1 list-disc list-inside text-amber-200/80">
                    <li>سأشارك تفاصيل وصول مشروعي مع الذكاء داخل الشات (تُحفظ مشفّرة).</li>
                    <li>الذكاء يعمل على نسخة معزولة أولاً — لا يلمس الأصل إلا بموافقتي الصريحة.</li>
                    <li>أفهم أن الاشتراك الشهري $150 يبدأ <em>بعد</em> أول تحديث ملموس وقبولي للجودة.</li>
                    <li>التطوير/الإضافات تُخصم كنقاط منفصلة عن الاشتراك.</li>
                  </ul>
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={accepted}
                  onChange={(e) => setAccepted(e.target.checked)}
                  data-testid="accept-checkbox"
                  className="w-4 h-4 accent-fuchsia-500"
                />
                <span className="text-xs font-bold text-amber-100">قرأت وأوافق على هذي الشروط</span>
              </label>
            </div>

            <button
              onClick={submit}
              disabled={busy || !accepted}
              data-testid="continuation-submit-btn"
              className="w-full py-4 rounded-xl bg-gradient-to-r from-fuchsia-500 to-rose-500 hover:from-fuchsia-400 hover:to-rose-400 transition font-black text-base text-white shadow-xl shadow-fuchsia-500/30 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {busy ? (
                <>
                  <span className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  جاري الإنشاء...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  ابدأ مع المدير الهندسي
                </>
              )}
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
