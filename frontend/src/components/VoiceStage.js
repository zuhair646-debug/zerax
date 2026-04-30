/**
 * Voice Stage v3 — fully voice-first immersive AI experience.
 *
 * NEW v3:
 *   - Auto-greet on open: AI speaks first using user's name
 *   - User name input (small badge top-corner)
 *   - Walking characters in background (not static)
 *   - Intent extraction: when user says "ابغى صورة لكافيه" → auto-navigate to /chat/image
 *     with subject pre-filled (passed via URL state)
 *   - HD TTS quality + cleaner Arabic pronunciation
 *   - Faster responses (Haiku for greetings)
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic, MicOff, X, Volume2, VolumeX, Sparkles, User as UserIcon } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const SR = (typeof window !== 'undefined') && (window.SpeechRecognition || window.webkitSpeechRecognition);

function getAnonId() {
  if (typeof window === 'undefined') return null;
  let id = localStorage.getItem('zitex_anon_id');
  if (!id) {
    id = 'anon_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
    localStorage.setItem('zitex_anon_id', id);
  }
  return id;
}

function getStoredName() {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('zitex_user_name') || '';
}

function setStoredName(name) {
  try { localStorage.setItem('zitex_user_name', name); } catch (_) {}
}

function getTimeHint() {
  const h = new Date().getHours();
  if (h >= 5 && h < 12) return 'morning';
  if (h >= 12 && h < 17) return 'afternoon';
  if (h >= 17 && h < 21) return 'evening';
  return 'night';
}

export default function VoiceStage({ open, onClose, initialCharacter = 'zara', mode = 'main', onSignupNeeded }) {
  const navigate = useNavigate();
  const [primary, setPrimary] = useState(initialCharacter);
  const [zaraState, setZaraState] = useState('hidden');
  const [laylaState, setLaylaState] = useState('hidden');
  const [stage, setStage] = useState('intro');
  const [listening, setListening] = useState(false);
  const [muted, setMuted] = useState(false);
  const [transcriptVisible, setTranscriptVisible] = useState(false);
  const [lastUserSaid, setLastUserSaid] = useState('');
  const [lastAIReply, setLastAIReply] = useState('');
  const [lastBanter, setLastBanter] = useState(null);
  const [subtitle, setSubtitle] = useState('');
  const [lipSyncTick, setLipSyncTick] = useState(0);
  const [anonUsage, setAnonUsage] = useState(null);
  const [userName, setUserName] = useState(getStoredName());
  const [showNamePrompt, setShowNamePrompt] = useState(!getStoredName());
  const [tempName, setTempName] = useState('');
  const recRef = useRef(null);
  const audioRef = useRef(null);
  const banterAudioRef = useRef(null);
  const sessionRef = useRef(null);
  const lipSyncIntervalRef = useRef(null);
  const greetedRef = useRef(false);
  const autoListenRef = useRef(false);
  const startListeningRef = useRef(null);
  const stageRef = useRef('intro');

  const isAuthed = !!(typeof window !== 'undefined' && localStorage.getItem('token'));
  const anonId = !isAuthed && mode === 'main' ? getAnonId() : null;

  // ===== Entrance + auto-greet =====
  useEffect(() => {
    if (!open) {
      setZaraState('hidden');
      setLaylaState('hidden');
      setStage('intro');
      greetedRef.current = false;
      autoListenRef.current = false;
      if (recRef.current) try { recRef.current.stop(); } catch (_) {}
      return;
    }
    const t1 = setTimeout(() => setZaraState('entering'), 100);
    const t2 = setTimeout(() => setLaylaState('entering'), 400);
    const t3 = setTimeout(() => { setZaraState('idle'); setLaylaState('idle'); setStage('idle'); }, 2200);
    sessionRef.current = `stage-${Date.now()}`;
    if (anonId) {
      fetch(`${API}/api/avatar/anon-usage?anon_id=${anonId}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => d && setAnonUsage(d))
        .catch(() => {});
    }
    // Auto-greet — wait until characters land + user has name
    const t4 = setTimeout(() => {
      if (!greetedRef.current && userName && !showNamePrompt) {
        greetedRef.current = true;
        autoGreet();
      } else if (!userName) {
        setSubtitle('اكتب اسمك عشان أسلم عليك يا غالي');
      }
    }, 2500);
    return () => [t1, t2, t3, t4].forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Greet right after name is provided
  useEffect(() => {
    if (open && userName && !showNamePrompt && !greetedRef.current && stage === 'idle') {
      greetedRef.current = true;
      autoGreet();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showNamePrompt, userName, stage, open]);

  // ===== Cleanup =====
  useEffect(() => () => {
    if (recRef.current) try { recRef.current.stop(); } catch (_) {}
    if (audioRef.current) try { audioRef.current.pause(); } catch (_) {}
    if (banterAudioRef.current) try { banterAudioRef.current.pause(); } catch (_) {}
    if (lipSyncIntervalRef.current) clearInterval(lipSyncIntervalRef.current);
  }, []);

  // ===== Character state mapping =====
  useEffect(() => {
    stageRef.current = stage;
    if (stage === 'idle') {
      setZaraState('idle'); setLaylaState('idle');
    } else if (stage === 'listening') {
      if (primary === 'zara') { setZaraState('listening'); setLaylaState('idle'); }
      else { setLaylaState('listening'); setZaraState('idle'); }
    } else if (stage === 'speaking') {
      if (primary === 'zara') { setZaraState('talking'); setLaylaState('listening'); }
      else { setLaylaState('talking'); setZaraState('listening'); }
    } else if (stage === 'banter') {
      if (primary === 'zara') { setLaylaState('talking'); setZaraState('listening'); }
      else { setZaraState('talking'); setLaylaState('listening'); }
    } else if (stage === 'thinking') {
      setZaraState('idle'); setLaylaState('idle');
    }
  }, [stage, primary]);

  // ===== Lip-sync =====
  const startLipSync = useCallback(() => {
    if (lipSyncIntervalRef.current) clearInterval(lipSyncIntervalRef.current);
    lipSyncIntervalRef.current = setInterval(() => setLipSyncTick(t => (t + 1) % 3), 140);
  }, []);
  const stopLipSync = useCallback(() => {
    if (lipSyncIntervalRef.current) { clearInterval(lipSyncIntervalRef.current); lipSyncIntervalRef.current = null; }
    setLipSyncTick(0);
  }, []);

  // ===== Auto-greet =====
  const autoGreet = async () => {
    setStage('thinking');
    setSubtitle('...');
    try {
      const r = await fetch(`${API}/api/avatar/greet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ primary, user_name: userName, time_hint: getTimeHint(), want_voice: !muted }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'fail');
      setLastAIReply(d.reply);
      setSubtitle(d.reply);
      setStage('speaking');
      if (d.audio_url && !muted) {
        const audio = new Audio(d.audio_url);
        audio.onplay = () => startLipSync();
        audio.onended = () => {
          stopLipSync();
          setStage('idle');
          setSubtitle('كلّمني... أنا أسمعك الحين');
          kickAutoListen();
        };
        audio.onerror = () => { stopLipSync(); setStage('idle'); kickAutoListen(); };
        audioRef.current = audio;
        audio.play().catch(() => { stopLipSync(); setStage('idle'); kickAutoListen(); });
      } else {
        setTimeout(() => { setStage('idle'); setSubtitle('كلّمني... أنا أسمعك'); kickAutoListen(); }, 3000);
      }
    } catch (e) {
      setStage('idle');
      setSubtitle(`هلا ${userName}! وش تبغى نسوي؟`);
      kickAutoListen();
    }
  };

  // ===== Listening (auto-VAD: continuous; restarts after AI finishes) =====
  const startListening = useCallback(() => {
    if (!SR) {
      toast.error('المتصفح ما يدعم الصوت — جرّب Chrome');
      return;
    }
    if (listening) return;
    if (anonUsage && anonUsage.blocked) {
      if (onSignupNeeded) onSignupNeeded();
      return;
    }
    try {
      const rec = new SR();
      rec.lang = 'ar-SA';
      rec.continuous = true;          // Keep listening continuously
      rec.interimResults = true;
      rec.maxAlternatives = 1;
      rec.onstart = () => { setListening(true); setStage('listening'); setSubtitle('أنا أسمعك... تكلم معي'); };
      rec.onresult = (e) => {
        const txt = Array.from(e.results).map(r => r[0].transcript).join(' ');
        setLastUserSaid(txt);
        if (e.results[e.results.length - 1].isFinal && txt.trim().length >= 2) {
          // Stop listening, send, then resume after AI finishes
          try { rec.stop(); } catch (_) {}
          handleUserSpeech(txt.trim());
        }
      };
      rec.onerror = (e) => {
        if (e.error === 'no-speech') {
          // Auto-restart after a moment
          setTimeout(() => {
            if (recRef.current === rec && stageRef.current !== 'speaking' && stageRef.current !== 'banter' && autoListenRef.current) {
              try { rec.start(); } catch (_) {}
            }
          }, 800);
        } else if (e.error === 'not-allowed') {
          toast.error('فعّلي إذن المايكروفون عشان أسمعك');
          setListening(false); setStage('idle');
          autoListenRef.current = false;
        } else if (e.error !== 'aborted') {
          setListening(false); setStage('idle');
        }
      };
      rec.onend = () => {
        // Auto-restart the recognition loop while we're still "listening" mode
        // and the AI isn't currently talking.
        setListening(false);
        if (autoListenRef.current && stageRef.current !== 'speaking' && stageRef.current !== 'banter' && stageRef.current !== 'thinking') {
          setTimeout(() => {
            if (autoListenRef.current && recRef.current === rec) {
              try { rec.start(); } catch (_) {}
            }
          }, 300);
        }
      };
      rec.start();
      recRef.current = rec;
      autoListenRef.current = true;
    } catch (_) {
      toast.error('فشل المايك');
      setListening(false);
    }
  }, [listening, anonUsage, onSignupNeeded]);

  // Keep a stable ref to startListening so audio callbacks can trigger VAD
  useEffect(() => { startListeningRef.current = startListening; }, [startListening]);

  // Helper: kick off auto-listen after AI finishes speaking
  const kickAutoListen = useCallback(() => {
    // If user muted, or name prompt is showing, or we're navigating away, skip
    if (muted || showNamePrompt) return;
    if (anonUsage && anonUsage.blocked) return;
    setTimeout(() => {
      if (startListeningRef.current && stageRef.current === 'idle') {
        startListeningRef.current();
      }
    }, 400);
  }, [muted, showNamePrompt, anonUsage]);

  const stopListening = useCallback(() => {
    autoListenRef.current = false;
    if (recRef.current) try { recRef.current.stop(); } catch (_) {}
    setListening(false);
    if (stage === 'listening') setStage('idle');
  }, [stage]);

  // ===== Send to backend + handle intent routing =====
  const handleUserSpeech = async (text) => {
    if (!text) return;
    setStage('thinking');
    setSubtitle('...');
    try {
      const endpoint = mode === 'companion' ? '/api/companion/voice-chat' : '/api/avatar/chat';
      const headers = { 'Content-Type': 'application/json' };
      const token = localStorage.getItem('token');
      if (token) headers.Authorization = `Bearer ${token}`;
      const body = mode === 'companion'
        ? { message: text, want_voice: !muted }
        : {
            message: text, session_id: sessionRef.current, want_voice: !muted,
            primary, anon_id: anonId, dual_banter: !muted && !text.match(/^(نعم|لا|اوكي|تمام|اي)$/i),
            user_name: userName || null, detect_intent: true,
          };
      const r = await fetch(`${API}${endpoint}`, { method: 'POST', headers, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');

      setLastAIReply(d.reply);
      setSubtitle(d.reply);
      setLastBanter(d.banter || null);
      if (d.anon_usage) setAnonUsage(d.anon_usage);

      setStage('speaking');

      // Schedule auto-navigation if intent detected
      const intent = d.intent;
      const shouldNavigate = intent && intent.intent && intent.route && mode !== 'companion';

      const finishAndMaybeNavigate = () => {
        if (shouldNavigate) {
          // Pass extracted subject as URL state via sessionStorage
          if (intent.subject) {
            sessionStorage.setItem('zitex_voice_intent', JSON.stringify({
              intent: intent.intent,
              subject: intent.subject,
              from_voice: true,
              ts: Date.now(),
            }));
          }
          setTimeout(() => {
            onClose && onClose();
            navigate(intent.route);
          }, 1200);
        } else {
          setStage('idle');
          setSubtitle('كملي... كلّمني تاني');
          kickAutoListen();
        }
      };

      if (d.audio_url && !muted) {
        const audio = new Audio(d.audio_url);
        audio.onplay = () => startLipSync();
        audio.onended = async () => {
          stopLipSync();
          if (d.banter && d.banter.audio_url && !muted) {
            await new Promise(r => setTimeout(r, 250));
            setStage('banter');
            setSubtitle(`${d.banter.from_char === 'zara' ? 'زارا' : 'ليلى'}: ${d.banter.text}`);
            const b = new Audio(d.banter.audio_url);
            b.onplay = () => startLipSync();
            b.onended = () => { stopLipSync(); finishAndMaybeNavigate(); };
            b.onerror = () => { stopLipSync(); finishAndMaybeNavigate(); };
            banterAudioRef.current = b;
            b.play().catch(() => { stopLipSync(); finishAndMaybeNavigate(); });
          } else {
            finishAndMaybeNavigate();
          }
        };
        audio.onerror = () => { stopLipSync(); finishAndMaybeNavigate(); };
        audioRef.current = audio;
        audio.play().catch(() => { stopLipSync(); finishAndMaybeNavigate(); });
      } else {
        setTimeout(finishAndMaybeNavigate, 2500);
      }
    } catch (e) {
      toast.error(e.message);
      setStage('idle');
      setSubtitle('حصل خطأ — جرّب تاني');
      if (e.message && e.message.includes('انتهت')) onSignupNeeded && onSignupNeeded();
    }
  };

  const toggleMute = () => {
    const nxt = !muted;
    setMuted(nxt);
    if (nxt) {
      if (audioRef.current) try { audioRef.current.pause(); } catch (_) {}
      if (banterAudioRef.current) try { banterAudioRef.current.pause(); } catch (_) {}
    }
  };

  const switchPrimary = () => {
    setPrimary(p => p === 'zara' ? 'layla' : 'zara');
    setSubtitle('بدّلت لرفيقتك الثانية');
    setTimeout(() => setSubtitle('كلّمني...'), 1500);
  };

  const submitName = () => {
    const n = tempName.trim();
    if (!n || n.length < 2) { toast.error('اكتب اسمك بشكل صحيح'); return; }
    setStoredName(n);
    setUserName(n);
    setShowNamePrompt(false);
  };

  if (!open) return null;

  const pickImage = (char, state) => {
    const base = char === 'zara' ? 'zara' : 'layla';
    if (state === 'talking') {
      return lipSyncTick % 2 === 0 ? `/avatars/${base}_idle.png` : `/avatars/${base}_talk.png`;
    }
    return `/avatars/${base}_idle.png`;
  };

  return (
    <div className="fixed inset-0 z-[100] overflow-hidden" data-testid="voice-stage">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#1a0a2e] via-[#0a0a12] to-[#2a0a1e]">
        <div className="absolute inset-0 opacity-40">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-amber-500/20 rounded-full blur-[120px] animate-pulse" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }} />
        </div>
        <div className="absolute inset-0 opacity-60" style={{
          backgroundImage: 'radial-gradient(1px 1px at 20% 30%, white 50%, transparent), radial-gradient(1px 1px at 50% 70%, white 50%, transparent), radial-gradient(1.5px 1.5px at 80% 20%, white 50%, transparent), radial-gradient(1px 1px at 30% 90%, white 50%, transparent), radial-gradient(1px 1px at 70% 50%, white 50%, transparent)',
          backgroundSize: '300px 300px',
        }} />
      </div>

      <div className="absolute bottom-0 left-0 right-0 h-1/3 bg-gradient-to-t from-black/60 to-transparent pointer-events-none" />

      {/* Top buttons */}
      <button onClick={onClose} className="absolute top-4 right-4 w-11 h-11 rounded-full bg-white/10 border border-white/20 backdrop-blur-md text-white hover:bg-white/20 z-50 flex items-center justify-center" data-testid="vs-close">
        <X className="w-5 h-5" />
      </button>

      <div className="absolute top-4 left-4 flex gap-2 z-50">
        <button onClick={toggleMute} className="w-11 h-11 rounded-full bg-white/10 border border-white/20 backdrop-blur-md text-white hover:bg-white/20 flex items-center justify-center" data-testid="vs-mute">
          {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
        </button>
        {mode !== 'companion' && (
          <button onClick={switchPrimary} className="h-11 px-4 rounded-full bg-white/10 border border-white/20 backdrop-blur-md text-white hover:bg-white/20 text-xs font-black flex items-center" data-testid="vs-swap">
            بدّلي ({primary === 'zara' ? 'لـ ليلى' : 'لـ زارا'})
          </button>
        )}
        {/* User name badge */}
        {userName && !showNamePrompt && (
          <button
            onClick={() => { setTempName(userName); setShowNamePrompt(true); }}
            className="h-11 px-3 rounded-full bg-amber-500/20 border border-amber-400/40 text-amber-200 text-xs font-black flex items-center gap-1"
            data-testid="vs-user-name"
          >
            <UserIcon className="w-3.5 h-3.5" /> {userName}
          </button>
        )}
      </div>

      {/* Anon trial */}
      {anonId && anonUsage && mode === 'main' && (
        <div className={`absolute top-20 left-1/2 -translate-x-1/2 z-50 px-3 py-1 rounded-full text-[11px] font-black backdrop-blur-md ${
          anonUsage.blocked ? 'bg-red-500/30 border border-red-400/50 text-red-200'
          : anonUsage.remaining <= 1 ? 'bg-amber-500/30 border border-amber-400/50 text-amber-200'
          : 'bg-emerald-500/20 border border-emerald-400/40 text-emerald-200'
        }`} data-testid="vs-anon-counter">
          <Sparkles className="w-3 h-3 inline me-1" />
          {anonUsage.blocked ? 'انتهت المحادثات المجانية — سجّل لتكمل' : `محادثات مجانية: ${anonUsage.remaining}/${anonUsage.limit}`}
        </div>
      )}

      {/* Characters with walking idle animation */}
      <Character
        name="zara"
        image={pickImage('zara', zaraState)}
        fallback="/avatars/f1_zara.png"
        state={zaraState}
        side="left"
        isPrimary={primary === 'zara'}
        dataTestId="vs-zara"
      />
      <Character
        name="layla"
        image={pickImage('layla', laylaState)}
        fallback="/avatars/f2_layla.png"
        state={laylaState}
        side="right"
        isPrimary={primary === 'layla'}
        dataTestId="vs-layla"
      />

      {/* Subtitle */}
      <div className="absolute bottom-40 left-1/2 -translate-x-1/2 px-6 py-3 max-w-[90%] bg-black/60 backdrop-blur-xl rounded-2xl border border-white/10 text-white text-center min-h-[56px] flex items-center justify-center transition-all" data-testid="vs-subtitle">
        <div className="text-sm sm:text-base font-bold">{subtitle || '...'}</div>
      </div>

      {/* Mic button */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3 z-40">
        <button
          onClick={listening ? stopListening : startListening}
          disabled={stage === 'thinking' || stage === 'speaking' || stage === 'banter' || showNamePrompt}
          className={`relative w-24 h-24 rounded-full flex items-center justify-center transition-all disabled:opacity-40 ${
            listening ? 'bg-red-500 shadow-[0_0_60px_rgba(239,68,68,0.8)] scale-110'
            : stage === 'thinking' ? 'bg-purple-500'
            : (stage === 'speaking' || stage === 'banter') ? 'bg-emerald-500 shadow-[0_0_60px_rgba(16,185,129,0.8)]'
            : 'bg-gradient-to-br from-amber-500 to-yellow-500 hover:scale-110 shadow-[0_0_40px_rgba(245,158,11,0.6)]'
          }`}
          data-testid="vs-mic-btn"
        >
          {listening && <span className="absolute inset-0 rounded-full border-4 border-red-400 animate-ping" />}
          {stage === 'thinking' ? <div className="w-6 h-6 border-4 border-white border-t-transparent rounded-full animate-spin" />
            : listening ? <MicOff className="w-10 h-10 text-white" />
            : <Mic className="w-10 h-10 text-black" />}
        </button>
        <div className="text-[11px] text-white/60 font-bold">
          {listening ? '🎙️ أسمعك الحين — تكلّم' : stage === 'thinking' ? 'تفكر...' : stage === 'speaking' ? 'تتكلم معاك' : stage === 'banter' ? 'تتدخل' : 'اضغط للبدء أو استنى الميكروفون يفتح'}
        </div>
      </div>

      <button onClick={() => setTranscriptVisible(!transcriptVisible)}
        className="absolute bottom-4 right-4 text-[10px] px-2 py-1 rounded-full bg-white/5 border border-white/10 text-white/50 hover:text-white/80 z-40"
        data-testid="vs-transcript-toggle">
        {transcriptVisible ? 'إخفاء النص' : 'عرض النص'}
      </button>

      {transcriptVisible && (lastUserSaid || lastAIReply) && (
        <div className="absolute top-32 left-4 right-4 max-w-2xl mx-auto bg-black/70 backdrop-blur-xl rounded-2xl border border-white/10 p-3 text-white text-sm z-40 space-y-2" data-testid="vs-transcript">
          {lastUserSaid && <div><span className="text-amber-300 font-black">أنت:</span> {lastUserSaid}</div>}
          {lastAIReply && <div><span className="text-purple-300 font-black">{primary === 'zara' ? 'زارا' : 'ليلى'}:</span> {lastAIReply}</div>}
          {lastBanter && <div><span className="text-pink-300 font-black">{lastBanter.from_char === 'zara' ? 'زارا' : 'ليلى'}:</span> {lastBanter.text}</div>}
        </div>
      )}

      {/* Name prompt overlay */}
      {showNamePrompt && (
        <div className="absolute inset-0 z-[110] bg-black/80 flex items-center justify-center p-4" data-testid="vs-name-prompt">
          <div className="bg-gradient-to-br from-[#2a1a3e] to-[#1a0a2e] rounded-3xl border-2 border-amber-400/40 p-6 max-w-sm w-full text-center" dir="rtl">
            <div className="text-3xl mb-2">👋</div>
            <h3 className="text-xl font-black text-white mb-1">قبل ما نبدأ...</h3>
            <p className="text-sm text-amber-200/80 mb-4">شنو اسمك؟</p>
            <input
              autoFocus
              value={tempName}
              onChange={(e) => setTempName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') submitName(); }}
              placeholder="اسمك"
              className="w-full p-3 mb-3 bg-black/40 border-2 border-amber-400/30 focus:border-amber-400 rounded-xl text-center text-lg text-white outline-none"
              dir="rtl"
              data-testid="vs-name-input"
            />
            <button
              onClick={submitName}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-500 text-black font-black"
              data-testid="vs-name-submit"
            >
              ابدأ
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ============== CHARACTER ==============
function Character({ image, fallback, state, side, isPrimary, dataTestId }) {
  const [imgSrc, setImgSrc] = useState(image);

  useEffect(() => { setImgSrc(image); }, [image]);

  const offScreenX = side === 'left' ? '-110%' : '110%';
  const onScreenX = side === 'left' ? '-15%' : '15%';

  const stateConfig = {
    hidden:    { x: offScreenX, y: '20%', scale: 0.8, opacity: 0,   animClass: '' },
    entering:  { x: onScreenX,  y: '0%',  scale: 1,   opacity: 1,   animClass: 'char-walking' },
    idle:      { x: onScreenX,  y: '0%',  scale: isPrimary ? 1.05 : 0.95, opacity: isPrimary ? 1 : 0.8, animClass: 'char-walking' },
    listening: { x: onScreenX,  y: '-2%', scale: isPrimary ? 1.1  : 0.95, opacity: 1,   animClass: 'char-lean' },
    talking:   { x: onScreenX,  y: '0%',  scale: 1.1, opacity: 1,   animClass: 'char-talk' },
  };
  const cfg = stateConfig[state] || stateConfig.idle;

  return (
    <div
      data-testid={dataTestId}
      className={`absolute bottom-0 ${side === 'left' ? 'left-0' : 'right-0'} w-1/2 sm:w-2/5 max-w-[500px] h-[85%] pointer-events-none ${cfg.animClass}`}
      style={{
        transform: `translate(${cfg.x}, ${cfg.y}) scale(${cfg.scale})`,
        opacity: cfg.opacity,
        transition: 'transform 1.2s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.8s ease',
        transformOrigin: side === 'left' ? 'bottom left' : 'bottom right',
      }}
    >
      <img
        src={imgSrc}
        onError={() => { if (fallback && imgSrc !== fallback) setImgSrc(fallback); }}
        alt=""
        className="w-full h-full object-contain object-bottom avatar-chroma"
        draggable={false}
        style={{
          filter: isPrimary
            ? 'drop-shadow(0 0 40px rgba(245,158,11,0.5)) drop-shadow(0 10px 30px rgba(0,0,0,0.5))'
            : 'drop-shadow(0 10px 30px rgba(0,0,0,0.4))',
        }}
      />
    </div>
  );
}
