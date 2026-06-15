import React, { useState } from 'react';
import { CheckCircle2, CircleDashed, XCircle, ArrowRight, Activity, Code, Server, Eye, PenTool, Film, Settings } from 'lucide-react';

interface StageData {
    status: string;
    logs: string;
    timestamp: number;
}

interface PipelineVisualizerProps {
    stages: Record<string, StageData>;
}

// Define the logical execution order of the pipeline
const PIPELINE_STEPS = [
    { id: 'chunking', label: 'Video Chunking', icon: Film },
    { id: 'observer', label: 'Observer AI', icon: Eye },
    { id: 'scriptwriter', label: 'Scriptwriter AI', icon: PenTool },
    { id: 'director', label: 'Director AI', icon: Activity },
    { id: 'editor', label: 'Editor AI', icon: Code },
    { id: 'specialist', label: 'YouTube Specialist', icon: Server },
    { id: 'builder', label: 'JSON Builder', icon: Settings },
    { id: 'finalizing', label: 'Finalizing', icon: CheckCircle2 }
];

export const PipelineVisualizer: React.FC<PipelineVisualizerProps> = ({ stages }) => {
    const [selectedStage, setSelectedStage] = useState<string | null>(null);

    // Auto-select the first active or running stage if none is selected
    React.useEffect(() => {
        if (!selectedStage && stages && Object.keys(stages).length > 0) {
            // Find the furthest running or failed step, or just the last completed one
            let activeStepId = PIPELINE_STEPS[0].id;
            for (const step of PIPELINE_STEPS) {
                const stepStatus = getStepStatus(step.id);
                if (stepStatus === 'running' || stepStatus === 'failed') {
                    activeStepId = step.id;
                    break;
                } else if (stepStatus === 'completed') {
                    activeStepId = step.id;
                }
            }
            setSelectedStage(activeStepId);
        }
    }, [stages, selectedStage]);

    // Group the raw database stages into our logical pipeline steps
    // The DB keys look like: "chunking", "chunk_0_observer", "chunk_1_observer", etc.
    const getStepStatus = (stepId: string) => {
        if (stepId === 'chunking' || stepId === 'finalizing') {
            return stages[stepId]?.status || 'pending';
        }
        
        // For agents, they run per chunk. Let's find the latest chunk for this agent.
        const agentStages = Object.keys(stages).filter(k => k.endsWith(`_${stepId}`));
        if (agentStages.length === 0) return 'pending';
        
        // If any chunk is failed, the step is failed
        if (agentStages.some(k => stages[k].status === 'failed')) return 'failed';
        
        // If any chunk is running, the step is running
        if (agentStages.some(k => stages[k].status === 'running')) return 'running';
        
        // If all chunks are completed, the step is completed
        if (agentStages.every(k => stages[k].status === 'completed')) return 'completed';
        
        return 'running';
    };

    const getStepLogs = (stepId: string) => {
        if (stepId === 'chunking' || stepId === 'finalizing') {
            return stages[stepId]?.logs || 'Waiting for stage to begin...';
        }
        
        const agentStages = Object.keys(stages).filter(k => k.endsWith(`_${stepId}`));
        if (agentStages.length === 0) return 'Waiting for stage to begin...';
        
        // Return concatenated logs for all chunks of this agent
        return agentStages.map(k => `--- ${k} ---\n${stages[k].logs}`).join('\n\n');
    };

    return (
        <div className="flex flex-col gap-6 w-full h-full">
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <Activity className="w-6 h-6 text-indigo-400" />
                Live Execution Graph
            </h3>
            
            {/* AWS Step Functions style horizontal graph */}
            <div className="bg-black/40 border border-white/5 rounded-2xl p-6 overflow-x-auto">
                <div className="flex items-center min-w-max px-4">
                    {PIPELINE_STEPS.map((step, index) => {
                        const status = getStepStatus(step.id);
                        const isSelected = selectedStage === step.id;
                        const StepIcon = step.icon;
                        
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
                        } else if (status === 'running') {
                            statusColor = "text-blue-400 border-blue-500/50 bg-blue-500/10 shadow-[0_0_15px_rgba(59,130,246,0.3)]";
                            iconColor = "text-blue-400";
                            StatusIcon = CircleDashed;
                            animation = "animate-pulse";
                        }
                        
                        return (
                            <React.Fragment key={step.id}>
                                <div 
                                    onClick={() => setSelectedStage(step.id)}
                                    className={`relative flex flex-col items-center gap-3 cursor-pointer group transition-all transform hover:scale-105 ${isSelected ? 'scale-105' : ''}`}
                                >
                                    {/* Node Box */}
                                    <div className={`w-16 h-16 rounded-2xl border-2 flex items-center justify-center transition-all duration-300 ${statusColor} ${animation} ${isSelected ? 'ring-2 ring-white/50 ring-offset-2 ring-offset-black' : ''}`}>
                                        <StepIcon className={`w-8 h-8 ${iconColor}`} />
                                    </div>
                                    
                                    {/* Status Badge */}
                                    <div className={`absolute -top-2 -right-2 bg-black rounded-full`}>
                                        <StatusIcon className={`w-5 h-5 ${status === 'running' ? 'animate-spin text-blue-400' : iconColor}`} />
                                    </div>
                                    
                                    <span className={`text-xs font-medium tracking-wide whitespace-nowrap transition-colors ${isSelected ? 'text-white' : 'text-white/50 group-hover:text-white/80'}`}>
                                        {step.label}
                                    </span>
                                </div>
                                
                                {index < PIPELINE_STEPS.length - 1 && (
                                    <div className="flex-1 w-12 mx-2 flex items-center justify-center">
                                        <ArrowRight className={`w-5 h-5 ${status === 'completed' ? 'text-emerald-500/50' : 'text-white/10'}`} />
                                    </div>
                                )}
                            </React.Fragment>
                        );
                    })}
                </div>
            </div>

            {/* Stage Details Panel */}
            {selectedStage && (
                <div className="bg-black/60 border border-white/10 rounded-2xl p-6 flex flex-col gap-4 max-h-96 flex-grow animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="flex items-center justify-between border-b border-white/10 pb-4">
                        <h4 className="text-lg font-bold text-white flex items-center gap-2">
                            {PIPELINE_STEPS.find(s => s.id === selectedStage)?.label} Output
                        </h4>
                        <span className={`text-xs px-3 py-1 rounded-full uppercase tracking-widest font-bold ${getStepStatus(selectedStage) === 'completed' ? 'bg-emerald-500/20 text-emerald-300' : getStepStatus(selectedStage) === 'failed' ? 'bg-rose-500/20 text-rose-300' : getStepStatus(selectedStage) === 'running' ? 'bg-blue-500/20 text-blue-300' : 'bg-white/10 text-white/50'}`}>
                            {getStepStatus(selectedStage)}
                        </span>
                    </div>
                    
                    <pre className="text-white/80 font-mono text-xs overflow-auto whitespace-pre-wrap flex-grow bg-[#0a0a0a] p-4 rounded-xl border border-white/5">
                        {getStepLogs(selectedStage)}
                    </pre>
                </div>
            )}
        </div>
    );
};
