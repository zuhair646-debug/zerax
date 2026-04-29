import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * SourceBrowser — owner-only page that lists every project file with:
 *   • A direct view link (opens raw text in a new tab — copy-paste to your repo)
 *   • A direct download link (saves the file with its name)
 *   • A search box to filter by path
 * Backed by the /api/source/manifest + /api/source/file endpoints (owner JWT).
 *
 * URL: /source
 */
export default function SourceBrowser({ user }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [copied, setCopied] = useState({});
  const [error, setError] = useState('');

  const token = useMemo(() => localStorage.getItem('token') || '', []);
  const isOwner = user && (user.role === 'owner' || user.is_owner);

  useEffect(() => {
    if (!token) { setError('غير مسجّل دخول'); setLoading(false); return; }
    if (!isOwner) { setError('هذه الصفحة للمالك فقط'); setLoading(false); return; }
    fetch(`${API}/api/source/manifest`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.ok ? r.json() : Promise.reject(r.statusText))
      .then((d) => { setFiles(d.files || []); setLoading(false); })
      .catch((e) => { setError(String(e)); setLoading(false); });
  }, [token, isOwner]);

  const filtered = useMemo(() => {
    if (!q.trim()) return files;
    const needle = q.trim().toLowerCase();
    return files.filter((f) => f.path.toLowerCase().includes(needle));
  }, [files, q]);

  const fmtSize = (n) => {
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(2)} MB`;
  };

  const buildAuthedUrl = (path, download = false) => {
    // Browsers can't add Authorization header on direct <a> click — use ?token= query
    // (server accepts both header and ?token query as fallback for owner-protected source endpoints)
    // We attach it via a temporary fetch + blob to keep auth header secure.
    return { path, download };
  };

  const openFile = async (path) => {
    try {
      const r = await fetch(`${API}/api/source/file?path=${encodeURIComponent(path)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const text = await r.text();
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener');
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (e) {
      toast.error('فشل: ' + e.message);
    }
  };

  const downloadFile = async (path) => {
    try {
      const r = await fetch(`${API}/api/source/file?path=${encodeURIComponent(path)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const text = await r.text();
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = path.split('/').pop();
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) {
      toast.error('فشل: ' + e.message);
    }
  };

  const copyContent = async (path) => {
    try {
      const r = await fetch(`${API}/api/source/file?path=${encodeURIComponent(path)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const text = await r.text();
      await navigator.clipboard.writeText(text);
      setCopied((c) => ({ ...c, [path]: true }));
      toast.success(`✅ تم نسخ ${path.split('/').pop()}`);
      setTimeout(() => setCopied((c) => ({ ...c, [path]: false })), 2000);
    } catch (e) {
      toast.error('فشل النسخ: ' + e.message);
    }
  };

  // Group by top-level folder
  const groups = useMemo(() => {
    const m = new Map();
    for (const f of filtered) {
      const top = f.path.split('/')[0] || 'root';
      if (!m.has(top)) m.set(top, []);
      m.get(top).push(f);
    }
    return Array.from(m.entries()).sort();
  }, [filtered]);

  const downloadZipAll = async () => {
    try {
      toast.info('⏳ جاري تحضير ZIP كامل المشروع...');
      const r = await fetch(`${API}/api/source/zip`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `zitex-${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      toast.success('✅ تم تحميل ZIP كامل المشروع');
    } catch (e) {
      toast.error('فشل تحميل ZIP: ' + e.message);
    }
  };

  const downloadZipFolder = async (prefix) => {
    try {
      toast.info(`⏳ جاري تحضير ZIP لـ ${prefix}...`);
      const r = await fetch(`${API}/api/source/zip-folder?prefix=${encodeURIComponent(prefix)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `zitex-${prefix.replace(/\//g, '-').replace(/-$/, '')}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      toast.success(`✅ تم تحميل ZIP لـ ${prefix}`);
    } catch (e) {
      toast.error('فشل تحميل ZIP: ' + e.message);
    }
  };

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0b14] text-white flex items-center justify-center p-8">
        <div className="bg-red-500/10 border border-red-400/30 rounded-2xl p-8 text-center max-w-md">
          <div className="text-4xl mb-3">🔒</div>
          <div className="font-black text-lg mb-2">{error}</div>
          <a href="/login" className="inline-block mt-3 px-5 py-2 bg-yellow-500 text-black rounded-lg font-black">تسجيل الدخول</a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0b14] text-white" dir="rtl" data-testid="source-browser-page">
      <div className="max-w-5xl mx-auto p-4 md:p-8">
        <div className="mb-6">
          <h1 className="text-3xl md:text-4xl font-black mb-2">📥 تحميل الكود (ملف بملف)</h1>
          <p className="text-sm text-white/60 leading-relaxed">
            انسخ كل ملف إلى مستودعك على GitHub (<code className="text-yellow-300">zuhair646-debug/zitex</code>) محافظاً على نفس المسار.
            استخدم <b>👁️ عرض</b> لفتح الملف في تبويب جديد، <b>📋 نسخ</b> لنسخه مباشرة، أو <b>⬇️ تنزيل</b> لحفظه على جهازك.
          </p>
        </div>

        {/* 🆕 Bulk ZIP downloads */}
        <div className="bg-gradient-to-br from-emerald-500/15 to-cyan-500/15 border border-emerald-400/40 rounded-2xl p-5 mb-6" data-testid="zip-section">
          <div className="flex items-start gap-3 flex-wrap">
            <div className="text-4xl flex-shrink-0">🚀</div>
            <div className="flex-1 min-w-[200px]">
              <h3 className="font-black text-lg text-emerald-300">تنزيل المشروع كاملاً (ZIP)</h3>
              <p className="text-xs text-white/65 mt-1 mb-3">
                طريقة أسرع — حمّل كل الكود ملف <b>ZIP</b> واحد بدلاً من النسخ ملف ملف.
                بعدها فُكّ الضغط ثم ادفع الكل دفعة واحدة إلى GitHub، أو ارفعه مباشرة إلى Railway/Vercel.
                ملف <code className="text-yellow-300">DEPLOY.md</code> داخل الـ ZIP فيه التعليمات الكاملة بالعربي.
              </p>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={downloadZipAll}
                  className="px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-600 hover:to-cyan-600 text-white font-black rounded-xl text-sm transition-all"
                  data-testid="zip-all-btn"
                >📦 تنزيل كل المشروع (ZIP)</button>
                <button
                  onClick={() => downloadZipFolder('backend/')}
                  className="px-4 py-2.5 bg-white/10 hover:bg-white/20 font-bold rounded-xl text-sm transition-all"
                  data-testid="zip-backend-btn"
                >🐍 backend فقط</button>
                <button
                  onClick={() => downloadZipFolder('frontend/src/')}
                  className="px-4 py-2.5 bg-white/10 hover:bg-white/20 font-bold rounded-xl text-sm transition-all"
                  data-testid="zip-frontend-btn"
                >⚛️ frontend/src فقط</button>
              </div>
            </div>
          </div>
        </div>

        <div className="text-center text-xs text-white/40 mb-3">— أو تصفّح ملف ملف —</div>

        <div className="sticky top-0 z-10 bg-[#0a0b14]/90 backdrop-blur-md py-3 mb-4 border-b border-white/10">
          <div className="flex gap-3 items-center">
            <input
              type="text"
              placeholder="🔍 ابحث (مثال: shipping أو ClientDashboard)"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="flex-1 px-4 py-2.5 bg-white/5 border border-white/15 rounded-xl text-sm focus:border-yellow-400 outline-none"
              data-testid="source-search"
            />
            <div className="text-xs text-white/60 whitespace-nowrap">{filtered.length} ملف</div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-20 opacity-60">⏳ جاري تحميل قائمة الملفات...</div>
        ) : (
          <div className="space-y-4">
            {groups.map(([group, items]) => (
              <details key={group} open={items.length < 30} className="bg-white/[.03] border border-white/10 rounded-xl">
                <summary className="cursor-pointer p-4 font-black text-yellow-300 select-none flex items-center justify-between">
                  <span>📁 {group}</span>
                  <span className="text-[11px] text-white/50 font-normal">{items.length} ملف</span>
                </summary>
                <div className="border-t border-white/10">
                  {items.map((f) => (
                    <div key={f.path} className="flex items-center gap-2 p-3 border-b border-white/5 hover:bg-white/[.04] transition-colors" data-testid={`source-file-${f.path}`}>
                      <code className="flex-1 min-w-0 text-xs md:text-sm font-mono truncate text-white/90">{f.path}</code>
                      <span className="hidden md:inline text-[10px] text-white/40 whitespace-nowrap">{fmtSize(f.size)}</span>
                      <button
                        onClick={() => openFile(f.path)}
                        className="text-[11px] px-2.5 py-1.5 bg-blue-500/20 hover:bg-blue-500/40 rounded-lg font-bold whitespace-nowrap"
                        title="فتح الملف في تبويب جديد"
                        data-testid={`view-${f.path}`}
                      >👁️ عرض</button>
                      <button
                        onClick={() => copyContent(f.path)}
                        className={`text-[11px] px-2.5 py-1.5 rounded-lg font-bold whitespace-nowrap ${copied[f.path] ? 'bg-emerald-500/40' : 'bg-white/10 hover:bg-white/20'}`}
                        title="نسخ المحتوى"
                        data-testid={`copy-${f.path}`}
                      >{copied[f.path] ? '✓ نسخ' : '📋 نسخ'}</button>
                      <button
                        onClick={() => downloadFile(f.path)}
                        className="text-[11px] px-2.5 py-1.5 bg-yellow-500/20 hover:bg-yellow-500/40 rounded-lg font-bold whitespace-nowrap"
                        title="تنزيل الملف"
                        data-testid={`download-${f.path}`}
                      >⬇️ تنزيل</button>
                    </div>
                  ))}
                </div>
              </details>
            ))}
          </div>
        )}

        <div className="mt-8 p-5 bg-gradient-to-br from-yellow-500/10 to-orange-500/10 border border-yellow-400/30 rounded-2xl">
          <div className="font-black text-yellow-300 mb-2">💡 نصيحة سريعة</div>
          <ul className="text-sm text-white/80 list-disc pr-5 space-y-1">
            <li>كل ملف يُحفظ بنفس المسار في الـ repo (مثال: <code className="text-yellow-300">backend/modules/websites/shipping.py</code>).</li>
            <li>الملفات الحساسة (.env، .git، node_modules، test_credentials) محجوبة تلقائياً ولن تظهر هنا.</li>
            <li>بعد رفع كل الملفات، انسخ <code>backend/.env.example</code> إلى <code>.env</code> وعبّئ القيم على Railway/Vercel.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
