import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Smartphone, Plus, Loader2, Check, ArrowLeft, Sparkles, MessageSquare,
  Trash2, Layers, Megaphone, Coins, ShoppingBag, Wand2, Upload,
  Globe, Box, Code2, AppWindow, CheckCircle2, Info, Download,
  Hammer, Eye, RotateCw, ExternalLink, Settings as SettingsIcon,
  ChevronDown, ChevronUp, Wrench, Send,
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

const QUICK_PROMPTS = [
  'اقترح ميزات أساسية لمشروعي',
  'حلّل خطوات الإطلاق المتبقية',
  'أضف لوحة تحكم للمالك',
  'ولّد لي نص تسويقي عربي للصفحة الرئيسية',
  'اعطني prompt لتوليد أيقونة التطبيق',
  'ابدأ البناء النهائي الآن',
];

export default function AppStudio() {
  const navigate = useNavigate();
  const [opts, setOpts] = useState({ project_types: [], features: [], feature_categories: [] });
  const [projects, setProjects] = useState([]);
  const [activeId, setActiveId] = useState('');
  const [active, setActive] = useState(null);
  const [features, setFeatures] = useState([]);

  // Chat
  const [messages, setMessages] = useState([]);
  const [chatBusy, setChatBusy] = useState(false);
  const [input, setInput] = useState('');
  const scrollRef = useRef(null);

  // Modals
  const [showNew, setShowNew] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importable, setImportable] = useState([]);
  const [tab, setTab] = useState('chat'); // chat | features | imports | preview

  // Build
  const [buildBusy, setBuildBusy] = useState(false);

  // ── Bootstrap ─────────────────────────────────────────────────────
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
    if (!pid) { setActive(null); setFeatures([]); setMessages([]); return; }
    try {
      const r = await fetch(`${AS}/projects/${pid}`, { headers: auth() });
      const d = await r.json();
      setActive(d.project);
      setFeatures(d.features || []);
      const cr = await fetch(`${AS}/conversation/${pid}`, { headers: auth() });
      const cd = await cr.json();
      setMessages(cd.messages || []);
    } catch { toast.error('فشل تحميل المشروع'); }
  }, []);
  useEffect(() => { loadProject(activeId); }, [activeId, loadProject]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, chatBusy]);

  // ── Chat ──────────────────────────────────────────────────────────
  const send = useCallback(async (raw) => {
    const text = (raw ?? input).trim();
    if (!text || !activeId || chatBusy) return;
    setInput('');
    setChatBusy(true);
    // Optimistic user message
    setMessages((prev) => [...prev, { role: 'user', content: text, ts: new Date().toISOString() }]);
    try {
      const r = await fetch(`${AS}/producer-chat`, {
        method: 'POST', headers: auth(),
        body: JSON.stringify({ project_id: activeId, step: 'discover', message: text }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      setMessages((prev) => [...prev, {
        role: 'assistant', content: d.reply || '', tools: d.tools || [],
        ts: new Date().toISOString(),
      }]);
      // Reload project + features (tools may have mutated state)
      loadProject(activeId);
      // If a build tool succeeded, switch to preview tab
      const builtTool = (d.tools || []).find((t) => t.name === 'build_project_now' && t.result?.ok);
      if (builtTool) setTab('preview');
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
    finally { setChatBusy(false); }
  }, [input, activeId, chatBusy, loadProject]);

  // ── Build ─────────────────────────────────────────────────────────
  const buildNow = useCallback(async () => {
    if (!activeId || buildBusy) return;
    if (!window.confirm(`بناء التطبيق سيخصم ${buildCost} نقطة. متابعة؟`)) return;
    setBuildBusy(true);
    try {
      const r = await fetch(`${AS}/build/${activeId}`, { method: 'POST', headers: auth() });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      toast.success(`✅ تم البناء · ${d.build.files.length} ملف · ${(d.build.bundle_size / 1024).toFixed(1)}KB`);
      loadProject(activeId);
      setTab('preview');
    } catch (e) { toast.error(`فشل البناء: ${e.message || ''}`); }
    finally { setBuildBusy(false); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId, buildBusy, loadProject]);

  // ── Features (manual add) ─────────────────────────────────────────
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

  // ── Imports ───────────────────────────────────────────────────────
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

  // ── Derived ───────────────────────────────────────────────────────
  const featsByCat = (cat) => (opts.features || []).filter((f) => f.category === cat);
  const ownedIds = new Set(features.map((f) => f.feature_id));
  const ownedCost = features.reduce((sum, f) => sum + (f.cost || 0), 0);
  const ptype = active ? (opts.project_types.find((t) => t.id === active.type) || {}) : {};
  const buildCost = ptype.build_cost || 0;
  const totalCost = ownedCost + buildCost;
  const buildOut = active?.build_output;

  return (
    <div className="min-h-screen bg-[#0b0d12] text-zinc-100 flex" dir="rtl" data-testid="app-studio-page">
      {/* ── LEFT Sidebar: projects ───────────────────────────────── */}
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
          className="m-3 px-3 py-2 bg-gradient-to-br from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 rounded-lg text-sm font-semibold text-white flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20"
          data-testid="new-project-btn">
          <Plus className="w-4 h-4" /> مشروع جديد
        </button>
        <div className="flex-1 overflow-y-auto px-3 pb-3">
          <div className="text-xs text-zinc-500 px-2 pb-2">مشاريعك ({projects.length})</div>
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

      {/* ── CENTER pane ──────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between bg-[#0e1118]">
          <div className="min-w-0">
            {active ? (
              <>
                <div className="text-sm font-semibold truncate flex items-center gap-2">
                  {active.title}
                  <span className={`text-[10px] px-2 py-0.5 rounded-full bg-gradient-to-br ${TYPE_COLOR[active.type] || ''} border`}>{active.type_label}</span>
                  {buildOut && <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-200">مبني ✓</span>}
                </div>
                <div className="text-xs text-zinc-500 truncate mt-0.5">{active.description || 'بلا وصف'}</div>
              </>
            ) : (
              <div className="text-sm text-zinc-400">اختر مشروع أو أنشئ جديد</div>
            )}
          </div>
          {active && (
            <div className="flex items-center gap-2">
              <button onClick={openImport}
                className="text-xs px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 flex items-center gap-1.5" data-testid="import-existing-btn">
                <Upload className="w-3 h-3" /> استيراد سابق
              </button>
            </div>
          )}
        </header>

        {/* Tabs */}
        {active && (
          <div className="border-b border-zinc-800 px-4 flex items-center gap-1 bg-[#0e1118]/60 overflow-x-auto">
            {[
              { id: 'chat',     label: 'محادثة الذكاء', icon: <MessageSquare className="w-3.5 h-3.5" /> },
              { id: 'features', label: 'الميزات',        icon: <Wand2 className="w-3.5 h-3.5" /> },
              { id: 'preview',  label: 'معاينة',          icon: <Eye className="w-3.5 h-3.5" />, disabled: !buildOut },
              { id: 'imports',  label: 'المستوردات',     icon: <Upload className="w-3.5 h-3.5" /> },
            ].map((t) => (
              <button key={t.id} onClick={() => !t.disabled && setTab(t.id)} disabled={t.disabled}
                className={`px-3 py-2 text-xs flex items-center gap-1.5 border-b-2 transition whitespace-nowrap ${
                  tab === t.id ? 'border-indigo-400 text-indigo-200'
                              : t.disabled ? 'border-transparent text-zinc-600 cursor-not-allowed'
                                            : 'border-transparent text-zinc-400 hover:text-zinc-200'
                }`} data-testid={`tab-${t.id}`}>
                {t.icon} {t.label}
                {t.disabled && <span className="text-[9px] text-zinc-600">(ابنِ أولاً)</span>}
              </button>
            ))}
          </div>
        )}

        <div className="flex-1 overflow-hidden">
          {!active ? (
            <EmptyState types={opts.project_types} onCreate={() => setShowNew(true)} />
          ) : tab === 'chat' ? (
            <ChatPane messages={messages} chatBusy={chatBusy} input={input} setInput={setInput}
              onSend={send} scrollRef={scrollRef} project={active} />
          ) : tab === 'features' ? (
            <FeaturesPane opts={opts} ownedIds={ownedIds} features={features}
              onAdd={addFeature} onRemove={removeFeature} catalog={featsByCat} />
          ) : tab === 'preview' ? (
            <PreviewPane build={buildOut} pid={activeId} />
          ) : (
            <ImportsPane project={active} onImportOpen={openImport} />
          )}
        </div>
      </main>

      {/* ── RIGHT Summary panel ──────────────────────────────────── */}
      {active && (
        <aside className="w-80 border-r border-zinc-800 bg-[#0e1118] p-4 overflow-y-auto shrink-0" data-testid="summary-panel">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><ShoppingBag className="w-4 h-4 text-indigo-400" /> ملخّص المشروع</h3>

          <div className="bg-gradient-to-br from-indigo-500/15 to-violet-500/10 border border-indigo-500/40 rounded-xl p-3 mb-3">
            <div className="text-[10px] text-indigo-200 mb-1">إجمالي التكلفة</div>
            <div className="text-3xl font-extrabold text-indigo-100">{totalCost}<span className="text-xs font-normal text-indigo-300 mr-1">نقطة</span></div>
            <div className="text-[10px] text-zinc-400 mt-1 leading-5">ميزات: {ownedCost}ن · بناء: {buildCost}ن</div>
          </div>

          <div className="space-y-1.5 text-xs mb-4">
            <SumRow label="النوع" value={active.type_label} />
            <SumRow label="الميزات" value={features.length} />
            <SumRow label="المستوردات" value={(active.imports || []).length} />
            <SumRow label="المرحلة" value={active.stage} />
          </div>

          {features.length > 0 && (
            <div className="mb-4">
              <div className="text-[10px] text-zinc-500 mb-1.5 uppercase">الميزات المضافة</div>
              <div className="space-y-1">
                {features.slice(0, 8).map((f) => (
                  <div key={f.id} className="text-[11px] bg-zinc-900 border border-zinc-800 rounded-md px-2 py-1 flex items-center justify-between">
                    <span className="truncate">{f.label_ar}</span>
                    <span className="text-amber-300 shrink-0">{f.cost}ن</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button onClick={buildNow} disabled={buildBusy}
            className="w-full bg-gradient-to-br from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 disabled:opacity-50 text-black font-bold py-2.5 rounded-lg text-sm flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-500/20"
            data-testid="build-final-btn">
            {buildBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Hammer className="w-4 h-4" />}
            {buildOut ? `أعد البناء (${buildCost}ن)` : `ابدأ البناء (${buildCost}ن)`}
          </button>
          <div className="text-[10px] text-zinc-500 mt-2 leading-5 text-center">
            يولّد كود كامل + zip قابل للتنزيل.
          </div>

          {buildOut && (
            <div className="mt-4 pt-4 border-t border-zinc-800 space-y-2">
              <a href={`${API}${buildOut.zip_url}`} download
                className="block bg-zinc-800 hover:bg-zinc-700 text-zinc-100 text-xs px-3 py-2 rounded-lg flex items-center justify-center gap-1.5"
                data-testid="download-zip-btn">
                <Download className="w-3.5 h-3.5" /> تنزيل المشروع كاملاً (.zip)
              </a>
              {buildOut.preview_url && (
                <a href={`${API}${buildOut.preview_url}`} target="_blank" rel="noreferrer"
                  className="block bg-zinc-800 hover:bg-zinc-700 text-zinc-100 text-xs px-3 py-2 rounded-lg flex items-center justify-center gap-1.5"
                  data-testid="open-preview-btn">
                  <ExternalLink className="w-3.5 h-3.5" /> افتح المعاينة في تبويب جديد
                </a>
              )}
              <div className="text-[10px] text-zinc-500 text-center">{buildOut.files?.length} ملف · {((buildOut.bundle_size || 0) / 1024).toFixed(1)}KB</div>
            </div>
          )}
        </aside>
      )}

      {showNew && <NewProjectModal opts={opts} onClose={() => setShowNew(false)}
        onCreated={(p) => { setShowNew(false); loadProjects(); setActiveId(p.id); }} />}
      {showImport && <ImportModal items={importable} onClose={() => setShowImport(false)} onImport={doImport} />}
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

// ─── Empty state ────────────────────────────────────────────────────
function EmptyState({ types, onCreate }) {
  return (
    <div className="max-w-4xl mx-auto p-8 overflow-y-auto h-full">
      <h2 className="text-2xl font-bold mb-2">ابدأ مشروعك الأول</h2>
      <p className="text-sm text-zinc-400 mb-6 leading-7">اختر نوع التطبيق اللي يناسبك — كل نوع له مزاياه وقدراته الواقعية:</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {types.map((t) => {
          const Icon = TYPE_ICON[t.id] || Smartphone;
          return (
            <div key={t.id} className={`bg-gradient-to-br ${TYPE_COLOR[t.id]} border rounded-2xl p-4`} data-testid={`type-card-${t.id}`}>
              <div className="flex items-center gap-2 mb-2"><Icon className="w-5 h-5" /><h3 className="font-semibold">{t.label_ar}</h3></div>
              <p className="text-xs text-zinc-300 leading-6 mb-3">{t.tagline_ar}</p>
              <div className="text-[11px] mb-2">
                <div className="text-emerald-300 font-semibold mb-1">المزايا:</div>
                <ul className="text-zinc-300 space-y-0.5 leading-5 list-disc pr-4">{(t.pros_ar || []).map((p, i) => <li key={i}>{p}</li>)}</ul>
              </div>
              <div className="text-[11px] mb-3">
                <div className="text-amber-300 font-semibold mb-1">قيود واقعية:</div>
                <ul className="text-zinc-400 space-y-0.5 leading-5 list-disc pr-4">{(t.cons_ar || []).map((c, i) => <li key={i}>{c}</li>)}</ul>
              </div>
              <div className="text-[10px] text-zinc-500">تكلفة البناء: <b className="text-amber-300">{t.build_cost}ن</b></div>
            </div>
          );
        })}
      </div>
      <button onClick={onCreate}
        className="w-full bg-gradient-to-br from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2"
        data-testid="empty-create-btn">
        <Plus className="w-5 h-5" /> أنشئ مشروعك الآن
      </button>
    </div>
  );
}

// ─── Chat pane (real chat with tool pills) ──────────────────────────
function ChatPane({ messages, chatBusy, input, setInput, onSend, scrollRef, project }) {
  return (
    <div className="h-full flex flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4" data-testid="chat-scroll">
        {messages.length === 0 && !chatBusy && (
          <div className="max-w-2xl mx-auto bg-gradient-to-br from-indigo-500/10 to-violet-500/10 border border-indigo-500/30 rounded-2xl p-5 text-center">
            <Sparkles className="w-7 h-7 text-indigo-300 mx-auto mb-2" />
            <h3 className="text-lg font-bold mb-2">المنتج التنفيذي بالخدمة</h3>
            <p className="text-sm text-zinc-300 leading-7 mb-4">
              أنا ذكاء عملي للتطبيقات. أقدر أضيف ميزات، أبني الكود، أولّد نص تسويقي، أو أرشدك لخطوات الإطلاق.
              مشروعك: <b className="text-indigo-200">{project?.title}</b>
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {QUICK_PROMPTS.map((p) => (
                <button key={p} onClick={() => onSend(p)}
                  className="text-xs bg-zinc-800 hover:bg-indigo-500/30 border border-zinc-700 hover:border-indigo-500/50 px-3 py-1.5 rounded-full transition"
                  data-testid={`quick-${p.slice(0, 15)}`}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => <Bubble key={i} m={m} />)}
        {chatBusy && (
          <div className="max-w-2xl mr-12 bg-[#12161e] border border-zinc-800 rounded-2xl p-3 flex items-center gap-2 text-sm text-zinc-400" data-testid="chat-thinking">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-300" />
            <span>الذكاء يفكر…</span>
          </div>
        )}
      </div>
      <div className="border-t border-zinc-800 bg-[#0e1118] p-4">
        <div className="max-w-3xl mx-auto flex gap-2">
          <textarea value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(); }
            }}
            disabled={chatBusy} rows={1}
            className="flex-1 bg-zinc-900 border border-zinc-700 focus:border-indigo-500/50 rounded-xl px-4 py-2.5 text-sm resize-none outline-none"
            placeholder="اطلب من الذكاء أي شي — يضيف ميزات، يبني، يحلّل، أو يولّد نص تسويقي…"
            data-testid="chat-input" />
          <button onClick={() => onSend()} disabled={chatBusy || !input.trim()}
            className="bg-gradient-to-br from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 disabled:opacity-50 text-white font-semibold px-5 rounded-xl text-sm flex items-center gap-1.5"
            data-testid="chat-send">
            <Send className="w-4 h-4" />
            <span className="hidden md:inline">إرسال</span>
          </button>
        </div>
      </div>
    </div>
  );
}

function Bubble({ m }) {
  const isUser = m.role === 'user';
  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : ''}`} data-testid={`msg-${m.role}`}>
      <div className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-bold ${
        isUser ? 'bg-zinc-700 text-zinc-200' : 'bg-gradient-to-br from-indigo-500 to-violet-600 text-white'
      }`}>
        {isUser ? 'أنا' : <Sparkles className="w-3.5 h-3.5" />}
      </div>
      <div className={`max-w-2xl rounded-2xl p-3 ${
        isUser ? 'bg-indigo-500/10 border border-indigo-500/20' : 'bg-[#12161e] border border-zinc-800'
      }`}>
        <div className="text-sm leading-7 whitespace-pre-wrap text-zinc-100">{m.content}</div>
        {(m.tools || []).length > 0 && (
          <div className="mt-3 pt-3 border-t border-zinc-800/60 space-y-2">
            {m.tools.map((t, i) => <ToolPill key={i} t={t} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function ToolPill({ t }) {
  const [open, setOpen] = useState(false);
  const ok = t.result?.ok;
  const labels = {
    add_feature_to_project: { icon: <Plus className="w-3 h-3" />, color: 'emerald', label: 'أضاف ميزة' },
    remove_feature_from_project: { icon: <Trash2 className="w-3 h-3" />, color: 'rose', label: 'حذف ميزة' },
    list_features: { icon: <Layers className="w-3 h-3" />, color: 'sky', label: 'قائمة الميزات' },
    update_project_metadata: { icon: <SettingsIcon className="w-3 h-3" />, color: 'amber', label: 'حدّث الإعدادات' },
    build_project_now: { icon: <Hammer className="w-3 h-3" />, color: 'violet', label: 'بنى المشروع' },
    suggest_app_icon_prompt: { icon: <Sparkles className="w-3 h-3" />, color: 'fuchsia', label: 'prompt للأيقونة' },
    generate_marketing_copy: { icon: <Megaphone className="w-3 h-3" />, color: 'cyan', label: 'نص تسويقي' },
    recommend_next_steps: { icon: <Wand2 className="w-3 h-3" />, color: 'amber', label: 'خطوات تالية' },
  };
  const meta = labels[t.name] || { icon: <Wrench className="w-3 h-3" />, color: 'zinc', label: t.name };
  return (
    <div className={`bg-${meta.color}-500/10 border border-${meta.color}-500/30 rounded-lg overflow-hidden`} data-testid={`tool-pill-${t.name}`}>
      <button onClick={() => setOpen(!open)} className="w-full px-2.5 py-1.5 flex items-center gap-2 text-xs">
        <span className={`text-${meta.color}-300`}>{meta.icon}</span>
        <span className={`font-medium text-${meta.color}-200 flex-1 text-right`}>{meta.label}</span>
        <span className={`text-[10px] ${ok ? 'text-emerald-300' : 'text-rose-300'}`}>{ok ? '✓' : '✗'}</span>
        {open ? <ChevronUp className="w-3 h-3 text-zinc-500" /> : <ChevronDown className="w-3 h-3 text-zinc-500" />}
      </button>
      {open && (
        <div className="px-2.5 py-2 border-t border-zinc-800/40 text-[10px] text-zinc-400 bg-zinc-900/40 max-h-40 overflow-auto">
          <div className="mb-1 text-zinc-500">المعطيات:</div>
          <pre className="text-zinc-300 mb-2 whitespace-pre-wrap break-all">{JSON.stringify(t.args || {}, null, 2)}</pre>
          <div className="mb-1 text-zinc-500">النتيجة:</div>
          <pre className="text-zinc-300 whitespace-pre-wrap break-all">{JSON.stringify(t.result || {}, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

// ─── Features marketplace ──────────────────────────────────────────
function FeaturesPane({ opts, ownedIds, features, onAdd, onRemove, catalog }) {
  return (
    <div className="overflow-y-auto h-full">
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
    </div>
  );
}

// ─── Preview pane (iframe live) ────────────────────────────────────
function PreviewPane({ build, pid }) {
  const [device, setDevice] = useState('mobile'); // mobile | desktop
  const [bust, setBust] = useState(0);
  if (!build?.preview_url) return null;
  const src = `${API}${build.preview_url}?_=${bust}`;
  return (
    <div className="h-full flex flex-col bg-[#0a0c11]">
      <div className="px-4 py-2 border-b border-zinc-800 flex items-center gap-2 bg-[#0e1118]">
        <div className="flex items-center gap-1 text-xs">
          <button onClick={() => setDevice('mobile')} className={`px-2 py-1 rounded ${device === 'mobile' ? 'bg-indigo-500/30 text-indigo-200' : 'text-zinc-400 hover:bg-zinc-800'}`} data-testid="preview-mobile">📱 جوال</button>
          <button onClick={() => setDevice('desktop')} className={`px-2 py-1 rounded ${device === 'desktop' ? 'bg-indigo-500/30 text-indigo-200' : 'text-zinc-400 hover:bg-zinc-800'}`} data-testid="preview-desktop">🖥️ سطح المكتب</button>
        </div>
        <div className="flex-1" />
        <button onClick={() => setBust((b) => b + 1)} className="text-xs px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 flex items-center gap-1" data-testid="preview-reload">
          <RotateCw className="w-3 h-3" /> تحديث
        </button>
        <a href={src} target="_blank" rel="noreferrer" className="text-xs px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 flex items-center gap-1">
          <ExternalLink className="w-3 h-3" /> فتح في تبويب
        </a>
        <a href={`${API}${build.zip_url}`} download className="text-xs px-2 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/40 text-emerald-200 flex items-center gap-1" data-testid="preview-download">
          <Download className="w-3 h-3" /> تنزيل zip
        </a>
      </div>
      <div className="flex-1 overflow-auto p-6 flex items-start justify-center">
        {device === 'mobile' ? (
          <div className="bg-black border-4 border-zinc-700 rounded-[40px] p-2 shadow-2xl" style={{ width: 390, height: 760 }}>
            <iframe src={src} title="preview" className="w-full h-full rounded-[28px] bg-white" data-testid="preview-iframe" />
          </div>
        ) : (
          <iframe src={src} title="preview" className="w-full h-[80vh] rounded-xl bg-white border border-zinc-700" data-testid="preview-iframe-desktop" />
        )}
      </div>
      <div className="px-4 py-2 border-t border-zinc-800 text-[10px] text-zinc-500 flex items-center gap-3">
        <span>📦 {build.files?.length} ملف</span>
        <span>·</span>
        <span>{((build.bundle_size || 0) / 1024).toFixed(1)}KB</span>
        <span>·</span>
        <span className="truncate">{build.preview_url}</span>
      </div>
    </div>
  );
}

// ─── Imports pane ──────────────────────────────────────────────────
function ImportsPane({ project, onImportOpen }) {
  const imports = project.imports || [];
  return (
    <div className="overflow-y-auto h-full">
      <div className="max-w-3xl mx-auto p-6 space-y-3" data-testid="imports-pane">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold">المستوردات في هذا المشروع</h2>
          <button onClick={onImportOpen} className="text-xs bg-indigo-500 hover:bg-indigo-400 text-white px-3 py-1.5 rounded-lg flex items-center gap-1.5">
            <Plus className="w-3 h-3" /> استورد جديد
          </button>
        </div>
        {imports.length === 0 ? (
          <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-8 text-center text-sm text-zinc-500">
            ما فيه مستوردات. اضغط <b className="text-indigo-300">استيراد سابق</b> فوق لاستيراد محتوى من حسابك.
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
    </div>
  );
}

// ─── New Project Modal ─────────────────────────────────────────────
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
                    <div className="text-[10px] text-amber-300 mt-1">{t.build_cost}ن للبناء</div>
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
              placeholder="موظفون 25-40، الرياض" data-testid="new-project-audience" />
          </Field>
          <Field label="اللون الأساسي">
            <div className="flex items-center gap-2">
              <input type="color" value={form.primary_color} onChange={(e) => setForm((f) => ({ ...f, primary_color: e.target.value }))}
                className="w-12 h-9 rounded cursor-pointer bg-zinc-900 border border-zinc-700" data-testid="new-project-color" />
              <input value={form.primary_color} onChange={(e) => setForm((f) => ({ ...f, primary_color: e.target.value }))}
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm font-mono" />
            </div>
          </Field>
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2 text-[11px] text-amber-200 flex items-start gap-1.5">
            <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            إنشاء المشروع مجاناً. الخصم يبدأ مع إضافة الميزات والبناء النهائي.
          </div>
          <div className="flex gap-2 pt-2">
            <button onClick={submit} disabled={busy}
              className="flex-1 bg-gradient-to-br from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 disabled:opacity-50 text-white font-semibold py-2 rounded-lg text-sm"
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

// ─── Import Modal ──────────────────────────────────────────────────
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
