/**
 * ZitexDuoLauncher v4 — wraps CharacterSceneEngine + VoiceStage + WakeWordListener.
 * - Characters are STATIONARY (breathing only).
 * - Auto-opens VoiceStage on first visit (cooldown 10 min) → user can talk immediately.
 * - Wake-word "يا زارا" / "يا ليلى" opens VoiceStage hands-free.
 */
import React, { useState, useEffect, lazy, Suspense } from 'react';
import CharacterSceneEngine from './CharacterSceneEngine';
import WakeWordListener from './WakeWordListener';

const VoiceStage = lazy(() => import('./VoiceStage'));

// Cooldown: don't auto-reopen if user dismissed within this window
const DISMISS_COOLDOWN_MS = 10 * 60 * 1000; // 10 minutes
const DISMISS_KEY = 'zitex_vs_dismissed_at';

export default function ZitexDuoLauncher() {
  const [open, setOpen] = useState(false);
  const [initial, setInitial] = useState('zara');

  const launch = (char) => {
    setInitial(char || 'zara');
    setOpen(true);
    try { window.dispatchEvent(new CustomEvent('zitex:voice-stage-open')); } catch (_) {}
  };

  const close = () => {
    setOpen(false);
    try {
      localStorage.setItem(DISMISS_KEY, String(Date.now()));
      window.dispatchEvent(new CustomEvent('zitex:voice-stage-close'));
    } catch (_) {}
  };

  // Auto-launch on first visit (if not recently dismissed)
  useEffect(() => {
    try {
      const last = parseInt(localStorage.getItem(DISMISS_KEY) || '0', 10);
      const since = Date.now() - last;
      if (since > DISMISS_COOLDOWN_MS) {
        // Give the page ~2s to settle, then open
        const t = setTimeout(() => launch('zara'), 2000);
        return () => clearTimeout(t);
      }
    } catch (_) {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Wake-word triggers VoiceStage
  useEffect(() => {
    const onWake = (e) => {
      const char = (e.detail && e.detail.character) || 'zara';
      launch(char);
    };
    window.addEventListener('zitex:wake-word', onWake);
    return () => window.removeEventListener('zitex:wake-word', onWake);
  }, []);

  return (
    <>
      {!open && <CharacterSceneEngine onLaunchVoice={launch} />}
      {!open && <WakeWordListener />}
      {open && (
        <Suspense fallback={<div className="fixed inset-0 z-[100] bg-black/80 flex items-center justify-center text-white">جاري التحميل...</div>}>
          <VoiceStage
            open={open}
            onClose={close}
            initialCharacter={initial}
            onSignupNeeded={() => { close(); window.location.href = '/register'; }}
          />
        </Suspense>
      )}
    </>
  );
}
