import React from 'react';
import { useWorkbenchStore, type ArcType } from '../../store/useWorkbenchStore';
import { Sparkles, Bot, Clock } from 'lucide-react';

export const NarrativeBlueprint: React.FC = () => {
  const { blocks, removeBlock, updateBlock } = useWorkbenchStore();

  return (
    <div className="flex flex-col h-full bg-[#09090b] p-6 overflow-y-auto relative z-20">
      <div className="flex items-center gap-2 mb-6">
        <Sparkles className="w-5 h-5 text-indigo-400" />
        <h2 className="text-xl font-bold text-slate-100">Narrative Blueprint</h2>
      </div>
      
      {blocks.length === 0 ? (
        <div className="flex-grow flex flex-col items-center justify-center text-slate-500 border-2 border-dashed border-white/10 rounded-2xl bg-white/5">
          <Clock className="w-8 h-8 mb-3 opacity-50" />
          <p className="font-medium">Timeline is empty</p>
          <p className="text-sm opacity-70">Press 'M' during playback to drop a marker</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {blocks.map(block => (
            <div key={block.id} className="bg-black/60 border border-white/10 rounded-2xl p-5 flex flex-col gap-4 shadow-xl backdrop-blur-sm relative group overflow-hidden">
              
              {/* Subtle gradient background based on arc type could go here */}
              <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500 rounded-l-2xl"></div>

              {/* Header */}
              <div className="flex justify-between items-center pl-2">
                <div className="flex items-center gap-3">
                  <span className="bg-indigo-500/20 text-indigo-300 px-2.5 py-1 rounded-md text-xs font-mono border border-indigo-500/30 font-semibold shadow-[0_0_10px_rgba(99,102,241,0.2)]">
                    {new Date(block.startTime * 1000).toISOString().substr(11, 8)}
                  </span>
                  <select 
                    className="bg-transparent text-slate-300 text-sm font-semibold outline-none cursor-pointer hover:text-white transition-colors"
                    value={block.arcType}
                    onChange={(e) => updateBlock(block.id, { arcType: e.target.value as ArcType })}
                  >
                    <option className="bg-slate-900">Hook</option>
                    <option className="bg-slate-900">Lore</option>
                    <option className="bg-slate-900">Walkthrough</option>
                    <option className="bg-slate-900">Struggle</option>
                    <option className="bg-slate-900">Victory</option>
                    <option className="bg-slate-900">Outro</option>
                  </select>
                </div>
                
                <button 
                  onClick={() => removeBlock(block.id)}
                  className="text-slate-500 hover:text-red-400 transition-colors p-1"
                  aria-label="Remove block"
                >
                  ✕
                </button>
              </div>

              {/* AI Context (Vision LLM Output) */}
              {block.aiContext && (
                <div className="pl-2">
                  <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-3 flex gap-3 items-start">
                    <Bot className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                    <p className="text-sm text-indigo-200/80 italic leading-relaxed">
                      "{block.aiContext}"
                    </p>
                  </div>
                </div>
              )}
              
              {/* Director Notes */}
              <div className="pl-2">
                <textarea 
                  className="bg-white/5 border border-white/10 text-slate-200 rounded-xl p-3 text-sm min-h-[80px] w-full resize-none placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:bg-white/10 transition-all shadow-inner"
                  placeholder="Director notes or dictation..."
                  value={block.directorNotes}
                  onChange={(e) => updateBlock(block.id, { directorNotes: e.target.value })}
                />
              </div>

              {/* AI Narrative Suggestions */}
              {block.aiSuggestions && block.aiSuggestions.length > 0 && (
                <div className="pl-2 flex flex-wrap gap-2">
                  {block.aiSuggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        const newNotes = block.directorNotes 
                          ? `${block.directorNotes}\nSuggestion: ${suggestion}`
                          : `Suggestion: ${suggestion}`;
                        updateBlock(block.id, { directorNotes: newNotes });
                      }}
                      className="text-xs bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-full px-3 py-1.5 transition-colors text-left flex items-center gap-1.5"
                    >
                      <Sparkles className="w-3 h-3" />
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
