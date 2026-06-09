import React, { useEffect, useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { BackButton } from '@/components/BackButton';
import { useNavigate } from 'react-router-dom';
import { Image as ImageIcon, Download, Share2, Trash2, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const MyImages = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/login'); return; }

    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/generate/images/history`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        setItems(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [navigate]);

  const handleShare = async (img) => {
    const url = img.image_url || img.url;
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'صورة من Zerax AI',
          text: img.prompt || 'تم إنشاؤها بواسطة Zerax',
          url,
        });
        toast.success('تمت المشاركة بنجاح');
      } catch (e) { /* user cancelled */ }
    } else {
      await navigator.clipboard.writeText(url);
      toast.success('تم نسخ الرابط للحافظة');
    }
  };

  const handleDownload = (img) => {
    const url = img.image_url || img.url;
    const a = document.createElement('a');
    a.href = url;
    a.download = `zitex-image-${img.id || Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a14] via-[#0a0a18] to-[#0a0a12]" data-testid="my-images-page">
      <Navbar user={user} setUser={setUser} transparent />

      <div className="container mx-auto px-4 md:px-8 max-w-7xl pt-24 pb-12">
        <div className="mb-6"><BackButton to="/dashboard" label="لوحة التحكم" /></div>

        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl md:text-4xl font-black text-white flex items-center gap-3">
              <ImageIcon className="w-8 h-8 text-purple-400" />
              صوري المحفوظة
            </h1>
            <p className="text-gray-400 text-sm mt-1">كل الصور اللي ولدتها · {items.length} صورة</p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/studio/image')}
            className="navbar-btn-primary inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-black text-black"
            data-testid="create-new-image-btn"
          >
            <Sparkles className="w-4 h-4" />
            إنشاء جديد
          </button>
        </div>

        {loading ? (
          <div className="text-center py-20 text-gray-500">جاري التحميل...</div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 rounded-2xl bg-slate-800/40 border border-slate-700">
            <ImageIcon className="w-16 h-16 text-purple-400/30 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">لا توجد صور بعد</h3>
            <p className="text-gray-400 text-sm mb-6">ابدأ بإنشاء أول صورة لك في استوديو الصور</p>
            <button
              type="button"
              onClick={() => navigate('/studio/image')}
              className="navbar-btn-primary inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-black text-black"
            >
              <Sparkles className="w-4 h-4" />
              أنشئ صورتك الأولى
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {items.map((img, idx) => (
              <div
                key={img.id || idx}
                className="group relative rounded-xl overflow-hidden aspect-square bg-slate-800 border border-slate-700 cursor-pointer"
                onClick={() => setSelected(img)}
                data-testid={`image-${idx}`}
              >
                <img
                  src={img.image_url || img.url}
                  alt={img.prompt || ''}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-3">
                  <p className="text-white text-xs font-medium line-clamp-2 mb-2">{img.prompt}</p>
                  <div className="flex gap-1">
                    <button type="button" onClick={(e) => { e.stopPropagation(); handleShare(img); }} className="flex-1 py-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white text-xs font-bold flex items-center justify-center gap-1">
                      <Share2 className="w-3 h-3" /> مشاركة
                    </button>
                    <button type="button" onClick={(e) => { e.stopPropagation(); handleDownload(img); }} className="flex-1 py-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white text-xs font-bold flex items-center justify-center gap-1">
                      <Download className="w-3 h-3" /> تنزيل
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Lightbox */}
        {selected && (
          <div
            className="fixed inset-0 bg-black/90 z-[100] flex items-center justify-center p-4"
            onClick={() => setSelected(null)}
            data-testid="image-lightbox"
          >
            <div className="max-w-4xl w-full" onClick={(e) => e.stopPropagation()}>
              <img src={selected.image_url || selected.url} alt="" className="w-full rounded-xl mb-4" />
              <p className="text-white text-sm mb-4">{selected.prompt}</p>
              <div className="flex gap-2">
                <button type="button" onClick={() => handleShare(selected)} className="flex-1 py-3 rounded-xl bg-amber-500 hover:bg-amber-600 text-black font-black text-sm flex items-center justify-center gap-2">
                  <Share2 className="w-4 h-4" /> مشاركة على السوشال
                </button>
                <button type="button" onClick={() => handleDownload(selected)} className="flex-1 py-3 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-black text-sm flex items-center justify-center gap-2">
                  <Download className="w-4 h-4" /> تنزيل
                </button>
                <button type="button" onClick={() => setSelected(null)} className="px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white">
                  إغلاق
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MyImages;
