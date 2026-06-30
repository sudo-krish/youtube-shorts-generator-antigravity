import React from 'react';
import { CheckCircle2, CircleDashed, XCircle, ArrowRight, Activity, Cpu } from 'lucide-react';

interface StageData {
    stage_name: string;
    status: string;
    chunk_id?: string;
    timestamp: number;
}

interface PipelineVisualizerProps {
    stages: StageData[];
    selectedNodeId?: string | null;
    onNodeClick?: (nodeId: string) => void;
}

export const PipelineVisualizer: React.FC<PipelineVisualizerProps> = ({ stages, selectedNodeId, onNodeClick }) => {
    
    const renderNode = (stage: StageData, idx: number) => {
        const label = stage.stage_name;
        const status = stage.status;
        const nodeId = stage.stage_name;

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
                key={`${nodeId}-${idx}`}
                className={`relative flex flex-col items-center gap-2 group transition-all transform hover:scale-105 cursor-pointer ${isSelected ? 'scale-110' : ''}`}
                onClick={() => onNodeClick && onNodeClick(nodeId)}
            >
                <div className={`w-12 h-12 md:w-14 md:h-14 rounded-2xl border-2 flex items-center justify-center transition-all duration-300 ${statusColor} ${animation} ${isSelected ? 'ring-2 ring-white/50' : ''}`}>
                    <Cpu className={`w-6 h-6 md:w-6 md:h-6 ${iconColor}`} />
                </div>
                <div className="absolute -top-1 -right-1 bg-black rounded-full">
                    <StatusIcon className={`w-4 h-4 ${(status === 'running' || status === 'processing') ? 'animate-spin text-blue-400' : iconColor}`} />
                </div>
                <span className={`text-[11px] font-medium tracking-wide whitespace-nowrap transition-colors ${isSelected ? 'text-white' : 'text-white/50 group-hover:text-white/80'}`}>
                    {label.replace(/_/g, ' ')}
                </span>
            </div>
        );
    };

    return (
        <div className="flex flex-col gap-6 w-full h-full">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-indigo-400" />
                Live Execution Graph (Dynamic)
            </h3>
            
            <div className="bg-black/40 border border-white/5 rounded-2xl p-6 overflow-x-auto custom-scrollbar flex items-center justify-start min-h-[200px]">
                <div className="flex flex-wrap gap-6 items-center w-full px-4 pb-4">
                    {(!stages || stages.length === 0) ? (
                        <div className="text-white/30 text-sm italic">Waiting for orchestrator to define sequence...</div>
                    ) : (
                        stages.map((stage, idx) => (
                            <React.Fragment key={idx}>
                                {renderNode(stage, idx)}
                                {idx < stages.length - 1 && (
                                    <div className="flex items-center justify-center">
                                        <ArrowRight className="w-4 h-4 text-white/10" />
                                    </div>
                                )}
                            </React.Fragment>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};
