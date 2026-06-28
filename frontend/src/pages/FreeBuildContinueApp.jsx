// FreeBuildContinueApp.jsx — Project Continuation for MOBILE & NATIVE APPS.
// Mirror of FreeBuildContinue but with app-specific copy + stack picker.
// Uses the same backend endpoint /projects/continuation/create with mode='continuation'
// + extra metadata `app_kind` so the AI engineer manager knows it's an app project.
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowRight, ShieldCheck, GitBranch, Eye, Microscope,
  Wrench, Sparkles, AlertTriangle, CheckCircle2, Smartphone,
  Apple, Bot, Layers, Gamepad2, Monitor, Code2,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const APP_KINDS = [
  { id: 'flutter', label: 'Flutter', desc: 'تطبيق مشترك للـ iOS و Android', icon: Layers, color: 'sky' },
  { id: 'react_native', label: 'React Native / Expo', desc: 'JavaScript/TypeScript للموبايل', icon: Smartphone, color: 'cyan' },
  { id: 'capacitor', label: 'Ionic / Capacitor', desc: 'PWA → APK/IPA', icon: Bot, color: 'indigo' },
  { id: 'android_native', label: 'Android أصلي', desc: 'Kotlin / Java + Gradle', icon: Smartphone, color: 'emerald' },
  { id: 'ios_native', label: 'iOS أصلي', desc: 'Swift / Objective-C + Xcode', icon: Apple, color: 'zinc' },
  { id: 'dotnet_maui', label: '.NET MAUI / Xamarin', desc: 'C# لكل المنصات', icon: Code2, color: 'violet' },
  { id: 'electron_tauri', label: 'Electron / Tauri', desc: 'تطبيقات سطح المكتب', icon: Monitor, color: 'amber' },
  { id: 'unity_game', label: 'Unity / Unreal / Godot', desc: 'ألعاب', icon: Gamepad2, color: 'rose' },
  { id: 'unknown', label: 'ما أعرف / تقنية أخرى', desc: 'الذكاء يكتشفها من المستودع', icon: Sparkles, color: 'fuchsia' },
];

export default function FreeBuildContinueApp() {
  const navigate = useNavigate();
  const [projectName, setProjectName] = useState('');
  const [briefDescription, setBriefDescription] = useState('');
  const [appKind, setAppKind] = useState('');
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/login?return=/freebuild/continue-app'); return; }
    if (!projectName.trim()) { toast.error('اكتب اسم التطبيق'); return; }
    if (briefDescription.trim().length < 30) {
      toast.error('وصف موجز للتطبيق ٣٠ حرف على الأقل');
      return;
    }
    if (!appKind) { toast.error('اختر نوع التقنية أو "ما أعرف"'); return; }
    if (!accepted) { toast.error('لازم تقرأ وتقبل الشروط'); return; }
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/freebuild-chat/projects/continuation/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          source_type: 'description',
          description: `**${projectName}** [نوع التطبيق: ${APP_KINDS.find(k => k.id === appKind)?.label || appKind}]\n\n${briefDescription}`,
          metadata: { project_kind: 'app', app_kind: appKind },
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
    <div dir="rtl" data-testid="freebuild-continue-app-page" className="min-h-screen bg-gradient-to-br from-[#0a0a1a] via-[#0a1a1f] to-[#0a1f1a] text-white">
      {/* Hero */}
      <div className="relative h-72 sm:h-96 overflow-hidden">
        <img src="https://images.unsplash.com/photo-1601972602288-3be527b4f18b?auto=format&fit=crop&w=1920&q=80"
             alt="Mobile App Maintenance" className="absolute inset-0 w-full h-full object-cover opacity-25" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a1a] via-[#0a0a1a]/80 to-transparent" />
        <div className="relative h-full max-w-6xl mx-auto px-6 flex flex-col justify-end pb-10">
          <button onClick={() => navigate('/')} className="self-end text-xs text-cyan-300 hover:text-cyan-100 mb-3 flex items-center gap-1" data-testid="back-home-btn">
            <ArrowRight className="w-3.5 h-3.5" />
            رجوع
          </button>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-cyan-500/20 border border-cyan-400/40 text-cyan-200">جديد</span>
            <span className="text-[11px] text-zinc-400">مدير هندسي ذكي لتطبيقاتك القائمة</span>
          </div>
          <h1 className="text-4xl sm:text-6xl font-black bg-gradient-to-r from-cyan-300 via-sky-300 to-emerald-300 bg-clip-text text-transparent">
            تكملة تطبيق
          </h1>
          <p className="text-sm sm:text-lg text-zinc-300 mt-3 max-w-3xl leading-relaxed">
            عندك تطبيق <strong className="text-cyan-200">iOS أو Android أو Cross-Platform</strong> وتبيه يتطوّر أو يتصلح أو يضيف ميزات؟
            خلّي <strong className="text-cyan-200">مدير هندسي ذكي</strong> يستلمه ويشتغل عليه — يدعم كل التقنيات:
            <span className="block text-xs sm:text-sm text-zinc-400 mt-1">
              Flutter · React Native / Expo · Capacitor · Native iOS/Android · .NET MAUI · Electron · Tauri · Unity · وغيرها
            </span>
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-10">
        {/* How it works — 4 phases (same flow as websites) */}
        <section className="mb-12" data-testid="how-it-works-section">
          <h2 className="text-xl font-black text-zinc-100 mb-2">كيف يشتغل؟ (٤ مراحل آمنة)</h2>
          <p className="text-xs text-zinc-500 mb-6">ما يلمس مستودعك الأصلي — يشتغل على نسخة معزولة عندنا.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { icon: <GitBranch className="w-6 h-6" />, num: '1', title: 'الاستلام الآمن',
                desc: 'الذكاء يسألك في الشات عن نوع المستودع (Git/EAS/Codemagic) ومفاتيح المتجر (Play/App Store). تُحفظ مشفّرة.',
                color: 'cyan' },
              { icon: <Microscope className="w-6 h-6" />, num: '2', title: 'الكشف والتحليل',
                desc: 'يستنسخ التطبيق لـ sandbox + يكتشف الستاك تلقائياً (Flutter/RN/Native/MAUI/Unity…) + يحدّد أوامر البناء/الاختبار.',
                color: 'sky' },
              { icon: <Wrench className="w-6 h-6" />, num: '3', title: 'الإصلاح والبناء',
                desc: 'يصلح الـ bugs + ينفّذ التحسينات + يبني APK/IPA/AAB في الـ sandbox أو عبر EAS/Codemagic للـ iOS.',
                color: 'emerald' },
              { icon: <CheckCircle2 className="w-6 h-6" />, num: '4', title: 'النشر على المتاجر',
                desc: 'بعد موافقتك، يرسل للمتاجر (Play Console، App Store Connect، Firebase Distribution، TestFlight) — كل خطوة موثقة.',
                color: 'amber' },
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

        {/* Tech stack support */}
        <section className="mb-12 rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-6" data-testid="stacks-section">
          <div className="flex items-center gap-2 mb-4">
            <Layers className="w-5 h-5 text-cyan-300" />
            <h2 className="text-base font-black text-cyan-100">دعم شامل لكل تقنيات البرمجة</h2>
          </div>
          <p className="text-xs text-zinc-400 mb-4">المدير الهندسي مدرّب على ٢٥+ تقنية. لو ما لقى الستاك يكتشفها تلقائياً من ملفات المشروع.</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-[11px]">
            {[
              'Flutter', 'React Native', 'Expo', 'Capacitor', 'Ionic',
              'Cordova', 'NativeScript', '.NET MAUI', 'Android (Kotlin)', 'iOS (Swift)',
              'Electron', 'Tauri', 'Unity', 'Unreal', 'Godot',
              'Next.js', 'Vue/Nuxt', 'Django', 'FastAPI', 'Express',
              'Go', 'Rust', 'Java Spring', 'Ruby Rails', 'PHP Laravel',
            ].map((t, i) => (
              <div key={i} className="px-2 py-1.5 rounded-lg bg-black/30 border border-white/5 text-zinc-300 text-center hover:bg-cyan-500/10 transition">
                {t}
              </div>
            ))}
          </div>
        </section>

        {/* Safety */}
        <section className="mb-12 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6" data-testid="safety-section">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-5 h-5 text-emerald-300" />
            <h2 className="text-base font-black text-emerald-100">ضمانات السلامة الصارمة</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-zinc-300">
            {[
              'استنساخ في sandbox معزول — مستودعك الأصلي محمي',
              'الـ AI ما ينفّذ إلا أوامر من قائمة بيضاء (npm/flutter/gradle...) — لا rm -rf، لا sudo',
              'كل build يحفظ snapshot قابل للاسترجاع لحظياً',
              'نشر للمتاجر يتطلب موافقة صريحة منك + Track Internal أولاً',
              'مفاتيح Keystore + Provisioning Profile تُحفظ بتشفير AES-128',
              'سجل قانوني مفصّل بـ SHA-256 لكل عملية',
            ].map((g, i) => (
              <div key={i} className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>{g}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Pricing — same as websites */}
        <section className="mb-12" data-testid="pricing-section">
          <h2 className="text-xl font-black text-zinc-100 mb-2">التسعير</h2>
          <p className="text-xs text-zinc-500 mb-6">نفس تسعير تكملة المواقع. شفّاف، صفر مفاجآت.</p>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-6">
              <div className="text-[10px] font-black text-emerald-300 mb-1">المرحلة ١ — مجاناً</div>
              <div className="text-3xl font-black text-emerald-200 mb-2">$0</div>
              <div className="text-xs text-zinc-300 leading-relaxed">الكشف + التحليل + أول تحديث ملموس على الـ sandbox. تشوف الجودة قبل ما تدفع.</div>
            </div>
            <div className="rounded-2xl border-2 border-cyan-500/50 bg-gradient-to-br from-cyan-500/15 to-sky-500/10 p-6 relative">
              <span className="absolute -top-2 right-4 text-[9px] font-black px-2 py-0.5 rounded-full bg-cyan-500 text-white">الأشهر</span>
              <div className="text-[10px] font-black text-cyan-300 mb-1">الاشتراك الشهري</div>
              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-3xl font-black text-cyan-200">$150</span>
                <span className="text-xs text-cyan-300">/ شهر</span>
              </div>
              <ul className="text-[11px] text-zinc-300 space-y-1.5">
                <li>✓ دعم فني + صيانة</li>
                <li>✓ Sandbox + Backup</li>
                <li>✓ مراقبة فريق Zenrex</li>
                <li>✓ EAS/Codemagic build minutes</li>
                <li>✓ إلغاء في أي وقت</li>
              </ul>
            </div>
            <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-6">
              <div className="text-[10px] font-black text-amber-300 mb-1">التطوير والإضافات</div>
              <div className="text-3xl font-black text-amber-200 mb-2">نقاط</div>
              <div className="text-xs text-zinc-300 leading-relaxed">كل ميزة جديدة / إصلاح كبير = نقاط حسب الحجم. منفصل عن الاشتراك.</div>
            </div>
          </div>
        </section>

        {/* CTA Form */}
        <section className="rounded-2xl border border-cyan-500/30 bg-black/40 backdrop-blur-sm p-6 sm:p-8" data-testid="cta-section">
          <h2 className="text-xl font-black text-zinc-100 mb-2">جاهز نبدأ؟</h2>
          <p className="text-xs text-zinc-500 mb-6">عرّفنا على التطبيق. تفاصيل الوصول يطلبها الذكاء في الشات بأمان.</p>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-zinc-400 mb-2">اسم التطبيق</label>
              <input
                type="text" value={projectName} onChange={(e) => setProjectName(e.target.value)}
                placeholder="مثلاً: تطبيق توصيل القهوة"
                data-testid="project-name-input"
                className="w-full px-4 py-3 rounded-lg bg-black/50 border border-white/10 text-sm focus:border-cyan-400/50 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-zinc-400 mb-2">نوع التقنية</label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2" data-testid="app-kind-picker">
                {APP_KINDS.map(k => (
                  <button
                    key={k.id}
                    onClick={() => setAppKind(k.id)}
                    data-testid={`app-kind-${k.id}`}
                    className={`text-right px-3 py-2.5 rounded-lg border transition flex items-start gap-2 ${
                      appKind === k.id
                        ? `border-${k.color}-400 bg-${k.color}-500/15`
                        : 'border-white/10 bg-black/30 hover:bg-white/5'
                    }`}
                  >
                    <k.icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${appKind === k.id ? `text-${k.color}-300` : 'text-zinc-400'}`} />
                    <div className="flex-1 min-w-0">
                      <div className={`text-[11px] font-bold ${appKind === k.id ? 'text-white' : 'text-zinc-300'}`}>{k.label}</div>
                      <div className="text-[9px] text-zinc-500 mt-0.5 truncate">{k.desc}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-zinc-400 mb-2">
                وصف موجز — أيش التطبيق؟ وأيش تبي تطوّر أو تصلح؟
              </label>
              <textarea
                value={briefDescription} onChange={(e) => setBriefDescription(e.target.value)}
                placeholder="مثلاً: تطبيق Flutter لتوصيل الطلبات في الرياض، منذ ٢٠٢٣. أبي أحسّن الأداء + أضيف Apple Pay + أرفعه لـ TestFlight. متجر Play موجود، iOS قيد المراجعة. الـ repo على GitHub."
                rows={5}
                data-testid="brief-description-input"
                className="w-full px-4 py-3 rounded-lg bg-black/50 border border-white/10 text-sm focus:border-cyan-400/50 focus:outline-none resize-none"
              />
              <p className="text-[10px] text-zinc-500 mt-2">
                💡 ما تشارك مفاتيح/كلمات سر هنا. الذكاء يسألك بطريقة آمنة في الشات ويحفظها مشفّرة.
              </p>
            </div>

            {/* Consent */}
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4" data-testid="consent-block">
              <div className="flex items-start gap-3 mb-3">
                <AlertTriangle className="w-5 h-5 text-amber-300 flex-shrink-0 mt-0.5" />
                <div className="text-xs text-amber-100/90 leading-relaxed">
                  <strong className="text-amber-200">إقرار وموافقة:</strong>
                  <ul className="mt-2 space-y-1 list-disc list-inside text-amber-200/80">
                    <li>سأشارك تفاصيل وصول الـ repo + مفاتيح المتاجر مع الذكاء (تُحفظ مشفّرة).</li>
                    <li>الذكاء يبني ويختبر في sandbox معزول قبل أي رفع للمتاجر.</li>
                    <li>أي نشر للمتاجر (Play/App Store) يحتاج موافقتي الصريحة.</li>
                    <li>الاشتراك الشهري $150 يبدأ بعد أول تحديث ملموس وقبولي للجودة.</li>
                  </ul>
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)}
                  data-testid="accept-checkbox" className="w-4 h-4 accent-cyan-500" />
                <span className="text-xs font-bold text-amber-100">قرأت وأوافق على الشروط</span>
              </label>
            </div>

            <button
              onClick={submit}
              disabled={busy || !accepted}
              data-testid="continuation-app-submit-btn"
              className="w-full py-4 rounded-xl bg-gradient-to-r from-cyan-500 to-sky-500 hover:from-cyan-400 hover:to-sky-400 transition font-black text-base text-white shadow-xl shadow-cyan-500/30 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {busy ? (
                <><span className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />جاري الإنشاء...</>
              ) : (
                <><Sparkles className="w-5 h-5" />ابدأ مع المدير الهندسي</>
              )}
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
