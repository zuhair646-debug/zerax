import React from 'react';
import { useLocation } from 'react-router-dom';
import LanguagePicker from './LanguagePicker';

/**
 * A floating Language Picker pinned to the bottom-right (or left in RTL)
 * on every page. Gives international visitors instant access to switch
 * language regardless of which page they're on or whether that page has
 * the main Navbar.
 *
 * Visibility:
 *   - Hidden on auth-flow routes (/login, /register, /auth/...) where
 *     focus is on the form.
 *   - Hidden when the main Navbar's LanguagePicker is visible (we'd be
 *     redundant) — we just always show it; the Navbar one is large at
 *     the top, this one is a compact pill at the bottom corner.
 */
export default function FloatingLanguagePicker() {
  const location = useLocation();
  const hide =
    location.pathname.startsWith('/login') ||
    location.pathname.startsWith('/register') ||
    location.pathname.startsWith('/auth');
  if (hide) return null;
  return (
    <div
      data-testid="floating-lang-picker"
      data-no-translate="true"
      className="fixed bottom-4 end-4 z-[100] shadow-2xl"
      style={{ pointerEvents: 'auto' }}
    >
      <LanguagePicker compact />
    </div>
  );
}
