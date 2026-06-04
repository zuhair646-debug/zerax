import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { LogOut, LayoutDashboard, Shield, Menu, X } from 'lucide-react';

// شعار Zitex — SVG حيّ بدون مربع، يدور برفق وله توهج ذهبي
export const ZitexLogo = ({ size = 'md', animated = true }) => {
  const px = { sm: 32, md: 44, lg: 64, xl: 96 }[size] || 44;
  const uid = React.useId();
  return (
    <span
      className={`zitex-logo-wrap ${animated ? 'zitex-logo-animated' : ''}`}
      style={{ width: px, height: px, display: 'inline-block', position: 'relative' }}
      aria-label="Zitex"
    >
      <svg
        viewBox="0 0 100 100"
        width={px}
        height={px}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ overflow: 'visible' }}
      >
        <defs>
          <linearGradient id={`zg-${uid}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#fde68a" />
            <stop offset="45%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#b45309" />
          </linearGradient>
          <radialGradient id={`zh-${uid}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(251,191,36,0.55)" />
            <stop offset="60%" stopColor="rgba(245,158,11,0.15)" />
            <stop offset="100%" stopColor="rgba(0,0,0,0)" />
          </radialGradient>
          <filter id={`zglow-${uid}`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.4" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {/* halo glow */}
        <circle cx="50" cy="50" r="46" fill={`url(#zh-${uid})`} className="zitex-logo-halo" />
        {/* rotating thin arc */}
        <g className="zitex-logo-orbit" style={{ transformOrigin: '50px 50px' }}>
          <path
            d="M 50 8 A 42 42 0 0 1 92 50"
            stroke={`url(#zg-${uid})`}
            strokeWidth="2"
            strokeLinecap="round"
            fill="none"
            opacity="0.55"
          />
          <circle cx="92" cy="50" r="2.4" fill="#fde68a" />
        </g>
        {/* the Z letter (handcrafted, no box) */}
        <g filter={`url(#zglow-${uid})`}>
          <path
            d="M 26 26 L 74 26 L 74 36 L 42 64 L 74 64 L 74 74 L 26 74 L 26 64 L 58 36 L 26 36 Z"
            fill={`url(#zg-${uid})`}
            stroke="#fbbf24"
            strokeWidth="0.6"
            strokeLinejoin="round"
          />
        </g>
        {/* tiny sparkle dot */}
        <circle cx="74" cy="26" r="2" fill="#fff7ed" className="zitex-logo-spark" />
      </svg>
    </span>
  );
};

export const Navbar = ({ user, transparent = false, setUser }) => {
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);

  const handleLogout = () => {
    localStorage.removeItem('token');
    if (setUser) {
      setUser(null);
    }
    navigate('/');
    window.location.reload();
  };

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'owner' || user?.is_owner;

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 ${transparent ? 'bg-[#0a0a12]/90 backdrop-blur-xl border-b border-amber-500/10' : 'bg-[#0a0a12]/95 backdrop-blur-md border-b border-amber-500/20'}`}>
      <div className="container mx-auto px-4 md:px-8 max-w-7xl">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-3" data-testid="navbar-logo">
            <ZitexLogo size="md" />
            <span className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">Zitex</span>
          </Link>

          {/* Desktop Menu */}
          <div className="hidden md:flex items-center gap-4">
            <Link to="/pricing" className="text-sm font-medium text-gray-400 hover:text-amber-400 transition-colors">
              الأسعار
            </Link>
            {user ? (
              <>
                <Button
                  variant="outline"
                  onClick={() => navigate(isAdmin ? '/admin' : '/dashboard')}
                  data-testid="navbar-dashboard-btn"
                  className="border-slate-700 text-gray-300 hover:bg-slate-800 hover:text-amber-400"
                >
                  {isAdmin ? <Shield className="w-4 h-4 me-2" /> : <LayoutDashboard className="w-4 h-4 me-2" />}
                  {isAdmin ? 'لوحة الأدمن' : 'لوحة التحكم'}
                </Button>
                {isAdmin && (
                  <Button
                    variant="outline"
                    onClick={() => navigate('/operator')}
                    data-testid="navbar-operator-btn"
                    className="border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
                    title="إدارة عملاء الوكالة (Agency Mode)"
                  >
                    🧑‍💼 الوكالة
                  </Button>
                )}
                <Button
                  variant="outline"
                  onClick={() => navigate('/affiliate')}
                  data-testid="navbar-affiliate-btn"
                  className="border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/10"
                  title="برنامج التسويق بالعمولة"
                >
                  🤝 الإحالة
                </Button>
                <Button 
                  variant="outline" 
                  onClick={handleLogout} 
                  data-testid="navbar-logout-btn" 
                  className="border-slate-700 text-gray-300 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30"
                >
                  <LogOut className="w-4 h-4 me-2" />
                  خروج
                </Button>
              </>
            ) : (
              <>
                <Button 
                  variant="ghost" 
                  onClick={() => navigate('/login')} 
                  data-testid="navbar-login-btn" 
                  className="text-gray-300 hover:text-amber-400 hover:bg-amber-500/10"
                >
                  دخول
                </Button>
                <Button 
                  onClick={() => navigate('/register')} 
                  data-testid="navbar-register-btn" 
                  className="bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-700 hover:to-yellow-700 shadow-lg shadow-amber-500/20"
                >
                  ابدأ مجاناً
                </Button>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button className="md:hidden p-2 rounded-lg hover:bg-slate-800" onClick={() => setIsMenuOpen(!isMenuOpen)}>
            {isMenuOpen ? <X className="text-amber-400" /> : <Menu className="text-amber-400" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-amber-500/10">
            <div className="flex flex-col gap-2">
              <Link to="/pricing" className="py-2 text-gray-300 hover:text-amber-400">الأسعار</Link>
              {user ? (
                <>
                  <Button 
                    variant="ghost" 
                    onClick={() => { navigate(isAdmin ? '/admin' : '/dashboard'); setIsMenuOpen(false); }} 
                    className="justify-start text-gray-300"
                  >
                    لوحة التحكم
                  </Button>
                  <Button 
                    variant="ghost" 
                    onClick={handleLogout} 
                    className="justify-start text-red-400"
                  >
                    خروج
                  </Button>
                </>
              ) : (
                <>
                  <Button 
                    variant="ghost" 
                    onClick={() => { navigate('/login'); setIsMenuOpen(false); }} 
                    className="justify-start text-gray-300"
                  >
                    دخول
                  </Button>
                  <Button 
                    onClick={() => { navigate('/register'); setIsMenuOpen(false); }} 
                    className="bg-gradient-to-r from-amber-600 to-yellow-600"
                  >
                    ابدأ مجاناً
                  </Button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};
