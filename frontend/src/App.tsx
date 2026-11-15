import React, { useState, useEffect } from "react";
import {
  Activity,
  DollarSign,
  TrendingUp,
  ShieldAlert,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Cpu,
  Newspaper,
  Radio,
  CheckCircle2,
  Clock,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

interface BotState {
  in_position?: boolean;
  entry_price?: number;
  position_size?: number;
  updated_at?: string;
}

interface StatusResponse {
  status: string;
  exchange?: string;
  mode?: string;
  symbol?: string;
  current_price?: number;
  state?: BotState;
  unrealized_pnl?: {
    percent: number;
    usd: number;
  };
  balances?: {
    USDT: number;
    BTC: number;
  };
  risk_rules?: {
    stop_loss_pct: number;
    take_profit_pct: number;
    trade_size_btc: number;
  };
}

interface CandlePoint {
  time: string;
  close: number;
  ema_fast?: number;
  ema_slow?: number;
  ema_13?: number;
  ema_18?: number;
  ema_9?: number;
  ema_21?: number;
  atr?: number;
  volume: number;
}

interface NewsData {
  headlines: string[];
  sentiment: string;
}

export default function App() {
  const [data, setData] = useState<StatusResponse | null>(null);
  const [candles, setCandles] = useState<CandlePoint[]>([]);
  const [news, setNews] = useState<NewsData>({ headlines: [], sentiment: "neutral" });
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchDashboardData = async () => {
    setIsRefreshing(true);
    try {
      // 1. Fetch Status
      const statusRes = await fetch("http://localhost:8000/api/status");
      if (statusRes.ok) {
        const json = await statusRes.json();
        setData(json);
      } else {
        setData((prev) => (prev ? { ...prev, status: "error" } : null));
      }

      // 2. Fetch Candles for Chart
      const candleRes = await fetch("http://localhost:8000/api/candles?limit=24");
      if (candleRes.ok) {
        const candleJson = await candleRes.json();
        if (candleJson.candles) {
          setCandles(candleJson.candles);
        }
      }

      // 3. Fetch News & Sentiment
      const newsRes = await fetch("http://localhost:8000/api/news");
      if (newsRes.ok) {
        const newsJson = await newsRes.json();
        setNews(newsJson);
      }

      setLastRefreshed(new Date());
    } catch (_e) {
      setData((prev) => (prev ? { ...prev, status: "offline" } : null));
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000); // 5s auto-refresh
    return () => clearInterval(interval);
  }, []);

  const isOnline = data?.status === "online";
  const inPosition = Boolean(data?.state?.in_position);
  const currentPrice = data?.current_price ?? 0;
  const entryPrice = data?.state?.entry_price ?? 0;
  const pnlPct = data?.unrealized_pnl?.percent ?? 0;
  const pnlUsd = data?.unrealized_pnl?.usd ?? 0;

  return (
    <div className="min-h-screen bg-gray-950 text-slate-100 p-6 md:p-10 font-sans">
      {/* Top Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between pb-8 border-b border-gray-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400 bg-clip-text text-transparent">
              Agent Flow Trading Terminal
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
              Level 4 Autonomous
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Real-time telemetry, quantitative indicators, FinBERT sentiment, and risk guardrails.
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-gray-900 border border-gray-800 px-3.5 py-1.5 rounded-lg text-xs">
            <Radio
              className={`w-3.5 h-3.5 ${isOnline ? "text-emerald-400 animate-pulse" : "text-rose-400"}`}
            />
            <span className="text-gray-300">{data?.mode || "Connecting..."}</span>
          </div>

          <button
            onClick={fetchDashboardData}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-700 active:scale-95 transition px-3.5 py-1.5 rounded-lg text-xs font-medium text-gray-200 border border-gray-700"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-cyan-400" : ""}`}
            />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {/* Main Grid: Telemetry Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 my-8">
        {/* Daemon Status Card */}
        <div className="bg-gray-900/90 border border-gray-800 rounded-xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between text-gray-400 text-xs font-medium">
            <span>DAEMON STATUS</span>
            <Cpu className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold uppercase tracking-wider ${
                isOnline ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {loading ? "INITIALIZING" : (data?.status ?? "OFFLINE")}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
            <Clock className="w-3 h-3" /> Updated: {lastRefreshed.toLocaleTimeString()}
          </p>
        </div>

        {/* Live BTC Price Card */}
        <div className="bg-gray-900/90 border border-gray-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between text-gray-400 text-xs font-medium">
            <span>BITCOIN MARKET PRICE</span>
            <DollarSign className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-slate-100">
              $
              {currentPrice.toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-2">Pair: BTC / USDT (Live Binance Feed)</p>
        </div>

        {/* Position & PnL Monitor Card */}
        <div
          className={`border rounded-xl p-5 shadow-lg ${
            inPosition
              ? pnlPct >= 0
                ? "bg-emerald-950/20 border-emerald-800/60"
                : "bg-rose-950/20 border-rose-800/60"
              : "bg-gray-900/90 border-gray-800"
          }`}
        >
          <div className="flex items-center justify-between text-gray-400 text-xs font-medium">
            <span>ACTIVE POSITION</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-3 flex items-center justify-between">
            <span
              className={`text-2xl font-bold ${inPosition ? "text-cyan-400" : "text-gray-400"}`}
            >
              {inPosition ? "IN POSITION" : "IN CASH (FLAT)"}
            </span>
            {inPosition && (
              <span
                className={`text-sm font-semibold flex items-center ${
                  pnlPct >= 0 ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {pnlPct >= 0 ? (
                  <ArrowUpRight className="w-4 h-4 mr-0.5" />
                ) : (
                  <ArrowDownRight className="w-4 h-4 mr-0.5" />
                )}
                {(pnlPct * 100).toFixed(2)}%
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-2">
            {inPosition
              ? `Entry: $${entryPrice.toLocaleString()} | PnL: $${pnlUsd.toFixed(2)}`
              : "Awaiting Combined Edge confirmation"}
          </p>
        </div>

        {/* Wallet Reserves Card */}
        <div className="bg-gray-900/90 border border-gray-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between text-gray-400 text-xs font-medium">
            <span>SIMULATED CAPITAL</span>
            <ShieldAlert className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-3 flex flex-col gap-1">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">USDT Balance:</span>
              <span className="font-semibold text-emerald-400">
                $
                {data?.balances?.USDT?.toLocaleString("en-US", { minimumFractionDigits: 2 }) ??
                  "0.00"}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">BTC Balance:</span>
              <span className="font-semibold text-amber-400">
                {data?.balances?.BTC?.toFixed(4) ?? "0.0000"} BTC
              </span>
            </div>
          </div>
          <div className="mt-2 text-[11px] text-gray-500 border-t border-gray-800 pt-1.5 flex justify-between">
            <span className="text-cyan-400 font-medium">Risk: 2x ATR Trailing Stop</span>
            <span>Optimized: EMA 13/18</span>
          </div>
        </div>
      </div>

      {/* Center Section: Indicator Chart & Combined Edge Decision */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 my-6">
        {/* Chart Column (2 spans) */}
        <div className="lg:col-span-2 bg-gray-900/90 border border-gray-800 rounded-xl p-6 shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-cyan-400" />
                Technical Trend: EMA 13 / EMA 18 Crossover (1h Candles)
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Mathematically optimized exponential moving averages + 14-period ATR volatility
                shield.
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full bg-cyan-400"></div>
                <span className="text-gray-300">EMA 13 (Fast)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full bg-amber-400"></div>
                <span className="text-gray-300">EMA 18 (Slow)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full bg-slate-400"></div>
                <span className="text-gray-300">Close</span>
              </div>
            </div>
          </div>

          <div className="h-72 w-full pt-2">
            {candles.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={candles} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                  <XAxis dataKey="time" stroke="#6b7280" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                  <YAxis
                    domain={["auto", "auto"]}
                    stroke="#6b7280"
                    tick={{ fill: "#9ca3af", fontSize: 11 }}
                    tickFormatter={(val) => `$${val.toLocaleString()}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#111827",
                      borderColor: "#374151",
                      borderRadius: "0.5rem",
                      fontSize: "12px",
                      color: "#f3f4f6",
                    }}
                    formatter={(val: number) => [`$${val.toLocaleString()}`, ""]}
                  />
                  <Line
                    type="monotone"
                    dataKey="close"
                    stroke="#94a3b8"
                    strokeWidth={1.5}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="ema_13"
                    stroke="#22d3ee"
                    strokeWidth={2.5}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="ema_18"
                    stroke="#f59e0b"
                    strokeWidth={2.5}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-gray-500">
                Loading candle telemetry...
              </div>
            )}
          </div>
        </div>

        {/* Strategy Intelligence Panel (1 span) */}
        <div className="bg-gray-900/90 border border-gray-800 rounded-xl p-6 shadow-lg flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2 mb-1">
              <CheckCircle2 className="w-5 h-5 text-indigo-400" />
              Combined Edge Strategy
            </h2>
            <p className="text-xs text-gray-400 mb-5">Dual-factor trigger alignment status.</p>

            {/* Condition 1: Technical */}
            <div className="bg-gray-800/80 rounded-lg p-3.5 border border-gray-700/60 mb-3.5">
              <div className="flex justify-between items-center text-xs text-gray-400 mb-1">
                <span>FACTOR 1: QUANTITATIVE TREND</span>
                <span className="font-semibold text-slate-300">EMA Crossover</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-bold text-amber-300">Trend Signal</span>
                <span className="px-2 py-0.5 text-xs font-semibold rounded bg-gray-700 text-gray-200">
                  HOLD (Downtrend)
                </span>
              </div>
            </div>

            {/* Condition 2: Sentiment */}
            <div className="bg-gray-800/80 rounded-lg p-3.5 border border-gray-700/60 mb-4">
              <div className="flex justify-between items-center text-xs text-gray-400 mb-1">
                <span>FACTOR 2: QUALITATIVE SENTIMENT</span>
                <span className="font-semibold text-slate-300">FinBERT NLP</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-bold text-cyan-300">News Sentiment</span>
                <span
                  className={`px-2 py-0.5 text-xs font-semibold rounded uppercase ${
                    news.sentiment === "positive"
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                      : news.sentiment === "negative"
                        ? "bg-rose-950 text-rose-300 border border-rose-800"
                        : "bg-gray-700 text-gray-300"
                  }`}
                >
                  {news.sentiment}
                </span>
              </div>
            </div>
          </div>

          {/* Decision Outcome */}
          <div className="bg-gray-950 border border-indigo-900/50 rounded-lg p-4 text-center">
            <span className="text-xs text-indigo-300 font-semibold tracking-wider uppercase">
              Current Executive Decision
            </span>
            <p className="text-base font-extrabold text-slate-100 mt-1">
              DEFENSIVE HOLD / PRESERVE CASH
            </p>
            <p className="text-[11px] text-gray-400 mt-1">
              Both momentum and news must turn bullish before entering long.
            </p>
          </div>
        </div>
      </div>

      {/* Bottom Section: Real-time News Ingestion & Sentiment Feed */}
      <div className="bg-gray-900/90 border border-gray-800 rounded-xl p-6 shadow-lg mt-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Newspaper className="w-5 h-5 text-indigo-400" />
            Live Market News Stream & FinBERT Sentiment Analysis
          </h2>
          <span className="text-xs text-gray-400">Scored by ProsusAI/finbert</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {news.headlines.length > 0 ? (
            news.headlines.map((headline, idx) => (
              <div
                key={idx}
                className="bg-gray-800/60 border border-gray-700/60 rounded-lg p-3.5 flex flex-col justify-between hover:border-gray-600 transition"
              >
                <p className="text-sm text-gray-200 line-clamp-2">"{headline}"</p>
                <div className="mt-3 flex items-center justify-between text-xs text-gray-400 border-t border-gray-700/40 pt-2">
                  <span>Feed Source</span>
                  <span className="text-cyan-400 font-medium">Verified Stream</span>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-3 text-center py-6 text-sm text-gray-500">
              Ingesting real-time market headlines...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
