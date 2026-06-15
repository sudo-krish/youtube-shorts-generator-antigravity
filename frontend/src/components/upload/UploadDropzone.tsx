import React, { useState, useRef } from 'react';
import { Upload, Video, Loader2 } from 'lucide-react';

interface UploadDropzoneProps {
  onUploadComplete: (videoId: string, videoName: string) => void;
}

export const UploadDropzone = ({ onUploadComplete }: UploadDropzoneProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file.name.endsWith('.mp4')) {
      alert('Only .mp4 files are supported.');
      return;
    }
    
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData
      });
      const result = await response.json();
      if (result.status === 'success') {
        onUploadComplete(result.video_id, file.name);
      } else {
        alert('Upload failed: ' + result.detail);
      }
    } catch (err) {
      console.error('Upload error:', err);
      alert('Network error during upload.');
    } finally {
      setIsUploading(false);
    }
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
    <div className="flex flex-col items-center justify-center w-full max-w-3xl mx-auto mt-20 relative z-10">
      <div className="text-center mb-12">
        <h2 className="text-5xl font-black tracking-tight text-white mb-4">
          Upload your <span className="text-aurora">Gameplay</span>
        </h2>
        <p className="text-lg text-white/50 font-light">
          Drop any raw VOD. Antigravity will slice the best moments.
        </p>
      </div>

      <div 
        onClick={() => !isUploading && fileInputRef.current?.click()}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`w-full relative group cursor-pointer transition-all duration-500 rounded-[2rem] p-1 
          ${isDragging ? 'scale-[1.02]' : 'hover:scale-[1.01]'}
        `}
      >
        {/* Glow border effect */}
        <div className={`absolute inset-0 rounded-[2rem] transition-opacity duration-500 blur-xl
          ${isDragging ? 'bg-gradient-to-r from-aurora-cyan to-aurora-violet opacity-100' : 'bg-gradient-to-r from-aurora-cyan/50 to-aurora-magenta/50 opacity-0 group-hover:opacity-100'}
        `}></div>

        <div className={`relative w-full h-80 rounded-[1.9rem] flex flex-col items-center justify-center border-2 transition-all duration-500 glass-panel
          ${isDragging ? 'border-aurora-cyan bg-white/10' : 'border-white/10 bg-black/40 group-hover:bg-black/60'}
        `}>
          
          {isUploading ? (
            <div className="flex flex-col items-center animate-pulse">
              <Loader2 className="w-16 h-16 text-aurora-cyan animate-spin mb-6" />
              <p className="text-xl font-bold text-white tracking-widest uppercase">Uploading to Orbit...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <div className={`w-24 h-24 rounded-full flex items-center justify-center mb-6 transition-all duration-500
                ${isDragging ? 'bg-aurora-cyan/20 scale-110 shadow-[0_0_30px_rgba(0,255,255,0.3)]' : 'bg-white/5 group-hover:bg-white/10 group-hover:scale-105'}
              `}>
                <Upload className={`w-10 h-10 ${isDragging ? 'text-aurora-cyan' : 'text-white/40 group-hover:text-white/80'}`} />
              </div>
              <p className="text-2xl font-bold text-white mb-2">Drag & Drop Video</p>
              <p className="text-sm text-white/40 mb-6 tracking-wide">Supports .MP4 format</p>
              
              <div className="flex items-center gap-2 px-6 py-3 rounded-full bg-white/5 border border-white/10 group-hover:border-white/20 transition-all">
                <Video className="w-4 h-4 text-white/50" />
                <span className="text-sm font-medium text-white/70">Browse Files</span>
              </div>
            </div>
          )}
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
