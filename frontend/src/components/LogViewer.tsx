import { useEffect, useRef, useState } from 'react';
import { Terminal } from 'lucide-react';
import { api } from '../api';

interface LogViewerProps {
    jobId: string;
}

export const LogViewer = ({ jobId }: LogViewerProps) => {
    const [logs, setLogs] = useState<string[]>([]);
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const wsUrl = api.getWebSocketUrl(jobId);
        const ws = new WebSocket(wsUrl);
        
        ws.onmessage = (event) => {
            // Check if it's the initial full log dump (could be multi-line)
            const text = event.data as string;
            const newLines = text.split('\n').filter(l => l.trim() !== '');
            setLogs(prev => [...prev, ...newLines].slice(-200));
        };

        return () => {
            ws.close();
        };
    }, [jobId]);

    useEffect(() => {
        if (endRef.current) {
            endRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs]);

    return (
        <div className="w-full h-full bg-black border border-white/10 rounded-xl overflow-hidden flex flex-col font-mono text-sm shadow-inner relative">
            <div className="bg-[#1a1a1a] px-4 py-2 border-b border-white/10 flex items-center gap-2 sticky top-0 z-10">
                <Terminal className="w-4 h-4 text-green-400" />
                <span className="text-white/70 text-xs font-semibold uppercase tracking-wider">Antigravity Terminal</span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-1">
                {logs.length === 0 ? (
                    <div className="text-white/30 italic">Waiting for incoming logs...</div>
                ) : (
                    logs.map((log, i) => (
                        <div key={i} className="text-green-400/90 whitespace-pre-wrap break-all">
                            {log}
                        </div>
                    ))
                )}
                <div ref={endRef} />
            </div>
        </div>
    );
};
