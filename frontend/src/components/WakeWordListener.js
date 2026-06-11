/**
 * Wake Word Listener — background speech recognition watching for
 * "يا زارا" / "يا ليلى" / "زارا" / "ليلى". On detection, dispatches a
 * custom event `zenrex:wake-word` with {character: 'zara'|'layla'}.
 *
 * - Toggle (on/off) persisted to localStorage.
 * - Auto-pauses when VoiceStage is open (listens for `zenrex:voice-stage-open`
 *   and `zenrex:voice-stage-close` events dispatched elsewhere).
 * - Shows a small floating indicator on the bottom-left corner.
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Mic, MicOff } from 'lucide-react';

const SR = (typeof window !== 'undefined') && (window.SpeechRecognition || window.webkitSpeechRecognition);
const LS_KEY = 'zenrex_wake_word_enabled';

// Wake word patterns — allow small variations
const WAKE_PATTERNS = [
  { re: /(يا\s+)?زار[اه]/i, char: 'zara' },
  { re: /(يا\s+)?ليل[اى]/i, char: 'layla' },
];

export default function WakeWordListener() {
  const [enabled, setEnabled] = useState(() => {
    try { return localStorage.getItem(LS_KEY) === '1'; } catch (_) { return false; }
  });
  const [active, setActive] = useState(false);
  const [paused, setPaused] = useState(false);
  const [lastHeard, setLastHeard] = useState('');
  const recRef = useRef(null);
  const pausedRef = useRef(false);
  const enabledRef = useRef(enabled);
  useEffect(() => { enabledRef.current = enabled; }, [enabled]);
  useEffect(() => { pausedRef.current = paused; }, [paused]);

  const stopRec = useCallback(() => {
    if (recRef.current) {
      try { recRef.current.stop(); } catch (_) {}
      recRef.current = null;
    }
    setActive(false);
  }, []);

  const startRec = useCallback(() => {
    if (!SR || !enabledRef.current || pausedRef.current || recRef.current) return;
    try {
      const rec = new SR();
      rec.lang = 'ar-SA';
      rec.continuous = true;
      rec.interimResults = true;
      rec.maxAlternatives = 1;
      rec.onstart = () => setActive(true);
      rec.onresult = (e) => {
        // Scan latest transcripts for wake words
        const latest = e.results[e.results.length - 1];
        if (!latest) return;
        const txt = latest[0].transcript || '';
        setLastHeard(txt.slice(-50));
        if (!latest.isFinal) return;
        for (const p of WAKE_PATTERNS) {
          if (p.re.test(txt)) {
            try { rec.stop(); } catch (_) {}
            window.dispatchEvent(new CustomEvent('zenrex:wake-word', { detail: { character: p.char, heard: txt } }));
            return;
          }
        }
      };
      rec.onerror = (ev) => {
        if (ev.error === 'not-allowed') {
          setEnabled(false);
          try { localStorage.setItem(LS_KEY, '0'); } catch (_) {}
        }
      };
      rec.onend = () => {
        setActive(false);
        recRef.current = null;
        // Auto-restart if still enabled & not paused
        if (enabledRef.current && !pausedRef.current) {
          setTimeout(() => startRec(), 400);
        }
      };
      rec.start();
      recRef.current = rec;
    } catch (_) {
      setActive(false);
    }
  }, []);

  // Start / stop loop based on enabled/paused
  useEffect(() => {
    if (enabled && !paused) startRec();
    else stopRec();
    return () => stopRec();
  }, [enabled, paused, startRec, stopRec]);

  // Listen for VoiceStage open/close to pause the wake word (avoid mic conflict)
  useEffect(() => {
    const onOpen = () => setPaused(true);
    const onClose = () => setPaused(false);
    window.addEventListener('zenrex:voice-stage-open', onOpen);
    window.addEventListener('zenrex:voice-stage-close', onClose);
    return () => {
      window.removeEventListener('zenrex:voice-stage-open', onOpen);
      window.removeEventListener('zenrex:voice-stage-close', onClose);
    };
  }, []);

  const toggle = () => {
    const nxt = !enabled;
    setEnabled(nxt);
    try { localStorage.setItem(LS_KEY, nxt ? '1' : '0'); } catch (_) {}
  };

  if (!SR) return null; // browser doesn't support Web Speech API

  // TEMPORARY: hide the visible toggle UI while Phase 2 is in progress.
  // Wake-word detection still runs in background if user had previously enabled it.
  return null;
  // eslint-disable-next-line no-unreachable
  return (
    <button
      onClick={toggle}
      data-testid="wake-word-toggle"
      title={enabled ? 'قل "يا زارا" أو "يا ليلى" لبدء المحادثة' : 'فعّل الاستماع بكلمة تنبيه'}
      className={`fixed bottom-20 left-4 z-30 px-3 h-10 rounded-full border backdrop-blur-md text-xs font-black flex items-center gap-2 transition-all ${
        enabled
          ? (active
              ? 'bg-emerald-500/25 border-emerald-400/60 text-emerald-100 shadow-[0_0_20px_rgba(16,185,129,0.4)]'
              : 'bg-amber-500/20 border-amber-400/50 text-amber-100')
          : 'bg-white/10 border-white/20 text-white/70 hover:bg-white/15'
      }`}
    >
      {enabled ? <Mic className="w-3.5 h-3.5" /> : <MicOff className="w-3.5 h-3.5" />}
      {enabled ? (active ? 'أستمع… قل "يا زارا"' : 'إعدادات...') : 'كلمة تنبيه'}
      {enabled && active && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />}
    </button>
  );
}
