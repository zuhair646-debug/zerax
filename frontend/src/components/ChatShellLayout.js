import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Menu, Plus, MessageSquare, Gift, Sparkles, Coins,
  ChevronLeft, Settings, LogOut, X, Trash2, Search,
  Share2, Crown, Zap,
} from 'lucide-react';

/**
 * Unified Chat Shell (Emergent-style)
 * ─────────────────────────────────────────────────────
 * Provides:
 *   • Left sidebar: sessions list + new chat button + footer (user/credits)
 *   • Top bar: title + referral discount badge + gift badge + balance
 *   • Center: caller's chat content (children)
 *
 * Props:
 *   title                — section name (e.g. "إنشاء المواقع")
 *   sessions             — [{ id, title, preview, updated_at, ... }]
 *   activeId             — currently selected session id
 *   onSelect(id)         — when user clicks a session
 *   onNewChat()          — when user clicks "محادثة جديدة"
 *   onDelete(id)         — optional delete handler
 *   credits              — number to display in topbar pill
 *   referralCode         — string, shown in gift popup
 *   children             — main chat content
 *   rightExtras          — optional ReactNode for top right (e.g. action buttons)
 */
export default function ChatShellLayout({
  title = 'محادثة',
  sessions = [],
  activeId = '',
  onSelect = () => {},
  onNewChat = () => {},
  onDelete,
  credits = 0,
  referralCode = '',
  children,
  rightExtras = null,
  emptyHint = 'ابدأ محادثة جديدة',
}) {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showGift, setShowGift] = useState(false);
  const [showReferral, setShowReferral] = useState(false);
  const [search, setSearch] = useState('');
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    // Fetch lightweight user info for the footer
    const token = localStorage.getItem('token');
    if (!token) return;
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setProfile(d.user || d))
      .catch(() => {});
  }, []);

  const filtered = search
    ? sessions.filter((s) => (s.title || '').toLowerCase().includes(search.toLowerCase()))
    : sessions;

  const shareReferral = async () => {
    const url = `${window.location.origin}/?ref=${referralCode || profile?.id || ''}`;
    try {
      if (navigator.share) {
        await navigator.share({
          title: 'انضم لـZitex واحصل على خصم',
          text: 'سجّل عبر رابطي واحصل على خصم ٢٠٪ على أول اشتراك',
          url,
        });
      } else {
        await navigator.clipboard.writeText(url);
        alert('تم نسخ الرابط ✅');
      }
    } catch (_) { /* user cancelled */ }
  };

  return (
    <div className="min-h-screen bg-[#06060f] text-white flex" dir="rtl" data-testid="chat-shell">
      {/* ── SIDEBAR ─────────────────────────────────────────── */}
      {sidebarOpen && (
        <aside className="w-72 border-l border-white/10 bg-[#0a0a14]/80 backdrop-blur-md flex flex-col shrink-0" data-testid="chat-shell-sidebar">
          {/* Logo / Section title */}
          <div className="p-4 border-b border-white/10 flex items-center justify-between">
            <button onClick={() => navigate('/dashboard')} className="flex items-center gap-2 hover:text-cyan-300" data-testid="shell-home-btn">
              <ChevronLeft className="w-4 h-4" />
              <span className="font-bold text-sm">{title}</span>
            </button>
            <button onClick={() => setSidebarOpen(false)} className="p-1.5 hover:bg-white/5 rounded lg:hidden" data-testid="shell-close-sidebar">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* New chat */}
          <button onClick={onNewChat}
            className="m-3 px-3 py-2.5 bg-gradient-to-l from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 rounded-lg text-sm font-bold text-white flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20"
            data-testid="shell-new-chat-btn">
            <Plus className="w-4 h-4" /> محادثة جديدة
          </button>

          {/* Search */}
          {sessions.length > 4 && (
            <div className="mx-3 mb-2 relative">
              <Search className="w-3.5 h-3.5 absolute right-2.5 top-1/2 -translate-y-1/2 text-white/40" />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="ابحث…"
                className="w-full bg-white/5 border border-white/10 rounded-md py-1.5 pr-8 pl-2 text-xs outline-none focus:border-cyan-400/40"
                data-testid="shell-search-input" />
            </div>
          )}

          {/* Sessions list */}
          <div className="flex-1 overflow-y-auto px-2 pb-2">
            <div className="text-[10px] text-white/40 px-2 pb-1.5 uppercase tracking-wider">
              المحادثات ({sessions.length})
            </div>
            {filtered.length === 0 && (
              <div className="text-xs text-white/30 px-2 py-8 text-center leading-6">
                {emptyHint}
              </div>
            )}
            {filtered.map((s) => (
              <div key={s.id}
                className={`group relative mb-1 rounded-lg transition ${
                  activeId === s.id
                    ? 'bg-cyan-500/15 border border-cyan-400/30'
                    : 'hover:bg-white/[0.04] border border-transparent'
                }`}
                data-testid={`shell-session-${s.id}`}>
                <button onClick={() => onSelect(s.id)}
                  className="w-full text-right px-2.5 py-2 flex items-start gap-2">
                  <MessageSquare className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${activeId === s.id ? 'text-cyan-300' : 'text-white/40'}`} />
                  <div className="flex-1 min-w-0">
                    <div className={`text-xs font-medium truncate ${activeId === s.id ? 'text-cyan-100' : 'text-white/80'}`}>
                      {s.title || s.preview || 'بدون عنوان'}
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {s.turns !== undefined && <span className="text-[9px] text-white/30">{s.turns} جولة</span>}
                      {s.complete && <span className="text-[9px] bg-emerald-500/15 text-emerald-300 px-1 rounded">✓</span>}
                      {s.published && <span className="text-[9px] bg-amber-500/15 text-amber-300 px-1 rounded">منشور</span>}
                    </div>
                  </div>
                </button>
                {onDelete && (
                  <button onClick={(e) => { e.stopPropagation(); onDelete(s.id); }}
                    className="absolute top-1/2 -translate-y-1/2 left-1 p-1 opacity-0 group-hover:opacity-100 text-white/40 hover:text-rose-300"
                    title="حذف"
                    data-testid={`shell-del-${s.id}`}>
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Footer: user info */}
          <div className="p-3 border-t border-white/10 bg-black/30">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xs font-bold shrink-0">
                {(profile?.email || profile?.name || 'U').charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate">{profile?.name || profile?.email || 'مستخدم'}</div>
                <div className="text-[10px] text-white/40 flex items-center gap-1">
                  <Coins className="w-2.5 h-2.5" /> {credits.toLocaleString()} نقطة
                </div>
              </div>
              <button onClick={() => navigate('/account')} className="p-1.5 hover:bg-white/5 rounded text-white/50 hover:text-white" title="حسابي" data-testid="shell-account-btn">
                <Settings className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </aside>
      )}

      {/* ── MAIN ─────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar with referral + gift */}
        <header className="border-b border-white/10 bg-[#0a0a14]/80 backdrop-blur-md px-4 py-2.5 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            {!sidebarOpen && (
              <button onClick={() => setSidebarOpen(true)} className="p-1.5 hover:bg-white/5 rounded" data-testid="shell-open-sidebar">
                <Menu className="w-4 h-4" />
              </button>
            )}
            <Sparkles className="w-4 h-4 text-cyan-400 shrink-0" />
            <h1 className="font-bold text-sm truncate">{title}</h1>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {/* Referral discount badge */}
            <button onClick={() => setShowReferral(true)}
              className="text-[11px] px-2.5 py-1 rounded-full bg-gradient-to-l from-emerald-500/20 to-emerald-500/10 border border-emerald-400/40 text-emerald-200 hover:from-emerald-500/30 hover:to-emerald-500/20 font-bold flex items-center gap-1.5 transition"
              data-testid="shell-referral-badge"
              title="ادعُ صديق واحصل على ٢٠٪ خصم">
              <Share2 className="w-3 h-3" />
              <span className="hidden sm:inline">خصم ٢٠٪</span>
              <span className="text-[9px] bg-emerald-500/30 px-1 rounded">جديد</span>
            </button>

            {/* Gift box */}
            <button onClick={() => setShowGift(true)}
              className="text-[11px] px-2.5 py-1 rounded-full bg-gradient-to-l from-amber-500/20 to-orange-500/10 border border-amber-400/40 text-amber-200 hover:from-amber-500/30 font-bold flex items-center gap-1.5 transition"
              data-testid="shell-gift-badge"
              title="هدية اليوم">
              <Gift className="w-3 h-3" />
              <span className="hidden sm:inline">هدية</span>
            </button>

            {/* Balance */}
            <div className="text-[11px] px-2.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-400/30 text-cyan-200 font-bold flex items-center gap-1" data-testid="shell-credits-pill">
              <Coins className="w-3 h-3" /> {credits.toLocaleString()}
            </div>

            {rightExtras}
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 min-h-0 overflow-hidden">
          {children}
        </main>
      </div>

      {/* ── Referral Modal ──────────────────────────────────── */}
      {showReferral && (
        <Modal onClose={() => setShowReferral(false)} testid="shell-referral-modal">
          <div className="text-center mb-4">
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 mx-auto flex items-center justify-center mb-3">
              <Share2 className="w-7 h-7 text-white" />
            </div>
            <h2 className="text-xl font-bold mb-1">ادعُ صديق · اربح ٢٠٪</h2>
            <p className="text-sm text-white/60 leading-7">
              لما يسجّل صديقك عبر رابطك ويشتري أول اشتراك،
              <br />تحصل <b className="text-emerald-300">٢٠٪ خصم</b> على فاتورتك القادمة + صديقك يحصل <b className="text-emerald-300">١٠٠ نقطة مجاناً</b>.
            </p>
          </div>
          <div className="bg-black/40 border border-white/10 rounded-xl p-3 mb-3 text-center" data-testid="shell-referral-link">
            <div className="text-[10px] text-white/40 mb-1">رابطك المخصّص</div>
            <div className="text-xs font-mono text-cyan-300 truncate" dir="ltr">
              {typeof window !== 'undefined' ? `${window.location.origin}/?ref=${referralCode || profile?.id || 'me'}` : ''}
            </div>
          </div>
          <button onClick={shareReferral}
            className="w-full bg-gradient-to-l from-emerald-500 to-teal-600 hover:from-emerald-400 text-white font-bold py-2.5 rounded-xl flex items-center justify-center gap-2"
            data-testid="shell-referral-share">
            <Share2 className="w-4 h-4" /> شارك الرابط الآن
          </button>
        </Modal>
      )}

      {/* ── Gift Modal ──────────────────────────────────────── */}
      {showGift && (
        <Modal onClose={() => setShowGift(false)} testid="shell-gift-modal">
          <div className="text-center mb-4">
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-amber-500 to-orange-600 mx-auto flex items-center justify-center mb-3 animate-pulse">
              <Gift className="w-7 h-7 text-white" />
            </div>
            <h2 className="text-xl font-bold mb-1">هدية زيتاكس اليومية 🎁</h2>
            <p className="text-sm text-white/60 leading-7">
              ادخل يومياً واحصل على <b className="text-amber-300">٥٠ نقطة مجاناً</b>،
              <br />ولو ثبّتت 7 أيام متتالية، تحصل <b className="text-amber-300">٥٠٠ نقطة + ميزة سرية</b>.
            </p>
          </div>
          <div className="grid grid-cols-7 gap-1.5 mb-4">
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className={`aspect-square rounded-lg border ${
                i === 0 ? 'bg-amber-500/20 border-amber-400/50 text-amber-200' : 'bg-white/5 border-white/10 text-white/30'
              } flex flex-col items-center justify-center text-[10px] font-bold`}>
                <span>يوم {i + 1}</span>
                <span className="text-[8px]">{i === 6 ? '🎉' : '+50'}</span>
              </div>
            ))}
          </div>
          <button onClick={() => alert('قريباً ✨')}
            className="w-full bg-gradient-to-l from-amber-500 to-orange-600 hover:from-amber-400 text-white font-bold py-2.5 rounded-xl flex items-center justify-center gap-2"
            data-testid="shell-gift-claim">
            <Crown className="w-4 h-4" /> اطلب هدية اليوم
          </button>
        </Modal>
      )}
    </div>
  );
}

function Modal({ children, onClose, testid }) {
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur z-50 flex items-center justify-center p-4" onClick={onClose} data-testid={testid}>
      <div onClick={(e) => e.stopPropagation()}
        className="bg-[#12161e] border border-white/15 rounded-2xl p-6 w-full max-w-md shadow-2xl">
        {children}
      </div>
    </div>
  );
}
