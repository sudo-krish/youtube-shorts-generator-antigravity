import { useState, useEffect } from 'react';
import { Play, Layers, Download, CheckCircle2, CircleDashed, FastForward, Activity } from 'lucide-react';
import { api } from '../../api';
import { VideoPlayer } from '../VideoPlayer';
import { TokenTracker } from '../TokenTracker';
import { AdvancedToggles } from '../AdvancedToggles';

interface RenderViewProps {
  jobId: string;
}

export const RenderView = ({ jobId }: RenderViewProps) => {
  const [variants, setVariants] = useState<any[]>([]);
  const [status, setStatus] = useState<'idle' | 'rendering' | 'completed'>('idle');
  const [progress, setProgress] = useState('');
  // @ts-ignore
  const [activeVideoPath, setActiveVideoPath] = useState<string | null>(null);

  useEffect(() => {
    const fetchVariants = async () => {
      try {
        const jobRes = await fetch(`http://localhost:8000/api/jobs/${jobId}/status`);
        const jobData = await jobRes.json();
        
        if (jobData.json_path) {
          const blueprintRes = await fetch(`http://localhost:8000/${jobData.json_path.split('backend/')[1] || 'workspace/' + jobData.json_path.split('/').pop()}`);
          if (blueprintRes.ok) {
            const blueprint = await blueprintRes.json();
            setVariants(blueprint.shorts || []);
          }
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchVariants();
  }, [jobId]);

  const [renderStatuses, setRenderStatuses] = useState<Record<string, any>>({});

  useEffect(() => {
    let interval: any;
    if (status === 'rendering') {
      interval = setInterval(async () => {
        try {
          const res = await api.getRenderStatus(jobId);
          if (res.variants) {
            const statusMap: Record<string, any> = {};
            let allCompleted = true;
            let total = res.variants.length;
            let done = 0;
            
            for (const v of res.variants) {
              statusMap[v.variant_id] = v;
              if (v.status !== 'completed' && v.status !== 'failed') {
                allCompleted = false;
              } else {
                done++;
              }
            }
            
            setRenderStatuses(statusMap);
            setProgress(`Rendering ${done} of ${total} variants...`);
            
            if (allCompleted && total > 0) {
              setStatus('completed');
              setProgress('Batch rendering finished!');
              clearInterval(interval);
            }
          }
        } catch (err) {
          console.error(err);
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [status, jobId]);

  const handleBatchRender = async () => {
    setStatus('rendering');
    setProgress(`Queuing ${variants.length} variants...`);
    
    try {
      const vIds = variants.map((v, i) => v.variant_id || String(i));
      await api.batchRender(jobId, vIds);
    } catch (err) {
      console.error(err);
      setStatus('idle');
      setProgress('Failed to start batch.');
    }
  };

  return (
    <div className="w-full flex flex-col gap-6 h-[calc(100vh-8rem)]">
      <header className="flex-none flex justify-between items-center bg-black/40 backdrop-blur-xl border border-white/10 p-6 rounded-2xl">
        <div>
          <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
            <Layers className="w-6 h-6 text-indigo-400" />
            Batch Render Factory
          </h2>
          <p className="text-sm text-white/50 mt-1 font-mono tracking-widest uppercase">
            {variants.length} Variants Ready for Generation
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white font-medium">
            {status === 'idle' ? 'Ready to Render' : progress}
          </div>
          
          <button 
            onClick={handleBatchRender}
            disabled={status === 'rendering'}
            className={`flex items-center gap-2 px-6 py-2 rounded-xl font-bold transition-all ${
              status === 'rendering' 
                ? 'bg-blue-500/20 border border-blue-500/50 text-blue-400 opacity-50 cursor-not-allowed' 
                : 'bg-indigo-500/20 border border-indigo-500/50 text-indigo-400 hover:bg-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.2)]'
            }`}
          >
            {status === 'rendering' ? (
              <><Activity className="w-4 h-4 animate-spin" /> Rendering Batch...</>
            ) : (
              <><FastForward className="w-4 h-4" /> Start Batch Render</>
            )}
          </button>
        </div>
      </header>

      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
        
        {/* Left Side: Grid of Variants */}
        <div className="flex-1 bg-black/40 border border-white/5 rounded-2xl overflow-y-auto custom-scrollbar p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {variants.length === 0 ? (
              <div className="col-span-full h-40 flex items-center justify-center text-white/30 italic">
                Loading variants blueprint...
              </div>
            ) : (
              variants.map((v, idx) => {
                const vId = v.variant_id || String(idx);
                const vStatus = renderStatuses[vId]?.status || 'queued';
                
                return (
                  <div key={idx} className="group relative bg-white/5 border border-white/10 rounded-xl overflow-hidden aspect-[9/16] flex flex-col items-center justify-center transition-all hover:border-indigo-500/50 hover:bg-white/10">
                    <div className="absolute top-3 left-3 bg-black/60 px-2 py-1 rounded text-[10px] font-mono text-white/70">
                      Variant {vId}
                    </div>
                    
                    {vStatus === 'completed' ? (
                      <div className="flex flex-col items-center gap-3">
                        <CheckCircle2 className="w-12 h-12 text-emerald-400" />
                        <button className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg text-xs font-bold hover:bg-emerald-500/30">
                          <Play className="w-3 h-3" /> Play
                        </button>
                      </div>
                    ) : vStatus === 'rendering' ? (
                      <div className="flex flex-col items-center gap-3">
                        <CircleDashed className="w-8 h-8 text-blue-400 animate-spin" />
                        <span className="text-xs text-blue-400 font-mono">Rendering...</span>
                      </div>
                    ) : vStatus === 'failed' ? (
                      <div className="flex flex-col items-center gap-3">
                        <Activity className="w-8 h-8 text-rose-400" />
                        <span className="text-xs text-rose-400 font-mono">Failed</span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-2 opacity-30">
                        <Layers className="w-8 h-8 text-white" />
                        <span className="text-xs font-mono text-white uppercase tracking-wider text-center px-4">
                          {v.hooks?.[0] || 'Pending Render'}
                        </span>
                      </div>
                    )}
                    
                    <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white">
                        <Download className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
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
