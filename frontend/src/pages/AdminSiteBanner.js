/**
 * Admin: Site Banner & Stories Management
 * Simple, complete CRUD: rotating banner slides + stories ribbon
 * + AI generation (image / video) + per-placement targeting (outside/inside/both).
 */
import React, { useEffect, useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { toast } from 'sonner';
import SiteBannerStories from '@/components/SiteBannerStories';

const API = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ Authorization: `Bearer ${localStorage.getItem('token') || ''}` });
const authJson = () => ({ ...auth(), 'Content-Type': 'application/json' });

const BLANK_SLIDE = {
  type: 'image', media_url: '', title: '', subtitle: '',
  cta_text: '', cta_link: '', duration_sec: 6, visible: true, placement: 'both',
};
const BLANK_STORY = {
  type: 'image', media_url: '', caption: '', link: '',
  duration_sec: 6, visible: true, placement: 'both',
};

export default function AdminSiteBanner() {
  const [tab, setTab] = useState('banner'); // 'banner' | 'stories' | 'preview'
  const [slides, setSlides] = useState([]);
  const [stories, setStories] = useState([]);
  const [settings, setSettings] = useState({ rotate_seconds: 6, animation: 'fade', overlay_opacity: 0.5 });
  const [editingSlide, setEditingSlide] = useState(null);
  const [editingStory, setEditingStory] = useState(null);
  const [genPrompt, setGenPrompt] = useState('');
  const [genTarget, setGenTarget] = useState('banner');
  const [genBusy, setGenBusy] = useState(false);
  const [vidPrompt, setVidPrompt] = useState('');
  const [vidJob, setVidJob] = useState(null);

  const load = async () => {
    try {
      const [b, s] = await Promise.all([
        fetch(`${API}/api/site/banner`).then(r => r.json()),
        fetch(`${API}/api/site/stories`).then(r => r.json()),
      ]);
      setSlides(b.slides || []);
      setSettings({
        rotate_seconds: b.rotate_seconds ?? 6,
        animation: b.animation || 'fade',
        overlay_opacity: b.overlay_opacity ?? 0.5,
      });
      setStories(s.stories || []);
    } catch (_) { toast.error('فشل التحميل'); }
  };
  useEffect(() => { load(); }, []);

  // Poll video job
  useEffect(() => {
    if (!vidJob || vidJob.status === 'done' || vidJob.status === 'failed') return;
    const t = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/site/media/jobs/${vidJob.job_id}`, { headers: auth() });
        if (!r.ok) return;
        const d = await r.json();
        setVidJob({ ...vidJob, ...d });
        if (d.status === 'done') { clearInterval(t); toast.success('🎬 تم توليد الفيديو'); load(); }
        if (d.status === 'failed') { clearInterval(t); toast.error('فشل توليد الفيديو'); }
      } catch (_) {}
    }, 5000);
    return () => clearInterval(t);
  }, [vidJob]);

  const uploadFile = (file, target) => {
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) { toast.error('الحد 8 ميجا'); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      const url = reader.result;
      const isVideo = file.type.startsWith('video/');
      if (target === 'banner') {
        await fetch(`${API}/api/site/banner/slides`, {
          method: 'POST', headers: authJson(),
          body: JSON.stringify({ ...BLANK_SLIDE, type: isVideo ? 'video' : 'image', media_url: url }),
        });
      } else {
        await fetch(`${API}/api/site/stories`, {
          method: 'POST', headers: authJson(),
          body: JSON.stringify({ ...BLANK_STORY, type: isVideo ? 'video' : 'image', media_url: url }),
        });
      }
      toast.success('✅ تم الرفع');
      load();
    };
    reader.readAsDataURL(file);
  };

  const generateImage = async () => {
    if (!genPrompt.trim()) return;
    setGenBusy(true);
    try {
      const r = await fetch(`${API}/api/site/media/generate-image`, {
        method: 'POST', headers: authJson(),
        body: JSON.stringify({ prompt: genPrompt, target: genTarget }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      toast.success('✨ تم التوليد');
      setGenPrompt('');
      load();
    } catch (e) { toast.error(e.message); }
    finally { setGenBusy(false); }
  };

  const generateVideo = async () => {
    if (!vidPrompt.trim()) return;
    try {
      const r = await fetch(`${API}/api/site/media/generate-video`, {
        method: 'POST', headers: authJson(),
        body: JSON.stringify({ prompt: vidPrompt, duration: 4, size: '1280x720', target: genTarget }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setVidJob({ job_id: d.job_id, status: 'queued' });
      toast.success(`🎬 بدأ التوليد (≈${Math.round(d.estimated_seconds / 60)} دقيقة)`);
      setVidPrompt('');
    } catch (e) { toast.error(e.message); }
  };

  const saveSlide = async (s) => {
    const isNew = !s.id;
    const url = isNew ? `${API}/api/site/banner/slides` : `${API}/api/site/banner/slides/${s.id}`;
    const method = isNew ? 'POST' : 'PATCH';
    const body = isNew ? s : (() => { const { id, ...rest } = s; return rest; })();
    const r = await fetch(url, { method, headers: authJson(), body: JSON.stringify(body) });
    if (!r.ok) { toast.error('فشل الحفظ'); return; }
    toast.success('✅ تم الحفظ');
    setEditingSlide(null);
    load();
  };
  const delSlide = async (id) => {
    if (!window.confirm('حذف هذا السلايد؟')) return;
    await fetch(`${API}/api/site/banner/slides/${id}`, { method: 'DELETE', headers: auth() });
    load();
  };

  const saveStory = async (s) => {
    const isNew = !s.id;
    const url = isNew ? `${API}/api/site/stories` : `${API}/api/site/stories/${s.id}`;
    const method = isNew ? 'POST' : 'PATCH';
    const body = isNew ? s : (() => { const { id, ...rest } = s; return rest; })();
    const r = await fetch(url, { method, headers: authJson(), body: JSON.stringify(body) });
    if (!r.ok) { toast.error('فشل الحفظ'); return; }
    toast.success('✅ تم الحفظ');
    setEditingStory(null);
    load();
  };
  const delStory = async (id) => {
    if (!window.confirm('حذف هذه الحالة؟')) return;
    await fetch(`${API}/api/site/stories/${id}`, { method: 'DELETE', headers: auth() });
    load();
  };

  const saveSettings = async () => {
    const r = await fetch(`${API}/api/site/banner/settings`, {
      method: 'PUT', headers: authJson(), body: JSON.stringify(settings),
    });
    if (!r.ok) { toast.error('فشل'); return; }
    toast.success('✅ تم حفظ الإعدادات');
    load();
  };

  return (
    <div className="min-h-screen bg-[#0a0a12] text-white" data-testid="admin-site-banner" dir="rtl">
      <Navbar transparent />
      <div className="container mx-auto px-4 md:px-8 max-w-6xl pt-24 pb-12">
        <h1 className="text-3xl font-black mb-2 bg-gradient-to-r from-amber-400 to-yellow-500 bg-clip-text text-transparent">🎬 إدارة البنر والحالات</h1>
        <p className="text-sm opacity-70 mb-6">تتحكّم بالبنر الدوّار والحالات الظاهرة على Zitex (داخل وخارج الموقع).</p>

        <div className="flex gap-1 p-1 bg-white/5 rounded-xl w-fit mb-6">
          {[
            { id: 'banner', label: '🌅 البنر الدوّار' },
            { id: 'stories', label: '⭕ الحالات' },
            { id: 'preview', label: '👁️ معاينة' },
          ].map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-4 py-2 rounded-lg text-sm font-bold ${tab === t.id ? 'bg-amber-500 text-black' : 'hover:bg-white/5'}`}
              data-testid={`asb-tab-${t.id}`}>{t.label}</button>
          ))}
        </div>

        {/* AI generation panel (shared) */}
        {tab !== 'preview' && (
          <div className="bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 border border-emerald-400/30 rounded-2xl p-4 mb-6">
            <h3 className="font-bold text-sm mb-2">✨ توليد بالذكاء الاصطناعي</h3>
            <div className="flex flex-wrap gap-2 items-center">
              <select value={genTarget} onChange={(e) => setGenTarget(e.target.value)}
                className="px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm">
                <option value="banner">🌅 سلايد بنر</option>
                <option value="story">⭕ Story</option>
              </select>
              <input value={genPrompt} onChange={(e) => setGenPrompt(e.target.value)}
                placeholder="مثال: لوحة فخمة لمنصة AI ساطعة بألوان ذهبية"
                className="flex-1 min-w-[300px] px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm"
                data-testid="asb-gen-prompt" />
              <button onClick={generateImage} disabled={genBusy || !genPrompt.trim()}
                className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-black font-black rounded-lg text-sm disabled:opacity-40"
                data-testid="asb-gen-image">
                {genBusy ? '⏳' : '✨ صورة'}
              </button>
            </div>
            <div className="flex flex-wrap gap-2 items-center mt-2">
              <input value={vidPrompt} onChange={(e) => setVidPrompt(e.target.value)}
                placeholder="فيديو (Sora 2): مشهد سينمائي 4 ثوانٍ"
                className="flex-1 min-w-[300px] px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm"
                data-testid="asb-vid-prompt" />
              <button onClick={generateVideo} disabled={!vidPrompt.trim() || (vidJob && !['done', 'failed'].includes(vidJob.status))}
                className="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white font-black rounded-lg text-sm disabled:opacity-40"
                data-testid="asb-gen-video">🎥 فيديو</button>
            </div>
            {vidJob && (
              <div className="mt-2 p-2 bg-black/30 rounded text-[11px]">
                {vidJob.status === 'queued' && '⏳ في الانتظار...'}
                {vidJob.status === 'processing' && <span className="animate-pulse">🎥 جارٍ توليد الفيديو...</span>}
                {vidJob.status === 'done' && '✅ تم!'}
                {vidJob.status === 'failed' && `❌ ${vidJob.error}`}
              </div>
            )}
          </div>
        )}

        {tab === 'banner' && (
          <div className="space-y-5">
            {/* Banner settings */}
            <div className="bg-white/5 border border-white/10 rounded-xl p-4">
              <h3 className="font-bold text-sm mb-3">⚙️ إعدادات الدوران</h3>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="text-[11px] opacity-70">الفترة بين السلايدات (ثوانٍ)</span>
                  <input type="number" min="2" max="30" value={settings.rotate_seconds}
                    onChange={(e) => setSettings({ ...settings, rotate_seconds: +e.target.value })}
                    className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" data-testid="asb-rotate-sec" />
                </label>
                <label className="block">
                  <span className="text-[11px] opacity-70">نوع الانتقال</span>
                  <select value={settings.animation} onChange={(e) => setSettings({ ...settings, animation: e.target.value })}
                    className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" data-testid="asb-animation">
                    <option value="fade">تلاشي</option>
                    <option value="slide">انزلاق</option>
                    <option value="kenburns">Ken Burns</option>
                  </select>
                </label>
              </div>
              <button onClick={saveSettings} className="mt-3 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black rounded-lg text-sm font-black" data-testid="asb-save-settings">💾 حفظ الإعدادات</button>
            </div>

            {/* Add */}
            <div className="flex gap-2 flex-wrap items-center">
              <button onClick={() => setEditingSlide(BLANK_SLIDE)} className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black rounded-lg text-sm font-black" data-testid="asb-add-slide">+ سلايد جديد</button>
              <label className="cursor-pointer px-4 py-2 bg-white/10 hover:bg-white/15 rounded-lg text-sm font-bold border border-white/15">
                📁 رفع ملف
                <input type="file" hidden accept="image/*,video/*" onChange={(e) => uploadFile(e.target.files[0], 'banner')} />
              </label>
            </div>

            {/* Slides grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {slides.length === 0 ? <div className="opacity-60 col-span-full text-center py-10 text-sm">لا توجد سلايدات بعد</div>
              : slides.map((s) => (
                <div key={s.id} className="bg-white/5 border border-white/10 rounded-xl overflow-hidden" data-testid={`asb-slide-${s.id}`}>
                  <div className="relative aspect-[16/9] bg-black">
                    {s.type === 'video' ? <video src={s.media_url} className="w-full h-full object-cover" muted autoPlay loop playsInline />
                                        : <img src={s.media_url} className="w-full h-full object-cover" alt="" />}
                    <span className="absolute top-2 left-2 bg-black/60 text-[10px] px-2 py-0.5 rounded">{s.placement}</span>
                  </div>
                  <div className="p-2">
                    <div className="font-bold text-sm truncate">{s.title || '(بدون عنوان)'}</div>
                    <div className="text-[11px] opacity-60 truncate">{s.subtitle || ''}</div>
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => setEditingSlide(s)} className="text-[11px] px-2 py-1 bg-white/10 rounded">تعديل</button>
                      <button onClick={() => delSlide(s.id)} className="text-[11px] px-2 py-1 text-red-300 hover:bg-red-500/20 rounded" data-testid={`asb-del-slide-${s.id}`}>🗑️</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {editingSlide && <EditSlideModal slide={editingSlide} onSave={saveSlide} onCancel={() => setEditingSlide(null)} />}
          </div>
        )}

        {tab === 'stories' && (
          <div className="space-y-4">
            <div className="flex gap-2 flex-wrap items-center">
              <button onClick={() => setEditingStory(BLANK_STORY)} className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black rounded-lg text-sm font-black" data-testid="asb-add-story">+ Story جديدة</button>
              <label className="cursor-pointer px-4 py-2 bg-white/10 hover:bg-white/15 rounded-lg text-sm font-bold border border-white/15">
                📁 رفع ملف
                <input type="file" hidden accept="image/*,video/*" onChange={(e) => uploadFile(e.target.files[0], 'story')} />
              </label>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {stories.length === 0 ? <div className="opacity-60 col-span-full text-center py-10 text-sm">لا توجد حالات بعد</div>
              : stories.map((s) => (
                <div key={s.id} className="bg-white/5 border border-white/10 rounded-xl overflow-hidden" data-testid={`asb-story-${s.id}`}>
                  <div className="relative aspect-[9/16] bg-black">
                    {s.type === 'video' ? <video src={s.media_url} className="w-full h-full object-cover" muted playsInline />
                                        : <img src={s.media_url} className="w-full h-full object-cover" alt="" />}
                    <span className="absolute top-1 left-1 bg-black/60 text-[9px] px-1.5 py-0.5 rounded">{s.placement}</span>
                  </div>
                  <div className="p-1.5">
                    <div className="text-[11px] truncate">{s.caption || '—'}</div>
                    <div className="flex gap-1 mt-1">
                      <button onClick={() => setEditingStory(s)} className="text-[10px] px-2 py-0.5 bg-white/10 rounded">تعديل</button>
                      <button onClick={() => delStory(s.id)} className="text-[10px] px-2 py-0.5 text-red-300" data-testid={`asb-del-story-${s.id}`}>🗑️</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {editingStory && <EditStoryModal story={editingStory} onSave={saveStory} onCancel={() => setEditingStory(null)} />}
          </div>
        )}

        {tab === 'preview' && (
          <div className="space-y-6">
            <div>
              <h3 className="font-bold mb-2">🌐 معاينة "خارج الموقع" (الـ Landing/Login)</h3>
              <div className="border border-white/10 rounded-xl overflow-hidden">
                <SiteBannerStories placement="outside" />
              </div>
            </div>
            <div>
              <h3 className="font-bold mb-2">🏠 معاينة "داخل الموقع" (Dashboard)</h3>
              <div className="border border-white/10 rounded-xl overflow-hidden">
                <SiteBannerStories placement="inside" />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function EditSlideModal({ slide, onSave, onCancel }) {
  const [s, setS] = useState(slide);
  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="bg-[#0e1128] border border-amber-500/30 rounded-2xl p-5 max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <h3 className="font-black text-lg mb-3">{slide.id ? 'تعديل سلايد' : 'سلايد جديد'}</h3>
        <div className="space-y-2 text-sm">
          <Field label="نوع المحتوى">
            <select value={s.type} onChange={(e) => setS({ ...s, type: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm">
              <option value="image">صورة</option><option value="video">فيديو</option>
            </select>
          </Field>
          <Field label="رابط الوسائط (URL أو data:)">
            <input value={s.media_url} onChange={(e) => setS({ ...s, media_url: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm font-mono" data-testid="asb-slide-url" />
          </Field>
          <Field label="العنوان">
            <input value={s.title || ''} onChange={(e) => setS({ ...s, title: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" />
          </Field>
          <Field label="العنوان الفرعي">
            <input value={s.subtitle || ''} onChange={(e) => setS({ ...s, subtitle: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="نص CTA"><input value={s.cta_text || ''} onChange={(e) => setS({ ...s, cta_text: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" /></Field>
            <Field label="رابط CTA"><input value={s.cta_link || ''} onChange={(e) => setS({ ...s, cta_link: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm font-mono" /></Field>
          </div>
          <Field label="الموقع">
            <select value={s.placement || 'both'} onChange={(e) => setS({ ...s, placement: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm">
              <option value="both">الاثنين معاً</option>
              <option value="outside">خارج الموقع (Login)</option>
              <option value="inside">داخل الموقع (Dashboard)</option>
            </select>
          </Field>
          <label className="flex items-center gap-2 mt-2">
            <input type="checkbox" checked={s.visible !== false} onChange={(e) => setS({ ...s, visible: e.target.checked })} />
            <span>ظاهر</span>
          </label>
        </div>
        <div className="flex gap-2 mt-4">
          <button onClick={onCancel} className="flex-1 py-2 bg-white/5 rounded-lg text-sm">إلغاء</button>
          <button onClick={() => onSave(s)} className="flex-2 px-6 py-2 bg-amber-500 text-black rounded-lg text-sm font-black" data-testid="asb-slide-save">💾 حفظ</button>
        </div>
      </div>
    </div>
  );
}

function EditStoryModal({ story, onSave, onCancel }) {
  const [s, setS] = useState(story);
  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="bg-[#0e1128] border border-amber-500/30 rounded-2xl p-5 max-w-md w-full max-h-[90vh] overflow-y-auto">
        <h3 className="font-black text-lg mb-3">{story.id ? 'تعديل Story' : 'Story جديدة'}</h3>
        <div className="space-y-2 text-sm">
          <Field label="نوع المحتوى">
            <select value={s.type} onChange={(e) => setS({ ...s, type: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm">
              <option value="image">صورة</option><option value="video">فيديو</option>
            </select>
          </Field>
          <Field label="رابط الوسائط"><input value={s.media_url} onChange={(e) => setS({ ...s, media_url: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm font-mono" /></Field>
          <Field label="التعليق"><input value={s.caption || ''} onChange={(e) => setS({ ...s, caption: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" /></Field>
          <Field label="رابط (CTA)"><input value={s.link || ''} onChange={(e) => setS({ ...s, link: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm font-mono" /></Field>
          <Field label="الموقع">
            <select value={s.placement || 'both'} onChange={(e) => setS({ ...s, placement: e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm">
              <option value="both">الاثنين معاً</option>
              <option value="outside">خارج (Login)</option>
              <option value="inside">داخل (Dashboard)</option>
            </select>
          </Field>
          <Field label="مدة العرض (ثوانٍ)"><input type="number" min="2" max="20" value={s.duration_sec || 6} onChange={(e) => setS({ ...s, duration_sec: +e.target.value })} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" /></Field>
          <label className="flex items-center gap-2 mt-2">
            <input type="checkbox" checked={s.visible !== false} onChange={(e) => setS({ ...s, visible: e.target.checked })} />
            <span>ظاهرة</span>
          </label>
        </div>
        <div className="flex gap-2 mt-4">
          <button onClick={onCancel} className="flex-1 py-2 bg-white/5 rounded-lg text-sm">إلغاء</button>
          <button onClick={() => onSave(s)} className="flex-2 px-6 py-2 bg-amber-500 text-black rounded-lg text-sm font-black" data-testid="asb-story-save">💾 حفظ</button>
        </div>
      </div>
    </div>
  );
}

const Field = ({ label, children }) => (
  <label className="block">
    <span className="text-[11px] opacity-70 mb-0.5 block">{label}</span>
    {children}
  </label>
);
