import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import LandingPage from '@/pages/LandingPage';
import DemoLanding from '@/pages/DemoLanding';
import VrmPreview from '@/pages/VrmPreview';
import ZitexDuoLauncher from '@/components/ZitexDuoLauncher';
import GlobalAvatarMount from '@/components/GlobalAvatarMount';
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
import StudioHub from '@/pages/studio/StudioHub';
import StudioImage from '@/pages/studio/StudioImage';
import StudioVideo from '@/pages/studio/StudioVideo';
import ChatVideo from '@/pages/chat/ChatVideo';
import ChatImage from '@/pages/chat/ChatImage';
import VideoStudio from '@/pages/VideoStudio';
import VideoRender from '@/pages/VideoRender';
import FreeBuild from '@/pages/FreeBuild';
import MobileAppBuilder from '@/pages/MobileAppBuilder';
import AppStudio from '@/pages/AppStudio';
import MobileAppMarketplace from '@/pages/MobileAppMarketplace';
import AIAgent from '@/pages/AIAgent';
import AppBuilder from '@/pages/AppBuilder';
import GameStudioDashboard from '@/pages/GameStudioDashboard';
import WebGamesStudio from '@/pages/WebGamesStudio';
import CinemaStudio from '@/pages/CinemaStudio';
import AppGamesStudio from '@/pages/AppGamesStudio';
import WebGameProject from '@/pages/WebGameProject';
import AppGameProject from '@/pages/AppGameProject';
import LogoPicker from '@/pages/LogoPicker';
import AdminMarketing from '@/pages/AdminMarketing';
import AvatarSettings from '@/pages/AvatarSettings';
import ChannelBridge from '@/pages/ChannelBridge';
import AdminAICore from '@/pages/AdminAICore';
import AdminAutoCoder from '@/pages/AdminAutoCoder';
import AdminQualityRouter from '@/pages/AdminQualityRouter';
import AdminSections from '@/pages/AdminSections';
import AdminApiKeys from '@/pages/AdminApiKeys';
import AdminIndependence from '@/pages/AdminIndependence';
import AdminAIReadiness from '@/pages/AdminAIReadiness';
import AdminLearning from '@/pages/AdminLearning';
import SecurityControlRoom from '@/pages/SecurityControlRoom';
import HoneypotCatcher from '@/pages/HoneypotCatcher';
import Pricing from '@/pages/Pricing';
import Billing from '@/pages/Billing';
import PricingSuccess from '@/pages/PricingSuccess';
import PricingAdmin from '@/pages/PricingAdmin';
import Companion from '@/pages/Companion';
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
          <Route path="/build-from-zero" element={<ProtectedRoute><FreeBuild /></ProtectedRoute>} />
          <Route path="/ai-agent" element={<ProtectedRoute><AIAgent /></ProtectedRoute>} />
          <Route path="/app-builder" element={<ProtectedRoute><AppBuilder user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/games" element={<ProtectedRoute><GameStudioDashboard user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/games/web" element={<ProtectedRoute><WebGamesStudio user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/games/app" element={<ProtectedRoute><AppGamesStudio user={user} /></ProtectedRoute>} />
          {/* 🎬 Cinema Studio — same Socratic flow as games, for video creation */}
          <Route path="/dashboard/cinema" element={<ProtectedRoute><CinemaStudio user={user} /></ProtectedRoute>} />
          <Route path="/cinema" element={user ? <Navigate to="/dashboard/cinema" /> : <Navigate to="/register" />} />
          {/* Public /games/web route — redirects to dashboard if logged in, otherwise to register */}
          <Route path="/games/web" element={user ? <Navigate to="/dashboard/games/web" /> : <Navigate to="/register" />} />
          <Route path="/games/mobile" element={user ? <Navigate to="/dashboard/games/app" /> : <Navigate to="/register" />} />
          <Route path="/dashboard/games/web/:id" element={<ProtectedRoute><WebGameProject user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/games/app/:id" element={<ProtectedRoute><AppGameProject user={user} /></ProtectedRoute>} />
          <Route path="/logo-picker" element={<LogoPicker />} />
          <Route path="/admin/marketing" element={<ProtectedRoute adminOnly><AdminMarketing user={user} /></ProtectedRoute>} />
          <Route path="/vrm-preview" element={<VrmPreview />} />
          <Route path="/demo" element={<DemoLanding />} />
          <Route path="/login" element={<LoginPage setUser={setUser} />} />
          <Route path="/register" element={<RegisterPage setUser={setUser} />} />
          <Route path="/auth-callback" element={<AuthCallback setUser={setUser} />} />
          <Route path="/pricing-old" element={<PricingPage user={user} />} />
          <Route path="/payment" element={<ProtectedRoute><PaymentPage user={user} /></ProtectedRoute>} />
          
          <Route path="/dashboard" element={<ProtectedRoute><ClientDashboard user={user} setUser={setUser} /></ProtectedRoute>} />
          <Route path="/dashboard/new-request" element={<ProtectedRoute><NewRequest user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/requests" element={<ProtectedRoute><MyRequests user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/requests/:id" element={<ProtectedRoute><RequestDetails user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/websites" element={<ProtectedRoute><MyWebsites user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/images" element={<ProtectedRoute><ImageGenerator user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/videos" element={<ProtectedRoute><VideoGenerator user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/apps" element={<ProtectedRoute><MobileAppBuilder /></ProtectedRoute>} />
          <Route path="/dashboard/apps-market" element={<MobileAppMarketplace />} />
          
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
          <Route path="/studio" element={<ProtectedRoute><StudioHub user={user} /></ProtectedRoute>} />
          <Route path="/studio/image" element={<ProtectedRoute><StudioImage user={user} /></ProtectedRoute>} />
          <Route path="/studio/video" element={<ProtectedRoute><StudioVideo user={user} /></ProtectedRoute>} />
          <Route path="/chat/video" element={<ProtectedRoute><VideoStudio /></ProtectedRoute>} />
          <Route path="/chat/video/render/:episodeId" element={<ProtectedRoute><VideoRender /></ProtectedRoute>} />
          <Route path="/chat/video-old" element={<ProtectedRoute><ChatVideo user={user} /></ProtectedRoute>} />
          <Route path="/chat/video-studio" element={<ProtectedRoute><VideoStudio /></ProtectedRoute>} />
          <Route path="/chat/app-studio" element={<ProtectedRoute><AppStudio /></ProtectedRoute>} />
          <Route path="/dashboard/app-studio" element={<ProtectedRoute><AppStudio /></ProtectedRoute>} />
          <Route path="/chat/image" element={<ProtectedRoute><ChatImage user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/avatar" element={<ProtectedRoute><AvatarSettings user={user} /></ProtectedRoute>} />
          <Route path="/dashboard/bridge" element={<ProtectedRoute><ChannelBridge user={user} /></ProtectedRoute>} />
          <Route path="/admin/ai-core" element={<ProtectedRoute adminOnly><AdminAICore user={user} /></ProtectedRoute>} />
          <Route path="/admin/autocoder" element={<ProtectedRoute adminOnly><AdminAutoCoder user={user} /></ProtectedRoute>} />
          <Route path="/admin/quality-router" element={<ProtectedRoute adminOnly><AdminQualityRouter user={user} /></ProtectedRoute>} />
          <Route path="/admin/sections" element={<ProtectedRoute adminOnly><AdminSections user={user} /></ProtectedRoute>} />
          <Route path="/admin/api-keys" element={<ProtectedRoute adminOnly><AdminApiKeys user={user} /></ProtectedRoute>} />
          <Route path="/admin/independence" element={<ProtectedRoute adminOnly><AdminIndependence user={user} /></ProtectedRoute>} />
          <Route path="/admin/ai-readiness" element={<ProtectedRoute adminOnly><AdminAIReadiness user={user} /></ProtectedRoute>} />
          <Route path="/admin/learning" element={<ProtectedRoute adminOnly><AdminLearning user={user} /></ProtectedRoute>} />
          <Route path="/admin/security" element={<ProtectedRoute adminOnly><SecurityControlRoom user={user} /></ProtectedRoute>} />
          <Route path="/admin/pricing" element={<ProtectedRoute adminOnly><PricingAdmin user={user} /></ProtectedRoute>} />
          <Route path="/companion" element={<ProtectedRoute><Companion user={user} setUser={setUser} /></ProtectedRoute>} />
          {/* 💰 Pricing & Billing */}
          <Route path="/pricing" element={<Pricing user={user} />} />
          <Route path="/billing" element={<ProtectedRoute><Billing user={user} /></ProtectedRoute>} />
          <Route path="/pricing/success" element={<ProtectedRoute><PricingSuccess user={user} /></ProtectedRoute>} />
          {/* 🛡️ Honeypot catch-all — bans scanners hitting /.env, /wp-admin, etc. */}
          <Route path="*" element={<HoneypotCatcher />} />
        </Routes>
        {/* Global persistent avatars — appear on EVERY route except VRM preview */}
        <GlobalAvatarMount />
      </BrowserRouter>
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
