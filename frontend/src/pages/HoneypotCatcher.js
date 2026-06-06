/**
 * 🛡️ HoneypotCatcher — catches scanner attempts on non-API paths
 * (/.env, /wp-admin, /phpmyadmin, etc.) and reports them to the
 * backend so the IP gets banned for 1 hour.
 *
 * Rendered as the catch-all "*" route in App.js.
 */
import React, { useEffect } from 'react';
import { useLocation, Link } from 'react-router-dom';

const TRAP_KEYWORDS = [
  '.env', 'wp-admin', 'wp-login', 'wordpress', 'wp-content',
  'phpmyadmin', 'pma', 'phpinfo', '.git', '.aws',
  'xmlrpc', 'admin.php', 'server-status', 'vendor/phpunit',
  'cgi-bin', 'config.json', 'HNAP1',
];

function looksLikeScanner(path) {
  const lower = (path || '').toLowerCase();
  return TRAP_KEYWORDS.some((kw) => lower.includes(kw));
}

export default function HoneypotCatcher() {
  const location = useLocation();
  const path = location.pathname + (location.search || '');

  useEffect(() => {
    if (looksLikeScanner(path)) {
      fetch(`${process.env.REACT_APP_BACKEND_URL}/api/security/honeypot-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
        keepalive: true,
      }).catch(() => { /* silent — scanner doesn't need feedback */ });
    }
  }, [path]);

  return (
    <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center p-8" dir="rtl">
      <div className="text-center max-w-md">
        <h1 className="text-5xl font-bold mb-3">404</h1>
        <p className="text-zinc-400 mb-6">الصفحة اللي تدوّر عليها مو موجودة</p>
        <Link
          to="/"
          className="inline-block px-6 py-3 bg-amber-500 hover:bg-amber-400 text-zinc-900 font-bold rounded-lg transition"
          data-testid="honeypot-home-btn"
        >
          الرجوع للرئيسية
        </Link>
      </div>
    </div>
  );
}
