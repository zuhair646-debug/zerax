import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Globe, Send, Loader2, Sparkles, Eye, ArrowRight, ArrowLeft,
  CheckCircle2, Check, Image as ImageIcon, FolderOpen, Code,
  Monitor, Smartphone, Trash2, MessageSquare, Paperclip, X,
  ZoomIn, Reply, Download,
} from 'lucide-react';
import { toast } from 'sonner';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import VoiceRecorderButton from '@/components/VoiceRecorderButton';

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
// LIGHTBOX (click-to-zoom + reply)
// ─────────────────────────────────────────────────────────────
function Lightbox({ open, asset, onClose, onReply, onApprove }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open || !asset) return null;
  const fullUrl = asset.image_url?.startsWith('http') ? asset.image_url : `${API}${asset.image_url}`;
  return (
    <div
      className="fixed inset-0 z-[60] bg-black/90 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
      data-testid="lightbox"
    >
      <button
        type="button"
        onClick={onClose}
        data-testid="lightbox-close"
        className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white z-10"
        aria-label="إغلاق"
      >
        <X className="w-5 h-5" />
      </button>

      <div className="max-w-6xl w-full max-h-[90vh] flex flex-col gap-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex-1 overflow-hidden rounded-2xl bg-black/40 border border-white/10 flex items-center justify-center">
          <img
            src={fullUrl}
            alt={asset.prompt || 'asset'}
            className="max-w-full max-h-[75vh] object-contain"
            data-testid="lightbox-img"
          />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-900/70 border border-white/10 rounded-xl p-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs text-emerald-300 font-bold">{asset.type}</p>
            <p className="text-xs text-zinc-400 truncate">{asset.prompt}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <a
              href={fullUrl}
              download
              data-testid="lightbox-download"
              className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-200 text-xs font-bold flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" /> تنزيل
            </a>
            {onApprove && !asset.approved && (
              <button
                type="button"
                onClick={() => { onApprove(asset.id); onClose(); }}
                data-testid="lightbox-approve"
                className="px-3 py-2 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-400/40 text-emerald-200 text-xs font-bold flex items-center gap-1.5"
              >
                <Check className="w-3.5 h-3.5" /> اعتمد
              </button>
            )}
            <button
              type="button"
              onClick={() => { onReply(asset); onClose(); }}
              data-testid="lightbox-reply"
              className="px-3 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-black text-xs font-bold flex items-center gap-1.5"
            >
              <Reply className="w-3.5 h-3.5" /> ردّ على الصورة
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// MARKDOWN TEXT (styled prose for AI messages)
// ─────────────────────────────────────────────────────────────
const MD_COMPONENTS = {
  h1: ({ node, ...p }) => <h1 className="text-base font-black text-emerald-200 mt-3 mb-2 first:mt-0" {...p} />,
  h2: ({ node, ...p }) => <h2 className="text-base font-black text-emerald-200 mt-3 mb-2 first:mt-0" {...p} />,
  h3: ({ node, ...p }) => <h3 className="text-sm font-black text-emerald-300 mt-2.5 mb-1.5 first:mt-0" {...p} />,
  p:  ({ node, ...p }) => <p className="text-sm leading-relaxed my-1.5" {...p} />,
  strong: ({ node, ...p }) => <strong className="font-bold text-emerald-100" {...p} />,
  em: ({ node, ...p }) => <em className="italic text-emerald-100" {...p} />,
  ul: ({ node, ...p }) => <ul className="my-2 space-y-1 pr-5 list-disc marker:text-emerald-400 text-sm" {...p} />,
  ol: ({ node, ...p }) => <ol className="my-2 space-y-1 pr-5 list-decimal marker:text-emerald-400 marker:font-bold text-sm" {...p} />,
  li: ({ node, ...p }) => <li className="leading-relaxed" {...p} />,
  a:  ({ node, ...p }) => <a className="text-cyan-400 hover:text-cyan-300 underline" target="_blank" rel="noreferrer" {...p} />,
  code: ({ inline, node, ...p }) =>
    inline
      ? <code className="px-1 py-0.5 rounded bg-black/40 text-amber-200 text-[12px] font-mono" {...p} />
      : <code className="block p-3 rounded-lg bg-black/50 text-amber-100 text-[12px] font-mono overflow-x-auto" {...p} />,
  pre: ({ node, ...p }) => <pre className="my-2 overflow-x-auto" {...p} />,
  blockquote: ({ node, ...p }) => <blockquote className="border-r-2 border-emerald-500/40 pr-3 my-2 text-zinc-300 italic" {...p} />,
};

function MarkdownText({ children }) {
  return (
    <div className="prose prose-invert max-w-none" dir="rtl">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
        {children || ''}
      </ReactMarkdown>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// OPTIONS PICKER (clickable pills the AI offers)
// ─────────────────────────────────────────────────────────────
function OptionsPicker({ messageIdx, options, savedAnswer, onConfirm }) {
  const [selected, setSelected] = useState([]);
  const [comment, setComment] = useState('');
  const [confirming, setConfirming] = useState(false);

  // If user already answered this question (saved on a later user turn), show the answer locked
  if (savedAnswer) {
    return (
      <div className="mt-3 flex flex-wrap gap-1.5" data-testid={`options-locked-${messageIdx}`}>
        {options.map((opt, i) => {
          const isPicked = savedAnswer.picks?.includes(opt);
          return (
            <span
              key={i}
              className={`px-2.5 py-1 rounded-full text-[11px] font-bold border ${
                isPicked
                  ? 'bg-emerald-500/30 border-emerald-400/60 text-emerald-100'
                  : 'bg-zinc-800/40 border-white/5 text-zinc-500 line-through opacity-60'
              }`}
            >
              {isPicked && '✓ '}{opt}
            </span>
          );
        })}
      </div>
    );
  }

  const toggle = (opt) => {
    setSelected((prev) => prev.includes(opt) ? prev.filter((x) => x !== opt) : [...prev, opt]);
  };

  const submit = async () => {
    if (selected.length === 0 && !comment.trim()) {
      toast.error('اختر خياراً أو اكتب تعليقاً');
      return;
    }
    setConfirming(true);
    try {
      await onConfirm({ picks: selected, comment: comment.trim() });
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="mt-3" data-testid={`options-${messageIdx}`}>
      <div className="flex flex-wrap gap-1.5">
        {options.map((opt, i) => {
          const isSelected = selected.includes(opt);
          return (
            <button
              key={i}
              type="button"
              onClick={() => toggle(opt)}
              disabled={confirming}
              data-testid={`option-${messageIdx}-${i}`}
              className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${
                isSelected
                  ? 'bg-emerald-500 border-emerald-400 text-black shadow-lg shadow-emerald-500/30'
                  : 'bg-white/5 border-white/15 text-zinc-200 hover:border-emerald-400/50 hover:bg-emerald-500/10'
              }`}
            >
              {isSelected && <Check className="w-3 h-3 inline -mt-0.5 ml-1" />}
              {opt}
            </button>
          );
        })}
      </div>
      {selected.length > 0 && (
        <p className="text-[11px] text-emerald-400 mt-2 font-bold">
          ✓ اخترت {selected.length} {selected.length === 1 ? 'خيار' : 'خيارات'}
        </p>
      )}
      <div className="mt-3 flex gap-2">
        <input
          type="text"
          placeholder="اكتب تعليق (اختياري)..."
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          disabled={confirming}
          data-testid={`option-comment-${messageIdx}`}
          className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-xs outline-none focus:border-emerald-400"
        />
        <button
          type="button"
          onClick={submit}
          disabled={confirming || (selected.length === 0 && !comment.trim())}
          data-testid={`option-confirm-${messageIdx}`}
          className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 disabled:from-zinc-700 disabled:to-zinc-800 text-black font-bold text-xs rounded-lg flex items-center gap-1.5"
        >
          {confirming ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : (
            <>
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>تأكيد</span>
            </>
          )}
        </button>
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
  const [attachments, setAttachments] = useState([]);
  const [replyToAsset, setReplyToAsset] = useState(null); // {id, type, image_url, prompt}
  const [lightboxAsset, setLightboxAsset] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activePhase, setActivePhase] = useState('discovery');
  const [activeTab, setActiveTab] = useState('chat'); // chat | live | approved
  const [previewMode, setPreviewMode] = useState('desktop');
  const [myProjectsOpen, setMyProjectsOpen] = useState(false);
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

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
    if ((!message.trim() && attachments.length === 0 && !replyToAsset) || loading) return;
    setLoading(true);
    const token = localStorage.getItem('token');
    const msgText = message;
    const filesToSend = attachments;
    const refAsset = replyToAsset;
    setMessage('');
    setAttachments([]);
    setReplyToAsset(null);
    try {
      const fd = new FormData();
      fd.append('message', msgText || '(انظر للصورة المرفقة)');
      filesToSend.forEach((f) => fd.append('files', f));
      if (refAsset?.id) fd.append('reference_asset_id', refAsset.id);
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/chat`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
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
      setAttachments(filesToSend);
      setReplyToAsset(refAsset);
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

  // Send a structured answer for an options question (called from OptionsPicker)
  const submitOptionAnswer = useCallback(async ({ picks, comment }) => {
    const token = localStorage.getItem('token');
    let textParts = [];
    if (picks.length > 0) {
      textParts.push(picks.length === 1 ? `اخترت: ${picks[0]}` : `اخترت: ${picks.join('، ')}`);
    }
    if (comment) textParts.push(comment);
    const fd = new FormData();
    fd.append('message', textParts.join('\n\n'));
    // Mark the answer so the UI can lock it
    fd.append('answer_meta', JSON.stringify({ picks, comment }));
    try {
      setLoading(true);
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/chat`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || 'فشل الإرسال');
      }
      const data = await r.json();
      if (data.html_updated) toast.success('✨ تم تحديث المعاينة الحية');
      const pr = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
      if (pr.ok) setProject(await pr.json());
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
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
                    {/* Quoted asset (WhatsApp-style reply) */}
                    {m.reference && m.reference.image_url && (
                      <button
                        type="button"
                        onClick={() => setLightboxAsset(m.reference)}
                        data-testid={`message-ref-${i}`}
                        className="mb-2 flex items-stretch gap-2 bg-black/30 border-r-2 border-emerald-400 rounded-lg overflow-hidden w-full text-right hover:bg-black/40"
                      >
                        <img
                          src={m.reference.image_url.startsWith('http') ? m.reference.image_url : `${API}${m.reference.image_url}`}
                          alt=""
                          className="w-12 h-12 object-cover shrink-0"
                        />
                        <div className="py-1.5 px-2 min-w-0 flex-1">
                          <p className="text-[10px] text-emerald-300 font-bold flex items-center gap-1">
                            <Reply className="w-3 h-3" /> ردّ على {m.reference.type}
                          </p>
                          <p className="text-[10px] text-zinc-400 truncate">{m.reference.prompt}</p>
                        </div>
                      </button>
                    )}
                    {m.attachments && m.attachments.length > 0 && (
                      <div className="mb-2 flex gap-1.5 flex-wrap">
                        {m.attachments.map((att, j) => (
                          <div key={j} className="px-2 py-1 bg-black/30 rounded-md flex items-center gap-1.5 text-[10px] text-emerald-200">
                            <Paperclip className="w-3 h-3" />
                            <span className="truncate max-w-[120px]">{att.name}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="text-sm leading-relaxed">
                      <MarkdownText>{m.content}</MarkdownText>
                    </div>

                    {/* Clickable options the AI offered */}
                    {m.role === 'assistant' && m.options && m.options.length > 0 && (
                      <OptionsPicker
                        messageIdx={i}
                        options={m.options}
                        savedAnswer={messages[i + 1]?.role === 'user' ? messages[i + 1]?.answer_meta : null}
                        onConfirm={submitOptionAnswer}
                      />
                    )}
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
                          <div key={a.id} className="rounded-lg bg-black/40 border border-emerald-500/20 overflow-hidden group" data-testid={`pending-asset-${a.id}`}>
                            {a.image_url ? (
                              <div className="relative">
                                <button
                                  type="button"
                                  onClick={() => setLightboxAsset(a)}
                                  data-testid={`zoom-asset-${a.id}`}
                                  className="block w-full"
                                  aria-label="تكبير الصورة"
                                >
                                  <img src={a.image_url.startsWith('http') ? a.image_url : `${API}${a.image_url}`} alt="" className="w-full aspect-video object-cover transition-transform group-hover:scale-[1.02]" />
                                </button>
                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center gap-2 pointer-events-none opacity-0 group-hover:opacity-100">
                                  <span className="pointer-events-auto">
                                    <button type="button" onClick={() => setLightboxAsset(a)} className="px-2.5 py-1.5 rounded-lg bg-white/15 backdrop-blur text-white text-xs font-bold flex items-center gap-1.5 hover:bg-white/25">
                                      <ZoomIn className="w-3.5 h-3.5" /> تكبير
                                    </button>
                                  </span>
                                  <span className="pointer-events-auto">
                                    <button type="button" onClick={() => setReplyToAsset(a)} data-testid={`reply-asset-${a.id}`} className="px-2.5 py-1.5 rounded-lg bg-emerald-500/80 backdrop-blur text-black text-xs font-bold flex items-center gap-1.5 hover:bg-emerald-400">
                                      <Reply className="w-3.5 h-3.5" /> ردّ
                                    </button>
                                  </span>
                                </div>
                              </div>
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
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => setLightboxAsset(a)}
                      data-testid={`approved-asset-${a.id}`}
                      className="rounded-xl overflow-hidden border border-violet-500/30 bg-black/30 hover:border-violet-400 transition-all text-right group"
                    >
                      {a.image_url && (
                        <div className="relative">
                          <img
                            src={a.image_url.startsWith('http') ? a.image_url : `${API}${a.image_url}`}
                            alt=""
                            className="w-full aspect-square object-cover transition-transform group-hover:scale-[1.04]"
                          />
                          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center">
                            <ZoomIn className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                          </div>
                        </div>
                      )}
                      <div className="p-2">
                        <p className="text-[10px] text-violet-300 font-bold">{a.type}</p>
                        <p className="text-[10px] text-zinc-500 truncate">{a.prompt}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Input bar (always visible at bottom) */}
          <div className="border-t border-white/10 p-3 sm:p-4 bg-zinc-900/50 shrink-0">
            {/* Reply-to-asset quote chip (WhatsApp-style) */}
            {replyToAsset && (
              <div className="mb-2 flex items-stretch gap-2 bg-black/40 border-r-2 border-emerald-400 rounded-lg overflow-hidden" data-testid="reply-quote">
                <img
                  src={replyToAsset.image_url?.startsWith('http') ? replyToAsset.image_url : `${API}${replyToAsset.image_url}`}
                  alt=""
                  className="w-14 h-14 object-cover shrink-0"
                />
                <div className="py-2 px-2 min-w-0 flex-1">
                  <p className="text-[11px] text-emerald-300 font-bold flex items-center gap-1">
                    <Reply className="w-3.5 h-3.5" /> ردّ على {replyToAsset.type}
                  </p>
                  <p className="text-[11px] text-zinc-400 truncate">{replyToAsset.prompt}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setReplyToAsset(null)}
                  data-testid="reply-quote-remove"
                  className="px-3 text-zinc-400 hover:text-red-400"
                  aria-label="إلغاء الرد"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Attached file chips */}
            {attachments.length > 0 && (
              <div className="mb-2 flex gap-2 flex-wrap" data-testid="attachment-chips">
                {attachments.map((file, i) => (
                  <div key={i} className="px-2.5 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center gap-2 text-xs">
                    <Paperclip className="w-3.5 h-3.5 text-emerald-300" />
                    <span className="text-emerald-100 max-w-[140px] truncate">{file.name}</span>
                    <button
                      type="button"
                      onClick={() => setAttachments(attachments.filter((_, j) => j !== i))}
                      data-testid={`remove-attachment-${i}`}
                      className="text-zinc-400 hover:text-red-400"
                      aria-label="إزالة المرفق"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              {/* Hidden file input */}
              <input
                type="file"
                ref={fileInputRef}
                accept="image/*"
                multiple
                onChange={(e) => {
                  const newFiles = Array.from(e.target.files || []);
                  setAttachments((prev) => [...prev, ...newFiles].slice(0, 4));
                  e.target.value = '';
                }}
                className="hidden"
                data-testid="file-input-hidden"
              />
              {/* Attach button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
                data-testid="attach-file-btn"
                title="أرفق صورة (Hero مرجعي، شعار قديم، إلهام...)"
                className="px-3 py-3 bg-white/5 hover:bg-emerald-500/20 hover:border-emerald-400/40 border border-white/10 rounded-xl transition-all text-zinc-300 hover:text-emerald-200 disabled:opacity-50"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              {/* Voice recorder */}
              <VoiceRecorderButton
                accentColor="emerald"
                disabled={loading}
                onTranscript={(text) => setMessage((m) => (m ? `${m.trim()} ${text}` : text))}
              />
              {/* Text input */}
              <input
                type="text"
                placeholder="اكتب أو سجّل صوت أو ارفع صورة..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
                disabled={loading}
                data-testid="chat-input"
                className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-3 outline-none focus:border-emerald-400 text-sm"
              />
              {/* Send */}
              <button
                type="button"
                onClick={send}
                disabled={loading || (!message.trim() && attachments.length === 0 && !replyToAsset)}
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
      <Lightbox
        open={!!lightboxAsset}
        asset={lightboxAsset}
        onClose={() => setLightboxAsset(null)}
        onReply={(a) => setReplyToAsset(a)}
        onApprove={approve}
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
