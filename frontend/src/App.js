import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import LandingPage from '@/pages/LandingPage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import ClientDashboard from '@/pages/ClientDashboard';
import NewRequest from '@/pages/NewRequest';
import MyRequests from '@/pages/MyRequests';
import RequestDetails from '@/pages/RequestDetails';
import MyWebsites from '@/pages/MyWebsites';
import ImageGenerator from '@/pages/ImageGenerator';
import VideoGenerator from '@/pages/VideoGenerator';
import PricingPage from '@/pages/PricingPage';
import PaymentPage from '@/pages/PaymentPage';
import AdminDashboard from '@/pages/AdminDashboard';
import AdminRequests from '@/pages/AdminRequests';
import AdminPayments from '@/pages/AdminPayments';
import AdminClients from '@/pages/AdminClients';
import AdminWebsites from '@/pages/AdminWebsites';
import AdminSettings from '@/pages/AdminSettings';
import AdminActivity from '@/pages/AdminActivity';
import AIChat from '@/pages/AIChat';
import ProjectsPage from '@/pages/ProjectsPage';
import '@/App.css';

function App() {
  const [user, setUser] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  // Custom setUser that also updates loading state
  const handleSetUser = React.useCallback((userData) => {
    setUser(userData);
    if (userData) {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/me`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
          const data = await response.json();
          if (data && data.id) {
            setUser(data);
          } else {
            localStorage.removeItem('token');
          }
        } else {
          localStorage.removeItem('token');
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('token');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const ProtectedRoute = ({ children, adminOnly = false }) => {
    if (loading) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-slate-900 text-white">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mr-3"></div>
          جاري التحميل...
        </div>
      );
    }
    
    if (!user) {
      return <Navigate to="/login" />;
    }
    
    const isAdmin = user.role === 'admin' || user.role === 'super_admin' || user.role === 'owner' || user.is_owner;
    
    if (adminOnly && !isAdmin) {
      return <Navigate to="/dashboard" />;
    }
    
    return children;
  };

  return (
    <div className="App" dir="rtl">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage user={user} />} />
          <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <LoginPage setUser={handleSetUser} />} />
          <Route path="/register" element={user ? <Navigate to="/dashboard" /> : <RegisterPage setUser={handleSetUser} />} />
          <Route path="/pricing" element={<PricingPage user={user} />} />
          <Route path="/payment" element={<ProtectedRoute><PaymentPage user={user} /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><ClientDashboard user={user} setUser={handleSetUser} /></ProtectedRoute>} />
          <Route path="/dashboard/new-request" element={<ProtectedRoute><NewRequest user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/requests" element={<ProtectedRoute><MyRequests user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/requests/:id" element={<ProtectedRoute><RequestDetails user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/websites" element={<ProtectedRoute><MyWebsites user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/images" element={<ProtectedRoute><ImageGenerator user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/videos" element={<ProtectedRoute><VideoGenerator user={user} /></ProtectedRoute>} />
          <Route path="/admin" element={<ProtectedRoute adminOnly><AdminDashboard user={user} /></ProtectedRoute>} />
          <Route path="/admin/requests" element={<ProtectedRoute adminOnly><AdminRequests user={user} /></ProtectedRoute>} />
          <Route path="/admin/payments" element={<ProtectedRoute adminOnly><AdminPayments user={user} /></ProtectedRoute>} />
          <Route path="/admin/clients" element={<ProtectedRoute adminOnly><AdminClients user={user} /></ProtectedRoute>} />
          <Route path="/admin/websites" element={<ProtectedRoute adminOnly><AdminWebsites user={user} /></ProtectedRoute>} />
          <Route path="/admin/settings" element={<ProtectedRoute adminOnly><AdminSettings user={user} /></ProtectedRoute>} />
          <Route path="/admin/activity" element={<ProtectedRoute adminOnly><AdminActivity user={user} /></ProtectedRoute>} />
          <Route path="/chat" element={<ProtectedRoute><AIChat user={user} /></ProtectedRoute>} />
          <Route path="/projects" element={<ProtectedRoute><ProjectsPage user={user} /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
