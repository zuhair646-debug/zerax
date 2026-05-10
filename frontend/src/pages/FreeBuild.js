import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Send, Loader2, Sparkles, ArrowRight, Save, ExternalLink, Trash2, Eye, RotateCcw, Check, GripVertical, Pencil, Plus, X, ChevronUp, ChevronDown, Paperclip, Mic, Square, Image as ImageIcon, Video, FileAudio } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

const API = process.env.REACT_APP_BACKEND_URL;
const FREEBUILD_TOOLS_VERSION = 'tools-fix-2026-05-10-attachments-voice';

const getFileKind = (file) => {
  const type = (file?.type || '').toLowerCase();
  const name = (file?.name || '').toLowerCase();
  if (type.startsWith('image/') || /\.(png|jpe?g|webp|gif|svg|heic|heif)$/i.test(name)) return 'image';
  if (type.startsWith('video/') || /\.(mp4|mov|webm|m4v|avi|mkv)$/i.test(name)) return 'video';
  if (type.startsWith('audio/') || /\.(webm|mp3|m4a|aac|ogg|wav|mp4)$/i.test(name)) return 'audio';
  return 'unknown';
};

const fileLabelIcon = (file) => getFileKind(file);

const fileToBase64Payload = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve({
    name: file.name,
    filename: file.name,
    type: file.type || 'application/octet-stream',
    content_type: file.type || 'application/octet-stream',
    size: file.size || 0,
    data_url: reader.result,
  });
  reader.onerror = () => reject(reader.error || new Error('فشل قراءة الملف'));
  reader.readAsDataURL(file);
});

const parseApiResponse = async (res) => {
  const raw = await res.text();
  let data;
  try { data = raw ? JSON.parse(raw) : {}; } catch { data = { detail: raw }; }
  if (!res.ok) throw new Error(data?.detail || data?.message || `HTTP ${res.status}`);
  return data;
};

const fetchJson = async (url, options = {}) => {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${url}`, { ...options, headers });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text }; }
  if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
  return data;
};

const Bubble = ({ role, content, progressNote }) => {
  if (role === 'assistant') {
    return (
      <div className="flex gap-2 mb-4" data-testid="chat-bubble-ai">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-yellow-600 flex items-center justify-center shadow-md shadow-amber-500/40">
          <Sparkles className="w-4 h-4 text-black" />
        </div>
        <div className="flex-1 max-w-[85%]">
          <div className="px-4 py-2.5 rounded-2xl rounded-tr-sm bg-white/[0.05] border border-amber-400/15 text-white leading-relaxed whitespace-pre-wrap" dir="auto">
            {content}
          </div>
          {progressNote && (
            <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-emerald-400 font-bold">
              <Check className="w-3 h-3" /> {progressNote}
            </div>
          )}
        </div>
      </div>
    );
  }
  return (
    <div className="flex gap-2 mb-4 flex-row-reverse" data-testid="chat-bubble-user">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-white/80 text-xs font-bold">أنا</div>
      <div className="max-w-[85%] px-4 py-2.5 rounded-2xl rounded-tl-sm bg-amber-500/15 border border-amber-400/30 text-amber-50 whitespace-pre-wrap" dir="auto">
        {content}
      </div>
    </div>
  );
};

const FreeBuild = () => {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [questionType, setQuestionType] = useState('text'); // text | yes_no | done
  const [options, setOptions] = useState(null);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);
  const [credits, setCredits] = useState(null);
  const [turns, setTurns] = useState(0);
  const [iframeBust, setIframeBust] = useState(Date.now());
  const [htmlStarted, setHtmlStarted] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [savedProjectId, setSavedProjectId] = useState(null);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [gallery, setGallery] = useState([]);
  const [navEditorOpen, setNavEditorOpen] = useState(false);
  const [navLinks, setNavLinks] = useState([]);
  const [navLoading, setNavLoading] = useState(false);
  const [addingTab, setAddingTab] = useState(false);
  const [newTabLabel, setNewTabLabel] = useState('');
  const [newTabBrief, setNewTabBrief] = useState('');
  const [constraints, setConstraints] = useState([]);
  const [constraintsOpen, setConstraintsOpen] = useState(false);
  const [newConstraintText, setNewConstraintText] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [transcribing, setTranscribing] = useState(false);
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const audioCaptureInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      toast.error('سجّل دخولك أولاً');
      navigate('/login');
      return;
    }
    begin();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      try {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
          mediaRecorderRef.current.stop();
        }
      } catch (_) {}
    };
  }, []);

  const begin = async () => {
    setLoading(true);
    try {
      const d = await fetchJson('/api/freebuild/v2/start', { method: 'POST', body: JSON.stringify({}) });
      setSessionId(d.session_id);
      setMessages([{ role: 'assistant', content: d.assistant_message, progressNote: null }]);
      setQuestionType(d.next_question_type);
      setOptions(d.options);
      setCredits(d.credits_balance);
      setTurns(0);
      setHtmlStarted(false);
      setSavedProjectId(null);
    } catch (e) {
      toast.error('فشل بدء المحادثة: ' + e.message);
    }
    setLoading(false);
  };

  const send = async (text) => {
    const msg = (text || input).trim();
    const filesToSend = [...attachments];
    if (!msg && filesToSend.length === 0) { toast.error('اكتب جوابك أو أرفق ملف'); return; }
    if (!sessionId) return;
    if (sending) return;

    const attachmentLabel = filesToSend.length
      ? `\n\n📎 ${filesToSend.map((f) => f.name).join('، ')}`
      : '';
    setMessages((m) => [...m, { role: 'user', content: `${msg || 'أرسلت مرفقات للمعاينة'}${attachmentLabel}` }]);
    setInput('');
    setAttachments([]);
    setSending(true);

    try {
      const token = localStorage.getItem('token');
      let d;
      if (filesToSend.length > 0) {
        const fd = new FormData();
        fd.append('session_id', sessionId);
        fd.append('message', msg || 'حلّل المرفقات وخذها كمرجع لتصميم الموقع.');
        filesToSend.forEach((file) => {
          fd.append('files', file, file.name);
        });
        try {
          const res = await fetch(`${API}/api/freebuild/v2/chat`, {
            method: 'POST',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: fd,
          });
          d = await parseApiResponse(res);
        } catch (multipartError) {
          // Some mobile browsers/proxies break multipart uploads. Fall back to JSON base64 metadata.
          const encoded = await Promise.all(filesToSend.map(fileToBase64Payload));
          const res = await fetch(`${API}/api/freebuild/v2/chat`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({
              session_id: sessionId,
              message: msg || 'حلّل المرفقات وخذها كمرجع لتصميم الموقع.',
              attachments: encoded,
            }),
          });
          d = await parseApiResponse(res);
        }
      } else {
        d = await fetchJson('/api/freebuild/v2/chat', {
          method: 'POST',
          body: JSON.stringify({ session_id: sessionId, message: msg }),
        });
      }
      setMessages((m) => [...m, {
        role: 'assistant',
        content: d.assistant_message,
        progressNote: d.progress_note,
      }]);
      setQuestionType(d.next_question_type);
      setOptions(d.options);
      setCredits(d.credits_balance);
      setTurns(d.turns);
      if (d.constraints) setConstraints(d.constraints);
      if (d.html_updated) {
        setHtmlStarted(true);
        // Bust iframe cache to reload updated preview
        setIframeBust(Date.now());
      }
      if (d.complete) {
        toast.success('الموقع جاهز! اضغط "حفظ" للحفاظ عليه.');
      }
    } catch (e) {
      toast.error(e.message);
      // Rollback optimistic user bubble
      setMessages((m) => m.slice(0, -1));
    }
    setSending(false);
  };


  const addFiles = (fileList) => {
    const incoming = Array.from(fileList || []);
    if (!incoming.length) return [];
    const allowed = incoming.filter((file) => {
      const kind = getFileKind(file);
      if (kind === 'unknown') {
        toast.error(`نوع الملف غير مدعوم: ${file.name || 'ملف بدون اسم'}`);
        return false;
      }
      if (file.size > 25 * 1024 * 1024) {
        toast.error(`الملف كبير جداً: ${file.name || 'ملف'}`);
        return false;
      }
      return true;
    });
    if (allowed.length) {
      setAttachments((prev) => [...prev, ...allowed].slice(0, 5));
      toast.success(`تم إرفاق ${allowed.length} ملف — اضغط زر الإرسال`);
    }
    return allowed;
  };

  const removeAttachment = (idx) => {
    setAttachments((prev) => prev.filter((_, i) => i !== idx));
  };

  const transcribeVoiceBlob = async (blob, filename) => {
    const token = localStorage.getItem('token');
    if (!token) throw new Error('يلزم تسجيل الدخول');
    const fd = new FormData();
    fd.append('audio', blob, filename);
    fd.append('language', 'ar');
    const res = await fetch(`${API}/api/stt/transcribe`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
    const data = await parseApiResponse(res);
    return (data.text || '').trim();
  };

  const handleRecordedBlob = async (blob, type, ext) => {
    if (blob.size < 800) {
      toast.error('التسجيل قصير جداً — اضغط وتكلم ثانيتين على الأقل');
      return;
    }
    const filename = `voice-${Date.now()}.${ext}`;
    setTranscribing(true);
    try {
      const text = await transcribeVoiceBlob(blob, filename);
      if (!text) throw new Error('لم يرجع نص من التسجيل');
      setInput((prev) => `${prev}${prev.trim() ? ' ' : ''}${text}`);
      toast.success('تم تحويل التسجيل إلى نص');
    } catch (e) {
      const file = new File([blob], filename, { type: type || 'audio/webm' });
      setAttachments((prev) => [...prev, file].slice(0, 5));
      toast.warning(`تعذر تحويل الصوت لنص، أضفت التسجيل كمرفق صوتي — اضغط إرسال`);
    } finally {
      setTranscribing(false);
    }
  };

  const startRecording = async () => {
    if (isRecording || sending || transcribing) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      // Safari/iPhone وبعض المتصفحات تمنع MediaRecorder. التسجيل الأصلي من النظام أضمن.
      audioCaptureInputRef.current?.click();
      toast.message('إذا فتح مسجل الجوال، سجّل الصوت ثم اختره كمرفق');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const supportedTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/mp4',
        'audio/aac',
        'audio/ogg;codecs=opus',
      ];
      const mimeType = supportedTypes.find((type) => {
        try { return MediaRecorder.isTypeSupported(type); } catch (_) { return false; }
      }) || '';
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        try { stream.getTracks().forEach((track) => track.stop()); } catch (_) {}
        const type = recorder.mimeType || 'audio/webm';
        const blob = new Blob(audioChunksRef.current, { type });
        audioChunksRef.current = [];
        const ext = type.includes('mp4') ? 'mp4' : type.includes('aac') ? 'aac' : type.includes('ogg') ? 'ogg' : 'webm';
        handleRecordedBlob(blob, type, ext);
      };
      mediaRecorderRef.current = recorder;
      recorder.start(1000);
      setIsRecording(true);
      setRecordingSeconds(0);
      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds((s) => {
          if (s >= 60) {
            stopRecording();
            return s;
          }
          return s + 1;
        });
      }, 1000);
    } catch (e) {
      if (e.name === 'NotAllowedError') {
        toast.error('اسمح للميكروفون من إعدادات المتصفح');
      } else {
        toast.error('خطأ في فتح الميكروفون: ' + (e.message || e.name || 'غير معروف'));
      }
      console.error('FreeBuild recording error', e);
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
    } catch (e) {
      toast.error('خطأ في إيقاف التسجيل');
    }
  };

  const regenerateImages = async () => {
    if (!sessionId || !htmlStarted) {
      toast.error('لازم يكون فيه موقع مولّد قبل');
      return;
    }
    if (sending) return;
    setSending(true);
    const tid = toast.loading('🎨 يعيد رسم الصور بنمط مختلف...');
    try {
      const d = await fetchJson('/api/freebuild/v2/regenerate-images', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, style_seed: '' }),
      });
      setCredits(d.credits_balance);
      setIframeBust(Date.now());
      toast.dismiss(tid);
      toast.success('تم تجديد الصور بمزاج جديد');
    } catch (e) {
      toast.dismiss(tid);
      toast.error(e.message);
    }
    setSending(false);
  };

  const openNavEditor = async () => {
    if (!sessionId) return;
    setNavLoading(true);
    setNavEditorOpen(true);
    try {
      const d = await fetchJson(`/api/freebuild/v2/nav/${sessionId}`);
      setNavLinks(d.links || []);
    } catch (e) {
      toast.error('فشل تحميل التبويبات: ' + e.message);
    }
    setNavLoading(false);
  };

  const navAction = async (body) => {
    setNavLoading(true);
    try {
      const d = await fetchJson('/api/freebuild/v2/edit-nav', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, ...body }),
      });
      setCredits(d.credits_balance);
      setIframeBust(Date.now());
      // Refresh nav list
      const fresh = await fetchJson(`/api/freebuild/v2/nav/${sessionId}`);
      setNavLinks(fresh.links || []);
      return d;
    } catch (e) {
      toast.error(e.message);
      throw e;
    } finally {
      setNavLoading(false);
    }
  };

  const renameTab = async (id) => {
    const link = navLinks.find((l) => l.id === id);
    const newLabel = window.prompt('الاسم الجديد:', link?.label || '');
    if (!newLabel || newLabel.trim() === link?.label) return;
    try {
      await navAction({ action: 'rename', route_id: id, new_label: newLabel.trim() });
      toast.success('تم إعادة التسمية');
    } catch {}
  };

  const deleteTab = async (id) => {
    if (id === 'home') { toast.error('لا يمكن حذف الرئيسية'); return; }
    if (!window.confirm('احذف هذا التبويب وصفحته؟')) return;
    try {
      await navAction({ action: 'delete', route_id: id });
      toast.success('تم الحذف');
    } catch {}
  };

  const moveTab = async (idx, dir) => {
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= navLinks.length) return;
    const reordered = [...navLinks];
    [reordered[idx], reordered[newIdx]] = [reordered[newIdx], reordered[idx]];
    setNavLinks(reordered);
    try {
      await navAction({ action: 'reorder', ordered_ids: reordered.map((l) => l.id) });
    } catch {}
  };

  const addTab = async () => {
    if (!newTabLabel.trim()) { toast.error('اكتب اسم التبويب'); return; }
    setAddingTab(true);
    const tid = toast.loading('🤖 الذكاء يبني الصفحة الجديدة...');
    try {
      const d = await navAction({
        action: 'add',
        new_label_for_add: newTabLabel.trim(),
        new_brief: newTabBrief.trim() || null,
      });
      toast.dismiss(tid);
      toast.success(d.ai_message || 'تمت الإضافة');
      setNewTabLabel('');
      setNewTabBrief('');
    } catch (e) {
      toast.dismiss(tid);
    }
    setAddingTab(false);
  };

  const openConstraints = async () => {
    if (!sessionId) return;
    setConstraintsOpen(true);
    try {
      const d = await fetchJson(`/api/freebuild/v2/constraints/${sessionId}`);
      setConstraints(d.constraints || []);
    } catch (e) {
      toast.error('فشل تحميل القيود: ' + e.message);
    }
  };

  const addConstraint = async () => {
    const rule = newConstraintText.trim();
    if (rule.length < 3) { toast.error('اكتب القيد بوضوح'); return; }
    try {
      const d = await fetchJson('/api/freebuild/v2/constraints/add', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, rule, category: 'manual' }),
      });
      setConstraints(d.constraints || []);
      setNewConstraintText('');
      toast.success('تم حفظ القيد — الذكاء راح يحترمه في كل التحديثات القادمة');
    } catch (e) { toast.error(e.message); }
  };

  const deleteConstraint = async (cid) => {
    try {
      const d = await fetchJson(`/api/freebuild/v2/constraints/${sessionId}/${cid}`, { method: 'DELETE' });
      setConstraints(d.constraints || []);
      toast.success('حُذف');
    } catch (e) { toast.error(e.message); }
  };

  const saveAsProject = async () => {
    const name = (projectName || 'موقعي').trim();
    try {
      const d = await fetchJson('/api/freebuild/v2/save-as-project', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, name }),
      });
      setSavedProjectId(d.project_id);
      setSaveOpen(false);
      toast.success(`تم حفظ "${name}"!`);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const loadGallery = async () => {
    try {
      const d = await fetchJson('/api/freebuild/v2/projects');
      setGallery(d.projects || []);
    } catch (e) {
      toast.error('فشل تحميل: ' + e.message);
    }
  };

  useEffect(() => { if (galleryOpen) loadGallery(); }, [galleryOpen]);

  const deleteProject = async (id) => {
    if (!window.confirm('تحذف هذا المشروع؟')) return;
    try {
      await fetchJson(`/api/freebuild/v2/project/${id}`, { method: 'DELETE' });
      toast.success('تم الحذف');
      loadGallery();
    } catch (e) { toast.error(e.message); }
  };

  const newSession = async () => {
    if (htmlStarted && !savedProjectId) {
      if (!window.confirm('موقعك لم يُحفظ بعد — تأكد تبدأ جلسة جديدة؟')) return;
    }
    await begin();
  };

  const previewUrl = sessionId ? `${API}/api/freebuild/v2/preview/${sessionId}?v=${iframeBust}` : null;

  // =======================================================================
  return (
    <div dir="rtl" className="h-screen bg-[#070710] text-white flex flex-col overflow-hidden" data-testid="freebuild-v2-page">
      {/* HEADER */}
      <div className="flex-shrink-0 backdrop-blur-xl bg-black/60 border-b border-amber-400/15">
        <div className="max-w-screen-2xl mx-auto px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
          <button onClick={() => navigate('/')} className="flex items-center gap-2 text-white/70 hover:text-amber-300 transition text-sm" data-testid="back-home-btn">
            <ArrowRight className="w-4 h-4" /> الرئيسية
          </button>
          <div className="flex items-center gap-2 text-amber-200/95 font-black text-sm sm:text-base">
            <Sparkles className="w-4 h-4 text-amber-400" /> المهندس الذكي — بناء مباشر
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="px-2 py-1 rounded-md bg-amber-400/10 border border-amber-400/25 text-amber-200" data-testid="credits-pill">
              {credits !== null ? `${credits} نقطة` : '…'}
            </span>
            <button onClick={newSession} className="px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 flex items-center gap-1" data-testid="new-session-btn" title="بدء جلسة جديدة">
              <RotateCcw className="w-3 h-3" /> <span className="hidden sm:inline">جديد</span>
            </button>
            {htmlStarted && (
              <button
                onClick={regenerateImages}
                disabled={sending}
                className="px-2.5 py-1 rounded-md bg-fuchsia-500/15 border border-fuchsia-400/30 text-fuchsia-200 hover:bg-fuchsia-500/25 flex items-center gap-1 disabled:opacity-50"
                data-testid="regen-images-btn"
                title="أعد رسم كل الصور بنمط مختلف (3 نقاط)"
              >
                <Sparkles className="w-3 h-3" /> <span className="hidden sm:inline">صور جديدة</span>
              </button>
            )}
            {htmlStarted && (
              <button
                onClick={openConstraints}
                className="px-2.5 py-1 rounded-md bg-rose-500/15 border border-rose-400/30 text-rose-200 hover:bg-rose-500/25 flex items-center gap-1 relative"
                data-testid="constraints-btn"
                title="قيود وممنوعات دائمة"
              >
                <X className="w-3 h-3" /> <span className="hidden sm:inline">قيود</span>
                {constraints.length > 0 && (
                  <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center">{constraints.length}</span>
                )}
              </button>
            )}
            {htmlStarted && (
              <button
                onClick={openNavEditor}
                className="px-2.5 py-1 rounded-md bg-amber-400/10 border border-amber-400/25 text-amber-200 hover:bg-amber-400/20 flex items-center gap-1"
                data-testid="edit-nav-btn"
                title="تحرير التبويبات (إضافة/إعادة تسمية/حذف)"
              >
                <Pencil className="w-3 h-3" /> <span className="hidden sm:inline">التبويبات</span>
              </button>
            )}
            <button onClick={() => setGalleryOpen(true)} className="px-2.5 py-1 rounded-md bg-amber-400/10 border border-amber-400/25 text-amber-200 hover:bg-amber-400/20" data-testid="gallery-btn">
              مواقعي
            </button>
          </div>
        </div>
      </div>

      {/* SPLIT LAYOUT */}
      <div className="flex-1 flex overflow-hidden flex-col lg:flex-row">
        {/* ===== LEFT: CHAT ===== */}
        <div className="w-full lg:w-[42%] flex flex-col border-b lg:border-b-0 lg:border-l border-amber-400/10 bg-[#0a0a14] max-h-[55vh] lg:max-h-none" data-testid="chat-panel">
          <div className="flex-1 overflow-y-auto p-4 sm:p-6" data-testid="chat-messages">
            {loading && messages.length === 0 && (
              <div className="text-center text-white/50 py-10">
                <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3" />
                جاري التحضير...
              </div>
            )}
            {messages.map((m, i) => (
              <Bubble key={i} role={m.role} content={m.content} progressNote={m.progressNote} />
            ))}
            {sending && (
              <div className="flex gap-2 mb-4" data-testid="chat-typing-indicator">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-yellow-600 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-black animate-pulse" />
                </div>
                <div className="px-4 py-3 rounded-2xl bg-white/[0.05] border border-amber-400/15">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" style={{ animationDelay: '0.15s' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" style={{ animationDelay: '0.3s' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* INPUT AREA */}
          <div className="flex-shrink-0 border-t border-amber-400/15 p-3 bg-[#0a0a14]">
            {htmlStarted && !savedProjectId && (
              <div className="mb-2 flex gap-2">
                <Button onClick={() => setSaveOpen(true)} className="flex-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-200 border border-emerald-400/40 font-bold text-xs h-9" data-testid="save-anytime-btn">
                  <Save className="w-3.5 h-3.5 ms-1.5" /> احفظ المشروع باسمه
                </Button>
              </div>
            )}
            {questionType === 'yes_no' && (
              <div className="flex gap-2 mb-2">
                <button
                  onClick={() => send(options?.[1] || 'لا')}
                  disabled={sending}
                  className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-br from-rose-500/20 to-rose-700/20 border-2 border-rose-400/40 text-rose-100 font-black hover:scale-[1.02] active:scale-95 transition disabled:opacity-50"
                  data-testid="quick-no-btn"
                >{options?.[1] || 'لا'}</button>
                <button
                  onClick={() => send(options?.[0] || 'نعم')}
                  disabled={sending}
                  className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-700/20 border-2 border-emerald-400/50 text-emerald-100 font-black hover:scale-[1.02] active:scale-95 transition disabled:opacity-50"
                  data-testid="quick-yes-btn"
                >{options?.[0] || 'نعم'}</button>
              </div>
            )}
            {attachments.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-1.5" data-testid="freebuild-attachments-list">
                {attachments.map((file, idx) => (
                  <div key={`${file.name}-${idx}`} className="flex items-center gap-1.5 max-w-full px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-[11px] text-white/75">
                    {fileLabelIcon(file) === 'image' ? <ImageIcon className="w-3 h-3 text-emerald-300" /> : fileLabelIcon(file) === 'video' ? <Video className="w-3 h-3 text-sky-300" /> : <FileAudio className="w-3 h-3 text-rose-300" />}
                    <span className="truncate max-w-[150px]">{file.name || 'ملف مرفق'}</span>
                    <button onClick={() => removeAttachment(idx)} className="text-white/40 hover:text-rose-300" disabled={sending} title="إزالة">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <input
              id="freebuild-file-input"
              ref={fileInputRef}
              type="file"
              accept="image/*,video/*,audio/*"
              multiple
              className="sr-only"
              onChange={(e) => {
                addFiles(e.target.files);
                e.target.value = '';
              }}
              data-testid="freebuild-file-input"
            />
            <input
              ref={audioCaptureInputRef}
              type="file"
              accept="audio/*"
              capture="microphone"
              className="sr-only"
              onChange={(e) => {
                addFiles(e.target.files);
                e.target.value = '';
              }}
              data-testid="freebuild-audio-capture-input"
            />
            <div className="flex items-end gap-2" data-testid="chat-input-bar">
              <label
                htmlFor="freebuild-file-input"
                aria-disabled={sending}
                className={`h-[42px] w-[42px] rounded-xl bg-white/5 border border-white/10 text-white/70 hover:text-amber-300 hover:border-amber-400/40 flex items-center justify-center cursor-pointer ${sending ? 'opacity-50 pointer-events-none' : ''}`}
                title="إرفاق صورة أو فيديو أو صوت"
                data-testid="freebuild-attach-btn"
              >
                <Paperclip className="w-4 h-4" />
              </label>
              <button
                type="button"
                onClick={() => {
                  if (isRecording) return stopRecording();
                  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
                    audioCaptureInputRef.current?.click();
                    return;
                  }
                  return startRecording();
                }}
                disabled={sending || transcribing}
                className={`h-[42px] min-w-[42px] px-3 rounded-xl border flex items-center justify-center gap-1.5 disabled:opacity-50 ${isRecording ? 'bg-rose-500/20 border-rose-400/50 text-rose-200 animate-pulse' : 'bg-white/5 border-white/10 text-white/70 hover:text-rose-300 hover:border-rose-400/40'}`}
                title={isRecording ? 'إيقاف التسجيل وتحويله لنص' : 'تسجيل صوت أو فتح مسجل الجوال'}
                data-testid="freebuild-record-btn"
              >
                {transcribing ? <Loader2 className="w-4 h-4 animate-spin" /> : isRecording ? <Square className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                {isRecording && <span className="text-[11px] font-bold">{recordingSeconds}s</span>}
              </button>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                placeholder={questionType === 'yes_no' ? 'أو اكتب إجابة مخصّصة...' : (htmlStarted ? 'وسّع الموقع أو ارفق صورة/فيديو كمرجع...' : 'اكتب جوابك هنا...')}
                rows={1}
                disabled={sending}
                className="flex-1 resize-none bg-black/50 border border-amber-400/20 rounded-xl px-3 py-2.5 text-white placeholder:text-white/35 focus:border-amber-400/60 focus:outline-none text-sm"
                data-testid="chat-input-textarea"
                style={{ minHeight: '42px', maxHeight: '120px' }}
              />
              <Button
                onClick={() => send()}
                disabled={sending || (!input.trim() && attachments.length === 0)}
                className="bg-gradient-to-br from-amber-500 to-yellow-500 text-black font-black h-[42px] px-4 flex-shrink-0 disabled:opacity-50"
                data-testid="chat-send-btn"
              >
                {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </Button>
            </div>
            <div className="mt-1.5 text-[10px] text-white/35 flex justify-between" data-tools-version={FREEBUILD_TOOLS_VERSION}>
              <span>{turns} دورة · {htmlStarted ? 'التصميم قيد البناء' : 'جمع فكرة'}</span>
              <span>{htmlStarted ? '3 نقاط/تحديث' : 'الأسئلة مجانية'} · أدوات محدثة</span>
            </div>
          </div>
        </div>

        {/* ===== RIGHT: LIVE PREVIEW ===== */}
        <div className="flex-1 flex flex-col bg-[#0d0d18]" data-testid="preview-panel">
          <div className="flex-shrink-0 px-4 py-2 flex items-center justify-between border-b border-amber-400/10 bg-black/40">
            <div className="flex items-center gap-2 text-xs text-white/60">
              <Eye className="w-3.5 h-3.5" />
              <span>المعاينة المباشرة</span>
              {htmlStarted && (
                <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 border border-emerald-400/30 text-emerald-300 text-[10px] font-bold animate-pulse">
                  LIVE
                </span>
              )}
            </div>
            {previewUrl && htmlStarted && (
              <a
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-amber-300 hover:text-amber-200 flex items-center gap-1"
                data-testid="open-preview-new-tab"
              >
                <ExternalLink className="w-3 h-3" /> تبويب جديد
              </a>
            )}
          </div>
          <div className="flex-1 p-2 sm:p-3">
            {previewUrl ? (
              <iframe
                src={previewUrl}
                title="Live preview"
                className="w-full h-full rounded-xl bg-white border-0 shadow-lg shadow-black/50"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                allow="autoplay; encrypted-media; fullscreen; microphone"
                data-testid="preview-iframe"
              />
            ) : (
              <div className="w-full h-full rounded-xl bg-black/40 flex items-center justify-center text-white/40 text-sm">
                <Loader2 className="w-5 h-5 animate-spin" />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* SAVE MODAL */}
      {saveOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4" onClick={() => setSaveOpen(false)} data-testid="save-modal">
          <div className="bg-[#0c0c18] border border-amber-400/25 rounded-2xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-black mb-4">احفظ الموقع</h3>
            <Input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="اسم الموقع (مثلاً: موقع تحفيظ القرآن)"
              className="bg-black/50 border-amber-400/20 text-white mb-4"
              data-testid="save-project-name-input"
            />
            <div className="flex gap-2">
              <Button onClick={() => setSaveOpen(false)} variant="outline" className="flex-1 border-white/20 text-white/80" data-testid="save-cancel-btn">إلغاء</Button>
              <Button onClick={saveAsProject} disabled={!projectName.trim()} className="flex-1 bg-emerald-500 hover:bg-emerald-400 text-black font-black disabled:opacity-50" data-testid="save-confirm-btn">
                <Save className="w-4 h-4 ms-2" /> احفظ
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* GALLERY MODAL */}
      {galleryOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-start justify-center p-4 overflow-auto" onClick={() => setGalleryOpen(false)} data-testid="gallery-modal">
          <div className="bg-[#0c0c18] border border-amber-400/25 rounded-2xl max-w-3xl w-full p-6 my-10" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-black mb-4">مواقعي المحفوظة ({gallery.length})</h3>
            {gallery.length === 0 ? (
              <div className="text-center py-10 text-white/50">لا يوجد مواقع محفوظة بعد</div>
            ) : (
              <div className="grid gap-2">
                {gallery.map((p) => (
                  <div key={p.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.04] border border-white/10 hover:border-amber-400/30 transition">
                    <div className="flex-1">
                      <div className="font-bold text-sm">{p.name}</div>
                      <div className="text-[11px] text-white/40">
                        {new Date(p.created_at).toLocaleDateString('ar')} · إصدار {p.version} · {p.credits_spent} نقطة
                      </div>
                    </div>
                    <a
                      href={`${API}/api/freebuild/v2/project-preview/${p.id}`}
                      target="_blank" rel="noopener noreferrer"
                      className="text-amber-300 hover:text-amber-200 flex items-center gap-1 text-xs"
                      data-testid={`gallery-open-${p.id}`}
                    >
                      <ExternalLink className="w-3.5 h-3.5" /> فتح
                    </a>
                    <button onClick={() => deleteProject(p.id)} className="text-rose-400 hover:text-rose-300" data-testid={`gallery-delete-${p.id}`}>
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <Button onClick={() => setGalleryOpen(false)} variant="outline" className="w-full mt-4 border-white/20" data-testid="gallery-close-btn">إغلاق</Button>
          </div>
        </div>
      )}

      {/* NAV EDITOR MODAL */}
      {navEditorOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-start justify-center p-4 overflow-auto" onClick={() => setNavEditorOpen(false)} data-testid="nav-editor-modal">
          <div className="bg-[#0c0c18] border border-amber-400/25 rounded-2xl max-w-2xl w-full p-6 my-10" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-black flex items-center gap-2">
                <Pencil className="w-4 h-4 text-amber-300" /> تحرير التبويبات
              </h3>
              <button onClick={() => setNavEditorOpen(false)} className="text-white/50 hover:text-white" data-testid="nav-editor-close">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-white/50 mb-4">
              غيّر ترتيب التبويبات، أعد تسميتها، احذفها، أو أضف صفحة جديدة (الذكاء يبنيها كاملة).
            </p>

            {navLoading && (
              <div className="flex items-center gap-2 text-amber-300 text-sm mb-3" data-testid="nav-editor-loading">
                <Loader2 className="w-4 h-4 animate-spin" /> جاري المعالجة...
              </div>
            )}

            {/* Existing tabs list */}
            <div className="space-y-2 mb-6 max-h-[40vh] overflow-y-auto">
              {navLinks.length === 0 ? (
                <div className="text-center py-6 text-white/50 text-sm">لا توجد تبويبات</div>
              ) : (
                navLinks.map((link, idx) => (
                  <div
                    key={link.id}
                    className="flex items-center gap-2 p-2.5 rounded-xl bg-white/[0.04] border border-white/10 hover:border-amber-400/30 transition"
                    data-testid={`nav-tab-row-${link.id}`}
                  >
                    <div className="flex flex-col gap-0.5">
                      <button
                        onClick={() => moveTab(idx, -1)}
                        disabled={idx === 0 || navLoading}
                        className="text-white/40 hover:text-amber-300 disabled:opacity-30"
                        data-testid={`nav-up-${link.id}`}
                      >
                        <ChevronUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => moveTab(idx, 1)}
                        disabled={idx === navLinks.length - 1 || navLoading}
                        className="text-white/40 hover:text-amber-300 disabled:opacity-30"
                        data-testid={`nav-down-${link.id}`}
                      >
                        <ChevronDown className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <GripVertical className="w-4 h-4 text-white/30 flex-shrink-0" />
                    <div className="flex-1">
                      <div className="font-bold text-sm">{link.label}</div>
                      <div className="text-[10px] text-white/40 font-mono">#/{link.id}</div>
                    </div>
                    <button
                      onClick={() => renameTab(link.id)}
                      disabled={navLoading}
                      className="text-amber-300 hover:text-amber-200 p-1.5"
                      title="إعادة تسمية"
                      data-testid={`nav-rename-${link.id}`}
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => deleteTab(link.id)}
                      disabled={navLoading || link.id === 'home'}
                      className="text-rose-400 hover:text-rose-300 disabled:opacity-30 p-1.5"
                      title={link.id === 'home' ? 'لا يمكن حذف الرئيسية' : 'حذف'}
                      data-testid={`nav-delete-${link.id}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Add new tab */}
            <div className="border-t border-white/10 pt-4">
              <div className="text-sm font-bold mb-2 flex items-center gap-2">
                <Plus className="w-4 h-4 text-emerald-400" /> إضافة تبويب جديد
                <span className="text-[10px] text-amber-300/80 font-normal mr-auto">(3 نقاط — الذكاء يبني الصفحة كاملة)</span>
              </div>
              <Input
                value={newTabLabel}
                onChange={(e) => setNewTabLabel(e.target.value)}
                placeholder="اسم التبويب (مثلاً: لوحة الوالدين)"
                className="bg-black/40 border-white/15 mb-2"
                data-testid="new-tab-label"
                disabled={addingTab}
              />
              <Textarea
                value={newTabBrief}
                onChange={(e) => setNewTabBrief(e.target.value)}
                placeholder="(اختياري) شنو يحتوي القسم؟ مثلاً: لوحة فيها متابعة تقدم الأطفال + رصيد المكافآت + زر تحويل"
                className="bg-black/40 border-white/15 mb-3 min-h-[70px]"
                data-testid="new-tab-brief"
                disabled={addingTab}
              />
              <Button
                onClick={addTab}
                disabled={addingTab || !newTabLabel.trim()}
                className="w-full bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-black font-black"
                data-testid="add-tab-btn"
              >
                {addingTab ? <><Loader2 className="w-4 h-4 animate-spin mr-2" /> الذكاء يبني الصفحة...</> : <><Plus className="w-4 h-4 mr-1" /> أضف وابني الصفحة</>}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* CONSTRAINTS MODAL */}
      {constraintsOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-start justify-center p-4 overflow-auto" onClick={() => setConstraintsOpen(false)} data-testid="constraints-modal">
          <div className="bg-[#0c0c18] border border-rose-400/30 rounded-2xl max-w-2xl w-full p-6 my-10" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-black flex items-center gap-2">
                <X className="w-4 h-4 text-rose-400" /> القيود الدائمة (الممنوعات)
              </h3>
              <button onClick={() => setConstraintsOpen(false)} className="text-white/50 hover:text-white" data-testid="constraints-close">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-white/55 mb-4 leading-relaxed">
              هذي قواعد ثابتة الذكاء راح يحترمها في كل تحديث قادم — ما بترجع تتغيّر مع الوقت.
              مثال: "ما أبي اللون الأحمر"، "ممنوع الإيموجي"، "لا تحط آيات قرآن مكتوبة".
              <br/>
              <span className="text-amber-300/80">💡 الذكاء يلتقط القيود تلقائياً من رسائلك — تقدر تشيك هنا أو تضيف يدوياً.</span>
            </p>

            <div className="space-y-2 mb-5 max-h-[40vh] overflow-y-auto">
              {constraints.length === 0 ? (
                <div className="text-center py-6 text-white/40 text-sm">لا توجد قيود محفوظة بعد</div>
              ) : (
                constraints.map((c) => (
                  <div
                    key={c.id}
                    className="flex items-start gap-2 p-3 rounded-xl bg-rose-500/[0.06] border border-rose-400/20"
                    data-testid={`constraint-row-${c.id}`}
                  >
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-rose-400/20 text-rose-200 flex-shrink-0">
                      {c.category}
                    </span>
                    <div className="flex-1 text-sm text-white/85 leading-relaxed">{c.rule}</div>
                    <button
                      onClick={() => deleteConstraint(c.id)}
                      className="text-rose-400 hover:text-rose-300 p-1 flex-shrink-0"
                      title="حذف القيد"
                      data-testid={`constraint-delete-${c.id}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="border-t border-white/10 pt-4">
              <div className="text-sm font-bold mb-2 flex items-center gap-2">
                <Plus className="w-4 h-4 text-rose-400" /> أضف قيد يدوي
              </div>
              <Textarea
                value={newConstraintText}
                onChange={(e) => setNewConstraintText(e.target.value)}
                placeholder="اكتب القيد بوضوح، مثلاً: 'ممنوع استخدام الخط Cairo' أو 'لا تحط أي صور بشرية'"
                className="bg-black/40 border-white/15 mb-3 min-h-[70px]"
                data-testid="new-constraint-text"
              />
              <Button
                onClick={addConstraint}
                disabled={!newConstraintText.trim()}
                className="w-full bg-gradient-to-r from-rose-500 to-rose-600 hover:from-rose-400 hover:to-rose-500 text-white font-black"
                data-testid="add-constraint-btn"
              >
                <Plus className="w-4 h-4 mr-1" /> احفظ القيد
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FreeBuild;
