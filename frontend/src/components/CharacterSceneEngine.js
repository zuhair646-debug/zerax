/**
 * Character Scene Engine — picks random fun scenarios for Zara & Layla to play out
 * while idle on the landing page. Makes them feel ALIVE instead of static.
 *
 * Scenes:
 *   - 'ball-toss'      : Zara tosses a ball across screen, Layla catches it
 *   - 'peek-hide'      : One hides off-screen, peeks back
 *   - 'walk-across'    : Walks slowly across bottom
 *   - 'hair-tease'     : One pokes the other's hair
 *   - 'dance'          : Bouncing dance motion
 *   - 'backstage-exit' : Walks out of frame, re-enters after delay
 *   - 'jump-surprise'  : Small jump / gasp
 *
 * Each scene has a duration & resets positions after.
 */
import React, { useEffect, useState, useRef } from 'react';

const SCENES = [
  { id: 'ball-toss',      duration: 4000, weight: 3 },
  { id: 'peek-hide',      duration: 3500, weight: 2 },
  { id: 'walk-across',    duration: 6000, weight: 3 },
  { id: 'hair-tease',     duration: 3000, weight: 2 },
  { id: 'dance',          duration: 3500, weight: 2 },
  { id: 'jump-surprise',  duration: 2500, weight: 2 },
  { id: 'sway-idle',      duration: 5000, weight: 4 }, // common baseline
];

function pickScene() {
  const total = SCENES.reduce((s, x) => s + x.weight, 0);
  const r = Math.random() * total;
  let acc = 0;
  for (const s of SCENES) { acc += s.weight; if (r <= acc) return s; }
  return SCENES[0];
}

export default function CharacterSceneEngine({ onLaunchVoice }) {
  const [scene, setScene] = useState(SCENES[SCENES.length - 1]); // start with idle sway
  const [tick, setTick] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    const runNext = () => {
      const next = pickScene();
      setScene(next);
      setTick(t => t + 1);
      const pause = 800 + Math.random() * 1500; // small gap between scenes
      timerRef.current = setTimeout(runNext, next.duration + pause);
    };
    runNext();
    return () => clearTimeout(timerRef.current);
  }, []);

  return (
    <>
      <SceneStyles />
      {/* Zara */}
      <button
        key={`zara-${tick}`}
        onClick={() => onLaunchVoice && onLaunchVoice('zara')}
        className={`fixed bottom-0 z-40 pointer-events-auto group zara-scene-${scene.id}`}
        style={{
          '--duration': `${scene.duration}ms`,
          animation: `zara-${scene.id} ${scene.duration}ms ease-in-out forwards`,
        }}
        data-testid="duo-launcher-zara"
        aria-label="تكلّم مع زارا"
      >
        <div className="relative w-28 sm:w-36 h-40 sm:h-48">
          <img
            src="/avatars/zara_idle.png"
            onError={(e) => { e.target.src = '/avatars/f1_zara.png'; }}
            alt=""
            className="w-full h-full object-contain object-bottom transition-transform group-hover:scale-110"
            style={{ filter: 'drop-shadow(0 0 20px rgba(245,158,11,0.4))' }}
            draggable={false}
          />
          {/* Optional prop: ball during ball-toss */}
          {scene.id === 'ball-toss' && (
            <div className="absolute bottom-16 left-1/2 w-5 h-5 rounded-full bg-gradient-to-br from-pink-400 to-orange-500 shadow-[0_0_15px_rgba(236,72,153,0.8)]"
              style={{ animation: `ball-fly 2000ms ease-in-out infinite` }} />
          )}
        </div>
      </button>

      {/* Layla */}
      <button
        key={`layla-${tick}`}
        onClick={() => onLaunchVoice && onLaunchVoice('layla')}
        className={`fixed bottom-0 z-40 pointer-events-auto group layla-scene-${scene.id}`}
        style={{
          '--duration': `${scene.duration}ms`,
          animation: `layla-${scene.id} ${scene.duration}ms ease-in-out forwards`,
        }}
        data-testid="duo-launcher-layla"
        aria-label="تكلّم مع ليلى"
      >
        <div className="relative w-28 sm:w-36 h-40 sm:h-48">
          <img
            src="/avatars/layla_idle.png"
            onError={(e) => { e.target.src = '/avatars/f2_layla.png'; }}
            alt=""
            className="w-full h-full object-contain object-bottom transition-transform group-hover:scale-110"
            style={{ filter: 'drop-shadow(0 0 20px rgba(168,85,247,0.4))' }}
            draggable={false}
          />
        </div>
      </button>

      {/* Center CTA */}
      <button
        onClick={() => onLaunchVoice && onLaunchVoice('zara')}
        className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 px-4 py-2 rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-pink-500 text-white font-black text-xs shadow-[0_0_30px_rgba(245,158,11,0.6)] hover:scale-105 transition flex items-center gap-1.5"
        data-testid="duo-launcher-cta"
      >
        ✨ اضغط وكلّمني صوتاً
      </button>
    </>
  );
}

function SceneStyles() {
  return (
    <style>{`
      /* ==== ZARA (enters from left) scenes ==== */

      /* Sway idle — gentle standing with arm gestures */
      @keyframes zara-sway-idle {
        0%, 100% { left: 0.5rem; transform: translateY(0) rotate(0deg); }
        25%      { left: 0.5rem; transform: translateY(-4px) rotate(-1.5deg); }
        50%      { left: 0.8rem; transform: translateY(-8px) rotate(0deg); }
        75%      { left: 0.5rem; transform: translateY(-4px) rotate(1.5deg); }
      }

      /* Walk across — walks from off-left to center and back */
      @keyframes zara-walk-across {
        0%   { left: -12rem; transform: translateY(0) rotate(0deg); }
        10%  { left: -6rem;  transform: translateY(-3px) rotate(-2deg); }
        30%  { left: 15vw;   transform: translateY(-6px) rotate(2deg); }
        50%  { left: 30vw;   transform: translateY(-3px) rotate(-2deg); }
        70%  { left: 15vw;   transform: translateY(-6px) rotate(2deg); }
        90%  { left: -5rem;  transform: translateY(-3px) rotate(-2deg); }
        100% { left: 0.5rem; transform: translateY(0) rotate(0deg); }
      }

      /* Ball toss — crouches, throws ball forward */
      @keyframes zara-ball-toss {
        0%, 100% { left: 0.5rem; transform: translateY(0) rotate(0deg); }
        30%      { left: 0.5rem; transform: translateY(-12px) scaleY(0.9) rotate(-5deg); }
        45%      { left: 1rem;   transform: translateY(-18px) scaleY(1.05) rotate(3deg); }
        70%      { left: 0.5rem; transform: translateY(0) rotate(0deg); }
      }

      /* Peek — hides behind edge, peeks out */
      @keyframes zara-peek-hide {
        0%   { left: 0.5rem; transform: translateY(0); }
        30%  { left: -8rem;  transform: translateY(20%); }
        50%  { left: -7rem;  transform: translateY(10%); }
        70%  { left: -8rem;  transform: translateY(20%); }
        100% { left: 0.5rem; transform: translateY(0); }
      }

      /* Hair tease — leans right toward Layla */
      @keyframes zara-hair-tease {
        0%, 100% { left: 0.5rem; transform: translateX(0) rotate(0); }
        40%      { left: 3rem;   transform: translateX(10vw) rotate(6deg); }
        60%      { left: 3rem;   transform: translateX(10vw) rotate(4deg); }
      }

      /* Dance — bounces happily */
      @keyframes zara-dance {
        0%, 100% { left: 0.5rem; transform: translateY(0) rotate(0deg) scale(1); }
        15%      { left: 1rem;   transform: translateY(-15px) rotate(-3deg) scale(1.02); }
        30%      { left: 0.5rem; transform: translateY(-5px) rotate(2deg) scale(1); }
        45%      { left: 1rem;   transform: translateY(-15px) rotate(-2deg) scale(1.02); }
        60%      { left: 0.5rem; transform: translateY(-5px) rotate(3deg) scale(1); }
        75%      { left: 1rem;   transform: translateY(-15px) rotate(-3deg) scale(1.02); }
      }

      /* Jump surprise — small startled jump */
      @keyframes zara-jump-surprise {
        0%, 100% { left: 0.5rem; transform: translateY(0) rotate(0deg); }
        20%      { left: 0.5rem; transform: translateY(-25px) rotate(-4deg) scale(1.05); }
        40%      { left: 0.5rem; transform: translateY(-10px) rotate(2deg); }
      }

      /* ==== LAYLA (enters from right) scenes ==== */

      @keyframes layla-sway-idle {
        0%, 100% { right: 0.5rem; transform: translateY(0) rotate(0deg); }
        25%      { right: 0.5rem; transform: translateY(-4px) rotate(1.5deg); }
        50%      { right: 0.8rem; transform: translateY(-8px) rotate(0deg); }
        75%      { right: 0.5rem; transform: translateY(-4px) rotate(-1.5deg); }
      }

      @keyframes layla-walk-across {
        0%   { right: -12rem; transform: translateY(0) rotate(0deg); }
        10%  { right: -6rem;  transform: translateY(-3px) rotate(2deg); }
        30%  { right: 15vw;   transform: translateY(-6px) rotate(-2deg); }
        50%  { right: 30vw;   transform: translateY(-3px) rotate(2deg); }
        70%  { right: 15vw;   transform: translateY(-6px) rotate(-2deg); }
        90%  { right: -5rem;  transform: translateY(-3px) rotate(2deg); }
        100% { right: 0.5rem; transform: translateY(0) rotate(0deg); }
      }

      /* Ball toss — Layla catches with a little hop */
      @keyframes layla-ball-toss {
        0%, 100% { right: 0.5rem; transform: translateY(0); }
        50%      { right: 0.5rem; transform: translateY(-6px) rotate(-3deg); }
        70%      { right: 1rem;   transform: translateY(-14px) rotate(2deg); }
      }

      @keyframes layla-peek-hide {
        0%   { right: 0.5rem; transform: translateY(0); }
        30%  { right: -8rem;  transform: translateY(20%); }
        50%  { right: -7rem;  transform: translateY(10%); }
        70%  { right: -8rem;  transform: translateY(20%); }
        100% { right: 0.5rem; transform: translateY(0); }
      }

      @keyframes layla-hair-tease {
        0%, 100% { right: 0.5rem; transform: translateX(0) rotate(0); }
        40%      { right: 3rem;   transform: translateX(-6vw) rotate(-4deg); }
        60%      { right: 3rem;   transform: translateX(-6vw) rotate(-3deg); }
      }

      @keyframes layla-dance {
        0%, 100% { right: 0.5rem; transform: translateY(0) rotate(0deg); }
        20%      { right: 1rem;   transform: translateY(-10px) rotate(2deg); }
        50%      { right: 0.5rem; transform: translateY(-3px) rotate(-1deg); }
        80%      { right: 1rem;   transform: translateY(-10px) rotate(2deg); }
      }

      @keyframes layla-jump-surprise {
        0%, 100% { right: 0.5rem; transform: translateY(0) rotate(0deg); }
        20%      { right: 0.5rem; transform: translateY(-22px) rotate(3deg) scale(1.04); }
        40%      { right: 0.5rem; transform: translateY(-8px) rotate(-2deg); }
      }

      /* Ball flies across during ball-toss */
      @keyframes ball-fly {
        0%   { transform: translate(0, 0) scale(1); opacity: 1; }
        40%  { transform: translate(calc(100vw - 12rem), -40vh) scale(1.2); opacity: 1; }
        50%  { opacity: 0.7; }
        70%  { transform: translate(calc(100vw - 20rem), -10vh) scale(1.1); opacity: 1; }
        100% { transform: translate(0, 0) scale(1); opacity: 0; }
      }
    `}</style>
  );
}
