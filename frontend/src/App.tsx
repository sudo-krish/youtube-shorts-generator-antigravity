import { useState } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { UploadDropzone } from './components/upload/UploadDropzone';
import { ConfigurationPanel } from './components/upload/ConfigurationPanel';
import { ExecutionView } from './components/execution/ExecutionView';
import { RenderView } from './components/execution/RenderView';
import { DatabaseViewer } from './components/DatabaseViewer';
import { Dashboard } from './components/Dashboard';
import { GameContextManager } from './components/GameContextManager';

export const App = () => {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [wizardState, setWizardState] = useState<'UPLOAD' | 'CONFIG' | 'DB_VIEWER' | 'RENDER_VIEW' | 'DASHBOARD' | 'GAME_MANAGER'>('UPLOAD');
  const [currentVideoId, setCurrentVideoId] = useState<string | null>(null);
  const [currentVideoName, setCurrentVideoName] = useState<string | null>(null);

  const handleSelectJob = (jobId: string | null) => {
    setSelectedJobId(jobId);
    if (!jobId) {
      setWizardState('UPLOAD');
      setCurrentVideoId(null);
      setCurrentVideoName(null);
    }
  };

  const handleUploadComplete = (videoId: string, videoName: string) => {
    setCurrentVideoId(videoId);
    setCurrentVideoName(videoName);
    setWizardState('CONFIG');
  };

  const handleAnalyzeStarted = (jobId: string) => {
    // When analysis starts, we transition to the ExecutionView
    // The ExecutionView depends on selectedJobId
    setSelectedJobId(jobId);
  };

  return (
    <div className="min-h-screen bg-premium-dark text-white font-sans flex selection:bg-white/20 relative overflow-hidden">
      {/* Aurora Background Effects */}
      <div className="aurora-bg">
        <div className="absolute rounded-full mix-blend-screen filter blur-[120px] opacity-30 animate-blob bg-aurora-cyan top-[-10%] left-[-10%] w-[500px] h-[500px]"></div>
        <div className="absolute rounded-full mix-blend-screen filter blur-[120px] opacity-30 animate-blob bg-aurora-magenta bottom-[-20%] right-[-10%] w-[600px] h-[600px]" style={{ animationDelay: '2s' }}></div>
        <div className="absolute rounded-full mix-blend-screen filter blur-[120px] opacity-30 animate-blob bg-aurora-violet top-[20%] left-[40%] w-[400px] h-[400px]" style={{ animationDelay: '4s' }}></div>
      </div>
      
      {/* Subtle Grain Overlay */}
      <div className="fixed inset-0 opacity-[0.015] pointer-events-none mix-blend-overlay z-0" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")' }}></div>

      <Sidebar 
        selectedJobId={selectedJobId} 
        onSelectJob={handleSelectJob} 
        onOpenDbViewer={() => {
          setSelectedJobId(null);
          setWizardState('DB_VIEWER');
        }}
        onOpenDashboard={() => {
          setSelectedJobId(null);
          setWizardState('DASHBOARD');
        }}
        onOpenGameManager={() => {
          setSelectedJobId(null);
          setWizardState('GAME_MANAGER');
        }}
      />

      {/* MAIN CANVAS */}
      <main className="flex-1 h-screen overflow-y-auto relative z-10 p-10 flex flex-col custom-scrollbar">
        {!selectedJobId ? (
          // NEW GENERATION FLOW
          <div className="flex-1 flex flex-col justify-center max-w-6xl mx-auto w-full">
            {wizardState === 'UPLOAD' && (
              <UploadDropzone onUploadComplete={handleUploadComplete} />
            )}
            
            {wizardState === 'CONFIG' && currentVideoId && currentVideoName && (
              <ConfigurationPanel 
                videoId={currentVideoId} 
                videoName={currentVideoName} 
                onAnalyzeStarted={handleAnalyzeStarted}
                onCancel={() => setWizardState('UPLOAD')}
              />
            )}
            
            {wizardState === 'DB_VIEWER' && (
              <DatabaseViewer onClear={() => {
                setWizardState('UPLOAD');
                window.location.reload();
              }} />
            )}
            
            {wizardState === 'DASHBOARD' && (
              <Dashboard />
            )}
            
            {wizardState === 'GAME_MANAGER' && (
              <GameContextManager onBack={() => setWizardState('UPLOAD')} />
            )}
          </div>
        ) : wizardState === 'RENDER_VIEW' ? (
          // BATCH RENDER FLOW
          <div className="flex-1 max-w-7xl mx-auto w-full">
            <RenderView jobId={selectedJobId} />
          </div>
        ) : (
          // EXECUTION FLOW
          <div className="flex-1 max-w-7xl mx-auto w-full">
            <ExecutionView jobId={selectedJobId} onNext={() => setWizardState('RENDER_VIEW')} />
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
