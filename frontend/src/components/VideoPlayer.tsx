import { useEffect, useRef } from 'react';
import * as animeLib from 'animejs';
const anime = (animeLib as any).default || animeLib;

export const VideoPlayer = () => {
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    anime({
      targets: wrapperRef.current,
      translateY: [-5, 5],
      rotateX: [-1, 1],
      rotateY: [-1, 1],
      direction: 'alternate',
      loop: true,
      easing: 'easeInOutSine',
      duration: 5000
    });
  }, []);

  return (
    <div style={{ perspective: '1200px' }} className="w-full flex justify-center h-full">
      <div 
        ref={wrapperRef}
        className="glass-panel w-full max-w-[340px] aspect-[9/16] rounded-[2.5rem] p-[6px] relative group overflow-hidden border border-white/5 border-t-white/10 border-l-white/10"
      >
        <div className="w-full h-full bg-[#020202] rounded-[2rem] overflow-hidden relative border border-white/[0.03]">
          
          <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center z-10 transition-opacity duration-500 group-hover:opacity-100 opacity-70">
            <div className="w-16 h-16 rounded-full bg-white/5 backdrop-blur-xl border border-white/10 flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(255,255,255,0.05)] transition-all duration-700 group-hover:scale-110 group-hover:shadow-[0_0_40px_rgba(255,255,255,0.15)] group-hover:bg-white/10 cursor-pointer">
              <div className="w-0 h-0 border-t-[8px] border-t-transparent border-l-[14px] border-l-white/80 border-b-[8px] border-b-transparent ml-2"></div>
            </div>
            <span className="text-white/60 font-semibold tracking-[0.2em] uppercase text-[10px]">Preview Render</span>
          </div>

        </div>
      </div>
    </div>
  );
};
