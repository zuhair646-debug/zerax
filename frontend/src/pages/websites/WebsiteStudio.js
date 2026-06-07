import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, ArrowRight, Loader2, Coins, FolderOpen } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

// Credit cost per category (Zitex points)
const CATEGORY_CREDITS = {
  restaurant: 250, coffee: 250, store: 280, barber: 200, salon_women: 220,
  pets: 200, clinic: 250, bakery: 230, car_wash: 200, sports_club: 240,
  library: 200, art_gallery: 260, maintenance: 200, jewelry: 320,
  gym: 240, academy: 270, plumbing: 180, electrical: 180, company: 300,
  portfolio: 280, saas: 350, cosmetics: 290, automotive: 320, realestate: 300,
  blank: 150,
};

export default function WebsiteStudio({ user }) {
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState('');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [catR, projR] = await Promise.all([
          fetch(`${API}/api/websites/categories`),
          fetch(`${API}/api/freebuild-chat/projects`, { headers: authH() }),
        ]);
        if (catR.ok && !cancelled) {
          const d = await catR.json();
          setCategories(d.categories || []);
        }
        if (projR.ok && !cancelled) {
          const d = await projR.json();
          setProjects((d.projects || []).filter((p) => p.category_id));
        }
      } finally { if (!cancelled) setLoading(false); }
    };
    load();
    return () => { cancelled = true; };
  }, []);

  const startProject = async (cat) => {
    setCreating(cat.id);
    try {
      const r = await fetch(`${API}/api/freebuild-chat/project`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH() },
        body: JSON.stringify({
          name: `${cat.name} — ${new Date().toLocaleDateString('ar', { day: 'numeric', month: 'short' })}`,
          description: `مشروع جديد من قالب ${cat.name}`,
          category_id: cat.id,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل إنشاء المشروع');
      toast.success(`✨ بدأ مشروع ${cat.name}`);
      navigate(`/freebuild/chat/${d.id}`);
    } catch (e) {
      toast.error(e.message);
    } finally { setCreating(''); }
  };

  if (loading) {
    return (
      <div dir="rtl" className="min-h-screen bg-zinc-950 flex items-center justify-center text-zinc-400">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400 ml-2" /> جاري التحميل...
      </div>
    );
  }

  return (
    <div dir="rtl" className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-cyan-950/10 text-white">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-8">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shrink-0">
              <Sparkles className="w-7 h-7 text-black" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-black mb-1">قوالب جاهزة احترافية</h1>
              <p className="text-zinc-400 text-sm">اختر فئة → الذكاء يقترح 3 تصاميم → تختار وتشخصها بضغطة زر</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => navigate('/dashboard/websites')}
            data-testid="my-website-projects"
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white text-sm font-bold shrink-0"
          >
            <FolderOpen className="w-4 h-4" />
            <span className="hidden sm:inline">مشاريعي</span>
          </button>
        </div>

        {/* Recent projects (if any) */}
        {projects.length > 0 && (
          <div className="mb-8">
            <h2 className="text-sm font-bold text-cyan-300 mb-3 flex items-center gap-2">
              <FolderOpen className="w-4 h-4" /> آخر مشاريعك ({projects.length})
            </h2>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {projects.slice(0, 8).map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => navigate(`/freebuild/chat/${p.id}`)}
                  data-testid={`recent-project-${p.id}`}
                  className="shrink-0 w-56 rounded-xl bg-zinc-900/70 border border-white/10 hover:border-cyan-400/40 p-3 text-right transition-all"
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xl">{p.category_icon || '🌐'}</span>
                    <span className="text-[11px] text-cyan-300 font-bold">{p.category_name || 'قالب'}</span>
                  </div>
                  <h3 className="font-black text-sm truncate">{p.name}</h3>
                  <p className="text-[10px] text-zinc-500 truncate mt-0.5">
                    {(p.messages || []).length} رسالة · {(p.approved_assets || []).length} أصل
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Category grid — compact rectangular cards */}
        <h2 className="text-sm font-bold text-cyan-300 mb-3 flex items-center gap-2">
          <Sparkles className="w-4 h-4" /> {categories.length} فئة متاحة
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3" data-testid="category-grid">
          {categories.map((c) => {
            const credits = CATEGORY_CREDITS[c.id] ?? 250;
            const isBusy = creating === c.id;
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => !isBusy && startProject(c)}
                disabled={!!creating}
                data-testid={`category-${c.id}`}
                className="group relative overflow-hidden rounded-xl border border-white/10 hover:border-cyan-400/60 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-cyan-500/15 bg-zinc-900 disabled:opacity-40 text-right h-[130px] flex flex-col justify-end"
              >
                {/* Background image */}
                {c.image && (
                  <div
                    className="absolute inset-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-110"
                    style={{ backgroundImage: `url('${c.image}')` }}
                    aria-hidden
                  />
                )}
                {/* Gradient overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black via-black/60 to-black/10" />
                {/* Color tint on hover */}
                <div
                  className="absolute inset-0 opacity-0 group-hover:opacity-30 transition-opacity mix-blend-overlay"
                  style={{ background: `linear-gradient(135deg, ${c.color}, transparent 70%)` }}
                  aria-hidden
                />
                {/* Credit chip top-left */}
                <div className="absolute top-2 left-2 z-10">
                  <span className="px-2 py-0.5 rounded-full bg-amber-500/30 backdrop-blur border border-amber-400/40 text-amber-100 text-[10px] font-black flex items-center gap-1">
                    <Coins className="w-2.5 h-2.5" />
                    {credits}
                  </span>
                </div>
                {/* Layouts chip top-right */}
                <div className="absolute top-2 right-2 z-10">
                  <span className="px-2 py-0.5 rounded-full bg-black/60 backdrop-blur border border-white/10 text-white/80 text-[10px] font-bold">
                    {c.layouts_count} تصميم
                  </span>
                </div>
                {/* Bottom block */}
                <div className="relative z-10 p-2.5">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span
                      className="w-6 h-6 rounded-md flex items-center justify-center text-sm shrink-0 shadow-lg"
                      style={{ background: `${c.color}cc`, color: '#fff' }}
                    >
                      {c.icon}
                    </span>
                    <span className="font-black text-sm text-white drop-shadow-lg truncate group-hover:text-cyan-200 transition">
                      {c.name}
                    </span>
                  </div>
                  <div className="text-[10px] text-white/70 flex items-center gap-1 group-hover:text-cyan-300">
                    {isBusy ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>جاري الإنشاء...</span>
                      </>
                    ) : (
                      <>
                        <span>ابدأ مشروع جديد</span>
                        <ArrowRight className="w-3 h-3 rotate-180 transition-transform group-hover:-translate-x-0.5" />
                      </>
                    )}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Info banner */}
        <div className="mt-8 rounded-2xl bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-violet-500/10 border border-cyan-500/20 p-5">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center shrink-0">
              <Sparkles className="w-5 h-5 text-cyan-300" />
            </div>
            <div className="text-sm">
              <h3 className="font-black text-base mb-1 text-cyan-100">كيف تشتغل القوالب الجاهزة؟</h3>
              <ol className="text-zinc-300 text-[13px] space-y-1 list-decimal pr-5 marker:text-cyan-400 marker:font-bold">
                <li>تختار فئة (مثلاً: مطاعم، عيادات، متاجر).</li>
                <li>الذكاء يقترح <strong className="text-cyan-200">3 تصاميم مختلفة</strong> فوراً في الشات.</li>
                <li>تضغط «اعتمد» على اللي يعجبك → ينتقل للمعاينة الحية بدون تغيير.</li>
                <li>تجاوب على أسئلة سريعة (اسم النشاط، رقم تواصل) عبر <strong className="text-emerald-200">خيارات قابلة للضغط</strong>.</li>
                <li>الذكاء يستبدل النصوص والصور والألوان فقط — هيكل القالب يبقى كما هو (موثوق وسريع).</li>
                <li>تختار: استضافة مجانية معنا، أو استلام الكود ($49)، أو إرشاد كامل ($99).</li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
