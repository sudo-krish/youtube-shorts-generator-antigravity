import { useState, useEffect } from 'react';
import { Gamepad2, Globe, ArrowRight, Video, CheckCircle2, Loader2, Info } from 'lucide-react';
import { ModelSettings } from '../ModelSettings';
import { api, API_BASE_URL } from '../../api';

interface ConfigurationPanelProps {
  videoId: string;
  videoName: string;
  onAnalyzeStarted: (jobId: string) => void;
  onCancel: () => void;
}

export const ConfigurationPanel = ({ videoId, videoName, onAnalyzeStarted, onCancel }: ConfigurationPanelProps) => {
  const [selectedGameId, setSelectedGameId] = useState<string>('');
  const [games, setGames] = useState<any[]>([]);
  const [playerSkill, setPlayerSkill] = useState('High/Pro Level');
  const [region, setRegion] = useState('North America');
  const [isInitializing, setIsInitializing] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/games`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success' && data.games && data.games.length > 0) {
          setGames(data.games);
          setSelectedGameId(data.games[0].id.toString());
        }
      })
      .catch(err => console.error("Failed to load games", err));
  }, []);

  const handleStart = async () => {
    setIsInitializing(true);
    try {
      const selectedGame = games.find(g => g.id.toString() === selectedGameId);
      const data = await api.analyzeVideo(videoId, { 
        game_id: selectedGame?.id,
        game_name: selectedGame?.game_name,
        game_type: selectedGame?.game_genre,
        player_skill: playerSkill, 
        region 
      });
      if (data.status === 'processing' && data.job_id) {
        onAnalyzeStarted(data.job_id);
      } else {
        alert('Failed to start analysis.');
        setIsInitializing(false);
      }
    } catch (err) {
      console.error(err);
      alert('Network error.');
      setIsInitializing(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center w-full max-w-4xl mx-auto mt-12 relative z-10 animate-float" style={{ animationDuration: '8s' }}>
      <div className="w-full glass-panel rounded-[2rem] p-10 relative overflow-hidden">
        {/* Subtle background glow */}
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-aurora-cyan/10 rounded-full blur-[100px] pointer-events-none"></div>
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-aurora-magenta/10 rounded-full blur-[100px] pointer-events-none"></div>

        <div className="flex items-center justify-between mb-10 pb-8 border-b border-white/10 relative z-10">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.15)]">
              <CheckCircle2 className="w-7 h-7 text-emerald-400" />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-white tracking-tight">Upload Successful</h3>
              <p className="text-sm text-white/50 flex items-center gap-2 mt-1">
                <Video className="w-3.5 h-3.5" /> {videoName}
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-white/40 uppercase tracking-widest flex items-center gap-2">
                <Gamepad2 className="w-4 h-4" /> Game
              </label>
              <select 
                value={selectedGameId} 
                onChange={e => setSelectedGameId(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-aurora-cyan/50 transition-colors appearance-none"
              >
                {games.map(g => (
                  <option key={g.id} value={g.id}>{g.game_name} ({g.game_genre})</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-white/40 uppercase tracking-widest flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" /> Player Skill Level
              </label>
              <select 
                value={playerSkill} 
                onChange={e => setPlayerSkill(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-aurora-magenta/50 transition-colors appearance-none"
              >
                <option>High/Pro Level</option>
                <option>Casual/Average</option>
                <option>Beginner/Noob</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-white/40 uppercase tracking-widest flex items-center gap-2">
                <Globe className="w-4 h-4" /> Region Culture
              </label>
              <select 
                value={region} 
                onChange={e => setRegion(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-aurora-magenta/50 transition-colors appearance-none"
              >
                <option>North America</option>
                <option>Europe</option>
                <option>Asia</option>
                <option>Global</option>
              </select>
            </div>
          </div>
        </div>

        {/* AI Intent Notice instead of Vibe/Narrative selector */}
        <div className="mt-8 relative z-10 bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-4 flex gap-4">
          <Info className="w-5 h-5 text-indigo-400 shrink-0" />
          <div>
            <h4 className="text-sm font-bold text-indigo-300">AI Director is Active</h4>
            <p className="text-xs text-indigo-400/80 mt-1 leading-relaxed">
              Based on your metadata, the AI Scriptwriter will automatically analyze the footage and generate multiple distinct variations (e.g., The Clutch, The Funny/Fail, The Educational Tip, The Speedrun) to test different YouTube retention algorithms.
            </p>
          </div>
        </div>

        <div className="mt-8 flex items-center justify-between relative z-10 pt-8 border-t border-white/10">
          <div className="flex items-center gap-4">
            <button 
              onClick={onCancel}
              className="px-6 py-3 rounded-full text-sm font-bold text-white/40 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <ModelSettings />
          </div>

          <button 
            onClick={handleStart}
            disabled={isInitializing}
            className={`px-8 py-4 rounded-full text-sm font-bold text-black bg-white flex items-center gap-3 transition-all duration-300 shadow-[0_0_30px_rgba(255,255,255,0.2)] hover:shadow-[0_0_40px_rgba(255,255,255,0.4)] hover:scale-105 disabled:opacity-50 disabled:hover:scale-100`}
          >
            {isInitializing ? (
              <>Igniting Engine <Loader2 className="w-4 h-4 animate-spin" /></>
            ) : (
              <>Start Generation <ArrowRight className="w-4 h-4" /></>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
