import React, { useState, useEffect, useMemo } from 'react';
import { Navbar } from '@/components/Navbar';
import { toast } from 'sonner';
import {
  Users, Search, ChevronLeft, Crown, DollarSign, Activity,
  MessageSquare, Globe, Image as ImageIcon, Video, CreditCard,
  Sparkles, ShieldCheck, Loader2, Eye, MapPin, Calendar, Layers,
  TrendingUp, AlertTriangle, Target, Zap,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function api(path, opts = {}) {
  const token = localStorage.getItem('token');
  return fetch(`${API}${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  });
}

const TabBtn = ({ active, icon: Icon, label, count, onClick, testid }) => (
  <button
    type="button"
    onClick={onClick}
    data-testid={testid}
    className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-bold transition-all ${
      active
        ? 'bg-amber-500/15 border border-amber-400/40 text-amber-200'
        : 'border border-transparent text-zinc-400 hover:text-white hover:bg-zinc-800/60'
    }`}
  >
    <Icon className="w-4 h-4" />
    <span>{label}</span>
    {count != null && (
      <span className="ms-1 px-1.5 rounded bg-zinc-800/80 text-[10px]" data-no-translate="true">{count}</span>
    )}
  </button>
);

const StatCard = ({ label, value, sub, icon: Icon, accent = 'amber' }) => (
  <div className={`bg-zinc-900/60 border border-zinc-800 rounded-xl p-4`}>
    <div className="flex items-center justify-between mb-2">
      <span className="text-zinc-500 text-xs font-bold">{label}</span>
      <Icon className={`w-4 h-4 text-${accent}-400`} />
    </div>
    <div className="text-2xl font-black text-white" data-no-translate="true">{value}</div>
    {sub && <div className="text-[11px] text-zinc-500 mt-1">{sub}</div>}
  </div>
);

export default function ClientIntelligence({ user }) {
  const [clients, setClients] = useState([]);
  const [total, setTotal] = useState(0);
  const [loadingList, setLoadingList] = useState(true);
  const [q, setQ] = useState('');
  const [sortBy, setSortBy] = useState('last_active');
  const [selected, setSelected] = useState(null);
  const [profile, setProfile] = useState(null);
  const [tab, setTab] = useState('overview');
  const [tabData, setTabData] = useState({});
  const [loadingTab, setLoadingTab] = useState(false);
  const [insights, setInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);

  // ----- list -----
  const loadClients = async () => {
    setLoadingList(true);
    try {
      const r = await api(`/api/admin/intelligence/clients?q=${encodeURIComponent(q)}&sort_by=${sortBy}&limit=100`);
      if (!r.ok) {
        if (r.status === 403) toast.error('هذه الصفحة للأدمن فقط');
        return;
      }
      const d = await r.json();
      setClients(d.items || []);
      setTotal(d.total || 0);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => { loadClients(); /* eslint-disable-next-line */ }, [sortBy]);

  // ----- selected profile -----
  const loadProfile = async (uid) => {
    setProfile(null);
    setTabData({});
    setInsights(null);
    setTab('overview');
    const r = await api(`/api/admin/intelligence/clients/${uid}/360`);
    if (r.ok) setProfile(await r.json());
  };

  const loadTabData = async (which) => {
    if (!selected) return;
    if (tabData[which]) return;
    setLoadingTab(true);
    try {
      const path = {
        conversations: 'conversations',
        projects: 'projects',
        media: 'media',
        payments: 'payments',
        sessions: 'sessions',
      }[which];
      if (!path) return;
      const r = await api(`/api/admin/intelligence/clients/${selected}/${path}`);
      if (r.ok) {
        const d = await r.json();
        setTabData((t) => ({ ...t, [which]: d }));
      }
    } finally {
      setLoadingTab(false);
    }
  };

  const generateInsights = async () => {
    if (!selected) return;
    setInsightsLoading(true);
    try {
      const r = await api(`/api/admin/intelligence/clients/${selected}/ai-insights`, { method: 'POST' });
      if (r.ok) {
        const d = await r.json();
        setInsights(d.report);
        toast.success('تم توليد تقرير الذكاء الاصطناعي');
      } else {
        const err = await r.json().catch(() => ({}));
        toast.error(err.detail || 'تعذّر التوليد');
      }
    } finally {
      setInsightsLoading(false);
    }
  };

  // ----- handlers -----
  useEffect(() => {
    if (selected) loadProfile(selected);
  }, [selected]);

  useEffect(() => {
    if (selected && tab !== 'overview' && tab !== 'insights') loadTabData(tab);
    // eslint-disable-next-line
  }, [tab, selected]);

  const filtered = useMemo(() => {
    if (!q.trim()) return clients;
    const x = q.trim().toLowerCase();
    return clients.filter((c) =>
      (c.email || '').toLowerCase().includes(x) ||
      (c.name || '').toLowerCase().includes(x)
    );
  }, [clients, q]);

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'owner' || user?.is_owner;
  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
        <div className="text-center">
          <ShieldCheck className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <div className="text-lg font-bold">هذه الصفحة للأدمن فقط</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white" style={{ paddingTop: 0 }}>
      <Navbar user={user} />
      <div className="pt-24 pb-12 px-4 max-w-[1400px] mx-auto">
        <div className="mb-6 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-zinc-950" />
          </div>
          <div>
            <h1 className="text-2xl font-black">مركز ذكاء العملاء</h1>
            <p className="text-zinc-500 text-sm">عرض 360° لكل عميل · للقراءة فقط · مع تحليل الذكاء الاصطناعي</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[340px,1fr] gap-5">
          {/* Sidebar: clients list */}
          <aside className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-3 flex flex-col h-[calc(100vh-180px)]">
            <div className="relative mb-2">
              <Search className="w-4 h-4 absolute top-2.5 right-3 text-zinc-500" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadClients()}
                data-testid="intel-search"
                placeholder="ابحث بالبريد أو الاسم..."
                className="w-full bg-black/40 border border-zinc-800 rounded-lg pe-9 ps-3 py-2 text-sm focus:border-amber-500 outline-none"
              />
            </div>
            <div className="flex gap-1 mb-2 text-[11px]">
              {[
                ['last_active', 'الأحدث نشاطاً'],
                ['total_spent', 'الأعلى صرفاً'],
                ['created_at', 'الأحدث تسجيلاً'],
              ].map(([k, l]) => (
                <button
                  key={k}
                  onClick={() => setSortBy(k)}
                  data-testid={`sort-${k}`}
                  className={`flex-1 px-2 py-1 rounded ${sortBy === k ? 'bg-amber-500/20 text-amber-200 border border-amber-400/30' : 'border border-zinc-800 text-zinc-400'}`}
                >
                  {l}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto -mx-1 px-1 space-y-1.5">
              {loadingList ? (
                <div className="text-center text-zinc-500 py-8"><Loader2 className="w-5 h-5 animate-spin mx-auto" /></div>
              ) : filtered.length === 0 ? (
                <div className="text-center text-zinc-500 py-8">لا يوجد عملاء مطابقون</div>
              ) : filtered.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setSelected(c.id)}
                  data-testid={`client-${c.id}`}
                  className={`w-full text-right p-3 rounded-lg border transition-all ${
                    selected === c.id
                      ? 'bg-amber-500/10 border-amber-400/50'
                      : 'bg-zinc-950/40 border-zinc-800 hover:border-zinc-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-sm truncate max-w-[200px]">{c.name || c.email}</span>
                    {c.total_spent_usd > 0 && (
                      <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 rounded" data-no-translate="true">
                        ${c.total_spent_usd}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-zinc-500 truncate">{c.email}</div>
                  <div className="flex flex-wrap gap-1 mt-2 text-[10px]">
                    {c.counts.websites > 0 && <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300" data-no-translate="true">🌐 {c.counts.websites}</span>}
                    {c.counts.games > 0 && <span className="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300" data-no-translate="true">🎮 {c.counts.games}</span>}
                    {c.counts.images > 0 && <span className="px-1.5 py-0.5 rounded bg-pink-500/10 text-pink-300" data-no-translate="true">🖼 {c.counts.images}</span>}
                    {c.counts.videos > 0 && <span className="px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-300" data-no-translate="true">🎬 {c.counts.videos}</span>}
                  </div>
                </button>
              ))}
            </div>
            <div className="text-[10px] text-zinc-600 text-center mt-2 pt-2 border-t border-zinc-800">
              المجموع: <span data-no-translate="true">{total}</span> عميل
            </div>
          </aside>

          {/* Main: profile */}
          <main className="bg-zinc-900/40 border border-zinc-800 rounded-2xl min-h-[calc(100vh-180px)]">
            {!selected ? (
              <div className="h-full flex flex-col items-center justify-center text-zinc-500 p-12 text-center">
                <Users className="w-12 h-12 mb-4 text-zinc-700" />
                <div className="text-lg">اختر عميلاً من القائمة لعرض التقرير الكامل</div>
                <div className="text-xs mt-2">تقرير 360° يشمل: المحادثات، المواقع، الصور، الفيديوهات، المدفوعات، النشاط، وتحليل الذكاء الاصطناعي</div>
              </div>
            ) : !profile ? (
              <div className="h-full flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-zinc-600" /></div>
            ) : (
              <div className="p-5">
                {/* Header card */}
                <div className="bg-gradient-to-br from-zinc-900 to-zinc-950 border border-zinc-800 rounded-2xl p-5 mb-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-2xl font-black flex items-center gap-2">
                        {profile.user.name || profile.user.email}
                        {profile.user.role && profile.user.role !== 'user' && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 uppercase">{profile.user.role}</span>
                        )}
                      </h2>
                      <div className="text-zinc-500 text-sm" data-no-translate="true">{profile.user.email}</div>
                      <div className="flex items-center gap-3 text-xs text-zinc-400 mt-2">
                        {profile.user.country && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> <span data-no-translate="true">{profile.user.country}</span></span>}
                        <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> منذ <span data-no-translate="true">{(profile.user.created_at || '').slice(0,10)}</span></span>
                        <span className="flex items-center gap-1"><Crown className="w-3 h-3" /> <span data-no-translate="true">{profile.user.plan}</span></span>
                      </div>
                    </div>
                    <div className="text-end">
                      <div className="text-3xl font-black text-amber-400" data-no-translate="true">${profile.spend.total_usd}</div>
                      <div className="text-[10px] text-zinc-500">إجمالي المدفوع · <span data-no-translate="true">{profile.spend.orders_completed}</span> طلب</div>
                      <div className="mt-2 inline-flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-full">
                        <Activity className="w-3 h-3" /> Engagement: <span data-no-translate="true">{profile.engagement_score}/100</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Tabs */}
                <div className="flex flex-wrap gap-2 mb-5 border-b border-zinc-800 pb-3">
                  <TabBtn active={tab === 'overview'} icon={Eye} label="نظرة عامة" onClick={() => setTab('overview')} testid="tab-overview" />
                  <TabBtn active={tab === 'conversations'} icon={MessageSquare} label="المحادثات" count={profile.counts.chats + profile.counts.freebuild_sessions} onClick={() => setTab('conversations')} testid="tab-conv" />
                  <TabBtn active={tab === 'projects'} icon={Globe} label="المشاريع" count={profile.counts.websites + profile.counts.games} onClick={() => setTab('projects')} testid="tab-proj" />
                  <TabBtn active={tab === 'media'} icon={ImageIcon} label="الوسائط" count={profile.counts.images + profile.counts.videos} onClick={() => setTab('media')} testid="tab-media" />
                  <TabBtn active={tab === 'payments'} icon={CreditCard} label="المدفوعات" count={profile.spend.orders_completed} onClick={() => setTab('payments')} testid="tab-pay" />
                  <TabBtn active={tab === 'sessions'} icon={Activity} label="النشاط" count={profile.activity.total_actions_30d} onClick={() => setTab('sessions')} testid="tab-sess" />
                  <TabBtn active={tab === 'insights'} icon={Sparkles} label="تحليل AI" onClick={() => setTab('insights')} testid="tab-ai" />
                </div>

                {/* Tab content */}
                <div className="min-h-[400px]">
                  {tab === 'overview' && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <StatCard label="مواقع" value={profile.counts.websites} icon={Globe} accent="blue" />
                      <StatCard label="ألعاب" value={profile.counts.games} icon={Layers} accent="purple" />
                      <StatCard label="صور" value={profile.counts.images} icon={ImageIcon} accent="pink" />
                      <StatCard label="فيديوهات" value={profile.counts.videos} icon={Video} accent="orange" />
                      <StatCard label="محادثات" value={profile.counts.chats} icon={MessageSquare} accent="emerald" />
                      <StatCard label="جلسات FreeBuild" value={profile.counts.freebuild_sessions} icon={Sparkles} accent="amber" />
                      <StatCard label="نشاط 30 يوم" value={profile.activity.total_actions_30d} sub={`${profile.activity.unique_ips} IP فريد`} icon={Activity} accent="cyan" />
                      <StatCard label="رصيد الشعلات" value={profile.user.credits} icon={Zap} accent="yellow" />
                    </div>
                  )}

                  {tab === 'conversations' && (
                    loadingTab ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> :
                    <div className="space-y-3" data-testid="conv-list">
                      {(tabData.conversations?.items || []).map((s, i) => (
                        <div key={i} className="bg-zinc-950/50 border border-zinc-800 rounded-xl p-4">
                          <div className="flex justify-between items-start mb-2">
                            <div>
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 uppercase me-2" data-no-translate="true">{s.source}</span>
                              <span className="font-bold">{s.title}</span>
                            </div>
                            <span className="text-[10px] text-zinc-600" data-no-translate="true">{(s.updated_at || '').slice(0,16)}</span>
                          </div>
                          <div className="text-[10px] text-zinc-500 mb-2"><span data-no-translate="true">{s.message_count}</span> رسالة</div>
                          <div className="space-y-1.5 max-h-72 overflow-y-auto bg-black/30 p-2 rounded">
                            {(s.messages || []).slice(-12).map((m, j) => (
                              <div key={j} className={`text-xs p-2 rounded ${m.role === 'user' ? 'bg-amber-500/5 border-r-2 border-amber-400/40' : 'bg-blue-500/5 border-r-2 border-blue-400/40'}`}>
                                <span className="text-[9px] text-zinc-500 me-2" data-no-translate="true">[{m.role}]</span>
                                <span className="text-zinc-300">{m.content}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                      {(tabData.conversations?.items || []).length === 0 && <div className="text-zinc-500 text-center py-8">لا توجد محادثات</div>}
                    </div>
                  )}

                  {tab === 'projects' && (
                    loadingTab ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> :
                    <div className="space-y-5" data-testid="proj-list">
                      {tabData.projects?.websites?.length > 0 && (
                        <div>
                          <h4 className="text-sm font-bold text-blue-300 mb-2">🌐 المواقع (<span data-no-translate="true">{tabData.projects.websites.length}</span>)</h4>
                          <div className="grid md:grid-cols-2 gap-2">
                            {tabData.projects.websites.map((w) => (
                              <div key={w.id} className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                                <div className="font-bold text-sm">{w.name}</div>
                                <div className="text-[10px] text-zinc-500 flex gap-2 mt-1">
                                  <span data-no-translate="true">v{w.version}</span>
                                  <span data-no-translate="true">{w.html_length} chars</span>
                                  <span data-no-translate="true">{w.credits_spent} 🔥</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {tabData.projects?.games?.length > 0 && (
                        <div>
                          <h4 className="text-sm font-bold text-purple-300 mb-2">🎮 الألعاب (<span data-no-translate="true">{tabData.projects.games.length}</span>)</h4>
                          <div className="grid md:grid-cols-2 gap-2">
                            {tabData.projects.games.map((g) => (
                              <div key={g.id} className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                                <div className="font-bold text-sm">{g.title}</div>
                                <div className="text-[10px] text-zinc-500 flex gap-2 mt-1" data-no-translate="true">{g.game_type} · {g.framework} · {g.phase}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {tabData.projects?.apps?.length > 0 && (
                        <div>
                          <h4 className="text-sm font-bold text-emerald-300 mb-2">📱 التطبيقات (<span data-no-translate="true">{tabData.projects.apps.length}</span>)</h4>
                          <div className="grid md:grid-cols-2 gap-2">
                            {tabData.projects.apps.map((a) => (
                              <div key={a.id} className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                                <div className="font-bold text-sm">{a.name}</div>
                                <div className="text-[10px] text-zinc-500" data-no-translate="true">{a.status}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {(tabData.projects?.total || 0) === 0 && <div className="text-zinc-500 text-center py-8">لا توجد مشاريع</div>}
                    </div>
                  )}

                  {tab === 'media' && (
                    loadingTab ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> :
                    <div className="space-y-5">
                      {tabData.media?.images?.length > 0 && (
                        <div>
                          <h4 className="text-sm font-bold text-pink-300 mb-2">🖼 الصور (<span data-no-translate="true">{tabData.media.images.length}</span>)</h4>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                            {tabData.media.images.slice(0, 24).map((img) => (
                              <div key={img.id} className="aspect-square bg-zinc-950 border border-zinc-800 rounded-lg overflow-hidden">
                                {img.url && <img src={img.url} alt="" className="w-full h-full object-cover" />}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {tabData.media?.videos?.length > 0 && (
                        <div>
                          <h4 className="text-sm font-bold text-orange-300 mb-2">🎬 الفيديوهات (<span data-no-translate="true">{tabData.media.videos.length}</span>)</h4>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            {tabData.media.videos.slice(0, 12).map((v) => (
                              <div key={v.id} className="bg-zinc-950 border border-zinc-800 rounded-lg p-2">
                                {v.url && <video src={v.url} controls className="w-full rounded" />}
                                <div className="text-[10px] text-zinc-500 mt-2 truncate">{v.prompt}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {!tabData.media?.images?.length && !tabData.media?.videos?.length && (
                        <div className="text-zinc-500 text-center py-8">لا توجد وسائط</div>
                      )}
                    </div>
                  )}

                  {tab === 'payments' && (
                    loadingTab ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> :
                    <div className="space-y-2" data-testid="pay-list">
                      {(tabData.payments?.orders || []).map((o) => (
                        <div key={o.id} className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3 flex justify-between items-center">
                          <div>
                            <div className="font-bold text-sm" data-no-translate="true">{o.package}</div>
                            <div className="text-[10px] text-zinc-500" data-no-translate="true">{o.method} · {(o.created_at || '').slice(0,10)}</div>
                          </div>
                          <div className="text-end">
                            <div className="font-bold text-amber-400" data-no-translate="true">${o.amount}</div>
                            <div className={`text-[10px] ${o.status === 'completed' ? 'text-emerald-400' : 'text-zinc-500'}`} data-no-translate="true">{o.status}</div>
                          </div>
                        </div>
                      ))}
                      {(tabData.payments?.orders || []).length === 0 && <div className="text-zinc-500 text-center py-8">لا توجد مدفوعات</div>}
                    </div>
                  )}

                  {tab === 'sessions' && (
                    loadingTab ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> :
                    <div className="space-y-1" data-testid="sess-list">
                      {(tabData.sessions?.events || []).slice(0, 80).map((e, i) => (
                        <div key={i} className="bg-zinc-950/50 border border-zinc-800/50 rounded-lg p-2.5 flex items-center justify-between text-xs">
                          <div>
                            <span className="font-bold" data-no-translate="true">{e.action}</span>
                            <span className="text-zinc-500 mx-2">·</span>
                            <span className="text-zinc-600" data-no-translate="true">{e.type}</span>
                          </div>
                          <div className="text-[10px] text-zinc-500" data-no-translate="true">{(e.at || '').replace('T',' ').slice(0,19)}</div>
                        </div>
                      ))}
                      {(tabData.sessions?.events || []).length === 0 && <div className="text-zinc-500 text-center py-8">لا يوجد نشاط</div>}
                    </div>
                  )}

                  {tab === 'insights' && (
                    <div className="space-y-4" data-testid="ai-insights">
                      {!insights && (
                        <div className="text-center py-8">
                          <Sparkles className="w-10 h-10 text-amber-400 mx-auto mb-3" />
                          <div className="text-lg font-bold mb-2">حلل سلوك العميل بالذكاء الاصطناعي</div>
                          <p className="text-zinc-500 text-sm mb-5 max-w-md mx-auto">
                            سيقرأ Claude كل المحادثات والـ prompts والمدفوعات ويعطي تقريراً يشمل: الاهتمامات، الفئة، نية الشراء، اقتراحات حملات إعلانية موجهة، وأفكار upsell.
                          </p>
                          <button
                            onClick={generateInsights}
                            disabled={insightsLoading}
                            data-testid="generate-insights-btn"
                            className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 text-zinc-950 font-black hover:opacity-90 disabled:opacity-50"
                          >
                            {insightsLoading ? <Loader2 className="w-4 h-4 animate-spin inline me-2" /> : <Sparkles className="w-4 h-4 inline me-2" />}
                            توليد التقرير
                          </button>
                        </div>
                      )}
                      {insights && (
                        <>
                          {insights._parse_error ? (
                            <pre className="text-xs whitespace-pre-wrap bg-zinc-950 p-3 rounded">{insights.raw}</pre>
                          ) : (
                            <div className="space-y-4">
                              {insights.profile_summary && (
                                <div className="bg-amber-500/5 border border-amber-400/30 rounded-xl p-4">
                                  <div className="text-amber-300 font-bold mb-1 flex items-center gap-1"><Eye className="w-4 h-4" /> ملخص الشخصية</div>
                                  <p className="text-sm text-zinc-300">{insights.profile_summary}</p>
                                </div>
                              )}
                              <div className="grid md:grid-cols-3 gap-3">
                                {insights.industry_guess && <StatCard label="القطاع" value={insights.industry_guess} icon={Layers} accent="blue" />}
                                {insights.tone_style && <StatCard label="الأسلوب" value={insights.tone_style} icon={MessageSquare} accent="emerald" />}
                                {insights.buying_intent && <StatCard label="نية الشراء" value={insights.buying_intent} icon={DollarSign} accent="amber" />}
                                {insights.lifecycle_stage && <StatCard label="مرحلة العميل" value={insights.lifecycle_stage} icon={TrendingUp} accent="purple" />}
                                {insights.satisfaction_signal && <StatCard label="مؤشر الرضى" value={insights.satisfaction_signal} icon={Activity} accent="pink" />}
                              </div>
                              {insights.top_interests && insights.top_interests.length > 0 && (
                                <div className="bg-zinc-950/50 border border-zinc-800 rounded-xl p-4">
                                  <div className="text-emerald-300 font-bold mb-2 flex items-center gap-1"><Target className="w-4 h-4" /> الاهتمامات الرئيسية</div>
                                  <div className="flex flex-wrap gap-1.5">
                                    {insights.top_interests.map((t, i) => (
                                      <span key={i} className="text-xs px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-400/20">{t}</span>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {insights.suggested_campaigns && insights.suggested_campaigns.length > 0 && (
                                <div className="bg-zinc-950/50 border border-zinc-800 rounded-xl p-4">
                                  <div className="text-purple-300 font-bold mb-2 flex items-center gap-1"><Sparkles className="w-4 h-4" /> حملات مقترحة</div>
                                  <div className="space-y-2">
                                    {insights.suggested_campaigns.map((c, i) => (
                                      <div key={i} className="bg-purple-500/5 border border-purple-400/20 rounded p-3">
                                        <div className="flex justify-between mb-1">
                                          <span className="font-bold text-sm">{c.title}</span>
                                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 uppercase" data-no-translate="true">{c.channel}</span>
                                        </div>
                                        <p className="text-xs text-zinc-400 mb-1">{c.message}</p>
                                        {c.offer && <p className="text-xs text-amber-300">العرض: {c.offer}</p>}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {insights.upsell_ideas && insights.upsell_ideas.length > 0 && (
                                <div className="bg-zinc-950/50 border border-zinc-800 rounded-xl p-4">
                                  <div className="text-amber-300 font-bold mb-2">💎 أفكار رفع المبيعات</div>
                                  <ul className="space-y-1 text-sm text-zinc-300">
                                    {insights.upsell_ideas.map((u, i) => <li key={i} className="flex gap-2"><span className="text-amber-400">→</span>{u}</li>)}
                                  </ul>
                                </div>
                              )}
                              {insights.risk_flags && insights.risk_flags.length > 0 && (
                                <div className="bg-red-500/5 border border-red-400/30 rounded-xl p-4">
                                  <div className="text-red-300 font-bold mb-2 flex items-center gap-1"><AlertTriangle className="w-4 h-4" /> تنبيهات</div>
                                  <ul className="space-y-1 text-sm text-red-200">
                                    {insights.risk_flags.map((r, i) => <li key={i}>⚠️ {r}</li>)}
                                  </ul>
                                </div>
                              )}
                              {insights.next_best_action && (
                                <div className="bg-emerald-500/5 border border-emerald-400/30 rounded-xl p-4">
                                  <div className="text-emerald-300 font-bold mb-1">🎯 أفضل إجراء قادم</div>
                                  <p className="text-sm text-zinc-300">{insights.next_best_action}</p>
                                </div>
                              )}
                              <div className="flex justify-end">
                                <button
                                  onClick={generateInsights}
                                  disabled={insightsLoading}
                                  className="text-xs text-zinc-500 hover:text-zinc-300"
                                >
                                  {insightsLoading ? '...' : '↻ إعادة التوليد'}
                                </button>
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
