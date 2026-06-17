/* eslint-disable react-hooks/set-state-in-effect */
import React, { useEffect, useState, useCallback } from 'react';
import { X, Upload, Cookie, Trash2, CheckCircle2, AlertCircle, Loader2, Info } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const PLATFORMS = [
  { id: 'youtube',   label: 'YouTube',   icon: '▶️', accent: 'bg-red-500/20 border-red-500/40 text-red-200' },
  { id: 'tiktok',    label: 'TikTok',    icon: '🎵', accent: 'bg-pink-500/20 border-pink-500/40 text-pink-200' },
  { id: 'instagram', label: 'Instagram', icon: '📷', accent: 'bg-fuchsia-500/20 border-fuchsia-500/40 text-fuchsia-200' },
  { id: 'facebook',  label: 'Facebook',  icon: '📘', accent: 'bg-blue-500/20 border-blue-500/40 text-blue-200' },
  { id: 'twitter',   label: 'Twitter/X', icon: '🐦', accent: 'bg-zinc-500/20 border-zinc-500/40 text-zinc-200' },
];

/**
 * Cookies upload manager — lets the user paste/upload browser cookies so the
 * AI's `download_media` and `search_and_download_media` tools can bypass
 * platform IP blocks (YouTube/TikTok/Instagram all aggressively block cloud IPs).
 */
export default function CookiesManager({ open, onClose }) {
  const [uploaded, setUploaded] = useState([]);
  const [busyPlatform, setBusyPlatform] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const refresh = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const r = await fetch(`${BACKEND_URL}/api/freebuild-chat/media/cookies/list`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) return;
      const data = await r.json();
      setUploaded(data.cookies || []);
    } catch {/* ignore */}
  }, []);

  const upload = useCallback(async (platform, file) => {
    setError('');
    setSuccess('');
    setBusyPlatform(platform);
    try {
      const token = localStorage.getItem('token');
      const fd = new FormData();
      fd.append('platform', platform);
      fd.append('cookies_file', file);
      const r = await fetch(`${BACKEND_URL}/api/freebuild-chat/media/cookies/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      const data = await r.json();
      if (!r.ok) {
        setError(data.detail || data.error || 'فشل رفع الكوكيز');
      } else {
        setSuccess(`✓ تم رفع كوكيز ${platform} (${(data.size_bytes/1024).toFixed(1)}KB)`);
        refresh();
      }
    } catch (e) {
      setError(`خطأ: ${e.message}`);
    } finally {
      setBusyPlatform('');
    }
  }, [refresh]);

  const remove = useCallback(async (platform) => {
    setError(''); setSuccess(''); setBusyPlatform(platform);
    try {
      const token = localStorage.getItem('token');
      await fetch(`${BACKEND_URL}/api/freebuild-chat/media/cookies/${platform}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      setSuccess(`✓ تم حذف كوكيز ${platform}`);
      refresh();
    } catch (e) {
      setError(`خطأ: ${e.message}`);
    } finally {
      setBusyPlatform('');
    }
  }, [refresh]);

  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  if (!open) return null;

  const uploadedSet = new Set(uploaded.map(c => c.platform));

  return (
    <div
      className="fixed inset-0 z-[200] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
      data-testid="cookies-manager-modal"
    >
      <div
        className="bg-zinc-950 border border-amber-500/30 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        dir="rtl"
      >
        {/* Header */}
        <div className="sticky top-0 bg-zinc-950 border-b border-white/10 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-500/20 border border-amber-500/30">
              <Cookie className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">إدارة كوكيز التحميل</h2>
              <p className="text-xs text-zinc-400">عشان الذكاء يقدر يحمّل من YouTube/TikTok/Instagram</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/10 text-zinc-400"
            data-testid="cookies-close-btn"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Instructions */}
        <div className="px-6 py-4 bg-amber-500/5 border-b border-amber-500/10">
          <div className="flex items-start gap-3 text-sm">
            <Info className="w-5 h-5 text-amber-300 flex-shrink-0 mt-0.5" />
            <div className="text-amber-100/90 leading-relaxed space-y-2">
              <p><b className="text-amber-300">ليش نحتاج كوكيز؟</b> YouTube و TikTok يحظرون السيرفرات بشكل تلقائي. لما ترفع كوكيز من متصفحك (وأنت مسجّل دخول) الذكاء يقدر يحمّل أي فيديو تطلبه.</p>
              <p><b className="text-amber-300">الخطوات:</b></p>
              <ol className="list-decimal pr-5 space-y-0.5 text-xs">
                <li>ثبّت إضافة <b>{'"Get cookies.txt LOCALLY"'}</b> من Chrome Web Store (مجاناً)</li>
                <li>افتح المنصة (YouTube/TikTok/إلخ) وتأكد أنك <b>مسجّل دخول</b></li>
                <li>اضغط أيقونة الإضافة → <b>Export</b> → احفظ ملف <code className="text-amber-300">cookies.txt</code></li>
                <li>ارجع هنا وارفع الملف بزر {'"📤 رفع"'} تحت المنصة المناسبة</li>
              </ol>
              <p className="text-emerald-300 text-xs">🔒 الكوكيز محفوظة على سيرفرك الخاص فقط، ما تنشاركها مع أحد.</p>
            </div>
          </div>
        </div>

        {/* Status messages */}
        {error && (
          <div className="px-6 py-3 bg-red-500/10 border-y border-red-500/30 text-red-200 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" /> {error}
          </div>
        )}
        {success && (
          <div className="px-6 py-3 bg-emerald-500/10 border-y border-emerald-500/30 text-emerald-200 text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" /> {success}
          </div>
        )}

        {/* Platforms list */}
        <div className="p-6 space-y-3">
          {PLATFORMS.map((p) => {
            const isUploaded = uploadedSet.has(p.id);
            const meta = uploaded.find(c => c.platform === p.id);
            const busy = busyPlatform === p.id;
            return (
              <div
                key={p.id}
                className={`rounded-xl border p-4 flex items-center justify-between gap-4 ${isUploaded ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-white/10 bg-white/[0.02]'}`}
                data-testid={`cookies-platform-${p.id}`}
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className={`text-2xl flex-shrink-0`}>{p.icon}</div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-white">{p.label}</div>
                    {isUploaded && meta ? (
                      <div className="text-xs text-emerald-300 mt-0.5">
                        ✓ كوكيز مرفوع · {(meta.size_bytes/1024).toFixed(1)}KB
                      </div>
                    ) : (
                      <div className="text-xs text-zinc-500 mt-0.5">لا يوجد كوكيز — التحميل قد يفشل بسبب IP block</div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <label
                    className={`px-3 py-2 rounded-lg text-xs font-bold cursor-pointer transition-colors ${busy ? 'bg-zinc-700 text-zinc-400' : 'bg-amber-500 text-zinc-900 hover:bg-amber-400'}`}
                    data-testid={`cookies-upload-${p.id}`}
                  >
                    {busy ? <Loader2 className="w-3 h-3 animate-spin inline" /> : <Upload className="w-3 h-3 inline ml-1" />}
                    {isUploaded ? 'تحديث' : 'رفع'}
                    <input
                      type="file"
                      accept=".txt,text/plain"
                      className="hidden"
                      disabled={busy}
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) upload(p.id, f);
                        e.target.value = '';
                      }}
                    />
                  </label>
                  {isUploaded && (
                    <button
                      type="button"
                      onClick={() => remove(p.id)}
                      disabled={busy}
                      className="px-3 py-2 rounded-lg bg-red-500/20 border border-red-500/40 text-red-200 hover:bg-red-500/30 transition-colors disabled:opacity-50"
                      data-testid={`cookies-delete-${p.id}`}
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer help */}
        <div className="px-6 pb-6">
          <div className="text-xs text-zinc-500 bg-white/[0.02] border border-white/5 rounded-lg p-3 leading-relaxed">
            💡 <b className="text-zinc-300">نصيحة:</b> لو الكوكيز انتهت صلاحيتها (بعد أسابيع)، رفع ملف جديد. الإضافة تتجدّد تلقائياً.
            <br />
            💡 لو ما عندك حساب على المنصة، تقدر تسوي حساب مجاني فقط لتصدير الكوكيز.
          </div>
        </div>
      </div>
    </div>
  );
}
