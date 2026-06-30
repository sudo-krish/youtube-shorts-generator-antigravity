import { useState, useEffect } from 'react';
import { PipelineVisualizer } from '../PipelineVisualizer';
import { RefreshCw, Play } from 'lucide-react';
import { LogViewer } from '../LogViewer';
import { ModelSettings } from '../ModelSettings';
import { api } from '../../api';

interface ExecutionViewProps {
  jobId: string;
  onNext?: () => void;
}

export const ExecutionView = ({ jobId, onNext }: ExecutionViewProps) => {
  const [status, setStatus] = useState<string>('processing');
  const [progressText, setProgressText] = useState('Initializing...');
  const [agentStates, setAgentStates] = useState<any[]>([]);
  const [jsonPath, setJsonPath] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeOutput, setNodeOutput] = useState<any>(null);
  const [isFetchingNode, setIsFetchingNode] = useState(false);

  useEffect(() => {
    // Reset state on new jobId
    setStatus('processing');
    setProgressText('Connecting to engine...');
    setAgentStates([]);
    setJsonPath(null);

    const pollInterval = setInterval(async () => {
      try {
        const data = await api.getJobStatus(jobId);
        
        if (data.stages) {
          setAgentStates(data.stages);
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

  const handleNodeClick = async (nodeId: string) => {
    setSelectedNodeId(nodeId);
    setIsFetchingNode(true);
    setNodeOutput(null);
    try {
      const data = await api.getNodeOutput(jobId, nodeId);
      setNodeOutput(data.output);
    } catch (err) {
      console.error("Failed to fetch node output", err);
      setNodeOutput("Error fetching output.");
    } finally {
      setIsFetchingNode(false);
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
          <ModelSettings />
          
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
            <button 
              onClick={() => onNext && onNext()}
              className="flex items-center gap-2 px-6 py-2 rounded-xl bg-indigo-500/20 border border-indigo-500/50 text-indigo-400 font-bold hover:bg-indigo-500/30 transition-all"
            >
              Next: Render Phase <Play className="w-4 h-4 ml-1" />
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 flex flex-col gap-6 min-h-0">
        
        {/* Main Graph Area */}
        <div className="glass-card rounded-2xl p-4 overflow-hidden relative flex-none w-full">
          <PipelineVisualizer 
            stages={agentStates} 
            selectedNodeId={selectedNodeId}
            onNodeClick={handleNodeClick}
          />
        </div>

        {/* Bottom Split: JSON Preview + Log Viewer */}
        <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-6 w-full">
          {/* Left: JSON/Markdown Output Preview */}
          <div className="flex-1 flex flex-col bg-black/40 border border-white/5 rounded-2xl overflow-hidden min-h-[250px]">
             <div className="bg-white/5 border-b border-white/5 px-4 py-3 flex items-center justify-between">
                <span className="text-sm font-bold text-white/80">Node Inspection</span>
                {selectedNodeId && (
                  <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-1 rounded">
                    {selectedNodeId}
                  </span>
                )}
             </div>
             <div className="flex-1 overflow-y-auto custom-scrollbar p-4 text-xs font-mono text-white/70">
                {!selectedNodeId ? (
                  <div className="h-full flex items-center justify-center text-white/30 italic">
                    Click a node in the graph to preview its generated output.
                  </div>
                ) : isFetchingNode ? (
                  <div className="h-full flex items-center justify-center text-blue-400 animate-pulse">
                    Fetching node state...
                  </div>
                ) : (
                  <pre className="whitespace-pre-wrap break-words">
                    {typeof nodeOutput === 'object' ? JSON.stringify(nodeOutput, null, 2) : nodeOutput || 'No output.'}
                  </pre>
                )}
             </div>
          </div>

          {/* Right: Log Viewer */}
          <div className="flex-1 flex flex-col min-h-[250px]">
            <LogViewer jobId={jobId} />
          </div>
        </div>
      </div>
    </div>
  );
};
