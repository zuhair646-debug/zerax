/**
 * Guardian Dashboard — admin-only live monitor of FreeBuild AI conversations.
 *
 * Shows a card per project with distress level (color-coded), last intervention,
 * recent message preview, and a manual intervention drawer.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Shield, AlertTriangle, Eye, Send, RefreshCw, MessageSquare, Sparkles } from 'lucide-react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const LEVEL_STYLES = {
  ok:        { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', dot: 'bg-emerald-400', label: '🟢 طبيعي' },
  warn:      { bg: 'bg-amber-500/10',   border: 'border-amber-500/30',   dot: 'bg-amber-400',   label: '🟡 إنذار' },
  intervene: { bg: 'bg-orange-500/10',  border: 'border-orange-500/30',  dot: 'bg-orange-400',  label: '🟠 تدخّل' },
  critical:  { bg: 'bg-red-500/10',     border: 'border-red-500/40',     dot: 'bg-red-500 animate-pulse', label: '🔴 حرج' },
};

const LEVEL_ORDER = { critical: 0, intervene: 1, warn: 2, ok: 3 };

export default function GuardianDashboard() {
  const [projects, setProjects] = useState([]);
  const [filter, setFilter] = useState('all'); // all | warn | intervene | critical
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null); // project for detail/inject drawer
  const [detail, setDetail] = useState(null);
  const [injectText, setInjectText] = useState('');
  const [injecting, setInjecting] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const token = useMemo(() => localStorage.getItem('token') || sessionStorage.getItem('token'), []);

  const fetchProjects = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const url = filter === 'all'
        ? `${API}/api/freebuild-chat/admin/guardian/projects`
        : `${API}/api/freebuild-chat/admin/guardian/projects?level=${filter}`;
      const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) {
        if (r.status === 403) toast.error('وصول مرفوض — أنت لست أدمن');
        else toast.error(`خطأ ${r.status}`);
        return;
      }
      const d = await r.json();
      setProjects(d.projects || []);
    } catch (e) {
      toast.error('فشل تحميل المشاريع');
    } finally {
      setLoading(false);
    }
  }, [filter, token]);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  // Auto-refresh every 6 seconds when enabled
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchProjects, 6000);
    return () => clearInterval(id);
  }, [autoRefresh, fetchProjects]);

  const openDetail = useCallback(async (proj) => {
    setSelected(proj);
    setDetail(null);
    try {
      const r = await fetch(`${API}/api/freebuild-chat/admin/guardian/project/${proj.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) setDetail(await r.json());
    } catch (_) { /* ignore */ }
  }, [token]);

  const handleInject = useCallback(async () => {
    if (!selected || !injectText.trim()) return;
    setInjecting(true);
    try {
      const fd = new FormData();
      fd.append('directive', injectText.trim());
      fd.append('diagnosis', 'تدخّل يدوي من الأدمن');
      const r = await fetch(`${API}/api/freebuild-chat/admin/guardian/project/${selected.id}/inject`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (r.ok) {
        toast.success('تم حقن التوجيه — سيُطبَّق في الرد القادم');
        setInjectText('');
        fetchProjects();
      } else {
        const t = await r.text();
        toast.error(`فشل الحقن: ${t.slice(0, 100)}`);
      }
    } finally {
      setInjecting(false);
    }
  }, [selected, injectText, token, fetchProjects]);

  // Sort by urgency then recency
  const filteredProjects = useMemo(() => {
    const q = search.trim().toLowerCase();
    return [...projects]
      .filter((p) => !q || (p.name || '').toLowerCase().includes(q) || (p.user_id || '').toLowerCase().includes(q))
      .sort((a, b) => {
        const la = LEVEL_ORDER[a.distress_level] ?? 9;
        const lb = LEVEL_ORDER[b.distress_level] ?? 9;
        if (la !== lb) return la - lb;
        return (b.distress_score || 0) - (a.distress_score || 0);
      });
  }, [projects, search]);

  const counts = useMemo(() => {
    const c = { ok: 0, warn: 0, intervene: 0, critical: 0 };
    projects.forEach((p) => { c[p.distress_level] = (c[p.distress_level] || 0) + 1; });
    return c;
  }, [projects]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" dir="rtl" data-testid="guardian-dashboard">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-zinc-950/95 backdrop-blur border-b border-zinc-800">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Shield className="w-6 h-6 text-emerald-400" />
            <div>
              <h1 className="text-lg font-bold">Zenrex Guardian</h1>
              <p className="text-xs text-zinc-400">مراقبة لحظية لجودة محادثات FreeBuild</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="bg-emerald-500/10 text-emerald-300 border-emerald-500/30">🟢 {counts.ok}</Badge>
            <Badge className="bg-amber-500/10 text-amber-300 border-amber-500/30">🟡 {counts.warn}</Badge>
            <Badge className="bg-orange-500/10 text-orange-300 border-orange-500/30">🟠 {counts.intervene}</Badge>
            <Badge className="bg-red-500/10 text-red-300 border-red-500/30">🔴 {counts.critical}</Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchProjects}
              disabled={loading}
              data-testid="refresh-btn"
            >
              <RefreshCw className={`w-4 h-4 ml-1 ${loading ? 'animate-spin' : ''}`} />
              تحديث
            </Button>
            <label className="flex items-center gap-1 text-xs text-zinc-400 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                data-testid="auto-refresh-toggle"
                className="accent-emerald-500"
              />
              تلقائي
            </label>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-5">
        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-4">
          {['all', 'critical', 'intervene', 'warn', 'ok'].map((lv) => (
            <Button
              key={lv}
              size="sm"
              variant={filter === lv ? 'default' : 'outline'}
              onClick={() => setFilter(lv)}
              data-testid={`filter-${lv}`}
              className={filter === lv ? 'bg-emerald-600 hover:bg-emerald-500' : ''}
            >
              {lv === 'all' ? 'الكل' : LEVEL_STYLES[lv]?.label || lv}
            </Button>
          ))}
          <Input
            placeholder="🔍 ابحث باسم المشروع أو user_id"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs bg-zinc-900 border-zinc-700"
            data-testid="search-input"
          />
        </div>

        {/* Grid of project cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filteredProjects.map((p) => {
            const sty = LEVEL_STYLES[p.distress_level] || LEVEL_STYLES.ok;
            return (
              <Card
                key={p.id}
                className={`${sty.bg} ${sty.border} border p-4 cursor-pointer hover:scale-[1.01] transition-transform`}
                onClick={() => openDetail(p)}
                data-testid={`project-card-${p.id}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`inline-block w-2.5 h-2.5 rounded-full ${sty.dot}`} />
                      <h3 className="font-semibold truncate text-sm">{p.name || '—'}</h3>
                    </div>
                    <p className="text-xs text-zinc-400 truncate">{p.user_id?.slice(0, 12)}…</p>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold leading-none">{p.distress_score}</div>
                    <div className="text-[10px] text-zinc-400">score</div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1.5 mb-2">
                  <Badge className="bg-zinc-800/60 text-zinc-300 text-[10px]">{p.current_phase}</Badge>
                  {p.has_html && <Badge className="bg-cyan-500/10 text-cyan-300 text-[10px]">HTML</Badge>}
                  {p.code_unlocked && <Badge className="bg-purple-500/10 text-purple-300 text-[10px]">💳 دفع</Badge>}
                  {p.intervention_count > 0 && (
                    <Badge className="bg-orange-500/15 text-orange-300 text-[10px]">
                      🛡️ {p.intervention_count}
                    </Badge>
                  )}
                </div>

                {p.distress_signals?.length > 0 && (
                  <div className="text-[11px] text-amber-300/90 mb-2 line-clamp-2">
                    ⚠️ {p.distress_signals.slice(0, 2).join(' · ')}
                  </div>
                )}

                {p.msg_preview?.length > 0 && (
                  <div className="text-[11px] text-zinc-400 bg-zinc-900/40 rounded p-2 max-h-16 overflow-hidden">
                    {p.msg_preview[p.msg_preview.length - 1]?.role === 'user' ? '👤' : '🤖'}{' '}
                    {p.msg_preview[p.msg_preview.length - 1]?.content?.slice(0, 80) || ''}
                  </div>
                )}

                {p.last_intervention && (
                  <div className="mt-2 pt-2 border-t border-zinc-800 text-[10px] text-zinc-500">
                    آخر تدخّل: {p.last_intervention.diagnosis?.slice(0, 70)}
                  </div>
                )}
              </Card>
            );
          })}
        </div>

        {filteredProjects.length === 0 && !loading && (
          <div className="text-center py-12 text-zinc-500">
            <Sparkles className="w-10 h-10 mx-auto mb-3 opacity-40" />
            ما فيه مشاريع مطابقة للفلتر
          </div>
        )}
      </div>

      {/* Detail dialog */}
      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-3xl bg-zinc-950 border-zinc-800 text-zinc-100 max-h-[90vh] overflow-y-auto" dir="rtl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-emerald-400" />
              {selected?.name} — التفاصيل
            </DialogTitle>
          </DialogHeader>

          {selected && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-2 text-center">
                <Card className="bg-zinc-900 border-zinc-800 p-3">
                  <div className="text-2xl font-bold">{selected.distress_score}</div>
                  <div className="text-xs text-zinc-400">Distress</div>
                </Card>
                <Card className="bg-zinc-900 border-zinc-800 p-3">
                  <div className="text-2xl font-bold">{selected.intervention_count}</div>
                  <div className="text-xs text-zinc-400">تدخّلات</div>
                </Card>
                <Card className="bg-zinc-900 border-zinc-800 p-3">
                  <div className="text-2xl font-bold">{detail?.messages?.length || 0}</div>
                  <div className="text-xs text-zinc-400">رسائل</div>
                </Card>
              </div>

              {detail?.guardian_interventions?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4 text-orange-400" />
                    سجل التدخّلات
                  </h3>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {detail.guardian_interventions.slice().reverse().map((iv, i) => (
                      <Card key={iv.id || i} className="bg-zinc-900/60 border-zinc-800 p-3">
                        <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
                          <span>{iv.severity}</span>
                          <span>{iv.created_at?.slice(0, 19).replace('T', ' ')}</span>
                        </div>
                        <div className="text-xs font-semibold text-amber-300 mb-1">{iv.diagnosis}</div>
                        <div className="text-xs text-zinc-300">{iv.directive}</div>
                      </Card>
                    ))}
                  </div>
                </div>
              )}

              {/* Manual inject */}
              <div className="border-t border-zinc-800 pt-3">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                  <Send className="w-4 h-4 text-emerald-400" />
                  حقن توجيه يدوي
                </h3>
                <Textarea
                  placeholder="مثلاً: ركّز على إضافة قسم آراء العملاء بأسلوب احترافي بدون أسئلة..."
                  value={injectText}
                  onChange={(e) => setInjectText(e.target.value)}
                  rows={4}
                  className="bg-zinc-900 border-zinc-700 text-sm"
                  data-testid="inject-textarea"
                />
                <Button
                  className="mt-2 bg-emerald-600 hover:bg-emerald-500 w-full"
                  onClick={handleInject}
                  disabled={injecting || !injectText.trim()}
                  data-testid="inject-submit-btn"
                >
                  {injecting ? 'جاري الحقن...' : '🚀 حقن في الرد القادم'}
                </Button>
              </div>

              {/* Recent messages */}
              {detail?.messages && (
                <div>
                  <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                    <MessageSquare className="w-4 h-4 text-cyan-400" />
                    آخر الرسائل
                  </h3>
                  <div className="space-y-1.5 max-h-64 overflow-y-auto">
                    {detail.messages.slice(-8).map((m, i) => (
                      <div
                        key={i}
                        className={`text-xs p-2 rounded ${
                          m.role === 'user' ? 'bg-cyan-500/10 text-cyan-100' : 'bg-zinc-900/60 text-zinc-200'
                        }`}
                      >
                        <span className="font-semibold opacity-70">{m.role === 'user' ? '👤 العميل' : '🤖 AI'}: </span>
                        {(m.content || '').slice(0, 220)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
