import React, { useEffect, useState } from 'react';

interface FactoryCounts {
  propositions: number;
  struggles: number;
  results: number;
}

export const FactoryDashboard: React.FC = () => {
  const [counts, setCounts] = useState<FactoryCounts>({ propositions: 0, struggles: 0, results: 0 });
  const [isForging, setIsForging] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [videos, setVideos] = useState<any[]>([]);

  // Poll factory status every 2 seconds
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/factory-status');
        const data = await res.json();
        if (data.status === 'success') {
          setCounts(data.counts);
        }
        
        const vidRes = await fetch('http://localhost:8000/api/videos');
        const vidData = await vidRes.json();
        if (vidData.status === 'success') {
          setVideos(vidData.videos);
        }
      } catch (e) {
        console.error(e);
      }
    };
    
    const interval = setInterval(fetchStatus, 2000);
    fetchStatus(); // initial fetch
    return () => clearInterval(interval);
  }, []);

  const handleForge = async () => {
    setIsForging(true);
    setMessage(null);
    try {
      const res = await fetch('http://localhost:8000/api/generate-short', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        setMessage(`Rendering started for unique short: ${data.video_id}`);
      } else {
        setMessage(`Error: ${data.detail || data.message}`);
      }
    } catch (e) {
      console.error(e);
      setMessage("Failed to forge short.");
    } finally {
      setIsForging(false);
    }
  };

  const totalClips = counts.propositions + counts.struggles + counts.results;
  const ready = counts.propositions > 0 && counts.struggles > 0 && counts.results > 0;

  return (
    <div className="glass-panel p-8 rounded-3xl w-full flex flex-col items-center">
      <h2 className="text-3xl font-bold text-white tracking-wide mb-2">Autonomous Factory</h2>
      <p className="text-premium-muted mb-8 font-light text-center">
        The AI is continuously slicing the video. We have extracted <span className="font-bold text-white">{totalClips}</span> atomic clips so far.
      </p>

      <div className="grid grid-cols-3 gap-6 w-full mb-10">
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 flex flex-col items-center justify-center">
          <span className="text-4xl font-black text-blue-400 mb-2">{counts.propositions}</span>
          <span className="text-sm text-white/60 uppercase tracking-widest font-semibold">Propositions</span>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 flex flex-col items-center justify-center">
          <span className="text-4xl font-black text-red-400 mb-2">{counts.struggles}</span>
          <span className="text-sm text-white/60 uppercase tracking-widest font-semibold">Struggles</span>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 flex flex-col items-center justify-center">
          <span className="text-4xl font-black text-green-400 mb-2">{counts.results}</span>
          <span className="text-sm text-white/60 uppercase tracking-widest font-semibold">Results</span>
        </div>
      </div>

      <button
        onClick={handleForge}
        disabled={isForging || !ready}
        className="w-full max-w-md py-4 rounded-full font-bold text-lg tracking-wide transition-all shadow-[0_0_30px_rgba(168,85,247,0.3)] hover:shadow-[0_0_50px_rgba(168,85,247,0.5)] disabled:opacity-50 disabled:shadow-none bg-gradient-to-r from-purple-600 to-indigo-600 text-white"
      >
        {isForging ? 'Forging in Background...' : (ready ? 'Forge Random Viral Short' : 'Waiting for Clips...')}
      </button>

      {message && (
        <div className="mt-6 px-6 py-3 bg-white/10 rounded-xl border border-white/20 text-white font-medium text-center">
          {message}
        </div>
      )}

      {videos.length > 0 && (
        <div className="mt-10 w-full">
          <h3 className="text-xl font-bold text-white mb-4 text-center">Forged Shorts</h3>
          <div className="flex flex-col gap-3">
            {videos.map((vid, i) => (
              <div key={i} className="bg-white/5 border border-white/10 p-4 rounded-xl flex items-center justify-between">
                <span className="text-white/80 font-mono text-sm">{vid.filename}</span>
                <a 
                  href={`http://localhost:8000/api/download/${vid.id}`} 
                  download 
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg font-semibold text-sm transition-colors"
                >
                  Download
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
