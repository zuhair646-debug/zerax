/**
 * ZCrownSpinner — animated GOLD Z logo + branded AI name "زنركس".
 *
 * Per UX requirement: keep the brand Z (NOT a generic dots animation),
 * paint it gold like the main Zenrex logo, and show the AI's own name
 * underneath so customers feel they're using Zenrex's proprietary AI
 * (never expose the underlying provider like Claude/Opus/Sonnet).
 */
import React from 'react';

export default function ZCrownSpinner({ size = 36, label = 'يحلل ويكتب...' }) {
  const px = `${size}px`;
  return (
    <div className="zcs-wrap" data-testid="z-crown-spinner" role="status" aria-live="polite">
      <div className="zcs-z" style={{ width: px, height: px }}>
        <span className="zcs-z-glyph">Z</span>
        <span className="zcs-ring" />
        <span className="zcs-ring zcs-ring-2" />
      </div>
      <div className="zcs-text">
        <span className="zcs-brand">زنركس</span>
        <span className="zcs-status">{label}</span>
      </div>
      <style>{`
        .zcs-wrap {
          display: inline-flex; align-items: center; gap: 10px;
          padding: 6px 14px 6px 8px;
          border-radius: 999px;
          background: linear-gradient(135deg, rgba(212,175,55,0.10), rgba(255,215,100,0.04));
          border: 1px solid rgba(212,175,55,0.35);
          backdrop-filter: blur(6px);
        }
        .zcs-z {
          position: relative;
          display: flex; align-items: center; justify-content: center;
          flex-shrink: 0;
        }
        .zcs-z-glyph {
          position: relative; z-index: 2;
          font-family: 'Cairo', 'Tajawal', serif;
          font-weight: 900;
          font-size: ${size * 0.62}px;
          background: linear-gradient(135deg, #FFD86B 0%, #D4AF37 45%, #B8860B 100%);
          -webkit-background-clip: text; background-clip: text;
          color: transparent;
          text-shadow: 0 0 12px rgba(212,175,55,0.45);
          animation: zcs-pulse 1.8s ease-in-out infinite;
          line-height: 1;
        }
        .zcs-ring {
          position: absolute; inset: 0;
          border-radius: 50%;
          border: 1.5px solid transparent;
          border-top-color: rgba(255,215,100,0.85);
          border-right-color: rgba(212,175,55,0.55);
          animation: zcs-rotate 1.5s linear infinite;
        }
        .zcs-ring-2 {
          inset: -3px;
          border-top-color: rgba(255,215,100,0.35);
          border-left-color: rgba(212,175,55,0.25);
          border-right-color: transparent; border-bottom-color: transparent;
          animation: zcs-rotate 2.4s linear infinite reverse;
        }
        .zcs-text { display: flex; flex-direction: column; line-height: 1.1; }
        .zcs-brand {
          font-size: 13px; font-weight: 800;
          background: linear-gradient(90deg, #FFD86B, #D4AF37);
          -webkit-background-clip: text; background-clip: text;
          color: transparent;
        }
        .zcs-status {
          font-size: 10.5px;
          color: rgba(255,235,180,0.75);
          font-weight: 500;
        }
        @keyframes zcs-pulse {
          0%, 100% { transform: scale(1);    filter: drop-shadow(0 0 4px rgba(212,175,55,0.5)); }
          50%      { transform: scale(1.08); filter: drop-shadow(0 0 10px rgba(255,215,100,0.85)); }
        }
        @keyframes zcs-rotate { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
