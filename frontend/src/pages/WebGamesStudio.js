import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Globe, Check, X, Loader2, Sparkles, Code, TestTube,
  Rocket, ArrowLeft, ArrowRight, Image as ImageIcon, Play
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const PHASES = [
  { id: 'discovery', name: 'الاكتشاف', icon: Sparkles },
  { id: 'gdd_review', name: 'مراجعة التصميم', icon: Check },
  { id: 'assets_generation', name: 'توليد الأصول', icon: ImageIcon },
  { id: 'code_review', name: 'البرمجة', icon: Code },
  { id: 'testing_done', name: 'الاختبار', icon: TestTube },
  { id: 'deployed', name: 'النشر', icon: Rocket },
];

export default function WebGamesStudio({ user }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get('project');
  
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(false);
  const [gameIdea, setGameIdea] = useState('');
  const [feedback, setFeedback] = useState('');
  const [assetType, setAssetType] = useState('2d_sprites');
  const [subdomain, setSubdomain] = useState('');
  
  const token = localStorage.getItem('token');

  useEffect(() => {
    if (projectId) {
      loadProject(projectId);
    }
  }, [projectId]);

  const loadProject = async (id) => {
    try {
      const res = await fetch(`${API}/api/games/project/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      setProject(data);
    } catch (e) {
      toast.error('فشل تحميل المشروع');
    }
  };

  const startProject = async () => {
    if (!gameIdea.trim()) {
      toast.error('اكتب فكرة اللعبة أولاً');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API}/api/games/web/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ game_idea: gameIdea })
      });
      
      const data = await res.json();
      if (res.ok) {
        setProject(data);
        toast.success(`المشروع بدأ! (${data.credits_spent} نقطة)`);
        window.history.pushState({}, '', `?project=${data.project_id}`);
      } else {
        toast.error(data.detail || 'فشل البدء');
      }
    } catch (e) {
      toast.error('خطأ في الاتصال');
    }
    setLoading(false);
  };

  const approveGDD = async (withFeedback = false) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/games/web/approve-gdd`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: project.project_id || project.id,
          feedback: withFeedback ? feedback : null
        })
      });
      
      const data = await res.json();
      if (res.ok) {
        await loadProject(project.project_id || project.id);
        toast.success(withFeedback ? 'تم التعديل' : `انتقلنا للمرحلة التالية (${data.credits_spent} نقطة)`);
        setFeedback('');
      } else {
        toast.error(data.detail || 'فشل');
      }
    } catch (e) {
      toast.error('خطأ');
    }
    setLoading(false);
  };

  const generateAssets = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/games/web/generate-assets`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: project.project_id || project.id,
          asset_type: assetType,
          count: 10
        })
      });
      
      const data = await res.json();
      if (res.ok) {
        await loadProject(project.project_id || project.id);
        toast.success(`تم توليد ${data.assets.length} أصل (${data.credits_spent} نقطة)`);
      } else {
        toast.error(data.detail || 'فشل');
      }
    } catch (e) {
      toast.error('خطأ');
    }
    setLoading(false);
  };

  const generateCode = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/games/web/generate-code`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: project.project_id || project.id
        })
      });
      
      const data = await res.json();
      if (res.ok) {
        await loadProject(project.project_id || project.id);
        toast.success(`تم توليد الكود! (${data.credits_spent} نقطة)`);
      } else {
        toast.error(data.detail || 'فشل');
      }
    } catch (e) {
      toast.error('خطأ');
    }
    setLoading(false);
  };

  const testGame = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/games/web/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: project.project_id || project.id
        })
      });
      
      const data = await res.json();
      if (res.ok) {
        await loadProject(project.project_id || project.id);
        toast.success(`الاختبار نجح! (${data.credits_spent} نقطة)`);
      } else {
        toast.error(data.detail || 'فشل');
      }
    } catch (e) {
      toast.error('خطأ');
    }
    setLoading(false);
  };

  const deployGame = async () => {
    if (!subdomain.trim()) {
      toast.error('أدخل اسم النطاق الفرعي');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API}/api/games/web/deploy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: project.project_id || project.id,
          subdomain
        })
      });
      
      const data = await res.json();
      if (res.ok) {
        await loadProject(project.project_id || project.id);
        toast.success(`تم النشر! (${data.credits_spent} نقطة)`);
      } else {
        toast.error(data.detail || 'فشل');
      }
    } catch (e) {
      toast.error('خطأ');
    }
    setLoading(false);
  };

  const getCurrentPhaseIndex = () => {
    if (!project) return 0;
    return PHASES.findIndex(p => p.id === project.phase) || 0;
  };

  return (
    <div dir="rtl" className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <div className="bg-zinc-900/50 backdrop-blur border-b border-white/10 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard/games')}
              className="p-2 rounded-xl hover:bg-white/5 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <Globe className="w-6 h-6 text-blue-400" />
              <div>
                <h1 className="text-xl font-bold">استوديو ألعاب الويب</h1>
                <p className="text-xs text-zinc-400">بناء تدريجي احترافي</p>
              </div>
            </div>
          </div>
          
          <div className="text-sm">
            <span className="text-zinc-400">رصيدك:</span>
            <span className="text-amber-400 font-bold mr-2">{user?.balance?.toLocaleString()} نقطة</span>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Phase Progress */}
        {project && (
          <div className="mb-12">
            <div className="flex items-center justify-between mb-4">
              {PHASES.map((phase, idx) => (
                <div key={phase.id} className="flex items-center flex-1">
                  <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                    idx <= getCurrentPhaseIndex()
                      ? 'bg-blue-500 border-blue-500 text-white'
                      : 'bg-zinc-800 border-zinc-700 text-zinc-500'
                  }`}>
                    <phase.icon className="w-5 h-5" />
                  </div>
                  {idx < PHASES.length - 1 && (
                    <div className={`flex-1 h-0.5 mx-2 ${
                      idx < getCurrentPhaseIndex() ? 'bg-blue-500' : 'bg-zinc-700'
                    }`} />
                  )}
                </div>
              ))}
            </div>
            <div className="flex justify-between text-xs text-zinc-400">
              {PHASES.map(phase => (
                <div key={phase.id} className="text-center" style={{ width: '16%' }}>
                  {phase.name}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Content based on phase */}
        {!project ? (
          // Phase 0: Start Project
          <div className="max-w-2xl mx-auto">
            <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-3xl p-8">
              <h2 className="text-2xl font-bold mb-4">ابدأ مشروع لعبة ويب جديد</h2>
              <p className="text-zinc-400 mb-6">
                أخبرنا عن فكرة لعبتك، وسنبني لك Game Design Document كامل ونبدأ العمل خطوة بخطوة معك
              </p>
              
              <textarea
                value={gameIdea}
                onChange={(e) => setGameIdea(e.target.value)}
                placeholder="مثال: لعبة platformer مثل Mario، اللاعب يقفز ويجمع عملات ويتجنب أعداء. الستايل: pixel art"
                className="w-full h-32 bg-black/40 border border-white/15 rounded-xl px-4 py-3 resize-none focus:border-blue-400 outline-none"
                dir="rtl"
              />
              
              <button
                onClick={startProject}
                disabled={loading}
                className="w-full mt-4 bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-bold py-3 rounded-xl hover:scale-105 transition-transform disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                <span>{loading ? 'جاري البدء...' : 'ابدأ المشروع (50 نقطة)'}</span>
              </button>
            </div>
          </div>
        ) : project.phase === 'gdd_review' ? (
          // Phase 1: GDD Review
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-3xl p-8">
              <h2 className="text-2xl font-bold mb-6">Game Design Document</h2>
              
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-zinc-400 mb-1">عنوان اللعبة</div>
                  <div className="text-lg font-bold">{project.gdd?.title}</div>
                </div>
                
                <div>
                  <div className="text-sm text-zinc-400 mb-1">النوع</div>
                  <div>{project.gdd?.genre}</div>
                </div>
                
                <div>
                  <div className="text-sm text-zinc-400 mb-1">المنصة</div>
                  <div>{project.gdd?.target_platform}</div>
                </div>
                
                <div>
                  <div className="text-sm text-zinc-400 mb-1">الـCore Loop</div>
                  <div>{project.gdd?.core_loop}</div>
                </div>
                
                <div>
                  <div className="text-sm text-zinc-400 mb-1">الميكانيكا الأساسية</div>
                  <ul className="list-disc list-inside space-y-1">
                    {project.gdd?.mechanics?.map((m, i) => (
                      <li key={i}><strong>{m.name}:</strong> {m.description}</li>
                    ))}
                  </ul>
                </div>
                
                <div>
                  <div className="text-sm text-zinc-400 mb-1">الستايل البصري</div>
                  <div>{project.gdd?.visual_style}</div>
                </div>
                
                <div>
                  <div className="text-sm text-zinc-400 mb-1">الوقت المتوقع</div>
                  <div>{project.gdd?.estimated_dev_time}</div>
                </div>
              </div>
            </div>

            <div className="space-y-6">
              <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-3xl p-8">
                <h3 className="text-xl font-bold mb-4">هل توافق على التصميم؟</h3>
                
                <button
                  onClick={() => approveGDD(false)}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-green-500 to-emerald-500 text-white font-bold py-3 rounded-xl hover:scale-105 transition-transform disabled:opacity-50 flex items-center justify-center gap-2 mb-3"
                >
                  <Check className="w-5 h-5" />
                  <span>موافق — انتقل للمرحلة التالية</span>
                </button>

                <div className="text-sm text-zinc-400 text-center mb-4">أو</div>

                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="مثال: غيّر النوع ل Racing، الستايل ل Low-poly 3D"
                  className="w-full h-24 bg-black/40 border border-white/15 rounded-xl px-4 py-3 resize-none focus:border-amber-400 outline-none mb-3"
                  dir="rtl"
                />
                
                <button
                  onClick={() => approveGDD(true)}
                  disabled={loading || !feedback.trim()}
                  className="w-full bg-white/10 hover:bg-white/15 border border-white/15 text-white font-bold py-3 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <X className="w-5 h-5" />
                  <span>اطلب تعديل</span>
                </button>
              </div>

              <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4">
                <div className="text-sm text-amber-400">
                  💡 <strong>نصيحة:</strong> راجع التصميم جيداً. كل تعديل لاحقاً راح يكلف نقاط إضافية
                </div>
              </div>
            </div>
          </div>
        ) : project.phase === 'mechanics_design' ? (
          // Phase 2: Mechanics Design (Auto-approved, show and move to assets)
          <div className="max-w-4xl mx-auto">
            <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-3xl p-8 mb-6">
              <h2 className="text-2xl font-bold mb-6">تصميم الميكانيكا</h2>
              
              {project.mechanics?.map((mech, i) => (
                <div key={i} className="bg-white/5 rounded-xl p-4 mb-4">
                  <h3 className="font-bold mb-2">{mech.name}</h3>
                  <pre className="text-xs bg-black/50 rounded p-3 overflow-x-auto">
                    <code>{mech.code_snippet}</code>
                  </pre>
                </div>
              ))}
            </div>

            <button
              onClick={() => setProject({ ...project, phase: 'assets_generation' })}
              className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold py-3 rounded-xl hover:scale-105 transition-transform flex items-center justify-center gap-2"
            >
              <ArrowRight className="w-5 h-5" />
              <span>انتقل لمرحلة توليد الأصول</span>
            </button>
          </div>
        ) : project.phase === 'assets_generation' ? (
          // Phase 3: Generate Assets
          <div className="max-w-4xl mx-auto">
            <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-3xl p-8 mb-6">
              <h2 className="text-2xl font-bold mb-6">توليد الأصول البصرية</h2>
              
              <div className="mb-6">
                <label className="block text-sm font-semibold mb-2">نوع الأصول</label>
                <div className="grid grid-cols-2 gap-4">
                  <button
                    onClick={() => setAssetType('2d_sprites')}
                    className={`p-4 rounded-xl border-2 transition-all ${
                      assetType === '2d_sprites'
                        ? 'border-blue-500 bg-blue-500/20'
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }`}
                  >
                    <ImageIcon className="w-6 h-6 mb-2 mx-auto" />
                    <div className="font-bold">Sprites 2D</div>
                    <div className="text-xs text-zinc-400">شخصيات وعناصر</div>
                  </button>
                  
                  <button
                    onClick={() => setAssetType('3d_models')}
                    className={`p-4 rounded-xl border-2 transition-all ${
                      assetType === '3d_models'
                        ? 'border-purple-500 bg-purple-500/20'
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }`}
                  >
                    <Globe className="w-6 h-6 mb-2 mx-auto" />
                    <div className="font-bold">Models 3D</div>
                    <div className="text-xs text-zinc-400">كائنات ثلاثية</div>
                  </button>
                </div>
              </div>

              <button
                onClick={generateAssets}
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-bold py-3 rounded-xl hover:scale-105 transition-transform disabled:opacity-50 flex items-center justify-center gap-2 mb-4"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                <span>{loading ? 'جاري التوليد...' : `وّلد 10 ${assetType === '2d_sprites' ? 'sprites' : 'models'} (${assetType === '2d_sprites' ? '80' : '150'} نقطة)`}</span>
              </button>

              {project.assets?.length > 0 && (
                <>
                  <div className="grid grid-cols-5 gap-4 mb-6">
                    {project.assets.map((asset, i) => (
                      <div key={i} className="bg-white/5 rounded-xl p-3 text-center">
                        <div className="w-full h-20 bg-zinc-800 rounded mb-2 flex items-center justify-center">
                          <ImageIcon className="w-8 h-8 text-zinc-600" />
                        </div>
                        <div className="text-xs truncate">{asset.name}</div>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={generateCode}
                    disabled={loading}
                    className="w-full bg-gradient-to-r from-green-500 to-emerald-500 text-white font-bold py-3 rounded-xl hover:scale-105 transition-transform disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    <Code className="w-5 h-5" />
                    <span>انتقل لمرحلة البرمجة (200 نقطة)</span>
                  </button>
                </>
              )}
            </div>
          </div>
        ) : project.phase === 'code_review' ? (
          // Phase 4: Code Review
          <div className="max-w-6xl mx-auto">
            <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-3xl p-8 mb-6">
              <h2 className="text-2xl font-bold mb-6">الكود المولّد</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-white/5 rounded-xl p-4">
                  <div className="text-sm text-zinc-400 mb-1">HTML</div>
                  <div className="text-xs font-mono">{project.code?.html?.split('\n').length} سطر</div>
                </div>
                <div className="bg-white/5 rounded-xl p-4">
                  <div className="text-sm text-zinc-400 mb-1">JavaScript</div>
                  <div className="text-xs font-mono">{project.code?.js?.split('\n').length} سطر</div>
                </div>
                <div className="bg-white/5 rounded-xl p-4">
                  <div className="text-sm text-zinc-400 mb-1">CSS</div>
                  <div className="text-xs font-mono">{project.code?.css?.split('\n').length} سطر</div>
                </div>
              </div>

              <div className="mb-6">
                <div className="bg-black/50 rounded-xl p-4 max-h-96 overflow-auto">
                  <pre className="text-xs"><code>{project.code?.html}</code></pre>
                </div>
              </div>

              <button
                onClick={testGame}
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-bold py-3 rounded-xl hover:scale-105 transition-transform disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <TestTube className="w-5 h-5" />}
                <span>{loading ? 'جاري الاختبار...' : 'اختبر اللعبة (80 نقطة)'}</span>
              </button>
            </div>
          </div>
        ) : project.phase === 'testing_done' ? (
          // Phase 5: Deploy
          <div className="max-w-2xl mx-auto">
            <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-3xl p-8">
              <h2 className="text-2xl font-bold mb-4">✅ الاختبار نجح!</h2>
              <p className="text-zinc-400 mb-6">اللعبة جاهزة للنشر. اختر اسم نطاق فرعي</p>
              
              {project.test_results && (
                <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4 mb-6">
                  <div className="text-sm space-y-1">
                    <div>✓ Syntax Check: {project.test_results.syntax_check ? 'Pass' : 'Fail'}</div>
                    <div>✓ Load Time: {project.test_results.load_time_ms}ms</div>
                    <div>✓ Playable: {project.test_results.playable ? 'Yes' : 'No'}</div>
                  </div>
                </div>
              )}

              <input
                type="text"
                value={subdomain}
                onChange={(e) => setSubdomain(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                placeholder="my-game"
                className="w-full bg-black/40 border border-white/15 rounded-xl px-4 py-3 focus:border-green-400 outline-none mb-2"
              />
              <div className="text-xs text-zinc-500 mb-4">{subdomain || 'my-game'}.vercel.app</div>

              <button
                onClick={deployGame}
                disabled={loading || !subdomain.trim()}
                className="w-full bg-gradient-to-r from-green-500 to-emerald-500 text-white font-bold py-3 rounded-xl hover:scale-105 transition-transform disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Rocket className="w-5 h-5" />}
                <span>{loading ? 'جاري النشر...' : 'انشر اللعبة (100 نقطة)'}</span>
              </button>
            </div>
          </div>
        ) : project.phase === 'deployed' ? (
          // Phase 6: Success
          <div className="max-w-2xl mx-auto">
            <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 border border-green-500/30 rounded-3xl p-12 text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-green-500 to-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6">
                <Rocket className="w-10 h-10 text-white" />
              </div>
              
              <h2 className="text-3xl font-bold mb-4">🎉 تم النشر بنجاح!</h2>
              <p className="text-zinc-300 mb-8">لعبتك الآن متاحة على الإنترنت</p>

              <a
                href={project.deploy_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 bg-white text-black font-bold px-6 py-3 rounded-xl hover:scale-105 transition-transform mb-4"
              >
                <Play className="w-5 h-5" />
                <span>افتح اللعبة</span>
              </a>

              <div className="bg-white/5 rounded-xl p-4 mt-8">
                <div className="text-sm text-zinc-400 mb-2">إجمالي النقاط المستخدمة</div>
                <div className="text-3xl font-bold text-amber-400">{project.credits_spent} نقطة</div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
