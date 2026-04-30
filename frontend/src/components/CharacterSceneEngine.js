/**
 * Character Scene Engine v5 — stationary PNG characters (proven, stable).
 *
 * ⚠️ 3D VRM pipeline is READY in Avatar3D.js + /public/avatars-3d/ folder.
 * To upgrade to 3D: download attractive adult anime VRM files from
 *   - VRoid Hub: https://hub.vroid.com/en/models
 *   - Booth.pm: https://booth.pm/en/browse/3D%20Models
 * Save them as /app/frontend/public/avatars-3d/zara.vrm and layla.vrm.
 * Then set USE_3D = true below and the landing page will auto-render 3D.
 */
import React, { lazy, Suspense } from 'react';

const Lazy3D = lazy(() => import('./CharacterSceneEngine3D'));

const USE_3D = true; // ✅ ENABLED — user uploaded Z.vrm as zara.vrm + layla.vrm

export default function CharacterSceneEngine({ onLaunchVoice }) {
  if (USE_3D) {
    return (
      <Suspense fallback={<SceneEngine2D onLaunchVoice={onLaunchVoice} />}>
        <Lazy3D onLaunchVoice={onLaunchVoice} />
      </Suspense>
    );
  }
  return <SceneEngine2D onLaunchVoice={onLaunchVoice} />;
}

function SceneEngine2D({ onLaunchVoice }) {
  return (
    <>
      <SceneStyles />
      {/* Zara — bottom-left, stationary with gentle breathing */}
      <button
        onClick={() => onLaunchVoice && onLaunchVoice('zara')}
        className="fixed bottom-0 left-2 z-40 pointer-events-auto group char-breathe"
        data-testid="duo-launcher-zara"
        aria-label="تكلّم مع زارا"
      >
        <div className="relative w-32 sm:w-40 h-44 sm:h-52">
          <img
            src="/avatars/zara_idle.png"
            onError={(e) => { e.target.src = '/avatars/f1_zara.png'; }}
            alt=""
            className="w-full h-full object-contain object-bottom transition-transform group-hover:scale-110"
            style={{ filter: 'drop-shadow(0 0 24px rgba(245,158,11,0.5))' }}
            draggable={false}
          />
          <HintDot color="amber" />
        </div>
      </button>

      {/* Layla — bottom-right */}
      <button
        onClick={() => onLaunchVoice && onLaunchVoice('layla')}
        className="fixed bottom-0 right-2 z-40 pointer-events-auto group char-breathe-delay"
        data-testid="duo-launcher-layla"
        aria-label="تكلّم مع ليلى"
      >
        <div className="relative w-32 sm:w-40 h-44 sm:h-52">
          <img
            src="/avatars/layla_idle.png"
            onError={(e) => { e.target.src = '/avatars/f2_layla.png'; }}
            alt=""
            className="w-full h-full object-contain object-bottom transition-transform group-hover:scale-110"
            style={{ filter: 'drop-shadow(0 0 24px rgba(168,85,247,0.5))' }}
            draggable={false}
          />
          <HintDot color="purple" />
        </div>
      </button>
    </>
  );
}

function HintDot({ color }) {
  const cls = color === 'amber'
    ? 'bg-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.9)]'
    : 'bg-purple-400 shadow-[0_0_12px_rgba(168,85,247,0.9)]';
  return <span className={`absolute top-3 right-3 w-3 h-3 rounded-full ${cls} animate-pulse pointer-events-none`} aria-hidden />;
}

function SceneStyles() {
  return (
    <style>{`
      @keyframes char-breathe {
        0%, 100% { transform: translateY(0) rotate(0deg) scaleY(1); }
        50%      { transform: translateY(-4px) rotate(-0.4deg) scaleY(1.01); }
      }
      .char-breathe       { animation: char-breathe 4.5s ease-in-out infinite; }
      .char-breathe-delay { animation: char-breathe 4.5s ease-in-out -2.2s infinite; }
    `}</style>
  );
}
