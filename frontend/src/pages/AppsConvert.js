import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowRight, Smartphone, Globe, Download, ExternalLink, Loader2,
  Package, Palette, Tag, Sparkles, CheckCircle2, Apple, Cpu,
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const APP_TYPES = [
  {
    id: 'pwa',
    label: 'PWA (Progressive Web App)',
    icon: Globe,
    desc: 'يتثبّت من المتصفّح مباشرة. أسرع طريقة للنشر — يدعم iOS و Android بدون متجر.',
    perks: ['تثبيت من المتصفح', 'offline cache', 'icon بشاشة البدء', 'لا يحتاج متجر'],
    color: 'emerald',
  },
  {
    id: 'hybrid',
    label: 'Hybrid (Capacitor — Android + iOS)',
    icon: Smartphone,
    desc: 'حزمة Capacitor جاهزة. تفتحها في Android Studio أو Xcode وتنشر على App Store / Play Store.',
    perks: ['Native shell', 'صلاحيات Camera/Geo', 'متاجر التطبيقات', 'web tech تحت الغطاء'],
    color: 'cyan',
  },
];

export default function AppsConvert() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState(false);
  const [savedField, setSavedField] = useState('');

  // local editable fields
  const [name, setName] = useState('');
  const [pkg, setPkg] = useState('com.zitex.app');
  const [color, setColor] = useState('#10b981');
  const [appType, setAppType] = useState('pwa');

  useEffect(() => {
    (async () => {
      const token = localStorage.getItem('token');
      try {
        const r = await fetch(`${API}/api/freebuild-chat/app-conversion/${id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok) {
          const d = await r.json().catch(() => ({}));
          throw new Error(d.detail || 'تحويل غير موجود');
        }
        const d = await r.json();
        setDoc(d);
        setName(d.name || '');
        setPkg(d.package_id || 'com.zitex.app');
        setColor(d.primary_color || '#10b981');
        setAppType(d.app_type || 'pwa');
      } catch (e) {
        toast.error(e.message);
        navigate('/dashboard');
      } finally {
        setLoading(false);
      }
    })();
  }, [id, navigate]);

  const saveField = async (field, value) => {
    const token = localStorage.getItem('token');
    const fd = new FormData();
    fd.append(field, value);
    try {
      const r = await fetch(`${API}/api/freebuild-chat/app-conversion/${id}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (r.ok) {
        setSavedField(field);
        setTimeout(() => setSavedField(''), 1500);
      }
    } catch { /* ignore save errors */ }
  };

  const build = async () => {
    if (building) return;
    setBuilding(true);
    const token = localStorage.getItem('token');
    try {
      // ensure latest meta saved first
      await Promise.all([
        saveField('name', name),
        saveField('package_id', pkg),
        saveField('primary_color', color),
        saveField('app_type', appType),
      ]);
      const r = await fetch(`${API}/api/freebuild-chat/app-conversion/${id}/build`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'فشل البناء');
      setDoc({ ...doc, status: 'built', last_build: data });
      toast.success(`✨ تم بناء التطبيق — ${data.files?.length || 0} ملف`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBuilding(false);
    }
  };

  if (loading) {
    return (
      <div dir="rtl" className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (!doc) return null;

  const lastBuild = doc.last_build;
  const previewUrl = lastBuild?.preview_url ? `${API}${lastBuild.preview_url}` : null;
  const zipUrl = lastBuild?.zip_url ? `${API}${lastBuild.zip_url}` : null;

  return (
    <div dir="rtl" className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-cyan-950/20 text-white">
      {/* Top bar */}
      <div className="border-b border-white/10 bg-black/30 backdrop-blur sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <button
            type="button"
            onClick={() => navigate('/freebuild/chat')}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 text-sm"
            data-testid="back-to-freebuild"
          >
            <ArrowRight className="w-4 h-4" />
            رجوع إلى FreeBuild
          </button>
          <div className="text-xs text-zinc-400">
            <span className="text-emerald-300 font-bold">🚀 محوّل التطبيقات</span>
            <span className="mx-2">·</span>
            <span>المصدر: موقع FreeBuild</span>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8 grid lg:grid-cols-[1fr_400px] gap-8">
        {/* LEFT: configuration */}
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-black mb-2 flex items-center gap-3" data-testid="apps-convert-title">
              <Smartphone className="w-8 h-8 text-cyan-400" />
              حوّل موقعك إلى تطبيق
            </h1>
            <p className="text-zinc-400 text-sm">
              الموقع <span className="text-emerald-300 font-bold">{doc.name || 'موقع بدون اسم'}</span> جاهز للتحويل. اختر نوع التطبيق وحدّد الإعدادات.
            </p>
          </div>

          {/* App type picker */}
          <div className="space-y-3">
            <h2 className="text-sm text-zinc-300 font-bold flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              نوع التطبيق
            </h2>
            <div className="grid sm:grid-cols-2 gap-3" data-testid="app-type-picker">
              {APP_TYPES.map((t) => {
                const Icon = t.icon;
                const active = appType === t.id;
                return (
                  <button
                    type="button"
                    key={t.id}
                    onClick={() => { setAppType(t.id); saveField('app_type', t.id); }}
                    data-testid={`app-type-${t.id}`}
                    className={`text-right rounded-xl border-2 p-4 transition-all ${
                      active
                        ? `border-${t.color}-400 bg-${t.color}-500/10 ring-2 ring-${t.color}-400/30`
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-${t.color}-500/20 text-${t.color}-300`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      {active && <CheckCircle2 className={`w-5 h-5 text-${t.color}-400`} />}
                    </div>
                    <div className="font-bold text-white text-sm mb-1">{t.label}</div>
                    <p className="text-[11px] text-zinc-400 leading-relaxed mb-2">{t.desc}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {t.perks.map((p) => (
                        <span key={p} className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-zinc-300">
                          {p}
                        </span>
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Metadata */}
          <div className="space-y-3 rounded-xl border border-white/10 bg-white/5 p-4">
            <h2 className="text-sm text-zinc-300 font-bold flex items-center gap-2">
              <Tag className="w-4 h-4" />
              معلومات التطبيق
            </h2>

            <label className="block">
              <span className="text-[11px] text-zinc-400 flex items-center gap-1">
                اسم التطبيق
                {savedField === 'name' && <span className="text-emerald-400 text-[10px]">✓ تم الحفظ</span>}
              </span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                onBlur={() => saveField('name', name)}
                data-testid="app-name-input"
                className="mt-1 w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/10 focus:border-emerald-400 outline-none text-sm"
                placeholder="مثال: مطعم زيتاكس"
              />
            </label>

            <label className="block">
              <span className="text-[11px] text-zinc-400 flex items-center gap-1">
                <Package className="w-3 h-3" />
                Package ID (للمتاجر)
                {savedField === 'package_id' && <span className="text-emerald-400 text-[10px]">✓ تم الحفظ</span>}
              </span>
              <input
                value={pkg}
                onChange={(e) => setPkg(e.target.value)}
                onBlur={() => saveField('package_id', pkg)}
                data-testid="app-package-input"
                className="mt-1 w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/10 focus:border-emerald-400 outline-none text-sm font-mono"
                placeholder="com.example.app"
                dir="ltr"
              />
              <span className="text-[10px] text-zinc-500 mt-1 block">حروف صغيرة + نقاط + شرطات فقط</span>
            </label>

            <label className="block">
              <span className="text-[11px] text-zinc-400 flex items-center gap-1">
                <Palette className="w-3 h-3" />
                اللون الأساسي
                {savedField === 'primary_color' && <span className="text-emerald-400 text-[10px]">✓ تم الحفظ</span>}
              </span>
              <div className="mt-1 flex items-center gap-2">
                <input
                  type="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  onBlur={() => saveField('primary_color', color)}
                  data-testid="app-color-input"
                  className="w-12 h-10 rounded-lg cursor-pointer border border-white/10 bg-zinc-900"
                />
                <input
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  onBlur={() => saveField('primary_color', color)}
                  className="flex-1 px-3 py-2 rounded-lg bg-zinc-900 border border-white/10 outline-none text-sm font-mono"
                  dir="ltr"
                />
              </div>
            </label>
          </div>

          {/* Build button */}
          <button
            type="button"
            onClick={build}
            disabled={building}
            data-testid="build-app-btn"
            className="w-full py-4 rounded-2xl bg-gradient-to-r from-emerald-500 to-cyan-600 hover:from-emerald-400 hover:to-cyan-500 disabled:opacity-50 disabled:cursor-wait text-black text-base font-black shadow-2xl shadow-emerald-500/30 flex items-center justify-center gap-2"
          >
            {building ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>جاري البناء... (10-30 ثانية)</span>
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                <span>ابدأ بناء التطبيق</span>
              </>
            )}
          </button>

          {/* Build result */}
          {lastBuild && (
            <div className="rounded-xl border-2 border-emerald-400/40 bg-emerald-500/5 p-5 space-y-4" data-testid="build-result">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-emerald-200">تم البناء بنجاح</h3>
                <span className="text-[10px] text-zinc-400 mr-auto">
                  {lastBuild.files?.length || 0} ملف · {((lastBuild.bundle_size || 0) / 1024).toFixed(1)} KB
                </span>
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                {previewUrl && (
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    data-testid="open-preview-btn"
                    className="px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-cyan-400/30 text-cyan-200 text-sm font-bold flex items-center justify-center gap-2"
                  >
                    <ExternalLink className="w-4 h-4" />
                    افتح المعاينة
                  </a>
                )}
                {zipUrl && (
                  <a
                    href={zipUrl}
                    download={`${name || 'app'}.zip`}
                    data-testid="download-zip-btn"
                    className="px-4 py-3 rounded-xl bg-gradient-to-r from-emerald-500/30 to-cyan-500/30 hover:from-emerald-500/40 hover:to-cyan-500/40 border border-emerald-400/40 text-emerald-100 text-sm font-bold flex items-center justify-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    تنزيل ZIP
                  </a>
                )}
              </div>
              {appType === 'hybrid' && (
                <div className="rounded-lg bg-black/30 border border-white/10 p-3 text-[11px] text-zinc-300 leading-relaxed space-y-1.5">
                  <div className="font-bold text-cyan-300 mb-1 flex items-center gap-1.5">
                    <Apple className="w-3.5 h-3.5" /> خطوات النشر على iOS + Android:
                  </div>
                  <div>1. فك ضغط الـZIP في مجلد على جهازك.</div>
                  <div className="font-mono text-cyan-200 bg-black/40 px-2 py-1 rounded" dir="ltr">npm install</div>
                  <div className="font-mono text-cyan-200 bg-black/40 px-2 py-1 rounded" dir="ltr">npx cap add android &amp;&amp; npx cap add ios</div>
                  <div className="font-mono text-cyan-200 bg-black/40 px-2 py-1 rounded" dir="ltr">npx cap open android  # أو ios</div>
                  <div>2. افتح Android Studio / Xcode وعدّل الأيقونات + شاشة البدء، ثم انشر.</div>
                </div>
              )}
              {appType === 'pwa' && (
                <div className="rounded-lg bg-black/30 border border-white/10 p-3 text-[11px] text-zinc-300 leading-relaxed">
                  <div className="font-bold text-emerald-300 mb-1">للنشر كـPWA:</div>
                  ارفع محتوى الـZIP على أي استضافة (Vercel/Netlify/Cloudflare Pages) — المتصفّح راح يكتشف الـmanifest.json تلقائياً ويعرض زر &ldquo;ثبّت التطبيق&rdquo;.
                </div>
              )}
            </div>
          )}
        </div>

        {/* RIGHT: source preview */}
        <div className="space-y-4">
          <h2 className="text-sm text-zinc-300 font-bold">معاينة الموقع المصدر</h2>
          <div className="rounded-2xl overflow-hidden border-2 border-white/10 bg-white" style={{ aspectRatio: '9 / 16' }}>
            {doc.current_html ? (
              <iframe
                title="source-preview"
                srcDoc={doc.current_html}
                sandbox=""
                className="w-full h-full border-none"
                data-testid="source-preview-iframe"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-zinc-500 text-sm">
                لا يوجد HTML
              </div>
            )}
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-[11px] text-zinc-400 leading-relaxed">
            <span className="text-emerald-300 font-bold">ملاحظة:</span> التحويل يأخذ نسخة من HTML الموقع ويغلّفها في shell تطبيق. أي تعديل لاحق على الموقع لن ينعكس تلقائياً — تحتاج تعيد البناء.
          </div>
        </div>
      </div>
    </div>
  );
}
