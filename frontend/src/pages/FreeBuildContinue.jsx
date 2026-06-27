// FreeBuildContinue.jsx — Project Continuation entry form.
// User pastes a URL or uploads code → AI analyzes → opens chat in continuation mode.
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowRight, Globe, Code, FileText, Sparkles, Lock, ShieldCheck } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function FreeBuildContinue() {
  const navigate = useNavigate();
  const [mode, setMode] = useState('url'); // 'url' | 'description'
  const [url, setUrl] = useState('');
  const [description, setDescription] = useState('');
  const [accessNote, setAccessNote] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/login?return=/freebuild/continue'); return; }
    if (mode === 'url' && !url.trim()) { toast.error('اكتب رابط الموقع'); return; }
    if (mode === 'description' && description.trim().length < 30) {
      toast.error('وصف المشروع لازم يكون ٣٠ حرف على الأقل');
      return;
    }
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/freebuild-chat/projects/continuation/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          source_type: mode,
          url: mode === 'url' ? url.trim() : null,
          description: description.trim() || null,
          access_note: accessNote.trim() || null,
        }),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        toast.error(e.detail || 'فشل إنشاء المشروع');
        return;
      }
      const d = await r.json();
      toast.success('تم! الذكاء الصناعي بدأ تحليل مشروعك...');
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
      <div className="relative h-64 sm:h-80 overflow-hidden">
        <img src="https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=1920&q=80"
             alt="Project Continuation" className="absolute inset-0 w-full h-full object-cover opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a1a] via-[#0a0a1a]/70 to-transparent" />
        <div className="relative h-full max-w-5xl mx-auto px-6 flex flex-col justify-end pb-8">
          <button onClick={() => navigate('/')} className="self-end text-xs text-fuchsia-300 hover:text-fuchsia-100 mb-3 flex items-center gap-1" data-testid="back-home-btn">
            <ArrowRight className="w-3.5 h-3.5" />
            رجوع
          </button>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-fuchsia-500/20 border border-fuchsia-400/40 text-fuchsia-200">جديد</span>
            <span className="text-[11px] text-zinc-400">قسم متخصّص للمواقع الموجودة</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-black bg-gradient-to-r from-fuchsia-300 via-rose-300 to-amber-300 bg-clip-text text-transparent">
            تكملة مشروع
          </h1>
          <p className="text-sm sm:text-base text-zinc-300 mt-2 max-w-2xl leading-relaxed">
            عندك موقع شغّال وتبي تكمّله، تطوّره، أو تعمل صيانة؟ ارفعه هنا والذكاء الصناعي يفحصه كامل،
            يطلع لك تقرير شامل (نقاط ضعف + فرص تحسين)، ثم يتابع التطوير معك خطوة بخطوة.
          </p>
        </div>
      </div>

      {/* Stages preview */}
      <div className="max-w-5xl mx-auto px-6 py-8">
        <h2 className="text-base font-bold text-zinc-300 mb-4">المراحل اللي راح يمشي معك فيها</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-10">
          {[
            { icon: '🔍', title: 'استكشاف', desc: 'قراءة الموقع' },
            { icon: '📋', title: 'تشخيص', desc: 'تقرير شامل' },
            { icon: '🎯', title: 'خطة', desc: 'صيانة + تطوير' },
            { icon: '✨', title: 'أول تحديث', desc: 'تجربة مجانية' },
            { icon: '🛠️', title: 'التنفيذ', desc: 'بعد التفعيل' },
            { icon: '🚀', title: 'متابعة', desc: 'صيانة مستمرة' },
          ].map((p, i) => (
            <div key={i} data-testid={`continuation-phase-${i + 1}`}
                 className="rounded-xl border border-fuchsia-500/15 bg-fuchsia-500/5 hover:bg-fuchsia-500/10 transition p-3 text-center">
              <div className="text-2xl mb-1">{p.icon}</div>
              <div className="text-xs font-bold text-fuchsia-200">{i + 1}. {p.title}</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">{p.desc}</div>
            </div>
          ))}
        </div>

        {/* Mode toggle */}
        <div className="flex gap-2 mb-4">
          {[
            { id: 'url', label: 'رابط الموقع', icon: <Globe className="w-3.5 h-3.5" /> },
            { id: 'description', label: 'وصف بدون رابط', icon: <FileText className="w-3.5 h-3.5" /> },
          ].map((t) => (
            <button key={t.id} data-testid={`continuation-mode-${t.id}`} onClick={() => setMode(t.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition ${
                      mode === t.id ? 'bg-fuchsia-500/30 border border-fuchsia-400/50 text-fuchsia-100'
                                    : 'bg-white/5 border border-white/10 text-zinc-400 hover:bg-white/10'
                    }`}>
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {/* Form */}
        <div className="rounded-2xl border border-fuchsia-500/20 bg-black/30 p-5 sm:p-6 backdrop-blur-sm" data-testid="continuation-form">
          {mode === 'url' && (
            <div className="mb-4">
              <label className="block text-xs font-bold text-zinc-400 mb-2">رابط الموقع الكامل</label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://mywebsite.com"
                dir="ltr"
                data-testid="continuation-url-input"
                className="w-full px-4 py-3 rounded-lg bg-black/40 border border-white/10 text-sm focus:border-fuchsia-400/50 focus:outline-none"
              />
              <p className="text-[10px] text-zinc-500 mt-2 leading-relaxed">
                💡 الذكاء يقرأ HTML، CSS، ويلاحظ التصميم + الأداء. لو الموقع يحتاج تسجيل دخول، اكتب تفاصيل في الحقل تحت.
              </p>
            </div>
          )}

          <div className="mb-4">
            <label className="block text-xs font-bold text-zinc-400 mb-2">
              وصف المشروع {mode === 'description' ? '(إلزامي)' : '(اختياري — لكن مهم)'}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="مثال: موقع مطعمي، فيه قائمة طعام + نموذج حجز. أبغى أضيف قسم الطلب الإلكتروني + تحسين سرعة الصفحة الرئيسية + ربط Stripe..."
              rows={4}
              data-testid="continuation-description-input"
              className="w-full px-4 py-3 rounded-lg bg-black/40 border border-white/10 text-sm focus:border-fuchsia-400/50 focus:outline-none resize-none leading-relaxed"
            />
          </div>

          <div className="mb-5">
            <label className="block text-xs font-bold text-zinc-400 mb-2 flex items-center gap-1.5">
              <Lock className="w-3 h-3" />
              ملاحظة وصول (اختياري)
            </label>
            <input
              type="text"
              value={accessNote}
              onChange={(e) => setAccessNote(e.target.value)}
              placeholder="مثلاً: لازم تسجل دخول بـ demo@.../pwd123 لرؤية لوحة التحكم"
              data-testid="continuation-access-input"
              className="w-full px-4 py-3 rounded-lg bg-black/40 border border-white/10 text-sm focus:border-fuchsia-400/50 focus:outline-none"
            />
            <p className="text-[10px] text-zinc-500 mt-1">المعلومات الحساسة (كلمات سر، API keys) لا تشاركها هنا — استخدم Concierge Vault داخل الشات.</p>
          </div>

          {/* Pricing notice */}
          <div className="mb-5 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 flex items-start gap-3" data-testid="continuation-pricing-notice">
            <Sparkles className="w-5 h-5 text-amber-300 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-amber-100 leading-relaxed">
              <strong className="text-amber-200">مجاني للبدء — $100 لتفعيل التنفيذ</strong>
              <p className="mt-1 text-amber-200/80">
                الذكاء يحلّل مشروعك ويطلع لك التقرير + أول تحديث <strong>مجاناً تماماً</strong>.
                بعد ما تشوف الجودة وتعجبك، تدفع $100 (مرة وحدة) لفتح التنفيذ الكامل + المتابعة المستمرة.
                <span className="text-amber-300 font-bold"> صفر مخاطرة — تجرّب أولاً، تدفع لاحقاً.</span>
              </p>
            </div>
          </div>

          <button
            onClick={submit}
            disabled={busy}
            data-testid="continuation-submit-btn"
            className="w-full py-3.5 rounded-xl bg-gradient-to-r from-fuchsia-500 to-rose-500 hover:from-fuchsia-400 hover:to-rose-400 transition font-black text-sm text-white shadow-lg shadow-fuchsia-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {busy ? (
              <>
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                جاري الإنشاء...
              </>
            ) : (
              <>
                <Code className="w-4 h-4" />
                ابدأ التحليل + المحادثة
              </>
            )}
          </button>

          <p className="text-[10px] text-zinc-500 mt-3 text-center flex items-center justify-center gap-1.5">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            بياناتك آمنة — لا نشارك كودك مع أي طرف ثالث
          </p>
        </div>
      </div>
    </div>
  );
}
