/**
 * ZitexDuoLauncher v7 — floating mic button + compact VoicePanel.
 *
 * Removed: 3D characters (code preserved in CharacterSceneEngine.js but not mounted).
 * Removed: Full-screen VoiceStage modal.
 * Kept: WakeWordListener (background detection, hidden UI).
 *
 * Flow: Click mic → VoicePanel opens inline (no page change) →
 * AI converses → if intent detected → navigate + pass subject via sessionStorage →
 * target page picks up the context and auto-fills its prompt field.
 */
import React, { useState, useEffect, lazy, Suspense } from 'react';
import WakeWordListener from './WakeWordListener';
import VoiceChatButton from './VoiceChatButton';

const VoicePanel = lazy(() => import('./VoicePanel'));

export default function ZitexDuoLauncher() {
  const [open, setOpen] = useState(false);

  const launch = () => {
    setOpen(true);
    try { window.dispatchEvent(new CustomEvent('zitex:voice-stage-open')); } catch (_) {}
  };

  const close = () => {
    setOpen(false);
    try { window.dispatchEvent(new CustomEvent('zitex:voice-stage-close')); } catch (_) {}
  };

  // Wake-word opens panel
  useEffect(() => {
    const onWake = () => launch();
    window.addEventListener('zitex:wake-word', onWake);
    return () => window.removeEventListener('zitex:wake-word', onWake);
  }, []);

  // "Continue conversation" after navigation — reopen panel if sessionStorage flag set
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem('zitex_voice_reopen');
      if (raw) {
        const data = JSON.parse(raw);
        if ((Date.now() - (data.ts || 0)) < 10000) {
          sessionStorage.removeItem('zitex_voice_reopen');
          setTimeout(() => launch(), 800);
        }
      }
    } catch (_) {}
  }, []);

  return (
    <>
      {!open && <VoiceChatButton onClick={launch} />}
      <WakeWordListener />
      <Suspense fallback={null}>
        {open && <VoicePanel open={open} onClose={close} />}
      </Suspense>
    </>
  );
}
