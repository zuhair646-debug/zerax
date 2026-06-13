import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import {
  Activity, TrendingUp, TrendingDown, Wallet, Power, ShieldCheck,
  RefreshCw, ExternalLink, AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL;

export default function MyTradingDashboard({ user }) {
  const [status, setStatus] = useState(null);
  const [account, setAccount] = useState(null);
  const [stocks, setStocks] = useState([]);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showConnect, setShowConnect] = useState(false);
  const [apiKeyId, setApiKeyId] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [paperMode, setPaperMode] = useState(true);

  const token = localStorage.getItem("token");
  const authHeaders = { Authorization: `Bearer ${token}` };

  const load = async () => {
    setLoading(true);
    try {
      const [s, a, h, t] = await Promise.all([
        fetch(`${API}/api/trading/status`,        { headers: authHeaders }).then(r => r.json()),
        fetch(`${API}/api/trading/account`,       { headers: authHeaders }).then(r => r.json()),
        fetch(`${API}/api/trading/halal-stocks`,  { headers: authHeaders }).then(r => r.json()),
        fetch(`${API}/api/trading/recent-trades`, { headers: authHeaders }).then(r => r.json()),
      ]);
      setStatus(s); setAccount(a); setStocks(h.stocks || []); setTrades(t.trades || []);
    } catch (e) {
      toast.error("فشل تحميل بيانات التداول");
    }
    setLoading(false);
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const saveCreds = async () => {
    if (!apiKeyId || !secretKey) { toast.error("API Key + Secret مطلوبان"); return; }
    try {
      const r = await fetch(`${API}/api/trading/connect`, {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ api_key_id: apiKeyId, secret_key: secretKey, paper: paperMode }),
      }).then(r => r.json());
      if (r.ok) { toast.success("تم ربط Alpaca بنجاح"); setShowConnect(false); await load(); }
    } catch { toast.error("فشل الربط"); }
  };

  const disconnect = async () => {
    if (!window.confirm("متأكد من فصل حساب Alpaca؟")) return;
    await fetch(`${API}/api/trading/disconnect`, { method: "POST", headers: authHeaders });
    toast.success("تم الفصل");
    load();
  };

  const isConnected = status?.connected;
  const equity = account?.equity ?? 0;
  const pnl = account?.daily_pnl ?? 0;
  const pnlPct = account?.daily_pnl_pct ?? 0;
  const marketUp = pnl >= 0;

  return (
    <div dir="rtl" className="min-h-screen bg-gradient-to-br from-[#0a0a14] via-[#0f0f17] to-[#13131c] text-white p-6 lg:p-10">
      {/* ── Header ── */}
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-[#a78bfa] to-[#7c3aed] bg-clip-text text-transparent">
              📈 محفظتي الذكية
            </h1>
            <p className="text-gray-400 mt-1 text-sm">
              نظام تداول AI شخصي — Halal stocks فقط ✓
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge className={isConnected ? "bg-emerald-600" : "bg-red-600"} data-testid="conn-badge">
              {isConnected ? "● Connected" : "● Not connected"}
            </Badge>
            {isConnected && (
              <Badge variant="outline" className="border-[#7c3aed] text-[#a78bfa]">
                {status?.paper_mode ? "Paper Trading" : "LIVE"}
              </Badge>
            )}
            <Button size="sm" variant="ghost" onClick={load} data-testid="refresh-btn">
              <RefreshCw className="w-4 h-4 ml-2" /> تحديث
            </Button>
          </div>
        </div>

        {/* ── Top metrics ── */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <MetricCard icon={<Wallet className="w-5 h-5" />} label="الرصيد الإجمالي"
                       value={`$${equity.toFixed(2)}`} accent="#a78bfa" />
          <MetricCard icon={marketUp ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                       label="ربح اليوم"
                       value={`${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}`}
                       subtitle={`${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%`}
                       accent={marketUp ? "#10b981" : "#ef4444"} />
          <MetricCard icon={<Activity className="w-5 h-5" />} label="صفقات نشطة"
                       value={(account?.positions || []).length} accent="#a78bfa" />
          <MetricCard icon={<ShieldCheck className="w-5 h-5" />} label="أسهم حلال"
                       value={status?.halal_tickers_count ?? 0}
                       subtitle="مفلترة شرعياً" accent="#10b981" />
        </div>

        {/* ── Market mood banner ── */}
        <Card className={`mb-6 border-0 ${marketUp ? "bg-emerald-950/40" : "bg-red-950/40"}`}>
          <CardContent className="py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${marketUp ? "bg-emerald-400" : "bg-red-400"} animate-pulse`} />
              <span className="text-sm">
                {isConnected
                  ? (marketUp ? "السوق إيجابي اليوم — الـ AI يبحث عن فرص شراء" : "السوق سلبي اليوم — الـ AI متحفظ")
                  : "اربط حسابك في Alpaca لتفعيل النظام"}
              </span>
            </div>
            {!isConnected && (
              <Button size="sm" onClick={() => setShowConnect(true)}
                       className="bg-[#7c3aed] hover:bg-[#6d28d9]" data-testid="connect-btn">
                ربط Alpaca
              </Button>
            )}
          </CardContent>
        </Card>

        {/* ── Tabs ── */}
        <Tabs defaultValue="overview">
          <TabsList className="bg-[#1a1a26] border border-[#2a2a36]">
            <TabsTrigger value="overview">نظرة عامة</TabsTrigger>
            <TabsTrigger value="stocks">قائمة الحلال</TabsTrigger>
            <TabsTrigger value="trades">سجل الصفقات</TabsTrigger>
            <TabsTrigger value="settings">الإعدادات</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-4">
            <Card className="bg-[#15151f] border-[#2a2a36]">
              <CardHeader>
                <CardTitle className="text-lg">حالة الـ AI Engine</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-gray-300">
                {!isConnected ? (
                  <EmptyState onConnect={() => setShowConnect(true)} />
                ) : (
                  <>
                    <Row label="الحساب" value={status?.paper_mode ? "Paper (تجريبي)" : "Live"} />
                    <Row label="الـ AI" value={status?.agent_running ? "🟢 شغّال" : "⏸️ متوقف"} />
                    <Row label="آخر تحديث" value={new Date(status?.as_of || "").toLocaleString("ar-SA")} />
                    <Row label="عدد الأسهم الحلال" value={status?.halal_tickers_count} />
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="stocks" className="mt-4">
            <Card className="bg-[#15151f] border-[#2a2a36]">
              <CardHeader>
                <CardTitle className="text-lg">قائمة الأسهم الحلال المعتمدة ({stocks.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {stocks.map(s => (
                    <div key={s.t}
                          className="bg-[#1a1a26] border border-[#2a2a36] rounded-lg p-3 hover:border-[#7c3aed] transition"
                          data-testid={`stock-${s.t}`}>
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-bold text-lg text-[#a78bfa]">{s.t}</div>
                          <div className="text-xs text-gray-400">{s.n}</div>
                        </div>
                        <Badge variant="outline" className="text-[10px] border-emerald-500 text-emerald-400">
                          {s.s}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="trades" className="mt-4">
            <Card className="bg-[#15151f] border-[#2a2a36]">
              <CardHeader>
                <CardTitle className="text-lg">سجل الصفقات الأخيرة</CardTitle>
              </CardHeader>
              <CardContent>
                {trades.length === 0 ? (
                  <p className="text-gray-500 text-sm py-8 text-center">لا توجد صفقات بعد. ابدأ بربط Alpaca.</p>
                ) : (
                  <div className="space-y-2">
                    {trades.map((t, i) => (
                      <div key={i} className="bg-[#1a1a26] rounded-lg p-3 flex justify-between text-sm">
                        <span>{t.ticker} {t.side === "buy" ? "🟢" : "🔴"} {t.qty}</span>
                        <span>${t.price?.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="settings" className="mt-4">
            <Card className="bg-[#15151f] border-[#2a2a36]">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-400" /> ربط Alpaca
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {isConnected ? (
                  <>
                    <div className="text-sm text-gray-300">الحساب مربوط ({status?.paper_mode ? "Paper" : "Live"})</div>
                    <Button onClick={disconnect} variant="destructive" data-testid="disconnect-btn">
                      <Power className="w-4 h-4 ml-2" /> فصل الحساب
                    </Button>
                  </>
                ) : (
                  <div className="space-y-3">
                    <p className="text-sm text-gray-400">
                      احصل على API keys من{" "}
                      <a href="https://alpaca.markets" target="_blank" rel="noopener noreferrer"
                          className="text-[#a78bfa] underline inline-flex items-center gap-1">
                        Alpaca <ExternalLink className="w-3 h-3" />
                      </a>
                    </p>
                    <Input value={apiKeyId} onChange={e => setApiKeyId(e.target.value)}
                            placeholder="API Key ID" className="bg-[#0a0a14] border-[#2a2a36]"
                            data-testid="api-key-input" />
                    <Input type="password" value={secretKey} onChange={e => setSecretKey(e.target.value)}
                            placeholder="Secret Key" className="bg-[#0a0a14] border-[#2a2a36]"
                            data-testid="secret-key-input" />
                    <div className="flex items-center justify-between bg-[#1a1a26] p-3 rounded">
                      <div>
                        <div className="text-sm font-semibold">Paper Trading</div>
                        <div className="text-xs text-gray-500">فلوس وهمية للتجربة (موصى به أول 7 أيام)</div>
                      </div>
                      <Switch checked={paperMode} onCheckedChange={setPaperMode}
                               data-testid="paper-switch" />
                    </div>
                    <Button onClick={saveCreds} className="bg-[#7c3aed] hover:bg-[#6d28d9] w-full"
                             data-testid="save-creds-btn">
                      حفظ وربط
                    </Button>
                  </div>
                )}

                <div className="mt-6 p-3 bg-amber-950/30 border border-amber-700/40 rounded text-xs text-amber-200 flex gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>
                    ابدأ بـ Paper Trading لمدة 7 أيام للتأكد من الاستراتيجية قبل ضخ أموال حقيقية.
                    الـ AI يفلتر الأسهم شرعياً تلقائياً (لا فوائد ربوية، لا قطاعات محرمة).
                  </span>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

const MetricCard = ({ icon, label, value, subtitle, accent }) => (
  <Card className="bg-[#15151f] border-[#2a2a36] hover:border-[#7c3aed] transition">
    <CardContent className="p-5">
      <div className="flex items-center justify-between mb-2 text-gray-400">
        <span className="text-xs">{label}</span>
        <span style={{ color: accent }}>{icon}</span>
      </div>
      <div className="text-2xl font-bold" style={{ color: accent }}>{value}</div>
      {subtitle && <div className="text-xs text-gray-500 mt-1">{subtitle}</div>}
    </CardContent>
  </Card>
);

const Row = ({ label, value }) => (
  <div className="flex justify-between items-center py-2 border-b border-[#2a2a36] last:border-0">
    <span className="text-gray-400">{label}</span>
    <span className="font-medium text-white">{value}</span>
  </div>
);

const EmptyState = ({ onConnect }) => (
  <div className="py-10 text-center space-y-3">
    <div className="text-5xl">🔌</div>
    <p className="text-gray-300">لم تربط Alpaca بعد</p>
    <Button onClick={onConnect} className="bg-[#7c3aed] hover:bg-[#6d28d9]"
             data-testid="empty-connect-btn">
      ابدأ الآن
    </Button>
  </div>
);
