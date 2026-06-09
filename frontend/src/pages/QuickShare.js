import React, { useEffect, useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { BackButton } from '@/components/BackButton';
import { useNavigate } from 'react-router-dom';
import { Send, Image as ImageIcon, Video, Share2, Link2, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';

const PLATFORMS = [
  { id: 'instagram', name: 'Instagram', color: '#E1306C', emoji: '📷' },
  { id: 'tiktok', name: 'TikTok', color: '#000000', emoji: '🎵' },
  { id: 'twitter', name: 'Twitter', color: '#1DA1F2', emoji: '𝕏' },
  { id: 'facebook', name: 'Facebook', color: '#1877F2', emoji: 'f' },
  { id: 'whatsapp', name: 'WhatsApp', color: '#25D366', emoji: '💬' },
  { id: 'snapchat', name: 'Snapchat', color: '#FFFC00', emoji: '👻' },
];

const QuickShare = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [tab, setTab] = useState('images'); // 'images' | 'videos'
  const [assets, setAssets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/login'); return; }
    const path = tab === 'images' ? 'images' : 'videos';
    setLoading(true);
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/generate/${path}/history`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => { setAssets(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [tab, navigate]);

  const shareNative = async (platform) => {
    if (!selected) return toast.error('اختاري ملف للنشر أولاً');
    const url = selected.image_url || selected.video_url || selected.url;
    const text = `${selected.prompt || 'محتوى من Zerax AI'} ✨\n#Zerax`;

    // Save to history
    const history = JSON.parse(localStorage.getItem('zitex_share_history') || '[]');
    history.unshift({
      platform: platform.id,
      platformName: platform.name,
      assetId: selected.id,
      assetUrl: url,
      prompt: selected.prompt,
      timestamp: Date.now(),
    });
    localStorage.setItem('zitex_share_history', JSON.stringify(history.slice(0, 50)));

    if (navigator.share) {
      try {
        await navigator.share({ title: `نشر على ${platform.name}`, text, url });
        toast.success(`تم فتح ${platform.name}!`);
      } catch (e) { /* cancelled */ }
    } else {
      // Fallback: open platform's intent URL
      const intents = {
        twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
        whatsapp: `https://wa.me/?text=${encodeURIComponent(text + ' ' + url)}`,
        facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
      };
      if (intents[platform.id]) {
        window.open(intents[platform.id], '_blank');
        toast.success(`تم فتح ${platform.name} في تبويب جديد`);
      } else {
        await navigator.clipboard.writeText(url);
        toast.info(`تم نسخ الرابط · افتحي ${platform.name} والصقي`);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a14] via-[#0a0a18] to-[#0a0a12]" data-testid="quick-share-page">
      <Navbar user={user} setUser={setUser} transparent />
      <div className="container mx-auto px-4 md:px-8 max-w-6xl pt-24 pb-12">
        <div className="mb-6"><BackButton to="/dashboard" label="لوحة التحكم" /></div>

        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-black text-white flex items-center gap-3 mb-2">
            <Send className="w-8 h-8 text-emerald-400" />
            النشر السريع
          </h1>
          <p className="text-gray-400 text-sm">اختاري ملف من مكتبتك → اضغطي منصة لنشره فوراً</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button type="button" onClick={() => { setTab('images'); setSelected(null); }} className={`navbar-btn px-4 py-2 rounded-lg text-sm font-bold border ${tab === 'images' ? 'bg-amber-500/20 text-amber-300 border-amber-500/50' : 'bg-slate-800/50 text-gray-400 border-slate-700'}`}>
            <ImageIcon className="w-4 h-4 inline ms-1" /> الصور
          </button>
          <button type="button" onClick={() => { setTab('videos'); setSelected(null); }} className={`navbar-btn px-4 py-2 rounded-lg text-sm font-bold border ${tab === 'videos' ? 'bg-amber-500/20 text-amber-300 border-amber-500/50' : 'bg-slate-800/50 text-gray-400 border-slate-700'}`}>
            <Video className="w-4 h-4 inline ms-1" /> الفيديوهات
          </button>
        </div>

        {/* Asset grid */}
        <div className="rounded-2xl bg-slate-800/40 border border-slate-700 p-4 mb-6">
          <h3 className="text-white font-bold text-sm mb-3">1. اختاري ملف:</h3>
          {loading ? (
            <p className="text-gray-500 text-center py-10">جاري التحميل...</p>
          ) : assets.length === 0 ? (
            <p className="text-gray-500 text-center py-10 text-sm">لا توجد {tab === 'images' ? 'صور' : 'فيديوهات'} للنشر</p>
          ) : (
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2 max-h-64 overflow-y-auto">
              {assets.map((a, idx) => (
                <button
                  type="button"
                  key={a.id || idx}
                  onClick={() => setSelected(a)}
                  className={`relative aspect-square rounded-lg overflow-hidden border-2 ${selected?.id === a.id ? 'border-amber-400' : 'border-slate-700'}`}
                  data-testid={`asset-${idx}`}
                >
                  {tab === 'images' ? (
                    <img src={a.image_url || a.url} alt="" className="w-full h-full object-cover" loading="lazy" />
                  ) : (
                    <video src={a.video_url || a.url} className="w-full h-full object-cover" muted />
                  )}
                  {selected?.id === a.id && (
                    <div className="absolute inset-0 bg-amber-400/30 flex items-center justify-center">
                      <CheckCircle className="w-6 h-6 text-white drop-shadow-lg" />
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Platform picker */}
        <div className="rounded-2xl bg-slate-800/40 border border-slate-700 p-4">
          <h3 className="text-white font-bold text-sm mb-3">2. اختاري منصة للنشر:</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
            {PLATFORMS.map((p) => (
              <button
                type="button"
                key={p.id}
                onClick={() => shareNative(p)}
                disabled={!selected}
                className="navbar-btn p-3 rounded-lg border border-slate-700 bg-slate-900/50 disabled:opacity-40 disabled:cursor-not-allowed flex flex-col items-center gap-1"
                style={{ borderColor: selected ? `${p.color}60` : undefined }}
                data-testid={`share-to-${p.id}`}
              >
                <span className="text-2xl">{p.emoji}</span>
                <span className="text-white text-xs font-bold">{p.name}</span>
              </button>
            ))}
          </div>
          {!selected && (
            <p className="text-amber-200/70 text-xs mt-3 text-center">اختاري ملف من الأعلى أولاً</p>
          )}
        </div>

        <button
          type="button"
          onClick={() => navigate('/dashboard/share-history')}
          className="navbar-btn w-full mt-6 py-3 rounded-xl border border-slate-700 bg-slate-800/40 text-gray-300 text-sm font-bold flex items-center justify-center gap-2"
        >
          <Share2 className="w-4 h-4" /> عرض سجل المشاركات
        </button>
      </div>
    </div>
  );
};

export default QuickShare;
