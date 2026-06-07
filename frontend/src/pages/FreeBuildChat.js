import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Globe, Send, Loader2, Sparkles, Eye, ArrowRight, ArrowLeft,
  CheckCircle2, Check, Image as ImageIcon, FolderOpen, Code,
  Monitor, Smartphone, Trash2, MessageSquare,
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// Phase definitions (purely visual sidebar — backend tracks current_phase)
const PHASES = [
  { id: 'discovery',   title: 'اكتشاف الفكرة',   icon: '🔍', desc: 'نسمع منك ونفهم رؤيتك' },
  { id: 'design',      title: 'اتجاهات التصميم', icon: '🎨', desc: 'نقترح 2-3 خيارات' },
  { id: 'assets',      title: 'توليد الأصول',    icon: '🖼️', desc: 'صور + شعار + بانرات' },
  { id: 'build',       title: 'البناء',          icon: '⚒️', desc: 'كتابة HTML/CSS تدريجي' },
  { id: 'preview',     title: 'المعاينة الحية',  icon: '👁️', desc: 'تجربة الموقع' },
  { id: 'deploy',      title: 'النشر',           icon: '🚀', desc: 'موقع جاهز للعالم' },
];

// ─────────────────────────────────────────────────────────────
// STEP 1: Project Entry (no categories — just listen)
// ─────────────────────────────────────────────────────────────
function ProjectEntry({ onCreated, onOpenMyProjects }) {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [idea, setIdea] = useState('');
  const [loading, setLoading] = useState(false);

  const create = async () => {
    if (!name.trim()) return toast.error('أدخل اسم المشروع');
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await fetch(`${API}/api/freebuild-chat/project`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name, description: idea }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'فشل إنشاء المشروع');
      onCreated(data.id);
      toast.success('✨ مشروع جديد جاهز!');
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div dir="rtl" className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-emerald-950/20 text-white p-6">
      <div className="max-w-4xl mx-auto">
        {/* Top nav */}
        <div className="mb-4 flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={onOpenMyProjects}
            data-testid="open-my-projects"
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all"
          >
            <FolderOpen className="w-4 h-4" />
            <span className="text-sm font-medium">مشاريعي السابقة</span>
          </button>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            data-testid="back-to-dashboard"
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all"
          >
            <ArrowRight className="w-4 h-4" />
            <span className="text-sm font-medium">رجوع للوحة التحكم</span>
          </button>
        </div>

        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
            <Globe className="w-8 h-8 text-black" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">إنشاء موقع من الصفر</h1>
            <p className="text-zinc-400">شات حواري ذكي — يسمعك، يصمم معك، ويبني خطوة بخطوة</p>
          </div>
        </div>

        {/* Project Info */}
        <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl p-6 mb-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-emerald-400" />
            <span>ابدأ مشروعك</span>
          </h2>
          <input
            type="text"
            placeholder="اسم المشروع (مثال: موقع عطر فاخر)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            data-testid="project-name-input"
            className="w-full bg-black/40 border border-white/15 rounded-xl px-4 py-3 mb-4 outline-none focus:border-emerald-400"
          />
          <textarea
            placeholder="اكتب فكرتك بكلمات بسيطة (اختياري — تقدر تترك الذكاء يسألك)"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            rows={4}
            data-testid="project-desc-input"
            className="w-full bg-black/40 border border-white/15 rounded-xl px-4 py-3 outline-none focus:border-emerald-400 resize-none"
          />
          <p className="text-xs text-zinc-500 mt-3">💡 لا داعي تختار قالب أو تصنيف — هذا إنشاء حر من الصفر. الذكاء راح يسألك ويصمم لك بحسب رغبتك.</p>
        </div>

        {/* Create Button */}
        <button
          type="button"
          onClick={create}
          disabled={!name.trim() || loading}
          data-testid="create-project-btn"
          className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 disabled:from-zinc-700 disabled:to-zinc-800 text-black font-bold rounded-xl py-4 transition-all flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>جاري الإنشاء...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              <span>ابدأ المحادثة</span>
              <ArrowLeft className="w-5 h-5" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// MY PROJECTS MODAL
// ─────────────────────────────────────────────────────────────
function MyProjectsModal({ open, onClose, onSelect }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem('token');
        const r = await fetch(`${API}/api/freebuild-chat/projects`, { headers: { Authorization: `Bearer ${token}` } });
        if (!r.ok) return;
        const d = await r.json();
        if (!cancelled) setProjects(d.projects || []);
      } catch (e) { /* silent */ }
      finally { if (!cancelled) setLoading(false); }
    };
    load();
    return () => { cancelled = true; };
  }, [open]);

  const remove = async (pid, e) => {
    e.stopPropagation();
    if (!window.confirm('حذف المشروع؟')) return;
    const token = localStorage.getItem('token');
    await fetch(`${API}/api/freebuild-chat/project/${pid}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
    setProjects((arr) => arr.filter((p) => p.id !== pid));
    toast.success('تم الحذف');
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-zinc-900 border border-white/10 rounded-2xl max-w-3xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="p-5 border-b border-white/10 flex items-center justify-between sticky top-0 bg-zinc-900 z-10">
          <h3 className="text-lg font-bold flex items-center gap-2"><FolderOpen className="w-5 h-5 text-emerald-400" /> مشاريعي السابقة</h3>
          <button type="button" onClick={onClose} className="text-zinc-400 hover:text-white">✕</button>
        </div>
        <div className="p-5">
          {loading ? (
            <p className="text-zinc-500 text-sm">جاري التحميل...</p>
          ) : projects.length === 0 ? (
            <p className="text-zinc-500 text-sm text-center py-8">ما عندك مشاريع بعد</p>
          ) : (
            <div className="space-y-2">
              {projects.map((p) => (
                <div
                  key={p.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => { onSelect(p.id); onClose(); }}
                  onKeyDown={(e) => { if (e.key === 'Enter') { onSelect(p.id); onClose(); } }}
                  data-testid={`project-card-${p.id}`}
                  className="p-4 rounded-xl bg-black/30 border border-white/10 hover:border-emerald-500/40 transition-all cursor-pointer flex items-center justify-between gap-3"
                >
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold truncate">{p.name}</h4>
                    <p className="text-xs text-zinc-500 truncate">{p.description || 'بدون وصف'}</p>
                    <p className="text-[10px] text-zinc-600 mt-1">{(p.messages || []).length} رسالة · {(p.approved_assets || []).length} أصل معتمد</p>
                  </div>
                  <button type="button" onClick={(e) => remove(p.id, e)} className="text-zinc-500 hover:text-red-400 p-2">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// STEP 2: Chat Workspace (Game Studio style)
// ─────────────────────────────────────────────────────────────
function ChatWorkspace({ projectId }) {
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [activePhase, setActivePhase] = useState('discovery');
  const [activeTab, setActiveTab] = useState('chat'); // chat | live | approved
  const [previewMode, setPreviewMode] = useState('desktop');
  const [myProjectsOpen, setMyProjectsOpen] = useState(false);
  const chatEndRef = useRef(null);

  // Fetch + poll project state
  useEffect(() => {
    let cancelled = false;
    const token = localStorage.getItem('token');
    const tick = async () => {
      try {
        const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
        if (r.ok && !cancelled) {
          const d = await r.json();
          setProject(d);
        }
      } catch (e) { /* silent */ }
    };
    tick();
    const iv = setInterval(tick, 4000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [projectId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (activeTab === 'chat') {
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  }, [project?.messages?.length, activeTab]);

  const send = async () => {
    if (!message.trim() || loading) return;
    setLoading(true);
    const token = localStorage.getItem('token');
    const msgText = message;
    setMessage('');
    try {
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: msgText }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || 'فشل الإرسال');
      }
      const data = await r.json();
      if (data.html_updated) toast.success('✨ تم تحديث المعاينة الحية');
      // Refresh
      const pr = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
      if (pr.ok) setProject(await pr.json());
    } catch (e) {
      toast.error(e.message);
      setMessage(msgText); // restore on error
    } finally {
      setLoading(false);
    }
  };

  const approve = useCallback(async (aid) => {
    const token = localStorage.getItem('token');
    const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/asset/${aid}/approve`, {
      method: 'POST', headers: { Authorization: `Bearer ${token}` },
    });
    if (r.ok) {
      toast.success('✅ تم اعتماد الأصل');
      const pr = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
      if (pr.ok) setProject(await pr.json());
    } else toast.error('فشل');
  }, [projectId]);

  if (!project) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-400 flex items-center gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-emerald-400" />
          جاري التحميل...
        </div>
      </div>
    );
  }

  // Compute pending + approved assets
  const pendingAssets = [];
  (project.messages || []).forEach((m) => {
    (m.pending_assets || []).forEach((a) => { if (!a.approved) pendingAssets.push(a); });
  });
  const approvedAssets = project.approved_assets || [];
  const messages = project.messages || [];

  return (
    <div dir="rtl" className="h-screen bg-zinc-950 text-white flex flex-col overflow-hidden">
      {/* Top Bar */}
      <div className="bg-zinc-900/80 backdrop-blur border-b border-white/10 px-4 sm:px-6 py-3 flex items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2 sm:gap-4 min-w-0 flex-1">
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            data-testid="back-from-chat"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all shrink-0"
            title="رجوع للوحة التحكم"
          >
            <ArrowRight className="w-4 h-4" />
            <span className="text-xs font-medium hidden sm:inline">رجوع</span>
          </button>
          <button
            type="button"
            onClick={() => setMyProjectsOpen(true)}
            data-testid="open-my-projects-chat"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all shrink-0"
            title="افتح مشاريعي السابقة"
          >
            <FolderOpen className="w-4 h-4" />
            <span className="text-xs font-medium hidden sm:inline">مشاريعي</span>
          </button>
          <Globe className="w-6 h-6 text-emerald-400 shrink-0" />
          <div className="min-w-0">
            <h1 className="font-bold text-base sm:text-lg truncate" data-testid="project-title">{project.name}</h1>
            <p className="text-xs text-zinc-500 truncate">{PHASES.find((p) => p.id === activePhase)?.title}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <div className="px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-xs text-emerald-300 font-bold hidden sm:inline">من الصفر</span>
          </div>
        </div>
      </div>

      {/* Main: 3 panes */}
      <div className="flex-1 flex overflow-hidden">
        {/* RIGHT (sidebar in RTL): Phases */}
        <div className="w-56 lg:w-64 bg-zinc-900/50 border-l border-white/10 p-3 lg:p-4 overflow-y-auto shrink-0 hidden md:block">
          <h2 className="font-bold mb-3 text-emerald-400 text-sm flex items-center gap-1.5">
            <span>📋</span> <span>المراحل</span>
          </h2>
          <div className="space-y-2">
            {PHASES.map((phase) => {
              const isActive = activePhase === phase.id;
              return (
                <button
                  key={phase.id}
                  type="button"
                  onClick={() => setActivePhase(phase.id)}
                  data-testid={`phase-${phase.id}`}
                  className={`w-full text-right p-3 rounded-lg border transition-all ${
                    isActive
                      ? 'bg-emerald-500/15 border-emerald-500/50 text-emerald-200'
                      : 'bg-black/20 border-white/10 hover:border-white/20 text-zinc-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold flex items-center gap-1.5">
                      <span>{phase.icon}</span><span>{phase.title}</span>
                    </span>
                    {isActive && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                  </div>
                  <p className="text-[10px] text-zinc-500 leading-tight">{phase.desc}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* CENTER: Tabs content */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Tab Bar */}
          <div className="flex border-b border-white/10 bg-zinc-900/40 px-2 gap-1 shrink-0" data-testid="studio-tabs">
            <button
              type="button"
              onClick={() => setActiveTab('chat')}
              data-testid="tab-chat"
              className={`px-3 sm:px-4 py-2.5 text-sm font-bold border-b-2 transition-all flex items-center gap-1.5 ${activeTab === 'chat' ? 'text-emerald-300 border-emerald-400' : 'text-zinc-400 border-transparent hover:text-white'}`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>المحادثة</span>
              {messages.length > 0 && (
                <span className="text-[10px] bg-emerald-500/20 px-1.5 py-0.5 rounded-full">{messages.length}</span>
              )}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('live')}
              data-testid="tab-live"
              className={`px-3 sm:px-4 py-2.5 text-sm font-bold border-b-2 transition-all flex items-center gap-1.5 ${activeTab === 'live' ? 'text-cyan-300 border-cyan-400' : 'text-zinc-400 border-transparent hover:text-white'}`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>المعاينة الحية</span>
              {project.current_html && <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('approved')}
              data-testid="tab-approved"
              className={`px-3 sm:px-4 py-2.5 text-sm font-bold border-b-2 transition-all flex items-center gap-1.5 ${activeTab === 'approved' ? 'text-violet-300 border-violet-400' : 'text-zinc-400 border-transparent hover:text-white'}`}
            >
              <ImageIcon className="w-3.5 h-3.5" />
              <span>المعتمدات</span>
              {approvedAssets.length > 0 && (
                <span className="text-[10px] bg-violet-500/20 px-1.5 py-0.5 rounded-full">{approvedAssets.length}</span>
              )}
            </button>
            <div className="flex-1" />
            <div className="text-[10px] text-zinc-500 hidden sm:flex items-center gap-1.5 px-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>محفوظ تلقائياً</span>
            </div>
          </div>

          {/* Tab Content */}
          {activeTab === 'chat' && (
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4" data-testid="chat-messages">
              {messages.length === 0 && (
                <div className="text-center py-12 max-w-2xl mx-auto">
                  <Sparkles className="w-12 h-12 mx-auto mb-4 text-emerald-400/60" />
                  <h3 className="text-xl font-bold text-emerald-200 mb-2">أهلين! ابدأ بسرد فكرتك</h3>
                  <p className="text-sm text-zinc-400 mb-6">
                    اكتب وش تبي تسوي بكل بساطة — مثلاً: «أبي موقع لمحل عطور فاخر»
                    أو «أبي صفحة بسيطة لخدماتي التصويرية». الذكاء راح يسألك أسئلة ذكية ويقترح
                    لك اتجاهات تصميم مختلفة قبل ما يبني.
                  </p>
                  <div className="grid sm:grid-cols-2 gap-2 max-w-lg mx-auto">
                    {[
                      'أبي موقع لمحل عطور فاخر، الجمهور سعودي وأبي إحساس راقي',
                      'صفحة هبوط لتطبيقي الجديد بألوان داكنة وحديثة',
                      'موقع للمطعم العائلي، يطلع جوّ دافئ ومريح',
                      'بورتفوليو لأعمالي التصويرية، أبي يكون فني',
                    ].map((s, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => setMessage(s)}
                        data-testid={`quick-prompt-${i}`}
                        className="p-3 rounded-lg bg-emerald-500/5 hover:bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-100 text-right transition-all"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                    m.role === 'user'
                      ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-50'
                      : 'bg-zinc-800/70 border border-white/10 text-zinc-100'
                  }`}>
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</p>
                    {m.had_html && (
                      <p className="text-cyan-400 text-[11px] mt-2 flex items-center gap-1">
                        <Eye className="w-3 h-3" />
                        <button type="button" onClick={() => setActiveTab('live')} className="underline hover:text-cyan-300">
                          تم تحديث المعاينة الحية — اضغط للمشاهدة
                        </button>
                      </p>
                    )}
                    {/* Pending assets inline */}
                    {m.pending_assets && m.pending_assets.length > 0 && (
                      <div className="mt-3 grid sm:grid-cols-2 gap-2">
                        {m.pending_assets.map((a) => (
                          <div key={a.id} className="rounded-lg bg-black/40 border border-emerald-500/20 overflow-hidden" data-testid={`pending-asset-${a.id}`}>
                            {a.image_url ? (
                              <img src={a.image_url.startsWith('http') ? a.image_url : `${API}${a.image_url}`} alt="" className="w-full aspect-video object-cover" />
                            ) : (
                              <div className="w-full aspect-video bg-zinc-900 flex items-center justify-center text-xs text-zinc-500">
                                {a.status === 'failed' ? '❌ فشل التوليد' : (
                                  <span className="flex items-center gap-2 animate-pulse">
                                    <Loader2 className="w-4 h-4 animate-spin" /> جاري التوليد...
                                  </span>
                                )}
                              </div>
                            )}
                            <div className="p-2">
                              <p className="text-[10px] text-emerald-300 font-bold mb-0.5">{a.type}</p>
                              <p className="text-[10px] text-zinc-400 mb-2 line-clamp-1">{a.prompt}</p>
                              {a.image_url && !a.approved && (
                                <button
                                  type="button"
                                  onClick={() => approve(a.id)}
                                  data-testid={`approve-asset-${a.id}`}
                                  className="w-full py-1.5 rounded bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-400/40 text-emerald-200 text-[11px] font-bold"
                                >
                                  ✓ اعتمد
                                </button>
                              )}
                              {a.approved && (
                                <p className="text-emerald-400 text-[11px] font-bold text-center py-1">✓ معتمد</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
          )}

          {activeTab === 'live' && (
            <div className="flex-1 overflow-hidden bg-black/40 flex flex-col" data-testid="tab-content-live">
              <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between gap-3">
                <h2 className="text-sm font-bold text-cyan-300 flex items-center gap-2">
                  <Eye className="w-4 h-4" /> <span>المعاينة الحية</span>
                </h2>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setPreviewMode('desktop')}
                    data-testid="preview-desktop-btn"
                    className={`p-1.5 rounded ${previewMode === 'desktop' ? 'bg-cyan-500/20 text-cyan-300' : 'text-zinc-500 hover:text-zinc-300'}`}
                  >
                    <Monitor className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setPreviewMode('mobile')}
                    data-testid="preview-mobile-btn"
                    className={`p-1.5 rounded ${previewMode === 'mobile' ? 'bg-cyan-500/20 text-cyan-300' : 'text-zinc-500 hover:text-zinc-300'}`}
                  >
                    <Smartphone className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-auto p-4 flex items-start justify-center">
                {project.current_html ? (
                  <iframe
                    title="Live Preview"
                    data-testid="preview-iframe"
                    srcDoc={project.current_html}
                    sandbox="allow-scripts allow-same-origin"
                    className={`bg-white rounded-lg shadow-2xl border border-white/10 transition-all ${previewMode === 'mobile' ? 'w-[375px]' : 'w-full max-w-5xl'}`}
                    style={{ height: '100%', minHeight: '600px' }}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-center">
                    <div>
                      <Code className="w-16 h-16 mx-auto mb-4 text-zinc-700" />
                      <p className="text-zinc-400 text-sm font-bold mb-1">لا يوجد HTML بعد</p>
                      <p className="text-zinc-600 text-xs">اطلب من الذكاء بناء صفحة كاملة في المحادثة</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'approved' && (
            <div className="flex-1 overflow-y-auto p-4 sm:p-6" data-testid="tab-content-approved">
              <h2 className="text-lg font-bold text-violet-300 mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5" /> <span>الأصول المعتمدة</span>
                <span className="text-xs text-zinc-500 font-normal">({approvedAssets.length})</span>
              </h2>
              {approvedAssets.length === 0 ? (
                <div className="text-center py-12">
                  <ImageIcon className="w-12 h-12 mx-auto mb-3 text-zinc-700" />
                  <p className="text-zinc-500 text-sm">سيظهر هنا كل أصل اعتمدته</p>
                  <p className="text-zinc-600 text-xs mt-1">الذكاء راح يستخدم هذي الأصول في الـ HTML</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                  {approvedAssets.map((a) => (
                    <div key={a.id} className="rounded-xl overflow-hidden border border-violet-500/30 bg-black/30">
                      {a.image_url && (
                        <img
                          src={a.image_url.startsWith('http') ? a.image_url : `${API}${a.image_url}`}
                          alt=""
                          className="w-full aspect-square object-cover"
                        />
                      )}
                      <div className="p-2">
                        <p className="text-[10px] text-violet-300 font-bold">{a.type}</p>
                        <p className="text-[10px] text-zinc-500 truncate">{a.prompt}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Input bar (always visible at bottom) */}
          <div className="border-t border-white/10 p-3 sm:p-4 bg-zinc-900/50 shrink-0">
            <div className="flex gap-2 sm:gap-3">
              <input
                type="text"
                placeholder="اكتب طلبك للذكاء (مثل: ابغى hero بألوان دافئة)..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
                disabled={loading}
                data-testid="chat-input"
                className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-3 outline-none focus:border-emerald-400 text-sm"
              />
              <button
                type="button"
                onClick={send}
                disabled={loading || !message.trim()}
                data-testid="chat-send-btn"
                className="px-5 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 disabled:from-zinc-700 disabled:to-zinc-800 text-black font-bold rounded-xl flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      <MyProjectsModal
        open={myProjectsOpen}
        onClose={() => setMyProjectsOpen(false)}
        onSelect={(pid) => navigate(`/freebuild/chat/${pid}`)}
      />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────────
export default function FreeBuildChat() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [myProjectsOpen, setMyProjectsOpen] = useState(false);

  if (id) return <ChatWorkspace projectId={id} />;

  return (
    <>
      <ProjectEntry
        onCreated={(pid) => navigate(`/freebuild/chat/${pid}`)}
        onOpenMyProjects={() => setMyProjectsOpen(true)}
      />
      <MyProjectsModal
        open={myProjectsOpen}
        onClose={() => setMyProjectsOpen(false)}
        onSelect={(pid) => { setMyProjectsOpen(false); navigate(`/freebuild/chat/${pid}`); }}
      />
    </>
  );
}
