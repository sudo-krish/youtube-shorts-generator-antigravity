import React, { useState } from 'react';
import { useWorkbenchStore } from '../../store/useWorkbenchStore';
import { fetchClient } from '../../api/client';
import { Scissors, Trash2, Cpu, Loader2 } from 'lucide-react';

export const ClipLibrary: React.FC = () => {
  const { clips, removeClip, videoFile } = useWorkbenchStore();
  const [isProcessing, setIsProcessing] = useState(false);

  const formatTime = (timeInSeconds: number) => {
    const d = new Date(timeInSeconds * 1000);
    return d.toISOString().substr(11, 8);
  };

  const handleBatchProcess = async () => {
    if (!videoFile) return;
    setIsProcessing(true);
    try {
      const res = await fetchClient('/video/batch-crop', {
        method: 'POST',
        body: JSON.stringify({
          payload: {
            video_filename: videoFile.name,
            clips: clips
          }
        })
      }) as { output: { message: string } };
      
      alert(`Success: ${res.output.message}`);
    } catch (err: unknown) {
      const error = err as Error;
      alert(`Failed: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex flex-col h-1/2 bg-[#09090b] p-6 overflow-y-auto border-t border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Scissors className="w-5 h-5 text-emerald-400" />
          <h2 className="text-lg font-bold text-slate-100">Clip Library</h2>
        </div>
        <span className="bg-emerald-500/10 text-emerald-400 text-xs px-2 py-1 rounded-full border border-emerald-500/20">
          {clips.length} Clips
        </span>
      </div>

      {clips.length === 0 ? (
        <div className="flex-grow flex flex-col items-center justify-center text-slate-500 border-2 border-dashed border-white/5 rounded-xl bg-white/5 p-4 text-center">
          <p className="text-sm">No clips saved yet.</p>
          <p className="text-xs opacity-60 mt-1">Use 'I' and 'O' in the player to set crop points, then Save Clip.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3 mb-6">
          {clips.map(clip => (
            <div key={clip.id} className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center justify-between group hover:bg-white/10 transition-colors">
              <div className="flex flex-col">
                <span className="text-sm font-medium text-slate-200">{clip.name}</span>
                <span className="text-xs font-mono text-slate-500 mt-0.5">
                  {formatTime(clip.startTime)} - {formatTime(clip.endTime)}
                </span>
              </div>
              <button 
                onClick={() => removeClip(clip.id)}
                className="text-slate-600 hover:text-red-400 p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                title="Delete Clip"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {clips.length > 0 && (
        <button 
          onClick={handleBatchProcess}
          disabled={isProcessing}
          className="w-full mt-auto py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(79,70,229,0.3)] transition-all disabled:opacity-50"
        >
          {isProcessing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Cpu className="w-5 h-5" />}
          {isProcessing ? 'Processing...' : 'Batch Process Clips'}
        </button>
      )}
    </div>
  );
};
