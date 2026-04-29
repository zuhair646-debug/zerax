/**
 * Studio Hub — entry page for the Image & Video studios.
 * Routes: /studio
 *
 * Shows credits balance, links to Image/Video studios, and the gallery.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Coins, ImageIcon, Video, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function StudioHub({ user }) {
  const navigate = useNavigate();
  const [credits, setCredits] = useState(null);
  const [pricing, setPricing] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/login'); return; }
    fetch(`${API}/api/studio/credits`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) { setCredits(d.credits); setPricing(d.pricing); } })
      .catch(() => toast.error('فشل تحميل الرصيد'));
  }, [navigate]);

  return (
    <div className="min-h-screen bg-[#0a0a12]" data-testid="studio-hub">
      <Navbar user={user} transparent />
      <div className="pt-20 max-w-5xl mx-auto px-4 pb-16">
        {/* Credits header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl sm:text-4xl font-black text-white mb-1">
              استوديو <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">الذكاء الاصطناعي</span>
            </h1>
            <p className="text-amber-200/70 text-sm">أنشئ صوراً وفيديوهات احترافية لمتجرك بسيناريو عميق</p>
          </div>
          <div className="flex-shrink-0 px-4 py-3 rounded-xl bg-gradient-to-br from-amber-500/15 to-yellow-500/10 border border-amber-400/30 text-right" data-testid="studio-credits-balance">
            <div className="text-[10px] font-bold text-amber-300/70 tracking-widest mb-0.5">رصيدك</div>
            <div className="flex items-center gap-2 justify-end">
              <Coins className="w-5 h-5 text-amber-400" />
              <span className="text-2xl font-black text-amber-300">{credits ?? '...'}</span>
              <span className="text-xs text-amber-200/60">نقطة</span>
            </div>
          </div>
        </div>

        {/* Studio cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div
            onClick={() => navigate('/studio/image')}
            className="group cursor-pointer relative rounded-2xl overflow-hidden border border-white/10 hover:border-purple-400/50 transition-all hover:shadow-[0_20px_60px_-12px_rgba(168,85,247,0.4)] hover:scale-[1.02]"
            data-testid="studio-card-image"
          >
            <div className="absolute inset-0 bg-cover bg-center scale-110 group-hover:scale-125 transition-transform duration-700"
              style={{ backgroundImage: `url('https://images.unsplash.com/photo-1502691876148-a84978e59af8?auto=format&fit=crop&w=1200&q=70')` }} />
            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/80 to-purple-900/30" />
            <div className="relative p-6 sm:p-8 min-h-[260px] flex flex-col justify-end text-right">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-400 to-violet-500 flex items-center justify-center shadow-lg">
                  <ImageIcon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-black text-white">إنشاء صور</h2>
                  <p className="text-xs text-white/60">سيناريو + جمهور + مزاج</p>
                </div>
              </div>
              <p className="text-sm text-white/75 mb-4 leading-relaxed">
                صور إعلانية عميقة لمتجرك بسيناريو احترافي، مع إمكانية التعديل بدل إعادة التوليد
              </p>
              <div className="flex items-center justify-between">
                <span className="text-xs px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 font-bold">
                  {pricing?.image ?? 5} نقاط
                </span>
                <span className="text-purple-300 font-black text-sm group-hover:translate-x-2 transition-transform">
                  ابدأ ←
                </span>
              </div>
            </div>
          </div>

          <div
            onClick={() => navigate('/studio/video')}
            className="group cursor-pointer relative rounded-2xl overflow-hidden border border-white/10 hover:border-orange-400/50 transition-all hover:shadow-[0_20px_60px_-12px_rgba(249,115,22,0.4)] hover:scale-[1.02]"
            data-testid="studio-card-video"
          >
            <div className="absolute inset-0 bg-cover bg-center scale-110 group-hover:scale-125 transition-transform duration-700"
              style={{ backgroundImage: `url('https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=1200&q=70')` }} />
            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/80 to-orange-900/30" />
            <div className="relative p-6 sm:p-8 min-h-[260px] flex flex-col justify-end text-right">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center shadow-lg">
                  <Video className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-black text-white">إنشاء فيديو</h2>
                  <p className="text-xs text-white/60">سيناريو + نص صوتي + مدة</p>
                </div>
              </div>
              <p className="text-sm text-white/75 mb-4 leading-relaxed">
                فيديو احترافي بـ Sora 2 — مع سيناريو منفصل عن النص الصوتي وحساب التكلفة قبل الإنشاء
              </p>
              <div className="flex items-center justify-between">
                <span className="text-xs px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 font-bold">
                  {pricing?.video_per_second ?? 4} نقاط/ثانية
                </span>
                <span className="text-orange-300 font-black text-sm group-hover:translate-x-2 transition-transform">
                  ابدأ ←
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="mt-8 p-4 rounded-xl bg-amber-500/5 border border-amber-400/15 text-amber-200/80 text-xs leading-relaxed flex items-start gap-3">
          <Sparkles className="w-4 h-4 text-amber-300 flex-shrink-0 mt-0.5" />
          <div>
            كل عملية توليد تستهلك نقاطاً من رصيدك — يتم خصمها تلقائياً قبل البدء، وتُعاد تلقائياً إذا فشل التوليد.
            <br/>
            في حالة عدم رضاك عن النتيجة، استخدم زر <strong className="text-amber-300">"تعديل"</strong> (3 نقاط) بدل إعادة التوليد للحصول على تحسين دقيق.
          </div>
        </div>
      </div>
    </div>
  );
}
