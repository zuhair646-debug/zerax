/**
 * ZitexDuoLauncher v2 — wraps CharacterSceneEngine + VoiceStage.
 * Characters perform random playful scenes (ball toss, dance, peek, hair-tease, etc.)
 * until the user clicks one → opens immersive VoiceStage.
 */
import React, { useState, lazy, Suspense } from 'react';
import CharacterSceneEngine from './CharacterSceneEngine';

const VoiceStage = lazy(() => import('./VoiceStage'));

export default function ZitexDuoLauncher() {
  const [open, setOpen] = useState(false);
  const [initial, setInitial] = useState('zara');

  const launch = (char) => {
    setInitial(char || 'zara');
    setOpen(true);
  };

  return (
    <>
      {!open && <CharacterSceneEngine onLaunchVoice={launch} />}
      {open && (
        <Suspense fallback={<div className="fixed inset-0 z-[100] bg-black/80 flex items-center justify-center text-white">جاري التحميل...</div>}>
          <VoiceStage
            open={open}
            onClose={() => setOpen(false)}
            initialCharacter={initial}
            onSignupNeeded={() => { setOpen(false); window.location.href = '/register'; }}
          />
        </Suspense>
      )}
    </>
  );
}
