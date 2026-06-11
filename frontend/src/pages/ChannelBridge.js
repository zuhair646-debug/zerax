/**
 * Channel Bridge — owner pushes Zenrex-generated assets (studio/wizard) to their client websites.
 * Route: /dashboard/bridge
 *
 * Lists owner's generated assets (studio images/videos + wizard results) and shows
 * buttons to publish to specific project as Story or Banner (2 pts each).
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Coins, Send, Loader2, History } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ChannelBridge({ user }) {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [assets, setAssets] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null); // asset_id currently pushing
  const [credits, setCredits] = useState(user?.credits || 0);

  const tokenH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

  useEffect(() => {
    if (!localStorage.getItem('token')) { navigate('/login'); return; }
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  useEffect(() => {
    if (selectedProject) loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProject]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [projR, assetsR, meR] = await Promise.all([
        fetch(`${API}/api/bridge/projects`, { headers: tokenH() }),
        fetch(`${API}/api/studio/gallery`, { headers: tokenH() }),
        fetch(`${API}/api/auth/me`, { headers: tokenH() }),
      ]);
      const projData = projR.ok ? await projR.json() : { projects: [] };
      setProjects(projData.projects || []);
      if (projData.projects?.length) setSelectedProject(projData.projects[0].id);
      if (assetsR.ok) {
        const d = await assetsR.json();
        // Gallery returns {items: [{id, type, media_url, ...}]}
        const combined = (d.items || []).map(x => ({
          ...x,
          _source: 'studio',
          _type: x.type === 'video' ? 'video' : 'image',
        }));
        setAssets(combined);
      }
      if (meR.ok) { const d = await meR.json(); setCredits(d.credits || 0); }
    } catch (e) { toast.error('فشل التحميل'); }
    setLoading(false);
  };

  const loadHistory = async () => {
    try {
      const r = await fetch(`${API}/api/bridge/history?project_id=${selectedProject}`, { headers: tokenH() });
      if (r.ok) {
        const d = await r.json();
        setHistory(d.history || []);
      }
    } catch (_) { /* ignore */ }
  };

  const pushToTarget = async (asset, target) => {
    if (!selectedProject) { toast.error('اختر متجر أول'); return; }
    setBusy(asset.id);
    try {
      const endpoint = target === 'banner' ? 'push-to-banner' : 'push-to-story';
      const body = target === 'banner'
        ? { project_id: selectedProject, asset_id: asset.id, asset_source: asset._source, title: asset.title || '', subtitle: '' }
        : { project_id: selectedProject, asset_id: asset.id, asset_source: asset._source, caption: asset.title || '' };
      const r = await fetch(`${API}/api/bridge/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenH() },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      toast.success(d.message);
      setCredits(c => c - (d.credits_deducted || 0));
      loadHistory();
    } catch (e) { toast.error(e.message); } finally { setBusy(null); }
  };

  if (loading) return (
    <div className="min-h-screen bg-[#0a0a12]"><Navbar user={user} transparent />
      <div className="pt-24 text-center text-white">جاري التحميل...</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0a12]" data-testid="channel-bridge-page">
      <Navbar user={user} transparent />
      <div className="pt-20 max-w-6xl mx-auto px-4 pb-16">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-black text-white mb-1">🌉 Channel Bridge</h1>
            <p className="text-amber-200/70 text-sm">انشر أصولك المولّدة (صور/فيديوهات) مباشرة في متاجرك كـStory أو بنر</p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-400/30 text-amber-300 text-sm font-bold">
            <Coins className="w-4 h-4" />
            <span>{credits}</span> نقطة
          </div>
        </div>

        {projects.length === 0 ? (
          <div className="p-8 rounded-2xl bg-white/5 border border-white/10 text-center text-white/70" data-testid="bridge-no-projects">
            ما عندك متاجر. <button onClick={() => navigate('/websites')} className="text-amber-300 font-bold">أنشئ أول متجر</button>
          </div>
        ) : (
          <>
            <div className="mb-5">
              <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">المتجر الوجهة</label>
              <select value={selectedProject} onChange={(e) => setSelectedProject(e.target.value)}
                className="w-full p-3 bg-black/40 border border-white/10 rounded-lg text-white outline-none focus:border-amber-400"
                data-testid="bridge-project-select">
                {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <div className="text-xs text-amber-200/60 mt-2">تكلفة النشر: 2 نقطة لكل أصل</div>
            </div>

            {assets.length === 0 ? (
              <div className="p-8 rounded-2xl bg-white/5 border border-white/10 text-center text-white/70">
                ما عندك أصول بعد. ابدأ من <button onClick={() => navigate('/studio')} className="text-amber-300 font-bold">الاستوديو</button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8" data-testid="bridge-assets-grid">
                {assets.map(asset => (
                  <div key={`${asset._source}-${asset.id}`} className="rounded-2xl overflow-hidden border border-white/10 bg-white/5 hover:border-amber-400/30 transition" data-testid={`bridge-asset-${asset.id}`}>
                    {asset._type === 'video' ? (
                      <video src={asset.media_url} className="w-full aspect-video object-cover" muted />
                    ) : (
                      <img src={asset.media_url} alt="" className="w-full aspect-square object-cover" />
                    )}
                    <div className="p-3 space-y-2">
                      <div className="text-xs text-white/60 truncate">{asset.title || asset.scenario || asset.prompt_used || 'بدون عنوان'}</div>
                      <div className="flex gap-2">
                        <Button onClick={() => pushToTarget(asset, 'story')} disabled={busy === asset.id}
                          size="sm" className="flex-1 bg-purple-500/20 border border-purple-400/30 text-purple-300 hover:bg-purple-500/30 text-xs font-bold"
                          data-testid={`bridge-story-${asset.id}`}>
                          {busy === asset.id ? <Loader2 className="w-3 h-3 animate-spin"/> : <><Send className="w-3 h-3 me-1" /> Story (2)</>}
                        </Button>
                        <Button onClick={() => pushToTarget(asset, 'banner')} disabled={busy === asset.id}
                          size="sm" className="flex-1 bg-amber-500/20 border border-amber-400/30 text-amber-300 hover:bg-amber-500/30 text-xs font-bold"
                          data-testid={`bridge-banner-${asset.id}`}>
                          بنر (2)
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* History */}
            <div className="p-5 rounded-2xl bg-white/5 border border-white/10">
              <div className="flex items-center gap-2 mb-3">
                <History className="w-4 h-4 text-amber-300" />
                <h3 className="text-sm font-black text-white">سجل النشر</h3>
              </div>
              {history.length === 0 ? (
                <div className="text-xs text-white/50">لسّا ما نشرت شي</div>
              ) : (
                <div className="space-y-2" data-testid="bridge-history-list">
                  {history.map(h => (
                    <div key={h.id} className="flex items-center justify-between text-xs py-2 border-b border-white/5" data-testid={`bridge-h-${h.id}`}>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded-full font-bold ${h.target === 'banner' ? 'bg-amber-500/20 text-amber-300' : 'bg-purple-500/20 text-purple-300'}`}>
                          {h.target === 'banner' ? 'بنر' : 'Story'}
                        </span>
                        <span className="text-white/70">{h.asset_source}</span>
                      </div>
                      <div className="text-white/50">
                        {new Date(h.created_at).toLocaleDateString('ar-SA')} · -{h.cost} نقطة
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
