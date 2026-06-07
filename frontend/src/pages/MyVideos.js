import React, { useEffect, useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { BackButton } from '@/components/BackButton';
import { useNavigate } from 'react-router-dom';
import { Video, Download, Share2, Sparkles, Play } from 'lucide-react';
import { toast } from 'sonner';

const MyVideos = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/login'); return; }
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/generate/videos/history`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => { setItems(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [navigate]);

  const handleShare = async (v) => {
    const url = v.video_url || v.url;
    if (navigator.share) {
      try { await navigator.share({ title: 'فيديو من Zitex', text: v.prompt || '', url }); toast.success('تمت المشاركة'); } catch (e) {}
    } else {
      await navigator.clipboard.writeText(url);
      toast.success('تم نسخ الرابط');
    }
  };

  const handleDownload = (v) => {
    const a = document.createElement('a');
    a.href = v.video_url || v.url;
    a.download = `zitex-video-${v.id || Date.now()}.mp4`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a14] via-[#0a0a18] to-[#0a0a12]" data-testid="my-videos-page">
      <Navbar user={user} setUser={setUser} transparent />
      <div className="container mx-auto px-4 md:px-8 max-w-7xl pt-24 pb-12">
        <div className="mb-6"><BackButton to="/dashboard" label="لوحة التحكم" /></div>

        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl md:text-4xl font-black text-white flex items-center gap-3">
              <Video className="w-8 h-8 text-orange-400" />
              فيديوهاتي
            </h1>
            <p className="text-gray-400 text-sm mt-1">{items.length} فيديو · جودة عالية</p>
          </div>
          <button type="button" onClick={() => navigate('/studio/video')} className="navbar-btn-primary inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-black text-black">
            <Sparkles className="w-4 h-4" /> إنشاء جديد
          </button>
        </div>

        {loading ? (
          <div className="text-center py-20 text-gray-500">جاري التحميل...</div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 rounded-2xl bg-slate-800/40 border border-slate-700">
            <Video className="w-16 h-16 text-orange-400/30 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">لا توجد فيديوهات بعد</h3>
            <p className="text-gray-400 text-sm mb-6">ابدأ بإنشاء أول فيديو بـ Sora 2</p>
            <button type="button" onClick={() => navigate('/studio/video')} className="navbar-btn-primary inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-black text-black">
              <Sparkles className="w-4 h-4" /> أنشئ فيديو
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((v, idx) => (
              <div key={v.id || idx} className="rounded-xl overflow-hidden bg-slate-800 border border-slate-700" data-testid={`video-${idx}`}>
                <div className="relative aspect-video bg-black">
                  <video src={v.video_url || v.url} className="w-full h-full object-cover" controls preload="metadata" />
                </div>
                <div className="p-3">
                  <p className="text-white text-xs font-medium line-clamp-2 mb-3">{v.prompt}</p>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => handleShare(v)} className="flex-1 py-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs font-bold flex items-center justify-center gap-1">
                      <Share2 className="w-3 h-3" /> مشاركة
                    </button>
                    <button type="button" onClick={() => handleDownload(v)} className="flex-1 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold flex items-center justify-center gap-1">
                      <Download className="w-3 h-3" /> تنزيل
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MyVideos;
