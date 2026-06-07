import { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

function getSupportedAudioMimeType() {
  if (typeof window === 'undefined' || !window.MediaRecorder) return '';
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
    'audio/ogg',
  ];
  return types.find((t) => window.MediaRecorder.isTypeSupported(t)) || '';
}

function audioExtension(mimeType) {
  if (mimeType.includes('mp4')) return 'mp4';
  if (mimeType.includes('ogg')) return 'ogg';
  if (mimeType.includes('mpeg')) return 'mp3';
  if (mimeType.includes('wav')) return 'wav';
  return 'webm';
}

/**
 * Self-contained voice recorder button.
 * Props:
 *   onTranscript(text) — called when transcription is ready
 *   accentColor — "amber" | "blue" (default amber)
 *   disabled — boolean
 */
export default function VoiceRecorderButton({ onTranscript, accentColor = 'amber', disabled = false }) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [seconds, setSeconds] = useState(0);

  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      try { mediaRecorderRef.current.stop(); } catch (_) {}
    }
    mediaStreamRef.current?.getTracks?.().forEach((t) => t.stop());
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  const transcribeAudio = async (blob, mimeType) => {
    const token = localStorage.getItem('token');
    if (!token) {
      toast.error('سجّل الدخول أولاً لاستخدام التسجيل الصوتي');
      return;
    }
    if (!blob || blob.size < 300) {
      toast.error('التسجيل قصير جداً، حاول مرة أخرى');
      return;
    }

    setTranscribing(true);
    try {
      const formData = new FormData();
      const ext = audioExtension(mimeType || blob.type || 'audio/webm');
      formData.append('audio', blob, `voice-${Date.now()}.${ext}`);
      formData.append('language', 'ar');

      const res = await fetch(`${API}/api/stt/transcribe`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      let data = {};
      try { data = await res.json(); } catch (_) { data = {}; }
      if (!res.ok) throw new Error(data.detail || data.message || 'فشل تحويل الصوت');
      const text = (data.text || '').trim();
      if (!text) {
        toast.error('ما فهمت الصوت بوضوح. جرّب التسجيل لمدة أطول وبهدوء');
        return;
      }
      onTranscript?.(text);
      toast.success('✓ تم تحويل الصوت إلى نص');
    } catch (e) {
      console.error('voice transcribe error:', e);
      toast.error(e.message || 'فشل تحويل الصوت');
    } finally {
      setTranscribing(false);
    }
  };

  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      toast.error('متصفحك لا يدعم التسجيل الصوتي. جرّب Chrome أو Safari محدث.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = getSupportedAudioMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

      audioChunksRef.current = [];
      mediaStreamRef.current = stream;
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        toast.error('حدث خطأ أثناء التسجيل');
        setRecording(false);
      };
      recorder.onstop = async () => {
        const chunks = audioChunksRef.current;
        const finalMimeType = recorder.mimeType || mimeType || 'audio/webm';
        mediaStreamRef.current?.getTracks?.().forEach((t) => t.stop());
        mediaStreamRef.current = null;
        mediaRecorderRef.current = null;
        setRecording(false);
        if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
        setSeconds(0);
        if (!chunks.length) {
          toast.error('لم يتم التقاط صوت. تأكد من صلاحية الميكروفون');
          return;
        }
        const blob = new Blob(chunks, { type: finalMimeType });
        await transcribeAudio(blob, finalMimeType);
      };

      recorder.start(100);
      setRecording(true);
      setSeconds(0);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch (e) {
      console.error('mic permission denied:', e);
      toast.error('يحتاج إذن الميكروفون. اسمح للموقع وحاول مرة أخرى.');
      setRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      try { mediaRecorderRef.current.stop(); } catch (_) {}
    }
  };

  const click = () => (recording ? stopRecording() : startRecording());

  const colorClass = recording
    ? 'bg-red-500/20 border-red-500/60 text-red-200 animate-pulse'
    : transcribing
    ? 'bg-amber-500/20 border-amber-500/60 text-amber-200'
    : accentColor === 'blue'
    ? 'bg-white/5 hover:bg-blue-500/20 hover:border-blue-400/40 border-white/10 text-blue-200'
    : accentColor === 'emerald'
    ? 'bg-white/5 hover:bg-emerald-500/20 hover:border-emerald-400/40 border-white/10 text-emerald-200'
    : 'bg-white/5 hover:bg-amber-500/20 hover:border-amber-400/40 border-white/10 text-amber-200';

  const label = recording
    ? `جاري التسجيل · ${seconds}s · اضغط للإيقاف`
    : transcribing
    ? 'يحوّل الصوت...'
    : 'تسجيل صوتي';

  return (
    <button
      type="button"
      onClick={click}
      disabled={disabled || transcribing}
      className={`px-4 py-3 border rounded-xl flex items-center gap-2 transition-all ${colorClass} disabled:opacity-50 disabled:cursor-not-allowed`}
      data-testid="voice-record-btn"
      title={label}
      aria-label={label}
    >
      {transcribing ? (
        <Loader2 className="w-5 h-5 animate-spin" />
      ) : recording ? (
        <>
          <MicOff className="w-5 h-5" />
          <span className="text-xs font-bold tabular-nums hidden sm:inline">{seconds}s</span>
        </>
      ) : (
        <Mic className="w-5 h-5" />
      )}
    </button>
  );
}
