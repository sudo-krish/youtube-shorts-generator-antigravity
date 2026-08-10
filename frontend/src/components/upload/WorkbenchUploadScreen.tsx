import React, { useState, useRef } from 'react';
import { Upload, Video } from 'lucide-react';
import { useWorkbenchStore } from '../../store/useWorkbenchStore';

export const WorkbenchUploadScreen: React.FC = () => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const setVideo = useWorkbenchStore(state => state.setVideo);

  const handleFile = (file: File) => {
    if (!file.name.endsWith('.mp4')) {
      alert('Only .mp4 files are supported.');
      return;
    }
    setVideo(file);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => setIsDragging(false);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="h-screen w-screen bg-[#09090b] flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Ambient background matching original aesthetic */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-3/4 h-[500px] bg-emerald-500/10 blur-[150px] rounded-full mix-blend-screen transform -translate-y-1/2"></div>
        <div className="absolute bottom-0 right-1/4 w-3/4 h-[500px] bg-indigo-500/10 blur-[150px] rounded-full mix-blend-screen transform translate-y-1/2"></div>
      </div>
      
      <div className="text-center mb-12 relative z-10">
        <h2 className="text-5xl font-black tracking-tight text-white mb-4">
          Upload to <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-indigo-500">Workbench</span>
        </h2>
        <p className="text-lg text-white/50 font-light">
          Drop any raw VOD to begin blueprinting locally. No upload wait times.
        </p>
      </div>

      <div 
        onClick={() => fileInputRef.current?.click()}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`w-full max-w-3xl relative group cursor-pointer transition-all duration-500 rounded-[2rem] p-1 z-10
          ${isDragging ? 'scale-[1.02]' : 'hover:scale-[1.01]'}
        `}
      >
        <div className={`absolute inset-0 rounded-[2rem] transition-opacity duration-500 blur-xl
          ${isDragging ? 'bg-gradient-to-r from-emerald-500 to-indigo-500 opacity-50' : 'bg-gradient-to-r from-emerald-500/30 to-indigo-500/30 opacity-0 group-hover:opacity-50'}
        `}></div>

        <div className={`relative w-full h-80 rounded-[1.9rem] flex flex-col items-center justify-center border-2 transition-all duration-500 backdrop-blur-sm
          ${isDragging ? 'border-emerald-500 bg-white/10' : 'border-white/10 bg-black/40 group-hover:bg-black/60'}
        `}>
          <div className="flex flex-col items-center">
            <div className={`w-24 h-24 rounded-full flex items-center justify-center mb-6 transition-all duration-500
              ${isDragging ? 'bg-emerald-500/20 scale-110 shadow-[0_0_30px_rgba(16,185,129,0.3)]' : 'bg-white/5 group-hover:bg-white/10 group-hover:scale-105'}
            `}>
              <Upload className={`w-10 h-10 ${isDragging ? 'text-emerald-400' : 'text-white/40 group-hover:text-white/80'}`} />
            </div>
            <p className="text-2xl font-bold text-white mb-2">Drag & Drop Video</p>
            <p className="text-sm text-white/40 mb-6 tracking-wide">Supports .MP4 format</p>
            
            <div className="flex items-center gap-2 px-6 py-3 rounded-full bg-white/5 border border-white/10 group-hover:border-white/20 transition-all">
              <Video className="w-4 h-4 text-white/50" />
              <span className="text-sm font-medium text-white/70">Browse Local Files</span>
            </div>
          </div>
        </div>
      </div>
      <input 
        type="file" 
        accept=".mp4" 
        className="hidden" 
        ref={fileInputRef}
        onChange={(e) => e.target.files && handleFile(e.target.files[0])}
      />
    </div>
  );
};
