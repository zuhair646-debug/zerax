/**
 * Zerax Companion — Mobile-first PWA page.
 * Route: /companion
 *
 * Flow:
 *   - If no profile → onboarding wizard (collects info conversationally)
 *   - Else: Chat with Zara/Layla (personalized)
 *
 * Features:
 *   - Bottom tab nav: 💬 محادثة | ⏰ منبّهات | 👤 ملفّي
 *   - Polls /api/companion/pending every 60s for proactive messages + due reminders
 *   - Shows browser notification when page is focused (if permission granted)
 *   - PWA install prompt banner
 */
import React, { useState, useEffect, useRef, useCallback, lazy, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Loader2, User, MessageCircle, Bell, Plus, Trash2, Settings, LogOut, Share2, Mic, Upload, X } from 'lucide-react';
import { toast } from 'sonner';
import ChatInput from '@/components/ChatInput';

const VoiceStage = lazy(() => import('@/components/VoiceStage'));

const API = process.env.REACT_APP_BACKEND_URL;
const POLL_INTERVAL = 60_000; // 1 min

const AGE_GROUPS = [
  { id: 'teen',        label: 'مراهق (13-19)' },
  { id: 'young_adult', label: 'شاب/شابة (20-30)' },
  { id: 'adult',       label: 'بالغ (31-50)' },
  { id: 'senior',      label: 'كبير سن (51+)' },
];

const ROLES = [
  { id: 'student',    label: '📚 طالب/طالبة' },
  { id: 'employee',   label: '💼 موظف/موظفة' },
  { id: 'freelancer', label: '🎨 مستقل/حر' },
  { id: 'parent',     label: '👨‍👩‍👧 ربة/رب أسرة' },
  { id: 'mixed',      label: '🔀 مشترك' },
  { id: 'other',      label: '✨ غير ذلك' },
];

export default function Companion() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const [tab, setTab] = useState('chat'); // 'chat' | 'reminders' | 'profile'
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [reminders, setReminders] = useState([]);
  const [reminderForm, setReminderForm] = useState({ title: '', body: '', trigger_at: '', repeat: 'none' });
  const [onboardingStep, setOnboardingStep] = useState(0);
  const [installPromptShown, setInstallPromptShown] = useState(false);
  const [voiceOpen, setVoiceOpen] = useState(false);
  const scrollRef = useRef(null);
  const deferredPromptRef = useRef(null);

  const tokenH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

  useEffect(() => {
    if (!localStorage.getItem('token')) { navigate('/login'); return; }
    loadProfile();
    // PWA install prompt
    const onBeforeInstall = (e) => {
      e.preventDefault();
      deferredPromptRef.current = e;
      setInstallPromptShown(true);
    };
    window.addEventListener('beforeinstallprompt', onBeforeInstall);
    // Register SW
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw-companion.js').catch(() => {});
    }
    // Add manifest link
    let link = document.querySelector('link[rel="manifest"]');
    if (!link) {
      link = document.createElement('link');
      link.rel = 'manifest';
      link.href = '/manifest-companion.json';
      document.head.appendChild(link);
    }
    // Request notification permission softly
    if ('Notification' in window && Notification.permission === 'default') {
      setTimeout(() => { try { Notification.requestPermission(); } catch (_) {} }, 10000);
    }
    return () => window.removeEventListener('beforeinstallprompt', onBeforeInstall);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  // Poll for proactive + reminders
  const pollPending = useCallback(async () => {
    if (!profile) return;
    try {
      const r = await fetch(`${API}/api/companion/pending`, { headers: tokenH() });
      if (!r.ok) return;
      const d = await r.json();
      const newMsgs = [];
      (d.proactive || []).forEach(m => {
        newMsgs.push({ role: 'assistant', content: m.message, id: m.id, char: m.from_char, kind: m.kind, proactive: true });
        if ('Notification' in window && Notification.permission === 'granted' && document.hidden) {
          try { new Notification(profile.preferred_avatar === 'zara' ? 'زارا' : 'ليلى', { body: m.message, icon: `/avatars/${m.from_char === 'zara' ? 'f1_zara' : 'f2_layla'}.png` }); } catch (_) {}
        }
      });
      (d.reminders_due || []).forEach(r => {
        const msg = `⏰ ${r.title}${r.body ? ' — ' + r.body : ''}`;
        newMsgs.push({ role: 'assistant', content: msg, id: r.id, kind: 'reminder' });
        if ('Notification' in window && Notification.permission === 'granted') {
          try { new Notification('⏰ منبّه', { body: r.title + (r.body ? ' — ' + r.body : '') }); } catch (_) {}
        }
      });
      if (newMsgs.length) setMessages(m => [...m, ...newMsgs]);
    } catch (_) { /* ignore */ }
  }, [profile]);

  useEffect(() => {
    if (!profile) return;
    pollPending();
    const id = setInterval(pollPending, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [profile, pollPending]);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/companion/profile`, { headers: tokenH() });
      if (r.ok) {
        const d = await r.json();
        if (d.has_profile) {
          setProfile(d.profile);
          setMessages([{
            role: 'assistant',
            content: `هلا ${d.profile.name || 'صديقي'}! 💛 رجعت لي — وش أخبارك اليوم؟`,
            char: d.profile.preferred_avatar || 'zara',
          }]);
          loadReminders();
        }
      }
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  const loadReminders = async () => {
    try {
      const r = await fetch(`${API}/api/companion/reminders`, { headers: tokenH() });
      if (r.ok) { const d = await r.json(); setReminders(d.reminders || []); }
    } catch (_) {}
  };



  const sendMessage = async ({ text, files }) => {
    if (!text.trim() || busy) return;
    const userMsg = { role: 'user', content: text };
    if (files.length > 0) {
      userMsg.attachments = files.map(f => f.name);
    }
    setMessages(m => [...m, userMsg]);
    setBusy(true);
    try {
      const formData = new FormData();
      formData.append('message', text);
      files.forEach(f => formData.append('files', f));

      const r = await fetch(`${API}/api/companion/chat`, {
        method: 'POST',
        headers: tokenH(),
        body: formData,
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setMessages(m => [...m, { role: 'assistant', content: d.reply, char: d.from_char }]);
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const promptInstall = async () => {
    if (!deferredPromptRef.current) return;
    deferredPromptRef.current.prompt();
    const choice = await deferredPromptRef.current.userChoice;
    if (choice.outcome === 'accepted') {
      toast.success('✓ تم إضافة التطبيق للجوال');
    }
    setInstallPromptShown(false);
  };

  const saveProfile = async (updates) => {
    try {
      const r = await fetch(`${API}/api/companion/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...tokenH() },
        body: JSON.stringify(updates),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setProfile(d.profile);
      return true;
    } catch (e) { toast.error(e.message); return false; }
  };

  const addReminder = async () => {
    if (!reminderForm.title.trim() || !reminderForm.trigger_at) {
      toast.error('العنوان والوقت مطلوبين'); return;
    }
    try {
      const r = await fetch(`${API}/api/companion/reminders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenH() },
        body: JSON.stringify({
          ...reminderForm,
          trigger_at: new Date(reminderForm.trigger_at).toISOString(),
        }),
      });
      if (!r.ok) { const d = await r.json(); throw new Error(d.detail); }
      toast.success('✓ تم الحفظ');
      setReminderForm({ title: '', body: '', trigger_at: '', repeat: 'none' });
      loadReminders();
    } catch (e) { toast.error(e.message); }
  };

  const deleteReminder = async (id) => {
    await fetch(`${API}/api/companion/reminders/${id}`, { method: 'DELETE', headers: tokenH() });
    loadReminders();
  };

  const triggerProactive = async () => {
    try {
      await fetch(`${API}/api/companion/trigger-proactive`, { method: 'POST', headers: tokenH() });
      toast.success('تم — ستظهر بعد قليل');
      setTimeout(pollPending, 1000);
    } catch (e) { toast.error('فشل'); }
  };

  if (loading) return (
    <div className="min-h-screen bg-[#0a0a12] flex items-center justify-center text-white">جاري التحميل...</div>
  );

  // Onboarding if no profile
  if (!profile) return <OnboardingWizard onDone={loadProfile} saveProfile={saveProfile} step={onboardingStep} setStep={setOnboardingStep} />;

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a12] via-[#0f0f1e] to-[#0a0a12] text-white flex flex-col" dir="rtl" data-testid="companion-page">
      {/* PWA install banner */}
      {installPromptShown && (
        <div className="bg-gradient-to-r from-amber-500/90 to-yellow-500/90 text-black px-3 py-2 text-xs flex items-center justify-between" data-testid="pwa-install-banner">
          <span className="font-black">📱 ثبّت Zerax كتطبيق على جوالك</span>
          <div className="flex gap-2">
            <button onClick={promptInstall} className="px-3 py-1 bg-black text-amber-300 rounded-full font-black" data-testid="pwa-install-btn">ثبّت</button>
            <button onClick={() => setInstallPromptShown(false)} className="text-black/70">✕</button>
          </div>
        </div>
      )}

      {/* Top bar */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-white/5 bg-black/40 backdrop-blur">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-amber-400/50">
            <img src={`/avatars/${profile.preferred_avatar === 'layla' ? 'f2_layla' : 'f1_zara'}.png`} alt="" className="w-full h-full object-cover object-top" />
          </div>
          <div>
            <div className="text-sm font-black">{profile.preferred_avatar === 'layla' ? 'ليلى' : 'زارا'}</div>
            <div className="text-[10px] text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" /> متصلة دائماً
            </div>
          </div>
        </div>
        <button onClick={triggerProactive} className="text-xs px-3 py-1.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-400/30 font-bold" data-testid="trigger-proactive-btn">
          اهتمي فيّ ✨
        </button>
        <button onClick={() => setVoiceOpen(true)} className="text-xs px-3 py-1.5 rounded-full bg-gradient-to-r from-amber-500 to-yellow-500 text-black font-black flex items-center gap-1" data-testid="companion-voice-btn">
          <Mic className="w-3.5 h-3.5" /> صوت
        </button>
      </div>

      {/* Content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {tab === 'chat' && (
          <>
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="companion-chat">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {m.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full overflow-hidden border border-amber-400/30 me-2 flex-shrink-0 mt-1">
                      <img src={`/avatars/${m.char === 'layla' ? 'f2_layla' : 'f1_zara'}.png`} alt="" className="w-full h-full object-cover object-top" />
                    </div>
                  )}
                  <div className={`max-w-[78%] px-3 py-2 rounded-2xl text-sm ${
                    m.role === 'user'
                      ? 'bg-amber-500/20 border border-amber-400/30'
                      : m.proactive
                        ? 'bg-gradient-to-br from-purple-500/20 to-pink-500/10 border border-purple-400/30'
                        : m.kind === 'reminder'
                          ? 'bg-blue-500/15 border border-blue-400/30'
                          : 'bg-white/5 border border-white/10'
                  }`}>
                    {m.proactive && <div className="text-[9px] text-purple-300 font-black mb-1">✨ مبادرة منها</div>}
                    <div className="whitespace-pre-wrap">{m.content}</div>
                  </div>
                </div>
              ))}
              {busy && (
                <div className="flex justify-start">
                  <div className="px-3 py-2 rounded-2xl bg-white/5 border border-white/10">
                    <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
                  </div>
                </div>
              )}
            </div>
            <div className="border-t border-white/5">
              {attachments.length > 0 && (
                <div className="p-2 flex flex-wrap gap-1.5">
                  {attachments.map((file, i) => (
                    <div key={i} className="flex items-center gap-1 px-2 py-1 bg-white/5 rounded text-xs">
                      <span className="truncate max-w-[120px]">{file.name}</span>
                      <button onClick={() => removeAttachment(i)} className="text-red-400 hover:text-red-300">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <div className="p-3 flex gap-2">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-10 h-10 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center"
                  title="إرفاق ملف">
                  <Upload className="w-4 h-4" />
                </button>
                <button
                  onClick={recording ? stopRecording : startRecording}
                  className={`w-10 h-10 rounded-full flex items-center justify-center ${recording ? 'bg-red-500/20 text-red-400' : 'bg-white/5 hover:bg-white/10'}`}
                  title={recording ? 'إيقاف التسجيل' : 'تسجيل صوتي'}>
                  <Mic className="w-4 h-4" />
                </button>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') sendMessage(); }}
                  placeholder="اكتب لها..."
                  className="flex-1 px-4 py-3 bg-black/40 border border-white/10 focus:border-amber-400 rounded-full text-sm outline-none"
                  data-testid="companion-input"
                />
                <button onClick={sendMessage} disabled={busy || !input.trim()}
                  className="w-12 h-12 rounded-full bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center text-black disabled:opacity-50"
                  data-testid="companion-send">
                  <Send className="w-5 h-5" />
                </button>
                <input type="file" multiple ref={fileInputRef} onChange={handleFileSelect} className="hidden" />
              </div>
            </div>
          </>
        )}

        {tab === 'reminders' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="companion-reminders">
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 space-y-2">
              <div className="text-sm font-black flex items-center gap-1.5"><Plus className="w-4 h-4" /> منبّه جديد</div>
              <input value={reminderForm.title} onChange={(e) => setReminderForm(f => ({ ...f, title: e.target.value }))}
                placeholder="اسم المنبّه"
                className="w-full p-2 bg-black/40 border border-white/10 rounded-lg text-sm outline-none"
                data-testid="reminder-title" />
              <input type="datetime-local" value={reminderForm.trigger_at} onChange={(e) => setReminderForm(f => ({ ...f, trigger_at: e.target.value }))}
                className="w-full p-2 bg-black/40 border border-white/10 rounded-lg text-sm outline-none"
                data-testid="reminder-time" />
              <select value={reminderForm.repeat} onChange={(e) => setReminderForm(f => ({ ...f, repeat: e.target.value }))}
                className="w-full p-2 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="reminder-repeat">
                <option value="none">لمرة واحدة</option>
                <option value="daily">يومياً</option>
                <option value="weekly">أسبوعياً</option>
              </select>
              <button onClick={addReminder} className="w-full py-2 rounded-lg bg-amber-500 text-black font-black text-sm" data-testid="reminder-add-btn">إضافة</button>
            </div>
            {reminders.length === 0 ? (
              <div className="text-center text-white/50 text-sm py-4">ما عندك منبّهات بعد</div>
            ) : (
              reminders.map(r => (
                <div key={r.id} className="p-3 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between" data-testid={`reminder-${r.id}`}>
                  <div>
                    <div className="text-sm font-bold">⏰ {r.title}</div>
                    <div className="text-[10px] text-white/60">{new Date(r.trigger_at).toLocaleString('ar-SA')} · {r.repeat === 'daily' ? 'يومياً' : r.repeat === 'weekly' ? 'أسبوعياً' : 'مرة'}</div>
                  </div>
                  <button onClick={() => deleteReminder(r.id)} className="text-red-400 p-1" data-testid={`reminder-del-${r.id}`}>
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {tab === 'profile' && (
          <ProfileEditor profile={profile} saveProfile={saveProfile} navigate={navigate} />
        )}
      </div>

      {/* Bottom tab nav */}
      <div className="grid grid-cols-3 border-t border-white/10 bg-black/60 backdrop-blur">
        <button onClick={() => setTab('chat')} className={`py-3 flex flex-col items-center gap-0.5 text-[10px] ${tab === 'chat' ? 'text-amber-400' : 'text-white/50'}`} data-testid="tab-chat">
          <MessageCircle className="w-5 h-5" /> محادثة
        </button>
        <button onClick={() => setTab('reminders')} className={`py-3 flex flex-col items-center gap-0.5 text-[10px] ${tab === 'reminders' ? 'text-amber-400' : 'text-white/50'}`} data-testid="tab-reminders">
          <Bell className="w-5 h-5" /> منبّهات
        </button>
        <button onClick={() => setTab('profile')} className={`py-3 flex flex-col items-center gap-0.5 text-[10px] ${tab === 'profile' ? 'text-amber-400' : 'text-white/50'}`} data-testid="tab-profile">
          <User className="w-5 h-5" /> ملفّي
        </button>
      </div>

      {/* Voice Stage overlay (companion mode) */}
      {voiceOpen && (
        <Suspense fallback={<div className="fixed inset-0 z-[100] bg-black/80 flex items-center justify-center text-white">جاري التحميل...</div>}>
          <VoiceStage
            open={voiceOpen}
            onClose={() => setVoiceOpen(false)}
            initialCharacter={profile.preferred_avatar || 'zara'}
            mode="companion"
          />
        </Suspense>
      )}
    </div>
  );
}

// ====================== ONBOARDING WIZARD ======================
function OnboardingWizard({ onDone, saveProfile, step, setStep }) {
  const [data, setData] = useState({
    preferred_avatar: 'zara', name: '', age_group: '', role: '',
    wake_time: '07:00', sleep_time: '23:00',
    goals: [], study_subjects: [], work_info: '', interests: [],
    family: '', kids_count: 0, location_city: '', diet: '',
    exam_dates: [],
    timezone_offset: 3,
  });

  const steps = [
    {
      title: 'اختر رفيقتك',
      render: () => (
        <div className="grid grid-cols-2 gap-3" data-testid="onb-avatar-picker">
          {[{ id: 'zara', name: 'زارا', emoji: '💛', desc: 'مرحة حماسية' }, { id: 'layla', name: 'ليلى', emoji: '🖤', desc: 'أنيقة هادئة' }].map(a => (
            <button key={a.id} onClick={() => setData(d => ({ ...d, preferred_avatar: a.id }))}
              className={`p-4 rounded-2xl border-2 ${data.preferred_avatar === a.id ? 'border-amber-400 bg-amber-500/10' : 'border-white/10 bg-white/5'}`}
              data-testid={`onb-avatar-${a.id}`}>
              <img src={`/avatars/${a.id === 'zara' ? 'f1_zara' : 'f2_layla'}.png`} alt="" className="w-24 h-24 mx-auto rounded-full object-cover mb-2" />
              <div className="font-black text-white">{a.name} {a.emoji}</div>
              <div className="text-[10px] text-white/60">{a.desc}</div>
            </button>
          ))}
        </div>
      ),
      canNext: true,
    },
    {
      title: 'شنو اسمك؟',
      render: () => (
        <input value={data.name} onChange={(e) => setData(d => ({ ...d, name: e.target.value }))}
          placeholder="اسمك"
          className="w-full p-3 bg-black/40 border border-white/10 rounded-lg text-center text-xl text-white outline-none"
          data-testid="onb-name" />
      ),
      canNext: () => data.name.trim().length > 0,
    },
    {
      title: 'فئتك العمرية؟',
      render: () => (
        <div className="space-y-2">
          {AGE_GROUPS.map(a => (
            <button key={a.id} onClick={() => setData(d => ({ ...d, age_group: a.id }))}
              className={`w-full p-3 rounded-xl border text-right ${data.age_group === a.id ? 'bg-amber-500/20 border-amber-400 text-amber-300' : 'bg-white/5 border-white/10 text-white'}`}
              data-testid={`onb-age-${a.id}`}>{a.label}</button>
          ))}
        </div>
      ),
      canNext: () => !!data.age_group,
    },
    {
      title: 'وضعك الحالي؟',
      render: () => (
        <div className="grid grid-cols-2 gap-2">
          {ROLES.map(a => (
            <button key={a.id} onClick={() => setData(d => ({ ...d, role: a.id }))}
              className={`p-3 rounded-xl border text-sm ${data.role === a.id ? 'bg-amber-500/20 border-amber-400' : 'bg-white/5 border-white/10'}`}
              data-testid={`onb-role-${a.id}`}>{a.label}</button>
          ))}
        </div>
      ),
      canNext: () => !!data.role,
    },
    {
      title: 'أوقاتك اليومية',
      render: () => (
        <div className="space-y-3">
          <div>
            <label className="text-xs text-white/70">تصحى الساعة</label>
            <input type="time" value={data.wake_time} onChange={(e) => setData(d => ({ ...d, wake_time: e.target.value }))}
              className="w-full p-3 bg-black/40 border border-white/10 rounded-lg text-white outline-none" data-testid="onb-wake" />
          </div>
          <div>
            <label className="text-xs text-white/70">تنام الساعة</label>
            <input type="time" value={data.sleep_time} onChange={(e) => setData(d => ({ ...d, sleep_time: e.target.value }))}
              className="w-full p-3 bg-black/40 border border-white/10 rounded-lg text-white outline-none" data-testid="onb-sleep" />
          </div>
        </div>
      ),
      canNext: true,
    },
    {
      title: 'معلومات إضافية (اختياري)',
      render: () => (
        <div className="space-y-2">
          <input value={data.location_city} onChange={(e) => setData(d => ({ ...d, location_city: e.target.value }))}
            placeholder="مدينتك" className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="onb-city" />
          <input value={data.work_info} onChange={(e) => setData(d => ({ ...d, work_info: e.target.value }))}
            placeholder="شغلك (اختياري)" className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="onb-work" />
          <input value={data.study_subjects.join(', ')} onChange={(e) => setData(d => ({ ...d, study_subjects: e.target.value.split(',').map(s => s.trim()).filter(Boolean) }))}
            placeholder="المواد اللي تدرسها (مفصولة بفاصلة)" className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="onb-subjects" />
          <input value={data.goals.join(', ')} onChange={(e) => setData(d => ({ ...d, goals: e.target.value.split(',').map(s => s.trim()).filter(Boolean) }))}
            placeholder="أهدافك (مثل: نحفان، تعلم برمجة...)" className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="onb-goals" />
          <input value={data.interests.join(', ')} onChange={(e) => setData(d => ({ ...d, interests: e.target.value.split(',').map(s => s.trim()).filter(Boolean) }))}
            placeholder="اهتماماتك (مثل: قراءة، ألعاب، رياضة...)" className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="onb-interests" />
        </div>
      ),
      canNext: true,
    },
  ];

  const current = steps[step];
  const canNext = typeof current.canNext === 'function' ? current.canNext() : current.canNext;

  const next = async () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      const ok = await saveProfile(data);
      if (ok) onDone();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a12] via-[#1a0f1f] to-[#0a0a12] text-white flex flex-col" dir="rtl" data-testid="companion-onboarding">
      <div className="p-4">
        <div className="flex gap-1 mb-4">
          {steps.map((_, i) => (
            <div key={i} className={`flex-1 h-1 rounded-full ${i <= step ? 'bg-amber-400' : 'bg-white/10'}`} />
          ))}
        </div>
        <h2 className="text-2xl font-black text-center mb-6">{current.title}</h2>
      </div>
      <div className="flex-1 px-4 overflow-y-auto">
        {current.render()}
      </div>
      <div className="p-4 border-t border-white/5">
        <button onClick={next} disabled={!canNext}
          className="w-full h-12 rounded-full bg-gradient-to-r from-amber-500 to-yellow-500 text-black font-black disabled:opacity-40"
          data-testid="onb-next">
          {step < steps.length - 1 ? 'التالي ←' : '✨ ابدأ معاي'}
        </button>
      </div>
    </div>
  );
}

// ====================== PROFILE EDITOR ======================
function ProfileEditor({ profile, saveProfile, navigate }) {
  const [name, setName] = useState(profile.name || '');
  const [wake, setWake] = useState(profile.wake_time || '07:00');
  const [sleep, setSleep] = useState(profile.sleep_time || '23:00');
  const [avatar, setAvatar] = useState(profile.preferred_avatar || 'zara');
  const [goals, setGoals] = useState((profile.goals || []).join(', '));
  const [interests, setInterests] = useState((profile.interests || []).join(', '));
  const [subjects, setSubjects] = useState((profile.study_subjects || []).join(', '));
  const [work, setWork] = useState(profile.work_info || '');
  const [city, setCity] = useState(profile.location_city || '');
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    await saveProfile({
      name, wake_time: wake, sleep_time: sleep, preferred_avatar: avatar,
      goals: goals.split(',').map(s => s.trim()).filter(Boolean),
      interests: interests.split(',').map(s => s.trim()).filter(Boolean),
      study_subjects: subjects.split(',').map(s => s.trim()).filter(Boolean),
      work_info: work, location_city: city,
    });
    setBusy(false);
    toast.success('✓ تم الحفظ');
  };

  const shareApp = () => {
    const url = window.location.origin + '/companion';
    if (navigator.share) {
      navigator.share({ title: 'Zerax Companion', text: 'رفيقتي الذكية — جربها!', url });
    } else {
      navigator.clipboard.writeText(url);
      toast.success('تم نسخ الرابط');
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="companion-profile">
      <div className="p-4 rounded-2xl bg-white/5 border border-white/10 space-y-3">
        <div>
          <label className="text-xs text-white/70">اسمك</label>
          <input value={name} onChange={(e) => setName(e.target.value)}
            className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="prof-name" />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div><label className="text-xs text-white/70">تصحى</label>
            <input type="time" value={wake} onChange={(e) => setWake(e.target.value)}
              className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="prof-wake" /></div>
          <div><label className="text-xs text-white/70">تنام</label>
            <input type="time" value={sleep} onChange={(e) => setSleep(e.target.value)}
              className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="prof-sleep" /></div>
        </div>
        <div>
          <label className="text-xs text-white/70 block mb-1">رفيقتك المفضلة</label>
          <div className="grid grid-cols-2 gap-2">
            {['zara', 'layla'].map(a => (
              <button key={a} onClick={() => setAvatar(a)}
                className={`p-2 rounded-lg border text-sm ${avatar === a ? 'bg-amber-500/20 border-amber-400' : 'bg-white/5 border-white/10'}`}
                data-testid={`prof-avatar-${a}`}>
                {a === 'zara' ? 'زارا 💛' : 'ليلى 🖤'}
              </button>
            ))}
          </div>
        </div>
        <input value={city} onChange={(e) => setCity(e.target.value)} placeholder="المدينة"
          className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="prof-city" />
        <input value={work} onChange={(e) => setWork(e.target.value)} placeholder="الشغل"
          className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="prof-work" />
        <input value={subjects} onChange={(e) => setSubjects(e.target.value)} placeholder="المواد الدراسية"
          className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="prof-subjects" />
        <input value={goals} onChange={(e) => setGoals(e.target.value)} placeholder="الأهداف"
          className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="prof-goals" />
        <input value={interests} onChange={(e) => setInterests(e.target.value)} placeholder="الاهتمامات"
          className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="prof-interests" />
        <button onClick={save} disabled={busy}
          className="w-full py-2.5 rounded-lg bg-amber-500 text-black font-black text-sm disabled:opacity-50" data-testid="prof-save">
          {busy ? 'جارٍ الحفظ...' : '💾 حفظ'}
        </button>
      </div>
      <button onClick={shareApp} className="w-full py-2.5 rounded-lg bg-white/5 border border-white/10 text-white font-bold text-sm flex items-center justify-center gap-2" data-testid="prof-share">
        <Share2 className="w-4 h-4" /> شاركها مع صديق
      </button>
      <button onClick={() => navigate('/dashboard')} className="w-full py-2.5 rounded-lg bg-white/5 border border-white/10 text-white/70 font-bold text-sm flex items-center justify-center gap-2" data-testid="prof-back">
        <Settings className="w-4 h-4" /> الرجوع للوحة الرئيسية
      </button>
      <button onClick={() => { localStorage.removeItem('token'); navigate('/login'); }} className="w-full py-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 font-bold text-sm flex items-center justify-center gap-2" data-testid="prof-logout">
        <LogOut className="w-4 h-4" /> خروج
      </button>
    </div>
  );
}
