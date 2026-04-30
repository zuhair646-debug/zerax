/**
 * ZitexDuoLauncher v5 — minimal landing peek (Zara/Layla in corners).
 * Click peek → opens full VoiceStage.
 * Wake-word "يا زارا/ليلى" still works hands-free.
 *
 * NOTE: Auto-open on first visit is DISABLED on landing.
 * The full conversation lives at /talk (post-registration).
 */
import React, { useState, useEffect, lazy, Suspense } from 'react';
import CharacterSceneEngine from './CharacterSceneEngine';
import WakeWordListener from './WakeWordListener';

const VoiceStage = lazy(() => import('./VoiceStage'));

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
    try { window.dispatchEvent(new CustomEvent('zitex:voice-stage-close')); } catch (_) {}
  };

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
