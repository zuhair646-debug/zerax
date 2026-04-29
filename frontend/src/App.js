import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import LandingPage from '@/pages/LandingPage';
import DemoLanding from '@/pages/DemoLanding';
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
import AdminSiteBanner from '@/pages/AdminSiteBanner';
import AuthCallback from '@/pages/AuthCallback';
import AdminActivity from '@/pages/AdminActivity';
import AdminCredits from '@/pages/AdminCredits';
import AdminTraining from '@/pages/AdminTraining';
import AIChat from '@/pages/AIChat';
import ProjectsPage from '@/pages/ProjectsPage';
import VisualDesigner from '@/pages/VisualDesigner';
import WebsiteStudio from '@/pages/websites/WebsiteStudio';
import PublicSite from '@/pages/PublicSite';
import SourceBrowser from '@/pages/SourceBrowser';
import Operator from '@/pages/Operator';
import Affiliate from '@/pages/Affiliate';
import AdminAffiliates from '@/pages/AdminAffiliates';
import AdminSites from '@/pages/websites/AdminSites';
import ClientSiteDashboard from '@/pages/client/ClientDashboard';
import DriverDashboardPage from '@/pages/driver/DriverDashboard';
import SubscriptionGate from '@/pages/billing/SubscriptionGate';
import BillingSuccess from '@/pages/billing/BillingSuccess';
import BillingCancel from '@/pages/billing/BillingCancel';
import '@/App.css';

function App() {
  const [user, setUser] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
        .then(res => res.json())
        .then(data => {
          if (data.id) {
            setUser(data);
          } else {
            localStorage.removeItem('token');
          }
          setLoading(false);
        })
        .catch(() => {
          localStorage.removeItem('token');
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const ProtectedRoute = ({ children, adminOnly = false }) => {
    if (loading) return <div className="flex items-center justify-center min-h-screen bg-slate-900 text-white">جاري التحميل...</div>;
    if (!user) return <Navigate to="/login" />;
    const isAdmin = user.role === 'admin' || user.role === 'super_admin' || user.role === 'owner' || user.is_owner;
    if (adminOnly && !isAdmin) return <Navigate to="/dashboard" />;
    return children;
  };

  return (
    <div className="App" dir="rtl">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage user={user} />} />
          <Route path="/demo" element={<DemoLanding />} />
          <Route path="/login" element={<LoginPage setUser={setUser} />} />
          <Route path="/register" element={<RegisterPage setUser={setUser} />} />
          <Route path="/auth-callback" element={<AuthCallback setUser={setUser} />} />
          <Route path="/pricing" element={<PricingPage user={user} />} />
          <Route path="/payment" element={<ProtectedRoute><PaymentPage user={user} /></ProtectedRoute>} />
          
          <Route path="/dashboard" element={<ProtectedRoute><ClientDashboard user={user} setUser={setUser} /></ProtectedRoute>} />
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
          <Route path="/admin/site-banner" element={<ProtectedRoute adminOnly><AdminSiteBanner user={user} /></ProtectedRoute>} />
          <Route path="/admin/activity" element={<ProtectedRoute adminOnly><AdminActivity user={user} /></ProtectedRoute>} />
          <Route path="/admin/credits" element={<ProtectedRoute adminOnly><AdminCredits user={user} /></ProtectedRoute>} />
          <Route path="/admin/training" element={<ProtectedRoute adminOnly><AdminTraining user={user} /></ProtectedRoute>} />
          <Route path="/chat" element={<ProtectedRoute><AIChat user={user} /></ProtectedRoute>} />
          <Route path="/projects" element={<ProtectedRoute><ProjectsPage user={user} /></ProtectedRoute>} />
          <Route path="/designer" element={<ProtectedRoute><VisualDesigner user={user} /></ProtectedRoute>} />
          <Route path="/websites" element={<ProtectedRoute><SubscriptionGate><WebsiteStudio user={user} /></SubscriptionGate></ProtectedRoute>} />
          <Route path="/billing/success" element={<ProtectedRoute><BillingSuccess /></ProtectedRoute>} />
          <Route path="/billing/cancel" element={<ProtectedRoute><BillingCancel /></ProtectedRoute>} />
          <Route path="/sites/:slug" element={<PublicSite />} />
          <Route path="/client/:slug" element={<ClientSiteDashboard />} />
          <Route path="/driver/:slug" element={<DriverDashboardPage />} />
          <Route path="/admin/sites" element={<ProtectedRoute adminOnly><AdminSites user={user} /></ProtectedRoute>} />
          <Route path="/source" element={<ProtectedRoute adminOnly><SourceBrowser user={user} /></ProtectedRoute>} />
          <Route path="/operator" element={<ProtectedRoute><Operator user={user} /></ProtectedRoute>} />
          <Route path="/affiliate" element={<ProtectedRoute><Affiliate user={user} /></ProtectedRoute>} />
          <Route path="/admin/affiliates" element={<ProtectedRoute adminOnly><AdminAffiliates /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
