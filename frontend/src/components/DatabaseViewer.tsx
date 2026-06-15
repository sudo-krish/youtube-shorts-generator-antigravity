import { useState, useEffect } from 'react';
import { Database, Trash2, RefreshCw, FileCode, Clock, CheckCircle2, XCircle, PlayCircle, Loader2 } from 'lucide-react';
import { api } from '../api';

interface DatabaseViewerProps {
  onClear: () => void;
}

export const DatabaseViewer = ({ onClear }: DatabaseViewerProps) => {
  const [dbData, setDbData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchDbDump = async () => {
    setLoading(true);
    try {
      const data = await api.getDatabaseDump();
      setDbData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDbDump();
  }, []);

  const handleClear = async () => {
    if (confirm("Are you sure you want to clear the ENTIRE database and wipe all generated files? This cannot be undone.")) {
      try {
        await api.clearDatabase();
        onClear(); // Tell parent to reset state
      } catch (err) {
        alert("Failed to clear database.");
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="w-8 h-8 animate-spin text-aurora-cyan" />
      </div>
    );
  }

  const renderStatusBadge = (status: string) => {
    if (status === 'completed') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Completed
        </span>
      );
    }
    if (status === 'failed') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <XCircle className="w-3.5 h-3.5" />
          Failed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        {status}
      </span>
    );
  };

  const formatDate = (timestamp: number) => {
    if (!timestamp) return '-';
    return new Date(timestamp * 1000).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  };

  return (
    <div className="flex flex-col gap-6 h-full w-full max-w-[1600px] mx-auto pb-8">
      <header className="flex justify-between items-center bg-black/40 backdrop-blur-xl border border-white/10 p-6 rounded-2xl shadow-lg">
        <div>
          <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
            <Database className="w-6 h-6 text-aurora-violet" />
            Database Inspector
          </h2>
          <p className="text-sm text-white/50 mt-1">Structured tabular view of internal SQLite architecture.</p>
        </div>
        
        <div className="flex gap-4">
          <button onClick={fetchDbDump} className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-all font-semibold text-white hover:text-aurora-cyan">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
          <button onClick={handleClear} className="flex items-center gap-2 px-5 py-2.5 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/30 rounded-xl transition-all font-semibold text-rose-400">
            <Trash2 className="w-4 h-4" /> Reset DB
          </button>
        </div>
      </header>

      <div className="flex flex-col gap-8 flex-1 overflow-y-auto custom-scrollbar pr-2">
        
        {/* Videos Table */}
        <section className="bg-black/30 border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
          <div className="p-5 bg-white/[0.02] border-b border-white/10">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <PlayCircle className="w-5 h-5 text-aurora-cyan" /> 
              Videos ({dbData?.videos?.length || 0})
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs uppercase bg-white/5 text-white/50 border-b border-white/10">
                <tr>
                  <th className="px-6 py-4 font-semibold tracking-wider">Video ID</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Name</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">File Path</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Created At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {dbData?.videos?.length === 0 ? (
                  <tr><td colSpan={4} className="px-6 py-8 text-center text-white/30 italic">No videos recorded.</td></tr>
                ) : (
                  dbData?.videos?.map((v: any) => (
                    <tr key={v.video_id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4 font-mono text-white/70">{v.video_id.substring(0, 8)}...</td>
                      <td className="px-6 py-4 text-white font-medium">{v.video_name}</td>
                      <td className="px-6 py-4 font-mono text-white/40 truncate max-w-xs" title={v.video_path}>{v.video_path}</td>
                      <td className="px-6 py-4 text-white/50 flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5" /> {formatDate(v.created_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Jobs Table */}
        <section className="bg-black/30 border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
          <div className="p-5 bg-white/[0.02] border-b border-white/10">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <FileCode className="w-5 h-5 text-aurora-magenta" /> 
              Jobs ({dbData?.jobs?.length || 0})
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs uppercase bg-white/5 text-white/50 border-b border-white/10">
                <tr>
                  <th className="px-6 py-4 font-semibold tracking-wider">Job ID</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Video ID</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Status</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Chunks</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Created At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {dbData?.jobs?.length === 0 ? (
                  <tr><td colSpan={5} className="px-6 py-8 text-center text-white/30 italic">No jobs recorded.</td></tr>
                ) : (
                  dbData?.jobs?.map((j: any) => (
                    <tr key={j.job_id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4 font-mono text-aurora-magenta font-semibold">{j.job_id.substring(0, 8)}...</td>
                      <td className="px-6 py-4 font-mono text-white/50">{j.video_id?.substring(0, 8)}...</td>
                      <td className="px-6 py-4">{renderStatusBadge(j.status)}</td>
                      <td className="px-6 py-4 text-white/70 font-mono bg-white/5 w-16 text-center">{j.num_chunks || 0}</td>
                      <td className="px-6 py-4 text-white/50">{formatDate(j.created_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Job Stages Table */}
        <section className="bg-black/30 border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
          <div className="p-5 bg-white/[0.02] border-b border-white/10 flex justify-between items-center">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Database className="w-5 h-5 text-aurora-violet" /> 
              Job Stages ({dbData?.job_stages?.length || 0})
            </h3>
          </div>
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
            <table className="w-full text-sm text-left relative">
              <thead className="text-xs uppercase bg-[#1a1a1a] text-white/50 border-b border-white/10 sticky top-0 z-10 shadow-md">
                <tr>
                  <th className="px-6 py-4 font-semibold tracking-wider">ID</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Job ID</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Stage</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Chunk</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Status</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Duration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {dbData?.job_stages?.length === 0 ? (
                  <tr><td colSpan={6} className="px-6 py-8 text-center text-white/30 italic">No stage executions recorded.</td></tr>
                ) : (
                  dbData?.job_stages?.map((s: any) => (
                    <tr key={s.id} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="px-6 py-4 text-white/30 font-mono">#{s.id}</td>
                      <td className="px-6 py-4 font-mono text-white/50">{s.job_id?.substring(0, 8)}</td>
                      <td className="px-6 py-4 font-semibold text-aurora-violet">{s.stage_name}</td>
                      <td className="px-6 py-4">
                        {s.chunk_id !== null ? (
                          <span className="px-2 py-1 rounded bg-white/10 text-white/80 font-mono text-xs border border-white/20">
                            Batch {s.chunk_id + 1}
                          </span>
                        ) : (
                          <span className="text-white/20 text-xs italic">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4">{renderStatusBadge(s.status)}</td>
                      <td className="px-6 py-4 text-white/50 font-mono text-xs">
                        {s.end_time && s.start_time 
                          ? `${(s.end_time - s.start_time).toFixed(1)}s` 
                          : '-'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

      </div>
    </div>
  );
};
