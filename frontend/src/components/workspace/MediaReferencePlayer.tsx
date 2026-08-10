import React, { useRef, useEffect } from 'react';
import { useWorkbenchStore } from '../../store/useWorkbenchStore';
import { fetchClient } from '../../api/client';
import { Play, Pause, FastForward, SkipBack, SkipForward, Maximize, Save } from 'lucide-react';

export const MediaReferencePlayer: React.FC = () => {
  const { 
    videoUrl, currentTime, duration, isPlaying, playbackRate, 
    inPoint, outPoint, setInPoint, setOutPoint, saveClip,
    setIsPlaying, setCurrentTime, setDuration, setPlaybackRate, addBlock, updateBlock
  } = useWorkbenchStore();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Sync play state
  useEffect(() => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.play().catch(console.error);
      } else {
        videoRef.current.pause();
      }
    }
  }, [isPlaying]);

  // Sync playback rate
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.playbackRate = playbackRate;
    }
  }, [playbackRate]);

  // Hotkey listener inside the player to grab canvas frames
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        document.activeElement?.tagName === 'INPUT' ||
        document.activeElement?.tagName === 'TEXTAREA' ||
        document.activeElement?.tagName === 'SELECT'
      ) {
        return;
      }

      if (e.key.toLowerCase() === 'i') {
        e.preventDefault();
        setInPoint(currentTime);
      }
      
      if (e.key.toLowerCase() === 'o') {
        e.preventDefault();
        setOutPoint(currentTime);
      }

      if (e.key.toLowerCase() === 'm') {
        e.preventDefault();
        
        let frameData = '';
        if (videoRef.current && canvasRef.current) {
          const video = videoRef.current;
          const canvas = canvasRef.current;
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            frameData = canvas.toDataURL('image/jpeg', 0.8);
          }
        }

        setIsPlaying(false);
        const blockId = Math.random().toString(36).substr(2, 9);
        
        addBlock({
          id: blockId,
          startTime: currentTime,
          endTime: currentTime + 5,
          arcType: 'Hook',
          directorNotes: '',
          entities: [],
          frameData: frameData,
          aiContext: 'Loading AI Analysis...',
          aiSuggestions: [],
          modifiers: {
            freezeFrame: false,
            speedMultiplier: 1.0,
            zoomFocus: 'none'
          }
        });

        // Async API call to Vision LLM
        fetchClient('/vision/analyze-frame', {
          method: 'POST',
          body: JSON.stringify({
            payload: {
              frame_data: frameData
            }
          })
        }).then((res: unknown) => {
          const response = res as { output: { aiContext: string; aiSuggestions: string[] } };
          updateBlock(blockId, {
            aiContext: response.output.aiContext,
            aiSuggestions: response.output.aiSuggestions
          });
        }).catch((err: Error) => {
          updateBlock(blockId, {
            aiContext: `Vision AI Failed: ${err.message}`
          });
        });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentTime, addBlock, updateBlock, setIsPlaying, setInPoint, setOutPoint]);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleScrub = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = Number(e.target.value);
    setCurrentTime(newTime);
    if (videoRef.current) {
      videoRef.current.currentTime = newTime;
    }
  };

  const formatTime = (timeInSeconds: number) => {
    const d = new Date(timeInSeconds * 1000);
    return d.toISOString().substr(11, 8);
  };

  return (
    <div className="flex flex-col h-full bg-[#09090b] border-r border-slate-800 p-4 relative z-20">
      
      {/* Hidden Canvas for Frame Extraction */}
      <canvas ref={canvasRef} className="hidden" />

      {/* Video Player */}
      <div className="bg-black flex-grow rounded-[1rem] flex items-center justify-center relative overflow-hidden mb-4 shadow-[0_0_40px_rgba(0,0,0,0.5)] border border-white/5">
        {videoUrl ? (
          <video 
            ref={videoRef}
            src={videoUrl}
            className="w-full h-full object-contain"
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onEnded={() => setIsPlaying(false)}
            onClick={() => setIsPlaying(!isPlaying)}
          />
        ) : (
          <div className="text-slate-500 flex flex-col items-center">
            <span className="text-4xl mb-2">🎬</span>
            <span>No media loaded</span>
          </div>
        )}
      </div>
      
      {/* Enhanced Controls */}
      <div className="flex flex-col gap-3 bg-white/5 p-4 rounded-xl border border-white/5 backdrop-blur-md">
        
        {/* Scrubber */}
        <div className="flex flex-col gap-1 relative group">
          <div className="flex items-center gap-3">
            <span className="text-emerald-400 font-mono text-sm w-16 text-right">{formatTime(currentTime)}</span>
            <div className="flex-grow relative h-4 flex items-center">
              {/* Timeline Track */}
              <div className="absolute inset-x-0 h-2 bg-slate-800 rounded-lg pointer-events-none"></div>
              
              {/* Selection Highlight */}
              {inPoint !== null && (
                <div 
                  className="absolute h-2 bg-indigo-500/50 rounded-lg pointer-events-none"
                  style={{
                    left: `${(inPoint / (duration || 1)) * 100}%`,
                    width: outPoint !== null 
                      ? `${Math.max(0, (outPoint - inPoint) / (duration || 1)) * 100}%`
                      : `${(1 - inPoint / (duration || 1)) * 100}%`
                  }}
                ></div>
              )}
              
              <input 
                type="range" 
                min={0}
                max={duration || 100}
                step="0.01"
                value={currentTime}
                onChange={handleScrub}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
              />
              {/* Playhead thumb visual */}
              <div 
                className="absolute w-3 h-3 bg-emerald-500 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.8)] pointer-events-none transform -translate-x-1.5"
                style={{ left: `${(currentTime / (duration || 1)) * 100}%` }}
              ></div>
            </div>
            <span className="text-slate-400 font-mono text-sm w-16">{formatTime(duration)}</span>
          </div>
        </div>
        
        {/* Playback & Cropping Controls */}
        <div className="flex items-center justify-between mt-2">
          
          <div className="flex items-center gap-2">
            <button 
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${inPoint !== null ? 'bg-indigo-500 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
              onClick={() => setInPoint(currentTime)}
              title="Set In Point (I)"
            >
              [ I ] SET IN
            </button>
            <button 
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${outPoint !== null ? 'bg-indigo-500 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
              onClick={() => setOutPoint(currentTime)}
              title="Set Out Point (O)"
            >
              SET OUT [ O ]
            </button>
            
            <button 
              className="ml-2 px-3 py-1.5 bg-emerald-500/20 hover:bg-emerald-500/40 text-emerald-400 rounded-lg text-xs font-bold transition-colors flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={() => saveClip()}
              disabled={inPoint === null || outPoint === null || inPoint >= outPoint}
            >
              <Save className="w-3 h-3" /> Save Clip
            </button>
          </div>

          <div className="flex items-center gap-2 absolute left-1/2 transform -translate-x-1/2">
            <button 
              className="p-2 hover:bg-white/10 rounded-full text-slate-300 transition-colors"
              onClick={() => {
                if (videoRef.current) {
                  videoRef.current.currentTime -= 5;
                }
              }}
              title="Rewind 5s"
            >
              <SkipBack className="w-5 h-5" />
            </button>
            <button 
              className="p-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 rounded-full transition-colors shadow-[0_0_15px_rgba(16,185,129,0.4)]"
              onClick={() => setIsPlaying(!isPlaying)}
            >
              {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current" />}
            </button>
            <button 
              className="p-2 hover:bg-white/10 rounded-full text-slate-300 transition-colors"
              onClick={() => {
                if (videoRef.current) {
                  videoRef.current.currentTime += 5;
                }
              }}
              title="Forward 5s"
            >
              <SkipForward className="w-5 h-5" />
            </button>
          </div>

          <div className="flex items-center gap-4">
            {/* Playback Rate Dropdown */}
            <div className="flex items-center gap-2 text-sm text-slate-400 bg-black/40 px-3 py-1.5 rounded-lg border border-white/10">
              <FastForward className="w-4 h-4" />
              <select 
                value={playbackRate}
                onChange={(e) => setPlaybackRate(Number(e.target.value))}
                className="bg-transparent text-slate-200 outline-none cursor-pointer"
              >
                <option value={0.5}>0.5x</option>
                <option value={1}>1.0x</option>
                <option value={1.5}>1.5x</option>
                <option value={2}>2.0x</option>
              </select>
            </div>
            
            <button 
              className="p-2 hover:bg-white/10 rounded-full text-slate-300 transition-colors"
              onClick={() => videoRef.current?.requestFullscreen()}
              title="Fullscreen"
            >
              <Maximize className="w-5 h-5" />
            </button>
          </div>
        </div>
        
        <div className="text-center mt-2 border-t border-white/5 pt-2 flex justify-center gap-6">
          <span className="text-slate-500 font-mono text-xs uppercase tracking-widest flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
            'M' - Marker
          </span>
          <span className="text-slate-500 font-mono text-xs uppercase tracking-widest flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
            'I'/'O' - Crop Points
          </span>
        </div>
      </div>
    </div>
  );
};
