import React, { useState, useEffect } from 'react';
import { Key, CheckCircle2, AlertCircle, Loader2, X } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * 🔑 FAL Key Manager (Owner only)
 * Visible when user is owner AND production fal key is broken.
 * Lets them paste a new key — tested vs Fal.ai BEFORE saving.
 */
export default function FalKeyManager({ accentColor = 'amber' }) {
  const token = (typeof localStorage !== 'undefined' && localStorage.getItem('token')) || '';
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [keyInput, setKeyInput] = useState('');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const fetchStatus = async () => {
    if (!token) return;
    try {
      const r = await fetch(`${API}/api/games/admin/fal-key-status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.status === 403) { setStatus({ forbidden: true }); return; }
      if (!r.ok) return;
      const d = await r.json();
      setStatus(d);
    } catch (e) { /* offline */ }
  };

  useEffect(() => { fetchStatus(); }, []); // eslint-disable-line

  // Hide button entirely if user is not owner
  if (status && status.forbidden) return null;

  const broken = status && status.live_test === 'broken';

  const handleSave = async () => {
    setErr(''); setMsg(''); setBusy(true);
    try {
      const r = await fetch(`${API}/api/games/admin/set-fal-key`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ fal_key: keyInput.trim() }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل الحفظ');
      setMsg(d.message || '✅ تم بنجاح');
      setKeyInput('');
      await fetchStatus();
      setTimeout(() => setOpen(false), 1500);
    } catch (e) {
      setErr(e.message || 'خطأ غير معروف');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {/* Always-visible floating pill — red if broken, green if working
          Positioned bottom-LEFT (top-LEFT on mobile) to avoid the orange mic button on the right */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        data-testid="fal-key-manager-btn"
        className={`fixed bottom-6 left-6 z-[60] px-4 py-2.5 rounded-full shadow-2xl border-2 flex items-center gap-2 text-sm font-bold transition-all hover:scale-105 ${
          broken
            ? 'bg-rose-500 hover:bg-rose-400 text-white border-rose-300 animate-pulse'
            : 'bg-emerald-500 hover:bg-emerald-400 text-white border-emerald-300'
        }`}
        title={broken ? 'مفتاح Fal فاسد — اضغط للإصلاح' : 'مفتاح Fal شغّال'}
      >
        <Key className="w-4 h-4" />
        <span>{broken ? '🔴 إصلاح مفتاح FAL' : (status?.live_test === 'working' ? '🟢 FAL شغّال' : '🔑 اختبار FAL')}</span>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => !busy && setOpen(false)}
          data-testid="fal-key-modal"
        >
          <div
            className={`bg-zinc-900 border-2 border-${accentColor}-500/40 rounded-2xl max-w-lg w-full p-6 shadow-2xl`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className={`text-lg font-bold text-${accentColor}-300 flex items-center gap-2`}>
                <Key className="w-5 h-5" /> إدارة مفتاح Fal.ai
              </h2>
              <button onClick={() => !busy && setOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Current Status */}
            <div className="mb-4 p-3 rounded-lg bg-black/30 border border-white/10 text-xs space-y-1.5">
              <div className="flex items-center gap-2 font-bold text-zinc-200">
                <span>الحالة الحالية:</span>
                {status?.live_test === 'working' && (
                  <span className="flex items-center gap-1 text-emerald-300">
                    <CheckCircle2 className="w-3.5 h-3.5" /> يشتغل
                  </span>
                )}
                {status?.live_test === 'broken' && (
                  <span className="flex items-center gap-1 text-rose-300">
                    <AlertCircle className="w-3.5 h-3.5" /> فاسد
                  </span>
                )}
              </div>
              <div className="text-zinc-400">
                مصدر المفتاح النشط:{' '}
                <code className="text-amber-200">{status?.active_source || '—'}</code>
              </div>
              {status?.vault_preview && (
                <div className="text-zinc-400">
                  vault: <code className="text-emerald-300">{status.vault_preview}</code>
                </div>
              )}
              {status?.env_preview && (
                <div className="text-zinc-400">
                  env (Railway): <code className="text-rose-300">{status.env_preview}</code>
                </div>
              )}
              {status?.live_error && (
                <div className="text-rose-300 break-all">خطأ Fal: {status.live_error}</div>
              )}
            </div>

            {/* Input */}
            <div className="space-y-2">
              <label className="text-xs text-zinc-300 font-bold">المفتاح الجديد</label>
              <input
                type="text"
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                placeholder="<uuid>:<hash>"
                dir="ltr"
                data-testid="fal-key-input"
                className={`w-full px-3 py-2 bg-black/40 border border-${accentColor}-500/30 rounded-lg text-sm text-white font-mono focus:outline-none focus:border-${accentColor}-400 placeholder:text-zinc-600`}
              />
              <p className="text-[11px] text-zinc-500 leading-relaxed">
                المفتاح الصحيح اللي حصلناه من اختباره محلياً:
                <code className="block mt-1 text-[10px] text-amber-200 bg-black/40 p-2 rounded break-all border border-amber-500/20" dir="ltr">
                  e016ba3b-d074-45c9-99a3-fc5168fe52e5:b653c35dfe685396dc45f6b83457623b
                </code>
                <button
                  onClick={() => setKeyInput('e016ba3b-d074-45c9-99a3-fc5168fe52e5:b653c35dfe685396dc45f6b83457623b')}
                  className="mt-1.5 text-[11px] text-amber-300 hover:text-amber-200 underline"
                  data-testid="fal-key-paste-suggested"
                >
                  📋 الصق المفتاح المقترح
                </button>
              </p>
            </div>

            {/* Messages */}
            {msg && (
              <div className="mt-3 p-2 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 text-xs flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{msg}</span>
              </div>
            )}
            {err && (
              <div className="mt-3 p-2 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-200 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{err}</span>
              </div>
            )}

            {/* Actions */}
            <div className="mt-4 flex gap-2 justify-end">
              <button
                onClick={() => !busy && setOpen(false)}
                disabled={busy}
                className="text-xs px-4 py-2 rounded-lg border border-white/10 text-zinc-300 hover:bg-white/5 disabled:opacity-40"
              >إلغاء</button>
              <button
                onClick={handleSave}
                disabled={busy || !keyInput.trim() || keyInput.length < 30}
                data-testid="fal-key-save-btn"
                className={`text-xs px-4 py-2 rounded-lg bg-${accentColor}-500 hover:bg-${accentColor}-400 text-black font-bold flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed`}
              >
                {busy ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> يختبر…</> : 'احفظ واختبر'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
