import { useState, useEffect } from 'react';
import { Play, Database, Activity, LayoutGrid, X, Download } from 'lucide-react';
import { api, API_BASE_URL } from '../../api';

export const TransformerTesting = () => {
  const [videos, setVideos] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<string>('');
  const [chunkIndex, setChunkIndex] = useState<number>(0);
  const [chunkDuration, setChunkDuration] = useState<number>(15.0);
  const [stepInterval, setStepInterval] = useState<number>(1);
  const [selectedTransformer, setSelectedTransformer] = useState<string>('yolo');
  const [isRunning, setIsRunning] = useState(false);
  
  const [viewModalData, setViewModalData] = useState<any | null>(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => {
      fetchHistory();
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const vids = await api.getVideos();
      setVideos(vids.videos || []);
      if (vids.videos && vids.videos.length > 0) {
        setSelectedVideo(vids.videos[0].video_id);
      }
      await fetchHistory();
    } catch (e) {
      console.error(e);
    }
  };

  const fetchHistory = async () => {
    try {
      const hist = await api.getTestHistory();
      setHistory(hist);
    } catch (e) {
      console.error(e);
    }
  };

  const handleRun = async () => {
    if (!selectedVideo) return;
    setIsRunning(true);
    try {
      await api.runTransformerTest(selectedVideo, chunkIndex, selectedTransformer, chunkDuration, 'valorant', stepInterval);
      await fetchHistory();
    } catch (e) {
      console.error(e);
      alert('Failed to start test');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto flex flex-col gap-8">
      <div>
        <h2 className="text-3xl font-black mb-2 flex items-center gap-3">
          <Activity className="w-8 h-8 text-aurora-cyan" />
          Transformer Testing
        </h2>
        <p className="text-white/60">Isolate and test individual ML Transformers on raw video chunks.</p>
      </div>

      {/* Control Panel */}
      <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-xl">
        <div className="grid grid-cols-6 gap-6">
          <div className="flex flex-col gap-2">
            <label className="text-xs uppercase tracking-wider text-white/50 font-bold">Select Video</label>
            <select 
              value={selectedVideo}
              onChange={(e) => setSelectedVideo(e.target.value)}
              className="bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-aurora-cyan transition-colors"
            >
              {videos.map(v => (
                <option key={v.video_id} value={v.video_id}>{v.video_name}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-xs uppercase tracking-wider text-white/50 font-bold">Chunk Index</label>
            <input 
              type="number" 
              min={0}
              value={chunkIndex}
              onChange={(e) => setChunkIndex(parseInt(e.target.value))}
              className="bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-aurora-cyan transition-colors"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-xs uppercase tracking-wider text-white/50 font-bold">Duration (s)</label>
            <input 
              type="number" 
              min={1}
              step={0.5}
              value={chunkDuration}
              onChange={(e) => setChunkDuration(parseFloat(e.target.value))}
              className="bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-aurora-cyan transition-colors"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-xs uppercase tracking-wider text-white/50 font-bold">Step (s)</label>
            <input 
              type="number" 
              min={1}
              step={1}
              value={stepInterval}
              onChange={(e) => setStepInterval(parseInt(e.target.value))}
              className="bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-aurora-cyan transition-colors"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-xs uppercase tracking-wider text-white/50 font-bold">Transformer</label>
            <select 
              value={selectedTransformer}
              onChange={(e) => setSelectedTransformer(e.target.value)}
              className="bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-aurora-cyan transition-colors"
            >
              <option value="yolo">YOLO Player Tracker</option>
              <option value="vision">LLaVA Vision Transformer</option>
              <option value="audio">Voxtral-Mini-3B Audio LLM</option>
              <option value="spatial">Optical Flow Spatial</option>
            </select>
          </div>

          <div className="flex flex-col justify-end">
            <button 
              onClick={handleRun}
              disabled={isRunning || !selectedVideo}
              className="bg-aurora-cyan text-black font-black uppercase tracking-widest text-sm py-3 px-6 rounded-xl hover:bg-aurora-cyan/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4" /> {isRunning ? 'Running...' : 'Run Test'}
            </button>
          </div>
        </div>
      </div>

      {/* History Table */}
      <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden backdrop-blur-xl">
        <table className="w-full text-left">
          <thead className="bg-white/5 border-b border-white/10 text-xs uppercase tracking-widest text-white/40">
            <tr>
              <th className="px-6 py-4 font-bold">Transformer</th>
              <th className="px-6 py-4 font-bold">Chunk</th>
              <th className="px-6 py-4 font-bold">Status</th>
              <th className="px-6 py-4 font-bold">Duration</th>
              <th className="px-6 py-4 font-bold">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {history.map(row => (
              <tr key={row.test_id} className="hover:bg-white/5 transition-colors group">
                <td className="px-6 py-4">
                  <div className="font-bold flex items-center gap-2">
                    <Database className="w-4 h-4 text-aurora-magenta" />
                    {row.transformer_name}
                  </div>
                </td>
                <td className="px-6 py-4 text-white/70">Idx: {row.chunk_index}</td>
                <td className="px-6 py-4">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase ${row.status === 'success' ? 'bg-green-500/20 text-green-400' : row.status === 'running' ? 'bg-yellow-500/20 text-yellow-400 animate-pulse' : 'bg-red-500/20 text-red-400'}`}>
                    {row.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-white/50 text-sm">
                  {row.end_time ? `${(row.end_time - row.start_time).toFixed(1)}s` : '...'}
                </td>
                <td className="px-6 py-4">
                  {row.status !== 'running' && (
                    <div className="flex items-center gap-4">
                      <button 
                        onClick={() => setViewModalData(row)}
                        className="text-aurora-cyan hover:text-white font-semibold text-sm transition-colors"
                      >
                        View Results
                      </button>
                      <a 
                        href={`${API_BASE_URL}/api/test/transformers/download/${row.test_id}`}
                        download
                        className="text-aurora-magenta hover:text-white font-semibold text-sm transition-colors flex items-center gap-1"
                      >
                        <Download className="w-4 h-4" /> Video
                      </a>
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {history.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-white/30">No test history found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* View Modal */}
      {viewModalData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-8 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#111] border border-white/10 rounded-2xl w-full max-w-6xl max-h-full flex flex-col overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-white/5">
              <h3 className="font-bold tracking-widest uppercase text-white/70 flex items-center gap-2">
                <LayoutGrid className="w-4 h-4 text-aurora-cyan" /> 
                {viewModalData.transformer_name} Results
              </h3>
              <button onClick={() => setViewModalData(null)} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                <X className="w-5 h-5 text-white/50 hover:text-white" />
              </button>
            </div>
            
            <div className="flex-1 flex overflow-hidden">
              {/* Raw JSON */}
              <div className="w-1/2 border-r border-white/5 p-4 overflow-y-auto custom-scrollbar bg-black/50">
                <pre className="text-[10px] text-green-400 font-mono whitespace-pre-wrap">
                  {viewModalData.output_data ? JSON.stringify(JSON.parse(viewModalData.output_data), null, 2) : 'No data'}
                </pre>
              </div>
              
              {/* Visualizer Video / Audio */}
              <div className="w-1/2 p-4 flex items-center justify-center bg-black/80 relative">
                {viewModalData.visual_output_path ? (
                  viewModalData.visual_output_path.endsWith('.wav') ? (
                    <audio 
                      src={`${API_BASE_URL}/assets/${viewModalData.visual_output_path.split('/assets/')[1]}`}
                      controls
                      className="w-full"
                    />
                  ) : (
                    <video 
                      src={`${API_BASE_URL}/assets/${viewModalData.visual_output_path.split('/assets/')[1]}`}
                      controls
                      className="max-w-full max-h-full rounded-xl shadow-[0_0_30px_rgba(0,0,0,0.8)]"
                    />
                  )
                ) : (
                  <div className="text-white/30 text-sm flex flex-col items-center gap-4">
                    <LayoutGrid className="w-12 h-12 text-white/10" />
                    No visual overlay available for this transformer.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
