import { Handle, Position } from '@xyflow/react';
import { Play, CheckCircle2, XCircle, Loader2, Link } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

interface ApiActionNodeProps {
  data: {
    label: string;
    description?: string;
    endpoint: string;
    status: 'idle' | 'running' | 'success' | 'error';
    onRun: () => void;
  };
}

export function ApiActionNode({ data }: ApiActionNodeProps) {
  return (
    <div className={cn(
      "glass-card p-4 min-w-[280px] relative overflow-hidden group cursor-pointer",
      data.status === 'running' && "border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.2)]",
      data.status === 'success' && "border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.2)]",
      data.status === 'error' && "border-rose-500/50 shadow-[0_0_15px_rgba(244,63,94,0.2)]"
    )}>
      <Handle type="target" position={Position.Top} className="!bg-zinc-500" />
      
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-zinc-100">{data.label}</h3>
          <div className="flex items-center gap-1.5 mt-2 bg-zinc-900/80 px-2 py-1 rounded text-[10px] text-zinc-400 border border-zinc-800">
            <Link className="w-3 h-3" />
            <span className="truncate max-w-[180px]">{data.endpoint}</span>
          </div>
        </div>
        
        <div className="flex-shrink-0">
          {data.status === 'running' && <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />}
          {data.status === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
          {data.status === 'error' && <XCircle className="w-5 h-5 text-rose-400" />}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-zinc-800/50 flex justify-end">
        <button
          onClick={(e) => {
            e.stopPropagation();
            data.onRun();
          }}
          disabled={data.status === 'running'}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-800 text-xs font-medium text-zinc-200 transition-colors",
            "hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed",
            data.status === 'running' && "bg-blue-900/30 text-blue-400 border border-blue-900/50"
          )}
        >
          {data.status === 'running' ? (
            <>Running...</>
          ) : (
            <>
              <Play className="w-3.5 h-3.5" />
              Run
            </>
          )}
        </button>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-zinc-500" />
    </div>
  );
}
