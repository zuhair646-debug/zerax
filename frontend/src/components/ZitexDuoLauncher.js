/**
 * ZitexDuoLauncher — lightweight floating trigger that opens the full Voice Stage.
 *
 * Replaces the old text-chat ZitexDuo.
 *
 * Always visible on landing + main pages. Shows both characters waving
 * at the bottom corners. Clicking either character → opens immersive
 * voice-first VoiceStage overlay.
 */
import React, { useState, lazy, Suspense } from 'react';
import { Mic, Sparkles } from 'lucide-react';

const VoiceStage = lazy(() => import('./VoiceStage'));

export default function ZitexDuoLauncher() {
  const [open, setOpen] = useState(false);
  const [initial, setInitial] = useState('zara');

  const launch = (char) => {
    setInitial(char);
    setOpen(true);
  };

  return (
    <>
      {!open && (
        <>
          {/* Zara — bottom-left peek */}
          <button
            onClick={() => launch('zara')}
            className="fixed bottom-0 left-0 w-28 sm:w-36 h-40 sm:h-48 z-40 group pointer-events-auto"
            style={{ animation: 'zd-walk-left 8s ease-in-out infinite' }}
            data-testid="duo-launcher-zara"
            aria-label="تكلّم مع زارا"
          >
            <img
              src="/avatars/zara_wave.png"
              onError={(e) => { e.target.src = '/avatars/f1_zara.png'; }}
              alt=""
              className="w-full h-full object-contain object-bottom transition-all group-hover:scale-110 group-hover:-translate-y-2"
              style={{ filter: 'drop-shadow(0 0 20px rgba(245,158,11,0.4))' }}
              draggable={false}
            />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 flex items-center gap-1 bg-amber-500 text-black text-[10px] font-black px-2 py-0.5 rounded-full opacity-0 group-hover:opacity-100 transition pointer-events-none whitespace-nowrap">
              <Mic className="w-2.5 h-2.5" /> كلّميني
            </div>
          </button>

          {/* Layla — bottom-right peek */}
          <button
            onClick={() => launch('layla')}
            className="fixed bottom-0 right-0 w-28 sm:w-36 h-40 sm:h-48 z-40 group pointer-events-auto"
            style={{ animation: 'zd-walk-right 9s ease-in-out infinite' }}
            data-testid="duo-launcher-layla"
            aria-label="تكلّم مع ليلى"
          >
            <img
              src="/avatars/layla_wave.png"
              onError={(e) => { e.target.src = '/avatars/f2_layla.png'; }}
              alt=""
              className="w-full h-full object-contain object-bottom transition-all group-hover:scale-110 group-hover:-translate-y-2"
              style={{ filter: 'drop-shadow(0 0 20px rgba(168,85,247,0.4))' }}
              draggable={false}
            />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 flex items-center gap-1 bg-purple-500 text-white text-[10px] font-black px-2 py-0.5 rounded-full opacity-0 group-hover:opacity-100 transition pointer-events-none whitespace-nowrap">
              <Mic className="w-2.5 h-2.5" /> كلّميني
            </div>
          </button>

          {/* Center CTA — tap-to-start pulse */}
          <button
            onClick={() => launch('zara')}
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 px-4 py-2 rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-pink-500 text-white font-black text-xs shadow-[0_0_30px_rgba(245,158,11,0.6)] hover:scale-105 transition flex items-center gap-1.5"
            data-testid="duo-launcher-cta"
          >
            <Sparkles className="w-3.5 h-3.5" /> اضغط وكلّمني صوتاً
          </button>

          {/* Inline keyframes for peek animation */}
          <style>{`
            @keyframes zd-walk-left {
              0%, 100% { transform: translate(0, 8px) rotate(0deg); }
              25%      { transform: translate(15px, -2px) rotate(-1.5deg); }
              50%      { transform: translate(30px, -10px) rotate(0deg); }
              75%      { transform: translate(15px, -4px) rotate(1.5deg); }
            }
            @keyframes zd-walk-right {
              0%, 100% { transform: translate(0, 8px) rotate(0deg); }
              25%      { transform: translate(-15px, -2px) rotate(1.5deg); }
              50%      { transform: translate(-30px, -10px) rotate(0deg); }
              75%      { transform: translate(-15px, -4px) rotate(-1.5deg); }
            }
          `}</style>
        </>
      )}

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
