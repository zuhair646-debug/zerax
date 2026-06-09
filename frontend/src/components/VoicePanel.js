/**
 * VoicePanel — compact inline voice conversation panel.
 *
 * Replaces the full-screen VoiceStage. When user clicks the mic button,
 * a small panel opens at bottom-right (ChatGPT-style) with:
 *   - Live subtitle (AI response)
 *   - Listening indicator
 *   - Stop / close controls
 *   - No 3D characters, no full-screen overlay
 *
 * When AI detects an intent (image/video/website), navigates to target
 * section AND writes `zerax_voice_intent` to sessionStorage so the
 * section page can auto-fill the prompt.
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { X, Mic, MicOff, Loader2, Coins, Volume2, VolumeX } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const SR = (typeof window !== 'undefined') && (window.SpeechRecognition || window.webkitSpeechRecognition);
const STORE_NAME_KEY = 'zerax_user_name';
const ANON_ID_KEY = 'zerax_anon_id';
const SESSION_KEY = 'zerax_voice_session_id';

function getUserName() {
  try {
    const raw = localStorage.getItem('user');
    if (raw) {
      const u = JSON.parse(raw);
      const n = u?.name || u?.full_name || u?.email?.split('@')[0];
      if (n && n.trim().length >= 2) return n.trim();
    }
  } catch (_) {}
  return localStorage.getItem(STORE_NAME_KEY) || '';
}

function getAnonId() {
  let id = localStorage.getItem(ANON_ID_KEY);
  if (!id) {
    id = 'anon_' + Math.random().toString(36).slice(2, 11) + Date.now().toString(36);
    localStorage.setItem(ANON_ID_KEY, id);
  }
  return id;
}

export default function VoicePanel({ open, onClose, user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [stage, setStage] = useState('idle'); // idle | listening | thinking | speaking
  const [subtitle, setSubtitle] = useState('');
  const [listening, setListening] = useState(false);
  const [muted, setMuted] = useState(false);
  const [credits, setCredits] = useState(user?.credits ?? null);
  const [sessionStarted, setSessionStarted] = useState(false);
  const recRef = useRef(null);
  const audioRef = useRef(null);
  const sessionRef = useRef(null);
  const autoListenRef = useRef(false);
  const stageRef = useRef('idle');
  const startListeningRef = useRef(null);
  const greetOnceRef = useRef(false);

  // Fetch credits on mount
  useEffect(() => {
    if (!open) return;
    const token = localStorage.getItem('token');
    if (!token) return;
    fetch(`${API}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setCredits(d.credits ?? 0))
      .catch(() => {});
  }, [open]);

  useEffect(() => { stageRef.current = stage; }, [stage]);

  // Session id persistence
  useEffect(() => {
    if (!open) return;
    const existing = sessionStorage.getItem(SESSION_KEY);
    if (existing) { sessionRef.current = existing; }
  }, [open]);

  // Start session: auto-greet + begin listening (once per open)
  useEffect(() => {
    if (!open || sessionStarted || greetOnceRef.current) return;
    greetOnceRef.current = true;
    setSessionStarted(true);
    autoGreet();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, sessionStarted]);

  // Graceful close
  const closePanel = useCallback(() => {
    autoListenRef.current = false;
    if (recRef.current) { try { recRef.current.stop(); } catch (_) {} }
    if (audioRef.current) { try { audioRef.current.pause(); } catch (_) {} }
    setListening(false);
    setStage('idle');
    onClose && onClose();
  }, [onClose]);

  // ============ API calls ============
  const autoGreet = async () => {
    setStage('speaking');
    setSubtitle('جاري التحضير...');
    const token = localStorage.getItem('token');
    const hour = new Date().getHours();
    const timeHint = hour < 11 ? 'morning' : hour < 17 ? 'afternoon' : 'evening';
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers.Authorization = `Bearer ${token}`;
      else headers['X-Anon-Id'] = getAnonId();
      const name = getUserName();
      const res = await fetch(`${API}/api/avatar/greet`, {
        method: 'POST', headers,
        body: JSON.stringify({
          primary: 'zara', user_name: name, time_hint: timeHint, want_voice: !muted,
        }),
      });
      if (!res.ok) throw new Error('greet fail');
      const d = await res.json();
      setSubtitle(d.reply || 'هلا! كيف أقدر أساعدك؟');
      sessionRef.current = d.session_id;
      if (d.session_id) sessionStorage.setItem(SESSION_KEY, d.session_id);
      await playAudio(d.audio_url);
    } catch (e) {
      setSubtitle('هلا! أنا زارا، كيف أقدر أخدمك؟');
      setStage('idle');
      kickAutoListen();
    }
  };

  const playAudio = (url) => new Promise((resolve) => {
    if (!url || muted) { setStage('idle'); kickAutoListen(); resolve(); return; }
    // Stop any currently playing audio to prevent double voices
    if (audioRef.current) {
      try { audioRef.current.pause(); audioRef.current.src = ''; } catch (_) {}
      audioRef.current = null;
    }
    try {
      const a = new Audio(url);
      audioRef.current = a;
      a.onended = () => { setStage('idle'); kickAutoListen(); resolve(); };
      a.onerror = () => { setStage('idle'); kickAutoListen(); resolve(); };
      a.play().catch(() => { setStage('idle'); kickAutoListen(); resolve(); });
    } catch (_) { setStage('idle'); kickAutoListen(); resolve(); }
  });

  // ============ Intent routing ============
  const INTENT_ROUTES = {
    image: '/chat/image',
    video: '/chat/video',
    website: '/websites',
    studio: '/dashboard/avatar',
  };

  const sendMessage = async (text) => {
    if (!text || !text.trim()) return;
    setStage('thinking');
    setSubtitle('...');
    const token = localStorage.getItem('token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    else headers['X-Anon-Id'] = getAnonId();
    try {
      const res = await fetch(`${API}/api/avatar/chat`, {
        method: 'POST', headers,
        body: JSON.stringify({
          message: text,
          primary: 'zara',
          session_id: sessionRef.current,
          want_voice: !muted,
          user_name: getUserName(),
          detect_intent: true,
          dual_banter: false,
        }),
      });
      if (!res.ok) throw new Error('chat fail');
      const d = await res.json();
      sessionRef.current = d.session_id;
      if (d.session_id) sessionStorage.setItem(SESSION_KEY, d.session_id);
      setSubtitle(d.reply || '');
      setStage('speaking');
      await playAudio(d.audio_url);

      // If there's an intent with subject, navigate & pass context
      if (d.intent && d.intent.intent && d.intent.intent !== 'unclear' && d.intent.subject) {
        const route = INTENT_ROUTES[d.intent.intent];
        if (route && location.pathname !== route) {
          sessionStorage.setItem('zerax_voice_intent', JSON.stringify({
            intent: d.intent.intent,
            subject: d.intent.subject,
            from_voice: true,
            ts: Date.now(),
          }));
          // Separate key for ZeraxDuoLauncher to re-open panel after navigation
          sessionStorage.setItem('zerax_voice_reopen', JSON.stringify({ ts: Date.now() }));
          toast.success(`تمام! أخذك إلى ${d.intent.intent === 'image' ? 'قسم الصور' : d.intent.intent === 'video' ? 'قسم الفيديو' : 'القسم المطلوب'}`);
          setTimeout(() => navigate(route), 1200);
        }
      }
    } catch (e) {
      setSubtitle('خلل في الاتصال. حاول مرة ثانية');
      setStage('idle');
      kickAutoListen();
    }
  };

  // ============ Speech recognition ============
  const startListening = useCallback(() => {
    if (!SR) { toast.error('متصفحك ما يدعم التعرف الصوتي'); return; }
    if (recRef.current || stageRef.current !== 'idle') return;
    try {
      const rec = new SR();
      rec.lang = 'ar-SA';
      rec.continuous = false;
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      rec.onstart = () => { setListening(true); setStage('listening'); };
      rec.onresult = (e) => {
        const text = e.results[0][0].transcript;
        setListening(false);
        recRef.current = null;
        sendMessage(text);
      };
      rec.onerror = (ev) => {
        setListening(false);
        recRef.current = null;
        if (ev.error === 'not-allowed') { toast.error('فعّل إذن المايكروفون'); autoListenRef.current = false; }
        else if (ev.error === 'no-speech' && autoListenRef.current) {
          setTimeout(() => startListeningRef.current?.(), 800);
        } else { setStage('idle'); }
      };
      rec.onend = () => {
        setListening(false);
        if (recRef.current === rec) recRef.current = null;
      };
      rec.start();
      recRef.current = rec;
      autoListenRef.current = true;
    } catch (_) { setListening(false); }
  }, []);

  useEffect(() => { startListeningRef.current = startListening; }, [startListening]);

  const kickAutoListen = useCallback(() => {
    if (muted) return;
    setTimeout(() => {
      if (stageRef.current === 'idle' && startListeningRef.current) {
        startListeningRef.current();
      }
    }, 500);
  }, [muted]);

  // Cleanup on close
  useEffect(() => {
    if (!open) {
      if (recRef.current) { try { recRef.current.stop(); } catch (_) {} }
      if (audioRef.current) { try { audioRef.current.pause(); } catch (_) {} }
      autoListenRef.current = false;
      setSessionStarted(false);
      greetOnceRef.current = false;
    }
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed bottom-24 right-4 sm:right-6 z-[90] w-[min(92vw,360px)] bg-gradient-to-br from-[#1f1428] to-[#0a0a12] rounded-3xl border border-amber-500/25 shadow-[0_20px_60px_rgba(0,0,0,0.6)] overflow-hidden" dir="rtl" data-testid="voice-panel">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${stage === 'listening' ? 'from-emerald-400 to-teal-500' : stage === 'speaking' ? 'from-amber-400 to-orange-500 animate-pulse' : stage === 'thinking' ? 'from-purple-400 to-pink-500' : 'from-amber-500 to-pink-500'} flex items-center justify-center`}>
            {stage === 'thinking' ? <Loader2 className="w-4 h-4 text-white animate-spin" /> : <Mic className="w-4 h-4 text-white" />}
          </div>
          <div>
            <div className="text-white font-black text-sm">زيتكس الصوتي</div>
            <div className="text-white/50 text-[10px]">
              {stage === 'listening' ? 'أسمعك...' : stage === 'thinking' ? 'يفكر...' : stage === 'speaking' ? 'يتكلم' : 'جاهز'}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {credits !== null && (
            <div className="px-2 h-7 rounded-lg bg-amber-500/15 border border-amber-400/30 text-amber-200 text-[10px] font-black flex items-center gap-1" data-testid="voice-credits">
              <Coins className="w-3 h-3" /> {credits}
            </div>
          )}
          <button onClick={() => setMuted(m => !m)} className="w-7 h-7 rounded-lg bg-white/5 hover:bg-white/15 text-white/70 flex items-center justify-center" data-testid="voice-mute" title={muted ? 'شغّل الصوت' : 'كتم الصوت'}>
            {muted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          </button>
          <button onClick={closePanel} className="w-7 h-7 rounded-lg bg-white/5 hover:bg-white/15 text-white/70 flex items-center justify-center" data-testid="voice-close">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Subtitle area */}
      <div className="px-4 py-5 min-h-[120px] max-h-[180px] overflow-y-auto">
        <p className="text-white/95 text-sm leading-relaxed font-bold whitespace-pre-wrap" data-testid="voice-subtitle">
          {subtitle || 'هلا! اضغط على المايك وكلّمني'}
        </p>
      </div>

      {/* Bottom controls */}
      <div className="px-4 py-3 bg-black/40 border-t border-white/10 flex items-center justify-between">
        <button
          onClick={() => {
            if (listening) {
              try { recRef.current?.stop(); } catch (_) {}
              setListening(false);
              autoListenRef.current = false;
            } else {
              startListening();
            }
          }}
          disabled={stage === 'thinking' || stage === 'speaking'}
          className={`flex-1 h-11 rounded-xl font-black text-xs flex items-center justify-center gap-2 transition ${
            listening
              ? 'bg-red-500 text-white'
              : stage === 'thinking' || stage === 'speaking'
              ? 'bg-white/5 text-white/30 cursor-not-allowed'
              : 'bg-gradient-to-r from-amber-500 to-orange-500 text-black hover:scale-[1.02]'
          }`}
          data-testid="voice-toggle-listen"
        >
          {listening ? <><MicOff className="w-4 h-4" /> أوقف</> : <><Mic className="w-4 h-4" /> كلّمني</>}
        </button>
      </div>
    </div>
  );
}
