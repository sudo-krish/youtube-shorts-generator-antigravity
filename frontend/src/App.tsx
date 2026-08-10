import { MediaReferencePlayer } from './components/workspace/MediaReferencePlayer';
import { NarrativeBlueprint } from './components/workspace/NarrativeBlueprint';
import { ScriptInspector } from './components/workspace/ScriptInspector';
import { ClipLibrary } from './components/workspace/ClipLibrary';
import { WorkbenchUploadScreen } from './components/upload/WorkbenchUploadScreen';
import { useWorkbenchStore } from './store/useWorkbenchStore';

export const App = () => {
  const { videoUrl } = useWorkbenchStore();

  if (!videoUrl) {
    return <WorkbenchUploadScreen />;
  }

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col font-sans overflow-hidden">
      {/* Header */}
      <header className="h-14 border-b border-slate-800 flex items-center px-6 bg-slate-900 shrink-0">
        <h1 className="text-lg font-bold tracking-tight">AI Director's Workbench</h1>
      </header>
      
      {/* 3-Pane Workspace */}
      <main className="flex-1 grid grid-cols-[1fr_400px_1fr] h-[calc(100vh-3.5rem)]">
        {/* Left Pane */}
        <section className="h-full overflow-hidden">
          <MediaReferencePlayer />
        </section>
        
        {/* Center Pane */}
        <section className="h-full border-x border-slate-800 overflow-hidden shadow-2xl z-10 relative">
          <NarrativeBlueprint />
        </section>
        
        {/* Right Pane */}
        <section className="h-full overflow-hidden flex flex-col">
          <div className="h-1/2 overflow-hidden border-b border-slate-800">
            <ScriptInspector />
          </div>
          <ClipLibrary />
        </section>
      </main>
    </div>
  );
};

export default App;
