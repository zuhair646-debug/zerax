/**
 * useCreditsGuard — central hook for credit-aware UIs.
 *
 * Returns { credits, isBlocked, unlimited, isLoading, refresh } so any page
 * (FreeBuildChat, Companion, AppStudio, etc.) can:
 *   - Disable input when isBlocked is true (credits === 0 and not admin)
 *   - Render an inline "Recharge" banner pointing to /pricing
 *   - Refresh balance imperatively after a successful AI call
 *
 * Listens to global window event `zenrex:credits-changed` and re-polls every
 * 25 seconds while mounted.
 */
import { useState, useEffect, useCallback } from 'react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function useCreditsGuard() {
  const [state, setState] = useState({
    credits: null,
    unlimited: false,
    isBlocked: false,
    isLoading: true,
    tier: 'free',
  });

  const refresh = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setState({ credits: null, unlimited: false, isBlocked: false, isLoading: false, tier: 'free' });
      return;
    }
    try {
      const r = await fetch(`${API}/api/usage/credits`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) {
        setState((s) => ({ ...s, isLoading: false }));
        return;
      }
      const d = await r.json();
      const unlimited = !!d.unlimited;
      const balance = Number(d.credits || 0);
      setState({
        credits: balance,
        unlimited,
        isBlocked: !unlimited && balance <= 0,
        isLoading: false,
        tier: d.tier || 'free',
      });
    } catch (_) {
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 25000);
    const onEvt = () => refresh();
    window.addEventListener('zenrex:credits-changed', onEvt);
    return () => {
      clearInterval(id);
      window.removeEventListener('zenrex:credits-changed', onEvt);
    };
  }, [refresh]);

  return { ...state, refresh };
}

/**
 * Helper to notify other listeners (e.g. CreditsBadge in Navbar) that
 * credits balance just changed. Call after any successful AI consumption.
 */
export function notifyCreditsChanged() {
  try {
    window.dispatchEvent(new Event('zenrex:credits-changed'));
  } catch (_) { /* SSR safety */ }
}
