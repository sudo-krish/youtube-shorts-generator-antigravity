import { useState } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { UploadDropzone } from './components/upload/UploadDropzone';
import { ConfigurationPanel } from './components/upload/ConfigurationPanel';
import { ExecutionView } from './components/execution/ExecutionView';
import { RenderView } from './components/execution/RenderView';
import { DatabaseViewer } from './components/DatabaseViewer';
import { Dashboard } from './components/Dashboard';
import { GameContextManager } from './components/GameContextManager';
import { PipelineCanvas } from './components/testing/PipelineCanvas';

export const App = () => {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [wizardState, setWizardState] = useState<'UPLOAD' | 'CONFIG' | 'DB_VIEWER' | 'RENDER_VIEW' | 'DASHBOARD' | 'GAME_MANAGER' | 'TESTING_UI'>('UPLOAD');
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
    setSelectedJobId(jobId);
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 font-sans flex selection:bg-white/10 relative overflow-hidden">
      {/* Minimal ambient light effect instead of saturated aurora */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-3/4 h-[500px] bg-emerald-500/5 blur-[150px] rounded-full mix-blend-screen transform -translate-y-1/2"></div>
        <div className="absolute bottom-0 right-1/4 w-3/4 h-[500px] bg-indigo-500/5 blur-[150px] rounded-full mix-blend-screen transform translate-y-1/2"></div>
      </div>
      
      {/* Subtle Grain Overlay */}
      <div className="fixed inset-0 opacity-[0.02] pointer-events-none mix-blend-overlay z-0" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.85%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")' }}></div>

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
        onOpenTestingUI={() => {
          setSelectedJobId(null);
          setWizardState('TESTING_UI');
        }}
      />

      {/* MAIN CANVAS */}
      <main className="flex-1 h-screen overflow-y-auto relative z-10 p-6 sm:p-10 flex flex-col custom-scrollbar">
        {!selectedJobId ? (
          <div className="flex-1 flex flex-col justify-center max-w-7xl mx-auto w-full h-full">
            {wizardState === 'UPLOAD' && (
              <div className="max-w-4xl mx-auto w-full">
                <UploadDropzone onUploadComplete={handleUploadComplete} />
              </div>
            )}
            
            {wizardState === 'CONFIG' && currentVideoId && currentVideoName && (
              <div className="max-w-4xl mx-auto w-full">
                <ConfigurationPanel 
                  videoId={currentVideoId} 
                  videoName={currentVideoName} 
                  onAnalyzeStarted={handleAnalyzeStarted}
                  onCancel={() => setWizardState('UPLOAD')}
                />
              </div>
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

            {wizardState === 'TESTING_UI' && (
              <div className="flex flex-col h-full space-y-4">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Testing Canvas</h1>
                  <p className="text-sm text-zinc-400 mt-1">Visually build and test the API pipeline steps.</p>
                </div>
                <div className="flex-1 min-h-[600px]">
                  <PipelineCanvas />
                </div>
              </div>
            )}
          </div>
        ) : wizardState === 'RENDER_VIEW' ? (
          <div className="flex-1 max-w-7xl mx-auto w-full">
            <RenderView jobId={selectedJobId} />
          </div>
        ) : (
          <div className="flex-1 max-w-7xl mx-auto w-full">
            <ExecutionView jobId={selectedJobId} onNext={() => setWizardState('RENDER_VIEW')} />
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
