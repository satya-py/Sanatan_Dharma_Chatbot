import React, { useState, useEffect } from "react";
import { LayoutDashboard, Database, Key, Server, RefreshCw, AlertCircle, FileText, Check, AlertTriangle } from "lucide-react";
import { adminService, type AdminMetrics } from "../services/api";

export const AdminDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [logs, setLogs] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linesCount, setLinesCount] = useState(100);

  const fetchMetricsAndLogs = async (quiet = false) => {
    if (!quiet) setIsLoading(true);
    setError(null);
    try {
      const [metricsData, logsData] = await Promise.all([
        adminService.getMetrics(),
        adminService.getLogs(linesCount)
      ]);
      setMetrics(metricsData);
      setLogs(logsData.logs);
    } catch (err) {
      console.error("Failed to load admin stats:", err);
      setError("Unable to retrieve administration metrics or server logs.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMetricsAndLogs();
  }, [linesCount]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchMetricsAndLogs(true);
  };

  return (
    <div className="flex-1 flex flex-col h-screen bg-stone-50/50 dark:bg-[#120a05] overflow-hidden">
      {/* Page Header */}
      <header className="h-16 border-b border-stone-200 dark:border-stone-800 bg-white/70 dark:bg-[#18110b]/70 backdrop-blur-md px-6 flex items-center justify-between z-10 flex-shrink-0">
        <div className="flex items-center gap-2">
          <LayoutDashboard className="w-5 h-5 text-saffron-500" />
          <span className="font-semibold text-stone-800 dark:text-stone-200">Admin Dashboard</span>
        </div>
        
        <button
          onClick={handleRefresh}
          disabled={isRefreshing || isLoading}
          className="p-2 rounded-xl bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 hover:bg-stone-250 dark:hover:bg-stone-700 text-stone-600 dark:text-stone-300 transition-all flex items-center gap-1.5 text-xs font-semibold disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </header>

      {/* Main Body */}
      <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6">
        {isLoading ? (
          <div className="text-center py-20 text-xs text-stone-400 dark:text-stone-600 animate-pulse">
            Loading administration statistics...
          </div>
        ) : error ? (
          <div className="max-w-4xl mx-auto p-4 bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded-2xl flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-xs font-semibold">{error}</span>
          </div>
        ) : !metrics ? null : (
          <div className="max-w-5xl mx-auto space-y-6">
            
            {/* Top Grid: DB Statistics & Hardware Health */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* Database Stats Card */}
              <div className="rounded-3xl border border-stone-200/50 dark:border-stone-800/40 bg-white dark:bg-[#18110b] p-6 space-y-4 shadow-sm">
                <div className="flex items-center gap-2 text-saffron-500 font-semibold text-sm">
                  <Database className="w-4 h-4" />
                  <span className="font-sans tracking-wide uppercase text-xs font-bold">Relational DB Stats</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-[10px] text-stone-400 block">Total Sessions</span>
                    <span className="text-lg font-bold text-stone-800 dark:text-stone-200">{metrics.db_stats.sessions}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-stone-400 block">Total Messages</span>
                    <span className="text-lg font-bold text-stone-800 dark:text-stone-200">{metrics.db_stats.messages}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-stone-400 block">Saved Bookmarks</span>
                    <span className="text-lg font-bold text-stone-800 dark:text-stone-200">{metrics.db_stats.bookmarks}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-stone-400 block">Database Size</span>
                    <span className="text-sm font-bold text-stone-800 dark:text-stone-200">{metrics.db_stats.db_size_kb} KB</span>
                  </div>
                </div>
              </div>

              {/* Vector DB Index Stats Card */}
              <div className="rounded-3xl border border-stone-200/50 dark:border-stone-800/40 bg-white dark:bg-[#18110b] p-6 space-y-4 shadow-sm">
                <div className="flex items-center gap-2 text-gold-550 dark:text-gold-400 font-semibold text-sm">
                  <Server className="w-4 h-4" />
                  <span className="font-sans tracking-wide uppercase text-xs font-bold">Vector DB Stats</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-[10px] text-stone-400 block">Gita Chunks</span>
                    <span className="text-lg font-bold text-stone-800 dark:text-stone-200">{metrics.vector_stats.gita_index_size}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-stone-400 block">Other Chunks</span>
                    <span className="text-lg font-bold text-stone-800 dark:text-stone-200">{metrics.vector_stats.scriptures_index_size}</span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-[10px] text-stone-400 block">Feedback Score Count</span>
                    <span className="text-sm font-bold text-stone-800 dark:text-stone-200">{metrics.db_stats.feedback} Submissions</span>
                  </div>
                </div>
              </div>

              {/* System & Hardware Health Card */}
              <div className="rounded-3xl border border-stone-200/50 dark:border-stone-800/40 bg-white dark:bg-[#18110b] p-6 space-y-4 shadow-sm">
                <div className="flex items-center gap-2 text-stone-500 dark:text-stone-400 font-semibold text-sm">
                  <Server className="w-4 h-4" />
                  <span className="font-sans tracking-wide uppercase text-xs font-bold">Hardware Health</span>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-stone-400">GPU Acceleration:</span>
                    {metrics.system_health.gpu_acceleration ? (
                      <span className="px-2 py-0.5 rounded-lg bg-green-500/10 text-green-500 font-bold text-[10px]">
                        ACTIVE
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-lg bg-yellow-500/10 text-yellow-500 font-bold text-[10px]">
                        DISABLED
                      </span>
                    )}
                  </div>
                  {metrics.system_health.gpu_acceleration && (
                    <div className="text-xs">
                      <span className="text-stone-400 block">Device Name:</span>
                      <span className="font-bold text-stone-700 dark:text-stone-300 text-[10px] truncate block max-w-full">
                        {metrics.system_health.gpu_device_name}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-stone-400">PyTorch Version:</span>
                    <span className="font-bold text-stone-600 dark:text-stone-400 text-[10px]">
                      {metrics.system_health.pytorch_version}
                    </span>
                  </div>
                </div>
              </div>

            </div>

            {/* Middle Grid: API Keys Configurations */}
            <div className="rounded-3xl border border-stone-200/50 dark:border-stone-800/40 bg-white dark:bg-[#18110b] p-6 space-y-4 shadow-sm">
              <div className="flex items-center gap-2 text-stone-850 dark:text-stone-200 font-semibold text-sm">
                <Key className="w-4 h-4 text-saffron-500" />
                <span className="font-sans tracking-wide uppercase text-xs font-bold">API Integration Status</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(metrics.keys_configured).map(([key, config]) => (
                  <div
                    key={key}
                    className="p-3.5 rounded-2xl bg-stone-50 dark:bg-stone-900/40 border border-stone-100 dark:border-stone-850/60 flex items-center justify-between"
                  >
                    <span className="text-xs font-semibold text-stone-655 dark:text-stone-400 capitalize">
                      {key.replace("_", " ")}
                    </span>
                    {config ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-yellow-500" />
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Bottom Section: Server Logs terminal */}
            <div className="rounded-3xl border border-stone-200/50 dark:border-stone-800/40 bg-white dark:bg-[#18110b] p-6 space-y-4 shadow-sm flex flex-col">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-stone-850 dark:text-stone-200 font-semibold text-sm">
                  <FileText className="w-4 h-4 text-saffron-500" />
                  <span className="font-sans tracking-wide uppercase text-xs font-bold">Recent System Logs</span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-stone-400 font-medium">Rows:</span>
                  <select
                    value={linesCount}
                    onChange={(e) => setLinesCount(parseInt(e.target.value))}
                    className="text-[10px] bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 rounded-lg px-2 py-1 focus:outline-none text-stone-750 dark:text-stone-300 font-medium"
                  >
                    <option value="50">50</option>
                    <option value="100">100</option>
                    <option value="200">200</option>
                  </select>
                </div>
              </div>

              {/* Log Window */}
              <div className="bg-stone-950 text-stone-300 font-mono text-[10px] p-5 rounded-2xl h-80 overflow-y-auto whitespace-pre leading-relaxed select-text border border-stone-900 shadow-inner">
                {logs ? logs : "No system logs recorded yet."}
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
};
export default AdminDashboard;
