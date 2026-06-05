import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Smartphone, Send, Paperclip, Loader2, Check, X, 
  Eye, Code, Image, FileText, Package, Sparkles,
  ArrowRight, Lock, Unlock, CheckCircle2
} from 'lucide-react';
import { toast } from 'sonner';

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
  
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Fetch programming types
  useEffect(() => {
    fetch(`${API}/api/games/programming-types?game_type=app`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(data => setProgrammingTypes(data.types || []))
      .catch(e => toast.error(e.message));
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
            <h2 className="text-xl font-bold mb-4">⚙️ اختر نوع البرمجة</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {programmingTypes.map(tech => (
                <button
                  key={tech.id}
                  onClick={() => setSelectedTech(tech.id)}
                  className={`p-4 rounded-xl border-2 transition-all text-right ${
                    selectedTech === tech.id
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-white/10 bg-black/20 hover:border-white/20'
                  }`}
                >
                  <div className="font-bold text-lg">{tech.name}</div>
                  <div className="text-sm text-zinc-400">{tech.desc}</div>
                  {selectedTech === tech.id && (
                    <div className="mt-2 flex items-center gap-2 text-blue-400">
                      <Check className="w-4 h-4" />
                      <span className="text-sm">محدد</span>
                    </div>
                  )}
                </button>
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
                <button
                  key={phase.id}
                  onClick={() => !isLocked && setActivePhase(phase.id)}
                  disabled={isLocked}
                  className={`w-full text-right p-3 rounded-lg border transition-all ${
                    isActive ? 'bg-blue-500/20 border-blue-500/50 text-blue-300' :
                    isLocked ? 'bg-black/20 border-white/5 text-zinc-600 cursor-not-allowed' :
                    'bg-black/20 border-white/10 hover:border-white/20'
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
                      onClick={(e) => { e.stopPropagation(); handleUnlockPhase(phase.id); }}
                      className="mt-2 w-full text-xs bg-blue-500/10 border border-blue-500/30 rounded px-2 py-1 hover:bg-blue-500/20">
                      🔓 فتح
                    </button>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Chat */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
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
                    <div className="text-sm whitespace-pre-wrap">{msg.assistant}</div>
                  </div>
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <div className="border-t border-white/10 p-4 bg-zinc-900/50">
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

            <div className="flex gap-3">
              <input type="file" ref={fileInputRef} multiple
                     onChange={e => setAttachments([...attachments, ...Array.from(e.target.files)])}
                     className="hidden" />
              <button onClick={() => fileInputRef.current?.click()}
                      className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl">
                <Paperclip className="w-5 h-5" />
              </button>
              <input
                type="text"
                placeholder="اكتب رسالتك..."
                value={message}
                onChange={e => setMessage(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-3 outline-none focus:border-blue-400"
              />
              <button
                onClick={handleSendMessage}
                disabled={loading || (!message.trim() && attachments.length === 0)}
                className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-400 hover:to-purple-500 disabled:from-zinc-700 disabled:to-zinc-800 text-white font-bold rounded-xl flex items-center gap-2">
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
    </div>
  );
}
