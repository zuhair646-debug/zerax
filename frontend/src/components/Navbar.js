import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { LogOut, LayoutDashboard, Shield, Menu, X, ArrowRight } from 'lucide-react';

// شعار Zitex — الصورة المعتمدة (L1: ملكي تراثي ذهبي) + حركة دوران لطيفة في المكان
export const ZitexLogo = ({ size = 'md', animated = true }) => {
  const px = { sm: 32, md: 44, lg: 64, xl: 96 }[size] || 44;
  // pick small image for sm/md, large for lg/xl — saves bandwidth
  const src = px <= 48 ? '/zitex-logo-sm.png' : '/zitex-logo.png';
  return (
    <span
      className={`zitex-logo-img-wrap ${animated ? 'zitex-logo-img-animated' : ''}`}
      style={{ width: px, height: px, display: 'inline-block', position: 'relative' }}
      aria-label="Zitex"
    >
      <img
        src={src}
        alt="Zitex"
        width={px}
        height={px}
        className="zitex-logo-img"
        draggable={false}
        style={{ width: '100%', height: '100%', objectFit: 'contain', userSelect: 'none' }}
      />
    </span>
  );
};

export const Navbar = ({ user, transparent = false, setUser }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);

  // Show "back" arrow on every page EXCEPT the landing page itself.
  const showBack = location.pathname !== '/' && location.pathname !== '';

  const handleBack = () => {
    if (window.history.length > 1 && location.key !== 'default') {
      navigate(-1);
    } else {
      navigate('/');
    }
  };

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
          <div className="flex items-center gap-2">
            {showBack && (
              <button
                onClick={handleBack}
                data-testid="navbar-back-btn"
                className="inline-flex items-center justify-center w-9 h-9 rounded-lg bg-slate-800/70 hover:bg-amber-500/10 text-gray-300 hover:text-amber-400 border border-slate-700 hover:border-amber-500/40 transition-all"
                title="رجوع"
                aria-label="رجوع"
              >
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
            <Link to="/" className="flex items-center gap-3" data-testid="navbar-logo">
              <ZitexLogo size="md" />
              <span className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">Zitex</span>
            </Link>
          </div>

          {/* Desktop Menu */}
          <div className="hidden md:flex items-center gap-3">
            <Link
              to="/pricing"
              className="navbar-link text-sm font-medium text-gray-300 px-3 py-2 rounded-lg"
              data-testid="navbar-pricing-link"
            >
              الأسعار
            </Link>
            {user ? (
              <>
                <button
                  type="button"
                  onClick={() => navigate(isAdmin ? '/admin' : '/dashboard')}
                  data-testid="navbar-dashboard-btn"
                  className="navbar-btn inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-700 text-gray-300 text-sm font-medium"
                >
                  {isAdmin ? <Shield className="w-4 h-4" /> : <LayoutDashboard className="w-4 h-4" />}
                  {isAdmin ? 'لوحة الأدمن' : 'لوحة التحكم'}
                </button>
                {isAdmin && (
                  <button
                    type="button"
                    onClick={() => navigate('/operator')}
                    data-testid="navbar-operator-btn"
                    className="navbar-btn inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-emerald-500/30 text-emerald-400 text-sm"
                    title="إدارة عملاء الوكالة"
                  >
                    الوكالة
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => navigate('/affiliate')}
                  data-testid="navbar-affiliate-btn"
                  className="navbar-btn inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-yellow-500/30 text-yellow-400 text-sm"
                  title="برنامج التسويق بالعمولة"
                >
                  الإحالة
                </button>
                <button
                  type="button"
                  onClick={handleLogout}
                  data-testid="navbar-logout-btn"
                  className="navbar-btn inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-700 text-gray-300 text-sm"
                >
                  <LogOut className="w-4 h-4" />
                  خروج
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => navigate('/login')}
                  data-testid="navbar-login-btn"
                  className="navbar-btn px-4 py-2 text-gray-300 text-sm rounded-lg"
                >
                  دخول
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/register')}
                  data-testid="navbar-register-btn"
                  className="navbar-btn-primary px-4 py-2 rounded-lg text-sm font-semibold text-black"
                >
                  ابدأ مجاناً
                </button>
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
