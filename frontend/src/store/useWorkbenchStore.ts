import { create } from 'zustand';

export type ArcType = 'Hook' | 'Lore' | 'Walkthrough' | 'Struggle' | 'Victory' | 'Outro';

export interface ClipSegment {
  id: string;
  name: string;
  startTime: number;
  endTime: number;
}

export interface ActionBlock {
  id: string;
  startTime: number; // in seconds
  endTime: number; // in seconds
  arcType: ArcType;
  directorNotes: string; // Transcribed or typed instructions
  entities: string[]; // RAG linked entities (e.g., "@Erlang Shen")
  frameData?: string; // Base64 screenshot of the exact frame
  aiContext?: string; // Vision LLM transcription of the frame
  aiSuggestions?: string[]; // Clickable narrative suggestions
  modifiers: {
    freezeFrame: boolean;
    speedMultiplier: number; // e.g., 1.0, 2.0
    zoomFocus: 'center' | 'left' | 'right' | 'none';
  };
}

interface WorkbenchState {
  videoFile: File | null;
  videoUrl: string | null;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  playbackRate: number;
  blocks: ActionBlock[];
  
  // Cropping State
  inPoint: number | null;
  outPoint: number | null;
  clips: ClipSegment[];
  
  // Actions
  setVideo: (file: File) => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setPlaybackRate: (rate: number) => void;
  
  setInPoint: (time: number | null) => void;
  setOutPoint: (time: number | null) => void;
  saveClip: (name?: string) => void;
  removeClip: (id: string) => void;

  addBlock: (block: Omit<ActionBlock, 'id'> & { id?: string }) => void;
  updateBlock: (id: string, updates: Partial<ActionBlock>) => void;
  removeBlock: (id: string) => void;
}

export const useWorkbenchStore = create<WorkbenchState>((set) => ({
  videoFile: null,
  videoUrl: null,
  currentTime: 0,
  duration: 100, // Default fallback
  isPlaying: false,
  playbackRate: 1.0,
  blocks: [],
  
  inPoint: null,
  outPoint: null,
  clips: [],
  
  setVideo: (file) => set({ 
    videoFile: file, 
    videoUrl: URL.createObjectURL(file),
    currentTime: 0,
    duration: 100,
    isPlaying: false,
    inPoint: null,
    outPoint: null,
    clips: []
  }),
  setCurrentTime: (time) => set({ currentTime: time }),
  setDuration: (duration) => set({ duration }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  setPlaybackRate: (rate) => set({ playbackRate: rate }),
  
  setInPoint: (time) => set({ inPoint: time }),
  setOutPoint: (time) => set({ outPoint: time }),
  saveClip: (name) => set((state) => {
    if (state.inPoint === null || state.outPoint === null || state.inPoint >= state.outPoint) return state;
    const newClip: ClipSegment = {
      id: Math.random().toString(36).substr(2, 9),
      name: name || `Clip ${state.clips.length + 1}`,
      startTime: state.inPoint,
      endTime: state.outPoint
    };
    return {
      clips: [...state.clips, newClip],
      inPoint: null,
      outPoint: null
    };
  }),
  removeClip: (id) => set((state) => ({
    clips: state.clips.filter(c => c.id !== id)
  })),

  addBlock: (blockData) => set((state) => {
    const newBlock: ActionBlock = {
      ...blockData,
      id: blockData.id || Math.random().toString(36).substr(2, 9),
    } as ActionBlock;
    
    // Add block and sort by startTime
    const newBlocks = [...state.blocks, newBlock].sort((a, b) => a.startTime - b.startTime);
    return { blocks: newBlocks };
  }),
  
  updateBlock: (id, updates) => set((state) => {
    const updatedBlocks = state.blocks.map(block => 
      block.id === id ? { ...block, ...updates } : block
    );
    // Re-sort in case startTime changed
    return { blocks: updatedBlocks.sort((a, b) => a.startTime - b.startTime) };
  }),
  
  removeBlock: (id) => set((state) => ({
    blocks: state.blocks.filter(block => block.id !== id)
  })),
}));
