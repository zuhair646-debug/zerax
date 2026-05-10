import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import {
  Lock, Unlock, KeyRound, Send, Loader2, Plus, Trash2,
  ArrowLeft, Terminal, FileCode, FolderTree, GitBranch,
  Search, FileEdit, FilePlus, FileX, RotateCw, ShieldCheck,
  AlertTriangle, Copy, ScrollText, MessageSquare,
  Globe, Download, Layers, FilePlus2, Database, Cpu, Sparkles, Zap,
  Mic, Square, X,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const SESSION_KEY = 'zitex_autocoder_session';
const MODEL_KEY = 'zitex_autocoder_model';

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
  { id: 'claude', label: 'Claude Sonnet 4.5', cost: 'مدفوع — الأذكى', tone: 'amber', icon: Sparkles },
  { id: 'groq', label: 'Llama 3.3 70B', cost: 'مجاني — سريع جداً', tone: 'emerald', icon: Zap },
  { id: 'gemini', label: 'Gemini 2.0 Flash', cost: 'مجاني — قدرة كبيرة', tone: 'sky', icon: Sparkles },
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
    if (typeof window === 'undefined') return 'claude';
    return localStorage.getItem(MODEL_KEY) || 'claude';
  });
  const [showModelMenu, setShowModelMenu] = useState(false);

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

  const send = async () => {
    const msg = input.trim();
    if (!msg || sending) return;
    setInput('');
    setSending(true);
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setCurrentStream('');
    setCurrentTools([]);
    let lastTurnCost = null;

    try {
      // Backend now uses multipart/form-data (to support file attachments)
      const fd = new FormData();
      fd.append('message', msg);
      if (conversationId) fd.append('conversation_id', conversationId);
      fd.append('model', model || 'claude');

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
            {messages.length === 0 && !currentStream && (
              <div className="max-w-2xl mx-auto text-center py-12">
                <ShieldCheck className="w-12 h-12 text-amber-400 mx-auto mb-4" />
                <h3 className="text-2xl font-black mb-2">شنو نبرمج اليوم؟</h3>
                <p className="text-white/60 text-sm mb-6 leading-relaxed">
                  هذا ذكاء برمجة متخصص. عنده وصول كامل لقاعدة الكود حقّك.<br/>
                  يقرا، يكتب، ينفّذ أوامر، ويعمل commit + push للـGitHub.
                </p>
                <div className="grid md:grid-cols-2 gap-3 text-start">
                  {[
                    'أضف صفحة جديدة /admin/logs تعرض آخر 100 سجل من autocoder_audit',
                    'اعرض شجرة /app/backend/modules وقل لي وش وظيفة كل module',
                    'اقرا /app/backend/server.py واشرح لي كيف الـauth يشتغل',
                    'سوّي fix لأي bug تشوفه بعد ما تشغّل pytest على /app/backend/tests',
                  ].map((ex) => (
                    <button
                      key={ex}
                      onClick={() => setInput(ex)}
                      data-testid="ac-example-chip"
                      className="p-3 rounded-xl border border-white/10 bg-white/[0.03] hover:border-amber-400/30 hover:bg-amber-500/5 text-sm transition leading-snug"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
                <div className="mt-8 inline-flex items-start gap-2 text-[11px] text-amber-300/60 bg-amber-500/5 border border-amber-500/15 rounded-lg p-3 max-w-md mx-auto">
                  <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                  <div className="text-start leading-relaxed">
                    صلاحيات مفتوحة بالكامل (read/write/exec/git push). راجع كل عملية قبل ما توافق.
                  </div>
                </div>
              </div>
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
            {isRecording && (
              <div data-testid="ac-recording-bar" className="max-w-3xl mx-auto mb-2 flex items-center gap-3 px-4 py-2 bg-rose-500/10 border border-rose-400/30 rounded-xl">
                <span className="relative flex w-3 h-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-500"></span>
                </span>
                <span className="text-rose-200 text-sm font-bold flex-1">
                  جاري التسجيل... {Math.floor(recordingSeconds / 60)}:{String(recordingSeconds % 60).padStart(2, '0')}
                  <span className="text-rose-300/60 text-xs font-normal ms-2">(حد أقصى 60 ثانية)</span>
                </span>
                <button
                  onClick={cancelRecording}
                  data-testid="ac-recording-cancel"
                  title="إلغاء"
                  className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/70"
                >
                  <X className="w-4 h-4" />
                </button>
                <button
                  onClick={stopRecording}
                  data-testid="ac-recording-stop"
                  title="إيقاف وتحويل"
                  className="px-3 py-1.5 rounded-lg bg-rose-500 hover:bg-rose-400 text-white text-xs font-bold flex items-center gap-1"
                >
                  <Square className="w-3 h-3 fill-current" /> إيقاف
                </button>
              </div>
            )}
            {transcribing && (
              <div data-testid="ac-transcribing-bar" className="max-w-3xl mx-auto mb-2 flex items-center gap-2 px-4 py-2 bg-amber-500/10 border border-amber-400/30 rounded-xl">
                <Loader2 className="w-4 h-4 animate-spin text-amber-300" />
                <span className="text-amber-200 text-sm">يحوّل الصوت لنص...</span>
              </div>
            )}
            <div className="max-w-3xl mx-auto flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
                }}
                rows={2}
                disabled={isRecording}
                placeholder={isRecording ? '🎙️ جاري التسجيل...' : 'اكتب أمرك للذكاء... أو اضغط الميكروفون لتسجل بصوتك'}
                data-testid="ac-input"
                className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-3 text-sm resize-none focus:border-amber-400 outline-none disabled:opacity-50"
              />
              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={transcribing || sending}
                data-testid="ac-mic-btn"
                title={isRecording ? 'أوقف التسجيل' : 'سجّل صوتياً'}
                className={`h-12 w-12 rounded-xl flex items-center justify-center disabled:opacity-50 transition ${
                  isRecording
                    ? 'bg-rose-500 hover:bg-rose-400 text-white animate-pulse'
                    : 'bg-white/10 hover:bg-white/15 text-white border border-white/15'
                }`}
              >
                {isRecording ? <Square className="w-5 h-5 fill-current" /> :
                  transcribing ? <Loader2 className="w-5 h-5 animate-spin" /> :
                  <Mic className="w-5 h-5" />}
              </button>
              <button
                onClick={send}
                disabled={sending || !input.trim() || isRecording || transcribing}
                data-testid="ac-send"
                className="h-12 w-12 rounded-xl bg-amber-500 hover:bg-amber-400 text-black flex items-center justify-center disabled:opacity-50"
              >
                {sending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </button>
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

function ModelSelector({ value, onChange, open, setOpen, keyStatus }) {
  const current = MODEL_OPTIONS.find((m) => m.id === value) || MODEL_OPTIONS[0];
  const Icon = current.icon;
  const providers = keyStatus?.providers || {};

  const toneClass = (tone) => ({
    amber: 'bg-amber-500/10 border-amber-400/30 text-amber-300',
    emerald: 'bg-emerald-500/10 border-emerald-400/30 text-emerald-300',
    sky: 'bg-sky-500/10 border-sky-400/30 text-sky-300',
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
    return (
      <div className="flex justify-end">
        <div className="bg-amber-500/15 border border-amber-400/25 rounded-2xl rounded-br-sm px-4 py-3 max-w-2xl text-sm leading-relaxed whitespace-pre-wrap">
          {m.content}
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
    </div>
  );
}

function ToolPill({ t }) {
  const [open, setOpen] = useState(false);
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
