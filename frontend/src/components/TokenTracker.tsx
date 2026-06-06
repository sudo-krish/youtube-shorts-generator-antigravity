import React, { useEffect, useRef } from 'react';
import * as animeLib from 'animejs';
const anime = (animeLib as any).default || animeLib;

interface TokenTrackerProps {
  metrics: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  } | null;
}

export const TokenTracker: React.FC<TokenTrackerProps> = ({ metrics }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (metrics && containerRef.current) {
      anime({
        targets: containerRef.current,
        translateY: [20, 0],
        opacity: [0, 1],
        duration: 800,
        easing: 'easeOutElastic(1, .8)'
      });
    }
  }, [metrics]);

  if (!metrics) return null;

  return (
    <div ref={containerRef} className="glass-panel p-6 rounded-3xl w-full border border-white/5 opacity-0 mt-8">
      <h3 className="text-xl font-semibold text-white mb-4 tracking-wide">Antigravity Token Metrics</h3>
      <div className="grid grid-cols-3 gap-4">
        <div className="flex flex-col items-center justify-center bg-white/5 p-4 rounded-2xl border border-white/5">
          <span className="text-3xl font-bold text-white mb-1">{metrics.prompt_tokens}</span>
          <span className="text-xs text-premium-muted uppercase tracking-widest text-center">Prompt</span>
        </div>
        <div className="flex flex-col items-center justify-center bg-white/5 p-4 rounded-2xl border border-white/5">
          <span className="text-3xl font-bold text-white mb-1">{metrics.completion_tokens}</span>
          <span className="text-xs text-premium-muted uppercase tracking-widest text-center">Completion</span>
        </div>
        <div className="flex flex-col items-center justify-center bg-white/10 p-4 rounded-2xl border border-white/10 relative overflow-hidden shadow-[0_0_20px_rgba(255,255,255,0.05)]">
          <div className="absolute inset-0 bg-gradient-to-tr from-white/10 to-transparent"></div>
          <span className="text-3xl font-bold text-white mb-1 z-10">{metrics.total_tokens}</span>
          <span className="text-xs text-premium-muted uppercase tracking-widest z-10 text-center">Total</span>
        </div>
      </div>
    </div>
  );
};
