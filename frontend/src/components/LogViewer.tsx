import { useEffect, useRef, useState } from 'react';
import { Terminal } from 'lucide-react';

export const LogViewer = () => {
    const [logs, setLogs] = useState<string[]>([]);
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/api/logs');
        
        ws.onmessage = (event) => {
            setLogs(prev => [...prev, event.data].slice(-200));
        };

        return () => {
            ws.close();
        };
    }, []);

    useEffect(() => {
        if (endRef.current) {
            endRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs]);

    return (
        <div className="w-full h-80 bg-black border border-white/10 rounded-xl overflow-hidden flex flex-col font-mono text-sm shadow-inner relative mt-4">
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
