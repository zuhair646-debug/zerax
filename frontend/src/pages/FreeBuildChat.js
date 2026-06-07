import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Globe, Send, Loader2, Sparkles, Eye, ArrowRight, ArrowLeft,
  CheckCircle2, Check, Image as ImageIcon, FolderOpen, Code,
  Monitor, Smartphone, Trash2, MessageSquare, Paperclip, X,
  ZoomIn, Reply, Download, ExternalLink, Rocket, Smartphone as Phone,
  Crown, Github, Globe2, Cloud, Link2, Copy, FileText, Plug,
  History, RotateCcw, Clock,
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
          {asset.html ? (
            <iframe
              title={asset.prompt || 'design'}
              data-testid="lightbox-iframe"
              srcDoc={asset.html}
              sandbox="allow-scripts allow-same-origin"
              className="bg-white w-full max-h-[75vh]"
              style={{ height: '75vh' }}
            />
          ) : (
            <img
              src={fullUrl}
              alt={asset.prompt || 'asset'}
              className="max-w-full max-h-[75vh] object-contain"
              data-testid="lightbox-img"
            />
          )}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-900/70 border border-white/10 rounded-xl p-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs text-emerald-300 font-bold">{asset.type}</p>
            <p className="text-xs text-zinc-400 truncate">{asset.prompt}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {!asset.html && (
              <a
                href={fullUrl}
                download
                data-testid="lightbox-download"
                className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-200 text-xs font-bold flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" /> تنزيل
              </a>
            )}
            {onApprove && !asset.approved && !asset.html && (
              <button
                type="button"
                onClick={() => { onApprove(asset.id); onClose(); }}
                data-testid="lightbox-approve"
                className="px-3 py-2 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-400/40 text-emerald-200 text-xs font-bold flex items-center gap-1.5"
              >
                <Check className="w-3.5 h-3.5" /> اعتمد
              </button>
            )}
            {!asset.html && (
              <button
                type="button"
                onClick={() => { onReply(asset); onClose(); }}
                data-testid="lightbox-reply"
                className="px-3 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-black text-xs font-bold flex items-center gap-1.5"
              >
                <Reply className="w-3.5 h-3.5" /> ردّ على الصورة
              </button>
            )}
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
// Color accents rotated by option index (unselected only).
const OPT_ACCENTS = [
  { ring: 'hover:border-cyan-400/60 hover:bg-cyan-500/10',     num: 'bg-cyan-500/15 text-cyan-200 ring-cyan-400/30' },
  { ring: 'hover:border-violet-400/60 hover:bg-violet-500/10', num: 'bg-violet-500/15 text-violet-200 ring-violet-400/30' },
  { ring: 'hover:border-amber-400/60 hover:bg-amber-500/10',   num: 'bg-amber-500/15 text-amber-200 ring-amber-400/30' },
  { ring: 'hover:border-rose-400/60 hover:bg-rose-500/10',     num: 'bg-rose-500/15 text-rose-200 ring-rose-400/30' },
  { ring: 'hover:border-teal-400/60 hover:bg-teal-500/10',     num: 'bg-teal-500/15 text-teal-200 ring-teal-400/30' },
];

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
              className={`px-3 py-1.5 rounded-full text-[11px] font-bold border ${
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
      <div className="flex flex-wrap gap-2">
        {options.map((opt, i) => {
          const isSelected = selected.includes(opt);
          const accent = OPT_ACCENTS[i % OPT_ACCENTS.length];
          return (
            <button
              key={i}
              type="button"
              onClick={() => toggle(opt)}
              disabled={confirming}
              data-testid={`option-${messageIdx}-${i}`}
              className={`group inline-flex items-center gap-2 px-3 py-2 rounded-full text-xs font-bold border transition-all duration-200 ${
                isSelected
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-500 border-emerald-300 text-black shadow-lg shadow-emerald-500/40 scale-[1.02]'
                  : `bg-white/5 border-white/10 text-zinc-200 ${accent.ring}`
              }`}
            >
              <span
                className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black ring-1 ${
                  isSelected ? 'bg-black/30 text-emerald-100 ring-white/30' : `${accent.num} ring-1`
                }`}
              >
                {isSelected ? <Check className="w-3 h-3" /> : (i + 1)}
              </span>
              <span>{opt}</span>
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
// SNAPSHOTS MODAL — version history (auto-saved before every change)
// ─────────────────────────────────────────────────────────────
function SnapshotsModal({ open, projectId, onClose, onRestored }) {
  const [snaps, setSnaps] = useState([]);
  const [currentSummary, setCurrentSummary] = useState('');
  const [loading, setLoading] = useState(true);
  const [previewing, setPreviewing] = useState(null); // {id, html}
  const [restoring, setRestoring] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      const token = localStorage.getItem('token');
      try {
        const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/snapshots`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const d = await r.json();
        if (!cancelled && r.ok) {
          setSnaps(d.snapshots || []);
          setCurrentSummary(d.current_summary || '');
        }
      } catch {
        if (!cancelled) toast.error('فشل جلب السجل');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [open, projectId]);

  const previewSnap = async (sid) => {
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/snapshots/${sid}/preview`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      if (r.ok) setPreviewing({ id: sid, html: d.html });
    } catch {
      toast.error('فشل المعاينة');
    }
  };

  const restoreSnap = async (sid) => {
    if (restoring) return;
    if (!window.confirm('متأكد إنك تبي ترجع لهذي النسخة؟ النسخة الحالية راح تتحفظ في السجل تلقائياً.')) return;
    setRestoring(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/snapshots/${sid}/restore`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل الاسترجاع');
      toast.success(`✅ تم الاسترجاع — ${d.restored_summary}`);
      onRestored && onRestored();
      onClose();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setRestoring(false);
    }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" data-testid="snapshots-modal">
      <div className="bg-zinc-950 border border-amber-400/30 rounded-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden flex flex-col">
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-gradient-to-r from-amber-500/10 to-orange-500/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
              <History className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h2 className="text-lg font-black text-white">سجل النسخ المحفوظة</h2>
              <p className="text-xs text-zinc-400">يحفظ النظام تلقائياً نسخة قبل كل تعديل (آخر 20 نسخة)</p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="text-zinc-400 hover:text-white p-2" data-testid="snapshots-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 grid lg:grid-cols-[1fr_1.3fr] gap-4">
          {/* LEFT: snapshots list */}
          <div className="space-y-2">
            <div className="rounded-lg border-2 border-emerald-400/40 bg-emerald-500/5 p-3" data-testid="current-version">
              <div className="text-[10px] text-emerald-400 font-bold mb-1 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> النسخة الحالية
              </div>
              <div className="text-xs text-white truncate">{currentSummary || '—'}</div>
            </div>
            {loading ? (
              <div className="text-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-amber-400 mx-auto" />
              </div>
            ) : snaps.length === 0 ? (
              <div className="text-center py-8 text-zinc-500 text-sm">
                لا يوجد نسخ سابقة. سيتم حفظ النسخ هنا تلقائياً عند كل تعديل.
              </div>
            ) : (
              snaps.map((s) => (
                <div
                  key={s.id}
                  className={`rounded-lg border p-3 transition-all cursor-pointer ${
                    previewing?.id === s.id
                      ? 'border-amber-400 bg-amber-500/10'
                      : 'border-white/10 bg-white/5 hover:bg-white/10'
                  }`}
                  onClick={() => previewSnap(s.id)}
                  data-testid={`snapshot-${s.id}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5 text-[10px] text-zinc-400">
                      <Clock className="w-3 h-3" />
                      <span>{new Date(s.created_at).toLocaleString('ar-SA')}</span>
                    </div>
                    <span className="text-[10px] text-zinc-500">{(s.size / 1024).toFixed(1)} KB</span>
                  </div>
                  <div className="text-xs text-white mb-1.5 truncate">{s.summary}</div>
                  {s.user_msg && (
                    <div className="text-[10px] text-zinc-500 italic truncate" dir="rtl">
                      الطلب: {s.user_msg}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); restoreSnap(s.id); }}
                    disabled={restoring}
                    data-testid={`restore-${s.id}`}
                    className="mt-2 w-full px-2 py-1 rounded text-[11px] bg-amber-500/20 hover:bg-amber-500/30 border border-amber-400/30 text-amber-200 font-bold flex items-center justify-center gap-1 disabled:opacity-50"
                  >
                    <RotateCcw className="w-3 h-3" />
                    استرجاع هذي النسخة
                  </button>
                </div>
              ))
            )}
          </div>

          {/* RIGHT: live preview of selected snapshot */}
          <div className="rounded-lg border border-white/10 bg-zinc-900 overflow-hidden" style={{ minHeight: '500px' }}>
            <div className="bg-zinc-800/60 border-b border-white/10 px-3 py-2 text-xs text-zinc-400 flex items-center gap-2">
              <Eye className="w-3.5 h-3.5" />
              {previewing ? 'معاينة النسخة المحددة' : 'اضغط على أي نسخة يسار لعرضها'}
            </div>
            {previewing ? (
              <iframe
                title="snapshot-preview"
                srcDoc={previewing.html}
                sandbox=""
                className="w-full h-full border-none bg-white"
                style={{ minHeight: '460px' }}
                data-testid="snapshot-preview-iframe"
              />
            ) : (
              <div className="h-full flex items-center justify-center text-zinc-600 text-sm" style={{ minHeight: '460px' }}>
                لا يوجد معاينة بعد
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// FINALIZE PROJECT MODAL (Hosting / Take Code / Guided)
// ─────────────────────────────────────────────────────────────
function FinalizeModal({ open, projectId, projectName, onClose, onConverted, onUnlocked }) {
  const [paths, setPaths] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem('token');
        const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/finalize-options`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          toast.error(err.detail || 'يجب إكمال الموقع أولاً');
          return;
        }
        const d = await r.json();
        if (!cancelled) setPaths(d.paths || []);
      } finally { if (!cancelled) setLoading(false); }
    };
    load();
    return () => { cancelled = true; };
  }, [open, projectId]);

  const choose = async (pathId, priceUsd) => {
    if (pathId === 'host_with_us') {
      toast.success('🚀 موقعك سينشر على Zitex قريباً — جاري الإعداد');
      return;
    }
    // Paid tiers: unlock (MOCKED — Lemon Squeezy wiring later)
    const tier = pathId === 'take_code_guided' ? 'guided' : 'code_only';
    setBusy(pathId);
    try {
      const token = localStorage.getItem('token');
      const fd = new FormData();
      fd.append('tier', tier);
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/unlock`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd,
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || 'فشل التفعيل');
      }
      toast.success(`✅ تم تفعيل باقة ${priceUsd > 0 ? `$${priceUsd}` : ''} — اربط حساباتك`);
      onUnlocked?.();
    } catch (e) {
      toast.error(e.message);
    } finally { setBusy(''); }
  };

  const convertToApp = async () => {
    setBusy('convert');
    try {
      const token = localStorage.getItem('token');
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/convert-to-app`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل التحويل');
      toast.success('✓ تم نقل المشروع لقسم التطبيقات');
      onConverted?.(d.app_id);
    } catch (e) {
      toast.error(e.message);
    } finally { setBusy(''); }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[55] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto" onClick={onClose}>
      <div
        className="bg-zinc-900 border border-emerald-500/30 rounded-2xl max-w-5xl w-full my-8 shadow-2xl shadow-emerald-500/10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-5 border-b border-white/10 flex items-center justify-between">
          <div>
            <h3 className="text-xl font-black flex items-center gap-2">
              <Rocket className="w-6 h-6 text-emerald-400" />
              <span>إنهاء المشروع</span>
            </h3>
            <p className="text-xs text-zinc-500 mt-1">{projectName} — اختر كيف تكمل من هنا</p>
          </div>
          <button type="button" onClick={onClose} className="text-zinc-400 hover:text-white p-2" data-testid="finalize-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5">
          {loading ? (
            <div className="text-center py-12 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
              <p className="text-sm">جاري التحميل...</p>
            </div>
          ) : (
            <div className="grid md:grid-cols-3 gap-4">
              {paths.map((p, i) => {
                const isFree = p.price_usd === 0;
                return (
                  <div
                    key={p.id}
                    data-testid={`finalize-path-${p.id}`}
                    className={`relative rounded-xl border p-5 flex flex-col transition-all hover:scale-[1.02] ${
                      isFree
                        ? 'border-emerald-400/60 bg-gradient-to-b from-emerald-500/15 to-zinc-900'
                        : i === 2
                        ? 'border-amber-400/40 bg-gradient-to-b from-amber-500/10 to-zinc-900'
                        : 'border-cyan-400/40 bg-gradient-to-b from-cyan-500/10 to-zinc-900'
                    }`}
                  >
                    {isFree && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-emerald-500 text-black text-[10px] font-black">
                        ✨ الأنسب
                      </div>
                    )}
                    {i === 2 && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-amber-500 text-black text-[10px] font-black flex items-center gap-1">
                        <Crown className="w-3 h-3" /> الأكثر طلباً
                      </div>
                    )}
                    <h4 className="text-base font-black mb-1">{p.title}</h4>
                    <p className="text-3xl font-black mb-1">
                      {isFree ? (
                        <span className="text-emerald-300">مجاناً</span>
                      ) : (
                        <span className="text-white">${p.price_usd}</span>
                      )}
                    </p>
                    <p className="text-xs text-zinc-400 mb-4 leading-relaxed">{p.subtitle}</p>
                    <ul className="space-y-1.5 mb-5 text-xs text-zinc-300 flex-1">
                      {p.features.map((f, j) => (
                        <li key={j} className="flex items-start gap-2">
                          <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>
                    <button
                      type="button"
                      onClick={() => choose(p.id, p.price_usd)}
                      disabled={busy === p.id}
                      data-testid={`finalize-btn-${p.id}`}
                      className={`w-full py-2.5 rounded-lg font-black text-sm transition-all ${
                        isFree
                          ? 'bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-black'
                          : i === 2
                          ? 'bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-black'
                          : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black'
                      }`}
                    >
                      {busy === p.id ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : p.cta}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Convert to App */}
        <div className="p-5 border-t border-white/10 bg-gradient-to-r from-violet-500/5 to-fuchsia-500/5 rounded-b-2xl">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-violet-500/20 flex items-center justify-center">
                <Phone className="w-6 h-6 text-violet-300" />
              </div>
              <div>
                <h4 className="font-black text-base flex items-center gap-2">
                  حوّل الموقع لتطبيق موبايل
                  <span className="text-[9px] bg-violet-500/30 text-violet-200 px-1.5 py-0.5 rounded">BETA</span>
                </h4>
                <p className="text-xs text-zinc-400 mt-0.5">ينتقل المشروع لقسم التطبيقات + ذكاء متخصص يكمل التحويل</p>
              </div>
            </div>
            <button
              type="button"
              onClick={convertToApp}
              disabled={busy === 'convert'}
              data-testid="convert-to-app-btn"
              className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-600 hover:from-violet-400 hover:to-fuchsia-500 text-white font-black text-sm flex items-center gap-2 shadow-lg shadow-violet-500/20 whitespace-nowrap"
            >
              {busy === 'convert' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Phone className="w-4 h-4" />
                  <span>تحويل لتطبيق</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// CONNECTIONS PANEL (GitHub / Vercel / Cloudflare / Domain)
// ─────────────────────────────────────────────────────────────
const PROVIDERS = [
  {
    id: 'github',
    title: 'GitHub',
    icon: Github,
    color: 'from-gray-700 to-gray-900',
    accent: 'gray',
    docs: 'https://github.com/settings/tokens?type=beta',
    docsLabel: 'احصل على Personal Access Token',
    hint: 'الصلاحيات: Contents (Read/Write) + Workflows. اللي تتم منه عمليات النشر.',
    placeholder: 'ghp_xxxxxxxxxxxxxxxxx',
    needsExtra: false,
  },
  {
    id: 'vercel',
    title: 'Vercel',
    icon: Globe2,
    color: 'from-black to-zinc-700',
    accent: 'zinc',
    docs: 'https://vercel.com/account/tokens',
    docsLabel: 'احصل على Vercel API Token',
    hint: 'لنشر الموقع تلقائياً مع CDN عالمي.',
    placeholder: 'vercel_xxxxxxxxxxxx',
    needsExtra: false,
  },
  {
    id: 'cloudflare',
    title: 'Cloudflare',
    icon: Cloud,
    color: 'from-orange-500 to-amber-600',
    accent: 'orange',
    docs: 'https://dash.cloudflare.com/profile/api-tokens',
    docsLabel: 'احصل على API Token',
    hint: 'لإدارة DNS والدومين والـ Pages.',
    placeholder: 'cf_xxxxxxxxxxxxxxxx',
    needsExtra: false,
  },
  {
    id: 'domain',
    title: 'دومين مخصص',
    icon: Link2,
    color: 'from-emerald-500 to-teal-600',
    accent: 'emerald',
    docs: null,
    docsLabel: '',
    hint: 'ادخل الدومين اللي تبي تربطه (مثل: myshop.com).',
    placeholder: 'example.com',
    needsExtra: false,
  },
];

function ConnectionsPanel({ open, projectId, onClose }) {
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drafts, setDrafts] = useState({}); // {github: 'ghp_...', vercel: '...'}
  const [busy, setBusy] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/connections`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) {
        const d = await r.json();
        setConnections(d.connections || []);
      }
    } finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    (async () => { if (!cancelled) await load(); })();
    return () => { cancelled = true; };
  }, [open, load]);

  const save = async (providerId) => {
    const token = (drafts[providerId] || '').trim();
    if (!token) { toast.error('أدخل القيمة أولاً'); return; }
    setBusy(providerId);
    try {
      const authToken = localStorage.getItem('token');
      const fd = new FormData();
      fd.append('token', token);
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/connections/${providerId}`, {
        method: 'POST', headers: { Authorization: `Bearer ${authToken}` }, body: fd,
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || 'فشل الحفظ');
      }
      toast.success(`✅ تم ربط ${providerId}`);
      setDrafts((d) => ({ ...d, [providerId]: '' }));
      await load();
    } catch (e) {
      toast.error(e.message);
    } finally { setBusy(''); }
  };

  const remove = async (providerId) => {
    if (!window.confirm('إلغاء الربط؟')) return;
    setBusy(`del-${providerId}`);
    try {
      const authToken = localStorage.getItem('token');
      await fetch(`${API}/api/freebuild-chat/project/${projectId}/connections/${providerId}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${authToken}` },
      });
      await load();
    } finally { setBusy(''); }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[58] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto" onClick={onClose}>
      <div className="bg-zinc-900 border border-emerald-500/30 rounded-2xl max-w-4xl w-full my-8 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="p-5 border-b border-white/10 flex items-center justify-between">
          <div>
            <h3 className="text-xl font-black flex items-center gap-2">
              <Plug className="w-6 h-6 text-emerald-400" />
              <span>اتصالات النشر</span>
            </h3>
            <p className="text-xs text-zinc-500 mt-1">اربط حساباتك وخلي الذكاء يتولى النشر بهدوء خطوة بخطوة</p>
          </div>
          <button type="button" onClick={onClose} className="text-zinc-400 hover:text-white p-2" data-testid="connections-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-3">
          {loading ? (
            <div className="text-center py-10 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
              <p className="text-sm">جاري التحميل...</p>
            </div>
          ) : PROVIDERS.map((p) => {
            const Icon = p.icon;
            const existing = connections.find((c) => c.provider === p.id);
            const draft = drafts[p.id] || '';
            return (
              <div key={p.id} data-testid={`conn-card-${p.id}`} className={`rounded-xl border bg-gradient-to-l ${p.color} bg-opacity-10 p-4`}>
                <div className="flex items-center justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-lg bg-black/40 flex items-center justify-center shrink-0">
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h4 className="font-black text-sm">{p.title}</h4>
                      <p className="text-[11px] text-zinc-300/70">{p.hint}</p>
                    </div>
                  </div>
                  {existing ? (
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="px-2 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/40 text-emerald-200 text-[10px] font-bold flex items-center gap-1">
                        <Check className="w-3 h-3" />
                        {existing.mask}
                      </span>
                      <button
                        type="button"
                        onClick={() => remove(p.id)}
                        disabled={busy === `del-${p.id}`}
                        data-testid={`conn-remove-${p.id}`}
                        className="text-zinc-400 hover:text-red-400 p-1"
                        aria-label="إلغاء"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <span className="px-2 py-1 rounded-full bg-zinc-700/40 border border-white/10 text-zinc-400 text-[10px] font-bold">
                      غير مربوط
                    </span>
                  )}
                </div>
                {!existing && (
                  <div className="mt-3 space-y-2">
                    <div className="flex gap-2">
                      <input
                        type="password"
                        placeholder={p.placeholder}
                        value={draft}
                        onChange={(e) => setDrafts((d) => ({ ...d, [p.id]: e.target.value }))}
                        data-testid={`conn-input-${p.id}`}
                        className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-emerald-100 font-mono outline-none focus:border-emerald-400"
                      />
                      <button
                        type="button"
                        onClick={() => save(p.id)}
                        disabled={busy === p.id || !draft.trim()}
                        data-testid={`conn-save-${p.id}`}
                        className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 disabled:bg-zinc-700 disabled:text-zinc-500 text-black text-xs font-black flex items-center gap-1.5"
                      >
                        {busy === p.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'احفظ'}
                      </button>
                    </div>
                    {p.docs && (
                      <a
                        href={p.docs}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-[11px] text-cyan-400 hover:text-cyan-300 underline"
                      >
                        <ExternalLink className="w-3 h-3" /> {p.docsLabel}
                      </a>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="p-4 border-t border-white/10 bg-black/30 rounded-b-2xl text-xs text-zinc-400">
          🔐 جميع المفاتيح تُحفظ مشفّرة في قاعدة البيانات (Fernet AES). لا يتم عرضها بعد الحفظ.
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// CODE ACTIONS PANEL (after code is unlocked)
// ─────────────────────────────────────────────────────────────
function CodeActions({ project, projectId, onOpenConnections }) {
  const [pushing, setPushing] = useState(false);
  const [repoName, setRepoName] = useState(() =>
    (project.name || 'zitex-site')
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-')
      .slice(0, 40) || 'zitex-site'
  );

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(project.current_html || '');
      toast.success('✓ تم نسخ الكود الكامل');
    } catch {
      toast.error('فشل النسخ');
    }
  };

  const downloadHtml = () => {
    const blob = new Blob([project.current_html || ''], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${repoName || 'site'}.html`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast.success('✓ تم التنزيل');
  };

  const exportPdf = () => {
    // Print-to-PDF via opening the iframe content with auto print
    const win = window.open('', '_blank');
    if (!win) { toast.error('السماح بالنوافذ المنبثقة مطلوب'); return; }
    win.document.write(project.current_html || '');
    win.document.close();
    setTimeout(() => { try { win.print(); } catch (e) { /* user can press Cmd+P */ } }, 700);
    toast.info('اختر "حفظ كـ PDF" من نافذة الطباعة');
  };

  const pushToGithub = async () => {
    if (!repoName.trim()) { toast.error('أدخل اسم المستودع'); return; }
    setPushing(true);
    try {
      const token = localStorage.getItem('token');
      const fd = new FormData();
      fd.append('repo_name', repoName.trim());
      fd.append('private', 'false');
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/push-to-github`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd,
      });
      const d = await r.json();
      if (!r.ok) {
        if ((d.detail || '').includes('ربط GitHub')) {
          toast.error('اربط GitHub أولاً من زر "الاتصالات"');
          onOpenConnections?.();
          return;
        }
        throw new Error(d.detail || 'فشل النشر');
      }
      toast.success('🚀 تم نشر الموقع على GitHub!');
      window.open(d.repo_url, '_blank', 'noopener,noreferrer');
    } catch (e) {
      toast.error(e.message);
    } finally { setPushing(false); }
  };

  return (
    <div className="rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/5 to-orange-500/5 p-3" data-testid="code-actions">
      <div className="flex items-center justify-between mb-2.5">
        <h4 className="text-sm font-black text-amber-200 flex items-center gap-2">
          <Crown className="w-4 h-4 text-amber-400" /> <span>أدوات الاستقلالية</span>
        </h4>
        <button
          type="button"
          onClick={onOpenConnections}
          data-testid="open-connections-from-actions"
          className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
        >
          <Plug className="w-3 h-3" /> الاتصالات
        </button>
      </div>
      <div className="flex flex-wrap gap-2 mb-3">
        <button type="button" onClick={copyAll} data-testid="code-copy-btn"
          className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-200 text-xs font-bold flex items-center gap-1.5">
          <Copy className="w-3.5 h-3.5" /> نسخ الكود
        </button>
        <button type="button" onClick={downloadHtml} data-testid="code-download-btn"
          className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-200 text-xs font-bold flex items-center gap-1.5">
          <Download className="w-3.5 h-3.5" /> تنزيل HTML
        </button>
        <button type="button" onClick={exportPdf} data-testid="code-pdf-btn"
          className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-200 text-xs font-bold flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5" /> PDF
        </button>
      </div>
      <div className="flex gap-2 items-center">
        <Github className="w-4 h-4 text-zinc-400 shrink-0" />
        <input
          type="text"
          placeholder="اسم المستودع"
          value={repoName}
          onChange={(e) => setRepoName(e.target.value)}
          data-testid="github-repo-input"
          className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-1.5 text-xs font-mono outline-none focus:border-emerald-400"
        />
        <button type="button" onClick={pushToGithub} disabled={pushing}
          data-testid="push-to-github-btn"
          className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-zinc-700 to-zinc-900 hover:from-zinc-600 hover:to-zinc-800 text-white text-xs font-bold flex items-center gap-1.5">
          {pushing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Github className="w-3.5 h-3.5" />}
          <span>ادفع لـ GitHub</span>
        </button>
      </div>
      {project.github_repo_url && (
        <p className="mt-2 text-[11px] text-emerald-400">
          ✓ آخر دفعة: <a href={project.github_repo_url} target="_blank" rel="noreferrer" className="underline hover:text-emerald-300">{project.github_repo_url.replace('https://github.com/', '')}</a>
        </p>
      )}
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
  const [finalizeOpen, setFinalizeOpen] = useState(false);
  const [connectionsOpen, setConnectionsOpen] = useState(false);
  const [snapshotsOpen, setSnapshotsOpen] = useState(false);
  const [thinkingStage, setThinkingStage] = useState(0);
  const [lastTask, setLastTask] = useState(null); // {label, model}
  const [loading, setLoading] = useState(false);
  const [activePhase, setActivePhase] = useState('discovery');
  const [activeTab, setActiveTab] = useState('chat'); // chat | live | approved
  const [previewMode, setPreviewMode] = useState('desktop');
  const [myProjectsOpen, setMyProjectsOpen] = useState(false);
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Pause polling while modals are open (avoids modal flicker on re-render)
  const pollPausedRef = useRef(false);
  useEffect(() => {
    pollPausedRef.current = finalizeOpen || connectionsOpen || snapshotsOpen || !!lightboxAsset;
  }, [finalizeOpen, connectionsOpen, snapshotsOpen, lightboxAsset]);

  // Manual force-refresh of project (used by 'Refresh' button)
  const [previewKey, setPreviewKey] = useState(0);
  const refreshProject = useCallback(async () => {
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) {
        const d = await r.json();
        setProject(d);
        setPreviewKey((k) => k + 1); // force iframe remount
        toast.success('🔄 تم تحديث المعاينة');
      }
    } catch (e) {
      toast.error('فشل التحديث');
    }
  }, [projectId]);

  // Fetch + poll project state (skip update if nothing changed)
  useEffect(() => {
    let cancelled = false;
    const token = localStorage.getItem('token');
    const tick = async () => {
      if (pollPausedRef.current) return;
      try {
        const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
        if (r.ok && !cancelled) {
          const d = await r.json();
          setProject((prev) => {
            // Skip setState if nothing meaningful changed (avoids child re-renders)
            if (prev && prev.updated_at === d.updated_at && prev.messages?.length === d.messages?.length) {
              return prev;
            }
            // Force iframe remount only if HTML actually changed
            if (prev && prev.current_html !== d.current_html) {
              setPreviewKey((k) => k + 1);
            }
            return d;
          });
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
    setThinkingStage(0);
    const token = localStorage.getItem('token');
    const msgText = message;
    const filesToSend = attachments;
    const refAsset = replyToAsset;
    setMessage('');
    setAttachments([]);
    setReplyToAsset(null);

    // Live thinking is now driven by SSE events from the agent (see agent_steps).
    // The legacy fake-stage timer is gone — real tool calls stream into the UI.
    const stageTimer = null;

    try {
      const fd = new FormData();
      fd.append('message', msgText || '(انظر للصورة المرفقة)');
      filesToSend.forEach((f) => fd.append('files', f));
      if (refAsset?.id) fd.append('reference_asset_id', refAsset.id);
      // Use streaming agent endpoint when no files attached (so user sees the AI's
      // live thinking — every tool call streams into the chat as a visible step)
      const useAgent = filesToSend.length === 0 && !refAsset?.id;
      if (useAgent) {
        // Stream Server-Sent Events; render each step live
        const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/agent-chat-stream`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: fd,
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const reader = r.body.getReader();
        const decoder = new TextDecoder();
        let buf = '';
        let finalSummary = '';
        let finalOptions = [];
        let liveSteps = [];
        let htmlUpdated = false;
        const stepsHolderId = `agent-steps-${Date.now()}`;
        // Push a placeholder assistant message we'll update live
        setProject((p) => p ? {
          ...p,
          messages: [...(p.messages || []),
            { role: 'user', content: msgText, timestamp: new Date().toISOString(), reference: refAsset, attachments: [] },
            { role: 'assistant', content: '', timestamp: new Date().toISOString(),
              agent_steps: [], agent_streaming: true, agent_holder_id: stepsHolderId },
          ],
        } : p);

        const updateLive = () => {
          setProject((p) => {
            if (!p) return p;
            const msgs = [...(p.messages || [])];
            for (let i = msgs.length - 1; i >= 0; i--) {
              if (msgs[i].agent_holder_id === stepsHolderId) {
                msgs[i] = { ...msgs[i], agent_steps: [...liveSteps], content: finalSummary || msgs[i].content };
                break;
              }
            }
            return { ...p, messages: msgs };
          });
        };

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buf.indexOf('\n\n')) !== -1) {
            const raw = buf.slice(0, idx);
            buf = buf.slice(idx + 2);
            const lines = raw.split('\n');
            let eventName = 'message';
            let dataStr = '';
            for (const ln of lines) {
              if (ln.startsWith('event:')) eventName = ln.slice(6).trim();
              else if (ln.startsWith('data:')) dataStr = ln.slice(5).trim();
            }
            if (!dataStr) continue;
            let payload;
            try { payload = JSON.parse(dataStr); } catch { continue; }
            if (eventName === 'start' || eventName === 'provider' || eventName === 'fallback') {
              liveSteps.push({ kind: eventName, ...payload });
            } else if (eventName === 'thinking') {
              liveSteps.push({ kind: 'thinking', text: payload.text });
            } else if (eventName === 'tool') {
              liveSteps.push({ kind: 'tool', ...payload });
            } else if (eventName === 'done') {
              finalSummary = payload.summary || '';
              finalOptions = payload.options || [];
              htmlUpdated = !!payload.html_updated;
              setLastTask({ label: `🤖 Agent (${payload.iterations || 0} خطوة)`, model: payload.model_used || '' });
            } else if (eventName === 'error') {
              liveSteps.push({ kind: 'error', message: payload.message });
            }
            updateLive();
          }
        }
        // Finalize: mark message as not streaming
        setProject((p) => {
          if (!p) return p;
          const msgs = [...(p.messages || [])];
          for (let i = msgs.length - 1; i >= 0; i--) {
            if (msgs[i].agent_holder_id === stepsHolderId) {
              msgs[i] = { ...msgs[i], agent_streaming: false, options: finalOptions, content: finalSummary };
              break;
            }
          }
          return { ...p, messages: msgs };
        });
        if (htmlUpdated) {
          toast.success('✨ تم تحديث المعاينة الحية', {
            action: { label: 'افتح', onClick: () => setActiveTab('live') },
          });
          setActiveTab((prev) => (prev === 'chat' ? 'live' : prev));
          // refresh full project to get new current_html
          const pr = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
          if (pr.ok) setProject(await pr.json());
        }
        // Skip the rest of the legacy path
        setMessage('');
        setLoading(false);
        clearInterval(stageTimer);
        setThinkingStage(0);
        return;
      }
      const endpoint = `${API}/api/freebuild-chat/project/${projectId}/chat`;
      const r = await fetch(endpoint, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || 'فشل الإرسال');
      }
      const data = await r.json();
      if (data.html_updated) {
        const iters = data.agent_iterations || 0;
        const msg = iters > 0
          ? `✨ تم تحديث المعاينة (🔁 ${iters} إصلاح تلقائي)`
          : '✨ تم تحديث المعاينة الحية';
        toast.success(msg, {
          action: { label: 'افتح', onClick: () => setActiveTab('live') },
        });
        setActiveTab((prev) => (prev === 'chat' ? 'live' : prev));
      }
      // Capture which AI model worked on this turn (for UI display)
      if (data.task_label || data.model_used) {
        setLastTask({ label: data.task_label || '', model: data.model_used || '' });
      }
      // Refresh
      const pr = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
      if (pr.ok) setProject(await pr.json());
    } catch (e) {
      toast.error(e.message);
      setMessage(msgText); // restore on error
      setAttachments(filesToSend);
      setReplyToAsset(refAsset);
    } finally {
      clearInterval(stageTimer);
      setLoading(false);
      setThinkingStage(0);
    }
  };

  // Note: legacy THINKING_STAGES removed — replaced by live SSE agent steps
  // streamed directly into the assistant message bubble (see agent_steps in JSX).

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

  const approveDesign = useCallback(async (variantId) => {
    const token = localStorage.getItem('token');
    const fd = new FormData();
    fd.append('variant_id', variantId);
    const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/approve-design`, {
      method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd,
    });
    if (r.ok) {
      toast.success('✨ تم اعتماد التصميم — شاهده في المعاينة الحية');
      const pr = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
      if (pr.ok) setProject(await pr.json());
      setActiveTab('live');
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
      if (data.html_updated) {
        toast.success('✨ تم تحديث المعاينة الحية', {
          action: { label: 'افتح', onClick: () => setActiveTab('live') },
        });
        setActiveTab((prev) => (prev === 'chat' ? 'live' : prev));
      }
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
          {project.current_html && (
            <button
              type="button"
              onClick={() => setSnapshotsOpen(true)}
              data-testid="open-snapshots"
              className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-amber-400/30 text-amber-200 text-xs font-bold flex items-center gap-1.5"
              title="سجل النسخ — استرجاع نسخة سابقة"
            >
              <History className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">السجل</span>
            </button>
          )}
          {project.code_unlocked && (
            <button
              type="button"
              onClick={() => setConnectionsOpen(true)}
              data-testid="open-connections"
              className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-emerald-400/30 text-emerald-200 text-xs font-bold flex items-center gap-1.5"
              title="ربط GitHub / Vercel / Cloudflare"
            >
              <Plug className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">الاتصالات</span>
            </button>
          )}
          {project.current_html && (
            <button
              type="button"
              onClick={() => setFinalizeOpen(true)}
              data-testid="open-finalize"
              className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-black text-xs font-black flex items-center gap-1.5 shadow-lg shadow-emerald-500/20"
              title="نشر / استلام / تحويل"
            >
              <Rocket className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">إنهاء المشروع</span>
              <span className="sm:hidden">إنهاء</span>
            </button>
          )}
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
              // Compute a per-phase status hint
              let stat = '';
              const qcount = messages.filter((mm) => mm.role === 'assistant' && (mm.options || []).length > 0).length;
              const variantsCount = messages.reduce((s, mm) => s + (mm.design_variants?.length || 0), 0);
              if (phase.id === 'discovery') stat = `${qcount} سؤال طُرح`;
              else if (phase.id === 'design')   stat = variantsCount > 0 ? `${variantsCount} تصميم` : 'بانتظار خيارات';
              else if (phase.id === 'assets')   stat = `${approvedAssets.length} معتمد`;
              else if (phase.id === 'build')    stat = project.code_unlocked ? '🔓 مفتوح' : '🔒 مقفل';
              else if (phase.id === 'preview')  stat = project.current_html ? '✓ جاهز' : '—';
              else if (phase.id === 'deploy')   stat = project.github_repo_url ? '✓ منشور' : '—';

              const handleClick = () => {
                setActivePhase(phase.id);
                // Functional routing — each phase opens the right context
                if (phase.id === 'assets') setActiveTab('approved');
                else if (phase.id === 'preview') setActiveTab('live');
                else if (phase.id === 'build') {
                  if (project.code_unlocked) setActiveTab('live');
                  else setFinalizeOpen(true);
                } else if (phase.id === 'deploy') {
                  if (project.code_unlocked) setConnectionsOpen(true);
                  else setFinalizeOpen(true);
                } else {
                  setActiveTab('chat');
                }
              };

              return (
                <button
                  key={phase.id}
                  type="button"
                  onClick={handleClick}
                  data-testid={`phase-${phase.id}`}
                  className={`w-full text-right p-3 rounded-lg border transition-all ${
                    isActive
                      ? 'bg-emerald-500/15 border-emerald-500/50 text-emerald-200'
                      : 'bg-black/20 border-white/10 hover:border-emerald-400/30 text-zinc-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1 gap-1">
                    <span className="text-sm font-bold flex items-center gap-1.5 min-w-0">
                      <span>{phase.icon}</span><span className="truncate">{phase.title}</span>
                    </span>
                    {isActive && <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />}
                  </div>
                  <p className="text-[10px] text-zinc-500 leading-tight">{phase.desc}</p>
                  <p className="text-[10px] mt-1 text-emerald-300/80 font-bold">{stat}</p>
                </button>
              );
            })}
          </div>

          {/* Lock-state mini card for "Build" phase */}
          {!project.code_unlocked && (
            <div className="mt-4 rounded-lg border border-amber-500/30 bg-gradient-to-b from-amber-500/10 to-zinc-900 p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-7 h-7 rounded-md bg-amber-500/20 flex items-center justify-center">
                  <Crown className="w-3.5 h-3.5 text-amber-300" />
                </span>
                <h4 className="text-xs font-black text-amber-200">الكود مقفل</h4>
              </div>
              <p className="text-[10px] text-amber-100/70 leading-relaxed mb-2">
                الموقع جاهز للعرض. للاطلاع على الكود ودفعه لـ GitHub، فعّل باقة الاستقلالية.
              </p>
              <button
                type="button"
                onClick={() => setFinalizeOpen(true)}
                data-testid="phase-unlock-btn"
                className="w-full py-1.5 rounded-md bg-amber-500 hover:bg-amber-400 text-black text-[11px] font-black"
                disabled={!project.current_html}
              >
                {project.current_html ? 'افتح الباقات' : 'أكمل الموقع أولاً'}
              </button>
            </div>
          )}
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

                    {/* Agent live thinking — visible while the agent reasons/calls tools */}
                    {m.role === 'assistant' && Array.isArray(m.agent_steps) && m.agent_steps.length > 0 && (
                      <div className="mt-3 space-y-1.5" data-testid={`agent-steps-${i}`}>
                        {m.agent_steps.map((s, sIdx) => {
                          if (s.kind === 'thinking') {
                            return (
                              <div key={sIdx} className="flex gap-2 text-xs text-zinc-400 bg-zinc-900/50 border-r-2 border-cyan-500/40 px-3 py-1.5 rounded">
                                <span className="text-cyan-300">💭</span>
                                <span className="italic">{s.text}</span>
                              </div>
                            );
                          }
                          if (s.kind === 'tool') {
                            const isDone = s.phase === 'done';
                            return (
                              <div key={sIdx} className={`flex gap-2 text-[11px] px-3 py-1.5 rounded border ${
                                isDone
                                  ? 'bg-emerald-500/5 border-emerald-400/20 text-emerald-200'
                                  : 'bg-amber-500/5 border-amber-400/30 text-amber-200 animate-pulse'
                              }`}>
                                <span>{s.label}</span>
                              </div>
                            );
                          }
                          if (s.kind === 'provider') {
                            return (
                              <div key={sIdx} className="text-[10px] text-zinc-500 px-3">
                                {s.message}
                              </div>
                            );
                          }
                          if (s.kind === 'fallback') {
                            return (
                              <div key={sIdx} className="text-[10px] text-amber-400 px-3">
                                ⚠️ {s.from} غير متاح — التحويل لمزود آخر
                              </div>
                            );
                          }
                          if (s.kind === 'error') {
                            return (
                              <div key={sIdx} className="text-[10px] text-red-400 px-3">
                                ❌ {s.message}
                              </div>
                            );
                          }
                          if (s.kind === 'start') {
                            return (
                              <div key={sIdx} className="text-[10px] text-cyan-400 px-3">
                                {s.message}
                              </div>
                            );
                          }
                          return null;
                        })}
                        {m.agent_streaming && (
                          <div className="text-[10px] text-zinc-500 px-3 italic flex items-center gap-2">
                            <span className="inline-block w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                            يعمل...
                          </div>
                        )}
                      </div>
                    )}

                    {/* Design variants — live HTML mini previews user can pick */}
                    {m.role === 'assistant' && m.design_variants && m.design_variants.length > 1 && (
                      <div className="mt-3 grid sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid={`variants-${i}`}>
                        {m.design_variants.map((v, idx) => {
                          const isChosen = project.approved_design_id === v.id;
                          return (
                            <div
                              key={v.id}
                              className={`rounded-xl overflow-hidden border-2 ${isChosen ? 'border-emerald-400 ring-2 ring-emerald-400/40' : 'border-white/15 hover:border-emerald-400/60'} transition-all bg-zinc-950 group`}
                              data-testid={`variant-card-${v.id}`}
                            >
                              <button
                                type="button"
                                onClick={() => setLightboxAsset({ id: v.id, type: 'تصميم', prompt: v.label, image_url: '', html: v.html })}
                                className="relative block w-full aspect-[4/3] overflow-hidden bg-white"
                                aria-label="تكبير التصميم"
                                data-testid={`zoom-variant-${v.id}`}
                              >
                                <iframe
                                  title={v.label}
                                  srcDoc={v.html}
                                  sandbox=""
                                  scrolling="no"
                                  className="absolute top-0 left-0 pointer-events-none"
                                  style={{
                                    width: '320%',
                                    height: '320%',
                                    transform: 'scale(0.3125)',
                                    transformOrigin: '0 0',
                                    border: 'none',
                                  }}
                                />
                                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent group-hover:from-black/30 transition-all" />
                                <div className="absolute bottom-2 right-2 px-2 py-1 rounded-md bg-black/60 backdrop-blur text-[10px] text-white font-bold flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <ZoomIn className="w-3 h-3" /> اضغط للتكبير
                                </div>
                                <div className="absolute top-2 right-2">
                                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-black shadow-lg ${isChosen ? 'bg-emerald-500 text-black' : 'bg-black/70 text-white'}`}>
                                    {idx + 1}
                                  </span>
                                </div>
                              </button>
                              <div className="p-2.5 flex items-center justify-between gap-2 bg-zinc-900">
                                <span className="text-xs text-zinc-200 font-bold truncate">{v.label}</span>
                                {isChosen ? (
                                  <span className="text-[10px] text-emerald-300 font-bold whitespace-nowrap">✓ مُعتمد</span>
                                ) : (
                                  <button
                                    type="button"
                                    onClick={() => approveDesign(v.id)}
                                    data-testid={`approve-variant-${v.id}`}
                                    className="px-2.5 py-1 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-black text-[10px] font-black shrink-0"
                                  >
                                    اعتمد
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

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
              {!loading && lastTask && (lastTask.label || lastTask.model) && (
                <div className="flex justify-start" data-testid="last-task-badge">
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900/60 border border-cyan-400/20 text-[10px] text-zinc-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    <span className="text-cyan-200">{lastTask.label}</span>
                    {lastTask.model && (
                      <span className="text-zinc-500 font-mono" dir="ltr">· {lastTask.model.split('+')[0].trim()}</span>
                    )}
                  </div>
                </div>
              )}
              {loading && (
                <div className="flex justify-start" data-testid="thinking-bubble">
                  <div className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 bg-zinc-900/60 border border-cyan-400/20">
                    <span className="flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" style={{ animationDelay: '0.4s' }} />
                    </span>
                    <span className="text-[11px] text-zinc-400">يبدأ الذكاء العمل...</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'live' && (
            <div className="flex-1 overflow-hidden bg-black/40 flex flex-col" data-testid="tab-content-live">
              <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between gap-3">
                <h2 className="text-sm font-bold text-cyan-300 flex items-center gap-2">
                  <Eye className="w-4 h-4" /> <span>المعاينة الحية</span>
                </h2>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={refreshProject}
                    data-testid="refresh-preview-btn"
                    title="جلب آخر إصدار من الذكاء وإعادة تحميل المعاينة"
                    className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-emerald-500/20 border border-emerald-400/30 text-emerald-200 text-xs font-bold flex items-center gap-1.5"
                  >
                    <ArrowRight className="w-3.5 h-3.5 rotate-180" />
                    <span>تحديث</span>
                  </button>
                  {project.current_html && (
                    <>
                      <button
                        type="button"
                        onClick={() => {
                          const blob = new Blob([project.current_html], { type: 'text/html;charset=utf-8' });
                          const url = URL.createObjectURL(blob);
                          window.open(url, '_blank', 'noopener,noreferrer');
                          setTimeout(() => URL.revokeObjectURL(url), 60_000);
                        }}
                        data-testid="open-in-new-tab-btn"
                        title="افتح كصفحة ويب حقيقية في تبويب جديد"
                        className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-cyan-500/20"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        <span>افتح بصفحة كاملة</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const blob = new Blob([project.current_html], { type: 'text/html;charset=utf-8' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `${(project.name || 'site').replace(/[^a-zA-Z0-9-_\u0600-\u06FF]/g, '_')}.html`;
                          document.body.appendChild(a);
                          a.click();
                          document.body.removeChild(a);
                          setTimeout(() => URL.revokeObjectURL(url), 1000);
                        }}
                        data-testid="download-html-btn"
                        title="تنزيل HTML"
                        className="px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-200 text-xs font-bold flex items-center gap-1.5"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}
                  <div className="flex items-center gap-1 border border-white/10 rounded-lg p-0.5 bg-black/20">
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
              </div>
              <div className="flex-1 overflow-auto p-4 flex items-start justify-center flex-col gap-3">
                {project.code_unlocked && (
                  <CodeActions
                    project={project}
                    projectId={projectId}
                    onOpenConnections={() => setConnectionsOpen(true)}
                  />
                )}
                {project.current_html ? (
                  <iframe
                    key={previewKey}
                    title="Live Preview"
                    data-testid="preview-iframe"
                    srcDoc={project.current_html}
                    sandbox="allow-scripts allow-same-origin"
                    className={`bg-white rounded-lg shadow-2xl border border-white/10 transition-all ${previewMode === 'mobile' ? 'w-[375px] self-center' : 'w-full max-w-5xl self-center'}`}
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
      <SnapshotsModal
        open={snapshotsOpen}
        projectId={projectId}
        onClose={() => setSnapshotsOpen(false)}
        onRestored={refreshProject}
      />
      <FinalizeModal
        open={finalizeOpen}
        projectId={projectId}
        projectName={project.name}
        onClose={() => setFinalizeOpen(false)}
        onConverted={(appId) => {
          setFinalizeOpen(false);
          toast.success('🚀 جاري فتح محوّل التطبيق...');
          navigate(`/apps/convert/${appId}`);
        }}
        onUnlocked={async () => {
          // Refresh project to pick up code_unlocked flag
          const token = localStorage.getItem('token');
          const pr = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
          if (pr.ok) setProject(await pr.json());
          setFinalizeOpen(false);
          setConnectionsOpen(true);
        }}
      />
      <ConnectionsPanel
        open={connectionsOpen}
        projectId={projectId}
        onClose={() => setConnectionsOpen(false)}
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
