import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Smartphone, Send, Paperclip, Loader2, Check, X, 
  Eye, Code, Image, FileText, Package, Sparkles,
  ArrowRight, Lock, Unlock, CheckCircle2, HelpCircle,
  Brain, FolderOpen
} from 'lucide-react';
import { toast } from 'sonner';
import TechInfoModal from '@/components/TechInfoModal';
import VoiceRecorderButton from '@/components/VoiceRecorderButton';
import QuickActions from '@/components/QuickActions';
import StorageBadge from '@/components/StorageBadge';
import ImageLightbox from '@/components/ImageLightbox';
import MyProjectsModal from '@/components/games/MyProjectsModal';
import AINotesPanel from '@/components/games/AINotesPanel';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AppGamesStudio({ user }) {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  
  const [step, setStep] = useState('select_tech');
  const [programmingTypes, setProgrammingTypes] = useState([]);
  const [selectedTech, setSelectedTech] = useState(null);
  const [projectTitle, setProjectTitle] = useState('');
  const [projectDesc, setProjectDesc] = useState('');
  
  const [project, setProject] = useState(null);
  const [message, setMessage] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activePhase, setActivePhase] = useState('discovery');
  const [infoTech, setInfoTech] = useState(null);
  const [lightbox, setLightbox] = useState(null);
  const [activeTab, setActiveTab] = useState('chat'); // chat | live | approved | notes
  const [resuming, setResuming] = useState(false);
  const [myProjectsOpen, setMyProjectsOpen] = useState(false);
  const [notesRefreshSignal, setNotesRefreshSignal] = useState(0);
  
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // 🔄 Auto-resume project — re-runs on URL change so MyProjectsModal switching works
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const pid = params.get('project');
    if (!pid || !token) return;
    if (project?.id === pid) return;
    setResuming(true);
    fetch(`${API}/api/games/project/${pid}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : Promise.reject(r))
      .then(data => {
        if (data?.project) {
          setProject(data.project);
          setStep('chat');
          setActivePhase(data.project.current_phase || 'discovery');
          setActiveTab('chat');
          toast.success('✅ تم استرجاع المشروع من حيث وقفت');
        }
      })
      .catch(() => toast.error('فشل استرجاع المشروع — قد يكون محذوف'))
      .finally(() => setResuming(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search]);

  // 🔗 Sync project ID to URL whenever it changes
  useEffect(() => {
    if (project?.id) {
      const url = new URL(window.location.href);
      if (url.searchParams.get('project') !== project.id) {
        url.searchParams.set('project', project.id);
        window.history.replaceState({}, '', url.toString());
      }
    }
  }, [project?.id]);

  // Fetch programming types
  useEffect(() => {
    fetch(`${API}/api/games/programming-types?game_type=app`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(data => setProgrammingTypes(data.types || []))
      .catch(e => toast.error(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Create project
  const handleCreateProject = async () => {
    if (!selectedTech || !projectTitle.trim()) {
      toast.error('اختر نوع البرمجة وأدخل عنوان المشروع');
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/games/project`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          game_type: 'app',
          title: projectTitle,
          description: projectDesc,
          programming_type: selectedTech
        })
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to create project');
      
      setProject(data.project);
      setStep('chat');
      toast.success('📱 مشروع تطبيق جاهز!');
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Send message
  const handleSendMessage = async () => {
    if (!message.trim() && attachments.length === 0) return;
    
    setLoading(true);
    const formData = new FormData();
    formData.append('message', message);
    formData.append('phase_id', activePhase);
    attachments.forEach(file => formData.append('files', file));
    
    try {
      const res = await fetch(`${API}/api/games/project/${project.id}/chat`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'فشل الإرسال');
      
      // Reload project
      const projectRes = await fetch(`${API}/api/games/project/${project.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const projectData = await projectRes.json();
      setProject(projectData.project);
      
      setMessage('');
      setAttachments([]);
      toast.success(`✨ ${data.credits_used} نقطة`);
      setNotesRefreshSignal(s => s + 1);
      
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Unlock phase
  const handleUnlockPhase = async (phaseId) => {
    try {
      const res = await fetch(`${API}/api/games/project/${project.id}/unlock-phase?phase_id=${phaseId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to unlock');
      
      setActivePhase(phaseId);
      
      const projectRes = await fetch(`${API}/api/games/project/${project.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const projectData = await projectRes.json();
      setProject(projectData.project);
      
      toast.success('🔓 المرحلة مفتوحة');
    } catch (e) {
      toast.error(e.message);
    }
  };

  // Approve asset
  const handleApproveAsset = async (assetId, approved) => {
    try {
      const res = await fetch(`${API}/api/games/project/${project.id}/approve-asset`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ asset_id: assetId, approved })
      });
      if (!res.ok) throw new Error('Failed');
      
      const projectRes = await fetch(`${API}/api/games/project/${project.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const projectData = await projectRes.json();
      setProject(projectData.project);
      
      if (approved) {
        toast.success('✅ تم اعتماد الـAsset — الذكاء سيستخدمه في المراحل القادمة', {
          duration: 4000
        });
      } else {
        toast.error('❌ تم رفض الـAsset — يمكنك طلب تعديل في الشات', {
          duration: 4000
        });
      }
    } catch (e) {
      toast.error(e.message);
    }
  };

  const phaseIcon = (id) => {
    const icons = {
      discovery: '🔍', architecture: '🏗️', mechanics: '⚙️',
      characters: '🎭', environment: '🏞️', assets: '🎨',
      programming: '💻', testing: '🧪', publishing: '📱'
    };
    return icons[id] || '📦';
  };

  // ═══════════════════════════════════════════════════════════════
  // STEP 1: Select Tech
  // ═══════════════════════════════════════════════════════════════
  if (step === 'select_tech') {
    return (
      <div dir="rtl" className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-blue-950/20 text-white p-6">
        <div className="max-w-4xl mx-auto">
          {/* Top nav row — My Projects (left) + Back (right) */}
          <div className="mb-4 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => setMyProjectsOpen(true)}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all"
              data-testid="open-my-projects"
              title="افتح كل مشاريعك ومحادثاتك السابقة"
            >
              <FolderOpen className="w-4 h-4" />
              <span className="text-sm font-medium">مشاريعي السابقة</span>
            </button>

            <button
              type="button"
              onClick={() => navigate('/dashboard/games')}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all"
              data-testid="back-to-games-dashboard"
            >
              <ArrowRight className="w-4 h-4" />
              <span className="text-sm font-medium">رجوع لاستوديو الألعاب</span>
            </button>
          </div>

          <div className="flex items-center gap-4 mb-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Smartphone className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">📱 App Games Studio</h1>
              <p className="text-zinc-400">اختر منصة البرمجة وابدأ</p>
            </div>
          </div>

          <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl p-6 mb-6">
            <h2 className="text-xl font-bold mb-2">⚙️ اختر نوع البرمجة</h2>
            <p className="text-xs text-zinc-500 mb-4">اضغط على <HelpCircle className="inline w-3.5 h-3.5 text-blue-300" /> لمعرفة الفرق بين كل منصة (3D، الأداء، الجمهور)</p>
            <div className="grid md:grid-cols-2 gap-4">
              {programmingTypes.map(tech => (
                <div
                  key={tech.id}
                  onClick={() => setSelectedTech(tech.id)}
                  className={`relative p-4 rounded-xl border-2 transition-all text-right cursor-pointer ${
                    selectedTech === tech.id
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-white/10 bg-black/20 hover:border-white/20'
                  }`}
                  data-testid={`tech-card-${tech.id}`}
                >
                  {/* (?) button */}
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setInfoTech(tech.id); }}
                    className="absolute top-2 left-2 w-7 h-7 rounded-full bg-black/40 hover:bg-black/70 border border-white/20 hover:border-blue-400/60 flex items-center justify-center transition-all hover:scale-110"
                    data-testid={`tech-info-btn-${tech.id}`}
                    aria-label={`معلومات عن ${tech.name}`}
                    title="ما هذا؟ اضغط لمعرفة المزيد"
                  >
                    <HelpCircle className="w-3.5 h-3.5 text-blue-200" />
                  </button>

                  <div className="font-bold text-lg pl-9">{tech.name}</div>
                  <div className="text-sm text-zinc-400">{tech.desc}</div>
                  {selectedTech === tech.id && (
                    <div className="mt-2 flex items-center gap-2 text-blue-400">
                      <Check className="w-4 h-4" />
                      <span className="text-sm">محدد</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl p-6 mb-6">
            <h2 className="text-xl font-bold mb-4">📝 معلومات التطبيق</h2>
            <input
              type="text"
              placeholder="اسم اللعبة (مثال: سباق سيارات 3D)"
              value={projectTitle}
              onChange={e => setProjectTitle(e.target.value)}
              className="w-full bg-black/40 border border-white/15 rounded-xl px-4 py-3 mb-4 outline-none focus:border-blue-400"
            />
            <textarea
              placeholder="وصف مختصر"
              value={projectDesc}
              onChange={e => setProjectDesc(e.target.value)}
              rows={3}
              className="w-full bg-black/40 border border-white/15 rounded-xl px-4 py-3 outline-none focus:border-blue-400 resize-none"
            />
          </div>

          <button
            onClick={handleCreateProject}
            disabled={!selectedTech || !projectTitle.trim() || loading}
            className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-400 hover:to-purple-500 disabled:from-zinc-700 disabled:to-zinc-800 text-white font-bold rounded-xl py-4 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>جاري الإنشاء...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                <span>ابدأ المشروع</span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>

        {/* Tech Info Modal */}
        {infoTech && (
          <TechInfoModal
            techId={infoTech}
            onClose={() => setInfoTech(null)}
            onSelect={(id) => setSelectedTech(id)}
          />
        )}

        {/* My Projects Modal — visible from select-tech step */}
        <MyProjectsModal
          open={myProjectsOpen}
          onClose={() => setMyProjectsOpen(false)}
          accentColor="blue"
        />
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════
  // STEP 2: Chat (same 3-pane layout)
  // ═══════════════════════════════════════════════════════════════
  const currentPhaseInfo = project?.phases_definitions?.find(p => p.id === activePhase);
  const messages = project?.phases?.[activePhase]?.messages || [];
  const allAssets = project?.assets || {};

  return (
    <div dir="rtl" className="h-screen bg-zinc-950 text-white flex flex-col">
      <div className="bg-zinc-900/80 backdrop-blur border-b border-white/10 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => navigate('/dashboard/games')}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all"
            data-testid="back-from-chat"
            title="رجوع لاستوديو الألعاب"
          >
            <ArrowRight className="w-4 h-4" />
            <span className="text-xs font-medium hidden sm:inline">رجوع</span>
          </button>
          <button
            type="button"
            onClick={() => setMyProjectsOpen(true)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-white transition-all"
            data-testid="open-my-projects-chat"
            title="افتح مشاريعي السابقة"
          >
            <FolderOpen className="w-4 h-4" />
            <span className="text-xs font-medium hidden sm:inline">مشاريعي</span>
          </button>
          <Smartphone className="w-6 h-6 text-blue-400" />
          <div>
            <h1 className="font-bold text-lg">{project?.title}</h1>
            <p className="text-sm text-zinc-400">{currentPhaseInfo?.title}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Programming Type Badge */}
          <div className="flex items-center gap-2 px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <Code className="w-4 h-4 text-amber-400" />
            <span className="text-sm font-medium text-amber-300">
              {programmingTypes.find(t => t.id === project?.programming_type)?.name || project?.programming_type}
            </span>
          </div>
          
          <StorageBadge projectId={project?.id} />
          {project?.preview_url && (
            <a href={project.preview_url} target="_blank" rel="noopener noreferrer"
               className="px-4 py-2 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-500/30 flex items-center gap-2">
              <Eye className="w-4 h-4" />
              <span>Preview</span>
            </a>
          )}
          <div className="px-4 py-2 bg-white/5 rounded-lg text-sm">💰 {user?.balance || 0}</div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Phases */}
        <div className="w-64 bg-zinc-900/50 border-l border-white/10 p-4 overflow-y-auto">
          <h2 className="font-bold mb-3 text-blue-400">📋 المراحل</h2>
          <div className="space-y-2">
            {project?.phases_definitions?.map(phase => {
              const phaseData = project.phases[phase.id];
              const isActive = activePhase === phase.id;
              const isLocked = phaseData.status === 'locked';
              
              return (
                <div
                  key={phase.id}
                  role="button"
                  tabIndex={isLocked ? -1 : 0}
                  aria-disabled={isLocked}
                  onClick={() => !isLocked && setActivePhase(phase.id)}
                  onKeyDown={(e) => {
                    if (!isLocked && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault();
                      setActivePhase(phase.id);
                    }
                  }}
                  className={`w-full text-right p-3 rounded-lg border transition-all ${
                    isActive ? 'bg-blue-500/20 border-blue-500/50 text-blue-300' :
                    isLocked ? 'bg-black/20 border-white/5 text-zinc-600 cursor-not-allowed' :
                    'bg-black/20 border-white/10 hover:border-white/20 cursor-pointer'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold">{phaseIcon(phase.id)} {phase.title.replace(/🔍|🏗️|⚙️|🎭|🏞️|🎨|💻|🧪|📱/g, '').trim()}</span>
                    {isLocked ? <Lock className="w-3 h-3" /> :
                     phaseData.status === 'completed' ? <CheckCircle2 className="w-3 h-3 text-green-400" /> :
                     <Unlock className="w-3 h-3 text-blue-400" />}
                  </div>
                  <div className="text-xs text-zinc-500">{phase.credits} نقطة</div>
                  {isLocked && (
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleUnlockPhase(phase.id); }}
                      className="mt-2 w-full text-xs bg-blue-500/10 border border-blue-500/30 rounded px-2 py-1 hover:bg-blue-500/20">
                      🔓 فتح
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Chat */}
        <div className="flex-1 flex flex-col">
          {/* Tab Bar */}
          <div className="flex border-b border-white/10 bg-zinc-900/40 px-2 gap-1" data-testid="studio-tabs">
            <button
              onClick={() => setActiveTab('chat')}
              data-testid="tab-chat"
              className={`px-4 py-2.5 text-sm font-bold border-b-2 transition-all ${activeTab === 'chat' ? 'text-blue-300 border-blue-400' : 'text-zinc-400 border-transparent hover:text-white'}`}
            >
              💬 المحادثة
              {messages.length > 0 && (
                <span className="ms-1.5 text-[10px] bg-blue-500/20 px-1.5 py-0.5 rounded-full">{messages.length}</span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('live')}
              data-testid="tab-live"
              className={`px-4 py-2.5 text-sm font-bold border-b-2 transition-all ${activeTab === 'live' ? 'text-cyan-300 border-cyan-400' : 'text-zinc-400 border-transparent hover:text-white'}`}
            >
              📡 البث المباشر
            </button>
            <button
              onClick={() => setActiveTab('approved')}
              data-testid="tab-approved"
              className={`px-4 py-2.5 text-sm font-bold border-b-2 transition-all ${activeTab === 'approved' ? 'text-emerald-300 border-emerald-400' : 'text-zinc-400 border-transparent hover:text-white'}`}
            >
              ✅ المعتمدات
              {(() => {
                const count = Object.values(allAssets).flat().filter(a => a?.approved).length;
                return count > 0 ? <span className="ms-1.5 text-[10px] bg-emerald-500/20 px-1.5 py-0.5 rounded-full">{count}</span> : null;
              })()}
            </button>
            <button
              onClick={() => setActiveTab('notes')}
              data-testid="tab-notes"
              className={`px-4 py-2.5 text-sm font-bold border-b-2 transition-all flex items-center gap-1.5 ${activeTab === 'notes' ? 'text-violet-300 border-violet-400' : 'text-zinc-400 border-transparent hover:text-white'}`}
            >
              <Brain className="w-3.5 h-3.5" />
              <span>ذاكرة AI</span>
            </button>
            <div className="flex-1" />
            {resuming && (
              <div className="text-xs text-zinc-500 flex items-center gap-1.5 px-2">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>جاري الاسترجاع...</span>
              </div>
            )}
            <div className="text-[10px] text-zinc-500 flex items-center gap-1.5 px-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>محفوظ تلقائياً</span>
            </div>
          </div>

          {/* TAB CONTENT: Live */}
          {activeTab === 'live' && (
            <div className="flex-1 overflow-y-auto p-6 bg-black/40" data-testid="tab-content-live">
              <div className="max-w-3xl mx-auto space-y-4">
                <h2 className="text-lg font-bold text-cyan-300 flex items-center gap-2">
                  <span>📡</span><span>البث المباشر — معاينة التطبيق</span>
                </h2>
                <p className="text-xs text-zinc-400">هنا تشوف التطبيق وهو يتبني خطوة بخطوة. كل عنصر معتمد يظهر مباشرة.</p>
                {project?.preview_url ? (
                  <div className="rounded-xl border border-cyan-500/30 overflow-hidden bg-black">
                    <iframe src={project.preview_url} className="w-full" style={{ height: '70vh' }} title="Live Preview" />
                  </div>
                ) : (
                  <div className="rounded-xl border border-white/10 bg-black/40 p-8 text-center">
                    <div className="text-5xl mb-3">🎬</div>
                    <p className="text-zinc-300 font-bold mb-2">لا يوجد بث مباشر بعد</p>
                    <p className="text-xs text-zinc-500">سيظهر هنا تلقائياً بعد ما تعتمد عناصر اللعبة ويبدأ AI بناء التطبيق.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB CONTENT: Approved */}
          {activeTab === 'approved' && (
            <div className="flex-1 overflow-y-auto p-6 bg-black/40" data-testid="tab-content-approved">
              <div className="max-w-5xl mx-auto space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-emerald-300 flex items-center gap-2">
                    <span>✅</span><span>الأصول المعتمدة</span>
                  </h2>
                  <p className="text-xs text-zinc-400">كل صورة أو موديل أو صوت اعتمدته يظهر هنا بشكل دائم.</p>
                </div>
                {Object.entries({
                  images: { label: '🎨 الصور المعتمدة', color: 'blue' },
                  models3d: { label: '🧊 موديلات 3D معتمدة', color: 'cyan' },
                  audio: { label: '🎵 موسيقى وصوتيات', color: 'violet' },
                  videos: { label: '🎬 فيديوهات معتمدة', color: 'rose' },
                }).map(([bucket, meta]) => {
                  const items = (allAssets[bucket] || []).filter(a => a.approved);
                  if (items.length === 0) return null;
                  return (
                    <div key={bucket} className="space-y-2">
                      <h3 className={`text-sm font-bold text-${meta.color}-300`}>{meta.label} · {items.length}</h3>
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                        {items.map(a => (
                          <div key={a.id} className={`rounded-lg border border-${meta.color}-500/30 bg-black/30 overflow-hidden`}>
                            {a.image_url && (
                              <img src={`${API}${a.image_url}`} alt={a.name}
                                   onClick={() => setLightbox({ src: `${API}${a.image_url}`, alt: a.name })}
                                   className="w-full aspect-square object-cover cursor-zoom-in hover:opacity-90 transition-opacity" loading="lazy" />
                            )}
                            {a.audio_url && (
                              <div className="p-3 aspect-square flex flex-col justify-center bg-violet-500/10">
                                <div className="text-3xl text-center mb-2">{a.type === 'music' ? '🎵' : '🔊'}</div>
                                <audio src={`${API}${a.audio_url}`} controls className="w-full" />
                              </div>
                            )}
                            {a.video_url && (
                              <video src={`${API}${a.video_url}`} controls className="w-full aspect-video" />
                            )}
                            <div className="p-2">
                              <div className="text-[10px] text-zinc-300 truncate font-bold">{a.name}</div>
                              <div className="text-[9px] text-zinc-500">{a.subtype || a.style}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
                {Object.values(allAssets).flat().filter(a => a?.approved).length === 0 && (
                  <div className="text-center text-zinc-500 mt-12">
                    <div className="text-5xl mb-3">📭</div>
                    <p className="font-bold mb-1">لا توجد أصول معتمدة بعد</p>
                    <p className="text-xs">ارجع للمحادثة واعتمد الأصول اللي تعجبك.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB CONTENT: AI Notes */}
          {activeTab === 'notes' && (
            <AINotesPanel
              projectId={project?.id}
              accentColor="blue"
              refreshSignal={notesRefreshSignal}
            />
          )}

          {activeTab === 'chat' && (
          <div className="flex-1 overflow-y-auto p-6 space-y-4" data-testid="tab-content-chat">
            {messages.length === 0 && (
              <div className="text-center text-zinc-500 mt-12">
                <div className="text-6xl mb-4">{phaseIcon(activePhase)}</div>
                <h3 className="text-xl font-bold mb-2">{currentPhaseInfo?.title}</h3>
                <p className="text-sm">{currentPhaseInfo?.description}</p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className="space-y-3">
                <div className="flex justify-end">
                  <div className="bg-blue-500/20 border border-blue-500/30 rounded-2xl rounded-br-sm px-4 py-3 max-w-2xl">
                    <div className="text-sm">{msg.user}</div>
                  </div>
                </div>
                <div className="flex justify-start">
                  <div className="bg-zinc-800/50 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 max-w-3xl">
                    <div className="text-sm whitespace-pre-wrap">
                      {(msg.assistant || '').replace(/<<[\s\S]*?>>/g, '').replace(/\n{3,}/g, '\n\n').trim()}
                    </div>
                    {msg.generated_assets?.length > 0 && (
                      <div className="mt-4 space-y-3" data-testid="inline-assets">
                        {msg.generated_assets.map((a) => {
                          const isImg = a.type === 'image';
                          const is3D = a.type === '3d';
                          const isVid = a.type === 'video';
                          const isAudio = a.type === 'music' || a.type === 'sfx';
                          const url = a.image_url || a.model_url || a.video_url || a.audio_url;
                          const fullUrl = url ? `${API}${url}` : null;
                          const subtypeBadge = a.subtype || a.style || a.type;
                          return (
                            <div key={a.id} className="border border-blue-500/20 rounded-xl overflow-hidden bg-black/30">
                              {isImg && fullUrl && (
                                <img src={fullUrl} alt={a.name} loading="lazy"
                                     onClick={() => setLightbox({ src: fullUrl, alt: a.name })}
                                     className="w-full max-w-md object-cover cursor-zoom-in hover:opacity-90 transition-opacity"
                                     data-testid={`generated-asset-${a.id}`} />
                              )}
                              {is3D && fullUrl && (
                                <div className="p-3 flex flex-col gap-2" data-testid={`generated-asset-${a.id}`}>
                                  <div className="flex items-center gap-2 text-blue-300 text-sm font-bold">
                                    <span>🧊</span><span>موديل 3D جاهز (.glb)</span>
                                  </div>
                                  <a href={fullUrl} download
                                     className="text-xs px-3 py-2 bg-blue-500/15 hover:bg-blue-500/25 border border-blue-400/40 rounded-lg text-blue-100 text-center font-bold">
                                    ⬇️ تنزيل الموديل (.glb)
                                  </a>
                                  <a href={`https://gltf-viewer.donmccurdy.com/?model=${encodeURIComponent(fullUrl)}`}
                                     target="_blank" rel="noopener noreferrer"
                                     className="text-xs px-3 py-2 bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-400/40 rounded-lg text-cyan-100 text-center font-bold">
                                    🔍 معاينة 3D
                                  </a>
                                </div>
                              )}
                              {isVid && fullUrl && (
                                <video src={fullUrl} controls className="w-full max-w-md"
                                       data-testid={`generated-asset-${a.id}`} />
                              )}
                              {isAudio && fullUrl && (
                                <div className="p-3 flex flex-col gap-2" data-testid={`generated-asset-${a.id}`}>
                                  <div className="text-xs text-blue-300 font-bold">
                                    {a.type === 'music' ? '🎵 موسيقى خلفية' : '🔊 مؤثر صوتي'} · {a.duration_sec}s
                                  </div>
                                  <audio src={fullUrl} controls className="w-full" />
                                </div>
                              )}
                              <div className="px-3 py-2 flex items-center justify-between gap-2 bg-black/40">
                                <div className="text-xs text-zinc-400 truncate flex-1">
                                  <span className="text-blue-300 font-bold">{subtypeBadge}</span>
                                  <span className="mx-1">·</span>
                                  <span>{a.name?.slice(0, 60)}</span>
                                </div>
                                {!a.approved ? (
                                  <div className="flex gap-1.5 shrink-0">
                                    <button onClick={() => handleApproveAsset(a.id, true)}
                                      className="text-xs px-2.5 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-400/40 text-emerald-200 rounded-lg font-bold"
                                      data-testid={`approve-asset-${a.id}`}>✓ معتمد</button>
                                    <button onClick={() => {
                                        setMessage(`عدّل ${isImg ? 'الصورة' : is3D ? 'الموديل 3D' : isVid ? 'الفيديو' : 'الصوت'} السابق: `);
                                        handleApproveAsset(a.id, false);
                                      }}
                                      className="text-xs px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-400/40 text-amber-200 rounded-lg font-bold"
                                      data-testid={`iterate-asset-${a.id}`}>↻ عدّل</button>
                                  </div>
                                ) : (
                                  <span className="text-xs px-2 py-1 bg-emerald-500/20 border border-emerald-400/40 text-emerald-200 rounded-lg shrink-0">✓ معتمد</span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>
          )}

          <div className="border-t border-white/10 p-4 bg-zinc-900/50">
            {/* Quick Action Suggestions */}
            <QuickActions
              currentPhase={activePhase}
              accentColor="blue"
              onSelect={(prompt) => setMessage(prompt)}
            />

            {attachments.length > 0 && (
              <div className="mb-3 flex gap-2 flex-wrap">
                {attachments.map((file, i) => (
                  <div key={i} className="px-3 py-2 bg-blue-500/10 border border-blue-500/30 rounded-lg flex items-center gap-2 text-sm">
                    <Paperclip className="w-4 h-4" />
                    <span>{file.name}</span>
                    <button onClick={() => setAttachments(attachments.filter((_, j) => j !== i))}>
                      <X className="w-4 h-4 hover:text-red-400" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-2 sm:gap-3">
              <input type="file" ref={fileInputRef} multiple
                     onChange={e => setAttachments([...attachments, ...Array.from(e.target.files)])}
                     className="hidden" />
              <button onClick={() => fileInputRef.current?.click()}
                      className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl"
                      data-testid="attach-file-btn"
                      title="أرفق ملف">
                <Paperclip className="w-5 h-5" />
              </button>
              <VoiceRecorderButton
                accentColor="blue"
                disabled={loading}
                onTranscript={(text) => setMessage((m) => (m ? `${m.trim()} ${text}` : text))}
              />
              <input
                type="text"
                placeholder="اكتب أو سجّل صوت..."
                value={message}
                onChange={e => setMessage(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-3 outline-none focus:border-blue-400"
                data-testid="chat-input"
              />
              <button
                onClick={handleSendMessage}
                disabled={loading || (!message.trim() && attachments.length === 0)}
                className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-400 hover:to-purple-500 disabled:from-zinc-700 disabled:to-zinc-800 text-white font-bold rounded-xl flex items-center gap-2"
                data-testid="chat-send-btn">
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </div>

        {/* Assets */}
        <div className="w-80 bg-zinc-900/50 border-r border-white/10 p-4 overflow-y-auto">
          <h2 className="font-bold mb-3 text-blue-400">🎨 الأصول</h2>
          {Object.entries(allAssets).map(([type, assets]) => {
            if (assets.length === 0) return null;
            return (
              <div key={type} className="mb-4">
                <div className="text-sm font-bold text-zinc-400 mb-2">{type}</div>
                <div className="space-y-2">
                  {assets.map(asset => (
                    <div key={asset.id} className={`p-3 rounded-lg border ${
                      asset.approved ? 'bg-green-500/10 border-green-500/30' : 'bg-black/20 border-white/10'
                    }`}>
                      <div className="text-sm font-bold mb-1">{asset.name}</div>
                      <div className="text-xs text-zinc-500 mb-2">{asset.description}</div>
                      {!asset.approved && (
                        <div className="flex gap-2">
                          <button onClick={() => handleApproveAsset(asset.id, true)}
                                  className="flex-1 px-2 py-1 bg-green-500/20 border border-green-500/30 rounded text-xs hover:bg-green-500/30">
                            ✓ اعتماد
                          </button>
                          <button onClick={() => handleApproveAsset(asset.id, false)}
                                  className="flex-1 px-2 py-1 bg-red-500/20 border border-red-500/30 rounded text-xs hover:bg-red-500/30">
                            ✗ رفض
                          </button>
                        </div>
                      )}
                      {asset.approved && (
                        <div className="text-xs text-green-400 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>معتمد</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
          {Object.values(allAssets).every(arr => arr.length === 0) && (
            <div className="text-center text-zinc-600 text-sm mt-8">لا توجد أصول</div>
          )}
        </div>
      </div>
      {lightbox && (
        <ImageLightbox
          src={lightbox.src}
          alt={lightbox.alt}
          downloadName={`${(lightbox.alt || 'asset').slice(0, 40).replace(/\s+/g, '_')}.png`}
          onClose={() => setLightbox(null)}
        />
      )}

      {/* My Projects Modal — visible from chat step */}
      <MyProjectsModal
        open={myProjectsOpen}
        onClose={() => setMyProjectsOpen(false)}
        accentColor="blue"
      />
    </div>
  );
}
