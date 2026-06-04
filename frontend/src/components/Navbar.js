import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { LogOut, LayoutDashboard, Shield, Menu, X } from 'lucide-react';

// شعار Zitex — حرف Z هندسي مع orbits متعددة تدور بشكل ذكي + قلب نابض
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
        viewBox="0 0 120 120"
        width={px}
        height={px}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ overflow: 'visible' }}
      >
        <defs>
          <linearGradient id={`zg-${uid}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#fef3c7" />
            <stop offset="35%" stopColor="#fbbf24" />
            <stop offset="70%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#92400e" />
          </linearGradient>
          <linearGradient id={`zgs-${uid}`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#fbbf24" stopOpacity="0" />
            <stop offset="50%" stopColor="#fde68a" stopOpacity="1" />
            <stop offset="100%" stopColor="#fbbf24" stopOpacity="0" />
          </linearGradient>
          <filter id={`zglow-${uid}`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="1.8" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* outer orbit — thin dotted, rotates CCW slow */}
        <g className="zitex-orbit-outer" style={{ transformOrigin: '60px 60px' }}>
          <circle cx="60" cy="60" r="54" stroke={`url(#zg-${uid})`} strokeWidth="0.8" strokeDasharray="2 5" fill="none" opacity="0.45" />
          <circle cx="60" cy="6" r="1.8" fill="#fbbf24" />
        </g>

        {/* middle orbit — arc with glowing head, rotates CW */}
        <g className="zitex-orbit-mid" style={{ transformOrigin: '60px 60px' }}>
          <path d="M 60 16 A 44 44 0 0 1 104 60" stroke={`url(#zg-${uid})`} strokeWidth="1.6" strokeLinecap="round" fill="none" opacity="0.7" />
          <circle cx="104" cy="60" r="2.6" fill="#fde68a" />
        </g>

        {/* inner orbit — small fast counter-spin */}
        <g className="zitex-orbit-inner" style={{ transformOrigin: '60px 60px' }}>
          <circle cx="60" cy="60" r="36" stroke="#fbbf24" strokeWidth="0.5" fill="none" opacity="0.25" />
          <circle cx="60" cy="24" r="1.5" fill="#fff7ed" />
        </g>

        {/* the Z letter — modern beveled with gradient sweep */}
        <g filter={`url(#zglow-${uid})`} className="zitex-letter-pulse">
          {/* main Z shape — angular, modern */}
          <path
            d="M 36 36 L 84 36 L 84 44 L 50 76 L 84 76 L 84 84 L 36 84 L 36 76 L 70 44 L 36 44 Z"
            fill={`url(#zg-${uid})`}
            stroke="#fcd34d"
            strokeWidth="0.5"
            strokeLinejoin="miter"
          />
          {/* shimmer overlay that sweeps across the Z */}
          <path
            d="M 36 36 L 84 36 L 84 44 L 50 76 L 84 76 L 84 84 L 36 84 L 36 76 L 70 44 L 36 44 Z"
            fill={`url(#zgs-${uid})`}
            className="zitex-letter-shimmer"
          />
        </g>

        {/* corner accents — diagonal dots */}
        <circle cx="36" cy="36" r="1.5" fill="#fef3c7" className="zitex-corner-tl" />
        <circle cx="84" cy="84" r="1.5" fill="#fef3c7" className="zitex-corner-br" />
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
