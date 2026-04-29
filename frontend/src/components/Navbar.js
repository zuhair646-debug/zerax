import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { LogOut, LayoutDashboard, Shield, Menu, X, MessageSquare, Rocket } from 'lucide-react';

// اللوغو الذهبي الجديد
const ZITEX_LOGO_URL = "https://static.prod-images.emergentagent.com/jobs/d28c1cbc-c039-46df-a176-2e32ebb0f715/images/f7f88c5a96c3a3978fb84a31dd4d6b922be1568a9083c93bf3cef363e8c17387.png";

export const ZitexLogo = ({ size = 'md', light = false }) => {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-14 h-14',
    xl: 'w-20 h-20'
  };
  
  return (
    <img 
      src={ZITEX_LOGO_URL} 
      alt="Zitex" 
      className={`${sizes[size]} object-contain`}
    />
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
                  onClick={() => navigate('/chat')}
                  data-testid="navbar-chat-btn"
                  className="bg-gradient-to-r from-amber-600 to-yellow-600 border-0 text-white hover:from-amber-700 hover:to-yellow-700 shadow-lg shadow-amber-500/20"
                >
                  <MessageSquare className="w-4 h-4 me-2" />
                  الشات الذكي
                </Button>
                <Button
                  variant="outline"
                  onClick={() => navigate('/projects')}
                  data-testid="navbar-projects-btn"
                  className="border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
                >
                  <Rocket className="w-4 h-4 me-2" />
                  مشاريعي
                </Button>
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
                    variant="default" 
                    onClick={() => { navigate('/chat'); setIsMenuOpen(false); }} 
                    className="justify-start bg-gradient-to-r from-amber-600 to-yellow-600"
                  >
                    <MessageSquare className="w-4 h-4 me-2" />
                    الشات الذكي
                  </Button>
                  <Button 
                    variant="ghost" 
                    onClick={() => { navigate('/projects'); setIsMenuOpen(false); }} 
                    className="justify-start text-amber-400"
                  >
                    <Rocket className="w-4 h-4 me-2" />
                    مشاريعي
                  </Button>
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
