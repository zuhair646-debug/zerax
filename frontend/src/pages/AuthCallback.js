/**
 * AuthCallback — handles the post-Google OAuth redirect.
 * URL format: /auth-callback#session_id=...
 *
 * Flow:
 *   1. Synchronously parse the session_id from URL fragment (set during render to
 *      avoid race conditions).
 *   2. POST to /api/auth/google/exchange — backend verifies session_id and returns
 *      our app's JWT + user object.
 *   3. Save token + user → setUser → navigate to dashboard.
 *
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
 */
import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { ZitexLogo } from '@/components/Navbar';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AuthCallback({ setUser }) {
  const navigate = useNavigate();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const hash = window.location.hash || '';
    const m = hash.match(/session_id=([^&]+)/);
    const sessionId = m ? decodeURIComponent(m[1]) : null;
    if (!sessionId) {
      toast.error('لم يتم العثور على بيانات الجلسة');
      navigate('/login', { replace: true });
      return;
    }

    (async () => {
      try {
        const r = await fetch(`${API}/api/auth/google/exchange`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'فشل تسجيل الدخول');

        localStorage.setItem('token', d.token);
        localStorage.setItem('user', JSON.stringify(d.user));
        if (typeof setUser === 'function') setUser(d.user);

        // Wipe the fragment from URL so it doesn't leak into history
        window.history.replaceState(null, '', '/dashboard');

        toast.success(d.is_new ? `🎉 أهلاً بك ${d.user.name}!` : `أهلاً ${d.user.name}!`);
        navigate(d.user.role === 'admin' ? '/admin' : '/dashboard', { replace: true });
      } catch (e) {
        toast.error(e.message || 'حدث خطأ');
        navigate('/login', { replace: true });
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen bg-[#08080f] flex flex-col items-center justify-center text-white" dir="rtl" data-testid="auth-callback">
      <ZitexLogo size="xl" />
      <div className="mt-6 flex items-center gap-3 text-amber-300">
        <div className="w-5 h-5 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
        <span className="font-bold">جارٍ تسجيل الدخول...</span>
      </div>
    </div>
  );
}
