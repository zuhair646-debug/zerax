/**
 * GlobalCreditsGuard — fixed bottom-of-screen toast shown on AI/chat routes
 * when the user's credit balance is zero. Single source of truth, mounted
 * once in App.js so every section (AppBuilder, MobileAppBuilder, ChatImage,
 * StudioVideo, AIChat, WebGamesStudio, etc.) gets the same calm prompt.
 *
 * Designed to be quiet (no overlay, no animation, no input-blocking) — it
 * sits above the page content with a clear single CTA → /pricing.
 */
import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Sparkles, ArrowLeft, X } from 'lucide-react';
import useCreditsGuard from '../hooks/useCreditsGuard';

// Routes that consume AI/credits and should show the prompt when blocked.
// Anything not in this allow-list (admin pages, /pricing, /login, etc.) is
// excluded so the user can navigate freely to recharge.
const AI_ROUTE_PATTERNS = [
  /^\/freebuild/,
  /^\/build/,
  /^\/chat/,
  /^\/ai\b/,
  /^\/companion/,
  /^\/avatar/,
  /^\/studio/,
  /^\/app-studio/,
  /^\/app-builder/,
  /^\/mobile-app/,
  /^\/video-studio/,
  /^\/image-studio/,
  /^\/image-generator/,
  /^\/games/,
  /^\/web-games/,
  /^\/operator/,
  /^\/new-request/,
  /^\/agent/,
];

const DISMISS_STORAGE_KEY = 'zenrex_credits_guard_dismissed_at';
const DISMISS_TTL_MS = 1000 * 60 * 10; // 10 minutes — reappears after that

export default function GlobalCreditsGuard() {
  const { isBlocked, unlimited } = useCreditsGuard();
  const location = useLocation();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = React.useState(false);

  // Refresh dismiss state on route change & on mount
  React.useEffect(() => {
    try {
      const ts = parseInt(localStorage.getItem(DISMISS_STORAGE_KEY) || '0', 10);
      setDismissed(ts > Date.now() - DISMISS_TTL_MS);
    } catch (_) {
      setDismissed(false);
    }
  }, [location.pathname]);

  if (unlimited || !isBlocked || dismissed) return null;

  const path = location.pathname || '/';
  const onAIRoute = AI_ROUTE_PATTERNS.some((re) => re.test(path));
  if (!onAIRoute) return null;

  // Don't shadow the /pricing or auth pages
  if (path.startsWith('/pricing') || path.startsWith('/login') || path.startsWith('/register')) {
    return null;
  }

  const dismiss = () => {
    try { localStorage.setItem(DISMISS_STORAGE_KEY, String(Date.now())); } catch (_) { /* ignore */ }
    setDismissed(true);
  };

  return (
    <div
      data-testid="global-credits-guard"
      dir="rtl"
      className="fixed bottom-3 inset-x-3 sm:left-auto sm:right-3 sm:bottom-3 sm:w-[360px] z-[120] rounded-xl border border-amber-500/40 bg-zinc-900/95 backdrop-blur shadow-xl p-3 flex items-center gap-3"
    >
      <div className="w-9 h-9 rounded-full bg-amber-500/15 border border-amber-500/30 flex items-center justify-center flex-shrink-0">
        <Sparkles className="w-4 h-4 text-amber-300" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] font-bold text-amber-200 leading-tight">انتهى رصيد النقاط</p>
        <p className="text-[10px] text-zinc-400 leading-tight truncate">اشحن باقة وتكمل من نفس النقطة</p>
      </div>
      <button
        type="button"
        onClick={() => navigate('/pricing')}
        data-testid="global-credits-recharge"
        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-400 hover:bg-amber-300 text-black text-[11px] font-black transition flex-shrink-0"
      >
        <span>الباقات</span>
        <ArrowLeft className="w-3 h-3" />
      </button>
      <button
        type="button"
        onClick={dismiss}
        data-testid="global-credits-dismiss"
        aria-label="إخفاء"
        className="text-zinc-500 hover:text-zinc-300 p-0.5 flex-shrink-0"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
