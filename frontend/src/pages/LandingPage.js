import React from 'react';
import { Navbar, ZitexLogo } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Zap, Shield, Globe, Image, Video, Code, ArrowLeft, CheckCircle, Gamepad2 } from 'lucide-react';

const LandingPage = ({ user }) => {
  const navigate = useNavigate();

  const services = [
    { icon: <Globe className="w-10 h-10" />, title: 'إنشاء المواقع', desc: 'مواقع احترافية مخصصة بالذكاء الاصطناعي', color: 'from-emerald-500 to-teal-500' },
    { icon: <Image className="w-10 h-10" />, title: 'توليد الصور', desc: 'صور إبداعية بتقنية GPT Image 1', color: 'from-amber-500 to-yellow-500' },
    { icon: <Video className="w-10 h-10" />, title: 'إنشاء الفيديو', desc: 'فيديوهات سينمائية بـ Sora 2', color: 'from-orange-500 to-red-500' },
    { icon: <Gamepad2 className="w-10 h-10" />, title: 'تصميم الألعاب', desc: 'ألعاب تفاعلية بـ Babylon.js', color: 'from-cyan-500 to-blue-500' },
  ];

  const features = [
    { icon: <Sparkles className="w-6 h-6 text-amber-400" />, title: 'ذكاء اصطناعي متطور', desc: 'نستخدم GPT-5.2 و Sora 2 لأفضل النتائج' },
    { icon: <Zap className="w-6 h-6 text-yellow-400" />, title: 'سرعة فائقة', desc: 'نتائج فورية وتسليم سريع' },
    { icon: <Shield className="w-6 h-6 text-emerald-400" />, title: 'أمان مطلق', desc: 'حماية كاملة لبياناتك ومشاريعك' },
  ];

  const pricing = [
    { title: 'توليد الصور', price: '5', unit: 'نقاط/صورة', desc: 'جودة عالية GPT Image 1', color: 'amber' },
    { title: 'إنشاء الفيديو', price: '20', unit: 'نقطة/فيديو', desc: 'فيديو سينمائي Sora 2', color: 'orange' },
    { title: 'إنشاء المواقع', price: '10', unit: 'نقاط/موقع', desc: 'موقع كامل بـ GPT-5.2', color: 'emerald' },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a12]" data-testid="landing-page">
      <Navbar user={user} transparent />
      
      {/* Hero Section */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-gradient-to-br from-amber-600/10 via-yellow-600/5 to-transparent"></div>
        <div className="absolute top-20 right-10 w-72 h-72 bg-amber-500/20 rounded-full blur-3xl"></div>
        <div className="absolute bottom-10 left-10 w-96 h-96 bg-yellow-500/10 rounded-full blur-3xl"></div>
        
        <div className="container mx-auto px-4 md:px-8 max-w-7xl relative z-10">
          <div className="text-center max-w-4xl mx-auto">
            <div className="flex justify-center mb-8">
              <ZitexLogo size="xl" />
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-tight mb-6 text-white" data-testid="hero-title">
              <span className="bg-gradient-to-r from-amber-400 via-yellow-400 to-amber-500 bg-clip-text text-transparent">Zitex</span>
              <br />
              <span className="text-3xl md:text-4xl font-medium text-amber-200/80">منصة الإبداع بالذكاء الاصطناعي</span>
            </h1>
            <p className="text-lg md:text-xl leading-relaxed text-gray-400 mb-10 max-w-2xl mx-auto" data-testid="hero-description">
              أنشئ مواقع احترافية، ولّد صوراً إبداعية، واصنع فيديوهات مذهلة - كل ذلك بقوة الذكاء الاصطناعي
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button 
                size="lg" 
                onClick={() => navigate(user ? '/chat' : '/register')}
                data-testid="hero-cta-btn"
                className="h-14 px-10 text-lg bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 text-black font-semibold shadow-lg shadow-amber-500/25"
              >
                <Sparkles className="w-5 h-5 me-2" />
                {user ? 'الشات الذكي' : 'ابدأ مجاناً'}
              </Button>
              <Button 
                size="lg" 
                variant="outline"
                onClick={() => navigate('/pricing')}
                data-testid="hero-pricing-btn"
                className="h-14 px-10 text-lg border-amber-500/30 text-amber-400 hover:bg-amber-500/10 hover:border-amber-500/50"
              >
                عرض الأسعار
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Services Section */}
      <section className="py-20 bg-[#0d0d18]">
        <div className="container mx-auto px-4 md:px-8 max-w-7xl">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-4" data-testid="services-title">
              خدماتنا
            </h2>
            <p className="text-amber-200/60 text-lg">كل ما تحتاجه لإطلاق مشروعك الرقمي</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {services.map((service, idx) => (
              <Card key={idx} className="bg-slate-800/30 border-slate-700/50 hover:border-amber-500/30 transition-all group cursor-pointer" data-testid={`service-card-${idx}`}>
                <CardContent className="p-6 text-center">
                  <div className={`w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br ${service.color} flex items-center justify-center text-white group-hover:scale-110 transition-transform shadow-lg`}>
                    {service.icon}
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-2">{service.title}</h3>
                  <p className="text-gray-400">{service.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 md:px-8 max-w-7xl">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
                لماذا <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">Zitex</span>؟
              </h2>
              <div className="space-y-6">
                {features.map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-slate-800/50 border border-slate-700/50 flex items-center justify-center flex-shrink-0">
                      {feature.icon}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white mb-1">{feature.title}</h3>
                      <p className="text-gray-400">{feature.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative">
              <div className="aspect-square rounded-3xl bg-gradient-to-br from-amber-500/10 to-yellow-500/10 p-8 flex items-center justify-center border border-amber-500/20">
                <ZitexLogo size="xl" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="py-20 bg-[#0d0d18]">
        <div className="container mx-auto px-4 md:px-8 max-w-7xl">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
              أسعار <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">تنافسية</span>
            </h2>
            <p className="text-gray-400 text-lg">نظام النقاط المرن - ادفع حسب استهلاكك</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            {pricing.map((plan, idx) => (
              <Card key={idx} className="bg-slate-800/30 border-slate-700/50 hover:border-amber-500/30 transition-all">
                <CardContent className="p-8 text-center">
                  <h3 className="text-xl font-semibold text-white mb-4">{plan.title}</h3>
                  <div className="mb-4">
                    <span className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">{plan.price}</span>
                    <span className="text-gray-400 ms-2">{plan.unit}</span>
                  </div>
                  <p className="text-gray-400">{plan.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
          
          <div className="text-center">
            <Button 
              size="lg"
              onClick={() => navigate('/pricing')}
              className="bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 text-black font-semibold shadow-lg shadow-amber-500/20"
            >
              عرض جميع الأسعار
              <ArrowLeft className="w-5 h-5 ms-2" />
            </Button>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 md:px-8 max-w-4xl text-center">
          <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">
            جاهز لبدء <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">الإبداع</span>؟
          </h2>
          <p className="text-xl text-gray-400 mb-10">
            انضم إلى آلاف المستخدمين وابدأ رحلتك مع Zitex
          </p>
          <Button 
            size="lg"
            onClick={() => navigate('/register')}
            className="h-14 px-12 text-lg bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 text-black font-semibold shadow-lg shadow-amber-500/25"
          >
            إنشاء حساب مجاني
            <ArrowLeft className="w-5 h-5 ms-2" />
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-amber-500/10">
        <div className="container mx-auto px-4 md:px-8 max-w-7xl">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <ZitexLogo size="sm" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500 font-bold text-xl">Zitex</span>
            </div>
            <p className="text-sm text-gray-500">
              © 2024 Zitex. جميع الحقوق محفوظة.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
