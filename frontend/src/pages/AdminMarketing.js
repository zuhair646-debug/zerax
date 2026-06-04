import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import {
  Send, Mail, MessageCircle, Twitter, Phone, Instagram,
  Sparkles, Image as ImageIcon, Loader2, CheckCircle2, XCircle,
  Clock, Trash2, Eye, Play, Pause, RefreshCw, AlertCircle, Copy,
  TrendingUp, BarChart3, Users, FileText,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const CHANNEL_ICONS = {
  telegram: Send, discord: MessageCircle, email: Mail,
  twitter: Twitter, whatsapp: Phone, instagram: Instagram,
};

const PLATFORMS = [
  { id: 'twitter', label: 'Twitter / X' },
  { id: 'telegram', label: 'Telegram' },
  { id: 'instagram', label: 'Instagram' },
  { id: 'discord', label: 'Discord' },
  { id: 'email', label: 'Email' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'tiktok', label: 'TikTok' },
  { id: 'linkedin', label: 'LinkedIn' },
];

export default function AdminMarketing({ user }) {
  const navigate = useNavigate();
  const [tab, setTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [posts, setPosts] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState({
    persona_id: 'devs', platform: 'twitter', topic_hint: '', generate_image: true,
  });
  const [scheduler, setScheduler] = useState({
    enabled: false, interval_minutes: 60,
    channels: ['telegram'], auto_approve: false,
  });

  const token = localStorage.getItem('token');

  const loadOverview = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/marketing/overview`, { headers: { Authorization: `Bearer ${token}` } });
      const d = await r.json();
      setOverview(d);
      if (d?.scheduler) {
        setScheduler((s) => ({ ...s, ...d.scheduler, enabled: d.scheduler.running }));
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [token]);

  const loadPosts = useCallback(async (status) => {
    try {
      const url = status ? `${API}/api/marketing/posts?status=${status}` : `${API}/api/marketing/posts`;
      const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      const d = await r.json();
      setPosts(d.posts || []);
    } catch (e) { console.error(e); }
  }, [token]);

  useEffect(() => {
    loadOverview();
    loadPosts();
  }, [loadOverview, loadPosts]);

  const generateOne = async () => {
    setGenerating(true);
    try {
      const r = await fetch(`${API}/api/marketing/generate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const d = await r.json();
      if (r.ok && d.post) {
        toast.success(`✨ تم توليد منشور لـ ${d.post.persona_name}`);
        loadPosts();
        loadOverview();
      } else {
        toast.error(d.detail || 'فشل التوليد');
      }
    } catch (e) { toast.error('خطأ: ' + e.message); }
    finally { setGenerating(false); }
  };

  const generateBatch = async () => {
    setGenerating(true);
    try {
      const r = await fetch(`${API}/api/marketing/generate-batch`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: 5 }),
      });
      const d = await r.json();
      if (r.ok) {
        toast.success(`✨ تم توليد ${d.saved} منشورات`);
        loadPosts();
        loadOverview();
      } else { toast.error(d.detail || 'فشل'); }
    } catch (e) { toast.error('خطأ: ' + e.message); }
    finally { setGenerating(false); }
  };

  const approvePost = async (id) => {
    await fetch(`${API}/api/marketing/posts/${id}/approve`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
    toast.success('تمت الموافقة');
    loadPosts(); loadOverview();
  };
  const rejectPost = async (id) => {
    await fetch(`${API}/api/marketing/posts/${id}/reject`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
    toast.success('تم الرفض');
    loadPosts(); loadOverview();
  };
  const deletePost = async (id) => {
    if (!window.confirm('حذف؟')) return;
    await fetch(`${API}/api/marketing/posts/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
    toast.success('تم الحذف');
    loadPosts(); loadOverview();
  };
  const publishPost = async (id, channels) => {
    const r = await fetch(`${API}/api/marketing/posts/${id}/publish`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ channels }),
    });
    const d = await r.json();
    const ok = d.results?.filter(x => x.ok).length || 0;
    const fail = d.results?.filter(x => !x.ok).length || 0;
    if (ok > 0) toast.success(`✅ نُشر في ${ok} قناة`);
    if (fail > 0) toast.error(`❌ ${fail} قناة فشلت`);
    loadPosts(); loadOverview();
  };

  const saveSchedule = async () => {
    const r = await fetch(`${API}/api/marketing/schedule`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: scheduler.enabled,
        interval_minutes: scheduler.interval_minutes,
        channels: scheduler.channels,
        auto_approve: scheduler.auto_approve,
      }),
    });
    if (r.ok) toast.success(scheduler.enabled ? '🚀 الطيار الآلي يعمل' : '⏸️ تم الإيقاف');
    loadOverview();
  };

  if (loading) return (
    <div className="min-h-screen bg-[#0a0a12] flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-amber-400" />
    </div>
  );

  const stats = overview || {};
  const channelStatus = stats.channels || {};
  const personas = stats.personas || [];

  return (
    <div className="min-h-screen bg-[#0a0a12]" dir="rtl">
      <Navbar user={user} />
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-black text-amber-300 flex items-center gap-2">
              <Sparkles className="w-7 h-7" /> مركز التسويق الذكي
            </h1>
            <p className="text-sm text-white/55 mt-1">
              ذكاء يولّد، يجدول، وينشر المحتوى تلقائياً عبر 6 منصات
            </p>
          </div>
          <Button onClick={() => navigate('/admin')} variant="outline" data-testid="back-to-admin">
            ← لوحة التحكم
          </Button>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1.5 mb-6 border-b border-white/10 overflow-x-auto">
          {[
            { id: 'overview', label: 'نظرة عامة', icon: BarChart3 },
            { id: 'generate', label: 'توليد محتوى', icon: Sparkles },
            { id: 'queue', label: 'قائمة المنشورات', icon: FileText },
            { id: 'channels', label: 'القنوات', icon: Send },
            { id: 'schedule', label: 'الطيار الآلي', icon: Clock },
          ].map((t) => {
            const Icon = t.icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => { setTab(t.id); if (t.id === 'queue') loadPosts(); }}
                data-testid={`mkt-tab-${t.id}`}
                className={`px-4 py-2.5 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${
                  active ? 'text-amber-300 border-amber-400' : 'text-white/55 border-transparent hover:text-white/80'
                }`}
              >
                <Icon className="w-4 h-4" />{t.label}
              </button>
            );
          })}
        </div>

        {/* ─── OVERVIEW TAB ─── */}
        {tab === 'overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <StatCard label="إجمالي المنشورات" value={stats.total_posts || 0} icon={FileText} color="amber" />
              <StatCard label="منشورة" value={stats.by_status?.published || 0} icon={CheckCircle2} color="emerald" />
              <StatCard label="مسودات" value={stats.by_status?.draft || 0} icon={Clock} color="cyan" />
              <StatCard label="مجدولة" value={stats.by_status?.scheduled || 0} icon={Clock} color="violet" />
              <StatCard label="مرفوضة" value={stats.by_status?.rejected || 0} icon={XCircle} color="rose" />
            </div>

            <Card className="bg-zinc-950/60 border-white/10">
              <CardContent className="p-5">
                <h3 className="text-sm font-bold text-amber-300 mb-3 flex items-center gap-2">
                  <Users className="w-4 h-4" />الجمهور المستهدف (5 شخصيات)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                  {personas.map((p) => (
                    <div key={p.id} className="p-3 rounded-lg bg-black/40 border border-white/8">
                      <div className="text-2xl mb-1">{p.emoji}</div>
                      <div className="text-sm font-bold text-white">{p.name}</div>
                      <div className="text-[10px] text-white/50 mt-1 leading-relaxed line-clamp-3">{p.description}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-zinc-950/60 border-white/10">
              <CardContent className="p-5">
                <h3 className="text-sm font-bold text-amber-300 mb-3">حالة القنوات</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {Object.entries(channelStatus).map(([key, c]) => {
                    const Icon = CHANNEL_ICONS[key] || Send;
                    return (
                      <div key={key} className="flex items-center justify-between p-2.5 rounded-lg bg-black/40 border border-white/8">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <Icon className="w-4 h-4 flex-shrink-0" style={{ color: c.color }} />
                          <div className="min-w-0">
                            <div className="text-xs font-bold text-white truncate">{c.label}</div>
                            <div className="text-[10px] text-white/45 truncate">{c.cost}</div>
                          </div>
                        </div>
                        {c.configured
                          ? <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                          : <XCircle className="w-4 h-4 text-white/30 flex-shrink-0" />}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {stats.recent?.length > 0 && (
              <div>
                <h3 className="text-sm font-bold text-amber-300 mb-2">آخر المنشورات</h3>
                <div className="space-y-2">
                  {stats.recent.slice(0, 5).map((p) => <PostCard key={p.id} post={p} compact />)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ─── GENERATE TAB ─── */}
        {tab === 'generate' && (
          <Card className="bg-zinc-950/60 border-white/10">
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-bold text-amber-300 mb-1.5 block">الجمهور المستهدف</label>
                  <select
                    value={form.persona_id}
                    onChange={(e) => setForm({ ...form, persona_id: e.target.value })}
                    data-testid="form-persona"
                    className="w-full bg-black/40 border border-white/15 rounded-lg px-3 py-2 text-sm text-white focus:border-amber-400 outline-none"
                  >
                    {personas.map((p) => <option key={p.id} value={p.id}>{p.emoji} {p.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold text-amber-300 mb-1.5 block">المنصة</label>
                  <select
                    value={form.platform}
                    onChange={(e) => setForm({ ...form, platform: e.target.value })}
                    data-testid="form-platform"
                    className="w-full bg-black/40 border border-white/15 rounded-lg px-3 py-2 text-sm text-white focus:border-amber-400 outline-none"
                  >
                    {PLATFORMS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold text-amber-300 mb-1.5 block">توليد صورة؟</label>
                  <div className="flex items-center gap-2 h-10">
                    <Switch
                      checked={form.generate_image}
                      onCheckedChange={(v) => setForm({ ...form, generate_image: v })}
                      data-testid="form-image-toggle"
                    />
                    <span className="text-xs text-white/65">{form.generate_image ? 'نعم (Nano Banana)' : 'لا'}</span>
                  </div>
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-amber-300 mb-1.5 block">تلميح موضوع (اختياري)</label>
                <Input
                  value={form.topic_hint}
                  onChange={(e) => setForm({ ...form, topic_hint: e.target.value })}
                  placeholder="مثال: ميزة جديدة، عرض خاص، قصة عميل..."
                  data-testid="form-topic"
                  className="bg-black/40 border-white/15"
                />
              </div>

              <div className="flex items-center gap-2">
                <Button
                  onClick={generateOne}
                  disabled={generating}
                  data-testid="btn-generate"
                  className="bg-gradient-to-r from-amber-500 to-yellow-500 text-black font-black"
                >
                  {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  ولّد منشور واحد
                </Button>
                <Button
                  onClick={generateBatch}
                  disabled={generating}
                  data-testid="btn-generate-batch"
                  variant="outline"
                  className="border-amber-400/30 text-amber-300"
                >
                  ولّد 5 منشورات (تنويع)
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* ─── QUEUE TAB ─── */}
        {tab === 'queue' && (
          <div>
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              {['', 'draft', 'scheduled', 'published', 'rejected', 'failed'].map((s) => (
                <button
                  key={s || 'all'}
                  onClick={() => loadPosts(s || null)}
                  className="px-3 py-1.5 text-xs rounded-md bg-zinc-900 hover:bg-zinc-800 border border-white/8 text-white/75 hover:text-white"
                >
                  {s === '' ? 'الكل' : s === 'draft' ? 'مسودات' : s === 'scheduled' ? 'مجدولة' : s === 'published' ? 'منشورة' : s === 'rejected' ? 'مرفوضة' : 'فشلت'}
                </button>
              ))}
              <Button size="sm" onClick={() => loadPosts()} variant="ghost" className="text-white/55">
                <RefreshCw className="w-3.5 h-3.5" />
              </Button>
            </div>
            <div className="space-y-3">
              {posts.length === 0 && (
                <div className="text-center py-12 text-white/40 text-sm">
                  لا توجد منشورات بعد. اذهب إلى تبويب "توليد محتوى" لتبدأ.
                </div>
              )}
              {posts.map((p) => (
                <PostCard
                  key={p.id}
                  post={p}
                  channelStatus={channelStatus}
                  onApprove={() => approvePost(p.id)}
                  onReject={() => rejectPost(p.id)}
                  onDelete={() => deletePost(p.id)}
                  onPublish={(channels) => publishPost(p.id, channels)}
                />
              ))}
            </div>
          </div>
        )}

        {/* ─── CHANNELS TAB ─── */}
        {tab === 'channels' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(channelStatus).map(([key, c]) => {
              const Icon = CHANNEL_ICONS[key] || Send;
              return (
                <Card key={key} className="bg-zinc-950/60 border-white/10">
                  <CardContent className="p-5">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-11 h-11 rounded-xl flex items-center justify-center"
                           style={{ background: `${c.color}25`, border: `1px solid ${c.color}50` }}>
                        <Icon className="w-5 h-5" style={{ color: c.color }} />
                      </div>
                      <div className="flex-1">
                        <div className="text-base font-bold text-white">{c.label}</div>
                        <div className="text-[11px] text-white/55">{c.cost}</div>
                      </div>
                      {c.configured
                        ? <span className="text-[10px] font-black px-2 py-1 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-400/30">متصل</span>
                        : <span className="text-[10px] font-black px-2 py-1 rounded bg-white/5 text-white/45 border border-white/10">غير متصل</span>}
                    </div>
                    {!c.configured && (
                      <div className="bg-amber-500/5 border border-amber-400/20 rounded-lg p-3 mt-2">
                        <div className="text-[11px] font-bold text-amber-300 mb-1.5 flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5" />خطوات الربط:
                        </div>
                        <ol className="text-[11px] text-white/70 space-y-1 list-decimal list-inside">
                          {(c.setup_steps || []).map((s, i) => <li key={i}>{s}</li>)}
                        </ol>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* ─── SCHEDULE TAB ─── */}
        {tab === 'schedule' && (
          <Card className="bg-zinc-950/60 border-white/10">
            <CardContent className="p-6 space-y-5">
              <div className="flex items-center justify-between p-4 rounded-xl bg-gradient-to-l from-amber-500/10 to-transparent border border-amber-400/30">
                <div>
                  <div className="text-base font-black text-amber-300 flex items-center gap-2">
                    {scheduler.enabled ? <Play className="w-5 h-5" /> : <Pause className="w-5 h-5" />}
                    الطيار الآلي
                  </div>
                  <div className="text-xs text-white/60 mt-1">
                    {scheduler.enabled
                      ? `يعمل · كل ${scheduler.interval_minutes} دقيقة`
                      : 'متوقّف — شغّله ليولّد وينشر تلقائياً'}
                  </div>
                </div>
                <Switch
                  checked={scheduler.enabled}
                  onCheckedChange={(v) => setScheduler({ ...scheduler, enabled: v })}
                  data-testid="scheduler-toggle"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-amber-300 mb-1.5 block">
                  الفترة بين كل منشور (دقيقة) — {scheduler.interval_minutes}
                </label>
                <input
                  type="range"
                  min={15} max={1440} step={15}
                  value={scheduler.interval_minutes}
                  onChange={(e) => setScheduler({ ...scheduler, interval_minutes: +e.target.value })}
                  className="w-full accent-amber-400"
                  data-testid="scheduler-interval"
                />
                <div className="flex justify-between text-[10px] text-white/40 mt-1">
                  <span>15 دقيقة</span><span>ساعة</span><span>6 ساعات</span><span>يوم</span>
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-amber-300 mb-2 block">القنوات المُختارة</label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {Object.entries(channelStatus).map(([key, c]) => {
                    const Icon = CHANNEL_ICONS[key] || Send;
                    const sel = scheduler.channels.includes(key);
                    return (
                      <button
                        key={key}
                        onClick={() => {
                          const next = sel ? scheduler.channels.filter(x => x !== key) : [...scheduler.channels, key];
                          setScheduler({ ...scheduler, channels: next });
                        }}
                        disabled={!c.configured}
                        className={`flex items-center gap-2 p-2.5 rounded-lg border text-xs transition ${
                          sel ? 'border-amber-400 bg-amber-400/10' : 'border-white/8 bg-black/30 opacity-60'
                        } ${!c.configured ? 'cursor-not-allowed opacity-30' : 'hover:border-amber-400/50'}`}
                      >
                        <Icon className="w-4 h-4" style={{ color: c.color }} />
                        <span className="font-bold text-white">{c.label}</span>
                        {!c.configured && <span className="text-[9px] text-white/40 mr-auto">غير متصل</span>}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-black/40 border border-white/8">
                <div>
                  <div className="text-xs font-bold text-white">نشر تلقائي بدون موافقة؟</div>
                  <div className="text-[10px] text-white/45 mt-0.5">
                    ينشر مباشرة بدون مراجعة (انتبه: محتوى AI قد يحتاج تدقيق)
                  </div>
                </div>
                <Switch
                  checked={scheduler.auto_approve}
                  onCheckedChange={(v) => setScheduler({ ...scheduler, auto_approve: v })}
                  data-testid="scheduler-auto-approve"
                />
              </div>

              <Button onClick={saveSchedule} data-testid="scheduler-save" className="w-full bg-amber-500 text-black font-black">
                حفظ الإعدادات
              </Button>

              {scheduler.last_run && (
                <div className="text-[11px] text-white/55 pt-2 border-t border-white/8">
                  آخر تشغيل: {new Date(scheduler.last_run).toLocaleString('ar-SA')}
                  {scheduler.next_run && <span> · التالي: {new Date(scheduler.next_run).toLocaleString('ar-SA')}</span>}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────
function StatCard({ label, value, icon: Icon, color = 'amber' }) {
  const map = {
    amber: 'from-amber-500/15 to-yellow-500/5 border-amber-400/25 text-amber-300',
    emerald: 'from-emerald-500/15 to-teal-500/5 border-emerald-400/25 text-emerald-300',
    cyan: 'from-cyan-500/15 to-blue-500/5 border-cyan-400/25 text-cyan-300',
    violet: 'from-violet-500/15 to-purple-500/5 border-violet-400/25 text-violet-300',
    rose: 'from-rose-500/15 to-pink-500/5 border-rose-400/25 text-rose-300',
  };
  return (
    <div className={`p-3 rounded-xl bg-gradient-to-br ${map[color]} border`}>
      <Icon className="w-4 h-4 mb-1.5 opacity-70" />
      <div className="text-2xl font-black text-white">{value}</div>
      <div className="text-[10px] text-white/55 mt-0.5">{label}</div>
    </div>
  );
}

function PostCard({ post, compact = false, channelStatus = {}, onApprove, onReject, onDelete, onPublish }) {
  const [showPublish, setShowPublish] = useState(false);
  const [selectedChannels, setSelectedChannels] = useState([]);

  const statusColor = {
    draft: 'bg-white/10 text-white/70',
    scheduled: 'bg-violet-500/15 text-violet-300',
    published: 'bg-emerald-500/15 text-emerald-300',
    rejected: 'bg-rose-500/15 text-rose-300',
    failed: 'bg-orange-500/15 text-orange-300',
  };
  const statusLabel = { draft: 'مسودة', scheduled: 'مجدولة', published: 'منشور', rejected: 'مرفوض', failed: 'فشل' };
  const PI = CHANNEL_ICONS[post.platform] || Send;

  return (
    <Card className="bg-zinc-950/60 border-white/10">
      <CardContent className={`p-4 ${compact ? 'space-y-2' : 'space-y-3'}`}>
        <div className="flex items-start gap-3">
          {post.image_url && (
            <img src={post.image_url} alt="" className="w-14 h-14 rounded-lg object-cover flex-shrink-0" />
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${statusColor[post.status] || 'bg-white/10'}`}>
                {statusLabel[post.status] || post.status}
              </span>
              <PI className="w-3 h-3 text-white/55" />
              <span className="text-[10px] text-white/55">{post.persona_name} · {post.bucket_name}</span>
            </div>
            <div className="text-xs text-white/85 whitespace-pre-wrap leading-relaxed line-clamp-4">{post.text}</div>
            {post.topic && <div className="text-[10px] text-amber-300/70 mt-1">📌 {post.topic}</div>}
          </div>
        </div>

        {!compact && (
          <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-white/8">
            <button onClick={() => navigator.clipboard.writeText(post.text) && toast.success('تم النسخ')}
                    className="text-[11px] px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-white/70 flex items-center gap-1">
              <Copy className="w-3 h-3" />نسخ
            </button>
            {post.status === 'draft' && onApprove && (
              <button onClick={onApprove} className="text-[11px] px-2 py-1 rounded bg-violet-500/15 hover:bg-violet-500/25 text-violet-300 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />موافقة
              </button>
            )}
            {(post.status === 'draft' || post.status === 'scheduled') && onPublish && (
              <button onClick={() => setShowPublish(!showPublish)} className="text-[11px] px-2 py-1 rounded bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 flex items-center gap-1">
                <Send className="w-3 h-3" />نشر الآن
              </button>
            )}
            {post.status !== 'rejected' && onReject && (
              <button onClick={onReject} className="text-[11px] px-2 py-1 rounded bg-white/5 hover:bg-rose-500/15 text-white/60 hover:text-rose-300">
                رفض
              </button>
            )}
            {onDelete && (
              <button onClick={onDelete} className="text-[11px] px-2 py-1 rounded bg-white/5 hover:bg-rose-500/15 text-white/40 hover:text-rose-300 mr-auto">
                <Trash2 className="w-3 h-3" />
              </button>
            )}
          </div>
        )}

        {showPublish && (
          <div className="p-3 rounded-lg bg-black/40 border border-amber-400/30 space-y-2">
            <div className="text-[11px] font-bold text-amber-300">اختر القنوات للنشر:</div>
            <div className="grid grid-cols-2 gap-1.5">
              {Object.entries(channelStatus).filter(([_, c]) => c.configured).map(([key, c]) => {
                const Icon = CHANNEL_ICONS[key] || Send;
                const sel = selectedChannels.includes(key);
                return (
                  <button key={key} onClick={() => {
                    setSelectedChannels(sel ? selectedChannels.filter(x => x !== key) : [...selectedChannels, key]);
                  }} className={`flex items-center gap-2 p-2 rounded text-[11px] border ${
                    sel ? 'border-amber-400 bg-amber-400/10' : 'border-white/8'
                  }`}>
                    <Icon className="w-3.5 h-3.5" style={{ color: c.color }} />
                    {c.label}
                  </button>
                );
              })}
            </div>
            {Object.values(channelStatus).every(c => !c.configured) && (
              <div className="text-[11px] text-amber-300 text-center py-2">
                لا توجد قنوات مربوطة بعد. اربط قناة من تبويب "القنوات".
              </div>
            )}
            <div className="flex items-center gap-2">
              <Button size="sm" onClick={() => { onPublish(selectedChannels); setShowPublish(false); }}
                      disabled={selectedChannels.length === 0}
                      className="bg-amber-500 text-black text-[11px] h-7">
                انشر في {selectedChannels.length} قناة
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setShowPublish(false)} className="text-white/55 text-[11px] h-7">إلغاء</Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
