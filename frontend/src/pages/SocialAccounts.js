import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { BackButton } from '@/components/BackButton';
import { Link2, CheckCircle, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

const PLATFORMS = [
  { id: 'instagram', name: 'Instagram', icon: '📷', color: '#E1306C', gradient: 'from-pink-500 via-purple-500 to-orange-500', desc: 'صور · ريلز · ستوريز' },
  { id: 'tiktok', name: 'TikTok', icon: '🎵', color: '#000000', gradient: 'from-black via-pink-500 to-cyan-500', desc: 'فيديوهات قصيرة' },
  { id: 'twitter', name: 'X / Twitter', icon: '𝕏', color: '#1DA1F2', gradient: 'from-slate-800 to-slate-900', desc: 'تغريدات + صور + فيديو' },
  { id: 'facebook', name: 'Facebook', icon: 'f', color: '#1877F2', gradient: 'from-blue-600 to-blue-700', desc: 'بوستات + صفحات' },
  { id: 'youtube', name: 'YouTube', icon: '▶', color: '#FF0000', gradient: 'from-red-600 to-red-700', desc: 'فيديوهات طويلة + Shorts' },
  { id: 'snapchat', name: 'Snapchat', icon: '👻', color: '#FFFC00', gradient: 'from-yellow-400 to-yellow-500', desc: 'سناب · ستوريز' },
  { id: 'linkedin', name: 'LinkedIn', icon: 'in', color: '#0A66C2', gradient: 'from-sky-700 to-blue-800', desc: 'محتوى احترافي' },
  { id: 'whatsapp', name: 'واتساب', icon: '💬', color: '#25D366', gradient: 'from-green-500 to-emerald-600', desc: 'حالات + شات' },
];

const SocialAccounts = ({ user, setUser }) => {
  const [connected, setConnected] = useState({});

  useEffect(() => {
    const saved = localStorage.getItem('zenrex_connected_socials');
    if (saved) setConnected(JSON.parse(saved));
  }, []);

  const toggleConnect = (id) => {
    const next = { ...connected, [id]: !connected[id] };
    setConnected(next);
    localStorage.setItem('zenrex_connected_socials', JSON.stringify(next));
    if (next[id]) {
      toast.success(`تم ربط ${PLATFORMS.find((p) => p.id === id).name} بنجاح`);
    } else {
      toast.info(`تم فصل ${PLATFORMS.find((p) => p.id === id).name}`);
    }
  };

  const connectedCount = Object.values(connected).filter(Boolean).length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a14] via-[#0a0a18] to-[#0a0a12]" data-testid="social-accounts-page">
      <Navbar user={user} setUser={setUser} transparent />

      <div className="container mx-auto px-4 md:px-8 max-w-5xl pt-24 pb-12">
        <div className="mb-6"><BackButton to="/dashboard" label="لوحة التحكم" /></div>

        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-black text-white mb-2 flex items-center gap-3">
            <Link2 className="w-8 h-8 text-pink-400" />
            الحسابات المرتبطة
          </h1>
          <p className="text-gray-400 text-sm">
            اربط حساباتك الاجتماعية مرة واحدة — وانشر محتواك بضغطة زر · {connectedCount} منصة مرتبطة
          </p>
        </div>

        <div className="rounded-2xl bg-amber-500/10 border border-amber-500/30 p-4 mb-8">
          <p className="text-amber-200 text-sm">
            <strong>ملاحظة:</strong> الربط حالياً عبر <strong>Web Share</strong> (مشاركة من جهازك مباشرة).
            قريباً جداً: ربط OAuth مباشر للنشر التلقائي بدون أي خطوات إضافية. 🚀
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {PLATFORMS.map((p) => {
            const isConnected = !!connected[p.id];
            return (
              <div
                key={p.id}
                className="rounded-2xl overflow-hidden border border-white/10 bg-slate-800/50"
                data-testid={`platform-${p.id}`}
              >
                <div className={`bg-gradient-to-r ${p.gradient} p-5 flex items-center gap-4`}>
                  <div
                    className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-black bg-white/15 backdrop-blur-md border border-white/25"
                  >
                    {p.icon}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-white text-lg font-black">{p.name}</h3>
                    <p className="text-white/85 text-xs font-medium">{p.desc}</p>
                  </div>
                  {isConnected && <CheckCircle className="w-6 h-6 text-white" />}
                </div>
                <div className="p-3 bg-slate-900/60">
                  <button
                    type="button"
                    onClick={() => toggleConnect(p.id)}
                    className={`navbar-btn w-full py-2.5 rounded-lg font-bold text-sm flex items-center justify-center gap-2 ${
                      isConnected
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        : 'bg-white/10 text-white border border-white/20'
                    }`}
                    data-testid={`toggle-${p.id}`}
                  >
                    {isConnected ? (
                      <><CheckCircle className="w-4 h-4" /> مرتبط — اضغط للفصل</>
                    ) : (
                      <><Link2 className="w-4 h-4" /> ربط الحساب</>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default SocialAccounts;
