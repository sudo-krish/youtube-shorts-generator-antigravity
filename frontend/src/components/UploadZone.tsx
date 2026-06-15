import { useState, useCallback, useRef, useEffect } from 'react';
import { UploadCloud, CheckCircle, FileJson, Scissors } from 'lucide-react';
import * as animeLib from 'animejs';

const anime = (animeLib as any).default || animeLib;

type FlowState = 'UPLOAD' | 'READY' | 'PROCESSING' | 'DONE';

import { PipelineVisualizer } from './PipelineVisualizer';

export const UploadZone = ({ onUploadSuccess, selectedJobId }: { onUploadSuccess?: (data: any) => void, selectedJobId?: string | null }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [flowState, setFlowState] = useState<FlowState>('UPLOAD');
  
  const [videoPath, setVideoPath] = useState<string | null>(null);
  const [videoName, setVideoName] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [agentStates, setAgentStates] = useState<any>({});
  
  const [jsonPath, setJsonPath] = useState<string | null>(null);
  const [progressText, setProgressText] = useState<string>('');
  const [globalFailureLogs, setGlobalFailureLogs] = useState<string | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const iconRef = useRef<SVGSVGElement>(null);

  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [agentModels, setAgentModels] = useState<Record<string, string>>({});

  useEffect(() => {
    if (flowState === 'UPLOAD' && cardRef.current) {
        anime({
        targets: cardRef.current,
        translateY: [-3, 3],
        direction: 'alternate',
        loop: true,
        easing: 'easeInOutSine',
        duration: 4000
        });
    }

    // Fetch available models
    fetch('http://localhost:8000/api/models')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
            setAvailableModels(data.models);
        }
      })
      .catch(console.error);

    // Fetch config
    fetch('http://localhost:8000/api/config')
      .then(res => res.json())
      .then(data => {
        if (data.models) {
            setAgentModels(data.models);
        }
      })
      .catch(console.error);
  }, [flowState]);

  useEffect(() => {
    if (selectedJobId) {
        setJobId(selectedJobId);
        setFlowState('PROCESSING');
        
        // Fetch specific job
        fetch(`http://localhost:8000/api/status/${selectedJobId}`)
          .then(res => res.json())
          .then(data => {
             setAgentStates(data.agent_states || {});
             if (data.status === 'completed' || data.status === 'failed') {
                 setFlowState('DONE');
                 if (data.status === 'failed') {
                     fetch(`http://localhost:8000/api/jobs/${selectedJobId}/logs`)
                         .then(res => res.json())
                         .then(logData => {
                             if (logData.status === 'success') {
                                 setGlobalFailureLogs(logData.logs);
                             }
                         });
                 }
             }
          });
          
        startPolling(selectedJobId);
    } else {
        setFlowState('UPLOAD');
        setJobId(null);
        setAgentStates({});
    }
  }, [selectedJobId]);

  const handleModelChange = async (agent: string, model: string) => {
    const newModels = { ...agentModels, [agent]: model };
    setAgentModels(newModels);
    try {
        await fetch('http://localhost:8000/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ models: newModels })
        });
    } catch (e) {
        console.error('Failed to save config', e);
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!isDragging && flowState === 'UPLOAD') {
      setIsDragging(true);
      anime({
        targets: cardRef.current,
        scale: 1.02,
        boxShadow: '0 0 40px rgba(255, 255, 255, 0.08)',
        borderColor: 'rgba(255,255,255,0.3)',
        duration: 400,
        easing: 'easeOutQuint'
      });
      anime({
        targets: iconRef.current,
        translateY: -5,
        color: '#FFFFFF',
        duration: 400,
        easing: 'easeOutQuint'
      });
    }
  }, [isDragging, flowState]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (flowState === 'UPLOAD') {
        setIsDragging(false);
        anime({
        targets: cardRef.current,
        scale: 1,
        boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
        borderColor: 'rgba(255,255,255,0.08)',
        duration: 400,
        easing: 'easeOutQuint'
        });
        anime({
        targets: iconRef.current,
        translateY: 0,
        color: 'rgba(255,255,255,0.3)',
        duration: 400,
        easing: 'easeOutQuint'
        });
    }
  }, [flowState]);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    handleDragLeave(e);
    
    if (flowState !== 'UPLOAD') return;

    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.mp4')) {
      setIsUploading(true);
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const response = await fetch('http://localhost:8000/api/upload', {
          method: 'POST',
          body: formData
        });
        const result = await response.json();
        if (result.status === 'success') {
            setVideoPath(result.video_id);
            setVideoName(file.name);
            setFlowState('READY');
        } else {
            setFlowState('READY');
        }
      } catch (err) {
        console.error('Upload failed:', err);
        alert('Upload failed.');
      } finally {
        setIsUploading(false);
      }
    } else {
      alert('Please drop an .mp4 file.');
    }
  }, [handleDragLeave, flowState]);

  const startPolling = (currentJobId: string) => {
    const pollInterval = setInterval(async () => {
        try {
            const statusRes = await fetch(`http://localhost:8000/api/status/${currentJobId}`);
            const statusData = await statusRes.json();
            
            if (statusData.agent_states) {
                setAgentStates(statusData.agent_states);
            }
            
            if (statusData.status === 'completed') {
                clearInterval(pollInterval);
                setJsonPath(statusData.json_path);
                setProgressText('');
                if (onUploadSuccess) onUploadSuccess({ data: statusData.result, json_path: statusData.json_path });
                setFlowState('DONE');
            } else if (statusData.status && statusData.status.includes('failed')) {
                clearInterval(pollInterval);
                setProgressText('Failed. You can Redrive to resume from the exact point of failure.');
                setFlowState('DONE');
                fetch(`http://localhost:8000/api/jobs/${currentJobId}/logs`)
                    .then(res => res.json())
                    .then(logData => {
                        if (logData.status === 'success') {
                            setGlobalFailureLogs(logData.logs);
                        }
                    });
            } else {
                setProgressText(statusData.progress || 'Processing...');
            }
        } catch (err) {
            console.error("Polling error:", err);
        }
    }, 3000);
  };

  const handleAnalyze = async () => {
    setFlowState('PROCESSING');
    setProgressText('Initializing job...');
    setAgentStates({});
    try {
        const response = await fetch('http://localhost:8000/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                video_id: videoPath,
                metadata: {}
            })
        });
        const data = await response.json();
        
        if (data.status === 'processing' && data.job_id) {
            setJobId(data.job_id);
            startPolling(data.job_id);
        } else if (data.status === 'success') {
            setJsonPath(data.json_path);
            setProgressText('');
            if (onUploadSuccess) onUploadSuccess(data);
            setFlowState('DONE');
        } else {
            alert('Analysis failed.');
            setFlowState('READY');
        }
    } catch(e) {
        alert('Failed to start AI analysis.');
        setFlowState('READY');
    }
  }

  const handleRedrive = async () => {
    if (!jobId) return;
    setFlowState('PROCESSING');
    setProgressText('Redriving from failure...');
    try {
        await fetch(`http://localhost:8000/api/redrive/${jobId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ video_path: videoPath, metadata: {} })
        });
        startPolling(jobId);
    } catch (e) {
        alert('Failed to redrive.');
        setFlowState('READY');
    }
  }

  const handleSplice = async () => {
    setFlowState('PROCESSING');
    try {
        await fetch('http://localhost:8000/api/splice', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ video_path: videoPath, json_path: jsonPath })
        });
        setFlowState('DONE');
        alert('Splicing triggered successfully! Check the dashboard.');
    } catch(e) {
        alert('Failed to trigger splicer.');
        setFlowState('DONE');
    }
  }

  return (
    <div className="w-full flex flex-col gap-6">
        {/* Upload Box or Status Box */}
        {flowState === 'UPLOAD' && (
            <div
            ref={cardRef}
            className="glass-panel relative flex flex-col items-center justify-center w-full h-72 rounded-3xl cursor-pointer overflow-hidden group transition-colors duration-500 border border-white/5 hover:border-white/10"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            >
            {isDragging && (
                <div className="absolute inset-0 bg-white/[0.02] backdrop-blur-3xl transition-opacity duration-300"></div>
            )}

            {isUploading ? (
                <div className="flex flex-col items-center z-10">
                <div className="w-12 h-12 border-4 border-white/20 border-t-white rounded-full animate-spin mb-4"></div>
                <h3 className="text-xl font-semibold mb-2 text-white tracking-wide">Securely Uploading...</h3>
                <p className="text-sm text-premium-muted font-light">Saving video to local disk</p>
                </div>
            ) : (
                <>
                <UploadCloud ref={iconRef} className="w-12 h-12 mb-6 text-white/30 z-10 transition-colors duration-500" />
                <h3 className="text-xl font-semibold mb-2 text-white z-10 tracking-wide">Upload Media</h3>
                <p className="text-sm text-premium-muted z-10 font-light">Drag and drop raw .mp4 stream</p>
                </>
            )}
            </div>
        )}

        {/* Agent Model Configuration UI */}
        {flowState === 'UPLOAD' && Object.keys(agentModels).length > 0 && (
            <div className="glass-panel p-6 rounded-3xl border border-white/10 w-full mb-6 shadow-xl">
                <h3 className="text-xl font-bold text-white mb-4">Agent Brain Configuration</h3>
                <p className="text-sm text-premium-muted mb-6 font-light">Assign specialized generative models to specific roles dynamically.</p>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Object.entries(agentModels).map(([agent, currentModel]) => (
                        <div key={agent} className="flex flex-col gap-2 bg-black/40 p-4 rounded-xl border border-white/5 shadow-inner">
                            <span className="text-indigo-400 font-bold text-sm capitalize">{agent} Agent</span>
                            <select 
                                value={currentModel}
                                onChange={(e) => handleModelChange(agent, e.target.value)}
                                className="bg-white/5 text-white text-sm border border-white/10 rounded-lg px-3 py-2 outline-none hover:border-indigo-500/50 transition-colors cursor-pointer"
                            >
                                {availableModels.map(m => <option className="bg-gray-900" key={m} value={m}>{m}</option>)}
                            </select>
                        </div>
                    ))}
                </div>
            </div>
        )}

        {(flowState === 'READY' || flowState === 'PROCESSING' || flowState === 'DONE') && (
            <div className="glass-panel p-8 rounded-3xl border border-white/10 flex flex-col">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h3 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                            <CheckCircle className="w-6 h-6 text-green-400" /> Workspace Ready
                        </h3>
                        <p className="text-premium-muted">File: {videoName}</p>
                    </div>
                </div>

                <div className="flex flex-col gap-4 w-full">
                    {progressText.includes('Failed.') && jobId && (
                        <button 
                            onClick={handleRedrive}
                            className="w-full py-4 rounded-xl font-bold transition-all bg-red-500/20 border border-red-500/50 hover:bg-red-500/30 text-red-200 flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(239,68,68,0.3)]"
                        >
                            Redrive from Failure
                        </button>
                    )}

                    <button 
                        onClick={handleAnalyze}
                        disabled={flowState === 'PROCESSING' || !videoPath}
                        className="w-full py-4 rounded-xl font-bold transition-all bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 text-white flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                        <FileJson className="w-5 h-5" /> 
                        {flowState === 'PROCESSING' ? (progressText || 'Running AI...') : '1. Run AI Analysis (Consumes Tokens)'}
                    </button>

                    <button 
                        onClick={handleSplice}
                        disabled={flowState === 'PROCESSING' || !jsonPath}
                        className="w-full py-4 rounded-xl font-bold transition-all bg-indigo-500/20 border border-indigo-500/50 hover:bg-indigo-500/30 text-indigo-200 flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                        <Scissors className="w-5 h-5" /> 
                        {flowState === 'PROCESSING' ? 'Processing...' : '2. Slice Video into Buckets (Free)'}
                    </button>
                </div>
                
                {Object.keys(agentStates).length > 0 && (
                    <div className="mt-8">
                        <PipelineVisualizer stages={agentStates} />
                    </div>
                )}

                {globalFailureLogs && (
                    <div className="mt-8 bg-black/60 border border-rose-500/30 rounded-2xl p-6">
                        <h4 className="text-lg font-bold text-rose-400 mb-4 flex items-center gap-2">
                            Global Pipeline Execution Logs
                        </h4>
                        <pre className="text-rose-200/80 font-mono text-xs overflow-auto whitespace-pre-wrap max-h-96 p-4 bg-[#0a0a0a] rounded-xl border border-rose-500/10">
                            {globalFailureLogs}
                        </pre>
                    </div>
                )}
            </div>
        )}


    </div>
  );
};
