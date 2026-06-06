import React, { useState } from 'react';
import { UploadZone } from './components/UploadZone';
import { FactoryDashboard } from './components/FactoryDashboard';
import { VideoPlayer } from './components/VideoPlayer';
import { TokenTracker } from './components/TokenTracker';
import { AdvancedToggles } from './components/AdvancedToggles';
import { LogViewer } from './components/LogViewer';

export interface TokenMetrics {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export const App = () => {
  const [metrics, setMetrics] = useState<TokenMetrics | null>(null);

  return (
    <div className="min-h-screen bg-premium-dark text-premium-light font-sans p-8 selection:bg-white/20 relative">
      {/* Subtle Grain Overlay */}
      <div className="fixed inset-0 opacity-[0.015] pointer-events-none mix-blend-overlay" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")' }}></div>

      <div className="max-w-7xl mx-auto relative z-10">
        <header className="mb-12 flex justify-between items-end">
          <div>
            <h1 className="text-4xl md:text-5xl font-bold bg-chrome-text text-transparent bg-clip-text mb-2 tracking-tight">Antigravity Studio</h1>
            <p className="text-premium-muted font-light tracking-wide text-lg">Hyper-Retentive Shorts Automation</p>
          </div>
          <div className="text-right">
             <div className="inline-block px-3 py-1 rounded-full border border-white/10 bg-white/5 text-xs text-white/50 tracking-widest uppercase">v2.0 Workspace</div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-8 flex flex-col gap-8">
            <UploadZone onUploadSuccess={(data) => {
               setMetrics(data.token_metrics);
            }} onProjectSelect={(project) => {
               // Optional: handle project selection if needed for metrics
            }}/>
            <FactoryDashboard />
          </div>

          <div className="lg:col-span-4 flex flex-col">
            <VideoPlayer />
            <TokenTracker metrics={metrics} />
            <AdvancedToggles />
          </div>
        </div>
        
        <div className="mt-8">
          <LogViewer />
        </div>
      </div>
    </div>
  );
};

export default App;
