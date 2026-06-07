import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { BackButton } from '@/components/BackButton';
import { useNavigate } from 'react-router-dom';
import { Share2, Trash2, Calendar, ExternalLink } from 'lucide-react';

const ShareHistory = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);

  useEffect(() => {
    setHistory(JSON.parse(localStorage.getItem('zitex_share_history') || '[]'));
  }, []);

  const clear = () => {
    if (window.confirm('متأكدة من حذف كل السجل؟')) {
      localStorage.removeItem('zitex_share_history');
      setHistory([]);
    }
  };

  const formatDate = (ts) => {
    const d = new Date(ts);
    return d.toLocaleString('ar-SA', { dateStyle: 'medium', timeStyle: 'short' });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a14] via-[#0a0a18] to-[#0a0a12]" data-testid="share-history-page">
      <Navbar user={user} setUser={setUser} transparent />
      <div className="container mx-auto px-4 md:px-8 max-w-4xl pt-24 pb-12">
        <div className="mb-6"><BackButton to="/dashboard" label="لوحة التحكم" /></div>

        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl md:text-4xl font-black text-white flex items-center gap-3">
              <Share2 className="w-8 h-8 text-cyan-400" />
              سجل المشاركات
            </h1>
            <p className="text-gray-400 text-sm mt-1">{history.length} مشاركة محفوظة</p>
          </div>
          {history.length > 0 && (
            <button type="button" onClick={clear} className="navbar-btn px-4 py-2 rounded-lg border border-red-500/30 text-red-400 text-sm font-bold inline-flex items-center gap-2">
              <Trash2 className="w-4 h-4" /> حذف الكل
            </button>
          )}
        </div>

        {history.length === 0 ? (
          <div className="text-center py-20 rounded-2xl bg-slate-800/40 border border-slate-700">
            <Share2 className="w-16 h-16 text-cyan-400/30 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">لا يوجد سجل بعد</h3>
            <p className="text-gray-400 text-sm mb-6">ابدئي بمشاركة محتواك على السوشال ميديا</p>
            <button type="button" onClick={() => navigate('/dashboard/share')} className="navbar-btn-primary inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-black text-black">
              <Share2 className="w-4 h-4" /> ابدأي النشر
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {history.map((h, idx) => (
              <div key={idx} className="rounded-xl bg-slate-800/40 border border-slate-700 p-4 flex items-center gap-4" data-testid={`history-${idx}`}>
                <div className="flex-shrink-0">
                  {h.assetUrl?.includes('.mp4') ? (
                    <video src={h.assetUrl} className="w-16 h-16 rounded-lg object-cover" muted />
                  ) : (
                    <img src={h.assetUrl} alt="" className="w-16 h-16 rounded-lg object-cover" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-bold">{h.platformName}</span>
                    <span className="text-gray-500 text-[10px] inline-flex items-center gap-1">
                      <Calendar className="w-3 h-3" /> {formatDate(h.timestamp)}
                    </span>
                  </div>
                  <p className="text-white text-sm font-medium line-clamp-1">{h.prompt || 'بدون وصف'}</p>
                </div>
                <button type="button" onClick={() => window.open(h.assetUrl, '_blank')} className="navbar-btn p-2 rounded-lg border border-slate-600 text-gray-300" title="فتح الملف">
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ShareHistory;
