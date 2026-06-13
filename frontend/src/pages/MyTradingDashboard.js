import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../components/ui/dialog";
import {
  Activity, TrendingUp, TrendingDown, Wallet, Power, ShieldCheck,
  RefreshCw, ExternalLink, AlertTriangle, Brain, X, Clock,
} from "lucide-react";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL;

export default function MyTradingDashboard({ user }) {
  const [status, setStatus] = useState(null);
  const [account, setAccount] = useState(null);
  const [stocks, setStocks] = useState([]);
  const [trades, setTrades] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [settings, setSettings] = useState({ max_position_pct: 20, daily_loss_limit_pct: 5, cooldown_minutes: 5, agent_running: false });
  const [clock, setClock] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showConnect, setShowConnect] = useState(false);
  const [apiKeyId, setApiKeyId] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [paperMode, setPaperMode] = useState(true);
  // AI suggest dialog
  const [aiTicker, setAiTicker] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState(null);
  // Manual trade dialog
  const [tradeOpen, setTradeOpen] = useState(false);
  const [tradeTicker, setTradeTicker] = useState("");
  const [tradeSide, setTradeSide] = useState("buy");
  const [tradeNotional, setTradeNotional] = useState("50");
  const [tradeBusy, setTradeBusy] = useState(false);

  const token = localStorage.getItem("token");
  const authHeaders = { Authorization: `Bearer ${token}` };

  const load = async () => {
    setLoading(true);
    try {
      const [s, a, h, t, sg, st] = await Promise.all([
        fetch(`${API}/api/trading/status`,         { headers: authHeaders }).then(r => r.json()),
        fetch(`${API}/api/trading/account`,        { headers: authHeaders }).then(r => r.json()),
        fetch(`${API}/api/trading/halal-stocks`,   { headers: authHeaders }).then(r => r.json()),
        fetch(`${API}/api/trading/recent-trades`,  { headers: authHeaders }).then(r => r.json()),
        fetch(`${API}/api/trading/ai-suggestions`, { headers: authHeaders }).then(r => r.json()),
        fetch(`${API}/api/trading/settings`,       { headers: authHeaders }).then(r => r.json()),
      ]);
      setStatus(s); setAccount(a); setStocks(h.stocks || []); setTrades(t.trades || []);
      setSuggestions(sg.suggestions || []);
      if (st?.ok) setSettings({
        max_position_pct: st.max_position_pct, daily_loss_limit_pct: st.daily_loss_limit_pct,
        cooldown_minutes: st.cooldown_minutes, agent_running: st.agent_running,
      });
      if (s.connected) {
        try {
          const cl = await fetch(`${API}/api/trading/market-clock`, { headers: authHeaders }).then(r => r.json());
          if (cl?.ok) setClock(cl);
        } catch { /* market clock optional */ }
      }
    } catch (e) {
      toast.error("فشل تحميل بيانات التداول");
    }
    setLoading(false);
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, []);

  const saveCreds = async () => {
    if (!apiKeyId || !secretKey) { toast.error("API Key + Secret مطلوبان"); return; }
    try {
      const r = await fetch(`${API}/api/trading/connect`, {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ api_key_id: apiKeyId, secret_key: secretKey, paper: paperMode }),
      }).then(r => r.json());
      if (r.ok) { toast.success("تم ربط Alpaca بنجاح"); setShowConnect(false); setApiKeyId(""); setSecretKey(""); await load(); }
      else toast.error(r.detail || "فشل الربط");
    } catch { toast.error("فشل الربط"); }
  };

  const disconnect = async () => {
    if (!window.confirm("متأكد من فصل حساب Alpaca؟")) return;
    await fetch(`${API}/api/trading/disconnect`, { method: "POST", headers: authHeaders });
    toast.success("تم الفصل");
    load();
  };

  const askAI = async (ticker, autoExecute = false) => {
    setAiTicker(ticker); setAiLoading(true); setAiResult(null);
    try {
      const r = await fetch(`${API}/api/trading/ai-suggest`, {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, auto_execute: autoExecute, max_notional: 100 }),
      });
      const data = await r.json();
      if (!r.ok) { toast.error(data.detail || "AI فشل"); setAiResult({ error: data.detail }); }
      else { setAiResult(data); if (data.executed_trade?.order_id) { toast.success(`AI نفّذ ${ticker} ${data.decision.action}`); load(); } }
    } catch (e) { toast.error("AI engine error"); setAiResult({ error: String(e) }); }
    setAiLoading(false);
  };

  const submitTrade = async () => {
    if (!tradeTicker || !tradeNotional) { toast.error("املأ الحقول"); return; }
    setTradeBusy(true);
    try {
      const r = await fetch(`${API}/api/trading/trade`, {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: tradeTicker, side: tradeSide, notional: parseFloat(tradeNotional) }),
      });
      const data = await r.json();
      if (!r.ok) toast.error(data.detail || "فشل إرسال الأمر");
      else { toast.success(`تم إرسال أمر ${tradeSide} ${tradeTicker}`); setTradeOpen(false); load(); }
    } catch { toast.error("فشل إرسال الأمر"); }
    setTradeBusy(false);
  };

  const closePos = async (ticker) => {
    if (!window.confirm(`إغلاق مركز ${ticker} بالكامل؟`)) return;
    try {
      const r = await fetch(`${API}/api/trading/close-position/${ticker}`, { method: "POST", headers: authHeaders });
      const data = await r.json();
      if (!r.ok) toast.error(data.detail || "فشل");
      else { toast.success(`تم إغلاق ${ticker}`); load(); }
    } catch { toast.error("فشل"); }
  };

  const saveSettings = async () => {
    try {
      const r = await fetch(`${API}/api/trading/settings`, {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      }).then(r => r.json());
      if (r.ok) toast.success("تم حفظ الإعدادات"); else toast.error("فشل");
    } catch { toast.error("فشل"); }
  };

  const openTradeDialog = (ticker, side = "buy") => {
    setTradeTicker(ticker); setTradeSide(side); setTradeNotional("50"); setTradeOpen(true);
  };

  const isConnected = status?.connected;
  const equity = account?.equity ?? 0;
  const pnl = account?.daily_pnl ?? 0;
  const pnlPct = account?.daily_pnl_pct ?? 0;
  const marketUp = pnl >= 0;
  const marketOpen = clock?.is_open;
  const positions = account?.positions || [];

  return (
    <div dir="rtl" className="min-h-screen bg-gradient-to-br from-[#0a0a14] via-[#0f0f17] to-[#13131c] text-white p-6 lg:p-10">
      <div className="max-w-7xl mx-auto">
        {/* ── Header ── */}
        <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-[#a78bfa] to-[#7c3aed] bg-clip-text text-transparent">
              📈 محفظتي الذكية
            </h1>
            <p className="text-gray-400 mt-1 text-sm">نظام تداول AI شخصي — Halal stocks فقط ✓</p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            {isConnected && clock && (
              <Badge className={marketOpen ? "bg-emerald-700" : "bg-gray-700"} data-testid="market-clock-badge">
                <Clock className="w-3 h-3 ml-1" /> {marketOpen ? "السوق مفتوح" : "السوق مغلق"}
              </Badge>
            )}
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
          <MetricCard icon={<Wallet className="w-5 h-5" />} label="الرصيد الإجمالي" value={`$${equity.toFixed(2)}`} accent="#a78bfa" />
          <MetricCard
            icon={marketUp ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
            label="ربح اليوم"
            value={`${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}`}
            subtitle={`${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%`}
            accent={marketUp ? "#10b981" : "#ef4444"}
          />
          <MetricCard icon={<Activity className="w-5 h-5" />} label="صفقات نشطة" value={positions.length} accent="#a78bfa" />
          <MetricCard icon={<ShieldCheck className="w-5 h-5" />} label="أسهم حلال" value={status?.halal_tickers_count ?? 0} subtitle="مفلترة شرعياً" accent="#10b981" />
        </div>

        {/* ── Mood banner ── */}
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
              <Button size="sm" onClick={() => setShowConnect(true)} className="bg-[#7c3aed] hover:bg-[#6d28d9]" data-testid="connect-btn">
                ربط Alpaca
              </Button>
            )}
          </CardContent>
        </Card>

        {/* ── Tabs ── */}
        <Tabs defaultValue="overview">
          <TabsList className="bg-[#1a1a26] border border-[#2a2a36]">
            <TabsTrigger value="overview" data-testid="tab-overview">نظرة عامة</TabsTrigger>
            <TabsTrigger value="stocks" data-testid="tab-stocks">قائمة الحلال</TabsTrigger>
            <TabsTrigger value="positions" data-testid="tab-positions">المراكز ({positions.length})</TabsTrigger>
            <TabsTrigger value="trades" data-testid="tab-trades">سجل الصفقات</TabsTrigger>
            <TabsTrigger value="ai-history" data-testid="tab-ai-history">تحليلات AI</TabsTrigger>
            <TabsTrigger value="settings" data-testid="tab-settings">الإعدادات</TabsTrigger>
          </TabsList>

          {/* Overview */}
          <TabsContent value="overview" className="mt-4">
            <Card className="bg-[#15151f] border-[#2a2a36]">
              <CardHeader><CardTitle className="text-lg">حالة الـ AI Engine</CardTitle></CardHeader>
              <CardContent className="space-y-3 text-sm text-gray-300">
                {!isConnected ? <EmptyState onConnect={() => setShowConnect(true)} /> : (
                  <>
                    <Row label="الحساب" value={status?.paper_mode ? "Paper (تجريبي)" : "Live"} />
                    <Row label="الـ AI" value={settings.agent_running ? "🟢 شغّال" : "⏸️ متوقف"} />
                    <Row label="آخر تحديث" value={new Date(status?.as_of || "").toLocaleString("ar-SA")} />
                    <Row label="قوة الشراء" value={`$${(account?.buying_power || 0).toFixed(2)}`} />
                    <Row label="حالة الحساب" value={account?.status || "—"} />
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Halal stocks */}
          <TabsContent value="stocks" className="mt-4">
            <Card className="bg-[#15151f] border-[#2a2a36]">
              <CardHeader><CardTitle className="text-lg">قائمة الأسهم الحلال المعتمدة ({stocks.length})</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {stocks.map(s => (
                    <div key={s.t} className="bg-[#1a1a26] border border-[#2a2a36] rounded-lg p-3 hover:border-[#7c3aed] transition" data-testid={`stock-${s.t}`}>
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <div className="font-bold text-lg text-[#a78bfa]">{s.t}</div>
                          <div className="text-xs text-gray-400">{s.n}</div>
                        </div>
                        <Badge variant="outline" className="text-[10px] border-emerald-500 text-emerald-400">{s.s}</Badge>
                      </div>
                      {isConnected && (
                        <div className="flex gap-2 mt-2">
                          <Button size="sm" variant="outline" className="flex-1 border-[#7c3aed] text-[#a78bfa] hover:bg-[#7c3aed]/10"
                                  onClick={() => askAI(s.t)} data-testid={`ai-${s.t}`}>
                            <Brain className="w-3 h-3 ml-1" /> AI
                          </Button>
                          <Button size="sm" className="flex-1 bg-emerald-700 hover:bg-emerald-600"
                                  onClick={() => openTradeDialog(s.t, "buy")} data-testid={`buy-${s.t}`}>شراء</Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Positions */}
          <TabsContent value="positions" className="mt-4">
            <Card className="bg-[#15151f] border-[#2a2a36]">
              <CardHeader><CardTitle className="text-lg">المراكز المفتوحة</CardTitle></CardHeader>
              <CardContent>
                {!isConnected ? (
                  <p className="text-gray-500 text-sm py-8 text-center">اربط Alpaca أولاً.</p>
                ) : positions.length === 0 ? (
                  <p className="text-gray-500 text-sm py-8 text-center">لا توجد مراكز مفتوحة حالياً.</p>
                ) : (
                  <div className="space-y-2">
                    {positions.map((p, i) => {
                      const up = p.unrealized_pl >= 0;
                      return (
                        <div key={i} className="bg-[#1a1a26] rounded-lg p-3 flex items-center justify-between" data-testid={`pos-${p.ticker}`}>
                          <div className="flex items-center gap-4">
                            <div className="font-bold text-lg text-[#a78bfa] w-16">{p.ticker}</div>
                            <div className="text-xs text-gray-400">
                              <div>الكمية: {p.qty}</div>
                              <div>دخول: ${p.avg_entry?.toFixed(2)}</div>
                            </div>
                            <div className="text-xs text-gray-400">
                              <div>الحالي: ${p.current_price?.toFixed(2) || "—"}</div>
                              <div>القيمة: ${p.market_value?.toFixed(2) || "—"}</div>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className={`text-sm font-bold ${up ? "text-emerald-400" : "text-red-400"}`}>
                              {up ? "+" : ""}${p.unrealized_pl?.toFixed(2)} ({p.unrealized_plpc?.toFixed(2)}%)
                            </div>
                            <Button size="sm" variant="outline" className="border-[#7c3aed] text-[#a78bfa]" onClick={() => askAI(p.ticker)} data-testid={`pos-ai-${p.ticker}`}>
                              <Brain className="w-3 h-3 ml-1" /> AI
                            </Button>
                            <Button size="sm" variant="destructive" onClick={() => closePos(p.ticker)} data-testid={`pos-close-${p.ticker}`}>
                              <X className="w-3 h-3 ml-1" /> إغلاق
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Trades */}
          <TabsContent value="trades" className="mt-4">
            <Card className="bg-[#15151f] border-[#2a2a36]">
              <CardHeader><CardTitle className="text-lg">سجل الصفقات الأخيرة</CardTitle></CardHeader>
              <CardContent>
                {trades.length === 0 ? (
                  <p className="text-gray-500 text-sm py-8 text-center">لا توجد صفقات بعد.</p>
                ) : (
                  <div className="space-y-2">
                    {trades.map((t, i) => (
                      <div key={i} className="bg-[#1a1a26] rounded-lg p-3 flex justify-between text-sm" data-testid={`trade-row-${i}`}>
                        <div className="flex items-center gap-3">
                          <span className="font-bold text-[#a78bfa] w-14">{t.ticker}</span>
                          <Badge className={t.side === "buy" ? "bg-emerald-700" : t.side === "sell" ? "bg-red-700" : "bg-gray-700"}>
                            {t.side === "buy" ? "🟢 شراء" : t.side === "sell" ? "🔴 بيع" : "إغلاق"}
                          </Badge>
                          {t.ai_initiated && <Badge variant="outline" className="border-[#a78bfa] text-[#a78bfa]"><Brain className="w-3 h-3 ml-1" />AI</Badge>}
                          <span className="text-gray-400">{t.qty ? `${t.qty} وحدة` : t.notional ? `$${t.notional}` : ""}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-gray-400 text-xs">{t.status}</span>
                          <span className="text-gray-500 text-xs">{new Date(t.ts).toLocaleString("ar-SA")}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* AI history */}
          <TabsContent value="ai-history" className="mt-4">
            <Card className="bg-[#15151f] border-[#2a2a36]">
              <CardHeader><CardTitle className="text-lg">سجل تحليلات الـ AI</CardTitle></CardHeader>
              <CardContent>
                {suggestions.length === 0 ? (
                  <p className="text-gray-500 text-sm py-8 text-center">لا توجد تحليلات بعد.</p>
                ) : (
                  <div className="space-y-2">
                    {suggestions.map((s, i) => {
                      const d = s.decision || {};
                      const colorMap = { buy: "bg-emerald-700", sell: "bg-red-700", hold: "bg-amber-700" };
                      return (
                        <div key={i} className="bg-[#1a1a26] rounded-lg p-3 text-sm" data-testid={`ai-row-${i}`}>
                          <div className="flex justify-between items-center mb-1">
                            <div className="flex items-center gap-3">
                              <span className="font-bold text-[#a78bfa]">{s.ticker}</span>
                              <Badge className={colorMap[d.action] || "bg-gray-700"}>{d.action?.toUpperCase()}</Badge>
                              <span className="text-xs text-gray-400">ثقة: {d.confidence}%</span>
                              {s.executed && <Badge variant="outline" className="border-emerald-500 text-emerald-400">نُفّذ</Badge>}
                            </div>
                            <span className="text-gray-500 text-xs">{new Date(s.ts).toLocaleString("ar-SA")}</span>
                          </div>
                          <p className="text-gray-300 text-xs leading-relaxed">{d.reasoning}</p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Settings */}
          <TabsContent value="settings" className="mt-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
                        <a href="https://alpaca.markets" target="_blank" rel="noopener noreferrer" className="text-[#a78bfa] underline inline-flex items-center gap-1">
                          Alpaca <ExternalLink className="w-3 h-3" />
                        </a>
                      </p>
                      <Input value={apiKeyId} onChange={e => setApiKeyId(e.target.value)} placeholder="API Key ID" className="bg-[#0a0a14] border-[#2a2a36]" data-testid="api-key-input" />
                      <Input type="password" value={secretKey} onChange={e => setSecretKey(e.target.value)} placeholder="Secret Key" className="bg-[#0a0a14] border-[#2a2a36]" data-testid="secret-key-input" />
                      <div className="flex items-center justify-between bg-[#1a1a26] p-3 rounded">
                        <div>
                          <div className="text-sm font-semibold">Paper Trading</div>
                          <div className="text-xs text-gray-500">فلوس وهمية للتجربة (موصى به أول 7 أيام)</div>
                        </div>
                        <Switch checked={paperMode} onCheckedChange={setPaperMode} data-testid="paper-switch" />
                      </div>
                      <Button onClick={saveCreds} className="bg-[#7c3aed] hover:bg-[#6d28d9] w-full" data-testid="save-creds-btn">
                        حفظ وربط
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="bg-[#15151f] border-[#2a2a36]">
                <CardHeader><CardTitle className="text-lg">حدود المخاطرة</CardTitle></CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <NumField label="أقصى % لكل سهم من رأس المال" value={settings.max_position_pct}
                            onChange={v => setSettings({ ...settings, max_position_pct: v })} testid="max-position-pct" />
                  <NumField label="حد الخسارة اليومية (%)" value={settings.daily_loss_limit_pct}
                            onChange={v => setSettings({ ...settings, daily_loss_limit_pct: v })} testid="daily-loss-limit" />
                  <NumField label="فترة التهدئة بين الصفقات (دقائق)" value={settings.cooldown_minutes}
                            onChange={v => setSettings({ ...settings, cooldown_minutes: v })} testid="cooldown-minutes" />
                  <Button onClick={saveSettings} className="bg-[#7c3aed] hover:bg-[#6d28d9] w-full mt-2" data-testid="save-settings-btn">
                    حفظ
                  </Button>
                </CardContent>
              </Card>
            </div>

            <div className="mt-4 p-3 bg-amber-950/30 border border-amber-700/40 rounded text-xs text-amber-200 flex gap-2">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>
                ابدأ بـ Paper Trading لمدة 7 أيام للتأكد من الاستراتيجية قبل ضخ أموال حقيقية.
                الـ AI يفلتر الأسهم شرعياً تلقائياً (لا فوائد ربوية، لا قطاعات محرمة).
              </span>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* ── AI suggest dialog ── */}
      <Dialog open={!!aiTicker} onOpenChange={(o) => { if (!o) { setAiTicker(null); setAiResult(null); } }}>
        <DialogContent className="bg-[#15151f] border-[#2a2a36] text-white max-w-lg" dir="rtl" data-testid="ai-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-[#a78bfa]" /> تحليل AI لسهم {aiTicker}
            </DialogTitle>
          </DialogHeader>
          {aiLoading && <div className="py-8 text-center text-gray-400">⏳ يحلل Claude البيانات...</div>}
          {!aiLoading && aiResult?.error && (
            <div className="py-4 text-red-400 text-sm">خطأ: {aiResult.error}</div>
          )}
          {!aiLoading && aiResult?.decision && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Badge className={
                  aiResult.decision.action === "buy" ? "bg-emerald-700"
                  : aiResult.decision.action === "sell" ? "bg-red-700"
                  : "bg-amber-700"
                }>
                  {aiResult.decision.action?.toUpperCase()}
                </Badge>
                <span className="text-sm text-gray-300">ثقة: <b>{aiResult.decision.confidence}%</b></span>
                {aiResult.decision.suggested_notional_usd && (
                  <span className="text-sm text-gray-300">المقترح: ${aiResult.decision.suggested_notional_usd}</span>
                )}
              </div>
              <div className="bg-[#1a1a26] rounded p-3 text-sm leading-relaxed">{aiResult.decision.reasoning}</div>
              {aiResult.executed_trade?.order_id && (
                <div className="text-xs text-emerald-400">✅ تم تنفيذ الصفقة (order_id: {aiResult.executed_trade.order_id})</div>
              )}
              {aiResult.executed_trade?.error && (
                <div className="text-xs text-red-400">❌ فشل التنفيذ: {aiResult.executed_trade.error}</div>
              )}
              <DialogFooter className="gap-2">
                {(aiResult.decision.action === "buy" || aiResult.decision.action === "sell") && !aiResult.executed_trade && (
                  <Button onClick={() => askAI(aiTicker, true)} className="bg-emerald-700 hover:bg-emerald-600" data-testid="ai-execute-btn">
                    نفّذ الآن
                  </Button>
                )}
                <Button variant="outline" onClick={() => { openTradeDialog(aiTicker, aiResult.decision.action === "sell" ? "sell" : "buy"); setAiTicker(null); }}>
                  أمر يدوي
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ── Manual trade dialog ── */}
      <Dialog open={tradeOpen} onOpenChange={setTradeOpen}>
        <DialogContent className="bg-[#15151f] border-[#2a2a36] text-white max-w-md" dir="rtl" data-testid="trade-dialog">
          <DialogHeader><DialogTitle>أمر يدوي — {tradeTicker}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="flex gap-2">
              <Button onClick={() => setTradeSide("buy")} className={tradeSide === "buy" ? "bg-emerald-700 hover:bg-emerald-600 flex-1" : "bg-[#1a1a26] flex-1"} data-testid="side-buy">شراء</Button>
              <Button onClick={() => setTradeSide("sell")} className={tradeSide === "sell" ? "bg-red-700 hover:bg-red-600 flex-1" : "bg-[#1a1a26] flex-1"} data-testid="side-sell">بيع</Button>
            </div>
            <div>
              <label className="text-xs text-gray-400">المبلغ بالدولار (Notional)</label>
              <Input type="number" value={tradeNotional} onChange={e => setTradeNotional(e.target.value)} className="bg-[#0a0a14] border-[#2a2a36]" data-testid="trade-notional" />
            </div>
            <div className="text-xs text-gray-500">سيتم إرسال الأمر كـ Market Order — Day TIF.</div>
          </div>
          <DialogFooter>
            <Button onClick={submitTrade} disabled={tradeBusy} className="bg-[#7c3aed] hover:bg-[#6d28d9]" data-testid="submit-trade-btn">
              {tradeBusy ? "..." : "إرسال الأمر"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Initial connect dialog ── */}
      <Dialog open={showConnect} onOpenChange={setShowConnect}>
        <DialogContent className="bg-[#15151f] border-[#2a2a36] text-white max-w-md" dir="rtl">
          <DialogHeader><DialogTitle>ربط Alpaca</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input value={apiKeyId} onChange={e => setApiKeyId(e.target.value)} placeholder="API Key ID" className="bg-[#0a0a14] border-[#2a2a36]" data-testid="dlg-api-key" />
            <Input type="password" value={secretKey} onChange={e => setSecretKey(e.target.value)} placeholder="Secret Key" className="bg-[#0a0a14] border-[#2a2a36]" data-testid="dlg-secret" />
            <div className="flex items-center justify-between bg-[#1a1a26] p-3 rounded">
              <span className="text-sm">Paper Trading</span>
              <Switch checked={paperMode} onCheckedChange={setPaperMode} data-testid="dlg-paper" />
            </div>
          </div>
          <DialogFooter>
            <Button onClick={saveCreds} className="bg-[#7c3aed] hover:bg-[#6d28d9]" data-testid="dlg-save">حفظ وربط</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
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

const NumField = ({ label, value, onChange, testid }) => (
  <div>
    <label className="text-xs text-gray-400 block mb-1">{label}</label>
    <Input type="number" value={value} onChange={e => onChange(parseFloat(e.target.value) || 0)}
           className="bg-[#0a0a14] border-[#2a2a36]" data-testid={testid} />
  </div>
);

const EmptyState = ({ onConnect }) => (
  <div className="py-10 text-center space-y-3">
    <div className="text-5xl">🔌</div>
    <p className="text-gray-300">لم تربط Alpaca بعد</p>
    <Button onClick={onConnect} className="bg-[#7c3aed] hover:bg-[#6d28d9]" data-testid="empty-connect-btn">
      ابدأ الآن
    </Button>
  </div>
);
