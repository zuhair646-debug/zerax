/**
 * CharacterSceneEngine3D — renders Zara & Layla as real 3D VRM characters.
 * Activated when USE_3D=true in CharacterSceneEngine.js (once proper VRM files
 * are uploaded to /app/frontend/public/avatars-3d/).
 */
import React, { lazy, Suspense } from 'react';

const Avatar3D = lazy(() => import('./Avatar3D'));

const ZARA_VRM = '/avatars-3d/zara.vrm';
const LAYLA_VRM = '/avatars-3d/layla.vrm';

export default function CharacterSceneEngine3D({ onLaunchVoice }) {
  return (
    <>
      <button
        onClick={() => onLaunchVoice && onLaunchVoice('zara')}
        className="fixed bottom-0 left-2 z-40 w-40 sm:w-52 md:w-64 h-56 sm:h-72 md:h-80 pointer-events-auto group cursor-pointer"
        data-testid="duo-launcher-zara"
        aria-label="تكلّم مع زارا"
      >
        <Suspense fallback={<PngFallback char="zara" />}>
          <Avatar3D
            url={ZARA_VRM}
            tint="#f5a623"
            className="w-full h-full transition-transform group-hover:scale-105"
            dataTestId="zara-3d"
            cameraPos={[0, 1.3, 1.5]}
            fov={28}
          />
        </Suspense>
        <HintDot color="amber" />
      </button>

      <button
        onClick={() => onLaunchVoice && onLaunchVoice('layla')}
        className="fixed bottom-0 right-2 z-40 w-40 sm:w-52 md:w-64 h-56 sm:h-72 md:h-80 pointer-events-auto group cursor-pointer"
        data-testid="duo-launcher-layla"
        aria-label="تكلّم مع ليلى"
      >
        <Suspense fallback={<PngFallback char="layla" />}>
          <Avatar3D
            url={LAYLA_VRM}
            tint="#a855f7"
            className="w-full h-full transition-transform group-hover:scale-105"
            dataTestId="layla-3d"
            cameraPos={[0, 1.3, 1.5]}
            fov={28}
          />
        </Suspense>
        <HintDot color="purple" />
      </button>

      <button
        onClick={() => onLaunchVoice && onLaunchVoice('zara')}
        className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 px-4 py-2 rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-pink-500 text-white font-black text-xs shadow-[0_0_30px_rgba(245,158,11,0.6)] hover:scale-105 transition flex items-center gap-1.5"
        data-testid="duo-launcher-cta"
      >
        اضغط وكلّمني صوتاً
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

function PngFallback({ char }) {
  const src = char === 'zara' ? '/avatars/zara_idle.png' : '/avatars/layla_idle.png';
  const fb = char === 'zara' ? '/avatars/f1_zara.png' : '/avatars/f2_layla.png';
  return (
    <img
      src={src}
      onError={(e) => { e.target.src = fb; }}
      alt=""
      className="w-full h-full object-contain object-bottom"
      draggable={false}
    />
  );
}
