import { useState, useEffect } from 'react';
import { Save, Gamepad2, Plus, ArrowLeft } from 'lucide-react';
import { API_BASE_URL } from '../api';

export const GameContextManager = ({ onBack }: { onBack: () => void }) => {
  const [games, setGames] = useState<any[]>([]);
  const [gameTypes, setGameTypes] = useState<any[]>([]);
  const [selectedGameId, setSelectedGameId] = useState<string>('');
  const [contextText, setContextText] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [newGameName, setNewGameName] = useState('');
  const [newGameTypeId, setNewGameTypeId] = useState<string>('');

  const fetchGames = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/games`);
      const data = await res.json();
      if (data.status === 'success') {
        setGames(data.games || []);
        setGameTypes(data.types || []);
        if (data.games?.length > 0 && !selectedGameId) {
          setSelectedGameId(data.games[0].id.toString());
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchGames();
  }, []);

  useEffect(() => {
    if (selectedGameId) {
      fetch(`${API_BASE_URL}/api/games/${selectedGameId}/context`)
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            setContextText(data.context);
          }
        })
        .catch(console.error);
    }
  }, [selectedGameId]);

  const handleSaveContext = async () => {
    if (!selectedGameId) return;
    setIsSaving(true);
    try {
      await fetch(`${API_BASE_URL}/api/games/${selectedGameId}/context`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: contextText }),
      });
    } catch (e) {
      console.error(e);
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddGame = async () => {
    if (!newGameName || !newGameTypeId) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/games`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_name: newGameName, game_type_id: parseInt(newGameTypeId) })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setIsAdding(false);
        setNewGameName('');
        await fetchGames();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto mt-12 mb-20 animate-fade-in relative z-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <button 
            onClick={onBack}
            className="flex items-center gap-2 text-sm font-bold text-white/50 hover:text-white transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </button>
          <h2 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
            <Gamepad2 className="w-8 h-8 text-aurora-cyan" /> Game Context Manager
          </h2>
          <p className="text-white/50 mt-2">Manage supported games and inject custom lore for the Scriptwriter.</p>
        </div>
        <button 
          onClick={() => setIsAdding(!isAdding)}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl text-sm font-bold text-white flex items-center gap-2 transition-all"
        >
          <Plus className="w-4 h-4" /> Add New Game
        </button>
      </div>

      {isAdding && (
        <div className="glass-panel p-6 rounded-2xl mb-8 border border-aurora-cyan/30">
          <h3 className="text-lg font-bold text-white mb-4">Add Supported Game</h3>
          <div className="flex gap-4">
            <input 
              type="text" 
              placeholder="Game Name (e.g., Overwatch)"
              className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-white focus:border-aurora-cyan/50 outline-none"
              value={newGameName}
              onChange={e => setNewGameName(e.target.value)}
            />
            <select 
              className="bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-white focus:border-aurora-cyan/50 outline-none"
              value={newGameTypeId}
              onChange={e => setNewGameTypeId(e.target.value)}
            >
              <option value="">Select Genre</option>
              {gameTypes.map(t => (
                <option key={t.id} value={t.id}>{t.game_genre.toUpperCase()}</option>
              ))}
            </select>
            <button 
              onClick={handleAddGame}
              className="px-6 py-2 bg-aurora-cyan text-black font-bold rounded-xl hover:bg-aurora-cyan/80 transition-colors"
            >
              Add
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-12 gap-8">
        <div className="col-span-4 glass-panel rounded-2xl overflow-hidden">
          <div className="p-4 border-b border-white/10 bg-white/5">
            <h3 className="font-bold text-white">Supported Games</h3>
          </div>
          <div className="p-2 space-y-1 max-h-[600px] overflow-y-auto">
            {games.map(game => (
              <button
                key={game.id}
                onClick={() => setSelectedGameId(game.id.toString())}
                className={`w-full text-left px-4 py-3 rounded-xl text-sm font-bold transition-all flex justify-between items-center ${
                  selectedGameId === game.id.toString() 
                    ? 'bg-aurora-cyan text-black' 
                    : 'text-white/60 hover:bg-white/5 hover:text-white'
                }`}
              >
                {game.game_name}
                <span className={`text-[10px] px-2 py-1 rounded-full ${
                  selectedGameId === game.id.toString() ? 'bg-black/20 text-black' : 'bg-white/10 text-white/40'
                }`}>
                  {game.game_genre.toUpperCase()}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="col-span-8 glass-panel rounded-2xl flex flex-col h-[700px]">
          <div className="p-6 border-b border-white/10 flex justify-between items-center bg-white/5">
            <div>
              <h3 className="text-xl font-bold text-white">Knowledge Base</h3>
              <p className="text-xs text-white/50 mt-1">This text is injected into the Scriptwriter AI prompt.</p>
            </div>
            <button 
              onClick={handleSaveContext}
              disabled={isSaving}
              className="px-6 py-2.5 bg-white text-black font-bold rounded-xl text-sm flex items-center gap-2 hover:bg-white/90 disabled:opacity-50 transition-all shadow-[0_0_20px_rgba(255,255,255,0.2)]"
            >
              <Save className="w-4 h-4" /> {isSaving ? 'Saving...' : 'Save Context'}
            </button>
          </div>
          <div className="flex-1 p-6">
            <textarea
              className="w-full h-full bg-black/40 border border-white/10 rounded-xl p-6 text-sm text-white/90 font-mono leading-relaxed focus:border-aurora-cyan/50 focus:ring-1 focus:ring-aurora-cyan/50 outline-none resize-none"
              placeholder="Paste lore, map callouts, gun stats, patch notes, or meta details here..."
              value={contextText}
              onChange={e => setContextText(e.target.value)}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
