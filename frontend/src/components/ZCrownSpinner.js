/**
 * ZCrownSpinner — animated branded chip using the REAL Zenrex crown logo (PNG)
 * plus the "Zenrex AI" brand name. Customers always see Zenrex's proprietary AI,
 * never the underlying model provider.
 */
import React from 'react';

export default function ZCrownSpinner({ size = 36, label = 'يحلل ويكتب...' }) {
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
        <span className="zcs-brand">زنركس AI</span>
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
        .zcs-logo {
          position: relative; z-index: 2;
          object-fit: contain;
          filter: drop-shadow(0 0 8px rgba(212,175,55,0.55));
          animation: zcs-pulse 1.8s ease-in-out infinite;
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
          0%, 100% { transform: scale(1);    filter: drop-shadow(0 0 6px rgba(212,175,55,0.6)); }
          50%      { transform: scale(1.08); filter: drop-shadow(0 0 12px rgba(255,215,100,0.95)); }
        }
        @keyframes zcs-rotate { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
