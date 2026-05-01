/**
 * ZitexDuoLauncher v6 — TEMPORARILY showing simple VoiceChatButton instead
 * of 3D characters (user request while we work on Phase 2).
 *
 * Everything else (VoiceStage + wake-word) is preserved. Toggle SHOW_3D_PEEK
 * to true to re-enable the character peek view.
 */
import React, { useState, useEffect, lazy, Suspense } from 'react';
import CharacterSceneEngine from './CharacterSceneEngine';
import WakeWordListener from './WakeWordListener';
import VoiceChatButton from './VoiceChatButton';

const VoiceStage = lazy(() => import('./VoiceStage'));

// ⚙️ Toggle this back to `true` when Phase 2 is ready to re-enable 3D peeks
const SHOW_3D_PEEK = false;

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
      {!open && SHOW_3D_PEEK && <CharacterSceneEngine onLaunchVoice={launch} />}
      {!open && !SHOW_3D_PEEK && <VoiceChatButton onClick={() => launch('zara')} />}
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
