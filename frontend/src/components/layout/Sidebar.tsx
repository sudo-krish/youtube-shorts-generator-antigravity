import { useState, useEffect } from 'react';
import type { FC } from 'react';
import { Play, History, Sparkles, Database, Activity } from 'lucide-react';
import { api } from '../../api';

interface SidebarProps {
  selectedJobId: string | null;
  onSelectJob: (jobId: string | null) => void;
  onOpenDbViewer: () => void;
  onOpenDashboard: () => void;
  onOpenGameManager: () => void;
}

export const Sidebar: FC<SidebarProps> = ({ 
  selectedJobId, 
  onSelectJob, 
  onOpenDbViewer,
  onOpenDashboard,
  onOpenGameManager
}) => {
  const [jobs, setJobs] = useState<any[]>([]);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchJobs = async () => {
    try {
      const data = await api.getJobs();
      if (data.status === 'success') {
        setJobs(data.jobs);
      }
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <aside className="w-80 border-r border-white/5 bg-black/60 backdrop-blur-2xl flex flex-col relative z-50 shadow-[4px_0_24px_rgba(0,0,0,0.5)] h-screen overflow-hidden shrink-0">
      <div className="p-8 border-b border-white/5 relative overflow-hidden group cursor-pointer" onClick={() => onSelectJob(null)}>
        {/* Subtle Aurora inside header */}
        <div className="absolute -top-10 -right-10 w-32 h-32 bg-aurora-violet/20 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-1000"></div>
        <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-3 relative z-10">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-aurora-cyan to-aurora-violet flex items-center justify-center shadow-[0_0_15px_rgba(138,43,226,0.5)]">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          Antigravity
        </h1>
        <p className="text-[10px] text-white/40 mt-2 tracking-[0.2em] uppercase font-semibold relative z-10">Editor Pro Max</p>
      </div>

      <div className="p-4 flex-grow overflow-y-auto flex flex-col gap-2 custom-scrollbar">
        <h3 className="text-[10px] uppercase tracking-widest text-white/30 font-bold mb-3 mt-2 px-2 flex items-center gap-2">
          <History className="w-3.5 h-3.5" /> Recent Sessions
        </h3>
        
        <button 
          onClick={() => onSelectJob(null)}
          className={`w-full text-left p-4 rounded-2xl transition-all duration-300 border relative overflow-hidden ${!selectedJobId ? 'bg-white/10 border-white/20 shadow-[0_0_20px_rgba(0,255,255,0.1)]' : 'bg-transparent border-transparent hover:bg-white/5'}`}
        >
          {!selectedJobId && <div className="absolute inset-0 bg-gradient-to-r from-aurora-cyan/10 to-transparent"></div>}
          <div className="flex items-center gap-4 relative z-10">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${!selectedJobId ? 'bg-aurora-cyan/20' : 'bg-white/5'}`}>
              <Play className={`w-4 h-4 ml-0.5 ${!selectedJobId ? 'text-aurora-cyan drop-shadow-[0_0_8px_rgba(0,255,255,0.8)]' : 'text-white/40'}`} />
            </div>
            <div>
              <p className={`text-sm font-bold ${!selectedJobId ? 'text-white' : 'text-white/60'}`}>New Project</p>
              <p className="text-xs text-white/40 mt-0.5">Start fresh</p>
            </div>
          </div>
        </button>

        <button 
          onClick={onOpenDashboard}
          className="w-full flex items-center justify-between p-3 rounded-xl border border-aurora-cyan/30 hover:border-aurora-cyan/60 bg-aurora-cyan/10 hover:bg-aurora-cyan/20 transition-all group"
        >
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-aurora-cyan group-hover:animate-pulse" />
            <span className="font-bold text-white/90 group-hover:text-white">Metrics Dashboard</span>
          </div>
        </button>

        <button 
          onClick={onOpenGameManager}
          className="w-full flex items-center justify-between p-3 rounded-xl border border-aurora-magenta/30 hover:border-aurora-magenta/60 bg-aurora-magenta/10 hover:bg-aurora-magenta/20 transition-all group"
        >
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-aurora-magenta group-hover:animate-pulse" />
            <span className="font-bold text-white/90 group-hover:text-white">Game Context</span>
          </div>
        </button>

        <button 
          onClick={onOpenDbViewer}
          className="w-full flex items-center justify-between p-3 rounded-xl border border-white/10 hover:border-white/20 hover:bg-white/5 transition-colors group"
        >
          <div className="flex items-center gap-3">
            <Database className="w-5 h-5 text-white/60 group-hover:text-white" />
            <span className="font-bold text-white/60 group-hover:text-white">System Database</span>
          </div>
        </button>

        <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent my-3"></div>

        {jobs.map(job => (
          <button 
            key={job.job_id}
            onClick={() => onSelectJob(job.job_id)}
            className={`w-full text-left p-4 rounded-2xl transition-all duration-300 border relative group ${selectedJobId === job.job_id ? 'bg-white/10 border-white/20' : 'bg-transparent border-transparent hover:bg-white/5'}`}
          >
            {selectedJobId === job.job_id && <div className="absolute inset-0 bg-gradient-to-r from-aurora-violet/10 to-transparent rounded-2xl pointer-events-none"></div>}
            
            <p className="text-sm font-bold text-white truncate relative z-10 group-hover:text-aurora-cyan transition-colors">{job.video_name}</p>
            <p className="text-[10px] text-white/30 mt-1 font-mono tracking-wider relative z-10">ID: {job.job_id.substring(0, 8)}</p>
            
            <div className="flex items-center justify-between mt-3 relative z-10">
              <span className={`text-[9px] uppercase tracking-widest font-bold px-2 py-1 rounded-md ${job.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : job.status === 'processing' ? 'bg-aurora-cyan/10 text-aurora-cyan border border-aurora-cyan/20 animate-pulse' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                {job.status}
              </span>
              <span className="text-[10px] text-white/20 font-medium">{new Date(job.created_at * 1000).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
            </div>
          </button>
        ))}
      </div>
    </aside>
  );
};
