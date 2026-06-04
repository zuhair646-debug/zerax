import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { 
  ArrowLeft, Send, Loader2, Sparkles, Check, ChevronRight,
  Users, Map, Gamepad2, Code, TestTube, Rocket, Download,
  Package, Zap, Crown
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const PHASES = [
  { id: 'discovery', name: 'Discovery & GDD', icon: Sparkles, credits: 50 },
  { id: 'characters', name: 'Character Design', icon: Users, credits: 150 },
  { id: 'environments', name: 'Environment Design', icon: Map, credits: 200 },
  { id: 'gameplay', name: 'Gameplay Mechanics', icon: Gamepad2, credits: 100 },
  { id: 'assets', name: 'Assets Generation', icon: Package, credits: 100 },
  { id: 'programming', name: 'Programming', icon: Code, credits: 300 },
  { id: 'testing', name: 'Testing & QA', icon: TestTube, credits: 100 },
  { id: 'deployment', name: 'Build & Deploy', icon: Rocket, credits: 150 }
];

export default function AppGamesStudio({ user }) {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  const [project, setProject] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentPhase, setCurrentPhase] = useState(0);

  useEffect(() => {
    if (!user) {
      navigate('/login');
    }
  }, [user, navigate]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/game-studio/app/chat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: input,
          project_id: project?.id
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'فشل إرسال الرسالة');
      }

      // Update messages
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        phase: data.current_phase,
        artifacts: data.artifacts
      }]);

      // Update project state
      if (data.project) {
        setProject(data.project);
        const phaseIndex = PHASES.findIndex(p => p.id === data.current_phase);
        if (phaseIndex !== -1) setCurrentPhase(phaseIndex);
      }

      // Show credits deducted
      if (data.credits_deducted > 0) {
        toast.success(`تم خصم ${data.credits_deducted} نقطة`);
      }

    } catch (err) {
      toast.error(err.message);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ ${err.message}`
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (type) => {
    if (!project?.id) return;
    
    try {
      const res = await fetch(
        `${API}/api/game-studio/app/build?project_id=${project.id}&platform=${type}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'فشل البناء');
      }

      toast.success(`جاري بناء ${type.toUpperCase()}...`);
      
      // Poll build status every 5s
      const pollInterval = setInterval(async () => {
        const statusRes = await fetch(
          `${API}/api/game-studio/app/status/${data.job_id}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        const statusData = await statusRes.json();

        if (statusData.status === 'completed') {
          clearInterval(pollInterval);
          toast.success(`✅ ${type.toUpperCase()} جاهز للتحميل!`);
          window.open(statusData.download_url, '_blank');
        } else if (statusData.status === 'failed') {
          clearInterval(pollInterval);
          toast.error('فشل البناء، راجع الـlogs');
        }
      }, 5000);

    } catch (err) {
      toast.error(err.message);
    }
  };

  const renderArtifact = (artifact) => {
    if (!artifact) return null;

    switch (artifact.type) {
      case 'gdd':
        return (
          <div className="bg-black/40 border border-amber-500/30 rounded-xl p-6 my-4">
            <div className="flex items-center gap-3 mb-4">
              <Sparkles className="w-5 h-5 text-amber-400" />
              <h3 className="text-lg font-bold">Game Design Document</h3>
            </div>
            <div className="prose prose-invert max-w-none text-sm">
              <pre className="whitespace-pre-wrap text-zinc-300">{artifact.content}</pre>
            </div>
            <button
              onClick={() => {
                const blob = new Blob([artifact.content], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'GDD.txt';
                a.click();
              }}
              className="mt-4 px-4 py-2 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/50 rounded-lg transition-all flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              <span>تحميل GDD</span>
            </button>
          </div>
        );

      case 'character_preview':
        return (
          <div className="bg-black/40 border border-purple-500/30 rounded-xl p-6 my-4">
            <div className="flex items-center gap-3 mb-4">
              <Users className="w-5 h-5 text-purple-400" />
              <h3 className="text-lg font-bold">معاينة الشخصية</h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {artifact.previews?.map((url, i) => (
                <img
                  key={i}
                  src={url}
                  alt={`شخصية ${i + 1}`}
                  className="w-full rounded-lg border border-white/10"
                />
              ))}
            </div>
          </div>
        );

      case 'environment_preview':
        return (
          <div className="bg-black/40 border border-green-500/30 rounded-xl p-6 my-4">
            <div className="flex items-center gap-3 mb-4">
              <Map className="w-5 h-5 text-green-400" />
              <h3 className="text-lg font-bold">معاينة البيئة</h3>
            </div>
            <img
              src={artifact.preview_url}
              alt="Environment"
              className="w-full rounded-lg border border-white/10"
            />
          </div>
        );

      case 'code_snippet':
        return (
          <div className="bg-black/40 border border-blue-500/30 rounded-xl p-6 my-4">
            <div className="flex items-center gap-3 mb-4">
              <Code className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-bold">{artifact.title || 'Code'}</h3>
            </div>
            <pre className="bg-black/60 p-4 rounded-lg overflow-x-auto text-xs">
              <code className="text-green-400">{artifact.code}</code>
            </pre>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div dir="rtl" className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-zinc-900/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard/games')}
              className="p-2 hover:bg-white/5 rounded-lg transition-all"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <Crown className="w-6 h-6 text-amber-400" />
                Game Apps Studio
              </h1>
              <p className="text-sm text-zinc-400">
                إنشاء ألعاب احترافية للموبايل والـPC
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="px-4 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg">
              <span className="text-sm text-zinc-400">الرصيد:</span>
              <span className="ml-2 font-bold text-amber-400">{user?.balance || 0}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-12 gap-6">
          {/* Sidebar - Phase Progress */}
          <div className="col-span-3 space-y-4">
            <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl p-6">
              <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-400" />
                مراحل التطوير
              </h2>

              <div className="space-y-3">
                {PHASES.map((phase, index) => {
                  const Icon = phase.icon;
                  const isActive = index === currentPhase;
                  const isCompleted = index < currentPhase;

                  return (
                    <div
                      key={phase.id}
                      className={`p-3 rounded-xl border transition-all ${
                        isActive
                          ? 'bg-amber-500/20 border-amber-500/50'
                          : isCompleted
                          ? 'bg-green-500/10 border-green-500/30'
                          : 'bg-black/40 border-white/10'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Icon className={`w-4 h-4 ${
                            isActive ? 'text-amber-400' :
                            isCompleted ? 'text-green-400' :
                            'text-zinc-500'
                          }`} />
                          <span className={`text-sm font-medium ${
                            isActive ? 'text-white' :
                            isCompleted ? 'text-green-400' :
                            'text-zinc-400'
                          }`}>
                            {phase.name}
                          </span>
                        </div>
                        {isCompleted && <Check className="w-4 h-4 text-green-400" />}
                      </div>
                      <div className="text-xs text-zinc-500">
                        {phase.credits} نقطة
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Total Credits Estimate */}
              <div className="mt-6 pt-4 border-t border-white/10">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">التكلفة المتوقعة:</span>
                  <span className="font-bold text-amber-400">
                    {PHASES.reduce((sum, p) => sum + p.credits, 0)}+ نقطة
                  </span>
                </div>
              </div>
            </div>

            {/* Download Section */}
            {project?.status === 'completed' && (
              <div className="bg-gradient-to-br from-green-500/20 to-blue-500/20 border border-green-500/30 rounded-2xl p-6">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <Download className="w-5 h-5 text-green-400" />
                  تحميل اللعبة
                </h3>
                <div className="space-y-2">
                  <button
                    onClick={() => handleDownload('android')}
                    className="w-full px-4 py-3 bg-green-500/20 hover:bg-green-500/30 border border-green-500/50 rounded-lg transition-all text-sm font-medium"
                  >
                    📱 Android APK
                  </button>
                  <button
                    onClick={() => handleDownload('ios')}
                    className="w-full px-4 py-3 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/50 rounded-lg transition-all text-sm font-medium"
                  >
                    🍎 iOS IPA
                  </button>
                  <button
                    onClick={() => handleDownload('pc')}
                    className="w-full px-4 py-3 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/50 rounded-lg transition-all text-sm font-medium"
                  >
                    💻 PC Build
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Main Chat Area */}
          <div className="col-span-9">
            <div className="bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl h-[calc(100vh-12rem)] flex flex-col">
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.length === 0 && (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center max-w-md">
                      <Crown className="w-16 h-16 text-amber-400 mx-auto mb-4" />
                      <h3 className="text-2xl font-bold mb-2">
                        مرحباً بك في Game Apps Studio
                      </h3>
                      <p className="text-zinc-400 mb-6">
                        صف لنا اللعبة اللي تبي تسويها، وبنبدأ معك خطوة بخطوة من الفكرة لين النشر
                      </p>
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <button
                          onClick={() => setInput('أبي لعبة Battle Royale مثل Fortnite')}
                          className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-right"
                        >
                          🎮 Battle Royale
                        </button>
                        <button
                          onClick={() => setInput('أبي لعبة RPG خيالية')}
                          className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-right"
                        >
                          ⚔️ RPG
                        </button>
                        <button
                          onClick={() => setInput('أبي لعبة سباقات سيارات')}
                          className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-right"
                        >
                          🏎️ Racing
                        </button>
                        <button
                          onClick={() => setInput('أبي لعبة استراتيجية مثل Travian')}
                          className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-right"
                        >
                          🏰 Strategy
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${msg.role === 'user' ? 'justify-start' : 'justify-end'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl p-4 ${
                        msg.role === 'user'
                          ? 'bg-white/10 border border-white/20'
                          : 'bg-gradient-to-br from-amber-500/20 to-purple-500/20 border border-amber-500/30'
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                      
                      {/* Render artifacts */}
                      {msg.artifacts?.map((artifact, idx) => (
                        <div key={idx}>
                          {renderArtifact(artifact)}
                        </div>
                      ))}

                      {/* Phase indicator */}
                      {msg.phase && (
                        <div className="mt-3 pt-3 border-t border-white/10 flex items-center gap-2 text-xs text-amber-400">
                          <ChevronRight className="w-3 h-3" />
                          <span>المرحلة: {PHASES.find(p => p.id === msg.phase)?.name}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-end">
                    <div className="bg-gradient-to-br from-amber-500/20 to-purple-500/20 border border-amber-500/30 rounded-2xl p-4 flex items-center gap-3">
                      <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
                      <span className="text-sm">الذكاء يفكر...</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Input */}
              <div className="border-t border-white/10 p-4">
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="اكتب رسالتك..."
                    disabled={loading}
                    className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-3 focus:border-amber-400 outline-none transition-all disabled:opacity-50"
                  />
                  <button
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                    className="px-6 py-3 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-bold text-black transition-all flex items-center gap-2"
                  >
                    <Send className="w-5 h-5" />
                    <span>إرسال</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
