import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import {
  Lock, Unlock, KeyRound, Send, Loader2, Plus, Trash2,
  ArrowLeft, Terminal, FileCode, FolderTree, GitBranch,
  Search, FileEdit, FilePlus, FileX, RotateCw, ShieldCheck,
  AlertTriangle, Copy, ScrollText, MessageSquare,
  Globe, Download, Layers, FilePlus2, Database, Cpu, Sparkles, Zap,
  Activity, CheckCircle2, XCircle, Rocket, PackageCheck, BrainCircuit, Gauge,
  ClipboardList, Link as LinkIcon, Lightbulb, Target, Hammer, Compass,
  CheckSquare, TimerReset, Workflow, Wand2, ExternalLink, ListChecks,
} from 'lucide-react';
import ChatInput from '../components/ChatInput';

const API = process.env.REACT_APP_BACKEND_URL;
const SESSION_KEY = 'zitex_autocoder_session';
const MODEL_KEY = 'zitex_autocoder_model';

const OWNER_MISSION_STEPS = [
  { title: 'أفهم الطلب', desc: 'ألخّص الهدف، أحدد الملفات/الخدمات، وأوضح لك وش راح أبني.', icon: Target, tone: 'amber' },
  { title: 'أنفّذ فعلياً', desc: 'أقرأ الكود، أعدل بدقة، وأعرض لك الأدوات اللي استخدمتها لحظة بلحظة.', icon: Hammer, tone: 'sky' },
  { title: 'أختبر وأثبت', desc: 'أشغّل فحوصات lint/endpoints/deploy قبل ما أقول خلصت.', icon: CheckSquare, tone: 'emerald' },
  { title: 'أعطيك خلاصة مربعة', desc: 'روابط، نواقص، اقتراحات، المطلوب منك، وخطوة التطوير التالية.', icon: ClipboardList, tone: 'violet' },
];

const OWNER_QUICK_PROMPTS = [
  'افحص نفسك كـ AutoCoder وطلع لي تقرير نواقصك وقدراتك وخطة ترقيتك القادمة',
  'رتّب لي خطة تطوير قسم برمجة زيتاكس لمدة أسبوع بالأولويات والروابط المطلوبة',
  'اعمل health check شامل للمنصة ثم أعطني خلاصة مربعة بما يحتاجه Zitex الآن',
  'اقترح تحسين واجهة جديدة للمالك ثم نفّذها واختبرها وانشرها',
];

function toneClasses(tone) {
  const map = {
    amber: 'from-amber-500/20 to-amber-500/5 border-amber-400/25 text-amber-200',
    sky: 'from-sky-500/20 to-sky-500/5 border-sky-400/25 text-sky-200',
    emerald: 'from-emerald-500/20 to-emerald-500/5 border-emerald-400/25 text-emerald-200',
    violet: 'from-violet-500/20 to-violet-500/5 border-violet-400/25 text-violet-200',
    rose: 'from-rose-500/20 to-rose-500/5 border-rose-400/25 text-rose-200',
  };
  return map[tone] || map.amber;
}

function extractUrls(text = '') {
  const urls = String(text).match(/https?:\/\/[^\s)\]}<>"']+/g) || [];
  return [...new Set(urls.map((u) => u.replace(/[.,،]+$/, '')))].slice(0, 8);
}

function pickLines(text = '', keywords = [], limit = 4) {
  const lines = String(text).split('\n').map((l) => l.replace(/^[-*•\d.)\s]+/, '').trim()).filter(Boolean);
  const picked = [];
  for (const line of lines) {
    if (keywords.some((k) => line.includes(k)) && !picked.includes(line)) picked.push(line);
    if (picked.length >= limit) break;
  }
  return picked;
}

function buildMessageInsights(message) {
  const text = message?.content || '';
  const tools = message?.tool_events || [];
  const failedTools = tools.filter((t) => t.ok === false).length;
  const callingTools = tools.filter((t) => t.status === 'calling').length;
  const okTools = tools.filter((t) => t.ok !== false && t.status !== 'calling').length;
  return {
    urls: extractUrls(text),
    needed: pickLines(text, ['أحتاج', 'المطلوب', 'أرسل', 'زودني', 'ناقص', 'نحتاج'], 5),
    suggestions: pickLines(text, ['اقتراح', 'أنصح', 'الأفضل', 'المرحلة', 'الخطوة القادمة', 'نقدر'], 5),
    warnings: pickLines(text, ['تحذير', 'تنبيه', 'خطر', 'مهم', '⚠️'], 3),
    okTools, failedTools, callingTools, toolCount: tools.length,
    status: message?.error ? 'error' : failedTools > 0 ? 'warning' : callingTools > 0 ? 'working' : 'ready',
  };
}

const TOOL_ICON = {
  list_dir: FolderTree,
  read_file: FileCode,
  write_file: FilePlus,
  edit_file: FileEdit,
  delete_file: FileX,
  search_code: Search,
  run_command: Terminal,
  restart_service: RotateCw,
  git_status: GitBranch,
  git_diff: GitBranch,
  git_commit_push: GitBranch,
  view_logs: ScrollText,
  list_env: KeyRound,
  pre_deploy_check: ShieldCheck,
  check_deployment_status: ShieldCheck,
  rollback_to_last_good: RotateCw,
  // New power tools
  web_search: Globe,
  fetch_url: Download,
  view_bulk_files: Layers,
  apply_patch: FilePlus2,
  db_query: Database,
  ast_analyze: Cpu,
};

const TOOL_LABEL = {
  list_dir: 'قائمة مجلد',
  read_file: 'قراءة ملف',
  write_file: 'كتابة ملف',
  edit_file: 'تعديل ملف',
  delete_file: 'حذف ملف',
  search_code: 'بحث في الكود',
  run_command: 'تنفيذ أمر',
  restart_service: 'إعادة تشغيل خدمة',
  git_status: 'git status',
  git_diff: 'git diff',
  git_commit_push: 'commit + push',
  view_logs: 'عرض السجلات',
  list_env: 'متغيرات البيئة',
  pre_deploy_check: 'فحص قبل النشر',
  check_deployment_status: 'حالة النشر',
  rollback_to_last_good: 'استرجاع لآخر إصدار شغّال',
  // New power tools
  web_search: 'بحث في الإنترنت',
  fetch_url: 'جلب URL',
  view_bulk_files: 'قراءة عدة ملفات',
  apply_patch: 'تطبيق patch',
  db_query: 'استعلام قاعدة البيانات',
  ast_analyze: 'تحليل AST',
};

const MODEL_OPTIONS = [
  { id: 'auto', label: '🤖 موجّه الجودة (موصى)', cost: 'يختار أعلى جودة متاحة تلقائياً', tone: 'amber', icon: Zap },
  { id: 'claude', label: 'Claude Sonnet 4.5 (الأذكى)', cost: 'Premium — Q10', tone: 'amber', icon: Sparkles },
  { id: 'openai', label: 'GPT-5.5 (الأقوى)', cost: 'Premium — Q10', tone: 'violet', icon: Sparkles },
  { id: 'gemini', label: 'Gemini 3 Pro (سياق طويل)', cost: 'Premium — Q9-10', tone: 'sky', icon: Sparkles },
  { id: 'deepseek', label: 'DeepSeek V3 (🇨🇳 reasoning)', cost: 'Strong — Q8-9', tone: 'emerald', icon: Sparkles },
  { id: 'kimi', label: 'Kimi K2 (🇨🇳 عربي طبيعي)', cost: 'Strong — Q8-9', tone: 'sky', icon: Sparkles },
];

// Map common backend error messages to friendlier guidance
function humanizeAutocoderError(raw) {
  const s = String(raw || '').toLowerCase();
  if (s.includes('credit_balance_too_low') || s.includes('insufficient_quota') || s.includes('billing')) {
    return 'رصيد Anthropic منخفض. حلّ سريع: بدّل الموديل من الأعلى إلى Llama 3.3 (Groq) — مجاني وسريع.';
  }
  if (s.includes('rate_limit') || s.includes('429') || s.includes('tpm') || s.includes('rpm')) {
    return 'تجاوزت حدّ الطلبات لحظياً. استنّى ~30 ثانية وجرّب من جديد، أو بدّل الموديل.';
  }
  if (s.includes('groq_api_key غير') || s.includes('gemini_api_key غير')) {
    return raw; // already in Arabic, descriptive
  }
  if (s.includes('groq') && s.includes('limit 12000')) {
    return 'الـsystem prompt كبير على Groq Free Tier. ارفع لـDev Tier (مجاني، يحتاج بطاقة فقط) من console.groq.com/settings/billing، أو استخدم Claude.';
  }
  if (s.includes('overloaded') || s.includes('503')) {
    return 'الخادم مزدحم لحظياً. حاول مرة ثانية بعد دقيقة.';
  }
  if (s.includes('session locked')) {
    return 'انتهت الجلسة (4 ساعات). افتح القفل من جديد بكلمة السر.';
  }
  return `خطأ من الخادم: ${raw}`;
}

export default function AdminAutoCoder() {
  const nav = useNavigate();
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const [phase, setPhase] = useState('loading'); // loading | setup | locked | unlocked
  const [acToken, setAcToken] = useState(null);
  const [acExpiresAt, setAcExpiresAt] = useState(null);

  // setup state
  const [setupPasscode, setSetupPasscode] = useState('');
  const [setupConfirm, setSetupConfirm] = useState('');
  const [setupBusy, setSetupBusy] = useState(false);
  const [generatedRecovery, setGeneratedRecovery] = useState(null);

  // unlock state
  const [unlockPasscode, setUnlockPasscode] = useState('');
  const [unlockBusy, setUnlockBusy] = useState(false);
  const [showRecover, setShowRecover] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState('');
  const [recoveryNewPass, setRecoveryNewPass] = useState('');
  const [recoveryBusy, setRecoveryBusy] = useState(false);

  // chat state
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [currentStream, setCurrentStream] = useState('');
  const [currentTools, setCurrentTools] = useState([]);
  const [showSidebar, setShowSidebar] = useState(false);
  const [keyStatus, setKeyStatus] = useState(null);
  const [model, setModel] = useState(() => {
    if (typeof window === 'undefined') return 'auto';
    return localStorage.getItem(MODEL_KEY) || 'auto';
  });
  const [showModelMenu, setShowModelMenu] = useState(false);

  // AutoCoder capability command center
  const [metaReport, setMetaReport] = useState(null);
  const [roadmap, setRoadmap] = useState(null);
  const [metaLoading, setMetaLoading] = useState(false);
  const [showMetaPanel, setShowMetaPanel] = useState(true);

  // Voice recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);
  const recordingCancelledRef = useRef(false);

  const scrollRef = useRef(null);

  // ---- bootstrap ----
  useEffect(() => {
    if (!token) { nav('/login'); return; }
    bootstrap();
    // eslint-disable-next-line
  }, []);

  const bootstrap = async () => {
    try {
      const r = await fetch(`${API}/api/autocoder/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.status === 403) {
        toast.error('هذا القسم للمالك فقط');
        nav('/dashboard'); return;
      }
      if (!r.ok) throw new Error('status failed');
      const d = await r.json();
      if (!d.is_setup) { setPhase('setup'); return; }
      // load key status (independent or fallback)
      loadKeyStatus();
      // try restore session
      try {
        const stored = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
        if (stored && stored.token && stored.expires_at) {
          if (new Date(stored.expires_at) > new Date()) {
            setAcToken(stored.token);
            setAcExpiresAt(stored.expires_at);
            setPhase('unlocked');
            loadConversations(stored.token);
            setTimeout(() => loadMetaReport(), 0);
            return;
          }
          localStorage.removeItem(SESSION_KEY);
        }
      } catch (_) {}
      setPhase('locked');
    } catch (e) {
      toast.error('فشل تحميل الحالة');
      setPhase('locked');
    }
  };

  // ---- key status ----
  const loadKeyStatus = async () => {
    try {
      const r = await fetch(`${API}/api/autocoder/key-status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) setKeyStatus(await r.json());
    } catch (_) {}
  };

  // ---- setup ----
  const doSetup = async () => {
    if (setupPasscode.length < 6) { toast.error('كلمة السر 6 أحرف على الأقل'); return; }
    if (setupPasscode !== setupConfirm) { toast.error('كلمتا السر غير متطابقتين'); return; }
    setSetupBusy(true);
    try {
      const r = await fetch(`${API}/api/autocoder/setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ passcode: setupPasscode }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'setup failed');
      setGeneratedRecovery(d.recovery_codes);
      toast.success('تم الإعداد. احفظ رموز الاسترجاع!');
    } catch (e) {
      toast.error(e.message);
    } finally { setSetupBusy(false); }
  };

  const finishSetupAfterRecovery = () => {
    setGeneratedRecovery(null);
    setSetupPasscode('');
    setSetupConfirm('');
    setPhase('locked');
  };

  // ---- unlock ----
  const doUnlock = async () => {
    if (!unlockPasscode) return;
    setUnlockBusy(true);
    try {
      const r = await fetch(`${API}/api/autocoder/unlock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ passcode: unlockPasscode }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'unlock failed');
      setAcToken(d.session_token);
      setAcExpiresAt(d.expires_at);
      localStorage.setItem(SESSION_KEY, JSON.stringify({
        token: d.session_token, expires_at: d.expires_at,
      }));
      setUnlockPasscode('');
      setPhase('unlocked');
      toast.success('تم فتح القفل');
      loadConversations(d.session_token);
      setTimeout(() => loadMetaReport(), 0);
    } catch (e) {
      toast.error('كلمة السر خاطئة');
    } finally { setUnlockBusy(false); }
  };

  const doRecover = async () => {
    if (!recoveryCode || recoveryNewPass.length < 6) { toast.error('املأ الحقول'); return; }
    setRecoveryBusy(true);
    try {
      const r = await fetch(`${API}/api/autocoder/recover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ recovery_code: recoveryCode.trim().toUpperCase(), new_passcode: recoveryNewPass }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'recover failed');
      toast.success('تم استرجاع الوصول. سجّل دخول بكلمة السر الجديدة');
      if (d.new_recovery_codes && d.new_recovery_codes.length) {
        setGeneratedRecovery(d.new_recovery_codes);
      }
      setShowRecover(false);
      setRecoveryCode('');
      setRecoveryNewPass('');
    } catch (e) {
      toast.error('رمز استرجاع غير صالح');
    } finally { setRecoveryBusy(false); }
  };

  const doEmergencyReset = async () => {
    if (!window.confirm('سيتم مسح كل إعدادات برمجة زيتاكس (كلمة السر + رموز الاسترجاع + الجلسات). بعدها ترجع لصفحة الإعداد لتختار كلمة سر جديدة. متأكد؟')) return;
    try {
      const r = await fetch(`${API}/api/autocoder/emergency-reset`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error('failed');
      localStorage.removeItem(SESSION_KEY);
      toast.success('تم المسح. أعد تحميل الصفحة');
      setTimeout(() => window.location.reload(), 1000);
    } catch (e) { toast.error('فشل المسح'); }
  };

  const doLock = async () => {
    try {
      await fetch(`${API}/api/autocoder/lock`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'X-AutoCoder-Token': acToken || '',
        },
      });
    } catch (_) {}
    localStorage.removeItem(SESSION_KEY);
    setAcToken(null);
    setMessages([]);
    setConversationId(null);
    setPhase('locked');
    toast.success('تم القفل');
  };

  // ---- chat ----
  const loadConversations = async (tk) => {
    try {
      const r = await fetch(`${API}/api/autocoder/conversations`, {
        headers: { Authorization: `Bearer ${token}`, 'X-AutoCoder-Token': tk || acToken || '' },
      });
      const d = await r.json();
      setConversations(d.conversations || []);
    } catch (_) {}
  };

  const loadMetaReport = async () => {
    if (!token) return;
    setMetaLoading(true);
    try {
      const [capRes, roadRes] = await Promise.all([
        fetch(`${API}/api/autocoder-meta/capabilities`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/api/autocoder-meta/roadmap`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      const capData = await capRes.json();
      const roadData = await roadRes.json();
      if (!capRes.ok) throw new Error(capData.detail || 'capabilities failed');
      if (!roadRes.ok) throw new Error(roadData.detail || 'roadmap failed');
      setMetaReport(capData);
      setRoadmap(roadData);
    } catch (e) {
      console.warn('AutoCoder meta load failed', e);
      toast.error('تعذر تحميل لوحة القدرات');
    } finally {
      setMetaLoading(false);
    }
  };

  const loadConversation = async (cid) => {
    try {
      const r = await fetch(`${API}/api/autocoder/conversation/${cid}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      setMessages(d.messages || []);
      setConversationId(cid);
      setShowSidebar(false);
    } catch (e) { toast.error('فشل التحميل'); }
  };

  const newChat = () => {
    setMessages([]);
    setConversationId(null);
    setCurrentStream('');
    setCurrentTools([]);
    setShowSidebar(false);
  };

  const deleteConversation = async (cid) => {
    if (!window.confirm('احذف هذه المحادثة؟')) return;
    try {
      await fetch(`${API}/api/autocoder/conversation/${cid}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
      });
      if (cid === conversationId) newChat();
      loadConversations();
    } catch (_) {}
  };

  // ─────────────────────────────────────────────────
  // 🎤 Voice recording (uses /api/autocoder/transcribe → Whisper)
  // ─────────────────────────────────────────────────
  const startRecording = async () => {
    if (isRecording || transcribing) return;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      toast.error('متصفحك ما يدعم تسجيل الصوت');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Pick a supported mimeType
      let mimeType = 'audio/webm;codecs=opus';
      if (!window.MediaRecorder?.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm';
        if (!window.MediaRecorder?.isTypeSupported(mimeType)) {
          mimeType = 'audio/mp4'; // Safari
        }
      }
      const mr = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      audioChunksRef.current = [];
      recordingCancelledRef.current = false;
      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mr.onstop = async () => {
        // Stop all tracks
        try { stream.getTracks().forEach((t) => t.stop()); } catch (_) {}
        if (recordingCancelledRef.current) {
          audioChunksRef.current = [];
          return;
        }
        const blob = new Blob(audioChunksRef.current, { type: mr.mimeType || 'audio/webm' });
        audioChunksRef.current = [];
        if (blob.size < 800) {
          toast.error('التسجيل قصير جداً');
          return;
        }
        await transcribeAudio(blob);
      };
      mr.start();
      mediaRecorderRef.current = mr;
      setIsRecording(true);
      setRecordingSeconds(0);
      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds((s) => {
          if (s >= 60) {
            // auto-stop at 60s
            stopRecording();
            return s;
          }
          return s + 1;
        });
      }, 1000);
    } catch (e) {
      console.error(e);
      if (e.name === 'NotAllowedError') {
        toast.error('رفضت إذن استخدام الميكروفون. اسمح من إعدادات المتصفح');
      } else {
        toast.error('تعذّر بدء التسجيل: ' + e.message);
      }
    }
  };

  const stopRecording = () => {
    if (!isRecording) return;
    setIsRecording(false);
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
    } catch (_) {}
  };

  const cancelRecording = () => {
    recordingCancelledRef.current = true;
    stopRecording();
    setRecordingSeconds(0);
    toast.info('تم إلغاء التسجيل');
  };

  const transcribeAudio = async (blob) => {
    setTranscribing(true);
    try {
      const fd = new FormData();
      const ext = blob.type.includes('mp4') ? 'mp4' : 'webm';
      fd.append('file', blob, `voice.${ext}`);
      const r = await fetch(`${API}/api/autocoder/transcribe`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'X-AutoCoder-Token': acToken || '',
        },
        body: fd,
      });
      const d = await r.json();
      if (!r.ok || !d.success) {
        throw new Error(d.detail || 'transcription failed');
      }
      const text = (d.text || '').trim();
      if (!text) {
        toast.error('ما لقينا كلام في التسجيل');
        return;
      }
      // Append to existing input rather than replace
      setInput((prev) => (prev ? `${prev} ${text}` : text));
      toast.success('تم التحويل لنص');
    } catch (e) {
      toast.error('فشل التحويل: ' + (e.message || ''));
    } finally {
      setTranscribing(false);
      setRecordingSeconds(0);
    }
  };

  const send = async (payload = null) => {
    // Support both ChatInput onSend({text, files}) and legacy direct call
    let msg, attachedFiles;
    if (payload && typeof payload === 'object') {
      msg = (payload.text || '').trim();
      attachedFiles = payload.files || [];
    } else {
      msg = input.trim();
      attachedFiles = [];
    }
    if ((!msg && attachedFiles.length === 0) || sending) return;
    setInput('');
    setSending(true);
    setMessages((prev) => [...prev, {
      role: 'user',
      content: msg,
      attachments: (attachedFiles || []).map((f) => ({
        name: f.name,
        type: f.type,
        size: f.size,
        previewUrl: f.type?.startsWith('image/') ? URL.createObjectURL(f) : '',
      })),
    }]);
    setCurrentStream('');
    setCurrentTools([]);
    let lastTurnCost = null;

    try {
      // Backend now uses multipart/form-data (to support file attachments)
      const fd = new FormData();
      fd.append('message', msg);
      if (conversationId) fd.append('conversation_id', conversationId);
      fd.append('model', model || 'claude');

      // Attach files from ChatInput (if any)
      if (attachedFiles && attachedFiles.length > 0) {
        attachedFiles.forEach((f) => {
          fd.append('attachments', f);
        });
      }

      const r = await fetch(`${API}/api/autocoder/chat`, {
        method: 'POST',
        headers: {
          // NOTE: do NOT set Content-Type — fetch sets it automatically with the multipart boundary
          Authorization: `Bearer ${token}`,
          'X-AutoCoder-Token': acToken,
        },
        body: fd,
      });
      if (r.status === 401) {
        toast.error('انتهت الجلسة. ادخل كلمة السر مرة ثانية');
        localStorage.removeItem(SESSION_KEY);
        setPhase('locked');
        return;
      }
      // If response is not ok and no SSE was produced, surface backend error explicitly
      if (!r.ok && !r.body) {
        let bodyText = '';
        try { bodyText = (await r.text()).slice(0, 400); } catch (_) {}
        throw new Error(`الخادم رفض الطلب (HTTP ${r.status}). ${bodyText}`);
      }
      if (!r.body) throw new Error('no stream');
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let assistantText = '';
      let toolEvents = [];
      let serverError = null;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';
        for (const part of parts) {
          if (!part.startsWith('data: ')) continue;
          try {
            const evt = JSON.parse(part.slice(6));
            if (evt.type === 'text') {
              assistantText += evt.content;
              setCurrentStream(assistantText);
            } else if (evt.type === 'tool') {
              toolEvents.push(evt);
              setCurrentTools([...toolEvents]);
            } else if (evt.type === 'saved') {
              setConversationId(evt.conversation_id);
              if (evt.turn_cost !== undefined) {
                lastTurnCost = evt.turn_cost;
                if (evt.turn_cost >= 0.01) {
                  toast.success(`💰 تكلفة هذه الرسالة: $${evt.turn_cost.toFixed(4)}`, { duration: 4000 });
                }
              }
              loadConversations();
            } else if (evt.type === 'auto_route') {
              // Smart Router decided which provider to use
              toolEvents.push({ ...evt, _isAutoRoute: true });
              setCurrentTools([...toolEvents]);
              toast.success(`🤖 Auto: ${evt.task} → ${evt.provider}`, { duration: 3500, description: evt.reason });
            } else if (evt.type === 'usage') {
              // Real-time cost update — append to current tools list as a special pill
              setCurrentTools((prev) => [...prev, { ...evt, _isUsage: true }]);
              toolEvents.push({ ...evt, _isUsage: true });
            } else if (evt.type === 'error') {
              serverError = evt.message || 'حصل خطأ غير محدد';
              toast.error(serverError, { duration: 7000 });
            }
          } catch (_) {}
        }
      }

      // If we got an error and no actual content, show it inline so user understands what happened
      if (serverError && !assistantText) {
        const friendly = humanizeAutocoderError(serverError);
        assistantText = `⚠️ ${friendly}`;
      }

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: assistantText, tool_events: toolEvents, error: serverError },
      ]);
      setCurrentStream('');
      setCurrentTools([]);
    } catch (e) {
      toast.error('خطأ في الشبكة: ' + e.message);
    } finally { setSending(false); }
  };

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, currentStream, currentTools]);

  // ════════════════════════════════════════════════════════════════════
  // Render gates
  // ════════════════════════════════════════════════════════════════════
  if (phase === 'loading') {
    return (
      <div className="min-h-screen bg-[#050505] text-white flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-amber-400" />
      </div>
    );
  }

  if (generatedRecovery) {
    return (
      <RecoveryDisplay
        codes={generatedRecovery}
        onDone={phase === 'setup' ? finishSetupAfterRecovery : () => setGeneratedRecovery(null)}
      />
    );
  }

  if (phase === 'setup') {
    return (
      <LockShell title="إعداد قسم برمجة زيتاكس">
        <div className="text-amber-300/80 text-xs mb-4 leading-relaxed">
          هذا أول دخول لك. ضع كلمة سر قوية. سنولّد لك 6 رموز استرجاع لاستخدامها لو نسيت كلمة السر.
        </div>
        <input
          type="password"
          value={setupPasscode}
          onChange={(e) => setSetupPasscode(e.target.value)}
          placeholder="كلمة السر (6 أحرف على الأقل)"
          data-testid="setup-passcode"
          className="w-full bg-black/40 border border-white/15 rounded-lg px-4 py-3 mb-3 text-sm focus:border-amber-400 outline-none"
        />
        <input
          type="password"
          value={setupConfirm}
          onChange={(e) => setSetupConfirm(e.target.value)}
          placeholder="تأكيد كلمة السر"
          data-testid="setup-confirm"
          className="w-full bg-black/40 border border-white/15 rounded-lg px-4 py-3 mb-4 text-sm focus:border-amber-400 outline-none"
        />
        <button
          onClick={doSetup}
          disabled={setupBusy}
          data-testid="setup-submit"
          className="w-full py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {setupBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
          إنشاء الحماية
        </button>
      </LockShell>
    );
  }

  if (phase === 'locked') {
    return (
      <LockShell title="برمجة زيتاكس">
        {!showRecover ? (
          <>
            <div className="text-amber-300/70 text-xs mb-4 leading-relaxed">
              قسم خاص بك بس. أدخل كلمة السر للدخول.
            </div>
            <input
              type="password"
              value={unlockPasscode}
              onChange={(e) => setUnlockPasscode(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && doUnlock()}
              placeholder="كلمة السر"
              data-testid="unlock-passcode"
              autoFocus
              className="w-full bg-black/40 border border-white/15 rounded-lg px-4 py-3 mb-3 text-sm focus:border-amber-400 outline-none"
            />
            <button
              onClick={doUnlock}
              disabled={unlockBusy}
              data-testid="unlock-submit"
              className="w-full py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {unlockBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Unlock className="w-4 h-4" />}
              دخول
            </button>
            <button
              onClick={() => setShowRecover(true)}
              data-testid="recover-link"
              className="w-full mt-3 text-amber-300/70 hover:text-amber-300 text-xs"
            >
              نسيت كلمة السر؟ استخدم رمز استرجاع
            </button>
          </>
        ) : (
          <>
            <div className="text-amber-300/70 text-xs mb-4 leading-relaxed">
              ادخل أحد رموز الاسترجاع الـ6 (يستخدم مرة واحدة) + كلمة سر جديدة.
            </div>
            <input
              type="text"
              value={recoveryCode}
              onChange={(e) => setRecoveryCode(e.target.value.toUpperCase())}
              placeholder="رمز الاسترجاع (مثال: ABCD-1234-EF56-7890)"
              data-testid="recovery-code"
              className="w-full bg-black/40 border border-white/15 rounded-lg px-4 py-3 mb-3 text-sm font-mono focus:border-amber-400 outline-none"
            />
            <input
              type="password"
              value={recoveryNewPass}
              onChange={(e) => setRecoveryNewPass(e.target.value)}
              placeholder="كلمة السر الجديدة"
              data-testid="recovery-new-passcode"
              className="w-full bg-black/40 border border-white/15 rounded-lg px-4 py-3 mb-4 text-sm focus:border-amber-400 outline-none"
            />
            <button
              onClick={doRecover}
              disabled={recoveryBusy}
              data-testid="recover-submit"
              className="w-full py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {recoveryBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
              استرجاع
            </button>
            <button
              onClick={() => setShowRecover(false)}
              className="w-full mt-3 text-white/50 hover:text-white text-xs"
            >
              رجوع
            </button>
            <div className="mt-6 pt-4 border-t border-white/10">
              <p className="text-[11px] text-rose-300/70 mb-2 leading-relaxed">
                ⚠️ ضايعة كلمة السر و الرموز ما تنفع؟ أنت المالك، تقدر تمسح كل شي وتبدأ من جديد:
              </p>
              <button
                onClick={doEmergencyReset}
                data-testid="emergency-reset-btn"
                className="w-full py-2 rounded-lg bg-rose-500/15 border border-rose-400/30 hover:bg-rose-500/25 text-rose-300 text-xs font-bold"
              >
                🚨 مسح كل الإعدادات والبدء من جديد
              </button>
            </div>
          </>
        )}
      </LockShell>
    );
  }

  // ════════════════════════════════════════════════════════════════════
  // Unlocked: full chat shell
  // ════════════════════════════════════════════════════════════════════
  return (
    <div dir="rtl" className="h-screen bg-[#050505] text-white flex flex-col overflow-hidden">
      <Toaster richColors position="top-center" />

      <header className="h-14 px-3 md:px-4 border-b border-amber-500/20 flex items-center justify-between bg-black/60 backdrop-blur z-20 flex-shrink-0">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSidebar((s) => !s)}
            data-testid="ac-toggle-sidebar"
            className="md:hidden p-2 hover:bg-white/5 rounded"
          >
            <MessageSquare className="w-4 h-4" />
          </button>
          <button onClick={() => nav('/admin')} className="p-1.5 hover:bg-white/5 rounded">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h1 className="font-black text-sm flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-amber-400" /> برمجة زيتاكس
            <span className="text-[10px] text-amber-300/60 font-normal me-1">(Owner Only)</span>
          </h1>
          <div className="hidden md:flex items-center gap-1 me-3 ms-2 border-s border-amber-500/20 ps-3">
            <button
              onClick={() => nav('/admin/api-keys')}
              data-testid="ac-link-keys"
              title="مفاتيح الذكاء الصناعي والرصيد"
              className="px-2 py-1 rounded text-[11px] bg-zinc-800/60 hover:bg-zinc-700 text-zinc-300 hover:text-amber-300 flex items-center gap-1"
            >
              <ShieldCheck className="w-3 h-3" /> المفاتيح
            </button>
            <button
              onClick={() => nav('/admin/sections')}
              data-testid="ac-link-sections"
              title="مركز الأقسام الذكية"
              className="px-2 py-1 rounded text-[11px] bg-zinc-800/60 hover:bg-zinc-700 text-zinc-300 hover:text-amber-300 flex items-center gap-1"
            >
              <Layers className="w-3 h-3" /> الأقسام
            </button>
            <button
              onClick={() => nav('/admin/quality-router')}
              data-testid="ac-link-quality"
              title="موجّه الجودة"
              className="px-2 py-1 rounded text-[11px] bg-zinc-800/60 hover:bg-zinc-700 text-zinc-300 hover:text-amber-300 flex items-center gap-1"
            >
              <Sparkles className="w-3 h-3" /> موجّه الجودة
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ModelSelector
            value={model}
            onChange={(m) => {
              setModel(m);
              localStorage.setItem(MODEL_KEY, m);
              setShowModelMenu(false);
            }}
            open={showModelMenu}
            setOpen={setShowModelMenu}
            keyStatus={keyStatus}
          />
          <SessionTimer expiresAt={acExpiresAt} />
          <button
            onClick={() => {
              setShowMetaPanel((v) => !v);
              if (!metaReport && !metaLoading) loadMetaReport();
            }}
            data-testid="ac-meta-toggle"
            className={`hidden sm:inline-flex px-3 py-1.5 rounded-md text-xs font-bold items-center gap-1 border transition ${showMetaPanel ? 'bg-sky-500/15 border-sky-400/30 text-sky-200' : 'bg-white/5 border-white/10 text-white/70 hover:text-white'}`}
          >
            <Gauge className="w-3.5 h-3.5" /> مركز القدرات
          </button>
          <button
            onClick={newChat}
            data-testid="ac-new-chat"
            className="px-3 py-1.5 rounded-md bg-amber-500 text-black text-xs font-bold flex items-center gap-1 hover:bg-amber-400"
          >
            <Plus className="w-3.5 h-3.5" /> جديدة
          </button>
          <button
            onClick={doLock}
            data-testid="ac-lock"
            title="قفل القسم"
            className="px-2 py-1.5 rounded-md bg-rose-500/20 text-rose-300 text-xs hover:bg-rose-500/30 flex items-center gap-1"
          >
            <Lock className="w-3.5 h-3.5" /> قفل
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside
          className={`${showSidebar ? 'flex' : 'hidden md:flex'} flex-col w-64 border-e border-white/10 bg-black/30 flex-shrink-0`}
        >
          <div className="p-2 border-b border-white/10 text-[10px] uppercase tracking-widest text-white/40">
            المحادثات
          </div>
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
            {conversations.length === 0 ? (
              <div className="text-center text-white/40 text-xs p-4">لا توجد بعد</div>
            ) : conversations.map((c) => (
              <div
                key={c.id}
                data-testid={`ac-conv-${c.id}`}
                onClick={() => loadConversation(c.id)}
                className={`group p-2 rounded-lg cursor-pointer flex items-start gap-2 text-xs transition ${conversationId === c.id ? 'bg-amber-500/15 border border-amber-400/30' : 'hover:bg-white/5'}`}
              >
                <MessageSquare className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 opacity-60" />
                <span className="flex-1 line-clamp-2 leading-snug">{c.preview || 'محادثة'}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteConversation(c.id); }}
                  className="opacity-0 group-hover:opacity-100 text-rose-400 hover:text-rose-300"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </aside>

        <main className="flex-1 flex flex-col min-w-0">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
            <OwnerMissionPanel
              metaReport={metaReport}
              roadmap={roadmap}
              metaLoading={metaLoading}
              messagesCount={messages.length}
              onPrompt={(text) => setInput(text)}
              onRefresh={loadMetaReport}
            />

            {keyStatus && !keyStatus.is_independent && (
              <div data-testid="ac-fallback-warning" className="max-w-3xl mx-auto bg-amber-500/10 border border-amber-400/30 rounded-xl p-4 text-xs text-amber-200 leading-relaxed">
                <div className="font-bold mb-1 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  تنبيه: الذكاء يستخدم مفتاح Emergent — تنخصم نقاط من حسابك
                </div>
                <div className="text-amber-200/80">
                  لجعل الذكاء مستقلاً 100% (بدون أي خصم نقاط)، أضف <code className="px-1 py-0.5 bg-black/40 rounded font-mono text-[11px]">ANTHROPIC_API_KEY</code> في إعدادات Railway → Variables. شوف الدليل في <code className="px-1 py-0.5 bg-black/40 rounded font-mono text-[11px]">/app/INDEPENDENCE_SETUP.md</code> داخل الكود.
                </div>
              </div>
            )}
            {showMetaPanel && (
              <AutoCoderCommandCenter
                report={metaReport}
                roadmap={roadmap}
                loading={metaLoading}
                onRefresh={loadMetaReport}
              />
            )}

            {messages.length === 0 && !currentStream && (
              <WelcomePromptBoard onPrompt={(text) => setInput(text)} />
            )}

            {messages.map((m, i) => <MessageBubble key={i} m={m} />)}

            {(currentStream || currentTools.length > 0) && (
              <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-4 max-w-3xl">
                <div className="text-[10px] uppercase tracking-widest text-amber-400/80 mb-2">برمجة زيتاكس</div>
                {currentTools.map((t, i) => <ToolPill key={i} t={t} />)}
                {currentStream && <div className="text-sm leading-relaxed whitespace-pre-wrap mt-2">{currentStream}</div>}
              </div>
            )}
          </div>

          <div className="border-t border-white/10 p-3 md:p-4 bg-black/40">
            <div className="max-w-3xl mx-auto">
              <ChatInput
                value={input}
                onChange={setInput}
                onSend={send}
                placeholder="اكتب أمرك للذكاء... أو اضغط الميكروفون لتسجل بصوتك"
                disabled={sending}
                supportFiles={true}
                supportVoice={true}
                supportEmojis={true}
              />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════
// Sub-components
// ════════════════════════════════════════════════════════════════════════

function OwnerMissionPanel({ metaReport, roadmap, metaLoading, messagesCount, onPrompt, onRefresh }) {
  const capabilities = metaReport?.capabilities || metaReport?.summary?.capabilities || [];
  const roadmapItems = roadmap?.phases || roadmap?.items || roadmap?.roadmap || [];
  const visibleCapabilities = Array.isArray(capabilities) ? capabilities.slice(0, 4) : [];
  const firstRoadmap = Array.isArray(roadmapItems) ? roadmapItems[0] : null;
  return (
    <section data-testid="ac-owner-mission-panel" className="max-w-6xl mx-auto rounded-3xl border border-amber-400/20 bg-[radial-gradient(circle_at_top_right,rgba(245,158,11,0.16),transparent_35%),linear-gradient(135deg,rgba(24,24,27,0.92),rgba(3,7,18,0.92))] shadow-2xl shadow-amber-950/20 overflow-hidden">
      <div className="p-5 md:p-6 border-b border-white/10 flex flex-col lg:flex-row gap-5 lg:items-center lg:justify-between">
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-2xl bg-amber-500 text-black flex items-center justify-center shadow-lg shadow-amber-500/20"><Wand2 className="w-7 h-7" /></div>
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1"><h2 className="text-xl md:text-2xl font-black">غرفة قيادة برمجة زيتاكس</h2><span className="text-[10px] px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-400/20 text-emerald-300">Owner AI Command</span></div>
            <p className="text-sm text-white/65 leading-relaxed max-w-2xl">هذه الصفحة صارت مخصصة لتطويري أنا: أفهم طلبك، أعرض خطوات التنفيذ، أوضح الأدوات، وأرتّب لك في النهاية خلاصة مربعة فيها الروابط والنواقص والاقتراحات.</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 min-w-[260px]">
          <MiniMetric label="المحادثات" value={messagesCount || 0} icon={MessageSquare} tone="amber" />
          <MiniMetric label="القدرات" value={visibleCapabilities.length || '—'} icon={BrainCircuit} tone="sky" />
          <button onClick={onRefresh} data-testid="ac-refresh-command" className="rounded-2xl border border-white/10 bg-white/[0.04] hover:bg-white/[0.08] p-3 text-start transition"><div className="flex items-center gap-2 text-violet-200 text-xs font-bold"><RotateCw className={`w-4 h-4 ${metaLoading ? 'animate-spin' : ''}`} /> تحديث</div><div className="text-[10px] text-white/40 mt-1">قدرات/خارطة</div></button>
        </div>
      </div>
      <div className="p-5 md:p-6 grid xl:grid-cols-[1.15fr_0.85fr] gap-5">
        <div className="grid sm:grid-cols-2 gap-3">
          {OWNER_MISSION_STEPS.map((step) => { const Icon = step.icon; return (<div key={step.title} className={`rounded-2xl border bg-gradient-to-br p-4 ${toneClasses(step.tone)}`}><div className="flex items-center gap-2 font-black mb-2"><Icon className="w-4 h-4" /> {step.title}</div><p className="text-xs text-white/65 leading-relaxed">{step.desc}</p></div>); })}
        </div>
        <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
          <div className="flex items-center justify-between gap-3 mb-3"><div className="font-black flex items-center gap-2"><Compass className="w-4 h-4 text-amber-300" /> مهام تطويري السريعة</div><span className="text-[10px] text-white/40">اضغط لإرسال أمر جاهز</span></div>
          <div className="space-y-2">{OWNER_QUICK_PROMPTS.map((prompt, idx) => (<button key={prompt} onClick={() => onPrompt(prompt)} data-testid={`ac-owner-prompt-${idx}`} className="w-full text-start rounded-xl border border-white/10 bg-white/[0.03] hover:border-amber-400/35 hover:bg-amber-500/10 px-3 py-2 text-xs leading-relaxed transition">{prompt}</button>))}</div>
          {firstRoadmap && (<div className="mt-3 rounded-xl border border-sky-400/20 bg-sky-500/5 p-3 text-xs text-sky-100/80"><div className="font-bold text-sky-200 mb-1 flex items-center gap-1"><Workflow className="w-3.5 h-3.5" /> أولوية من الخارطة</div><div className="line-clamp-2">{firstRoadmap.title || firstRoadmap.name || firstRoadmap.summary || JSON.stringify(firstRoadmap).slice(0, 120)}</div></div>)}
        </div>
      </div>
    </section>
  );
}

function MiniMetric({ label, value, icon: Icon, tone }) {
  return (<div className={`rounded-2xl border bg-gradient-to-br p-3 ${toneClasses(tone)}`}><div className="flex items-center gap-2 text-xs font-bold"><Icon className="w-4 h-4" /> {label}</div><div className="text-xl font-black mt-1">{value}</div></div>);
}

function WelcomePromptBoard({ onPrompt }) {
  const examples = [
    { title: 'طوّرني أنا', text: 'افحص قسم برمجة زيتاكس واقترح 10 ترقيات للواجهة والذكاء ثم نفّذ الأعلى أولوية', icon: BrainCircuit, tone: 'amber' },
    { title: 'فحص شامل', text: 'اعمل health check شامل للمنصة والذكاء والتكاملات ثم أعطني تقرير مرتب وخلاصة مربعة', icon: Activity, tone: 'emerald' },
    { title: 'خطة أسبوع', text: 'اكتب خطة تطوير AutoCoder لمدة أسبوع: يوم بيوم، الأدوات المطلوبة، والنتيجة النهائية', icon: TimerReset, tone: 'sky' },
    { title: 'تصميم فاخر', text: 'صمّم تجربة مستخدم أفخم لقسم المالك مع خطوات تنفيذ واختبار ونشر', icon: Sparkles, tone: 'violet' },
  ];
  return (<div data-testid="ac-welcome-board" className="max-w-5xl mx-auto py-8"><div className="text-center mb-6"><div className="inline-flex w-16 h-16 rounded-3xl bg-amber-500/15 border border-amber-400/30 items-center justify-center mb-4 shadow-xl shadow-amber-500/10"><Terminal className="w-7 h-7 text-amber-400" /></div><h3 className="text-2xl font-black mb-2">وش نطوّر في برمجة زيتاكس؟</h3><p className="text-white/60 text-sm leading-relaxed max-w-2xl mx-auto">اختر أمر جاهز أو اكتب بصوتك. الردود هنا منظمة: فهم الطلب ← التنفيذ ← الأدوات ← الإثبات ← خلاصة مربعة.</p></div><div className="grid md:grid-cols-2 gap-3">{examples.map((ex, idx) => { const Icon = ex.icon; return (<button key={ex.title} onClick={() => onPrompt(ex.text)} data-testid={`ac-example-chip-${idx}`} className={`text-start rounded-2xl border bg-gradient-to-br p-4 hover:scale-[1.01] transition ${toneClasses(ex.tone)}`}><div className="flex items-center gap-2 font-black mb-2"><Icon className="w-4 h-4" /> {ex.title}</div><p className="text-xs text-white/65 leading-relaxed">{ex.text}</p></button>); })}</div><div className="mt-5 rounded-2xl border border-amber-400/20 bg-amber-500/5 p-4 text-xs text-amber-100/75 flex items-start gap-2"><AlertTriangle className="w-4 h-4 mt-0.5 text-amber-300 shrink-0" /><div>صلاحياتي قوية جداً: قراءة/كتابة/تنفيذ/نشر. لذلك الواجهة تعرض لك الأدوات والخطوات حتى تتابع وش يصير لحظة بلحظة.</div></div></div>);
}

function AssistantSummaryBox({ message }) {
  const insights = buildMessageInsights(message);
  const hasContent = insights.urls.length || insights.needed.length || insights.suggestions.length || insights.warnings.length || insights.toolCount;
  if (!hasContent) return null;
  const statusTone = insights.status === 'error' ? 'rose' : insights.status === 'warning' ? 'amber' : 'emerald';
  return (<div data-testid="ac-summary-box" className={`mt-4 rounded-2xl border bg-gradient-to-br p-4 ${toneClasses(statusTone)}`}><div className="flex items-center justify-between gap-3 mb-3"><div className="font-black flex items-center gap-2"><ClipboardList className="w-4 h-4" /> خلاصة التنفيذ</div><div className="text-[10px] text-white/45">تتولّد تلقائياً من الرد والأدوات</div></div><div className="grid md:grid-cols-2 gap-3"><SummaryMiniCard title="حالة الأدوات" icon={ListChecks} items={[`الأدوات المستخدمة: ${insights.toolCount}`, `نجح: ${insights.okTools}`, insights.failedTools ? `تعثر: ${insights.failedTools}` : 'لا توجد أدوات متعثرة']} /><SummaryMiniCard title="المطلوب/النواقص" icon={Target} items={insights.needed.length ? insights.needed : ['لا يوجد طلب واضح منك في هذا الرد.']} /><SummaryMiniCard title="اقتراحات قادمة" icon={Lightbulb} items={insights.suggestions.length ? insights.suggestions : ['اسألني عن الخطوة التالية أو اضغط أحد أوامر التطوير السريعة.']} /><SummaryMiniCard title="روابط مهمة" icon={LinkIcon} items={insights.urls.length ? insights.urls : ['ما فيه روابط داخل هذا الرد.']} isLinks /></div>{insights.warnings.length > 0 && (<div className="mt-3 rounded-xl border border-rose-400/25 bg-rose-500/10 p-3"><div className="font-bold text-rose-200 text-xs mb-1 flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" /> تنبيهات</div><ul className="space-y-1 text-xs text-white/70 list-disc pe-4">{insights.warnings.map((item, i) => <li key={i}>{item}</li>)}</ul></div>)}</div>);
}

function SummaryMiniCard({ title, icon: Icon, items, isLinks = false }) {
  return (<div className="rounded-xl border border-white/10 bg-black/25 p-3 min-h-[112px]"><div className="font-bold text-xs mb-2 flex items-center gap-1.5"><Icon className="w-3.5 h-3.5" /> {title}</div><ul className="space-y-1.5 text-[11px] text-white/68 leading-relaxed">{items.slice(0, 5).map((item, idx) => (<li key={`${item}-${idx}`} className="break-words">{isLinks && String(item).startsWith('http') ? (<a href={item} target="_blank" rel="noreferrer" className="text-sky-300 hover:text-sky-200 inline-flex items-center gap-1"><ExternalLink className="w-3 h-3" /> {item}</a>) : item}</li>))}</ul></div>);
}

function LockShell({ title, children }) {
  return (
    <div dir="rtl" className="min-h-screen bg-[#050505] text-white flex items-center justify-center p-6">
      <Toaster richColors position="top-center" />
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex w-16 h-16 rounded-2xl bg-amber-500/15 border border-amber-400/30 items-center justify-center mb-4">
            <Lock className="w-7 h-7 text-amber-400" />
          </div>
          <h1 className="text-2xl font-black mb-1" data-testid="ac-lock-title">{title}</h1>
          <p className="text-white/50 text-xs">قسم خاص بمالك المنصة فقط</p>
        </div>
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 backdrop-blur">
          {children}
        </div>
      </div>
    </div>
  );
}

function RecoveryDisplay({ codes, onDone }) {
  const copyAll = () => {
    navigator.clipboard.writeText(codes.join('\n'));
    toast.success('تم النسخ');
  };
  return (
    <div dir="rtl" className="min-h-screen bg-[#050505] text-white flex items-center justify-center p-6">
      <Toaster richColors position="top-center" />
      <div className="w-full max-w-lg">
        <div className="text-center mb-6">
          <div className="inline-flex w-16 h-16 rounded-2xl bg-emerald-500/15 border border-emerald-400/30 items-center justify-center mb-4">
            <KeyRound className="w-7 h-7 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-black mb-1">رموز الاسترجاع</h1>
          <p className="text-amber-300/80 text-xs leading-relaxed">
            احفظ هذه الرموز في مكان آمن جداً (Password Manager / Notes مشفّرة).<br/>
            كل رمز يعمل مرة واحدة فقط لاسترجاع الوصول لو نسيت كلمة السر.
          </p>
        </div>
        <div className="bg-black/60 border border-amber-500/20 rounded-2xl p-5 mb-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-sm" data-testid="recovery-codes-list">
            {codes.map((c, i) => (
              <div key={i} className="bg-amber-500/5 border border-amber-500/15 rounded-lg px-3 py-2 text-amber-200 text-center select-all">
                {c}
              </div>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={copyAll}
            data-testid="copy-recovery-codes"
            className="flex-1 py-3 rounded-lg bg-white/10 hover:bg-white/15 text-sm font-bold flex items-center justify-center gap-2"
          >
            <Copy className="w-4 h-4" /> نسخ الكل
          </button>
          <button
            onClick={onDone}
            data-testid="recovery-codes-done"
            className="flex-1 py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-sm font-bold"
          >
            حفظت الرموز، تابع
          </button>
        </div>
      </div>
    </div>
  );
}


function AutoCoderCommandCenter({ report, roadmap, loading, onRefresh }) {
  const integrations = report?.recommended_integrations || [];
  const capabilities = report?.capabilities || [];
  const providers = report?.llm_providers || [];
  const phases = roadmap?.phases || [];
  const configuredIntegrations = integrations.filter((i) => i.status === 'configured').length;
  const partialIntegrations = integrations.filter((i) => i.status === 'partial').length;
  const missingIntegrations = integrations.filter((i) => i.status === 'missing').length;
  const configuredProviders = providers.filter((p) => p.configured).length;
  const readiness = integrations.length ? Math.round(((configuredIntegrations + partialIntegrations * 0.45) / integrations.length) * 100) : 0;
  const topNext = integrations.filter((i) => i.status !== 'configured').slice(0, 5);

  const statusTone = {
    configured: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200',
    partial: 'border-amber-400/30 bg-amber-500/10 text-amber-200',
    missing: 'border-rose-400/25 bg-rose-500/10 text-rose-200',
  };
  const statusText = { configured: 'جاهز', partial: 'جزئي', missing: 'ناقص' };

  return (
    <section data-testid="ac-command-center" className="max-w-6xl mx-auto mb-5 overflow-hidden rounded-[1.75rem] border border-white/10 bg-gradient-to-br from-zinc-950 via-black to-zinc-950 shadow-2xl shadow-amber-950/10">
      <div className="relative p-5 md:p-6">
        <div className="absolute inset-0 pointer-events-none opacity-70">
          <div className="absolute -top-24 end-10 w-72 h-72 rounded-full bg-amber-500/10 blur-3xl" />
          <div className="absolute top-10 -start-20 w-72 h-72 rounded-full bg-sky-500/10 blur-3xl" />
          <div className="absolute bottom-0 start-1/3 w-64 h-64 rounded-full bg-emerald-500/10 blur-3xl" />
        </div>

        <div className="relative flex flex-col lg:flex-row lg:items-start justify-between gap-5">
          <div className="min-w-0">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-400/25 bg-amber-500/10 px-3 py-1 text-[11px] text-amber-200 mb-3">
              <BrainCircuit className="w-3.5 h-3.5" /> AutoCoder Intelligence OS
            </div>
            <h2 className="text-2xl md:text-4xl font-black tracking-tight mb-2">مركز قدرات برمجة زيتاكس</h2>
            <p className="text-sm md:text-base text-white/60 leading-relaxed max-w-3xl">
              لوحة تنفيذية تعرض وش أقدر أسوي الآن، أي مفاتيح شغالة، وش النواقص الأعلى أثراً عشان أصير أقوى وأكثر استقلالية.
            </p>
          </div>
          <button onClick={onRefresh} disabled={loading} data-testid="ac-meta-refresh" className="shrink-0 inline-flex items-center justify-center gap-2 rounded-xl bg-white/10 hover:bg-white/15 border border-white/15 px-4 py-2 text-sm font-bold disabled:opacity-50">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCw className="w-4 h-4" />}
            تحديث الفحص
          </button>
        </div>

        <div className="relative grid grid-cols-2 lg:grid-cols-4 gap-3 mt-6">
          <MetaStat icon={ShieldCheck} label="قدرات تنفيذية" value={capabilities.length || '—'} tone="amber" hint="قراءة/كتابة/اختبار/نشر" />
          <MetaStat icon={Cpu} label="نماذج LLM جاهزة" value={`${configuredProviders}/${providers.length || '—'}`} tone="sky" hint="مع fallback حسب المهمة" />
          <MetaStat icon={PackageCheck} label="تكاملات جاهزة" value={`${configuredIntegrations}/${integrations.length || '—'}`} tone="emerald" hint={`${partialIntegrations} جزئي · ${missingIntegrations} ناقص`} />
          <MetaStat icon={Gauge} label="جاهزية المنظومة" value={integrations.length ? `${readiness}%` : '—'} tone="violet" hint="حسب مفاتيح التكاملات" />
        </div>

        {!report && loading && (
          <div className="relative mt-5 rounded-2xl border border-white/10 bg-white/[0.03] p-6 text-center text-white/60">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-amber-300" />
            جاري تحميل تقرير القدرات...
          </div>
        )}

        {report && (
          <div className="relative grid xl:grid-cols-12 gap-4 mt-5">
            <div className="xl:col-span-5 rounded-2xl border border-white/10 bg-white/[0.035] p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-black flex items-center gap-2"><Activity className="w-4 h-4 text-amber-300" /> القدرات الحالية</h3>
                <span className="text-[10px] text-white/40">{report.generated_at ? new Date(report.generated_at).toLocaleString('ar') : ''}</span>
              </div>
              <div className="grid sm:grid-cols-2 gap-2">
                {capabilities.slice(0, 8).map((c) => (
                  <div key={c.id || c.name} className="rounded-xl border border-white/10 bg-black/25 p-3 hover:border-amber-400/25 transition">
                    <div className="text-sm font-bold text-white mb-1">{c.name_ar || c.name || c.id}</div>
                    <div className="text-[11px] text-white/50 leading-relaxed">{(c.details_ar || c.description_ar || c.description || c.id || '').toString()}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="xl:col-span-4 rounded-2xl border border-white/10 bg-white/[0.035] p-4">
              <h3 className="font-black flex items-center gap-2 mb-4"><Rocket className="w-4 h-4 text-sky-300" /> خارطة التطوير</h3>
              <div className="space-y-3">
                {phases.slice(0, 7).map((p, idx) => (
                  <div key={p.phase} className="flex gap-3 group">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 rounded-full bg-sky-500/15 border border-sky-400/30 text-sky-200 flex items-center justify-center text-xs font-black">{p.phase}</div>
                      {idx !== phases.slice(0, 7).length - 1 && <div className="w-px flex-1 bg-white/10 mt-2" />}
                    </div>
                    <div className="pb-2 min-w-0">
                      <div className="text-sm font-bold group-hover:text-sky-200 transition">{p.title}</div>
                      <div className="text-[11px] text-white/50 leading-relaxed">{p.outcome}</div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {(p.keys || []).map((k) => <span key={k} className="rounded bg-black/35 border border-white/10 px-1.5 py-0.5 text-[10px] font-mono text-white/55">{k}</span>)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="xl:col-span-3 rounded-2xl border border-white/10 bg-white/[0.035] p-4">
              <h3 className="font-black flex items-center gap-2 mb-4"><KeyRound className="w-4 h-4 text-emerald-300" /> أهم النواقص</h3>
              <div className="space-y-2">
                {topNext.length === 0 ? (
                  <div className="rounded-xl border border-emerald-400/25 bg-emerald-500/10 p-3 text-sm text-emerald-200">كل التكاملات المقترحة جاهزة 👑</div>
                ) : topNext.map((i) => (
                  <div key={i.id} className="rounded-xl border border-white/10 bg-black/25 p-3">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="font-bold text-sm truncate">{i.name}</div>
                      <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] ${statusTone[i.status] || statusTone.missing}`}>{statusText[i.status] || i.status}</span>
                    </div>
                    <p className="text-[11px] text-white/50 leading-relaxed mb-2">{i.why_ar}</p>
                    <div className="flex flex-wrap gap-1">
                      {(i.env_vars || []).slice(0, 4).map((v) => <code key={v} className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-amber-200/80">{v}</code>)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="xl:col-span-12 grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {providers.map((p) => (
                <div key={p.id} className="rounded-2xl border border-white/10 bg-black/25 p-3 flex items-start gap-3">
                  <div className={`mt-0.5 rounded-xl p-2 ${p.configured ? 'bg-emerald-500/10 text-emerald-300' : 'bg-rose-500/10 text-rose-300'}`}>
                    {p.configured ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-bold">{p.name}</div>
                    <div className="text-[11px] text-white/45">{p.configured ? 'مفتاح متوفر' : `ينقص ${p.env}`}</div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {(p.best_for || []).slice(0, 3).map((b) => <span key={b} className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-white/45">{b}</span>)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function MetaStat({ icon: Icon, label, value, hint, tone }) {
  const tones = {
    amber: 'from-amber-500/20 to-orange-500/5 border-amber-400/25 text-amber-200',
    sky: 'from-sky-500/20 to-cyan-500/5 border-sky-400/25 text-sky-200',
    emerald: 'from-emerald-500/20 to-teal-500/5 border-emerald-400/25 text-emerald-200',
    violet: 'from-violet-500/20 to-fuchsia-500/5 border-violet-400/25 text-violet-200',
  };
  return (
    <div className={`rounded-2xl border bg-gradient-to-br p-4 ${tones[tone] || tones.amber}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-white/55">{label}</span>
        <Icon className="w-4 h-4" />
      </div>
      <div className="text-2xl md:text-3xl font-black text-white">{value}</div>
      <div className="text-[11px] text-white/45 mt-1">{hint}</div>
    </div>
  );
}

function ModelSelector({ value, onChange, open, setOpen, keyStatus }) {
  const current = MODEL_OPTIONS.find((m) => m.id === value) || MODEL_OPTIONS[0];
  const Icon = current.icon;
  const providers = keyStatus?.providers || {};

  const toneClass = (tone) => ({
    amber: 'bg-amber-500/10 border-amber-400/30 text-amber-300',
    emerald: 'bg-emerald-500/10 border-emerald-400/30 text-emerald-300',
    sky: 'bg-sky-500/10 border-sky-400/30 text-sky-300',
    violet: 'bg-violet-500/10 border-violet-400/30 text-violet-300',
  }[tone] || 'bg-white/5 border-white/15 text-white/70');

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        data-testid="ac-model-selector"
        title="اختر الموديل"
        className={`text-[10px] md:text-[11px] px-2 md:px-3 py-1.5 rounded-full inline-flex items-center gap-1.5 border transition ${toneClass(current.tone)} hover:brightness-125`}
      >
        <Icon className="w-3 h-3" />
        <span className="font-bold">{current.label}</span>
      </button>
      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div
            data-testid="ac-model-menu"
            className="absolute end-0 mt-2 w-72 bg-[#0a0a0a] border border-white/15 rounded-xl shadow-2xl z-50 overflow-hidden"
          >
            <div className="p-2 border-b border-white/10 text-[10px] uppercase tracking-widest text-white/40">
              الموديل المستخدم
            </div>
            <div className="p-1.5 space-y-1">
              {MODEL_OPTIONS.map((m) => {
                const providerInfo = providers[m.id];
                const available = providerInfo?.available !== false;
                const MIcon = m.icon;
                const selected = value === m.id;
                return (
                  <button
                    key={m.id}
                    onClick={() => available && onChange(m.id)}
                    disabled={!available}
                    data-testid={`ac-model-option-${m.id}`}
                    className={`w-full text-start p-2.5 rounded-lg flex items-start gap-2 transition ${
                      selected ? 'bg-amber-500/10 border border-amber-400/30' :
                      available ? 'hover:bg-white/5 border border-transparent' :
                      'opacity-40 cursor-not-allowed border border-transparent'
                    }`}
                  >
                    <MIcon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${selected ? 'text-amber-300' : 'text-white/60'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-bold">{m.label}</span>
                        {selected && (
                          <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1.5 rounded">مختار</span>
                        )}
                      </div>
                      <div className="text-[11px] text-white/50 mt-0.5">{m.cost}</div>
                      {!available && providerInfo?.get_key_url && (
                        <a
                          href={providerInfo.get_key_url}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="inline-block mt-1 text-[10px] text-sky-400 hover:text-sky-300 underline"
                        >
                          احصل على مفتاح مجاني →
                        </a>
                      )}
                      {!available && !providerInfo?.get_key_url && (
                        <div className="text-[10px] text-rose-300/70 mt-0.5">المفتاح غير مضبوط</div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
            <div className="p-2 border-t border-white/10 text-[10px] text-white/40 leading-relaxed">
              💡 الموديلات المجانية ممتازة للمهام البسيطة (قراءة ملفات، تنفيذ أوامر). استخدم Claude للـrefactor المعقّد.
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function SessionTimer({ expiresAt }) {
  const [remaining, setRemaining] = useState('');
  useEffect(() => {
    if (!expiresAt) return;
    const tick = () => {
      const ms = new Date(expiresAt) - new Date();
      if (ms <= 0) { setRemaining('انتهت'); return; }
      const h = Math.floor(ms / 3600000);
      const m = Math.floor((ms % 3600000) / 60000);
      setRemaining(h > 0 ? `${h}س ${m}د` : `${m}د`);
    };
    tick();
    const id = setInterval(tick, 30000);
    return () => clearInterval(id);
  }, [expiresAt]);
  if (!remaining) return null;
  return (
    <span
      data-testid="ac-session-timer"
      className="hidden md:inline-flex text-[10px] px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-400/20 text-emerald-300 items-center gap-1"
    >
      <ScrollText className="w-3 h-3" /> {remaining}
    </span>
  );
}

function MessageBubble({ m }) {
  if (m.role === 'user') {
    const attachments = m.attachments || [];
    return (
      <div className="flex justify-end">
        <div className="bg-amber-500/15 border border-amber-400/25 rounded-2xl rounded-br-sm px-4 py-3 max-w-2xl text-sm leading-relaxed">
          {m.content && <div className="whitespace-pre-wrap">{m.content}</div>}
          {attachments.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {attachments.map((a, idx) => {
                const isImage = a.type?.startsWith('image/');
                const src = a.previewUrl || (a.url ? `${API}${a.url}` : '');
                const sizeKb = a.size ? `${Math.max(1, Math.round(a.size / 1024))}KB` : '';
                return (
                  <div key={`${a.name || a.url || 'file'}-${idx}`} className="rounded-xl overflow-hidden border border-amber-300/25 bg-black/25 max-w-[180px]">
                    {isImage && src ? (
                      <img src={src} alt={a.name || 'attachment'} className="w-full h-28 object-cover bg-black/40" />
                    ) : (
                      <div className="px-3 py-2 text-xs text-amber-100/90">📎 {a.name || a.url || 'ملف مرفق'}</div>
                    )}
                    <div className="px-2 py-1 text-[10px] text-amber-100/80 truncate">
                      {a.name || 'مرفق'} {sizeKb && <span className="text-amber-100/50">• {sizeKb}</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }
  const isErrorOnly = !!m.error && (!m.tool_events || m.tool_events.length === 0);
  return (
    <div className={`rounded-2xl p-4 max-w-3xl border ${isErrorOnly ? 'bg-rose-500/[0.06] border-rose-400/30' : 'bg-white/[0.04] border-white/10'}`}>
      <div className={`text-[10px] uppercase tracking-widest mb-2 ${isErrorOnly ? 'text-rose-300/80' : 'text-amber-400/80'}`}>
        {isErrorOnly ? '⚠️ خطأ' : 'برمجة زيتاكس'}
      </div>
      {(m.tool_events || []).map((t, i) => <ToolPill key={i} t={t} />)}
      {m.content && <div className="text-sm leading-relaxed whitespace-pre-wrap mt-2">{m.content}</div>}
      <AssistantSummaryBox message={m} />
    </div>
  );
}

function ToolPill({ t }) {
  const [open, setOpen] = useState(false);
  // Auto Smart Router decision pill
  if (t._isAutoRoute) {
    return (
      <div data-testid="auto-route-pill" className="my-1.5 rounded-lg border border-amber-400/40 bg-gradient-to-l from-amber-500/[0.10] to-amber-500/[0.04] px-3 py-2 text-xs flex items-center gap-2">
        <Zap className="w-3.5 h-3.5 text-amber-300" />
        <span className="font-bold text-amber-200">Auto Smart</span>
        <span className="text-white/50">·</span>
        <span className="text-white/70">{t.task}</span>
        <span className="text-white/30">→</span>
        <span className="font-bold text-amber-300">{t.provider}</span>
        <span className="text-white/40 truncate flex-1">{t.reason}</span>
        {t.est_cost_usd_per_turn !== undefined && (
          <span className="text-[10px] text-emerald-300/80 font-mono shrink-0">
            ~${t.est_cost_usd_per_turn.toFixed(4)}
          </span>
        )}
      </div>
    );
  }
  // Special rendering for usage events (must come AFTER hooks)
  if (t._isUsage) {
    return (
      <div data-testid="usage-pill" className="my-1.5 rounded-lg border border-emerald-400/30 bg-emerald-500/[0.05] px-3 py-2 text-xs flex items-center gap-2">
        <span>💰</span>
        <span className="font-bold text-emerald-300">${(t.cost_usd ?? 0).toFixed(4)}</span>
        <span className="text-white/50 text-[10px]">
          {t.input?.toLocaleString()} in / {t.output?.toLocaleString()} out
          {t.cached_read > 0 && <span className="ml-1 text-emerald-400">• {t.cached_read.toLocaleString()} cached (90% أرخص)</span>}
        </span>
      </div>
    );
  }
  const Icon = TOOL_ICON[t.name] || Terminal;
  const isCalling = t.status === 'calling';
  const isOk = t.ok !== false;
  return (
    <div className="my-1.5 rounded-lg border border-white/10 bg-black/30 overflow-hidden text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/5 text-start"
      >
        <Icon className={`w-3.5 h-3.5 ${isCalling ? 'text-amber-300 animate-pulse' : isOk ? 'text-emerald-300' : 'text-rose-300'}`} />
        <span className="font-bold">{TOOL_LABEL[t.name] || t.name}</span>
        <span className="text-white/40 truncate flex-1">{t.summary || (isCalling ? 'يشتغل...' : '')}</span>
        {!isCalling && (
          <span className={`text-[10px] px-1.5 py-0.5 rounded ${isOk ? 'bg-emerald-500/15 text-emerald-300' : 'bg-rose-500/15 text-rose-300'}`}>
            {isOk ? 'تم' : 'فشل'}
          </span>
        )}
      </button>
      {open && (
        <div className="border-t border-white/10 bg-black/40 p-3 space-y-2">
          {t.args && Object.keys(t.args).length > 0 && (
            <div>
              <div className="text-[10px] uppercase text-white/40 mb-1">المدخلات</div>
              <pre className="text-[11px] text-white/70 whitespace-pre-wrap break-all bg-black/40 rounded p-2 max-h-40 overflow-y-auto">{JSON.stringify(t.args, null, 2)}</pre>
            </div>
          )}
          {t.preview && (
            <div>
              <div className="text-[10px] uppercase text-white/40 mb-1">النتيجة</div>
              <pre className="text-[11px] text-white/70 whitespace-pre-wrap break-all bg-black/40 rounded p-2 max-h-60 overflow-y-auto">{t.preview}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
