import { useState, useEffect } from 'react';
import { PipelineVisualizer } from '../PipelineVisualizer';
import { RefreshCw, Play } from 'lucide-react';
import { VideoPlayer } from '../VideoPlayer';
import { TokenTracker } from '../TokenTracker';
import { AdvancedToggles } from '../AdvancedToggles';
import { LogViewer } from '../LogViewer';
import { api } from '../../api';

interface ExecutionViewProps {
  jobId: string;
}

export const ExecutionView = ({ jobId }: ExecutionViewProps) => {
  const [status, setStatus] = useState<string>('processing');
  const [progressText, setProgressText] = useState('Initializing...');
  const [agentStates, setAgentStates] = useState<Record<string, any>>({});
  const [jsonPath, setJsonPath] = useState<string | null>(null);

  useEffect(() => {
    // Reset state on new jobId
    setStatus('processing');
    setProgressText('Connecting to engine...');
    setAgentStates({});
    setJsonPath(null);

    const pollInterval = setInterval(async () => {
      try {
        const data = await api.getJobStatus(jobId);
        
        if (data.agent_states) {
          setAgentStates(data.agent_states);
        }
        
        if (data.status === 'completed') {
          clearInterval(pollInterval);
          setStatus('completed');
          setJsonPath(data.json_path);
          setProgressText('Generation Complete');
        } else if (data.status && data.status.includes('failed')) {
          clearInterval(pollInterval);
          setStatus('failed');
          setProgressText('Pipeline Execution Failed');
        } else {
          setStatus('processing');
          setProgressText(data.progress || 'Processing...');
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
    
    try {
      const data = await api.redriveJob(jobId);
      if (data.status === 'processing') {
        window.location.reload();
      }
    } catch (err) {
      console.error("Redrive error:", err);
    }
  };

  const handleCancel = async () => {
    try {
      await api.cancelJob(jobId);
      setStatus('failed');
      setProgressText('Pipeline Execution Cancelled');
    } catch (err) {
      console.error("Cancel error:", err);
    }
  };

  return (
    <div className="w-full flex flex-col gap-6 h-[calc(100vh-8rem)]">
      <header className="flex-none flex justify-between items-center bg-black/40 backdrop-blur-xl border border-white/10 p-6 rounded-2xl">
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

          {status === 'processing' && (
            <button 
              onClick={handleCancel}
              className="flex items-center gap-2 px-6 py-2 rounded-xl bg-orange-500/20 border border-orange-500/50 text-orange-400 font-bold hover:bg-orange-500/30 transition-all"
            >
              Cancel Job
            </button>
          )}
          
          {status === 'completed' && jsonPath && (
            <button className="flex items-center gap-2 px-6 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 font-bold hover:bg-emerald-500/30 transition-all">
              <Play className="w-4 h-4" /> Play Short
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
        
        {/* Left Side: Main Graph + Logs */}
        <div className="flex-1 flex flex-col gap-6 min-w-0">
          {/* Main Graph Area */}
          <div className="glass-card rounded-2xl p-4 overflow-hidden relative flex-none w-full">
            <PipelineVisualizer stages={agentStates} />
          </div>

          {/* Bottom Log Viewer */}
          <div className="flex-1 min-h-0 flex flex-col w-full">
            <LogViewer jobId={jobId} />
          </div>
        </div>

        {/* Right Sidebar Tools */}
        <div className="w-full lg:w-80 xl:w-96 flex flex-col gap-6 flex-none overflow-y-auto custom-scrollbar pr-2 pb-4">
          <VideoPlayer />
          <TokenTracker metrics={{ prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }} />
          <AdvancedToggles />
        </div>
      </div>
    </div>
  );
};
