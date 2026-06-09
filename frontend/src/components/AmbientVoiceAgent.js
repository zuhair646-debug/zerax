/**
 * AmbientVoiceAgent — Completely invisible voice agent.
 *
 * Behavior:
 *   - Single floating mic button (bottom-right, small)
 *   - Pulses gently when idle
 *   - Always listening in background for wake word "زيتكس"
 *   - On wake: pulse brighter, capture user speech
 *   - AI replies via audio (no chat bubble visible)
 *   - Route navigation happens silently when intent detected
 *   - User never sees a chat panel — just hears the AI
 *
 * Manual trigger: click the mic once to start listening (no panel opens).
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Mic } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const SR = (typeof window !== 'undefined') && (window.SpeechRecognition || window.webkitSpeechRecognition);
const ANON_ID_KEY = 'zerax_anon_id';
const SESSION_KEY = 'zerax_voice_session_id';
const WAKE_PATTERNS = [/ز[يَ]ت[كك]س/i, /zerax/i, /يا\s+زيتكس/i];

function getUserName() {
  try {
    const raw = localStorage.getItem('user');
    if (raw) {
      const u = JSON.parse(raw);
      const n = u?.name || u?.full_name || u?.email?.split('@')[0];
      if (n && n.trim().length >= 2) return n.trim();
    }
  } catch (_) {}
  return localStorage.getItem('zerax_user_name') || '';
}

function getUserGender() {
  // Returns 'male' | 'female' | '' (unknown)
  // Used by the avatar to pick the OPPOSITE-gender voice:
  //   user female → AI replies as male (Mohammed)
  //   user male   → AI replies as female (Layan)
  try {
    const raw = localStorage.getItem('user');
    if (raw) {
      const u = JSON.parse(raw);
      const g = (u?.gender || '').toLowerCase();
      if (g === 'male' || g === 'female') return g;
    }
  } catch (_) {}
  const stored = (localStorage.getItem('zerax_user_gender') || '').toLowerCase();
  if (stored === 'male' || stored === 'female') return stored;
  return '';
}

function getAnonId() {
  let id = localStorage.getItem(ANON_ID_KEY);
  if (!id) {
    id = 'anon_' + Math.random().toString(36).slice(2, 11) + Date.now().toString(36);
    localStorage.setItem(ANON_ID_KEY, id);
  }
  return id;
}

const INTENT_ROUTES = {
  image: '/chat/image',
  video: '/chat/video',
  website: '/websites',
  studio: '/dashboard/avatar',
};

export default function AmbientVoiceAgent() {
  const navigate = useNavigate();
  const location = useLocation();
  const [phase, setPhase] = useState('ambient'); // ambient | listening | thinking | speaking
  const [micOn, setMicOn] = useState(false);
  const recRef = useRef(null);
  const audioRef = useRef(null);
  const sessionRef = useRef(sessionStorage.getItem(SESSION_KEY) || null);
  const phaseRef = useRef('ambient');
  const wakeActiveRef = useRef(false);
  const activeListenRef = useRef(false);
  const cleanupRef = useRef(false);

  useEffect(() => { phaseRef.current = phase; }, [phase]);

  // ============== Audio playback ==============
  const playAudio = useCallback((url) => new Promise((resolve) => {
    if (!url) { resolve(); return; }
    if (audioRef.current) {
      try { audioRef.current.pause(); audioRef.current.src = ''; } catch (_) {}
      audioRef.current = null;
    }
    try {
      const a = new Audio(url);
      audioRef.current = a;
      a.onended = () => { resolve(); };
      a.onerror = () => { resolve(); };
      a.play().catch(() => resolve());
    } catch (_) { resolve(); }
  }), []);

  // ============== Chat backend call ==============
  const sendToAI = useCallback(async (text) => {
    if (!text || !text.trim()) { setPhase('ambient'); return; }
    setPhase('thinking');
    const token = localStorage.getItem('token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    else headers['X-Anon-Id'] = getAnonId();

    try {
      const res = await fetch(`${API}/api/avatar/chat`, {
        method: 'POST', headers,
        body: JSON.stringify({
          message: text,
          session_id: sessionRef.current,
          want_voice: true,
          user_name: getUserName(),
          user_gender: getUserGender(),
          detect_intent: true,
          dual_banter: false,
        }),
      });
      if (!res.ok) throw new Error('chat failed');
      const d = await res.json();
      sessionRef.current = d.session_id;
      if (d.session_id) sessionStorage.setItem(SESSION_KEY, d.session_id);

      setPhase('speaking');
      // Show a quick toast with reply text (so user sees what was said)
      if (d.reply) {
        toast(d.reply, { duration: 6000, position: 'bottom-center' });
      }
      await playAudio(d.audio_url);

      // Navigate if intent routed
      if (d.intent && d.intent.intent && d.intent.intent !== 'unclear' && d.intent.subject) {
        const route = INTENT_ROUTES[d.intent.intent];
        if (route && location.pathname !== route) {
          sessionStorage.setItem('zerax_voice_intent', JSON.stringify({
            intent: d.intent.intent, subject: d.intent.subject, from_voice: true, ts: Date.now(),
          }));
          setTimeout(() => navigate(route), 400);
        }
      }
    } catch (e) {
      toast.error('حصل خلل في الاتصال');
    } finally {
      setPhase('ambient');
    }
  }, [location.pathname, navigate, playAudio]);

  // ============== Active Listening (after wake) ==============
  const startActiveListen = useCallback(() => {
    if (!SR || recRef.current || phaseRef.current === 'thinking' || phaseRef.current === 'speaking') return;
    try {
      const rec = new SR();
      rec.lang = 'ar-SA';
      rec.continuous = false;
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      rec.onstart = () => { setPhase('listening'); };
      rec.onresult = (e) => {
        const text = e.results[0][0].transcript;
        activeListenRef.current = false;
        recRef.current = null;
        sendToAI(text);
      };
      rec.onerror = (ev) => {
        if (recRef.current === rec) recRef.current = null;
        activeListenRef.current = false;
        if (ev.error === 'not-allowed') {
          toast.error('فعّل إذن الميكروفون للاستماع');
        }
        setPhase('ambient');
      };
      rec.onend = () => {
        if (recRef.current === rec) recRef.current = null;
        if (phaseRef.current === 'listening') setPhase('ambient');
      };
      rec.start();
      recRef.current = rec;
      activeListenRef.current = true;
    } catch (_) { setPhase('ambient'); }
  }, [sendToAI]);

  // ============== Wake Word Background Listener ==============
  const startWakeListen = useCallback(() => {
    if (!SR || !micOn || wakeActiveRef.current || activeListenRef.current) return;
    if (phaseRef.current !== 'ambient') return;

    try {
      const rec = new SR();
      rec.lang = 'ar-SA';
      rec.continuous = true;
      rec.interimResults = true;
      rec.maxAlternatives = 1;
      rec.onstart = () => { wakeActiveRef.current = true; };
      rec.onresult = (e) => {
        const latest = e.results[e.results.length - 1];
        if (!latest) return;
        const txt = (latest[0].transcript || '').trim();
        // Check wake word on any result (interim or final)
        for (const p of WAKE_PATTERNS) {
          if (p.test(txt)) {
            try { rec.stop(); } catch (_) {}
            wakeActiveRef.current = false;
            recRef.current = null;
            // Clear the rest (we captured the wake phrase; now listen fresh)
            setTimeout(() => startActiveListen(), 200);
            return;
          }
        }
      };
      rec.onerror = (ev) => {
        wakeActiveRef.current = false;
        if (recRef.current === rec) recRef.current = null;
        if (ev.error === 'not-allowed') {
          setMicOn(false);
          toast.error('ما قدرنا نفعّل الميكروفون');
        } else if (ev.error !== 'aborted' && micOn && !cleanupRef.current) {
          setTimeout(() => { if (!cleanupRef.current) startWakeListen(); }, 1000);
        }
      };
      rec.onend = () => {
        wakeActiveRef.current = false;
        if (recRef.current === rec) recRef.current = null;
        // Auto-restart wake listener while micOn and not busy
        if (micOn && !cleanupRef.current && phaseRef.current === 'ambient' && !activeListenRef.current) {
          setTimeout(() => startWakeListen(), 300);
        }
      };
      rec.start();
      recRef.current = rec;
    } catch (_) { wakeActiveRef.current = false; }
  }, [micOn, startActiveListen]);

  // Toggle mic on/off
  const toggleMic = useCallback(() => {
    const next = !micOn;
    setMicOn(next);
    try { localStorage.setItem('zerax_mic_on', next ? '1' : '0'); } catch (_) {}
    if (!next) {
      // Turn off: stop any running recognition
      if (recRef.current) { try { recRef.current.stop(); } catch (_) {} recRef.current = null; }
      if (audioRef.current) { try { audioRef.current.pause(); } catch (_) {} }
      wakeActiveRef.current = false;
      activeListenRef.current = false;
      setPhase('ambient');
    } else {
      toast.success('تمام، نادني بـ"زيتكس" وكلّمني', { duration: 3500, position: 'bottom-center' });
    }
  }, [micOn]);

  // Restore mic state from localStorage
  useEffect(() => {
    try {
      if (localStorage.getItem('zerax_mic_on') === '1') setMicOn(true);
    } catch (_) {}
  }, []);

  // Start/stop wake listener based on micOn state
  useEffect(() => {
    if (micOn && phase === 'ambient' && !wakeActiveRef.current && !activeListenRef.current) {
      startWakeListen();
    }
    return () => {
      cleanupRef.current = true;
      if (recRef.current) { try { recRef.current.stop(); } catch (_) {} }
      setTimeout(() => { cleanupRef.current = false; }, 100);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [micOn, phase]);

  // Manual single-click: also start active listening
  const onButtonClick = () => {
    if (!micOn) {
      toggleMic();
    } else if (phase === 'ambient') {
      // User wants to talk immediately without wake word
      if (recRef.current) { try { recRef.current.stop(); } catch (_) {} recRef.current = null; }
      wakeActiveRef.current = false;
      setTimeout(() => startActiveListen(), 150);
    }
  };

  // Visual states for the button
  const ring = phase === 'listening'
    ? 'ring-4 ring-emerald-400/70'
    : phase === 'thinking'
    ? 'ring-4 ring-purple-400/70'
    : phase === 'speaking'
    ? 'ring-4 ring-amber-400/70'
    : micOn
    ? 'ring-2 ring-amber-400/40'
    : '';

  const gradient = phase === 'listening'
    ? 'from-emerald-400 to-teal-500'
    : phase === 'thinking'
    ? 'from-purple-500 to-pink-500'
    : phase === 'speaking'
    ? 'from-amber-400 to-orange-500'
    : 'from-amber-500 via-orange-500 to-pink-500';

  return (
    <button
      onClick={onButtonClick}
      data-testid="ambient-voice-button"
      aria-label={micOn ? `نادني بـ"زيتكس" أو اضغط للكلام (${phase})` : 'فعّل الاستماع الصوتي'}
      className={`fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-gradient-to-br ${gradient} text-white shadow-[0_0_28px_rgba(245,158,11,0.55)] flex items-center justify-center hover:scale-110 active:scale-95 transition-all ${ring} group`}
    >
      {/* Breathing pulse when ambient */}
      {phase === 'ambient' && micOn && (
        <span className="absolute inset-0 rounded-full bg-amber-400/20 animate-ping" aria-hidden />
      )}
      {/* Strong pulse while listening */}
      {phase === 'listening' && (
        <>
          <span className="absolute inset-0 rounded-full bg-emerald-400/40 animate-ping" aria-hidden />
          <span className="absolute -inset-1 rounded-full bg-emerald-400/20 animate-pulse" aria-hidden />
        </>
      )}
      {/* Speaking indicator */}
      {phase === 'speaking' && (
        <span className="absolute inset-0 rounded-full bg-amber-400/30 animate-pulse" aria-hidden />
      )}
      <Mic className="w-6 h-6 relative z-10" strokeWidth={2.5} />
      {/* Status dot */}
      {micOn && (
        <span className={`absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full ${phase === 'listening' ? 'bg-emerald-400' : phase === 'speaking' ? 'bg-amber-300' : 'bg-white'} border-2 border-black`} aria-hidden />
      )}
      {/* Tooltip */}
      <span className="absolute bottom-[105%] right-0 mb-2 px-3 py-1.5 rounded-xl bg-black/80 backdrop-blur-md text-white text-[11px] font-black whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" dir="rtl">
        {!micOn
          ? 'اضغط لتفعيل الصوت'
          : phase === 'listening'
          ? '🎙️ أسمعك — كلّم'
          : phase === 'thinking'
          ? '💭 أفكر...'
          : phase === 'speaking'
          ? '🔊 أتكلم'
          : 'نادني "زيتكس" أو اضغط'}
      </span>
    </button>
  );
}
