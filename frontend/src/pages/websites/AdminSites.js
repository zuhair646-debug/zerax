import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, ExternalLink, Eye, Copy, RefreshCw } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

export default function AdminSites() {
  const nav = useNavigate();
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [previewSite, setPreviewSite] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/admin/sites`, { headers: authH() });
      if (!r.ok) throw new Error(String(r.status));
      const d = await r.json();
      setSites(d.sites || []);
    } catch (e) {
      toast.error(e.message === '403' ? 'غير مسموح — لوحة المشرف فقط' : 'فشل التحميل');
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const copyLink = (slug) => {
    const url = `${window.location.origin}/sites/${slug}`;
    navigator.clipboard.writeText(url);
    toast.success('📋 تم نسخ الرابط: ' + url);
  };

  const totalVisits = sites.reduce((s, x) => s + (x.visits || 0), 0);

  return (
    <div className="min-h-screen bg-[#0b0f1f] text-white p-4 md:p-6" dir="rtl">
      <header className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => nav('/admin')} className="p-2 hover:bg-white/10 rounded-lg" data-testid="back-btn">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl md:text-2xl font-bold">🌐 المواقع المعتمدة — لوحة المشرف</h1>
        </div>
        <button onClick={load} className="p-2 bg-white/10 hover:bg-white/20 rounded-lg flex items-center gap-1.5" data-testid="refresh-btn">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> تحديث
        </button>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/10 border border-green-500/30 p-4 rounded-xl">
          <div className="text-3xl font-black text-green-400">{sites.length}</div>
          <div className="text-xs opacity-70 mt-1">مشروع معتمد</div>
        </div>
        <div className="bg-gradient-to-br from-yellow-500/20 to-orange-500/10 border border-yellow-500/30 p-4 rounded-xl">
          <div className="text-3xl font-black text-yellow-400">{totalVisits}</div>
          <div className="text-xs opacity-70 mt-1">إجمالي الزيارات</div>
        </div>
        <div className="bg-gradient-to-br from-blue-500/20 to-cyan-500/10 border border-blue-500/30 p-4 rounded-xl">
          <div className="text-3xl font-black text-blue-400">{new Set(sites.map((s) => s.user_id)).size}</div>
          <div className="text-xs opacity-70 mt-1">عميل نشط</div>
        </div>
        <div className="bg-gradient-to-br from-purple-500/20 to-pink-500/10 border border-purple-500/30 p-4 rounded-xl">
          <div className="text-3xl font-black text-purple-400">{sites.length ? Math.round(totalVisits / sites.length) : 0}</div>
          <div className="text-xs opacity-70 mt-1">متوسط زيارات/موقع</div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16 opacity-60">جاري التحميل...</div>
      ) : sites.length === 0 ? (
        <div className="text-center py-16 opacity-60">لا توجد مواقع معتمدة بعد</div>
      ) : (
        <div className="bg-[#0e1128] rounded-xl border border-white/10 overflow-x-auto">
          <table className="w-full text-sm" data-testid="sites-table">
            <thead>
              <tr className="border-b border-white/10 text-xs uppercase opacity-60">
                <th className="text-right p-3">الموقع</th>
                <th className="text-right p-3">المالك</th>
                <th className="text-right p-3">الرابط</th>
                <th className="text-right p-3">الزيارات</th>
                <th className="text-right p-3">الاعتماد</th>
                <th className="text-right p-3">الإجراء</th>
              </tr>
            </thead>
            <tbody>
              {sites.map((s) => (
                <tr key={s.id} className="border-b border-white/5 hover:bg-white/[0.03]" data-testid={`site-row-${s.id}`}>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-400" />
                      <span className="font-bold">{s.name}</span>
                      <span className="text-[10px] opacity-50 bg-white/5 px-1.5 py-0.5 rounded">{s.template}</span>
                    </div>
                  </td>
                  <td className="p-3 text-xs">
                    <div>{s.owner_name || '—'}</div>
                    <div className="opacity-60">{s.owner_email}</div>
                  </td>
                  <td className="p-3">
                    <code className="text-xs bg-white/5 px-2 py-1 rounded text-yellow-400">/sites/{s.slug}</code>
                  </td>
                  <td className="p-3 font-bold text-yellow-400">{s.visits || 0}</td>
                  <td className="p-3 text-xs opacity-70">{s.approved_at ? new Date(s.approved_at).toLocaleDateString('ar') : '—'}</td>
                  <td className="p-3">
                    <div className="flex gap-1">
                      <button onClick={() => copyLink(s.slug)} className="p-1.5 bg-white/10 hover:bg-white/20 rounded" title="نسخ الرابط" data-testid={`copy-${s.id}`}>
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => setPreviewSite(s)} className="p-1.5 bg-yellow-500/20 hover:bg-yellow-500/40 rounded text-yellow-400" title="معاينة" data-testid={`preview-${s.id}`}>
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <a href={`/sites/${s.slug}`} target="_blank" rel="noreferrer" className="p-1.5 bg-green-500/20 hover:bg-green-500/40 rounded text-green-400" title="فتح الموقع الحي" data-testid={`open-${s.id}`}>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Preview modal (iframe full-screen) */}
      {previewSite && (
        <div className="fixed inset-0 bg-black/95 z-50 flex flex-col" data-testid="preview-modal">
          <div className="flex items-center justify-between p-3 bg-[#0e1128] border-b border-white/10">
            <div className="flex items-center gap-3">
              <span className="font-bold">👁️ معاينة حية (بدون علم العميل)</span>
              <code className="text-xs bg-white/10 px-2 py-1 rounded text-yellow-400">/sites/{previewSite.slug}</code>
              <span className="text-xs opacity-60">👤 {previewSite.owner_email}</span>
            </div>
            <button onClick={() => setPreviewSite(null)} className="px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded text-xs font-bold" data-testid="close-preview-btn">إغلاق ✕</button>
          </div>
          <iframe
            src={`/sites/${previewSite.slug}`}
            className="flex-1 w-full bg-white"
            title="site-preview"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          />
        </div>
      )}
    </div>
  );
}
