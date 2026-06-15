import { useState } from 'react';
import { api } from '../api';

export const AdvancedToggles = () => {
  const [bRoll, setBRoll] = useState(true);
  const [zooms, setZooms] = useState(true);
  const [seo, setSeo] = useState(false);
  const [sfx, setSfx] = useState(true);
  const [isDownloadingSFX, setIsDownloadingSFX] = useState(false);

  const downloadSFX = async () => {
      setIsDownloadingSFX(true);
      try {
          const res = await api.installSfx();
          if (res.status === 'success') {
              alert('SFX Pack successfully installed!');
          }
      } catch (e) {
          alert('Failed to download SFX pack');
      } finally {
          setIsDownloadingSFX(false);
      }
  };

  const Toggle = ({ label, desc, state, setter }: any) => (
    <div className="flex items-center justify-between p-4 bg-white/[0.02] border border-white/5 rounded-2xl mb-3 hover:bg-white/[0.04] transition-colors cursor-pointer" onClick={() => setter(!state)}>
      <div className="pr-4">
        <h4 className="text-white font-medium mb-1">{label}</h4>
        <p className="text-xs text-premium-muted font-light leading-relaxed">{desc}</p>
      </div>
      <button 
        className={`w-12 h-6 rounded-full transition-colors duration-300 relative shrink-0 ${state ? 'bg-white/40' : 'bg-white/10'}`}
      >
        <div className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform duration-300 ${state ? 'translate-x-6' : 'translate-x-0'}`} />
      </button>
    </div>
  );

  return (
    <div className="glass-panel p-6 rounded-3xl w-full border border-white/5 mt-8">
      <h3 className="text-xl font-semibold text-white mb-4 tracking-wide">Sound Design Engine</h3>
      
      <button 
          onClick={downloadSFX}
          disabled={isDownloadingSFX}
          className="w-full py-3 mb-6 rounded-xl font-bold transition-all bg-emerald-500/20 border border-emerald-500/50 hover:bg-emerald-500/30 text-emerald-200 disabled:opacity-50"
      >
          {isDownloadingSFX ? 'Downloading SFX Assets...' : 'Download / Update Free SFX Pack'}
      </button>

      <Toggle label="Multi-Track SFX Injection" desc="Dynamically layers impacts, risers, and swooshes over the music bed at peak intensity timestamps." state={sfx} setter={setSfx} />

      <h3 className="text-xl font-semibold text-white mb-4 tracking-wide mt-8">Engine Features</h3>
      <Toggle label="Intelligent B-Roll & Memes" desc="Auto-inserts green screen reactions during 'Struggle' phases." state={bRoll} setter={setBRoll} />
      <Toggle label="Audio-Driven Smart Zooms" desc="Punches in on audio amplitude spikes for comedic effect." state={zooms} setter={setZooms} />
      <Toggle label="Multi-Platform SEO Output" desc="Generates optimized titles/tags for YT Shorts, Reels, and TikTok." state={seo} setter={setSeo} />
    </div>
  );
};
