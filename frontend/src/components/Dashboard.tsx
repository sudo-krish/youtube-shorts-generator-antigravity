import { useEffect, useState } from 'react';
import { api } from '../api';
import { Activity, Database, DollarSign, AlertCircle, RefreshCw, Layers } from 'lucide-react';

export const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<any>(null);
  const [balance, setBalance] = useState<any>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const usageRes = await api.getMetricsUsage();
      if (usageRes.status === 'success') {
        setMetrics(usageRes.data);
      }
      
      const balanceRes = await api.getDeepseekBalance();
      if (balanceRes.status === 'success') {
        setBalance(balanceRes.data);
      } else {
        setBalance({ error: balanceRes.message });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <RefreshCw className="w-10 h-10 text-aurora-cyan animate-spin" />
      </div>
    );
  }

  const usageData = metrics?.usage || [];
  const rateLimits = metrics?.rate_limits || [];
  
  const totalCost = usageData.reduce((acc: number, item: any) => acc + (item.total_cost || 0), 0);

  // Extract DeepSeek balance info safely
  let liveBalance = "N/A";
  if (balance && !balance.error && balance.balance_infos && balance.balance_infos.length > 0) {
     const info = balance.balance_infos[0];
     liveBalance = `${info.currency} ${info.total_balance}`;
  } else if (balance?.error) {
     liveBalance = "Error: " + balance.error;
  }

  return (
    <div className="w-full h-full p-8 overflow-y-auto custom-scrollbar">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-black bg-gradient-to-r from-aurora-cyan to-aurora-violet bg-clip-text text-transparent">
            AI Fleet Dashboard
          </h1>
          <p className="text-white/60 mt-2">Monitor Token Usage, Costs, and Rate Limits in Real-time</p>
        </div>
        <button 
          onClick={fetchDashboardData}
          className="p-3 bg-white/5 rounded-xl border border-white/10 hover:bg-white/10 transition-colors"
        >
          <RefreshCw className="w-5 h-5 text-white/80" />
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="glass-panel p-6 rounded-2xl flex items-start gap-4 border border-aurora-magenta/30 shadow-[0_0_15px_rgba(255,0,255,0.1)]">
          <div className="p-3 bg-aurora-magenta/20 rounded-xl">
            <DollarSign className="w-6 h-6 text-aurora-magenta" />
          </div>
          <div>
            <p className="text-sm font-bold text-white/50 uppercase tracking-wider mb-1">Total Engine Spend</p>
            <p className="text-3xl font-black text-white">${totalCost.toFixed(5)}</p>
            <p className="text-xs text-white/40 mt-2">Aggregated across all jobs</p>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl flex items-start gap-4 border border-aurora-cyan/30 shadow-[0_0_15px_rgba(0,255,255,0.1)]">
          <div className="p-3 bg-aurora-cyan/20 rounded-xl">
            <Database className="w-6 h-6 text-aurora-cyan" />
          </div>
          <div>
            <p className="text-sm font-bold text-white/50 uppercase tracking-wider mb-1">DeepSeek Live Balance</p>
            <p className="text-3xl font-black text-white">{liveBalance}</p>
            <p className="text-xs text-white/40 mt-2">Fetched via /user/balance</p>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl flex items-start gap-4 border border-amber-500/30 shadow-[0_0_15px_rgba(255,191,0,0.1)]">
          <div className="p-3 bg-amber-500/20 rounded-xl">
            <AlertCircle className="w-6 h-6 text-amber-500" />
          </div>
          <div>
            <p className="text-sm font-bold text-white/50 uppercase tracking-wider mb-1">429 Rate Limits Hit</p>
            <p className="text-3xl font-black text-white">{rateLimits.length}</p>
            <p className="text-xs text-white/40 mt-2">System throttles captured</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Token Usage Breakdown */}
        <div className="glass-panel p-6 rounded-2xl">
          <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-aurora-cyan" /> Model Consumption
          </h2>
          {usageData.length === 0 ? (
            <p className="text-white/40 py-8 text-center">No usage data logged yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="py-3 px-4 text-xs font-bold text-white/50 uppercase">Provider / Model</th>
                    <th className="py-3 px-4 text-xs font-bold text-white/50 uppercase">Reqs</th>
                    <th className="py-3 px-4 text-xs font-bold text-white/50 uppercase">Tokens (In/Out)</th>
                    <th className="py-3 px-4 text-xs font-bold text-white/50 uppercase">Est. Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {usageData.map((item: any, i: number) => (
                    <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Layers className="w-4 h-4 text-white/40" />
                          <div>
                            <p className="text-sm font-bold text-white">{item.model_name}</p>
                            <p className="text-xs text-white/40 uppercase tracking-wider">{item.provider}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm font-medium text-white">{item.total_requests}</td>
                      <td className="py-3 px-4">
                        <p className="text-xs text-white/60">I: {item.total_prompt_tokens?.toLocaleString()}</p>
                        <p className="text-xs text-white/60">O: {item.total_completion_tokens?.toLocaleString()}</p>
                      </td>
                      <td className="py-3 px-4 text-sm font-bold text-emerald-400">
                        ${(item.total_cost || 0).toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Rate Limits Feed */}
        <div className="glass-panel p-6 rounded-2xl">
          <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-amber-500" /> Recent Rate Limits
          </h2>
          {rateLimits.length === 0 ? (
            <p className="text-white/40 py-8 text-center">No rate limits hit yet. Smooth sailing!</p>
          ) : (
            <div className="space-y-3 max-h-[400px] overflow-y-auto custom-scrollbar pr-2">
              {rateLimits.map((limit: any, i: number) => (
                <div key={i} className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-bold px-2 py-1 bg-amber-500/20 text-amber-400 rounded-md">
                      {limit.model_name}
                    </span>
                    <span className="text-xs text-white/40">
                      {new Date(limit.timestamp * 1000).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm text-white/80 font-mono overflow-hidden text-ellipsis line-clamp-3">
                    {limit.error_message}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
