import React, { useState, useEffect } from 'react';
import { PipelineVisualizer } from '../PipelineVisualizer';
import { RefreshCw, Play, FileJson } from 'lucide-react';
import { VideoPlayer } from '../VideoPlayer';
import { TokenTracker } from '../TokenTracker';
import { AdvancedToggles } from '../AdvancedToggles';

interface ExecutionViewProps {
  jobId: string;
}

export const ExecutionView = ({ jobId }: ExecutionViewProps) => {
  const [status, setStatus] = useState<string>('processing');
  const [progressText, setProgressText] = useState('Initializing...');
  const [agentStates, setAgentStates] = useState<Record<string, any>>({});
  const [globalFailureLogs, setGlobalFailureLogs] = useState<string | null>(null);
  const [jsonPath, setJsonPath] = useState<string | null>(null);

  useEffect(() => {
    // Reset state on new jobId
    setStatus('processing');
    setProgressText('Connecting to engine...');
    setAgentStates({});
    setGlobalFailureLogs(null);
    setJsonPath(null);

    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/jobs/${jobId}/status`);
        const statusData = await res.json();
        
        if (statusData.agent_states) {
          setAgentStates(statusData.agent_states);
        }
        
        if (statusData.status === 'completed') {
          clearInterval(pollInterval);
          setStatus('completed');
          setJsonPath(statusData.json_path);
          setProgressText('Generation Complete');
        } else if (statusData.status && statusData.status.includes('failed')) {
          clearInterval(pollInterval);
          setStatus('failed');
          setProgressText('Pipeline Execution Failed');
          fetch(`http://localhost:8000/api/jobs/${jobId}/logs`)
            .then(res => res.json())
            .then(logData => {
              if (logData.status === 'success') {
                setGlobalFailureLogs(logData.logs);
              }
            });
        } else {
          setStatus('processing');
          setProgressText(statusData.progress || 'Processing...');
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 3000);

    return () => clearInterval(pollInterval);
  }, [jobId]);

  const handleRedrive = async () => {
    setStatus('processing');
    setProgressText('Redriving from failed state...');
    setGlobalFailureLogs(null);
    
    try {
      await fetch(`http://localhost:8000/api/redrive/${jobId}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
      });
      // Polling will naturally pick up the new state changes since the interval is recreated by useEffect (wait, we need to trigger re-poll if it failed)
      // Actually, since jobId didn't change, the useEffect won't re-run. We need to trigger a re-mount or restart polling.
      // Easiest is to force a re-fetch.
      window.location.reload(); // Simple but effective for now, or just restart interval logic here
    } catch (err) {
      console.error("Redrive error:", err);
    }
  };

  return (
    <div className="w-full flex flex-col gap-8 h-full">
      <header className="flex justify-between items-center bg-black/40 backdrop-blur-xl border border-white/10 p-6 rounded-2xl">
        <div>
          <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${status === 'completed' ? 'bg-emerald-500 shadow-[0_0_10px_#10b981]' : status === 'failed' ? 'bg-rose-500 shadow-[0_0_10px_#f43f5e]' : 'bg-aurora-cyan animate-pulse shadow-[0_0_10px_#00ffff]'}`}></div>
            Pipeline Execution
          </h2>
          <p className="text-sm text-white/50 mt-1 font-mono tracking-widest uppercase">Job: {jobId.substring(0, 12)}</p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white font-medium">
            {progressText}
          </div>
          
          {status === 'failed' && (
            <button 
              onClick={handleRedrive}
              className="flex items-center gap-2 px-6 py-2 rounded-xl bg-rose-500/20 border border-rose-500/50 text-rose-400 font-bold hover:bg-rose-500/30 transition-all"
            >
              <RefreshCw className="w-4 h-4" /> Redrive
            </button>
          )}
          
          {status === 'completed' && jsonPath && (
            <button className="flex items-center gap-2 px-6 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 font-bold hover:bg-emerald-500/30 transition-all">
              <Play className="w-4 h-4" /> Play Short
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[600px]">
        {/* Main Graph Area */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <div className="flex-1 glass-card rounded-2xl p-6 overflow-hidden relative">
            <PipelineVisualizer stages={agentStates} />
          </div>
          
          {globalFailureLogs && (
            <div className="h-64 glass-card rounded-2xl p-0 overflow-hidden flex flex-col border-rose-500/30">
              <div className="bg-rose-500/10 p-3 border-b border-rose-500/20 flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-widest text-rose-400 flex items-center gap-2">
                  <FileJson className="w-4 h-4" /> Exception Logs
                </span>
              </div>
              <div className="flex-1 overflow-y-auto p-4 bg-black/60 font-mono text-[11px] text-rose-300/80 whitespace-pre-wrap leading-relaxed">
                {globalFailureLogs}
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar Tools */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <VideoPlayer />
          <TokenTracker metrics={{ prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }} />
          <AdvancedToggles />
        </div>
      </div>
    </div>
  );
};
