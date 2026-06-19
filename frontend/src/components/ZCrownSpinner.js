/**
 * ZCrownSpinner — rotating GOLD "Z" mark with the universal Zenrex brand
 * (English-only label — "Zenrex" is the global brand regardless of the
 * customer's UI language).
 *
 * Visual contract:
 *   • The actual Z+crown PNG rotates slowly (one full rotation / 2.4s).
 *   • Outer ring orbits faster the other way for the "AI thinking" feel.
 *   • Label is "Zenrex" in English, not transliterated, in every locale.
 */
import React from 'react';

export default function ZCrownSpinner({ size = 38, label = '' }) {
  const px = `${size}px`;
  return (
    <div className="zcs-wrap" data-testid="z-crown-spinner" role="status" aria-live="polite">
      <div className="zcs-z" style={{ width: px, height: px }}>
        <img
          src="/zenrex-logo.png"
          alt="Zenrex"
          className="zcs-logo"
          style={{ width: `${size * 0.92}px`, height: `${size * 0.92}px` }}
        />
        <span className="zcs-ring" />
        <span className="zcs-ring zcs-ring-2" />
      </div>
      <div className="zcs-text">
        <span className="zcs-brand">Zenrex</span>
        {label ? <span className="zcs-status">{label}</span> : null}
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
        .zcs-logo {
          position: relative; z-index: 2;
          object-fit: contain;
          filter: drop-shadow(0 0 8px rgba(212,175,55,0.55));
          animation: zcs-rotate-logo 2.4s linear infinite;
        }
        .zcs-ring {
          position: absolute; inset: -2px;
          border-radius: 50%;
          border: 1.5px solid transparent;
          border-top-color: rgba(255,215,100,0.85);
          border-right-color: rgba(212,175,55,0.55);
          animation: zcs-rotate 1.5s linear infinite;
        }
        .zcs-ring-2 {
          inset: -5px;
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
          letter-spacing: 0.5px;
        }
        .zcs-status {
          font-size: 10.5px;
          color: rgba(255,235,180,0.75);
          font-weight: 500;
        }
        @keyframes zcs-rotate-logo {
          0%   { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes zcs-rotate { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
