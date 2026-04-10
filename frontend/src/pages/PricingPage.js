import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { toast } from 'sonner';
import { 
  Check, Star, Zap, Image, Video, Globe, Gift, 
  Users, Crown, Sparkles, Copy, Share2
} from 'lucide-react';

const PricingPage = ({ user }) => {
  const [pricing, setPricing] = useState(null);
  const [referralInfo, setReferralInfo] = useState(null);
  const [userBalance, setUserBalance] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPricing();
    if (user) {
      fetchReferralInfo();
      fetchUserBalance();
    }
  }, [user]);

  const fetchPricing = async () => {
    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/pricing`);
      if (res.ok) {
        const data = await res.json();
        setPricing(data);
      }
    } catch (error) {
      console.error('Error fetching pricing:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchReferralInfo = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/referral/info`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setReferralInfo(data);
      }
    } catch (error) {
      console.error('Error fetching referral info:', error);
    }
  };

  const fetchUserBalance = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/user/balance`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUserBalance(data);
      }
    } catch (error) {
      console.error('Error fetching balance:', error);
    }
  };

  const copyReferralCode = () => {
    if (referralInfo?.referral_code) {
      navigator.clipboard.writeText(referralInfo.referral_code);
      toast.success('تم نسخ كود الدعوة!');
    }
  };

  const shareReferralLink = () => {
    if (referralInfo?.referral_link) {
      if (navigator.share) {
        navigator.share({
          title: 'انضم لـ Zitex',
          text: `انضم لمنصة Zitex واحصل على 20 نقطة مجانية! استخدم كود الدعوة: ${referralInfo.referral_code}`,
          url: referralInfo.referral_link
        });
      } else {
        navigator.clipboard.writeText(referralInfo.referral_link);
        toast.success('تم نسخ رابط الدعوة!');
      }
    }
  };

  const handlePurchase = async (packageId, packageType = 'credits') => {
    if (!user) {
      toast.error('يرجى تسجيل الدخول أولاً');
      window.location.href = '/login';
      return;
    }
    toast.info('جاري التحويل لصفحة الدفع...');
    window.location.href = `/payment?package=${packageId}&type=${packageType}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a12] flex items-center justify-center">
        <div className="animate-spin w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a12] via-[#0d0d18] to-[#0a0a12]" data-testid="pricing-page">
      <Navbar user={user} />
      
      <div className="pt-24 pb-16 px-4">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="text-center mb-16">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
              أسعار <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">شفافة</span> وبسيطة
            </h1>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto">
              ابدأ مجاناً مع 20 نقطة + 3 صور + 2 فيديو، واشترِ المزيد حسب احتياجك
            </p>
          </div>

          {/* User Balance Card */}
          {user && userBalance && (
            <Card className="bg-gradient-to-r from-amber-900/30 to-yellow-900/30 border-amber-500/30 mb-12">
              <CardContent className="p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="text-gray-400 text-sm">رصيدك الحالي</p>
                    <p className="text-3xl font-bold text-white">{userBalance.credits} <span className="text-lg text-amber-400">نقطة</span></p>
                  </div>
                  <div className="flex gap-4 text-center">
                    <div className="bg-slate-800/50 rounded-lg px-4 py-2">
                      <p className="text-2xl font-bold text-amber-400">{userBalance.free_images}</p>
                      <p className="text-xs text-gray-400">صور مجانية</p>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg px-4 py-2">
                      <p className="text-2xl font-bold text-orange-400">{userBalance.free_videos}</p>
                      <p className="text-xs text-gray-400">فيديو مجاني</p>
                    </div>
                    {userBalance.bonus_points > 0 && (
                      <div className="bg-slate-800/50 rounded-lg px-4 py-2">
                        <p className="text-2xl font-bold text-emerald-400">{userBalance.bonus_points}</p>
                        <p className="text-xs text-gray-400">نقاط مكافأة</p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Credits Packages */}
          <div className="mb-16">
            <h2 className="text-2xl font-bold text-white text-center mb-8 flex items-center justify-center gap-2">
              <Zap className="w-6 h-6 text-amber-400" />
              باقات النقاط
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {pricing?.credits_packages?.map((pkg) => (
                <Card 
                  key={pkg.id}
                  className={`relative overflow-hidden transition-all duration-300 hover:scale-105 ${
                    pkg.popular 
                      ? 'bg-gradient-to-b from-amber-900/50 to-slate-800 border-amber-500 shadow-lg shadow-amber-500/20' 
                      : 'bg-slate-800/50 border-slate-700 hover:border-amber-500/50'
                  }`}
                >
                  {pkg.popular && (
                    <div className="absolute top-0 left-0 right-0 bg-gradient-to-r from-amber-500 to-yellow-500 text-black text-center py-1 text-sm font-semibold">
                      <Star className="w-4 h-4 inline me-1" />
                      الأكثر شعبية
                    </div>
                  )}
                  
                  <CardHeader className={pkg.popular ? 'pt-10' : ''}>
                    <CardTitle className="text-white text-xl">{pkg.name}</CardTitle>
                    <CardDescription className="text-gray-400">
                      {pkg.credits} نقطة
                      {pkg.bonus > 0 && <span className="text-emerald-400 mr-1">+ {pkg.bonus} هدية</span>}
                    </CardDescription>
                  </CardHeader>
                  
                  <CardContent>
                    <div className="mb-6">
                      <span className="text-4xl font-bold text-white">{pkg.price_sar}</span>
                      <span className="text-gray-400 mr-1">ر.س</span>
                      <span className="text-gray-500 text-sm block">≈ ${pkg.price_usd}</span>
                    </div>
                    
                    <ul className="space-y-3 text-gray-300 text-sm">
                      <li className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400" />
                        {Math.floor(pkg.credits / 5)} صورة تقريباً
                      </li>
                      <li className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400" />
                        {Math.floor(pkg.credits / 25)} فيديو 12 ثانية
                      </li>
                      <li className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400" />
                        صلاحية دائمة
                      </li>
                      {pkg.bonus > 0 && (
                        <li className="flex items-center gap-2 text-emerald-400">
                          <Gift className="w-4 h-4" />
                          +{pkg.bonus} نقطة هدية
                        </li>
                      )}
                    </ul>
                  </CardContent>
                  
                  <CardFooter>
                    <Button 
                      onClick={() => handlePurchase(pkg.id, 'credits')}
                      className={`w-full ${
                        pkg.popular 
                          ? 'bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 text-black font-semibold' 
                          : 'bg-slate-700 hover:bg-slate-600'
                      }`}
                    >
                      اشتري الآن
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          </div>

          {/* Subscriptions */}
          <div className="mb-16">
            <h2 className="text-2xl font-bold text-white text-center mb-8 flex items-center justify-center gap-2">
              <Crown className="w-6 h-6 text-amber-400" />
              الاشتراكات الشهرية
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {pricing?.subscriptions && Object.entries(pricing.subscriptions).map(([key, sub]) => (
                <Card key={key} className="bg-slate-800/50 border-slate-700 hover:border-amber-500/50 transition-all">
                  <CardHeader>
                    <div className="flex items-center gap-2 mb-2">
                      {key.includes('image') && <Image className="w-5 h-5 text-amber-400" />}
                      {key.includes('video') && <Video className="w-5 h-5 text-orange-400" />}
                      {key.includes('all') && <Sparkles className="w-5 h-5 text-yellow-400" />}
                    </div>
                    <CardTitle className="text-white">{sub.name}</CardTitle>
                    <CardDescription className="text-gray-400">{sub.limit}</CardDescription>
                  </CardHeader>
                  
                  <CardContent>
                    <div className="mb-4">
                      <span className="text-3xl font-bold text-white">{sub.price_sar}</span>
                      <span className="text-gray-400 mr-1">ر.س/شهر</span>
                    </div>
                    
                    <ul className="space-y-2">
                      {sub.features?.map((feature, idx) => (
                        <li key={idx} className="flex items-center gap-2 text-gray-300 text-sm">
                          <Check className="w-4 h-4 text-emerald-400" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                  
                  <CardFooter>
                    <Button 
                      onClick={() => handlePurchase(key, 'subscription')}
                      variant="outline"
                      className="w-full border-amber-500/50 text-amber-400 hover:bg-amber-500/20"
                    >
                      اشترك الآن
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          </div>

          {/* Service Costs */}
          <div className="mb-16">
            <h2 className="text-2xl font-bold text-white text-center mb-8">تكلفة الخدمات بالنقاط</h2>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {pricing?.service_costs && [
                { key: 'image_generation', icon: Image, color: 'text-amber-400', label: 'صورة واحدة' },
                { key: 'video_12_seconds', icon: Video, color: 'text-orange-400', label: 'فيديو 12 ثانية' },
                { key: 'video_60_seconds', icon: Video, color: 'text-red-400', label: 'فيديو دقيقة' },
                { key: 'website_simple', icon: Globe, color: 'text-emerald-400', label: 'موقع بسيط' },
              ].map(({ key, icon: Icon, color, label }) => (
                <Card key={key} className="bg-slate-800/30 border-slate-700 text-center">
                  <CardContent className="pt-6">
                    <Icon className={`w-8 h-8 mx-auto mb-2 ${color}`} />
                    <p className="text-2xl font-bold text-white">{pricing.service_costs[key]}</p>
                    <p className="text-sm text-gray-400">نقطة</p>
                    <p className="text-xs text-gray-500 mt-1">{label}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Referral Section */}
          {user && (
            <Card className="bg-gradient-to-r from-emerald-900/30 to-teal-900/30 border-emerald-500/30 mb-16">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Users className="w-6 h-6 text-emerald-400" />
                  ادعُ أصدقاءك واكسب نقاط
                </CardTitle>
                <CardDescription className="text-gray-400">
                  احصل على {referralInfo?.rewards?.inviter_bonus || 30} نقطة لكل صديق ينضم، وصديقك يحصل على {referralInfo?.rewards?.invited_bonus || 20} نقطة!
                </CardDescription>
              </CardHeader>
              
              <CardContent>
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex-1 min-w-[200px]">
                    <label className="text-sm text-gray-400 block mb-1">كود الدعوة الخاص بك</label>
                    <div className="flex gap-2">
                      <div className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 text-white font-mono text-lg">
                        {referralInfo?.referral_code || '---'}
                      </div>
                      <Button onClick={copyReferralCode} variant="outline" className="border-emerald-500/50 text-emerald-400">
                        <Copy className="w-4 h-4" />
                      </Button>
                      <Button onClick={shareReferralLink} className="bg-emerald-600 hover:bg-emerald-700">
                        <Share2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                  
                  <div className="text-center px-6 py-4 bg-slate-800/50 rounded-lg">
                    <p className="text-3xl font-bold text-emerald-400">{referralInfo?.total_referrals || 0}</p>
                    <p className="text-sm text-gray-400">دعوة ناجحة</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Free Trial Info */}
          <div className="text-center">
            <Card className="bg-slate-800/30 border-amber-500/20 inline-block">
              <CardContent className="p-6">
                <Gift className="w-12 h-12 text-amber-400 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-white mb-2">ابدأ مجاناً الآن!</h3>
                <p className="text-gray-400 mb-4">
                  كل مستخدم جديد يحصل على: <span className="text-amber-400 font-semibold">20 نقطة + 3 صور + 2 فيديو</span> مجاناً
                </p>
                {!user && (
                  <Button 
                    onClick={() => window.location.href = '/register'}
                    className="bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 text-black font-semibold"
                  >
                    سجّل الآن مجاناً
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PricingPage;
