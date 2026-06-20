import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import VideoStudioPreview from './VideoStudioPreview';
import VideoPhaseTracker, { VIDEO_PHASES } from '../components/VideoPhaseTracker';
import ZCrownSpinner from '../components/ZCrownSpinner';
import ZenrexBrand from '../components/ZenrexBrand';
import ConnectionHelpModal from '../components/ConnectionHelpModal';
import StorageIndicator from '../components/StorageIndicator';
import UsageIndicator from '../components/UsageIndicator';
import CookiesManager from '../components/CookiesManager';
import CreditsBlockedBanner from '../components/CreditsBlockedBanner';
import useCreditsGuard, { notifyCreditsChanged } from '../hooks/useCreditsGuard';
import {
  Globe, Send, Loader2, Sparkles, Eye, ArrowRight, ArrowLeft,
  CheckCircle2, Check, Image as ImageIcon, FolderOpen, Code,
  Monitor, Smartphone, Trash2, MessageSquare, Paperclip, X,
  ZoomIn, Reply, Download, ExternalLink, Rocket, Smartphone as Phone,
  Crown, Github, Globe2, Cloud, Link2, Copy, FileText, Plug, Mic,
  History, RotateCcw, Clock, HelpCircle, AlertCircle, ChevronLeft,
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
// Quick Edits Box — appears in sidebar; sends inline correction
// requests to the AI without showing code. Designed so a non-tech
// user can say "اجعل الزر أكبر" and the AI patches HTML in place.
// ─────────────────────────────────────────────────────────────
function QuickEditsBox({ projectId, onApplied, token, api }) {
  const [val, setVal] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    const txt = val.trim();
    if (!txt) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('message', `⚡ تعديل سريع: ${txt}`);
      const r = await fetch(`${api}/api/freebuild-chat/project/${projectId}/chat`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      const data = await r.json().catch(() => ({}));
      if (r.ok) {
        toast.success('✨ تم تطبيق التعديل في المعاينة');
        setVal('');
        if (onApplied) onApplied(data);
      } else {
        toast.error(data.detail || 'فشل التعديل');
      }
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };
  const quickHints = ['اجعل اللون الأساسي ذهبي', 'كبّر الزر الرئيسي', 'بدّل صورة الـhero', 'أضف قسم آراء العملاء'];
  return (
    <div className="mt-4 rounded-xl border border-violet-500/30 bg-gradient-to-b from-violet-500/10 to-zinc-900/40 p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-6 h-6 rounded-md bg-violet-500/25 flex items-center justify-center text-[14px]">⚡</span>
        <h4 className="text-[12px] font-black text-violet-200">تعديلات سريعة</h4>
      </div>
      <p className="text-[10px] text-violet-200/60 leading-relaxed mb-2">
        اكتب وش تبي تغيّر، الذكاء يعدّله فوراً في المعاينة بدون كود
      </p>
      <textarea
        value={val}
        onChange={(e) => setVal(e.target.value)}
        rows={2}
        placeholder="مثال: غيّر اللون الأساسي إلى ذهبي..."
        data-testid="quick-edit-input"
        className="w-full bg-black/40 border border-white/15 rounded-lg px-2 py-1.5 text-[11px] outline-none focus:border-violet-400 resize-none text-white"
      />
      <div className="flex flex-wrap gap-1 mt-1.5">
        {quickHints.map((h, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setVal(h)}
            className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 hover:bg-violet-500/20 border border-white/10 text-zinc-400 hover:text-violet-200 transition"
          >
            {h}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={submit}
        disabled={!val.trim() || busy}
        data-testid="quick-edit-submit"
        className="mt-2 w-full bg-violet-500 hover:bg-violet-400 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-[11px] font-black rounded-lg py-1.5 transition flex items-center justify-center gap-1.5"
      >
        {busy ? <><Loader2 className="w-3 h-3 animate-spin" /><span>جاري التطبيق...</span></> : <><Sparkles className="w-3 h-3" /><span>طبّق التعديل</span></>}
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// STEP 1: Project Entry — REDESIGNED 2026-06-19 v2 (cache-bust ${Date.now()})
// Build timestamp: 2026-06-19T01:35:00Z — force unique webpack contenthash
// ─────────────────────────────────────────────────────────────
const _BUILD_VERSION = '2026-06-19-redesign-v2';
const QUICK_EXAMPLES = [
  { icon: '🌹', title: 'متجر عطور فاخر',     hint: 'متجر إلكتروني بهوية راقية، صفحة كل عطر، سلة شراء، Stripe' },
  { icon: '☕',  title: 'موقع مطعم/كافيه',    hint: 'منيو تفاعلي، صور أطباق، حجز طاولة، خريطة' },
  { icon: '💼', title: 'بورتفوليو شخصي',     hint: 'سيرة، مشاريع، شهادات، فورم تواصل' },
  { icon: '🏥', title: 'عيادة طبية',         hint: 'الأطباء، حجز موعد، خدمات، أسئلة شائعة' },
  { icon: '🏠', title: 'موقع عقارات',         hint: 'إعلانات شقق، فلاتر، خريطة، حاسبة قسط' },
  { icon: '🎓', title: 'منصة تعليمية',        hint: 'كورسات، شهادات، اختبارات، اشتراكات' },
  { icon: '📰', title: 'مدوّنة احترافية',     hint: 'مقالات، تصنيفات، تعليقات، نشرة بريدية' },
  { icon: '🎨', title: 'وكالة إبداعية',       hint: 'أعمال، عملاء، خدمات، طلب عرض سعر' },
];

function ProjectEntry({ onCreated, onOpenMyProjects }) {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [idea, setIdea] = useState('');
  const [loading, setLoading] = useState(false);
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const r = await fetch(`${API}/api/freebuild-chat/projects`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (r.ok) {
          const data = await r.json();
          const items = (data.items || data.projects || []).slice(0, 4);
          setRecent(items);
        }
      } catch (_) { /* silent */ }
    })();
  }, []);

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

  const applyExample = (ex) => {
    setName(ex.title);
    setIdea(ex.hint);
    setTimeout(() => {
      const el = document.querySelector('[data-testid="project-name-input"]');
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el?.focus();
    }, 100);
  };

  const fmtDate = (s) => {
    if (!s) return '';
    try {
      const d = new Date(s);
      const diff = (Date.now() - d.getTime()) / 1000;
      if (diff < 3600) return `قبل ${Math.max(1, Math.round(diff/60))} د`;
      if (diff < 86400) return `قبل ${Math.round(diff/3600)} س`;
      if (diff < 604800) return `قبل ${Math.round(diff/86400)} يوم`;
      return d.toLocaleDateString('ar-SA');
    } catch (_) { return ''; }
  };

  return (
    <div dir="rtl" lang="ar" translate="no" className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-emerald-950/20 text-white">
      {/* Top nav */}
      <div className="sticky top-0 z-20 backdrop-blur-md bg-zinc-950/60 border-b border-white/5">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 sm:gap-3">
            <a href="/" className="hover:opacity-90" aria-label="Zenrex"><ZenrexBrand size={26} /></a>
            <span className="hidden sm:inline text-zinc-700">•</span>
            <a
              href="/freebuild/projects"
              data-testid="open-my-projects"
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all text-xs sm:text-sm font-medium"
            >
              <FolderOpen className="w-4 h-4" />
              <span className="hidden sm:inline">مشاريعي قيد الإنشاء</span>
              <span className="sm:hidden">مشاريعي</span>
            </a>
          </div>
          <div className="flex items-center gap-2">
            <StorageIndicator compact />
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              data-testid="back-to-dashboard"
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all text-xs sm:text-sm font-medium"
            >
              <ArrowRight className="w-4 h-4" />
              <span className="hidden sm:inline">لوحة التحكم</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
        {/* Hero */}
        <div className="text-center mb-8 sm:mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-400/30 text-emerald-300 text-xs font-bold mb-5">
            <Sparkles className="w-3.5 h-3.5" />
            <span>إنشاء حر بالكامل — بدون قوالب، الذكاء يصمم معك</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-black mb-3 leading-tight">
            <span className="bg-gradient-to-l from-emerald-300 via-emerald-400 to-teal-400 bg-clip-text text-transparent">
              ابني موقعك من الصفر
            </span>
            <span className="block text-xl sm:text-2xl text-zinc-300 font-bold mt-2">
              بمحادثة عربية بسيطة
            </span>
          </h1>
          <p className="text-zinc-400 text-sm sm:text-base max-w-2xl mx-auto">
            اكتب فكرتك بكلامك العادي. الذكاء يسمعك، يسأل اللي يحتاجه، يصمم، يولّد الصور والشعار، وينشر الموقع.
          </p>
        </div>

        {/* Main two-column on desktop */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left: Form */}
          <div className="lg:col-span-3 space-y-4">
            <div className="bg-gradient-to-br from-zinc-900/80 to-zinc-900/40 backdrop-blur border border-white/10 rounded-2xl p-5 sm:p-6 shadow-2xl shadow-emerald-500/5">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                  <Globe className="w-6 h-6 text-black" />
                </div>
                <div>
                  <h2 className="text-lg sm:text-xl font-black">ابدأ مشروعك</h2>
                  <p className="text-xs text-zinc-500">يكفي اسم وفكرة بسيطة — لا تحتاج تختار قالب</p>
                </div>
              </div>

              <label className="block text-xs font-bold text-zinc-400 mb-1.5">اسم المشروع *</label>
              <input
                type="text"
                placeholder="مثال: موقع عطر فاخر"
                value={name}
                onChange={(e) => setName(e.target.value)}
                data-testid="project-name-input"
                className="w-full bg-black/50 border border-white/15 rounded-xl px-4 py-3 mb-4 outline-none focus:border-emerald-400 transition-colors"
              />

              <label className="block text-xs font-bold text-zinc-400 mb-1.5">صف فكرتك (اختياري)</label>
              <textarea
                placeholder="مثال: متجر عطور فاخر للنساء، ألوان وردي وذهبي، خط أنيق، صفحة لكل عطر..."
                value={idea}
                onChange={(e) => setIdea(e.target.value)}
                rows={4}
                data-testid="project-desc-input"
                className="w-full bg-black/50 border border-white/15 rounded-xl px-4 py-3 outline-none focus:border-emerald-400 resize-none transition-colors"
              />

              <button
                type="button"
                onClick={create}
                disabled={!name.trim() || loading}
                data-testid="create-project-btn"
                className="mt-4 w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 disabled:from-zinc-700 disabled:to-zinc-800 disabled:cursor-not-allowed text-black font-black rounded-xl py-3.5 transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/40 active:scale-[.98]"
              >
                {loading ? (
                  <><Loader2 className="w-5 h-5 animate-spin" /><span>جاري الإنشاء...</span></>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    <span>ابدأ المحادثة</span>
                    <ArrowLeft className="w-5 h-5" />
                  </>
                )}
              </button>

              <p className="text-xs text-zinc-500 mt-3 text-center">
                💡 لما تضغط الزر، يفتح الشات الذكي ويبدأ يسألك خطوة بخطوة
              </p>

              <a
                href="/native/new"
                data-testid="native-app-cta"
                className="mt-4 w-full inline-flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600/20 via-pink-600/20 to-amber-500/20 hover:from-purple-500/30 hover:via-pink-500/30 hover:to-amber-500/30 border border-purple-400/30 rounded-xl py-3 transition-all"
              >
                <span className="text-purple-300">📱</span>
                <span className="text-sm font-bold text-zinc-100">أو ابني تطبيق جوال من الصفر (PWA)</span>
                <ArrowLeft className="w-4 h-4 text-zinc-400" />
              </a>
            </div>

            {recent.length > 0 && (
              <div className="bg-zinc-900/40 border border-white/10 rounded-2xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-bold text-zinc-300 flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    <span>تابع مشروعك السابق</span>
                  </h3>
                  <button
                    onClick={onOpenMyProjects}
                    className="text-xs text-emerald-400 hover:text-emerald-300"
                  >
                    عرض الكل ←
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {recent.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => onCreated(p.id)}
                      className="text-right p-3 rounded-xl bg-black/30 hover:bg-emerald-500/10 border border-white/5 hover:border-emerald-400/30 transition-all group"
                    >
                      <div className="text-sm font-bold truncate group-hover:text-emerald-300">{p.name || 'مشروع بدون اسم'}</div>
                      <div className="text-[10px] text-zinc-500 mt-1">{fmtDate(p.updated_at || p.created_at)}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right: Quick examples */}
          <div className="lg:col-span-2">
            <div className="bg-zinc-900/30 border border-white/10 rounded-2xl p-5 lg:sticky lg:top-20">
              <h3 className="text-sm font-bold text-zinc-300 mb-1 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span>أفكار جاهزة — اضغط للاستلهام</span>
              </h3>
              <p className="text-xs text-zinc-500 mb-4">اختر واحدة لتعبئة الحقول، عدّل عليها كيف ما تبي</p>
              <div className="grid grid-cols-2 gap-2">
                {QUICK_EXAMPLES.map((ex, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => applyExample(ex)}
                    data-testid={`example-tile-${i}`}
                    className="text-right p-3 rounded-xl bg-black/40 hover:bg-emerald-500/10 border border-white/5 hover:border-emerald-400/40 transition-all group active:scale-[.97]"
                  >
                    <div className="text-2xl mb-1">{ex.icon}</div>
                    <div className="text-xs font-bold leading-tight group-hover:text-emerald-300">{ex.title}</div>
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-zinc-600 mt-4 text-center">
                ✦ الذكاء يصمم لك تصميماً فريداً لكل فكرة، ليس قالباً جاهزاً
              </p>
            </div>
          </div>
        </div>

        {/* Bottom features strip */}
        <div className="mt-10 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { i: '🎨', t: 'تصميم فريد', s: 'بدون قوالب' },
            { i: '🤖', t: 'شات ذكي', s: 'يسألك ويصمم' },
            { i: '🖼️', t: 'صور وشعار', s: 'AI تلقائي' },
            { i: '🚀', t: 'نشر فوري', s: 'دومين خاص' },
          ].map((f, i) => (
            <div key={i} className="bg-zinc-900/30 border border-white/5 rounded-xl p-3 text-center">
              <div className="text-2xl mb-1">{f.i}</div>
              <div className="text-xs font-bold">{f.t}</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">{f.s}</div>
            </div>
          ))}
        </div>
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
/**
 * Smart image component for chat markdown.
 *
 * Why this exists: AI tools return image URLs in many shapes — absolute https,
 * relative `/uploads/...`, raw filesystem paths, transient pre-signed URLs that
 * sometimes return 404. The default ReactMarkdown `<img>` renders a broken
 * ❓ placeholder, which looked horrendous in the storyboard.
 *
 * We now: resolve relative URLs against the API base, lazy-load, show a clean
 * Arabic shimmer while loading, and on error replace with a gentle retry card
 * instead of a broken-icon. We also render quick **Approve / Edit / Regenerate**
 * action chips beneath each image so the user can drive the workflow without
 * typing — exactly what the user asked for ("اعتماد / تغيير / تعديل").
 */
function MarkdownImage({ src, alt, title }) {
  const [loaded, setLoaded] = useState(false);
  const [errored, setErrored] = useState(false);
  if (!src) return null;
  const url = src.startsWith('http') ? src : (src.startsWith('/') ? `${API}${src}` : src);

  const sendChatLine = (text) => {
    // Bubble up a "synthetic user message" so the AI knows the action.
    try {
      const evt = new CustomEvent('zenrex:option-pick', { detail: { text } });
      window.dispatchEvent(evt);
    } catch { /* ignore */ }
  };

  if (errored) {
    return (
      <div className="my-2 inline-block rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200 max-w-xs">
        <div className="font-bold mb-0.5">⚠️ ما قدرت أحمّل الصورة</div>
        <div className="text-zinc-400">{alt || 'reference'}</div>
        <button
          type="button"
          onClick={() => { setErrored(false); setLoaded(false); }}
          className="mt-1 px-2 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 text-[10px]"
        >إعادة المحاولة</button>
      </div>
    );
  }

  return (
    <span className="block my-2.5">
      <span className="block relative rounded-xl overflow-hidden border border-white/10 bg-zinc-900/60">
        {!loaded && (
          <span className="block absolute inset-0 bg-gradient-to-br from-zinc-800 to-zinc-900 animate-pulse" />
        )}
        <img
          src={url}
          alt={alt || ''}
          title={title || alt || ''}
          loading="lazy"
          onLoad={() => setLoaded(true)}
          onError={() => setErrored(true)}
          className={`max-w-full h-auto block transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'}`}
        />
      </span>
      {(alt || title) && (
        <span className="block text-[11px] text-zinc-400 mt-1 px-1">{alt || title}</span>
      )}
      <span className="flex gap-1.5 mt-1.5 flex-wrap">
        <button
          type="button"
          onClick={() => sendChatLine(`✓ اعتمد هذي الصورة: ${alt || 'الصورة المعروضة'}`)}
          className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-500/20 hover:bg-emerald-500/35 text-emerald-200 border border-emerald-500/40 transition"
        >✓ اعتماد</button>
        <button
          type="button"
          onClick={() => sendChatLine(`🔄 ولّد لي صورة بديلة لـ: ${alt || 'الصورة المعروضة'}`)}
          className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-cyan-500/20 hover:bg-cyan-500/35 text-cyan-200 border border-cyan-500/40 transition"
        >🔄 تغيير</button>
        <button
          type="button"
          onClick={() => sendChatLine(`✏️ عدّل على هذي الصورة: ${alt || 'الصورة'} — أبي تغيّر `)}
          className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-500/20 hover:bg-amber-500/35 text-amber-200 border border-amber-500/40 transition"
        >✏️ تعديل</button>
      </span>
    </span>
  );
}

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
  img: ({ node, src, alt, title }) => <MarkdownImage src={src} alt={alt} title={title} />,
};

/**
 * MarkdownText is `React.memo`'d so a re-render of the parent chat list doesn't
 * re-parse every previous message. During SSE streaming, only the CURRENTLY
 * growing message has a new `children` string; older bubbles short-circuit.
 *
 * This removed the visible "flicker / ripple" the user reported: as the agent
 * streamed text deltas, ReactMarkdown was re-parsing every assistant message in
 * the list on each delta, briefly blanking glyphs as virtual DOM diffed.
 */
const MarkdownText = React.memo(function MarkdownText({ children }) {
  return (
    <div className="prose prose-invert max-w-none" dir="rtl">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
        {children || ''}
      </ReactMarkdown>
    </div>
  );
});

// ─────────────────────────────────────────────────────────────
// MESSAGE ACTIONS — clean copy/quote toolbar shown under finalized
// assistant messages. Designed to be subtle ("بلا زحمة"): low-opacity
// pills that brighten on hover. Three actions: copy raw text, quote
// the message into the input box, share via Web Share API (mobile).
// ─────────────────────────────────────────────────────────────
function MessageActions({ content, onQuote }) {
  const [copied, setCopied] = useState(false);
  const text = String(content || '');

  const doCopy = async () => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement('textarea');
        ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta); ta.focus(); ta.select();
        document.execCommand('copy'); document.body.removeChild(ta);
      }
      setCopied(true);
      toast.success('تم النسخ ✨');
      setTimeout(() => setCopied(false), 1800);
    } catch {
      toast.error('ما قدرت أنسخ — جرّب يدوي');
    }
  };

  const doShare = async () => {
    if (navigator.share) {
      try { await navigator.share({ text, title: 'Zenrex AI' }); } catch { /* user cancelled */ }
    } else {
      const url = `https://wa.me/?text=${encodeURIComponent(text)}`;
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  if (!text.trim()) return null;
  return (
    <div className="mt-2 pt-2 border-t border-white/5 flex items-center gap-1 opacity-50 hover:opacity-100 transition-opacity" data-testid="message-actions">
      <button
        type="button"
        onClick={doCopy}
        data-testid="msg-action-copy"
        className="text-[11px] text-zinc-400 hover:text-emerald-300 px-2 py-1 rounded-md hover:bg-emerald-500/10 flex items-center gap-1 transition-colors"
        title="انسخ النص"
      >
        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
        <span>{copied ? 'انتسخ' : 'نسخ'}</span>
      </button>
      <button
        type="button"
        onClick={() => onQuote && onQuote(text)}
        data-testid="msg-action-quote"
        className="text-[11px] text-zinc-400 hover:text-cyan-300 px-2 py-1 rounded-md hover:bg-cyan-500/10 flex items-center gap-1 transition-colors"
        title="اقتبس هذي الرسالة في إجابتك"
      >
        <Reply className="w-3.5 h-3.5" />
        <span>اقتباس</span>
      </button>
      <button
        type="button"
        onClick={doShare}
        data-testid="msg-action-share"
        className="text-[11px] text-zinc-400 hover:text-violet-300 px-2 py-1 rounded-md hover:bg-violet-500/10 flex items-center gap-1 transition-colors"
        title="أرسل النص (واتساب/مشاركة)"
      >
        <ExternalLink className="w-3.5 h-3.5" />
        <span>مشاركة</span>
      </button>
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
function InlineVideoBubble({ url, poster_url, caption, duration_sec, model, scene_id, cost_usd, idx }) {
  const src = url && url.startsWith('http') ? url : `${API}${url || ''}`;
  return (
    <div
      className="bg-gradient-to-br from-fuchsia-500/15 to-violet-500/15 border border-fuchsia-500/30 rounded-xl p-2.5"
      data-testid={`msg-inline-video-${idx}`}
    >
      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
        <span className="text-[10px] font-bold text-fuchsia-200 uppercase tracking-wide">🎬 فيديو</span>
        {scene_id && <span className="text-[10px] bg-black/40 px-1.5 py-0.5 rounded">{scene_id}</span>}
        {model && <span className="text-[10px] bg-black/40 px-1.5 py-0.5 rounded text-fuchsia-300">{model}</span>}
        {duration_sec && <span className="text-[10px] text-zinc-400 mr-auto">{Number(duration_sec).toFixed(1)}s</span>}
      </div>
      <video
        src={src}
        poster={poster_url && (poster_url.startsWith('http') ? poster_url : `${API}${poster_url}`)}
        controls
        playsInline
        preload="metadata"
        className="w-full rounded-lg bg-black"
        data-testid={`msg-inline-video-player-${idx}`}
      />
      {caption && <p className="text-[11px] text-zinc-200 mt-1.5 leading-snug">{caption}</p>}
      <div className="flex items-center gap-2 mt-1 text-[10px] flex-wrap">
        {cost_usd !== undefined && cost_usd !== null && (
          <span className="text-amber-400">تكلفة: ${Number(cost_usd).toFixed(3)}</span>
        )}
        <a
          href={src}
          download
          target="_blank"
          rel="noreferrer"
          className="ml-auto text-fuchsia-300 hover:text-fuchsia-200 underline"
          data-testid={`msg-inline-video-download-${idx}`}
        >تحميل</a>
      </div>
    </div>
  );
}


function InlineAudioBubble({ url, caption, duration_sec, voice, kind, cost_estimate, idx }) {
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [actualDur, setActualDur] = useState(duration_sec || 0);

  const toggle = () => {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
    } else {
      el.play().catch(() => toast.error('ما قدرت أشغّل الصوت — تأكد من السماعة'));
    }
  };
  const onLoaded = () => {
    if (audioRef.current?.duration && !isNaN(audioRef.current.duration)) {
      setActualDur(audioRef.current.duration);
    }
  };
  const onTime = () => {
    if (!audioRef.current || !audioRef.current.duration) return;
    setProgress((audioRef.current.currentTime / audioRef.current.duration) * 100);
  };
  const onEnd = () => { setPlaying(false); setProgress(0); };
  const seek = (e) => {
    const el = audioRef.current;
    if (!el || !el.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    el.currentTime = (x / rect.width) * el.duration;
  };
  const fmt = (s) => {
    if (!s || isNaN(s)) return '0:00';
    const m = Math.floor(s / 60); const sec = Math.floor(s % 60);
    return `${m}:${String(sec).padStart(2, '0')}`;
  };
  const kindStyle = {
    sample: { bg: 'from-cyan-500/15 to-blue-500/15', border: 'border-cyan-500/30', label: '🎧 عينة' },
    full_scenario: { bg: 'from-violet-500/15 to-fuchsia-500/15', border: 'border-violet-500/30', label: '🎬 السيناريو الكامل' },
    voiceover: { bg: 'from-emerald-500/15 to-teal-500/15', border: 'border-emerald-500/30', label: '🎙️ التعليق الصوتي' },
  }[kind] || { bg: 'from-zinc-700/40 to-zinc-800/40', border: 'border-white/10', label: '🔊 صوت' };
  const src = url && url.startsWith('http') ? url : `${API}${url || ''}`;

  return (
    <div
      className={`bg-gradient-to-br ${kindStyle.bg} border ${kindStyle.border} rounded-xl p-3 flex items-center gap-3`}
      data-testid={`msg-inline-audio-${idx}`}
    >
      <audio
        ref={audioRef}
        src={src}
        onLoadedMetadata={onLoaded}
        onTimeUpdate={onTime}
        onEnded={onEnd}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        preload="metadata"
      />
      <button
        type="button"
        onClick={toggle}
        data-testid={`msg-inline-audio-play-${idx}`}
        className="w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white flex-shrink-0 transition"
        aria-label={playing ? 'إيقاف' : 'تشغيل'}
      >
        {playing
          ? <span className="block w-3 h-3 border-l-[3px] border-r-[3px] border-white" />
          : <span className="block w-0 h-0 border-y-[6px] border-y-transparent border-l-[10px] border-l-white ml-1" />
        }
      </button>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="text-[10px] font-bold text-zinc-300 uppercase tracking-wide">{kindStyle.label}</span>
          <span className="text-[10px] text-zinc-400 tabular-nums">{fmt(actualDur)}</span>
        </div>
        <div
          onClick={seek}
          className="h-1.5 bg-white/10 rounded-full overflow-hidden cursor-pointer"
        >
          <div className="h-full bg-white/70 transition-all" style={{ width: `${progress}%` }} />
        </div>
        {caption && <p className="text-[11px] text-zinc-200 mt-1.5 leading-snug">{caption}</p>}
        <div className="flex items-center gap-2 mt-1 text-[10px] text-zinc-400 flex-wrap">
          {voice && <span className="bg-black/30 px-1.5 py-0.5 rounded">{voice}</span>}
          {cost_estimate && <span className="text-amber-400">{cost_estimate}</span>}
        </div>
      </div>
    </div>
  );
}



function OptionsPicker({ messageIdx, options, savedAnswer, onConfirm }) {
  const [selected, setSelected] = useState([]);
  const [comment, setComment] = useState('');
  const [confirming, setConfirming] = useState(false);

  // Normalize each option: accept plain string OR {label, emoji?, image_url?, description?}.
  const norm = (options || []).map((o) => {
    if (typeof o === 'string') return { label: o };
    if (o && typeof o === 'object') return {
      label: o.label || o.id || '',
      emoji: o.emoji || '',
      image_url: o.image_url || '',
      description: o.description || '',
    };
    return { label: String(o ?? '') };
  }).filter((o) => o.label);

  const hasImages = norm.some((o) => !!o.image_url);
  const hasDescriptions = norm.some((o) => !!o.description);
  const isRichLayout = hasImages || hasDescriptions;

  // If user already answered this question, show the answer locked
  if (savedAnswer) {
    const picks = savedAnswer.picks || [];
    return (
      <div className="mt-3 flex flex-wrap gap-1.5" data-testid={`options-locked-${messageIdx}`}>
        {norm.map((opt, i) => {
          const isPicked = picks.includes(opt.label);
          return (
            <span
              key={i}
              className={`px-3 py-1.5 rounded-full text-[11px] font-bold border ${
                isPicked
                  ? 'bg-emerald-500/30 border-emerald-400/60 text-emerald-100'
                  : 'bg-zinc-800/40 border-white/5 text-zinc-500 line-through opacity-60'
              }`}
            >
              {isPicked && '✓ '}{opt.emoji ? `${opt.emoji} ` : ''}{opt.label}
            </span>
          );
        })}
      </div>
    );
  }

  const toggle = (label) => {
    setSelected((prev) => prev.includes(label) ? prev.filter((x) => x !== label) : [...prev, label]);
  };

  /**
   * Detect "freeform" options like "غير ذلك — اكتب فكرتك". These are auto-submit:
   * the user shouldn't have to ALSO type a comment + press تأكيد. One click =
   * submission, then the AI takes over with a conversational follow-up like
   * "احكي لي فكرتك بكامل التفاصيل".
   */
  const isFreeformOption = (label = '') => {
    const s = String(label).toLowerCase();
    return s.includes('غير ذلك') || s.includes('اكتب فكرتك') ||
           s.includes('other') || s.includes('custom') || s.includes('free');
  };

  const submitImmediate = async (label) => {
    setConfirming(true);
    try {
      await onConfirm({ picks: [label], comment: '' });
    } finally {
      setConfirming(false);
    }
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

  // ─── Rich card layout (with images/descriptions) ───
  if (isRichLayout) {
    return (
      <div className="mt-3" data-testid={`options-${messageIdx}`}>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          {norm.map((opt, i) => {
            const isSelected = selected.includes(opt.label);
            return (
              <button
                key={i}
                type="button"
                onClick={() => isFreeformOption(opt.label) ? submitImmediate(opt.label) : toggle(opt.label)}
                disabled={confirming}
                data-testid={`option-${messageIdx}-${i}`}
                className={`group relative text-right rounded-xl overflow-hidden border transition-all duration-200 ${
                  isSelected
                    ? 'border-emerald-400 ring-2 ring-emerald-400/60 shadow-lg shadow-emerald-500/30 scale-[1.02]'
                    : 'border-white/10 hover:border-emerald-400/50 hover:scale-[1.01] bg-zinc-900/60'
                }`}
              >
                {opt.image_url ? (
                  <div className="relative aspect-video bg-zinc-900 overflow-hidden">
                    <img
                      src={opt.image_url}
                      alt={opt.label}
                      loading="lazy"
                      className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                      onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent" />
                    {opt.emoji && (
                      <div className="absolute top-1.5 right-1.5 text-lg drop-shadow-lg">{opt.emoji}</div>
                    )}
                    {isSelected && (
                      <div className="absolute top-1.5 left-1.5 w-6 h-6 rounded-full bg-emerald-500 text-black flex items-center justify-center shadow-lg">
                        <Check className="w-3.5 h-3.5" />
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="aspect-video bg-gradient-to-br from-zinc-800 to-zinc-900 flex items-center justify-center text-4xl">
                    {opt.emoji || '✨'}
                  </div>
                )}
                <div className="p-2">
                  <p className={`text-xs font-black ${isSelected ? 'text-emerald-300' : 'text-white'}`}>
                    {opt.label}
                  </p>
                  {opt.description && (
                    <p className="text-[10px] text-zinc-400 mt-0.5 line-clamp-2 leading-snug">
                      {opt.description}
                    </p>
                  )}
                </div>
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
            placeholder="اكتب تعليق أو اختيار آخر (اختياري)..."
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

  // ─── Simple chip/pill layout (no images) ───
  return (
    <div className="mt-3" data-testid={`options-${messageIdx}`}>
      <div className="flex flex-wrap gap-2">
        {norm.map((opt, i) => {
          const isSelected = selected.includes(opt.label);
          const accent = OPT_ACCENTS[i % OPT_ACCENTS.length];
          return (
            <button
              key={i}
              type="button"
              onClick={() => isFreeformOption(opt.label) ? submitImmediate(opt.label) : toggle(opt.label)}
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
                {isSelected ? <Check className="w-3 h-3" /> : (opt.emoji || (i + 1))}
              </span>
              <span>{opt.label}</span>
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
      toast.success('🚀 موقعك سينشر على Zenrex قريباً — جاري الإعداد');
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
  const [helpFor, setHelpFor] = useState(null); // providerId currently showing help modal

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
                      <h4 className="font-black text-sm flex items-center gap-1.5">
                        {p.title}
                        <button
                          type="button"
                          onClick={() => setHelpFor(p.id)}
                          data-testid={`conn-help-${p.id}`}
                          className="text-amber-300 hover:text-amber-200 inline-flex items-center"
                          title="كيف أحصل عليه؟"
                          aria-label={`دليل ${p.title}`}
                        >
                          <HelpCircle className="w-4 h-4" />
                        </button>
                      </h4>
                      <p className="text-[11px] text-zinc-300/70">{p.hint}</p>
                    </div>
                  </div>
                  {existing ? (
                    <div className="flex items-center gap-2 shrink-0" data-testid={`conn-status-${p.id}-connected`}>
                      <span className="px-2 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/50 text-emerald-200 text-[10px] font-bold flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        <Check className="w-3 h-3" />
                        مربوط · {existing.mask}
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
                    <span
                      data-testid={`conn-status-${p.id}-disconnected`}
                      className="px-2 py-1 rounded-full bg-red-500/15 border border-red-500/40 text-red-300 text-[10px] font-bold flex items-center gap-1"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                      <AlertCircle className="w-3 h-3" />
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
                      <button
                        type="button"
                        onClick={() => setHelpFor(p.id)}
                        data-testid={`conn-show-guide-${p.id}`}
                        className="inline-flex items-center gap-1.5 text-[11px] text-amber-300 hover:text-amber-200"
                      >
                        <HelpCircle className="w-3.5 h-3.5" />
                        <span>دليل خطوة بخطوة + صور</span>
                      </button>
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
      <ConnectionHelpModal
        open={!!helpFor}
        providerId={helpFor}
        onClose={() => setHelpFor(null)}
      />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// CODE ACTIONS PANEL (after code is unlocked)
// ─────────────────────────────────────────────────────────────
function CodeActions({ project, projectId, onOpenConnections }) {
  const [pushing, setPushing] = useState(false);
  const [repoName, setRepoName] = useState(() =>
    (project.name || 'zenrex-site')
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-')
      .slice(0, 40) || 'zenrex-site'
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
// Plan Task Card — beautiful animated checklist rendered when
// the AI calls `plan_task(title, steps)`. Each step fades in
// with a stagger, then animates to "in progress" → "done".
// Purely visual progress: shows the user a clear roadmap.
// ─────────────────────────────────────────────────────────────
function PlanTaskCard({ plan, updates }) {
  const steps = plan?.steps || [];
  const total = steps.length;
  const eta = plan?.estimated_minutes || 5;
  // Build a status map from REAL update_plan_step events (no more visual timer)
  const statusByIdx = {};
  (updates || []).forEach((u) => {
    statusByIdx[u.step_index] = { status: u.status, note: u.note };
  });
  const doneCount = Object.values(statusByIdx).filter((s) => s.status === 'done').length;
  const inProgressIdx = Object.entries(statusByIdx).find(([, s]) => s.status === 'in_progress')?.[0];

  return (
    <div
      className="my-2 rounded-2xl overflow-hidden border border-cyan-500/30 bg-gradient-to-br from-zinc-950 via-zinc-950 to-cyan-950/20 shadow-lg shadow-cyan-500/5"
      data-testid="plan-task-card"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-cyan-500/20 bg-cyan-500/5 flex items-center gap-3">
        <div className="text-xl">📋</div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-cyan-400/80 font-bold uppercase tracking-wider">خطة العمل</div>
          <div className="text-sm text-white font-semibold truncate" data-testid="plan-task-title">
            {plan?.title}
          </div>
        </div>
        <div className="text-[10px] text-zinc-400 bg-zinc-900/60 px-2 py-1 rounded-full border border-zinc-700/50 shrink-0">
          ⏱ ~{eta}د
        </div>
      </div>

      {/* Steps */}
      <div className="px-4 py-3 space-y-2">
        {steps.map((stepText, idx) => {
          const u = statusByIdx[idx];
          const status = u?.status || 'pending';
          const note = u?.note || '';
          const isFailed = status === 'failed';
          return (
            <div
              key={idx}
              className={`flex items-start gap-3 px-3 py-2 rounded-lg transition-all duration-500 ${
                status === 'done'
                  ? 'bg-emerald-500/10 border border-emerald-500/30'
                  : status === 'in_progress'
                  ? 'bg-cyan-500/10 border border-cyan-500/40 ring-1 ring-cyan-400/20'
                  : isFailed
                  ? 'bg-red-500/10 border border-red-500/40'
                  : 'bg-zinc-900/40 border border-zinc-800/60'
              }`}
              style={{ animation: `fadeInUp 400ms ease-out ${idx * 80}ms both` }}
              data-testid={`plan-step-${idx}`}
            >
              {/* Status icon */}
              <div className="mt-0.5 shrink-0">
                {status === 'done' && (
                  <div className="w-5 h-5 rounded-full bg-emerald-500/20 border border-emerald-400/60 flex items-center justify-center">
                    <svg className="w-3 h-3 text-emerald-300" viewBox="0 0 12 12" fill="none">
                      <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                )}
                {status === 'in_progress' && (
                  <div className="w-5 h-5 rounded-full bg-cyan-500/30 border border-cyan-300/80 flex items-center justify-center">
                    <div className="w-2 h-2 rounded-full bg-cyan-300 animate-pulse" />
                  </div>
                )}
                {isFailed && (
                  <div className="w-5 h-5 rounded-full bg-red-500/20 border border-red-400/60 flex items-center justify-center">
                    <span className="text-red-300 text-[10px] font-bold">✕</span>
                  </div>
                )}
                {status === 'pending' && (
                  <div className="w-5 h-5 rounded-full bg-zinc-800 border border-zinc-700" />
                )}
              </div>

              {/* Step number + text */}
              <div className="flex-1 min-w-0">
                <div className={`text-[11px] font-bold mb-0.5 ${
                  status === 'done' ? 'text-emerald-400/70' :
                  status === 'in_progress' ? 'text-cyan-300' :
                  isFailed ? 'text-red-400' :
                  'text-zinc-600'
                }`}>
                  {String(idx + 1).padStart(2, '0')}
                </div>
                <div className={`text-xs leading-snug ${
                  status === 'done' ? 'text-emerald-100/90 line-through decoration-emerald-500/40 decoration-1' :
                  status === 'in_progress' ? 'text-white' :
                  isFailed ? 'text-red-200' :
                  'text-zinc-500'
                }`}>
                  {stepText}
                </div>
                {note && (
                  <div className={`mt-1 text-[10px] ${isFailed ? 'text-red-300/80' : 'text-cyan-300/70'}`}>
                    💬 {note}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer progress bar */}
      <div className="px-4 pb-3">
        <div className="h-1 bg-zinc-900 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-700 ease-out"
            style={{ width: `${total > 0 ? (doneCount / total) * 100 : 0}%` }}
          />
        </div>
        <div className="mt-1.5 flex justify-between text-[10px] text-zinc-500">
          <span>
            {doneCount} / {total} خطوة
            {inProgressIdx !== undefined && <span className="text-cyan-400 mr-2">• #{Number(inProgressIdx) + 1} جارية</span>}
          </span>
          <span>{Math.round((doneCount / Math.max(total, 1)) * 100)}%</span>
        </div>
      </div>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────
// AuditReportCard — comprehensive multi-angle audit results.
// Rendered when the AI calls `audit_project`. Shows per-category
// scores + overall grade + expandable details per check.
// ─────────────────────────────────────────────────────────────
function AuditReportCard({ report }) {
  const [openCheck, setOpenCheck] = useState(null);
  const checks = report?.checks || {};
  const scores = report?.scores || {};
  const overall = report?.overall_score || 0;
  const grade = report?.grade || '';
  const elapsed = report?.elapsed_seconds || 0;
  const checkLabels = {
    html: { label: 'بنية HTML', icon: '📐' },
    js: { label: 'JavaScript', icon: '⚡' },
    visual: { label: 'الاختبار البصري الحي', icon: '👁️' },
    security: { label: 'الأمن', icon: '🛡️' },
    performance: { label: 'الأداء', icon: '🚀' },
    seo: { label: 'SEO', icon: '🔍' },
    accessibility: { label: 'الوصولية', icon: '♿' },
  };
  const scoreColor = (s) => {
    if (s === null || s === undefined) return 'text-zinc-500';
    if (s >= 90) return 'text-emerald-400';
    if (s >= 75) return 'text-cyan-400';
    if (s >= 60) return 'text-amber-400';
    if (s >= 40) return 'text-orange-400';
    return 'text-red-400';
  };
  const overallColor = scoreColor(overall);

  return (
    <div
      className="my-2 rounded-2xl overflow-hidden border border-purple-500/30 bg-gradient-to-br from-zinc-950 via-zinc-950 to-purple-950/20 shadow-lg shadow-purple-500/5"
      data-testid="audit-report-card"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-purple-500/20 bg-purple-500/5 flex items-center gap-3">
        <div className="text-xl">🔍</div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-purple-400/80 font-bold uppercase tracking-wider">تقرير التدقيق الشامل</div>
          <div className="text-sm text-white font-semibold" data-testid="audit-grade">{grade}</div>
        </div>
        <div className={`text-2xl font-black ${overallColor}`} data-testid="audit-overall-score">
          {overall}<span className="text-sm text-zinc-500">/100</span>
        </div>
      </div>

      {/* Per-category scores */}
      <div className="px-4 py-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
        {Object.entries(scores).map(([key, score]) => {
          const lbl = checkLabels[key] || { label: key, icon: '•' };
          const isOpen = openCheck === key;
          const check = checks[key] || {};
          const isSkipped = check.skipped;
          return (
            <div
              key={key}
              className="rounded-lg border border-zinc-800 bg-zinc-900/40 overflow-hidden transition-all"
              data-testid={`audit-check-${key}`}
            >
              <button
                onClick={() => setOpenCheck(isOpen ? null : key)}
                className="w-full flex items-center gap-3 px-3 py-2 hover:bg-zinc-900/60 transition"
              >
                <span className="text-lg">{lbl.icon}</span>
                <span className="text-xs text-white font-semibold flex-1 text-right">{lbl.label}</span>
                {isSkipped ? (
                  <span className="text-[10px] text-zinc-500">— تخطّى</span>
                ) : (
                  <span className={`text-sm font-bold ${scoreColor(score)}`}>
                    {score !== null && score !== undefined ? `${score}` : '—'}
                  </span>
                )}
                <svg className={`w-3 h-3 text-zinc-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} viewBox="0 0 12 12" fill="none">
                  <path d="M3 5L6 8L9 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </button>
              {isOpen && (
                <div className="px-3 pb-3 pt-1 text-[11px] text-zinc-300 leading-relaxed border-t border-zinc-800 max-h-60 overflow-y-auto" dir="auto">
                  {check.review && <pre className="whitespace-pre-wrap font-sans">{check.review}</pre>}
                  {check.error && <div className="text-red-400">❌ {check.error}</div>}
                  {check.issues && check.issues.length > 0 && (
                    <ul className="list-disc list-inside space-y-1">
                      {check.issues.slice(0, 8).map((iss, ii) => (
                        <li key={ii}>{typeof iss === 'string' ? iss : JSON.stringify(iss)}</li>
                      ))}
                    </ul>
                  )}
                  {check.errors && check.errors.length > 0 && (
                    <ul className="list-disc list-inside space-y-1 text-red-300">
                      {check.errors.slice(0, 5).map((e, ei) => (
                        <li key={ei}>{typeof e === 'string' ? e : (e.message || JSON.stringify(e))}</li>
                      ))}
                    </ul>
                  )}
                  {check.console_errors && check.console_errors.length > 0 && (
                    <div className="text-red-300">
                      Console errors: {check.console_errors.length}
                    </div>
                  )}
                  {check.skipped && <div className="text-zinc-500">{check.reason}</div>}
                  {!check.review && !check.error && !check.issues?.length && !check.errors?.length && !check.skipped && (
                    <div className="text-emerald-400/80">✓ ما فيه ملاحظات</div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-4 pb-3 pt-1 flex justify-between text-[10px] text-zinc-500">
        <span>تم الفحص في {elapsed}s</span>
        <span>اضغط على أي قسم لرؤية التفاصيل</span>
      </div>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────
// Inline Choice Modal (used by the AI's `ask_user_inline` tool)
// AI pauses mid-turn → user clicks an option → user's choice
// becomes their next chat message → AI resumes.
// ─────────────────────────────────────────────────────────────
function InlineChoiceModal({ request, freeText, setFreeText, onClose, onPick }) {
  if (!request) return null;
  const rawOpts = request.options || [];
  // Normalize: accept strings or {label, emoji?, image_url?, description?}
  const norm = rawOpts.map((o) => {
    if (typeof o === 'string') return { label: o };
    if (o && typeof o === 'object') return {
      label: o.label || o.id || '',
      emoji: o.emoji || '',
      image_url: o.image_url || '',
      description: o.description || '',
    };
    return { label: String(o ?? '') };
  }).filter((o) => o.label);
  const hasImages = norm.some((o) => !!o.image_url);
  return (
    <div
      className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      data-testid="inline-choice-modal"
    >
      <div className={`bg-gradient-to-b from-zinc-900 to-black border border-cyan-500/40 rounded-2xl ${hasImages ? 'max-w-3xl' : 'max-w-lg'} w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto`}>
        <div className="flex items-start gap-3 mb-4">
          <div className="text-3xl">🤔</div>
          <div className="flex-1">
            <h2 className="text-base font-bold text-cyan-300 leading-snug" data-testid="inline-choice-question">
              {request.question}
            </h2>
            {request.context && (
              <p className="text-xs text-zinc-500 mt-1">{request.context}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-white text-xl leading-none"
            data-testid="inline-choice-close"
          >×</button>
        </div>

        {hasImages ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {norm.map((opt, i) => (
              <button
                key={i}
                onClick={() => onPick(opt.label)}
                className="group relative text-right rounded-xl overflow-hidden border border-zinc-800 hover:border-cyan-400 hover:scale-[1.03] transition-all duration-200 bg-zinc-900/60"
                data-testid={`inline-choice-option-${i}`}
              >
                {opt.image_url ? (
                  <div className="relative aspect-video bg-zinc-900 overflow-hidden">
                    <img
                      src={opt.image_url}
                      alt={opt.label}
                      loading="lazy"
                      className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-110"
                      onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent" />
                    {opt.emoji && (
                      <div className="absolute top-2 right-2 text-xl drop-shadow-lg">{opt.emoji}</div>
                    )}
                  </div>
                ) : (
                  <div className="aspect-video bg-gradient-to-br from-zinc-800 to-zinc-900 flex items-center justify-center text-5xl">
                    {opt.emoji || '✨'}
                  </div>
                )}
                <div className="p-2.5">
                  <p className="text-sm font-black text-white group-hover:text-cyan-300 transition-colors">
                    {opt.label}
                  </p>
                  {opt.description && (
                    <p className="text-[11px] text-zinc-400 mt-1 line-clamp-2 leading-snug">
                      {opt.description}
                    </p>
                  )}
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {norm.map((opt, i) => (
              <button
                key={i}
                onClick={() => onPick(opt.label)}
                className="w-full text-right px-4 py-3 rounded-xl bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-cyan-500/60 text-white text-sm font-semibold transition group flex items-center gap-2"
                data-testid={`inline-choice-option-${i}`}
              >
                {opt.emoji && <span className="text-lg">{opt.emoji}</span>}
                <span className="flex-1">{opt.label}</span>
                {opt.description && (
                  <span className="text-[11px] text-zinc-500 hidden sm:inline">{opt.description}</span>
                )}
                <span className="text-cyan-400 group-hover:text-cyan-300">›</span>
              </button>
            ))}
          </div>
        )}

        {request.allow_free_text && (
          <div className="mt-4 pt-4 border-t border-zinc-800">
            <label className="block text-xs text-zinc-500 mb-2">أو اكتب جوابك بحرية:</label>
            <div className="flex gap-2">
              <input
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                placeholder="اكتب هنا..."
                className="flex-1 bg-zinc-950 border border-zinc-700 focus:border-cyan-500 rounded-lg px-3 py-2 text-white text-sm outline-none"
                onKeyDown={(e) => { if (e.key === 'Enter' && freeText.trim()) onPick(freeText.trim()); }}
                data-testid="inline-choice-free-input"
              />
              <button
                onClick={() => freeText.trim() && onPick(freeText.trim())}
                disabled={!freeText.trim()}
                className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black text-sm font-bold transition disabled:opacity-40"
                data-testid="inline-choice-free-submit"
              >
                إرسال
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────
// Secure Credential Request Modal
// AI tool `request_credential` emits a sentinel → this modal pops up
// so the user can paste an API key safely. Value is encrypted at rest.
// ─────────────────────────────────────────────────────────────
function CredentialModal({ request, value, setValue, submitting, onClose, onSubmit }) {
  const [showValue, setShowValue] = useState(false);
  if (!request) return null;
  return (
    <div
      className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      data-testid="credential-modal"
    >
      <div className="bg-gradient-to-b from-zinc-900 to-black border border-amber-500/40 rounded-2xl max-w-lg w-full p-6 shadow-2xl">
        <div className="flex items-start gap-3 mb-4">
          <div className="text-3xl">🔑</div>
          <div className="flex-1">
            <h2 className="text-lg font-bold text-amber-300" data-testid="credential-modal-title">
              {request.label || request.service}
            </h2>
            <p className="text-xs text-zinc-500 mt-0.5">الخدمة: {request.service}</p>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-white text-xl leading-none"
            data-testid="credential-modal-close"
          >×</button>
        </div>

        {request.instructions && (
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 mb-4">
            <p className="text-xs text-amber-200 leading-relaxed whitespace-pre-wrap">
              {request.instructions}
            </p>
          </div>
        )}

        <label className="block text-xs font-semibold text-zinc-400 mb-2">
          الصق المفتاح هنا (سيتم تشفيره فوراً):
        </label>
        <div className="relative">
          <input
            type={showValue ? 'text' : 'password'}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="paste your key here..."
            className="w-full bg-zinc-950 border border-zinc-700 focus:border-amber-500 rounded-lg px-3 py-2.5 text-white text-sm font-mono outline-none transition"
            autoFocus
            dir="ltr"
            data-testid="credential-input"
          />
          <button
            type="button"
            onClick={() => setShowValue(!showValue)}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1"
            data-testid="credential-show-toggle"
          >
            {showValue ? '🙈 إخفاء' : '👁️ عرض'}
          </button>
        </div>

        <div className="mt-2 text-[11px] text-zinc-600 leading-relaxed">
          🔒 المفتاح يُخزّن مشفّراً (Fernet/AES-128) ولن يُعرض في الشات. الذكاء يقدر يستخدمه بس ما يقدر يطبعه نصياً.
        </div>

        <div className="flex gap-2 mt-5">
          <button
            onClick={onClose}
            disabled={submitting}
            className="flex-1 px-4 py-2.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm font-bold transition disabled:opacity-40"
            data-testid="credential-cancel"
          >
            إلغاء
          </button>
          <button
            onClick={onSubmit}
            disabled={submitting || !value.trim() || value.trim().length < 4}
            className="flex-1 px-4 py-2.5 rounded-lg bg-gradient-to-r from-amber-500 to-yellow-500 text-black text-sm font-bold transition hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
            data-testid="credential-submit"
          >
            {submitting ? '⏳ جاري الحفظ...' : '💾 حفظ المفتاح'}
          </button>
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
  const [attachments, setAttachments] = useState([]);
  const [replyToAsset, setReplyToAsset] = useState(null); // {id, type, image_url, prompt}
  const [lightboxAsset, setLightboxAsset] = useState(null);
  const [finalizeOpen, setFinalizeOpen] = useState(false);
  const [connectionsOpen, setConnectionsOpen] = useState(false);
  const [snapshotsOpen, setSnapshotsOpen] = useState(false);
  const [cookiesOpen, setCookiesOpen] = useState(false);
  const [thinkingStage, setThinkingStage] = useState(0);
  const [lastTask, setLastTask] = useState(null); // {label, model}
  const [loading, setLoading] = useState(false);
  // Active phase = either a user-clicked override OR what the backend currently
  // tracks for this project (so when the AI calls set_current_phase the sidebar
  // updates automatically).
  const [activePhaseOverride, setActivePhaseOverride] = useState(null);
  const activePhase = activePhaseOverride || project?.current_phase || 'discovery';
  const setActivePhase = setActivePhaseOverride;
  const [activeTab, setActiveTab] = useState('chat'); // chat | live | approved
  // Credits guard — disables input + shows recharge UI when credits = 0
  const { isBlocked: creditsBlocked, refresh: refreshCredits, credits: liveCredits, unlimited: liveUnlimited } = useCreditsGuard();

  // Mode helpers — video modes hide HTML/Build/Deploy UI entirely.
  const isVideoMode = ['video_studio', 'anime_studio', 'longform_video'].includes(project?.mode);
  const isStudioMode = isVideoMode || project?.mode === 'image_studio';
  const isAppMode = project?.mode === 'app';
  const VIDEO_PHASE_EMOJI = { film_type: '🎞️', characters: '👥', script: '📝', voice: '🎙️', storyboard: '🖼️', preview: '👁️', render: '✨' };
  const sidebarPhases = isVideoMode
    ? VIDEO_PHASES.map((p) => ({ id: p.id, title: p.label, icon: VIDEO_PHASE_EMOJI[p.id] || '🎬', desc: p.desc }))
    : PHASES;
  const [previewMode, setPreviewMode] = useState('desktop');
  // For app mode: which device frame to show (iphone | android) — initial pick from project.platform
  const [appDevice, setAppDevice] = useState('iphone');
  const [myProjectsOpen, setMyProjectsOpen] = useState(false);
  // Mobile-only: controls the slide-in drawer that exposes the right-side
  // phases sidebar on small screens. Default closed; user taps the colored
  // FAB to peek at phases without losing the chat context.
  const [phasesMobileOpen, setPhasesMobileOpen] = useState(false);
  const [credentialRequest, setCredentialRequest] = useState(null); // {service, label, instructions}
  const [credentialValue, setCredentialValue] = useState('');
  const [credentialSubmitting, setCredentialSubmitting] = useState(false);
  const [inlineChoice, setInlineChoice] = useState(null); // {question, options, allow_free_text, context}
  const [inlineChoiceText, setInlineChoiceText] = useState('');
  const chatEndRef = useRef(null);
  const chatScrollRef = useRef(null);
  const userScrolledUpRef = useRef(false);
  const fileInputRef = useRef(null);
  // AbortController for the in-flight SSE stream — lets the user hit "Stop"
  // when they don't like the direction the AI is taking. When aborted, we
  // queue a follow-up that prompts: "What do you want me to change?"
  const streamAbortRef = useRef(null);
  const [stopReason, setStopReason] = useState(null); // 'user_cancel' | null

  // Auto-scroll to bottom when AI streams new content — UNLESS the user has
  // scrolled up to read earlier output (we respect their intent).
  const isAtBottom = useCallback(() => {
    const el = chatScrollRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }, []);
  const onChatScroll = useCallback(() => {
    userScrolledUpRef.current = !isAtBottom();
  }, [isAtBottom]);
  const scrollToBottomSoon = useCallback(() => {
    if (userScrolledUpRef.current) return;
    const el = chatScrollRef.current;
    if (!el) return;
    requestAnimationFrame(() => {
      try { el.scrollTo({ top: el.scrollHeight, behavior: 'auto' }); } catch (_) { /* ignore */ }
    });
  }, []);

  // Pause polling while modals are open (avoids modal flicker on re-render)
  const pollPausedRef = useRef(false);
  useEffect(() => {
    pollPausedRef.current = finalizeOpen || connectionsOpen || snapshotsOpen || !!lightboxAsset;
  }, [finalizeOpen, connectionsOpen, snapshotsOpen, lightboxAsset]);

  // Also pause polling while an SSE chat stream is in flight — the local state
  // has the optimistic user msg + the live-typing AI reply which the DB doesn't
  // yet know about. A poll-replace here would WIPE the in-progress chat.
  const loadingRef = useRef(false);
  useEffect(() => { loadingRef.current = loading; }, [loading]);

  // Manual force-refresh of project (used by 'Refresh' button)
  const [previewKey, setPreviewKey] = useState(0);

  // ── Quick-message bus — health-card suggestion buttons (and other UI bits)
  // dispatch a `freebuild_quick_message` window event with the text to send.
  // We populate the composer with it; user can edit or hit Send.
  useEffect(() => {
    const handler = (e) => {
      const text = e?.detail?.text;
      if (!text) return;
      setMessage((m) => (m ? `${m.trim()} ${text}` : text));
      try {
        toast.info('💡 الاقتراح أُضيف للمحادثة — اضغط إرسال');
      } catch (_) { /* ignore */ }
    };
    window.addEventListener('freebuild_quick_message', handler);
    return () => window.removeEventListener('freebuild_quick_message', handler);
  }, []);
  // When an "app" mode project loads, force mobile preview and pick the device
  // frame matching the chosen platform (ios → iphone, android → android, both → iphone default)
  useEffect(() => {
    if (project?.mode === 'app') {
      setPreviewMode('mobile');
      const p = (project.platform || 'both').toLowerCase();
      if (p === 'android') setAppDevice('android');
      else setAppDevice('iphone');
    }
  }, [project?.mode, project?.platform]);

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
      // Don't poll while a stream is actively writing to local state, OR while
      // any local message has streaming=true. Both cases mean local state is
      // ahead of the DB and a DB-replace would WIPE the user's just-sent
      // message + the live AI reply mid-flight.
      if (pollPausedRef.current || loadingRef.current) return;
      try {
        const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
        if (r.ok && !cancelled) {
          const d = await r.json();
          setProject((prev) => {
            // Never overwrite a project that has more (newer) messages locally
            // — the DB hasn't caught up to our optimistic update yet.
            if (prev && (prev.messages?.length || 0) > (d.messages?.length || 0)) {
              return prev;
            }
            // Skip setState if nothing meaningful changed (avoids child re-renders)
            if (prev && prev.updated_at === d.updated_at && prev.messages?.length === d.messages?.length) {
              return prev;
            }
            // Force iframe remount only if HTML actually changed
            if (prev && prev.current_html !== d.current_html) {
              setPreviewKey((k) => k + 1);
            }
            // PRESERVE LOCAL agent_steps on assistant messages — the DB only
            // stores the final `content` summary, not the streamed bubbles.
            // If we just swap in the DB version, the styled live_text bubbles
            // would vanish and m.content would suddenly appear in a different
            // style — causing the "text writes then disappears" flash.
            // We merge per-index: pick text from DB (authoritative) but keep
            // local agent_steps/agent_streaming/agent_holder_id when present.
            if (prev?.messages && d.messages && prev.messages.length === d.messages.length) {
              const merged = d.messages.map((dm, i) => {
                const pm = prev.messages[i];
                if (!pm) return dm;
                if (pm.role !== 'assistant' || dm.role !== 'assistant') return dm;
                if (!pm.agent_steps || pm.agent_steps.length === 0) return dm;
                return {
                  ...dm,
                  agent_steps: pm.agent_steps,
                  agent_holder_id: pm.agent_holder_id,
                  agent_streaming: false, // streaming already done by the time polling lands
                };
              });
              return { ...d, messages: merged };
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

  // Listen for in-chat action buttons (approve/regenerate/edit on images).
  // The MarkdownImage component dispatches `zenrex:option-pick` events; we
  // pre-fill the composer so the user can confirm or tweak before submitting
  // (auto-send would surprise people who clicked accidentally).
  useEffect(() => {
    const onPick = (e) => {
      const text = (e?.detail?.text || '').trim();
      if (!text) return;
      setMessage((prev) => (prev ? `${prev}\n${text}` : text));
      setActiveTab('chat');
    };
    window.addEventListener('zenrex:option-pick', onPick);
    return () => window.removeEventListener('zenrex:option-pick', onPick);
  }, []);

  const send = async () => {
    if ((!message.trim() && attachments.length === 0 && !replyToAsset) || loading) return;
    if (creditsBlocked) {
      toast.error('رصيد النقاط انتهى — اشحن باقة لمواصلة الدردشة');
      navigate('/pricing');
      return;
    }
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
      // Pass the user's UI language so the AI replies in the same language
      try {
        const lang = (typeof window !== 'undefined' && window.localStorage)
          ? (localStorage.getItem('zenrex_lang_manual') || localStorage.getItem('zenrex_lang') || 'ar')
          : 'ar';
        fd.append('user_language', lang);
      } catch (_) { fd.append('user_language', 'ar'); }
      filesToSend.forEach((f) => fd.append('files', f));
      if (refAsset?.id) fd.append('reference_asset_id', refAsset.id);
      // Use streaming agent endpoint when no files attached (so user sees the AI's
      // live thinking — every tool call streams into the chat as a visible step)
      const useAgent = filesToSend.length === 0 && !refAsset?.id;
      if (useAgent) {
        // Stream Server-Sent Events; render each step live.
        // Bind an AbortController so the user can hit "Stop" mid-stream.
        const abortController = new AbortController();
        streamAbortRef.current = abortController;
        setStopReason(null);
        const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/agent-chat-stream`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: fd,
          signal: abortController.signal,
        });
        if (!r.ok) {
          if (r.status === 402) {
            await refreshCredits();
            notifyCreditsChanged();
            toast.error('رصيد النقاط انتهى — اشحن باقة لمواصلة الدردشة');
            navigate('/pricing');
            return;
          }
          throw new Error(`HTTP ${r.status}`);
        }
        const reader = r.body.getReader();
        const decoder = new TextDecoder();
        let buf = '';
        let finalSummary = '';
        let finalOptions = [];
        let finalInlineImages = [];
        let finalInlineAudio = [];
        let finalInlineVideo = [];
        let liveSteps = [];
        let htmlUpdated = false;
        const stepsHolderId = `agent-steps-${Date.now()}`;
        // Push a placeholder assistant message we'll update live
        setProject((p) => {
          if (!p) return p;
          return {
            ...p,
            messages: [...(p.messages || []),
              { role: 'user', content: msgText, timestamp: new Date().toISOString(), reference: refAsset, attachments: [] },
              { role: 'assistant', content: '', timestamp: new Date().toISOString(),
                agent_steps: [], agent_streaming: true, agent_holder_id: stepsHolderId },
            ],
          };
        });

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
          // Auto-scroll to bottom so user sees the live typing without scrolling
          scrollToBottomSoon();
        };

        let streamReceivedDone = false;
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
            } else if (eventName === 'text_delta') {
              // Live streaming text from Claude — append to the current text bubble.
              // If the last step is an open "live_text" bubble, extend it; else create one.
              const last = liveSteps[liveSteps.length - 1];
              if (last && last.kind === 'live_text' && last.open) {
                last.text = (last.text || '') + (payload.text || '');
              } else {
                liveSteps.push({ kind: 'live_text', text: payload.text || '', open: true, step: payload.step });
              }
            } else if (eventName === 'text_end') {
              // Close the current live_text bubble so subsequent text starts a new one
              const last = liveSteps[liveSteps.length - 1];
              if (last && last.kind === 'live_text') last.open = false;
            } else if (eventName === 'tool') {
              liveSteps.push({ kind: 'tool', ...payload });
              // Detect request_credential sentinel → open secure modal so the
              // user can paste their API key safely (encrypted at rest).
              if (
                payload?.name === 'request_credential' &&
                payload?.phase === 'done' &&
                payload?.result?.needs_user_input
              ) {
                setCredentialRequest({
                  service: payload.result.service,
                  label: payload.result.label || payload.result.service,
                  instructions: payload.result.instructions || '',
                });
                setCredentialValue('');
              }
              // Detect ask_user_inline sentinel → open Inline Choice Modal.
              if (
                payload?.name === 'ask_user_inline' &&
                payload?.phase === 'done' &&
                payload?.result?.pending_user_input &&
                payload?.result?.kind === 'choice'
              ) {
                setInlineChoice({
                  question: payload.result.question,
                  options: payload.result.options || [],
                  allow_free_text: payload.result.allow_free_text !== false,
                  context: payload.result.context || '',
                });
                setInlineChoiceText('');
              }
            } else if (eventName === 'tool_building') {
              // Update or push a "building" indicator. Now also carries a live
              // snippet of the code being typed — like Cursor/Claude's editor.
              const last = liveSteps[liveSteps.length - 1];
              if (last && last.kind === 'tool_building' && last.step === payload.step && !last.done) {
                last.bytes = payload.bytes;
                last.label = payload.label;
                last.snippet = payload.snippet;
                last.tool_name = payload.tool_name || last.tool_name;
                if (payload.done) last.done = true;
              } else {
                liveSteps.push({ kind: 'tool_building', ...payload });
              }
            } else if (eventName === 'done') {
              streamReceivedDone = true;
              finalSummary = payload.summary || '';
              finalOptions = payload.options || [];
              finalInlineImages = payload.inline_images || [];
              finalInlineAudio = payload.inline_audio || [];
              finalInlineVideo = payload.inline_video || [];
              htmlUpdated = !!payload.html_updated;
              setLastTask({ label: `🤖 Agent (${payload.iterations || 0} خطوة)`, model: payload.model_used || '' });
              // Credits were just deducted server-side — refresh the visible
              // balance pill in both the chat input strip and the navbar so
              // the user sees the drop in near-real-time.
              try { await refreshCredits(); } catch (_) { /* ignore */ }
              notifyCreditsChanged();
            } else if (eventName === 'error') {
              liveSteps.push({ kind: 'error', message: payload.message });
            } else if (eventName === 'ping') {
              // Heartbeat — keeps proxies alive during long tool generation. No UI.
            } else if (eventName === 'tool_progress') {
              // Long-running tool keepalive — update the running tool's label so
              // the user sees "still working (12s)" instead of a frozen UI.
              const last = liveSteps.findLast?.(
                (s) => s.kind === 'tool' && s.name === payload.name && s.phase === 'running'
              );
              if (last) {
                last.label = payload.message || last.label;
                last.elapsed_sec = payload.elapsed_sec;
              } else {
                liveSteps.push({
                  kind: 'tool',
                  name: payload.name,
                  phase: 'running',
                  label: payload.message,
                  elapsed_sec: payload.elapsed_sec,
                });
              }
            }
            updateLive();
          }
        }
        // GRACEFUL INTERRUPTION HANDLING:
        // If the stream ended (proxy timeout, network blip) without a 'done' event,
        // synthesize a helpful summary that PRESERVES the work shown above.
        // Also handles user-initiated cancel via the Stop button.
        if (!streamReceivedDone) {
          const wasUserCancel = abortController.signal.aborted;
          // Collect the AI's last narration so it stays visible as the message body
          const allNarration = liveSteps
            .filter((s) => s.kind === 'live_text' && (s.text || '').trim())
            .map((s) => s.text.trim())
            .join('\n\n');
          const completedTools = liveSteps.filter((s) => s.kind === 'tool' && s.phase === 'done').length;
          const builtTools = liveSteps.filter((s) => s.kind === 'tool_building' && s.done);
          const codeBytes = builtTools.reduce((acc, b) => acc + (b.bytes || 0), 0);
          let interruptNote;
          if (wasUserCancel) {
            interruptNote = `\n\n🛑 **أوقفت التنفيذ بناءً على طلبك.** عشان ما تخسر رصيد، خبّرني الحين:\n\n- وش بالضبط ما عجبك في النتيجة الحالية؟\n- تبيها تغيير **جذري** (نبدأ من الصفر) ولاّ **تعديلات** بس على نفس الفكرة؟\n- عندك مرجع أو فكرة محددة في بالك؟ ارفقها لي (صورة/فيديو/ملف) وأنا أرتّب نفسي من جديد.`;
            setLastTask({ label: '🛑 أوقفه المستخدم', model: '' });
          } else {
            interruptNote = codeBytes > 0
              ? `\n\n💾 خلصت من كتابة ~${codeBytes.toLocaleString()} حرف لكن الاتصال انقطع قبل ما أحفظ. ابعث "كمّل" أكمل من حيث وقفت.`
              : completedTools > 0
                ? `\n\n⏸️ نفّذت ${completedTools} خطوة وانقطع الاتصال. ابعث "كمّل" نكمل.`
                : `\n\n⏸️ انقطع الاتصال قبل ما أبدأ. أعد المحاولة من فضلك.`;
            setLastTask({ label: '⏸️ انقطع', model: '' });
          }
          finalSummary = allNarration ? allNarration + interruptNote : interruptNote.trim();
          if (wasUserCancel) {
            // Offer one-click choice chips so the user can answer fast.
            finalOptions = [
              { id: 'change_radical', label: '🔄 غيّر كل شي من جديد', emoji: '🔄' },
              { id: 'change_partial', label: '✏️ بس عدّل قسم معيّن', emoji: '✏️' },
              { id: 'change_style',   label: '🎨 غيّر الستايل/الألوان', emoji: '🎨' },
              { id: 'change_text',    label: '📝 غيّر النصوص فقط',     emoji: '📝' },
            ];
          }
        }
        // Finalize: mark message as not streaming
        setProject((p) => {
          if (!p) return p;
          const msgs = [...(p.messages || [])];
          for (let i = msgs.length - 1; i >= 0; i--) {
            if (msgs[i].agent_holder_id === stepsHolderId) {
              msgs[i] = { ...msgs[i], agent_streaming: false, options: finalOptions, inline_images: finalInlineImages, inline_audio: finalInlineAudio, inline_video: finalInlineVideo, content: finalSummary };
              break;
            }
          }
          return { ...p, messages: msgs };
        });
        if (htmlUpdated) {
          toast.success('✨ تم تحديث المعاينة الحية', {
            action: { label: 'افتح', onClick: () => setActiveTab('live') },
          });
          setActiveTab('live');
          // refresh project HTML/snapshots but preserve local messages
          // (DB doesn't have agent_steps — refetching would erase the live narration
          // bubbles the user just watched, making the response feel "wiped")
          const pr = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
          if (pr.ok) {
            const fresh = await pr.json();
            setProject((p) => {
              if (!p) return fresh;
              // Keep our local messages (they have agent_steps); take new HTML/snapshots from server
              const localMsgs = p.messages || [];
              const dbMsgs = fresh.messages || [];
              // Merge: use local messages but adopt any new server-only fields (had_html, etc.)
              const merged = localMsgs.map((lm) => {
                if (!lm.agent_holder_id) return lm;
                const dbCounter = dbMsgs.find(
                  (dm) => dm.role === lm.role && (dm.content || '').slice(0, 40) === (lm.content || '').slice(0, 40)
                );
                return dbCounter ? { ...lm, had_html: dbCounter.had_html, agent_iterations: dbCounter.agent_iterations } : lm;
              });
              return { ...fresh, messages: merged };
            });
          }
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
        setActiveTab('live');
      }
      // Capture which AI model worked on this turn (for UI display)
      if (data.task_label || data.model_used) {
        setLastTask({ label: data.task_label || '', model: data.model_used || '' });
      }
      // Refresh
      const pr = await fetch(`${API}/api/freebuild-chat/project/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
      if (pr.ok) setProject(await pr.json());
    } catch (e) {
      // AbortError is the user clicking Stop — already handled inside the try
      // block via the wasUserCancel branch. Don't surface it as an error toast.
      if (e?.name === 'AbortError') {
        // no-op: graceful cancel
      } else {
        // Stream errored unexpectedly (proxy timeout, network blip). Do NOT
        // restore the user's typed message into the input — that confused users
        // who thought the chat "reset". Instead, append a soft inline note to
        // the in-flight assistant bubble so they see what happened in context.
        const errMsg = String(e?.message || 'انقطع الاتصال');
        setProject((p) => {
          if (!p) return p;
          const msgs = [...(p.messages || [])];
          for (let i = msgs.length - 1; i >= 0; i--) {
            if (msgs[i].role === 'assistant' && msgs[i].agent_streaming) {
              const softNote = `\n\n⚠️ انقطع الاتصال (${errMsg.slice(0, 80)}) — ابعث "كمّل" أكمل من نفس النقطة بدون ما تخسر تقدّمك.`;
              msgs[i] = {
                ...msgs[i],
                agent_streaming: false,
                content: (msgs[i].content || '') + softNote,
              };
              break;
            }
          }
          return { ...p, messages: msgs };
        });
      }
    } finally {
      streamAbortRef.current = null;
      clearInterval(stageTimer);
      setLoading(false);
      setThinkingStage(0);
    }
  };

  // User-initiated cancel of the in-flight SSE stream. We let the existing
  // !streamReceivedDone branch synthesize the friendly "ما أعجبك؟" follow-up
  // — the user can answer in plain Arabic or click an option chip.
  const stopStream = useCallback(() => {
    if (streamAbortRef.current) {
      setStopReason('user_cancel');
      try { streamAbortRef.current.abort(); } catch { /* already aborted */ }
    }
  }, []);

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
        setActiveTab('live');
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
            onClick={() => navigate('/freebuild/projects')}
            data-testid="open-my-projects-chat"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all shrink-0"
            title="افتح مشاريعي قيد الإنشاء"
          >
            <FolderOpen className="w-4 h-4" />
            <span className="text-xs font-medium hidden sm:inline">مشاريعي</span>
          </button>
          <a href="/" className="hidden md:inline-flex shrink-0" aria-label="Zenrex"><ZenrexBrand size={22} /></a>
          <Globe className="w-6 h-6 text-emerald-400 shrink-0" />
          <div className="min-w-0">
            <h1 className="font-bold text-base sm:text-lg truncate" data-testid="project-title">{project.name}</h1>
            <p className="text-xs text-zinc-500 truncate">{sidebarPhases.find((p) => p.id === activePhase)?.title}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {!isVideoMode && (
          <button
            type="button"
            onClick={async () => {
              try {
                const token = localStorage.getItem('token');
                const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/export`, {
                  headers: { Authorization: `Bearer ${token}` },
                });
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                const blob = await r.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const safe = (project.name || 'project').replace(/[^a-zA-Z0-9-_\u0600-\u06FF]/g, '_').slice(0, 40);
                a.download = `zenrex-${safe}-${projectId.slice(0, 8)}.json`;
                document.body.appendChild(a); a.click(); a.remove();
                URL.revokeObjectURL(url);
                toast.success('تم تنزيل نسخة كاملة من المشروع 💾');
              } catch (e) {
                toast.error(`فشل التنزيل: ${e.message}`);
              }
            }}
            data-testid="export-project"
            className="hidden sm:flex px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-cyan-400/30 text-cyan-200 text-xs font-bold items-center gap-1.5"
            title="تنزيل نسخة احتياطية كاملة من المشروع (رسائل + قرارات + شخصيات + أصول) — JSON"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">نسخة احتياطية</span>
          </button>
          )}
          {!isVideoMode && project.current_html && (
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
          {!isVideoMode && project.code_unlocked && (
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
          {!isVideoMode && project.current_html && (
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
          <div className={`hidden sm:flex px-3 py-1.5 ${isVideoMode ? 'bg-red-500/10 border-red-500/30' : 'bg-emerald-500/10 border-emerald-500/30'} border rounded-lg items-center gap-1.5`}>
            <Sparkles className={`w-3.5 h-3.5 ${isVideoMode ? 'text-red-400' : 'text-emerald-400'}`} />
            <span className={`text-xs ${isVideoMode ? 'text-red-300' : 'text-emerald-300'} font-bold hidden sm:inline`}>{isVideoMode ? '🎬 استوديو الفيديو' : isAppMode ? '📱 استوديو التطبيقات' : 'من الصفر'}</span>
          </div>
          <div className="hidden sm:flex"><UsageIndicator compact refreshKey={messages.length} /></div>
          <div className="hidden sm:flex"><StorageIndicator compact /></div>
        </div>
      </div>

      {/* Main: 3 panes */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* RIGHT (sidebar in RTL): Phases.
            • Desktop (md+): always visible as a static column on the right.
            • Mobile: hidden by default. A floating colored button (FAB) below
              opens it as a slide-in drawer. Slides off-screen otherwise. */}
        <div
          className={`bg-zinc-900/95 backdrop-blur-xl border-l border-white/10 p-3 lg:p-4 overflow-y-auto shrink-0 transition-transform duration-300
            md:relative md:w-56 lg:w-64 md:translate-x-0 md:block
            fixed inset-y-0 right-0 z-40 w-72 max-w-[85vw] ${phasesMobileOpen ? 'translate-x-0' : 'translate-x-full'} md:translate-x-0`}
          data-testid="phases-sidebar"
        >
          {/* Mobile-only close button */}
          <button
            type="button"
            onClick={() => setPhasesMobileOpen(false)}
            className="md:hidden absolute top-2 left-2 w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-zinc-300"
            aria-label="إغلاق المراحل"
            data-testid="close-phases-drawer"
          >
            <X className="w-4 h-4" />
          </button>
          {/* 📊 SITE HEALTH SCORE — visible after first build */}
          {project?.last_health && (
            <div className="mb-4 rounded-xl border border-zinc-700/60 bg-gradient-to-br from-zinc-900 to-zinc-950 p-3" data-testid="health-card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-zinc-400">صحة الموقع</span>
                <span className="text-lg">{project.last_health.summary_emoji}</span>
              </div>
              <div className="flex items-baseline gap-1 mb-1">
                <span className={`text-3xl font-black ${
                  project.last_health.total >= 80 ? 'text-emerald-400' :
                  project.last_health.total >= 60 ? 'text-amber-400' : 'text-orange-400'
                }`} data-testid="health-score-total">
                  {project.last_health.total}
                </span>
                <span className="text-zinc-500 text-sm">/100</span>
                <span className="text-zinc-400 text-xs mr-2">{project.last_health.grade}</span>
              </div>
              {/* Dimension bars */}
              <div className="space-y-1 mb-3">
                {(project.last_health.dimensions || []).map((d) => (
                  <div key={d.id} className="text-[10px]">
                    <div className="flex justify-between text-zinc-400 mb-0.5">
                      <span>{d.name}</span>
                      <span>{d.score}/{d.max}</span>
                    </div>
                    <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          d.percent >= 80 ? 'bg-emerald-500' :
                          d.percent >= 60 ? 'bg-amber-500' : 'bg-orange-500'
                        }`}
                        style={{ width: `${d.percent}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              {/* Top suggestions — click to apply */}
              {(project.last_health.top_suggestions || []).length > 0 && (
                <div className="border-t border-zinc-800 pt-2">
                  <div className="text-[10px] font-bold text-zinc-400 mb-1.5">
                    💡 رفعها لـ{Math.min(95, project.last_health.total + project.last_health.improvement_potential)}+:
                  </div>
                  {project.last_health.top_suggestions.slice(0, 3).map((sug, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        try {
                          window.dispatchEvent(new CustomEvent('freebuild_quick_message', {
                            detail: { text: sug },
                          }));
                        } catch (_) { /* ignore */ }
                      }}
                      data-testid={`health-suggest-${i}`}
                      className="text-right w-full text-[11px] text-emerald-300/90 hover:text-emerald-200 hover:bg-emerald-500/10 rounded px-2 py-1 mb-0.5 transition"
                    >
                      • {sug.length > 55 ? sug.slice(0, 55) + '…' : sug}
                    </button>
                  ))}
                </div>
              )}
              {/* Checkout CTA if not unlocked */}
              {!project.code_unlocked && project.current_html && (
                <button
                  onClick={() => (window.location.href = `/freebuild/checkout/${project.id}`)}
                  data-testid="upgrade-cta"
                  className="mt-3 w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs font-bold py-2 rounded-lg hover:opacity-90"
                >
                  🚀 احصد الكود — $100
                </button>
              )}
            </div>
          )}
          <h2 className="font-bold mb-3 text-emerald-400 text-sm flex items-center gap-1.5">
            <span>📋</span> <span>مراحل البناء</span>
          </h2>
          <div className="space-y-2">
            {sidebarPhases.map((phase, phaseIdx) => {
              const isActive = activePhase === phase.id;
              // Compute "done" state based on real signals
              const qcount = messages.filter((mm) => mm.role === 'assistant' && (mm.options || []).length > 0).length;
              const variantsCount = messages.reduce((s, mm) => s + (mm.design_variants?.length || 0), 0);
              let stat = '';
              let isDone = false;
              if (isVideoMode) {
                const phaseHistory = new Set(project?.phase_history || []);
                const currentPhase = project?.current_phase || 'film_type';
                if (phaseHistory.has(phase.id)) { stat = '✓ منتهية'; isDone = true; }
                else if (phase.id === currentPhase) stat = '🟠 جارية الآن';
                else stat = '🔒 مقفلة';
              } else {
                // Determine if the phase is "done" based on real artifacts.
                // Rule: any phase whose milestone artifact exists OR is implicit
                // in `phase_history` (server-marked) is considered complete.
                const phaseHistory = new Set(project?.phase_history || []);
                const htmlExists = !!project?.current_html;
                if (phase.id === 'discovery') {
                  isDone = (
                    phaseHistory.has('discovery') || qcount >= 2 || htmlExists ||
                    (project?.brief && Object.keys(project.brief || {}).length >= 3)
                  );
                  stat = isDone ? `✓ ${qcount || ''} سؤال`.trim() : `${qcount} سؤال طُرح`;
                } else if (phase.id === 'design') {
                  isDone = (
                    phaseHistory.has('design') || htmlExists || variantsCount > 0
                  );
                  stat = isDone ? '✓ معتمد' : (variantsCount > 0 ? `${variantsCount} اقتراح` : 'بانتظار خيارات');
                } else if (phase.id === 'assets') {
                  isDone = phaseHistory.has('assets') || approvedAssets.length >= 1 || htmlExists;
                  stat = isDone ? `✓ ${approvedAssets.length} معتمد` : `${approvedAssets.length} معتمد`;
                } else if (phase.id === 'build') {
                  isDone = htmlExists;
                  stat = isDone ? '✓ مبني' : (project?.code_unlocked ? '🔓 جاهز للبناء' : '🔒 مقفل');
                } else if (phase.id === 'preview') {
                  isDone = !!project?.preview_approved;
                  stat = isDone ? '✓ معتمد' : (htmlExists ? '🟠 للمراجعة' : '—');
                } else if (phase.id === 'deploy') {
                  isDone = !!project?.deployed_url || !!project?.github_repo_url || !!project?.published;
                  stat = isDone ? '✓ منشور' : '—';
                }
              }

              // Color logic: red (locked) / orange+pulse (active) / green (done)
              let stateClasses = '';
              let dotClass = '';
              let icColor = 'text-zinc-400';
              if (isDone) {
                stateClasses = 'bg-emerald-500/15 border-emerald-500/50 text-emerald-100 shadow-[0_0_18px_rgba(16,185,129,0.25)]';
                dotClass = 'bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]';
                icColor = 'text-emerald-300';
              } else if (isActive) {
                stateClasses = 'bg-orange-500/15 border-orange-500/60 text-orange-100 shadow-[0_0_20px_rgba(249,115,22,0.35)] animate-pulse';
                dotClass = 'bg-orange-400 animate-pulse';
                icColor = 'text-orange-300';
              } else {
                stateClasses = 'bg-rose-500/5 border-rose-500/20 text-rose-200/60 hover:border-rose-400/40';
                dotClass = 'bg-rose-500/40';
                icColor = 'text-rose-300/60';
              }

              const handleClick = () => {
                setActivePhase(phase.id);
                if (isVideoMode) { setActiveTab('chat'); return; }
                if (phase.id === 'assets') setActiveTab('approved');
                else if (phase.id === 'preview' || phase.id === 'build') {
                  if (project?.current_html) setActiveTab('live');
                  else setActiveTab('chat');
                } else if (phase.id === 'deploy') {
                  if (project?.code_unlocked) setConnectionsOpen(true);
                  else if (project?.current_html) setActiveTab('live');
                  else setActiveTab('chat');
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
                  className={`w-full text-right p-3 rounded-lg border transition-all ${stateClasses}`}
                >
                  <div className="flex items-center justify-between mb-1 gap-1">
                    <span className={`text-sm font-bold flex items-center gap-1.5 min-w-0 ${icColor}`}>
                      <span className={`w-2 h-2 rounded-full ${dotClass} shrink-0`}></span>
                      <span className="truncate">{phaseIdx + 1}. {phase.title}</span>
                    </span>
                    {isDone ? <Check className="w-4 h-4 text-emerald-400 shrink-0" /> : null}
                  </div>
                  <p className="text-[10px] opacity-70 leading-tight">{phase.desc}</p>
                  <p className="text-[10px] mt-1 font-bold opacity-90">{stat}</p>
                </button>
              );
            })}
          </div>

          {/* Quick edits box — visible when site has a current_html (something to edit) */}
          {!isVideoMode && project?.current_html && (
            <QuickEditsBox
              projectId={project.id}
              onApplied={() => { setActiveTab('live'); }}
              token={localStorage.getItem('token')}
              api={API}
            />
          )}

          {/* Lock-state mini card for "Build" phase — website mode only */}
          {!isVideoMode && !project.code_unlocked && (
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
            {/* GitHub push / paywall button — website mode only */}
            {!isVideoMode && (
            <button
              type="button"
              onClick={() => {
                if (!project.current_html) {
                  toast.info('أكمل بناء الموقع أولاً قبل النشر');
                  return;
                }
                if (project.code_unlocked) {
                  setConnectionsOpen(true);
                } else {
                  setFinalizeOpen(true);
                }
              }}
              data-testid="chat-github-deploy-btn"
              className={`hidden sm:flex items-center gap-1.5 px-3 py-1.5 my-1 mx-1 rounded-md text-[11px] font-black transition-all ${
                project.code_unlocked
                  ? 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-200 border border-emerald-400/40'
                  : 'bg-amber-500/15 hover:bg-amber-500/25 text-amber-200 border border-amber-400/40'
              }`}
              title={project.code_unlocked ? 'انشر إلى GitHub' : 'افتح حزمة الاستقلالية لنشر الكود'}
            >
              {project.code_unlocked ? (
                <>
                  <Github className="w-3.5 h-3.5" />
                  <span>ادفع لـ GitHub</span>
                </>
              ) : (
                <>
                  <Crown className="w-3.5 h-3.5" />
                  <span>افتح GitHub Push (مدفوع)</span>
                </>
              )}
            </button>
            )}
            <div className="text-[10px] text-zinc-500 hidden sm:flex items-center gap-1.5 px-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>محفوظ تلقائياً</span>
            </div>
          </div>

          {/* Video/anime/longform projects get a phase tracker above the chat.
              It's a non-disruptive layer — never interferes with message rendering. */}
          {['video_studio', 'anime_studio', 'longform_video', 'image_studio'].includes(project?.mode) && (
            <VideoPhaseTracker project={project} onOpenAssets={(phaseId) => setActiveTab('approved')} />
          )}

          {/* Tab Content */}
          {activeTab === 'chat' && (
            <div ref={chatScrollRef} onScroll={onChatScroll} className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4" data-testid="chat-messages">
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
                      {/* Render the main content bubble ONLY if there are no
                          live_text steps. When the assistant streamed via SSE
                          we keep those styled bubbles as the single source of
                          truth — swapping to m.content would cause a visible
                          flash where text appears to "rewrite itself". */}
                      {!(
                        (m.role === 'assistant') &&
                        (m.agent_streaming || (m.agent_steps || []).some((s) => s.kind === 'live_text'))
                      ) && (
                        <MarkdownText>{m.content}</MarkdownText>
                      )}
                    </div>

                    {/* Clean copy/quote toolbar — only on finished assistant messages with content */}
                    {m.role === 'assistant' && !m.agent_streaming && (m.content || '').trim().length > 0 && (
                      <MessageActions
                        content={m.content}
                        onQuote={(text) => {
                          const quoted = String(text)
                            .split('\n')
                            .map((ln) => '> ' + ln)
                            .join('\n');
                          setMessage((prev) => (prev ? `${quoted}\n\n${prev}` : `${quoted}\n\n`));
                          const inp = document.querySelector('[data-testid="chat-input"]');
                          if (inp) { try { inp.focus(); inp.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch { /* DOM not ready */ } }
                        }}
                      />
                    )}

                    {/* Brand spinner — only while the agent is actively working.
                        Uses neutral dots (no Zenrex Z) per UX request. */}
                    {m.role === 'assistant' && m.agent_streaming && (
                      <div className="mt-3" data-testid={`agent-spinner-${i}`}>
                        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-400/30">
                          <span className="flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-cyan-300 animate-pulse" style={{ animationDelay: '0ms' }} />
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-pulse" style={{ animationDelay: '180ms' }} />
                            <span className="w-1.5 h-1.5 rounded-full bg-cyan-300 animate-pulse" style={{ animationDelay: '360ms' }} />
                          </span>
                          <span className="text-[12px] font-semibold bg-gradient-to-r from-cyan-300 via-emerald-300 to-cyan-300 bg-clip-text text-transparent">
                            يحلل ويكتب...
                          </span>
                        </div>
                      </div>
                    )}

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
                          if (s.kind === 'live_text') {
                            // Live streaming text from Claude. Render markdown
                            // incrementally so headings/lists look polished.
                            // Keep these bubbles visible permanently — even
                            // after streaming completes — because they are the
                            // single source of truth (the main m.content bubble
                            // is hidden when live_text steps exist). This
                            // eliminates the "text writes then disappears"
                            // flash users complained about.
                            // Only hide empty bubbles (no text accumulated).
                            const hasText = (s.text || '').trim().length > 0;
                            if (!hasText) return null;
                            return (
                              <div key={sIdx} className="text-sm leading-relaxed text-zinc-100">
                                <MarkdownText>{s.text || ''}</MarkdownText>
                                {s.open && <span className="inline-block w-1.5 h-4 bg-emerald-400 ml-0.5 align-middle animate-pulse" />}
                              </div>
                            );
                          }
                          if (s.kind === 'tool_building') {
                            // Only render the LATEST tool_building step (or the
                            // 'done' final one) to avoid the spammy "78ch → 90ch →
                            // 159ch" cascade that feels like text being written
                            // then deleted. Earlier in-progress steps are
                            // suppressed since they're superseded.
                            const allBuilds = (m.agent_steps || []).filter((x) => x.kind === 'tool_building');
                            const lastBuild = allBuilds[allBuilds.length - 1];
                            if (s !== lastBuild && !s.done) return null;
                            const snippet = (s.snippet || '').trim();
                            const isDone = !!s.done;
                            return (
                              <div key={sIdx} className={`rounded-lg overflow-hidden border ${
                                isDone
                                  ? 'border-emerald-400/30 bg-emerald-500/5'
                                  : 'border-cyan-400/40 bg-zinc-950/80'
                              }`}>
                                <div className={`px-3 py-1.5 text-[11px] font-bold flex items-center gap-2 ${
                                  isDone ? 'text-emerald-200' : 'text-cyan-200'
                                }`}>
                                  <span className={isDone ? '' : 'animate-pulse'}>
                                    {isDone ? '✓' : '●'}
                                  </span>
                                  <span>{s.label}</span>
                                </div>
                                {!isDone && snippet && (
                                  <pre className="px-3 pb-2 m-0 text-[10.5px] leading-snug text-cyan-100/80 overflow-hidden font-mono whitespace-pre-wrap break-all" dir="ltr" style={{ maxHeight: '5.5rem', textAlign: 'left' }}>
                                    <code>{snippet}<span className="inline-block w-1 h-3 bg-cyan-300 ml-0.5 align-middle animate-pulse" /></code>
                                  </pre>
                                )}
                              </div>
                            );
                          }
                          if (s.kind === 'tool') {
                            const isDone = s.phase === 'done';
                            // Special card renderer for `plan_task` results — checklist with REAL progress tracking.
                            if (s.name === 'plan_task' && isDone && s.result?.kind === 'plan') {
                              // Collect all update_plan_step events matching this plan_id from liveSteps
                              const planId = s.result.plan_id;
                              const stepUpdates = (m.live_steps || []).filter(
                                (x) => x.kind === 'tool' &&
                                       x.name === 'update_plan_step' &&
                                       x.phase === 'done' &&
                                       x.result?.plan_id === planId
                              ).map((x) => ({
                                step_index: x.result.step_index,
                                status: x.result.status,
                                note: x.result.note || '',
                              }));
                              return (
                                <PlanTaskCard key={sIdx} plan={s.result} updates={stepUpdates} />
                              );
                            }
                            // Hide update_plan_step from the noisy generic tool list (it updates the card silently)
                            if (s.name === 'update_plan_step') return null;
                            // Special card for audit_project
                            if (s.name === 'audit_project' && isDone && s.result?.kind === 'audit_report') {
                              return <AuditReportCard key={sIdx} report={s.result} />;
                            }
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

                    {/* AI's attached reference images (inline_images from finish() tool) */}
                    {m.role === 'assistant' && m.inline_images && m.inline_images.length > 0 && (
                      <div
                        className={`mt-3 grid gap-2 ${
                          m.inline_images.length === 1 ? 'grid-cols-1' :
                          m.inline_images.length === 2 ? 'grid-cols-2' :
                          'grid-cols-2 sm:grid-cols-3'
                        }`}
                        data-testid={`msg-inline-images-${i}`}
                      >
                        {m.inline_images.map((img, ii) => (
                          <button
                            key={ii}
                            type="button"
                            onClick={() => setLightboxAsset({ id: `inline-${i}-${ii}`, type: 'reference', image_url: img.url, prompt: img.caption || '' })}
                            data-testid={`msg-inline-image-${i}-${ii}`}
                            className="group relative rounded-xl overflow-hidden border border-white/10 hover:border-emerald-400/60 transition-all bg-zinc-900/60 text-right"
                          >
                            <div className="aspect-video bg-zinc-900 overflow-hidden">
                              <img
                                src={img.url.startsWith('http') ? img.url : `${API}${img.url}`}
                                alt={img.caption || ''}
                                loading="lazy"
                                className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                              />
                            </div>
                            {img.caption && (
                              <p className="text-[11px] text-zinc-300 p-2 line-clamp-2 leading-snug">{img.caption}</p>
                            )}
                            <div className="absolute top-1.5 left-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                              <div className="px-2 py-1 rounded-md bg-black/70 backdrop-blur text-white text-[10px] flex items-center gap-1">
                                <ZoomIn className="w-3 h-3" /> تكبير
                              </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}

                    {/* AI's attached voice clips (inline_audio from finish() tool) */}
                    {m.role === 'assistant' && m.inline_audio && m.inline_audio.length > 0 && (
                      <div className="mt-3 space-y-2" data-testid={`msg-inline-audio-list-${i}`}>
                        {m.inline_audio.map((au, ii) => (
                          <InlineAudioBubble
                            key={ii}
                            idx={`${i}-${ii}`}
                            url={au.url}
                            caption={au.caption}
                            duration_sec={au.duration_sec}
                            voice={au.voice}
                            kind={au.kind}
                            cost_estimate={au.cost_estimate}
                          />
                        ))}
                      </div>
                    )}

                    {/* AI's attached generated video clips */}
                    {m.role === 'assistant' && m.inline_video && m.inline_video.length > 0 && (
                      <div className="mt-3 space-y-2" data-testid={`msg-inline-video-list-${i}`}>
                        {m.inline_video.map((v, ii) => (
                          <InlineVideoBubble
                            key={ii}
                            idx={`${i}-${ii}`}
                            url={v.url}
                            poster_url={v.poster_url}
                            caption={v.caption}
                            duration_sec={v.duration_sec}
                            model={v.model}
                            scene_id={v.scene_id}
                            cost_usd={v.cost_usd}
                          />
                        ))}
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
              {!loading && lastTask && lastTask.label && (
                <div className="flex justify-start" data-testid="last-task-badge">
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900/60 border border-cyan-400/20 text-[10px] text-zinc-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    <span className="text-cyan-200">{lastTask.label}</span>
                    {/* Model name intentionally hidden — Zenrex presents
                        a unified branded AI experience without disclosing
                        the underlying provider. */}
                  </div>
                </div>
              )}
              {loading && (
                <div className="flex justify-start" data-testid="thinking-bubble">
                  <div className="inline-flex items-center gap-3 rounded-full pl-4 pr-3 py-1.5 bg-gradient-to-r from-cyan-500/10 via-emerald-500/10 to-cyan-500/10 border border-cyan-400/30 relative overflow-hidden">
                    {/* Animated shimmer sweep */}
                    <span className="absolute inset-0 ai-think-shimmer bg-gradient-to-r from-transparent via-cyan-400/25 to-transparent pointer-events-none" />
                    {/* Simple three-dot pulse (no branding Z in chat per UX request) */}
                    <span className="relative flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-300 animate-pulse" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-pulse" style={{ animationDelay: '180ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-300 animate-pulse" style={{ animationDelay: '360ms' }} />
                    </span>
                    <span className="text-[12px] font-semibold bg-gradient-to-r from-cyan-300 via-emerald-300 to-cyan-300 bg-clip-text text-transparent">
                      يحلل ويكتب...
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'live' && (
            <div className="flex-1 overflow-hidden bg-black/40 flex flex-col" data-testid="tab-content-live">
              {/* For video/anime/longform projects, the "live preview" shows a slideshow
                  studio (synchronized keyframes + voiceover + subtitles + watermark)
                  instead of an HTML iframe — the customer never gets a website here. */}
              {['video_studio', 'anime_studio', 'longform_video', 'image_studio'].includes(project?.mode) ? (
                <VideoStudioPreview project={project} />
              ) : (
                <>
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
                {isAppMode && (
                  <div className="self-center flex items-center gap-2 mb-1" data-testid="app-device-toggle">
                    <button
                      type="button"
                      onClick={() => setAppDevice('iphone')}
                      data-testid="device-iphone-btn"
                      className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition ${appDevice === 'iphone' ? 'bg-zinc-100 text-zinc-900 border-zinc-100' : 'bg-zinc-900 text-zinc-400 border-zinc-700 hover:border-zinc-500'}`}
                    >
                      📱 iPhone
                    </button>
                    <button
                      type="button"
                      onClick={() => setAppDevice('android')}
                      data-testid="device-android-btn"
                      className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition ${appDevice === 'android' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' : 'bg-zinc-900 text-zinc-400 border-zinc-700 hover:border-zinc-500'}`}
                    >
                      🤖 Android
                    </button>
                  </div>
                )}
                {project.current_html ? (
                  isAppMode ? (
                    /* Mobile device frame: iPhone or Android */
                    <div
                      className="self-center relative"
                      data-testid="phone-frame"
                      style={{
                        width: '390px',
                        height: '844px',
                        background: appDevice === 'iphone' ? '#1a1a1a' : '#222',
                        borderRadius: appDevice === 'iphone' ? '52px' : '32px',
                        padding: appDevice === 'iphone' ? '14px' : '10px',
                        boxShadow: '0 25px 70px rgba(0,0,0,0.6), inset 0 0 0 1.5px rgba(255,255,255,0.06)',
                      }}
                    >
                      {/* iPhone notch (Dynamic Island) */}
                      {appDevice === 'iphone' && (
                        <div
                          className="absolute left-1/2 -translate-x-1/2 z-10 rounded-full"
                          style={{ top: '22px', width: '110px', height: '32px', background: '#000' }}
                        />
                      )}
                      {/* Android top camera dot */}
                      {appDevice === 'android' && (
                        <div
                          className="absolute left-1/2 -translate-x-1/2 z-10 rounded-full"
                          style={{ top: '14px', width: '10px', height: '10px', background: '#000', border: '2px solid #333' }}
                        />
                      )}
                      <iframe
                        key={previewKey}
                        title="Live Preview"
                        data-testid="preview-iframe"
                        srcDoc={project.current_html}
                        sandbox="allow-scripts allow-same-origin"
                        className="w-full h-full bg-white"
                        style={{ borderRadius: appDevice === 'iphone' ? '40px' : '24px', border: 0 }}
                      />
                      {/* Android home bar / iPhone home indicator */}
                      <div
                        className="absolute left-1/2 -translate-x-1/2 rounded-full bg-white/40"
                        style={{
                          bottom: appDevice === 'iphone' ? '8px' : '4px',
                          width: appDevice === 'iphone' ? '130px' : '90px',
                          height: '4px',
                        }}
                      />
                    </div>
                  ) : (
                    <iframe
                      key={previewKey}
                      title="Live Preview"
                      data-testid="preview-iframe"
                      srcDoc={project.current_html}
                      sandbox="allow-scripts allow-same-origin"
                      className={`bg-white rounded-lg shadow-2xl border border-white/10 transition-all ${previewMode === 'mobile' ? 'w-[375px] self-center' : 'w-full max-w-5xl self-center'}`}
                      style={{ height: '100%', minHeight: '600px' }}
                    />
                  )
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-center">
                    <div>
                      <Code className="w-16 h-16 mx-auto mb-4 text-zinc-700" />
                      <p className="text-zinc-400 text-sm font-bold mb-1">{isAppMode ? 'لا يوجد تطبيق بعد' : 'لا يوجد HTML بعد'}</p>
                      <p className="text-zinc-600 text-xs">{isAppMode ? 'اطلب من الذكاء بناء أول شاشة من تطبيقك' : 'اطلب من الذكاء بناء صفحة كاملة في المحادثة'}</p>
                    </div>
                  </div>
                )}
              </div>
                </>
              )}
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
                  {approvedAssets.map((a) => {
                    // Detect audio assets (voiceover MP3s) and render them with a built-in player
                    const audioUrl = a.audio_url || (a.url && /\.(mp3|wav|m4a|ogg)/i.test(a.url) ? a.url : '');
                    if (audioUrl) {
                      return (
                        <div
                          key={a.id}
                          data-testid={`approved-audio-${a.id}`}
                          className="rounded-xl overflow-hidden border border-amber-500/30 bg-black/30 p-3 flex flex-col gap-2"
                        >
                          <div className="flex items-center gap-2">
                            <Mic className="w-4 h-4 text-amber-400" />
                            <p className="text-[10px] text-amber-300 font-bold">{a.type || 'voiceover'}</p>
                          </div>
                          <audio controls src={audioUrl.startsWith('http') ? audioUrl : `${API}${audioUrl}`} className="w-full h-8" />
                          <p className="text-[10px] text-zinc-400 truncate">{a.prompt || a.voice_id || ''}</p>
                        </div>
                      );
                    }
                    // Detect subtitle / script text assets
                    if (a.kind === 'script' || a.kind === 'subtitles' || a.text) {
                      return (
                        <div
                          key={a.id}
                          data-testid={`approved-text-${a.id}`}
                          className="rounded-xl overflow-hidden border border-cyan-500/30 bg-black/30 p-3 flex flex-col gap-2"
                        >
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-cyan-400" />
                            <p className="text-[10px] text-cyan-300 font-bold">{a.kind || 'text'}{a.language ? ` · ${a.language}` : ''}</p>
                          </div>
                          <div className="text-[10px] text-zinc-300 leading-relaxed max-h-32 overflow-auto whitespace-pre-wrap" dir="rtl">
                            {(a.text || a.prompt || '').slice(0, 400)}{(a.text || '').length > 400 ? '…' : ''}
                          </div>
                        </div>
                      );
                    }
                    // Default: image asset
                    return (
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
                    );
                  })}
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
                {attachments.map((file, i) => {
                  const mime = file.type || '';
                  const isImg = mime.startsWith('image/');
                  const isVid = mime.startsWith('video/');
                  const isAud = mime.startsWith('audio/');
                  const icon = isImg ? <ImageIcon className="w-3.5 h-3.5 text-emerald-300" />
                    : isVid ? <Eye className="w-3.5 h-3.5 text-violet-300" />
                    : isAud ? <FileText className="w-3.5 h-3.5 text-amber-300" />
                    : <FileText className="w-3.5 h-3.5 text-cyan-300" />;
                  const previewUrl = isImg ? URL.createObjectURL(file) : null;
                  const sizeKb = file.size / 1024;
                  const sizeLabel = sizeKb > 1024 ? `${(sizeKb / 1024).toFixed(1)}MB` : `${Math.round(sizeKb)}KB`;
                  return (
                    <div key={i} className="px-2.5 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center gap-2 text-xs">
                      {previewUrl ? (
                        <img src={previewUrl} alt="" className="w-7 h-7 object-cover rounded" onLoad={(e) => URL.revokeObjectURL(e.target.src)} />
                      ) : icon}
                      <div className="flex flex-col min-w-0">
                        <span className="text-emerald-100 max-w-[140px] truncate">{file.name}</span>
                        <span className="text-[9px] text-zinc-400">{sizeLabel}</span>
                      </div>
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
                  );
                })}
              </div>
            )}

            <div className="flex gap-2">
              {/* When out of credits, the entire input bar is replaced by the
                  Recharge banner — typing is fully disabled across the chat. */}
              {creditsBlocked ? (
                <div className="flex-1">
                  <CreditsBlockedBanner />
                </div>
              ) : (
              <>
              {/* Hidden file input — accepts images, videos, audio, PDFs, docs, code, archives.
                  The AI reads images natively (vision) and uses OCR/parsing for the rest. */}
              <input
                type="file"
                ref={fileInputRef}
                accept="image/*,video/*,audio/*,application/pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.csv,.json,.html,.css,.js,.ts,.py,.zip"
                multiple
                onChange={(e) => {
                  const newFiles = Array.from(e.target.files || []);
                  const MAX_MB = 50;
                  const tooBig = newFiles.filter((f) => f.size > MAX_MB * 1024 * 1024);
                  const okFiles = newFiles.filter((f) => f.size <= MAX_MB * 1024 * 1024);
                  if (tooBig.length) {
                    toast.error(`الحد الأقصى ${MAX_MB} ميجا — ${tooBig.length} ملف(ات) تم تخطّيها`);
                  }
                  setAttachments((prev) => [...prev, ...okFiles].slice(0, 6));
                  e.target.value = '';
                }}
                className="hidden"
                data-testid="file-input-hidden"
              />
              {/* Attach button — now supports everything (image/video/audio/file). */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
                data-testid="attach-file-btn"
                title="أرفق صورة، فيديو، صوت، PDF، Word، Excel، أو أي ملف (حتى 50 ميجا، 6 ملفات)"
                className="px-2.5 sm:px-3 py-2.5 sm:py-3 bg-white/5 hover:bg-emerald-500/20 hover:border-emerald-400/40 border border-white/10 rounded-xl transition-all text-zinc-300 hover:text-emerald-200 disabled:opacity-50 shrink-0"
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
                placeholder="اكتب رسالتك..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
                disabled={loading}
                data-testid="chat-input"
                className="min-w-0 flex-1 bg-black/40 border border-white/15 rounded-xl px-3 sm:px-4 py-2.5 sm:py-3 outline-none focus:border-emerald-400 text-sm"
              />
              {/* Send / Stop — same button morphs based on streaming state.
                  While the AI is writing, this becomes a red "Stop" button so the
                  user can interrupt instantly (saves credits if direction is wrong). */}
              {loading ? (
                <button
                  type="button"
                  onClick={stopStream}
                  data-testid="chat-stop-btn"
                  title="أوقف الذكاء الآن — لو ما عجبك التوجه نوضّح له وش تبي"
                  className="px-3 sm:px-5 py-2.5 sm:py-3 bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-400 hover:to-rose-500 text-white font-bold rounded-xl flex items-center gap-1.5 animate-pulse shadow-lg shadow-red-500/30 shrink-0"
                >
                  <span className="w-3 h-3 sm:w-3.5 sm:h-3.5 bg-white rounded-sm" />
                  <span className="text-xs hidden sm:inline">إيقاف</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={send}
                  disabled={!message.trim() && attachments.length === 0 && !replyToAsset}
                  data-testid="chat-send-btn"
                  aria-label="إرسال"
                  className="px-3 sm:px-5 py-2.5 sm:py-3 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 disabled:from-zinc-700 disabled:to-zinc-800 text-black font-bold rounded-xl flex items-center gap-1.5 shrink-0"
                >
                  <Send className="w-4 h-4 sm:w-5 sm:h-5" />
                  <span className="text-xs hidden sm:inline">إرسال</span>
                </button>
              )}
              </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Mobile-only FAB: open the phases drawer.
          Green gradient + glow so it stands out on top of the chat without
          obstructing messages. Tapping any phase auto-closes the drawer. */}
      <button
        type="button"
        onClick={() => setPhasesMobileOpen(true)}
        data-testid="open-phases-mobile"
        aria-label="المراحل والذكاء الصناعي"
        className="md:hidden fixed top-20 right-3 z-30 w-12 h-12 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/40 flex items-center justify-center hover:scale-110 active:scale-95 transition-transform"
      >
        <ChevronLeft className="w-5 h-5" />
      </button>

      {/* Mobile-only backdrop that closes the phases drawer when tapped. */}
      {phasesMobileOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-30"
          onClick={() => setPhasesMobileOpen(false)}
          data-testid="phases-mobile-backdrop"
        />
      )}

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
      <CookiesManager
        open={cookiesOpen}
        onClose={() => setCookiesOpen(false)}
      />
      <CredentialModal
        request={credentialRequest}
        value={credentialValue}
        setValue={setCredentialValue}
        submitting={credentialSubmitting}
        onClose={() => { setCredentialRequest(null); setCredentialValue(''); }}
        onSubmit={async () => {
          if (!credentialRequest || !credentialValue.trim()) return;
          setCredentialSubmitting(true);
          try {
            const token = localStorage.getItem('token');
            const fd = new FormData();
            fd.append('service', credentialRequest.service);
            fd.append('label', credentialRequest.label || credentialRequest.service);
            fd.append('value', credentialValue.trim());
            const r = await fetch(`${API}/api/freebuild-chat/project/${projectId}/credential`, {
              method: 'POST',
              headers: { Authorization: `Bearer ${token}` },
              body: fd,
            });
            if (!r.ok) {
              const t = await r.text();
              toast.error(`فشل الحفظ: ${t.slice(0, 100)}`);
              setCredentialSubmitting(false);
              return;
            }
            const savedSvc = credentialRequest.service;
            const savedLabel = credentialRequest.label || savedSvc;
            toast.success(`✅ تم حفظ ${savedLabel} (مشفّر). اكتب "كمّل" عشان الذكاء يختبره ويواصل.`);
            setCredentialRequest(null);
            setCredentialValue('');
            setCredentialSubmitting(false);
            // Pre-fill a helpful continuation message in the input
            setMessage(`تم حفظ مفتاح ${savedLabel}. اختبره الآن بـ validate_credential('${savedSvc}') وكمّل المهمة.`);
          } catch (e) {
            toast.error(`خطأ: ${e.message || e}`);
            setCredentialSubmitting(false);
          }
        }}
      />
      <InlineChoiceModal
        request={inlineChoice}
        freeText={inlineChoiceText}
        setFreeText={setInlineChoiceText}
        onClose={() => { setInlineChoice(null); setInlineChoiceText(''); }}
        onPick={(picked) => {
          if (!picked) return;
          setInlineChoice(null);
          setInlineChoiceText('');
          // Pre-fill the chat input with the user's choice so they review + send
          setMessage(picked);
          toast.info('اضغط إرسال أو عدّل قبلها.');
        }}
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
