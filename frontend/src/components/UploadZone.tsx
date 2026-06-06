import { useState, useCallback, useRef, useEffect } from 'react';
import { UploadCloud, CheckCircle, Play, FileJson, Scissors } from 'lucide-react';
import * as animeLib from 'animejs';

const anime = (animeLib as any).default || animeLib;

type FlowState = 'UPLOAD' | 'READY' | 'PROCESSING' | 'DONE';

export const UploadZone = ({ onUploadSuccess, onProjectSelect }: { onUploadSuccess?: (data: any) => void, onProjectSelect?: (project: any) => void }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [flowState, setFlowState] = useState<FlowState>('UPLOAD');
  
  const [videoPath, setVideoPath] = useState<string | null>(null);
  const [videoName, setVideoName] = useState<string | null>(null);
  
  const [jsonPath, setJsonPath] = useState<string | null>(null);
  const [aiData, setAiData] = useState<any>(null);
  const [progressText, setProgressText] = useState<string>('');

  const [projects, setProjects] = useState<any[]>([]);
  const cardRef = useRef<HTMLDivElement>(null);
  const iconRef = useRef<SVGSVGElement>(null);

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

    // Fetch historical projects
    fetch('http://localhost:8000/api/projects')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
            setProjects(data.projects);
        }
      })
      .catch(console.error);
  }, [flowState]);

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
        const res = await fetch('http://localhost:8000/api/upload', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        console.log('Upload success:', data);
        setVideoPath(data.video_path);
        setVideoName(file.name);
        setFlowState('READY');
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

  const handleAnalyze = async () => {
    setFlowState('PROCESSING');
    setProgressText('Initializing job...');
    try {
        const res = await fetch('http://localhost:8000/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ video_path: videoPath })
        });
        const data = await res.json();
        
        if (data.status === 'processing' && data.job_id) {
            const pollInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch(`http://localhost:8000/api/status/${data.job_id}`);
                    const statusData = await statusRes.json();
                    
                    if (statusData.status === 'completed') {
                        clearInterval(pollInterval);
                        setAiData(statusData.result.top_fights);
                        setJsonPath(statusData.json_path);
                        setProgressText('');
                        if (onUploadSuccess) onUploadSuccess({ data: statusData.result, json_path: statusData.json_path });
                        setFlowState('DONE');
                    } else if (statusData.status === 'failed') {
                        clearInterval(pollInterval);
                        alert('Analysis failed: ' + statusData.progress);
                        setProgressText('');
                        setFlowState('READY');
                    } else {
                        setProgressText(statusData.progress || 'Processing...');
                    }
                } catch (err) {
                    console.error("Polling error:", err);
                }
            }, 3000);
        } else if (data.status === 'success') {
            setAiData(data.data);
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

  const loadProject = (project: any) => {
    setVideoPath(project.video_path);
    setVideoName(project.video_name);
    setJsonPath(project.json_path);
    setAiData(project.data);
    setFlowState('DONE');
    if (onProjectSelect) onProjectSelect(project);
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
            </div>
        )}

        {/* Existing Projects List */}
        {flowState === 'UPLOAD' && projects.length > 0 && (
            <div className="glass-panel p-6 rounded-3xl border border-white/10">
                <h3 className="text-xl font-bold text-white mb-4">Historical Projects</h3>
                <div className="flex flex-col gap-2">
                    {projects.map((p, i) => (
                        <div key={i} onClick={() => loadProject(p)} className="p-4 rounded-xl bg-white/5 hover:bg-white/10 cursor-pointer transition-colors border border-white/5 flex justify-between items-center">
                            <div>
                                <p className="text-white font-medium">{p.video_name}</p>
                                <p className="text-xs text-premium-muted">{p.clips} clips extracted</p>
                            </div>
                            <Play className="w-5 h-5 text-white/50" />
                        </div>
                    ))}
                </div>
            </div>
        )}

        {/* JSON Viewer */}
        {flowState === 'DONE' && aiData && (
            <div className="glass-panel p-6 rounded-3xl border border-white/10 flex flex-col">
                <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    <FileJson className="w-5 h-5 text-purple-400" /> AI Semantic Layout
                </h3>
                <p className="text-sm text-premium-muted mb-4 font-light">The AI successfully generated the following blueprint for the splicer.</p>
                <div className="bg-black/60 rounded-xl p-4 overflow-auto max-h-96 border border-white/5">
                    <pre className="text-xs text-purple-200/80 font-mono">
                        {JSON.stringify(aiData, null, 2)}
                    </pre>
                </div>
            </div>
        )}

        {/* History Tracker */}
        {projects.length > 0 && (
            <div className="glass-panel p-6 rounded-3xl w-full">
                <h3 className="text-xl font-bold text-white mb-4">History Tracker</h3>
                <p className="text-sm text-premium-muted mb-4 font-light">Recover a previous session to iterate locally without LLM token costs.</p>
                <div className="flex flex-col gap-2">
                    {projects.map((proj, idx) => (
                        <div 
                            key={idx}
                            className="px-4 py-3 rounded-xl bg-white/5 border border-white/5 w-full flex justify-between items-center group"
                        >
                            <span className="text-white font-medium">{proj.video_name}</span>
                            <div className="flex items-center gap-3">
                                <span className="text-xs px-2 py-1 bg-white/10 rounded-md text-white/60">
                                    {proj.clips} Clips
                                </span>
                                <button
                                    onClick={async () => {
                                        try {
                                            await fetch('http://localhost:8000/api/splice', {
                                                method: 'POST',
                                                headers: {'Content-Type': 'application/json'},
                                                body: JSON.stringify({ video_path: proj.video_path, json_path: proj.json_path })
                                            });
                                            alert('Resplicing started! View terminal logs above.');
                                        } catch (e) {
                                            alert('Failed to resplice');
                                        }
                                    }}
                                    className="text-xs px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-md transition-colors flex items-center gap-1"
                                >
                                    <Scissors className="w-3 h-3" /> Re-Splice to Factory
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )}
    </div>
  );
};
