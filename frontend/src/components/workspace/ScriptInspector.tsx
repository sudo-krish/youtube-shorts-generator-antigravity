import React from 'react';

export const ScriptInspector: React.FC = () => {
  return (
    <div className="flex flex-col h-full bg-slate-900 border-l border-slate-800 p-4">
      <h2 className="text-xl font-bold mb-4 text-slate-200">AI Script & Spec</h2>
      
      <div className="flex-grow bg-slate-950 rounded-lg p-4 border border-slate-800 mb-4 overflow-y-auto">
        <p className="text-slate-500 italic text-sm">
          Awaiting script generation. Add action blocks and click Generate to see the preview here.
        </p>
      </div>
      
      <div className="flex flex-col gap-2">
        <button className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 text-white rounded transition-colors font-semibold">
          Generate Script
        </button>
        <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition-colors">
          Render Final Video
        </button>
      </div>
    </div>
  );
};
