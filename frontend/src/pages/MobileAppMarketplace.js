import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { ChevronRight, Smartphone, Gamepad2, AppWindow, Wrench, Baby, Eye, GitFork, Loader2, Sparkles, Download, Globe } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORY_META = {
  game: { Icon: Gamepad2, label: '🎮 ألعاب', color: 'from-rose-500 to-orange-500' },
  app: { Icon: AppWindow, label: '📱 تطبيقات', color: 'from-cyan-500 to-blue-600' },
  tool: { Icon: Wrench, label: '🛠️ أدوات', color: 'from-emerald-500 to-teal-600' },
  kids: { Icon: Baby, label: '🧒 أطفال', color: 'from-fuchsia-500 to-pink-600' },
};

const fetchJson = async (url, options = {}) => {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${url}`, { ...options, headers });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text }; }
  if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
  return data;
};

export default function MobileAppMarketplace() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('all');
  const [sort, setSort] = useState('remix');
  const [remixingId, setRemixingId] = useState(null);
  const [topCreators, setTopCreators] = useState([]);
  const [creatorsWindow, setCreatorsWindow] = useState('week');

  const load = async (cat, srt) => {
    setLoading(true);
    try {
      const q = new URLSearchParams({ category: cat, sort: srt });
      const r = await fetch(`${API}/api/mobile-app/marketplace?${q.toString()}`);
      const d = await r.json();
      setTemplates(d.templates || []);
    } catch (e) {
      toast.error(e.message || 'فشل تحميل المعرض');
    }
    setLoading(false);
  };

  useEffect(() => { load(category, sort); }, [category, sort]);

  // Load top creators
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/mobile-app/top-creators?window=${creatorsWindow}`);
        const d = await r.json();
        setTopCreators(d.creators || []);
      } catch {}
    })();
  }, [creatorsWindow]);

  const remix = async (id) => {
    const token = localStorage.getItem('token');
    if (!token) { toast.error('سجّل الدخول أولاً للريمكس'); navigate('/login'); return; }
    setRemixingId(id);
    try {
      const d = await fetchJson(`/api/mobile-app/remix/${id}`, { method: 'POST' });
      toast.success('تم نسخ القالب! خذني للباني...');
      // Pass session_id via localStorage so MobileAppBuilder picks it up
      localStorage.setItem('zenrex_mobile_remix_session', d.session_id);
      navigate('/dashboard/apps');
    } catch (e) {
      toast.error(e.message);
    }
    setRemixingId(null);
  };

  return (
    <div className="min-h-screen bg-[#06060f] text-white" dir="rtl" data-testid="mobile-marketplace">
      {/* HEADER */}
      <div className="border-b border-cyan-400/15 bg-[#0a0a14]/80 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button onClick={() => navigate('/dashboard')} className="p-2 rounded-lg hover:bg-white/5">
              <ChevronRight className="w-5 h-5 rotate-180" />
            </button>
            <Globe className="w-6 h-6 text-cyan-400" />
            <div>
              <div className="font-black text-sm">سوق التطبيقات</div>
              <div className="text-[10px] text-white/40">تطبيقات صنعها المجتمع — اعمل Remix وحوّلها لتطبيقك</div>
            </div>
          </div>
          <button
            onClick={() => navigate('/dashboard/apps')}
            className="px-3 py-1.5 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 hover:from-cyan-400 text-white text-xs font-bold flex items-center gap-1.5"
            data-testid="open-builder-btn"
          >
            <Sparkles className="w-3.5 h-3.5" /> ابني تطبيقي
          </button>
        </div>
      </div>

      {/* FILTERS */}
      <div className="max-w-7xl mx-auto px-4 py-4 flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1.5">
          {['all', 'game', 'app', 'tool', 'kids'].map((c) => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`px-3 py-1.5 rounded-full text-xs font-bold border transition ${
                category === c
                  ? 'bg-cyan-500/20 border-cyan-400/50 text-cyan-100'
                  : 'bg-white/5 border-white/10 text-white/60 hover:bg-white/10'
              }`}
              data-testid={`filter-${c}`}
            >
              {c === 'all' ? 'الكل' : CATEGORY_META[c]?.label || c}
            </button>
          ))}
        </div>
        <div className="ms-auto flex items-center gap-1.5">
          <button
            onClick={() => setSort('remix')}
            className={`px-3 py-1.5 rounded-full text-xs font-bold border ${
              sort === 'remix' ? 'bg-amber-500/20 border-amber-400/50 text-amber-100' : 'bg-white/5 border-white/10 text-white/60'
            }`}
            data-testid="sort-remix"
          >🔥 الأكثر Remix</button>
          <button
            onClick={() => setSort('new')}
            className={`px-3 py-1.5 rounded-full text-xs font-bold border ${
              sort === 'new' ? 'bg-amber-500/20 border-amber-400/50 text-amber-100' : 'bg-white/5 border-white/10 text-white/60'
            }`}
            data-testid="sort-new"
          >🆕 الأحدث</button>
        </div>
      </div>

      {/* TOP CREATORS LEADERBOARD */}
      {topCreators.length > 0 && (
        <div className="max-w-7xl mx-auto px-4 pb-2">
          <div className="rounded-2xl bg-gradient-to-br from-amber-500/10 via-amber-500/5 to-transparent border border-amber-400/20 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-black flex items-center gap-2 text-amber-100">
                🏆 المبدعون الأكثر تأثيراً
                <span className="text-[10px] text-amber-300/60 font-normal">(حسب عدد الـRemix)</span>
              </h3>
              <div className="flex gap-1">
                {[
                  { id: 'week', label: 'هذا الأسبوع' },
                  { id: 'month', label: 'هذا الشهر' },
                  { id: 'all', label: 'كل الوقت' },
                ].map((w) => (
                  <button
                    key={w.id}
                    onClick={() => setCreatorsWindow(w.id)}
                    className={`px-2.5 py-1 rounded-full text-[10px] font-bold border transition ${
                      creatorsWindow === w.id
                        ? 'bg-amber-500/25 border-amber-400/50 text-amber-100'
                        : 'bg-white/5 border-white/10 text-white/50 hover:text-white/80'
                    }`}
                    data-testid={`window-${w.id}`}
                  >
                    {w.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
              {topCreators.slice(0, 5).map((c) => (
                <div
                  key={c.user_id}
                  className="px-3 py-2 rounded-xl bg-white/[0.04] border border-white/10 flex items-center gap-2"
                  data-testid={`creator-${c.rank}`}
                >
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-black flex-shrink-0 ${
                    c.rank === 1 ? 'bg-gradient-to-br from-amber-400 to-yellow-600 text-black' :
                    c.rank === 2 ? 'bg-gradient-to-br from-zinc-300 to-zinc-500 text-black' :
                    c.rank === 3 ? 'bg-gradient-to-br from-orange-600 to-orange-800 text-white' :
                    'bg-white/10 text-white/70'
                  }`}>
                    {c.rank === 1 ? '🥇' : c.rank === 2 ? '🥈' : c.rank === 3 ? '🥉' : `#${c.rank}`}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-bold truncate">{c.name}</div>
                    <div className="text-[10px] text-amber-300/80">
                      {c.total_remixes} remix · {c.apps_published} app
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* GRID */}
      <div className="max-w-7xl mx-auto px-4 pb-12">
        {loading ? (
          <div className="flex items-center justify-center py-24 text-white/40">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : templates.length === 0 ? (
          <div className="text-center py-24 text-white/40">
            <Smartphone className="w-12 h-12 mx-auto mb-3 opacity-40" />
            <div>لا توجد تطبيقات منشورة في هذي الفئة بعد.</div>
            <button onClick={() => navigate('/dashboard/apps')} className="mt-4 px-4 py-2 rounded-full bg-cyan-500/20 border border-cyan-400/40 text-cyan-100 text-sm font-bold">كن أول من ينشر</button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((t) => {
              const meta = CATEGORY_META[t.category] || CATEGORY_META.app;
              const Icon = meta.Icon;
              return (
                <div
                  key={t.id}
                  className="group relative bg-white/[0.03] hover:bg-white/[0.06] border border-white/10 hover:border-cyan-400/30 rounded-2xl overflow-hidden transition"
                  data-testid={`template-${t.id}`}
                >
                  {/* iPhone-styled mini preview */}
                  <div className="relative bg-gradient-to-br from-zinc-900 to-zinc-950 aspect-[9/16] flex items-center justify-center overflow-hidden">
                    <iframe
                      src={`${API}/api/mobile-app/public/${t.id}`}
                      className="w-[375px] h-[667px] origin-top-right scale-[0.55] pointer-events-none"
                      title={t.name}
                      sandbox="allow-scripts"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/40 pointer-events-none" />
                    <div className={`absolute top-2 right-2 w-9 h-9 rounded-xl bg-gradient-to-br ${meta.color} flex items-center justify-center shadow-lg`}>
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                  </div>
                  {/* Meta */}
                  <div className="p-3">
                    <div className="font-black text-sm truncate">{t.name}</div>
                    <div className="text-[10px] text-white/40 mt-0.5 flex items-center justify-between">
                      <span>بواسطة {t.author_name}</span>
                      <span className="flex items-center gap-1">
                        <GitFork className="w-3 h-3" />
                        {t.remix_count || 0}
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-1.5">
                      <a
                        href={`${API}/api/mobile-app/public/${t.id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="px-2 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-[11px] text-white/80 font-bold flex items-center justify-center gap-1"
                      >
                        <Eye className="w-3 h-3" /> معاينة
                      </a>
                      <button
                        onClick={() => remix(t.id)}
                        disabled={remixingId === t.id}
                        className="px-2 py-1.5 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 hover:from-cyan-400 text-white text-[11px] font-bold flex items-center justify-center gap-1 disabled:opacity-50"
                        data-testid={`remix-${t.id}`}
                      >
                        {remixingId === t.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <GitFork className="w-3 h-3" />} Remix
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
