import { useState, useEffect } from 'react';
import { X, Settings, TerminalSquare } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

interface NodeInspectorProps {
  nodeId: string | null;
  nodeData: any;
  outputData: any;
  onUpdatePayload: (payloadStr: string) => void;
  onClose: () => void;
}

export function NodeInspector({ nodeId, nodeData, outputData, onUpdatePayload, onClose }: NodeInspectorProps) {
  const [activeTab, setActiveTab] = useState<'config' | 'output'>('config');
  const [localPayload, setLocalPayload] = useState('');

  useEffect(() => {
    if (nodeData?.payloadTemplate) {
      setLocalPayload(nodeData.payloadTemplate);
    }
  }, [nodeData?.payloadTemplate, nodeId]);

  if (!nodeId || !nodeData) return null;

  return (
    <div className="absolute right-4 top-4 bottom-4 w-96 glass-panel flex flex-col z-10 animate-in slide-in-from-right-8 duration-300 rounded-lg overflow-hidden border border-zinc-800">
      <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-zinc-900/50">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100">Node Inspector</h2>
          <p className="text-xs text-zinc-400 mt-0.5">{nodeData.label}</p>
        </div>
        <button 
          onClick={onClose}
          className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex border-b border-zinc-800">
        <button
          onClick={() => setActiveTab('config')}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-medium transition-colors border-b-2",
            activeTab === 'config' ? "border-emerald-500 text-emerald-400" : "border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
          )}
        >
          <Settings className="w-3.5 h-3.5" />
          Configuration
        </button>
        <button
          onClick={() => setActiveTab('output')}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-medium transition-colors border-b-2",
            activeTab === 'output' ? "border-emerald-500 text-emerald-400" : "border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
          )}
        >
          <TerminalSquare className="w-3.5 h-3.5" />
          Output Data
        </button>
      </div>
      
      <div className="flex-1 p-4 overflow-y-auto custom-scrollbar">
        {activeTab === 'config' ? (
          <div className="flex flex-col h-full space-y-4">
            <div>
              <label className="text-xs font-medium text-zinc-300 block mb-1.5">Endpoint</label>
              <input 
                type="text" 
                value={nodeData.endpoint} 
                readOnly
                className="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-xs text-zinc-400 font-mono"
              />
            </div>
            
            <div className="flex-1 flex flex-col">
              <label className="text-xs font-medium text-zinc-300 block mb-1.5">Payload Template (JSON)</label>
              <p className="text-[10px] text-zinc-500 mb-2 leading-relaxed">
                Use <code className="text-emerald-400/80 bg-emerald-400/10 px-1 rounded">{"{{"} node_id.key {"}}"}</code> syntax to inject values from connected parent nodes.
              </p>
              <textarea
                value={localPayload}
                onChange={(e) => setLocalPayload(e.target.value)}
                onBlur={() => onUpdatePayload(localPayload)}
                className="flex-1 w-full bg-zinc-950 border border-zinc-800 rounded p-3 text-xs text-zinc-300 font-mono resize-none focus:outline-none focus:border-emerald-500/50 transition-colors custom-scrollbar"
                placeholder={'{\n  "key": "value"\n}'}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-col h-full">
            <h3 className="text-xs font-medium text-zinc-300 mb-2 uppercase tracking-wider">Execution Result</h3>
            {outputData ? (
              <pre className="flex-1 text-[10px] sm:text-xs font-mono bg-zinc-950 p-3 rounded-lg overflow-x-auto overflow-y-auto border border-zinc-900 text-zinc-300 custom-scrollbar">
                {JSON.stringify(outputData, null, 2)}
              </pre>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 space-y-2">
                <TerminalSquare className="w-8 h-8 opacity-20" />
                <p className="text-xs italic text-center px-4">No output generated yet.<br/>Run the node on the canvas to view results.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
