import React from 'react';
import { CheckCircle2, CircleDashed, XCircle, ArrowRight, Activity, Code, Server, Eye, PenTool, Film, Settings, Cpu, Image, Move, Combine } from 'lucide-react';

interface StageData {
    status: string;
    logs: string;
    timestamp: number;
}

interface PipelineVisualizerProps {
    stages: Record<string, StageData>;
    selectedNodeId?: string | null;
    onNodeClick?: (nodeId: string) => void;
}

const AGENT_STEPS = [
    { id: 'ast_transformer', label: 'Audio (AST)', icon: Cpu },
    { id: 'siglip_transformer', label: 'Visual (SigLIP)', icon: Image },
    { id: 'spatial_transformer', label: 'Spatial Flow', icon: Move },
    { id: 'matrix_merging', label: 'Matrix Merge', icon: Combine },
    { id: 'observer', label: 'Observer', icon: Eye },
    { id: 'scriptwriter', label: 'Scriptwriter', icon: PenTool },
    { id: 'director', label: 'Director', icon: Activity },
    { id: 'editor', label: 'Editor', icon: Code },
    { id: 'specialist', label: 'Specialist', icon: Server },
    { id: 'builder', label: 'Builder', icon: Settings },
];

export const PipelineVisualizer: React.FC<PipelineVisualizerProps> = ({ stages, selectedNodeId, onNodeClick }) => {
    
    // Determine number of chunks, or if it's a legacy non-chunked job
    const chunkIndices = Object.keys(stages || {})
        .map(k => {
            const match = k.match(/^chunk_(\d+)_/);
            return match ? parseInt(match[1]) : -1;
        })
        .filter(i => i >= 0);
    
    // Check if it's a legacy job with direct stage names
    const hasLegacyStages = Object.keys(stages || {}).some(k => AGENT_STEPS.some(s => s.id === k));
    
    // If it has legacy stages, we render it as 1 batch. Otherwise max chunk index.
    const numChunks = hasLegacyStages ? 1 : (chunkIndices.length > 0 ? Math.max(...chunkIndices) + 1 : 0);
    
    const getStatusForNode = (chunkIdx: number, stepId: string) => {
        if (hasLegacyStages) {
            return (stages && stages[stepId]) ? stages[stepId].status : 'pending';
        }
        const key = `chunk_${chunkIdx}_${stepId}`;
        return (stages && stages[key]) ? stages[key].status : 'pending';
    };
    
    const renderNode = (label: string, Icon: any, status: string, tooltipText: string, nodeId: string) => {
        let statusColor = "text-white/20 border-white/10 bg-white/5";
        let iconColor = "text-white/30";
        let StatusIcon = CircleDashed;
        let animation = "";
        
        if (status === 'completed') {
            statusColor = "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
            iconColor = "text-emerald-400";
            StatusIcon = CheckCircle2;
        } else if (status === 'failed') {
            statusColor = "text-rose-400 border-rose-500/30 bg-rose-500/10";
            iconColor = "text-rose-400";
            StatusIcon = XCircle;
        } else if (status === 'running' || status === 'processing') {
            statusColor = "text-blue-400 border-blue-500/50 bg-blue-500/10 shadow-[0_0_15px_rgba(59,130,246,0.3)]";
            iconColor = "text-blue-400";
            StatusIcon = CircleDashed;
            animation = "animate-pulse";
        }
        
        const isSelected = selectedNodeId === nodeId;
        
        return (
            <div 
                className={`relative flex flex-col items-center gap-2 group transition-all transform hover:scale-105 cursor-pointer ${isSelected ? 'scale-110' : ''}`}
                title={tooltipText}
                onClick={() => onNodeClick && onNodeClick(nodeId)}
            >
                <div className={`w-12 h-12 md:w-14 md:h-14 rounded-2xl border-2 flex items-center justify-center transition-all duration-300 ${statusColor} ${animation} ${isSelected ? 'ring-2 ring-white/50' : ''}`}>
                    <Icon className={`w-6 h-6 md:w-6 md:h-6 ${iconColor}`} />
                </div>
                <div className="absolute -top-1 -right-1 bg-black rounded-full">
                    <StatusIcon className={`w-4 h-4 ${(status === 'running' || status === 'processing') ? 'animate-spin text-blue-400' : iconColor}`} />
                </div>
                <span className={`text-[11px] font-medium tracking-wide whitespace-nowrap transition-colors ${isSelected ? 'text-white' : 'text-white/50 group-hover:text-white/80'}`}>
                    {label}
                </span>
            </div>
        );
    };

    return (
        <div className="flex flex-col gap-6 w-full h-full">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-indigo-400" />
                Live Execution Graph
            </h3>
            
            <div className="bg-black/40 border border-white/5 rounded-2xl p-6 overflow-x-auto custom-scrollbar flex items-center justify-start min-h-[200px]">
                <div className="flex items-center min-w-max px-4 mx-auto pb-4">
                    
                    {/* Entry Node */}
                    {renderNode('Chunking', Film, (stages && stages['chunking']) ? stages['chunking'].status : 'pending', 'chunking', 'chunking')}
                    
                    <div className="w-10 flex items-center justify-center">
                        <ArrowRight className="w-5 h-5 text-white/10" />
                    </div>
                    
                    {/* Middle Batch Grid */}
                    <div className="flex flex-col gap-6 border-l-2 border-r-2 border-white/10 px-6 py-4 relative">
                        {numChunks === 0 ? (
                            <div className="text-white/30 text-sm italic">Waiting for batches...</div>
                        ) : (
                            Array.from({ length: numChunks }).map((_, chunkIdx) => (
                                <div key={chunkIdx} className="flex items-center gap-5">
                                    <div className="text-xs font-bold text-white/40 tracking-widest uppercase w-16">
                                        Batch {chunkIdx + 1}
                                    </div>
                                    {AGENT_STEPS.map((step, idx) => (
                                        <React.Fragment key={`${chunkIdx}-${step.id}`}>
                                            {renderNode(step.label, step.icon, getStatusForNode(chunkIdx, step.id), hasLegacyStages ? step.id : `chunk_${chunkIdx}_${step.id}`, hasLegacyStages ? step.id : `chunk_${chunkIdx}_${step.id}`)}
                                            {idx < AGENT_STEPS.length - 1 && (
                                                <div className="w-6 flex items-center justify-center">
                                                    <ArrowRight className="w-4 h-4 text-white/10" />
                                                </div>
                                            )}
                                        </React.Fragment>
                                    ))}
                                </div>
                            ))
                        )}
                        
                        {/* Connecting horizontal lines for the grid container */}
                        <div className="absolute top-1/2 -left-6 w-6 h-0.5 bg-white/10"></div>
                        <div className="absolute top-1/2 -right-6 w-6 h-0.5 bg-white/10"></div>
                    </div>
                    
                    <div className="w-10 flex items-center justify-center">
                        <ArrowRight className="w-5 h-5 text-white/10" />
                    </div>
                    
                    {/* Exit Node */}
                    {renderNode('Finalizing', CheckCircle2, (stages && stages['finalizing']) ? stages['finalizing'].status : 'pending', 'finalizing', 'finalizing')}
                    
                </div>
            </div>
        </div>
    );
};
