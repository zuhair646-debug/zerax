/**
 * Character Scene Engine v7 — 3D PEEK FROM CORNERS (no more old PNGs)
 *
 * Uses real VRM characters via Avatar3D with CSS clip-path to show only
 * head + shoulders peeking from the bottom corners. Click → opens VoiceStage.
 */
import React, { lazy, Suspense } from 'react';

const Avatar3D = lazy(() => import('./Avatar3D'));

const ZARA_VRM = '/avatars-3d/zara.vrm';
const LAYLA_VRM = '/avatars-3d/layla.vrm';

export default function CharacterSceneEngine({ onLaunchVoice }) {
  return (
    <>
      <PeekStyles />

      {/* Zara — bottom-left peek */}
      <button
        onClick={() => onLaunchVoice && onLaunchVoice('zara')}
        className="fixed bottom-0 left-0 z-40 pointer-events-auto group peek-zara w-44 sm:w-52 h-52 sm:h-60"
        data-testid="duo-launcher-zara"
        aria-label="تكلّم مع زارا"
      >
        <Suspense fallback={<div className="w-full h-full" />}>
          <Avatar3D
            url={ZARA_VRM}
            tint="#f5a623"
            className="w-full h-full transition-transform group-hover:scale-110"
            dataTestId="zara-3d"
            cameraPos={[0, 1.3, 2.5]}
            fov={45}
            sceneOffset={0}
          />
        </Suspense>
        <PeekTooltip side="left" name="زارا" />
        <span className="absolute top-2 right-3 w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_10px_rgba(245,158,11,0.9)] animate-pulse" aria-hidden />
      </button>

      {/* Layla — bottom-right peek */}
      <button
        onClick={() => onLaunchVoice && onLaunchVoice('layla')}
        className="fixed bottom-0 right-0 z-40 pointer-events-auto group peek-layla w-44 sm:w-52 h-52 sm:h-60"
        data-testid="duo-launcher-layla"
        aria-label="تكلّم مع ليلى"
      >
        <Suspense fallback={<div className="w-full h-full" />}>
          <Avatar3D
            url={LAYLA_VRM}
            tint="#a855f7"
            className="w-full h-full transition-transform group-hover:scale-110"
            dataTestId="layla-3d"
            cameraPos={[0, 1.3, 2.5]}
            fov={45}
            sceneOffset={2.5}
          />
        </Suspense>
        <PeekTooltip side="right" name="ليلى" />
        <span className="absolute top-2 left-3 w-2.5 h-2.5 rounded-full bg-purple-400 shadow-[0_0_10px_rgba(168,85,247,0.9)] animate-pulse" aria-hidden />
      </button>
    </>
  );
}

function PeekTooltip({ side, name }) {
  return (
    <span
      className={`absolute top-1 ${side === 'left' ? 'left-2' : 'right-2'} px-2 py-1 rounded-full bg-black/70 backdrop-blur-md text-white text-[10px] font-black whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none`}
    >
      كلّم {name} 🎤
    </span>
  );
}

function PeekStyles() {
  return (
    <style>{`
      /* Slide up from below the screen (head peeks out) */
      @keyframes peek-up-left {
        0%   { transform: translateY(50%) rotate(-8deg); opacity: 0; }
        70%  { transform: translateY(8%) rotate(-2deg); opacity: 1; }
        100% { transform: translateY(0) rotate(0deg); opacity: 1; }
      }
      @keyframes peek-up-right {
        0%   { transform: translateY(50%) rotate(8deg); opacity: 0; }
        70%  { transform: translateY(8%) rotate(2deg); opacity: 1; }
        100% { transform: translateY(0) rotate(0deg); opacity: 1; }
      }
      .peek-zara  { animation: peek-up-left 1.6s ease-out forwards; transform-origin: bottom center; }
      .peek-layla { animation: peek-up-right 1.6s ease-out forwards; transform-origin: bottom center; }
    `}</style>
  );
}
