import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Smartphone, Plus, Loader2, Check, ArrowLeft, Sparkles, MessageSquare,
  Trash2, Layers, Megaphone, Coins, ShoppingBag, Wand2, Upload,
  Globe, Box, Code2, AppWindow, CheckCircle2, Info,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const AS = `${API}/api/app-studio`;
const auth = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
});

const TYPE_ICON = { pwa: Globe, hybrid: AppWindow, native: Code2, fullstack: Box };
const TYPE_COLOR = {
  pwa: 'from-sky-500/15 to-sky-500/5 border-sky-500/40 text-sky-200',
  hybrid: 'from-emerald-500/15 to-emerald-500/5 border-emerald-500/40 text-emerald-200',
  native: 'from-amber-500/15 to-amber-500/5 border-amber-500/40 text-amber-200',
  fullstack: 'from-violet-500/15 to-violet-500/5 border-violet-500/40 text-violet-200',
};

const CAT_ICON = { core: Box, screen: Layers, money: Coins, addon: Megaphone, ai: Sparkles };

const WIZARD_STEPS = [
  { id: 'discover', label: '١. اكتشاف الفكرة' },
  { id: 'features', label: '٢. الميزات' },
  { id: 'addons',   label: '٣. الإضافات' },
  { id: 'launch',   label: '٤. الإطلاق' },
];

export default function AppStudio() {
  const navigate = useNavigate();
  const [opts, setOpts] = useState({ project_types: [], features: [], feature_categories: [] });
  const [projects, setProjects] = useState([]);
  const [activeId, setActiveId] = useState('');
  const [active, setActive] = useState(null);
  const [features, setFeatures] = useState([]);

  // Chat / wizard
  const [step, setStep] = useState('discover');
  const [reply, setReply] = useState('');
  const [chatBusy, setChatBusy] = useState(false);
  const [msg, setMsg] = useState('');

  // Modals
  const [showNew, setShowNew] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importable, setImportable] = useState([]);
  const [tab, setTab] = useState('chat'); // chat | features | imports

  // Load catalogues + projects
  useEffect(() => {
    fetch(`${AS}/options`, { headers: auth() }).then((r) => r.json()).then((d) => d.ok && setOpts(d));
  }, []);
  const loadProjects = useCallback(async () => {
    try {
      const r = await fetch(`${AS}/projects`, { headers: auth() });
      const d = await r.json();
      setProjects(d.projects || []);
    } catch { /* */ }
  }, []);
  useEffect(() => { loadProjects(); }, [loadProjects]);

  const loadProject = useCallback(async (pid) => {
    if (!pid) { setActive(null); setFeatures([]); return; }
    try {
      const r = await fetch(`${AS}/projects/${pid}`, { headers: auth() });
      const d = await r.json();
      setActive(d.project);
      setFeatures(d.features || []);
    } catch { toast.error('فشل تحميل المشروع'); }
  }, []);
  useEffect(() => { loadProject(activeId); }, [activeId, loadProject]);

  const askProducer = useCallback(async (m = '') => {
    if (!activeId) return;
    setChatBusy(true);
    try {
      const r = await fetch(`${AS}/producer-chat`, {
        method: 'POST', headers: auth(),
        body: JSON.stringify({ project_id: activeId, step, message: m || `أرشدني في مرحلة ${step}` }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      setReply(d.reply || '');
      setMsg('');
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
    finally { setChatBusy(false); }
  }, [activeId, step]);
  useEffect(() => { if (activeId) askProducer(); /* auto-ask on step change */ // eslint-disable-next-line
  }, [step, activeId]);

  const addFeature = async (feature_id) => {
    if (!activeId) return;
    const feat = opts.features.find((f) => f.id === feature_id);
    if (!window.confirm(`أضف "${feat?.label_ar}" بتكلفة ${feat?.cost} نقطة؟`)) return;
    try {
      const r = await fetch(`${AS}/feature/add`, {
        method: 'POST', headers: auth(),
        body: JSON.stringify({ project_id: activeId, feature_id, config: {} }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      toast.success(`تمت الإضافة · خُصم ${d.credits_charged} نقطة`);
      loadProject(activeId);
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
  };

  const removeFeature = async (fdbId) => {
    if (!window.confirm('احذف الميزة؟ (النقاط لا تُسترجع)')) return;
    await fetch(`${AS}/feature/${fdbId}`, { method: 'DELETE', headers: auth() });
    loadProject(activeId);
  };

  const openImport = async () => {
    setShowImport(true);
    try {
      const r = await fetch(`${AS}/importable`, { headers: auth() });
      setImportable((await r.json()).items || []);
    } catch { /* */ }
  };
  const doImport = async (source) => {
    try {
      const r = await fetch(`${AS}/import`, {
        method: 'POST', headers: auth(),
        body: JSON.stringify({ project_id: activeId, source }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      toast.success(d.note || 'تم الاستيراد');
      setShowImport(false);
      loadProject(activeId);
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
  };

  const featsByCat = (cat) => (opts.features || []).filter((f) => f.category === cat);
  const ownedIds = new Set(features.map((f) => f.feature_id));
  const ownedCost = features.reduce((sum, f) => sum + (f.cost || 0), 0);
  const buildCost = active ? (opts.project_types.find((t) => t.id === active.type) || {}).build_cost : 0;
  const totalCost = ownedCost + (buildCost || 0);

  return (
    <div className="min-h-screen bg-[#0b0d12] text-zinc-100 flex" dir="rtl" data-testid="app-studio-page">
      {/* ── LEFT: Projects sidebar ───────────────────────────────── */}
      <aside className="w-64 border-l border-zinc-800 bg-[#0e1118] flex flex-col shrink-0">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-3">
          <button onClick={() => navigate('/dashboard')} className="p-2 rounded-lg hover:bg-zinc-800" data-testid="back-btn">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2">
            <Smartphone className="w-5 h-5 text-indigo-400" />
            <h1 className="text-sm font-semibold">استوديو التطبيقات</h1>
          </div>
        </div>

        <button onClick={() => setShowNew(true)}
          className="m-3 px-3 py-2 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 rounded-lg text-sm font-medium text-indigo-200 flex items-center justify-center gap-2"
          data-testid="new-project-btn">
          <Plus className="w-4 h-4" /> مشروع جديد
        </button>

        <div className="flex-1 overflow-y-auto px-3 pb-3">
          <div className="text-xs text-zinc-500 px-2 pb-2">مشاريعك</div>
          {projects.length === 0 && <div className="text-xs text-zinc-600 px-2 py-6 text-center">ما عندك مشاريع.</div>}
          {projects.map((p) => {
            const Icon = TYPE_ICON[p.type] || Smartphone;
            return (
              <button key={p.id} onClick={() => setActiveId(p.id)}
                className={`w-full text-right px-3 py-2 mb-1 rounded-lg text-sm transition ${
                  activeId === p.id ? 'bg-indigo-500/15 text-indigo-100 border border-indigo-500/30'
                                    : 'hover:bg-zinc-800 text-zinc-300 border border-transparent'
                }`} data-testid={`project-item-${p.id}`}>
                <div className="flex items-center gap-2">
                  <Icon className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <span className="font-medium truncate">{p.title}</span>
                </div>
                <div className="text-[10px] text-zinc-500 mt-0.5">{p.type_label} · {p.features_count || 0} ميزة</div>
              </button>
            );
          })}
        </div>
      </aside>

      {/* ── CENTER: Main pane ──────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between bg-[#0e1118]">
          <div className="min-w-0">
            {active ? (
              <>
                <div className="text-sm font-medium truncate">{active.title}</div>
                <div className="text-xs text-zinc-500 truncate">{active.type_label} · {active.description || 'بلا وصف'}</div>
              </>
            ) : (
              <div className="text-sm text-zinc-400">اختر مشروع أو أنشئ جديد</div>
            )}
          </div>
          {active && (
            <button onClick={openImport}
              className="text-xs px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 flex items-center gap-1.5" data-testid="import-existing-btn">
              <Upload className="w-3 h-3" /> استورد موقع/تطبيق سابق
            </button>
          )}
        </header>

        {/* Tabs */}
        {active && (
          <div className="border-b border-zinc-800 px-4 flex items-center gap-1 bg-[#0e1118]/60">
            {[
              { id: 'chat',     label: 'محادثة المنتج', icon: <MessageSquare className="w-3.5 h-3.5" /> },
              { id: 'features', label: 'الميزات',       icon: <Wand2 className="w-3.5 h-3.5" /> },
              { id: 'imports',  label: 'المستوردات',    icon: <Upload className="w-3.5 h-3.5" /> },
            ].map((t) => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`px-3 py-2 text-xs flex items-center gap-1.5 border-b-2 transition ${
                  tab === t.id ? 'border-indigo-400 text-indigo-200' : 'border-transparent text-zinc-400 hover:text-zinc-200'
                }`} data-testid={`tab-${t.id}`}>
                {t.icon} {t.label}
              </button>
            ))}
          </div>
        )}

        <div className="flex-1 overflow-y-auto">
          {!active ? (
            <EmptyState types={opts.project_types} onCreate={() => setShowNew(true)} />
          ) : tab === 'chat' ? (
            <ChatPane step={step} setStep={setStep} reply={reply} chatBusy={chatBusy}
              msg={msg} setMsg={setMsg} onAsk={askProducer} />
          ) : tab === 'features' ? (
            <FeaturesPane opts={opts} ownedIds={ownedIds} features={features}
              onAdd={addFeature} onRemove={removeFeature} catalog={featsByCat} />
          ) : (
            <ImportsPane project={active} onImportOpen={openImport} />
          )}
        </div>
      </main>

      {/* ── RIGHT: Summary panel ────────────────────────────────── */}
      {active && (
        <aside className="w-72 border-r border-zinc-800 bg-[#0e1118] p-4 overflow-y-auto shrink-0" data-testid="summary-panel">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><ShoppingBag className="w-4 h-4 text-indigo-400" /> ملخّص المشروع</h3>

          <div className="bg-gradient-to-br from-indigo-500/15 to-violet-500/10 border border-indigo-500/40 rounded-xl p-3 mb-3">
            <div className="text-[10px] text-indigo-200 mb-1">إجمالي تكلفة البناء حتى الآن</div>
            <div className="text-2xl font-bold text-indigo-100">{totalCost} <span className="text-xs font-normal text-indigo-300">نقطة</span></div>
            <div className="text-[10px] text-zinc-400 mt-1 leading-5">
              ميزات: {ownedCost}ن · بناء نهائي: {buildCost || 0}ن
            </div>
          </div>

          <div className="space-y-2 text-xs">
            <SumRow label="النوع" value={active.type_label} />
            <SumRow label="الميزات" value={`${features.length}`} />
            <SumRow label="المستوردات" value={`${(active.imports || []).length}`} />
            <SumRow label="المرحلة" value={active.stage} />
          </div>

          <div className="mt-4 pt-4 border-t border-zinc-800">
            <button onClick={() => toast.info('سيتم إطلاق خطوة البناء النهائي قريباً')}
              className="w-full bg-emerald-500 hover:bg-emerald-400 text-black font-medium py-2 rounded-lg text-sm flex items-center justify-center gap-1.5"
              data-testid="build-final-btn">
              <CheckCircle2 className="w-4 h-4" /> ابدأ البناء النهائي ({buildCost || 0}ن)
            </button>
            <div className="text-[10px] text-zinc-500 mt-2 leading-5 text-center">
              يولّد الكود الكامل + ينشر تلقائياً (للأنواع القابلة للنشر).
            </div>
          </div>
        </aside>
      )}

      {/* ── New Project Modal ───────────────────────────────────── */}
      {showNew && (
        <NewProjectModal opts={opts} onClose={() => setShowNew(false)}
          onCreated={(p) => { setShowNew(false); loadProjects(); setActiveId(p.id); }} />
      )}

      {/* ── Import Modal ────────────────────────────────────────── */}
      {showImport && (
        <ImportModal items={importable} onClose={() => setShowImport(false)} onImport={doImport} />
      )}
    </div>
  );
}

function SumRow({ label, value }) {
  return (
    <div className="flex items-center justify-between text-zinc-300">
      <span className="text-zinc-500">{label}</span>
      <b>{value}</b>
    </div>
  );
}

// ─── Empty state — show project types ─────────────────────────────────
function EmptyState({ types, onCreate }) {
  return (
    <div className="max-w-4xl mx-auto p-8">
      <h2 className="text-xl font-semibold mb-2">ابدأ مشروعك الأول</h2>
      <p className="text-sm text-zinc-400 mb-6 leading-7">اختر نوع التطبيق اللي يناسبك — كل نوع له مزاياه وقدراته الواقعية:</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {types.map((t) => {
          const Icon = TYPE_ICON[t.id] || Smartphone;
          return (
            <div key={t.id} className={`bg-gradient-to-br ${TYPE_COLOR[t.id]} border rounded-2xl p-4`} data-testid={`type-card-${t.id}`}>
              <div className="flex items-center gap-2 mb-2">
                <Icon className="w-5 h-5" />
                <h3 className="font-semibold">{t.label_ar}</h3>
              </div>
              <p className="text-xs text-zinc-300 leading-6 mb-3">{t.tagline_ar}</p>
              <div className="text-[11px] mb-2">
                <div className="text-emerald-300 font-semibold mb-1">المزايا:</div>
                <ul className="text-zinc-300 space-y-0.5 leading-5 list-disc pr-4">
                  {(t.pros_ar || []).map((p, i) => <li key={i}>{p}</li>)}
                </ul>
              </div>
              <div className="text-[11px] mb-3">
                <div className="text-amber-300 font-semibold mb-1">قيود واقعية:</div>
                <ul className="text-zinc-400 space-y-0.5 leading-5 list-disc pr-4">
                  {(t.cons_ar || []).map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
              <div className="text-[10px] text-zinc-500">تكلفة البناء النهائي: <b className="text-amber-300">{t.build_cost}ن</b></div>
            </div>
          );
        })}
      </div>
      <button onClick={onCreate}
        className="w-full bg-indigo-500 hover:bg-indigo-400 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2"
        data-testid="empty-create-btn">
        <Plus className="w-5 h-5" /> أنشئ مشروعك الآن
      </button>
    </div>
  );
}

// ─── Chat pane (Producer wizard) ─────────────────────────────────────
function ChatPane({ step, setStep, reply, chatBusy, msg, setMsg, onAsk }) {
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-4">
        <div className="text-xs text-zinc-500 mb-3 flex items-center gap-2"><Wand2 className="w-3.5 h-3.5" /> رحلة بناء التطبيق</div>
        <div className="flex flex-wrap gap-2">
          {WIZARD_STEPS.map((s) => (
            <button key={s.id} onClick={() => setStep(s.id)}
              className={`text-xs px-3 py-1.5 rounded-lg transition ${
                step === s.id ? 'bg-indigo-500 text-white font-semibold' : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300'
              }`} data-testid={`wizard-${s.id}`}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-gradient-to-br from-indigo-500/10 to-violet-500/10 border border-indigo-500/30 rounded-2xl p-4" data-testid="producer-reply-card">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-indigo-300" />
          <span className="text-sm font-semibold text-indigo-200">المنتج التنفيذي</span>
          {chatBusy && <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-300" />}
        </div>
        <div className="text-sm text-zinc-100 leading-7 whitespace-pre-wrap min-h-[100px]">
          {reply || (chatBusy ? 'يفكّر بمشروعك…' : 'اضغط مرحلة من فوق وراح يرشدك خطوة بخطوة.')}
        </div>
        <div className="flex gap-2 mt-3">
          <input value={msg} onChange={(e) => setMsg(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && onAsk(msg)}
            disabled={chatBusy} className="flex-1 bg-zinc-900 border border-indigo-500/30 rounded-lg px-3 py-1.5 text-sm"
            placeholder="اسأل أو وصف فكرتك…" data-testid="producer-input" />
          <button onClick={() => onAsk(msg)} disabled={chatBusy || !msg.trim()}
            className="bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 text-white font-medium px-4 rounded-lg text-sm" data-testid="producer-send">
            اسأل
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Features marketplace ────────────────────────────────────────────
function FeaturesPane({ opts, ownedIds, features, onAdd, onRemove, catalog }) {
  return (
    <div className="max-w-5xl mx-auto p-6 space-y-5">
      {(opts.feature_categories || []).map((cat) => {
        const Icon = CAT_ICON[cat.id] || Box;
        const list = catalog(cat.id);
        return (
          <div key={cat.id} className="bg-[#12161e] border border-zinc-800 rounded-2xl p-4" data-testid={`feat-cat-${cat.id}`}>
            <div className="flex items-center gap-2 mb-3">
              <Icon className="w-4 h-4 text-indigo-300" />
              <h3 className="text-sm font-semibold">{cat.label} <span className="text-xs text-zinc-500">({list.length})</span></h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {list.map((f) => {
                const owned = ownedIds.has(f.id);
                const ownedFeat = features.find((x) => x.feature_id === f.id);
                return (
                  <div key={f.id} className={`flex items-center justify-between p-3 rounded-lg border ${
                    owned ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-zinc-900 border-zinc-800 hover:border-indigo-500/40'
                  }`} data-testid={`feature-${f.id}`}>
                    <div className="flex items-center gap-2">
                      {owned ? <Check className="w-4 h-4 text-emerald-400" /> : <Plus className="w-3.5 h-3.5 text-zinc-500" />}
                      <span className="text-sm">{f.label_ar}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-amber-300 font-semibold">{f.cost}ن</span>
                      {owned ? (
                        <button onClick={() => onRemove(ownedFeat.id)} className="text-xs bg-rose-500/20 hover:bg-rose-500/40 text-rose-200 px-2 py-0.5 rounded">
                          <Trash2 className="w-3 h-3" />
                        </button>
                      ) : (
                        <button onClick={() => onAdd(f.id)} className="text-xs bg-indigo-500 hover:bg-indigo-400 text-white px-3 py-1 rounded" data-testid={`add-feature-${f.id}`}>
                          أضف
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Imports pane ────────────────────────────────────────────────────
function ImportsPane({ project, onImportOpen }) {
  const imports = project.imports || [];
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-3" data-testid="imports-pane">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold">المستوردات في هذا المشروع</h2>
        <button onClick={onImportOpen} className="text-xs bg-indigo-500 hover:bg-indigo-400 text-white px-3 py-1.5 rounded-lg flex items-center gap-1.5">
          <Plus className="w-3 h-3" /> استورد جديد
        </button>
      </div>
      {imports.length === 0 ? (
        <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-8 text-center text-sm text-zinc-500">
          ما فيه مستوردات. اضغط <b className="text-indigo-300">استورد موقع/تطبيق سابق</b> فوق لاستيراد محتوى من حسابك.
        </div>
      ) : (
        imports.map((im, i) => (
          <div key={im.id || i} className="bg-[#12161e] border border-zinc-800 rounded-xl p-3 flex items-center gap-3">
            <Upload className="w-4 h-4 text-emerald-400" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{im.label}</div>
              <div className="text-[10px] text-zinc-500">{im.kind} · {im.imported_at?.slice(0, 10)}</div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ─── New Project Modal ───────────────────────────────────────────────
function NewProjectModal({ opts, onClose, onCreated }) {
  const [form, setForm] = useState({ title: '', type: 'pwa', description: '', target_audience: '', primary_color: '#6366f1', style_direction: '' });
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!form.title.trim()) return toast.error('عنوان المشروع مطلوب');
    setBusy(true);
    try {
      const r = await fetch(`${AS}/projects/create`, { method: 'POST', headers: auth(), body: JSON.stringify(form) });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      toast.success('تم إنشاء المشروع');
      onCreated(d.project);
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur z-50 flex items-center justify-center p-4">
      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="new-project-modal">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Sparkles className="w-5 h-5 text-indigo-400" /> مشروع جديد</h2>
        <div className="space-y-3">
          <Field label="اسم المشروع">
            <input value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              placeholder="تطبيق توصيل قهوة" data-testid="new-project-title" />
          </Field>
          <Field label="نوع التطبيق">
            <div className="grid grid-cols-2 gap-2">
              {(opts.project_types || []).map((t) => {
                const Icon = TYPE_ICON[t.id] || Smartphone;
                const sel = form.type === t.id;
                return (
                  <button key={t.id} type="button" onClick={() => setForm((f) => ({ ...f, type: t.id }))}
                    className={`text-right p-3 rounded-xl border transition ${
                      sel ? `bg-gradient-to-br ${TYPE_COLOR[t.id]}` : 'border-zinc-700 hover:border-zinc-500'
                    }`} data-testid={`new-project-type-${t.id}`}>
                    <div className="flex items-center gap-2 mb-1"><Icon className="w-4 h-4" /><b className="text-sm">{t.label_ar}</b></div>
                    <div className="text-[10px] text-zinc-400 leading-5">{t.tagline_ar}</div>
                    <div className="text-[10px] text-amber-300 mt-1">{t.build_cost}ن للبناء النهائي</div>
                  </button>
                );
              })}
            </div>
          </Field>
          <Field label="وصف الفكرة">
            <textarea value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm h-20"
              placeholder="تطبيق يوصل قهوة المتجر للحي خلال ١٥ دقيقة" data-testid="new-project-desc" />
          </Field>
          <Field label="الجمهور المستهدف">
            <input value={form.target_audience} onChange={(e) => setForm((f) => ({ ...f, target_audience: e.target.value }))}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              placeholder="موظفون 25-40، الرياض، يبغون قهوة سريعة" data-testid="new-project-audience" />
          </Field>
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2 text-[11px] text-amber-200 flex items-start gap-1.5">
            <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            إنشاء المشروع مجاناً. الخصم يبدأ مع إضافة الميزات والبناء النهائي.
          </div>
          <div className="flex gap-2 pt-2">
            <button onClick={submit} disabled={busy}
              className="flex-1 bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 text-white font-medium py-2 rounded-lg text-sm"
              data-testid="new-project-create-btn">
              {busy ? 'جاري الإنشاء…' : 'إنشاء'}
            </button>
            <button onClick={onClose} className="px-4 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm">إلغاء</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Import Modal ────────────────────────────────────────────────────
function ImportModal({ items, onClose, onImport }) {
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur z-50 flex items-center justify-center p-4">
      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto" data-testid="import-modal">
        <h2 className="text-lg font-semibold mb-2 flex items-center gap-2"><Upload className="w-5 h-5 text-indigo-400" /> استورد من حسابك</h2>
        <p className="text-xs text-zinc-400 mb-4 leading-6">اختر موقعاً أو تطبيقاً سابقاً بنيته على زيتاكس لاستخدامه نقطة انطلاق:</p>
        {items.length === 0 ? (
          <div className="text-sm text-zinc-500 text-center py-8">
            ما عندك مواقع أو تطبيقات محفوظة. ابنِ واحدة من قسم FreeBuild أو Mobile Apps أولاً.
          </div>
        ) : (
          <div className="space-y-2 mb-4">
            {items.map((it, i) => (
              <button key={i} onClick={() => onImport(it.source)}
                className="w-full text-right bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 hover:border-indigo-500/50 rounded-xl p-3 flex items-center gap-3 transition"
                data-testid={`import-item-${it.kind}-${it.id}`}>
                {it.kind === 'freebuild_site' ? <Globe className="w-4 h-4 text-sky-400" /> : <Smartphone className="w-4 h-4 text-emerald-400" />}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{it.label}</div>
                  <div className="text-[10px] text-zinc-500">{it.kind === 'freebuild_site' ? 'موقع FreeBuild' : 'تطبيق سابق'}</div>
                </div>
                <Plus className="w-4 h-4 text-indigo-400" />
              </button>
            ))}
          </div>
        )}
        <button onClick={onClose} className="w-full bg-zinc-800 hover:bg-zinc-700 py-2 rounded-lg text-sm">إغلاق</button>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="text-xs text-zinc-400 block mb-1">{label}</label>
      {children}
    </div>
  );
}
