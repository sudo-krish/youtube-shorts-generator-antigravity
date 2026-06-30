import React from 'react';
import { BoxSelect, Video, FileText, Clapperboard, Scissors, Zap, Wrench } from 'lucide-react';

const NODE_PRESETS = [
  {
    type: 'apiAction',
    label: 'Extract Chunk',
    icon: <Scissors className="w-4 h-4 text-emerald-400" />,
    endpoint: '/media/editor/chunker',
    payloadTemplate: '{\n  "video_path": "{{ global.video_path }}",\n  "start_time": 0.0,\n  "duration": 15.0\n}'
  },
  {
    type: 'apiAction',
    label: 'YOLO Tracker',
    icon: <BoxSelect className="w-4 h-4 text-emerald-400" />,
    endpoint: '/transformers/yolo',
    payloadTemplate: '{\n  "video_path": "{{ global.video_path }}",\n  "duration": 900,\n  "step": 1.0\n}'
  },
  {
    type: 'apiAction',
    label: 'Narrator',
    icon: <Video className="w-4 h-4 text-blue-400" />,
    endpoint: '/agents/narrator',
    payloadTemplate: '{\n  "frame_dir": "/tmp/frames",\n  "yolo_data": {{ parent_node_id.data }}\n}'
  },
  {
    type: 'apiAction',
    label: 'Scriptwriter',
    icon: <FileText className="w-4 h-4 text-amber-400" />,
    endpoint: '/agents/scriptwriter',
    payloadTemplate: '{\n  "observer_context": {{ narrator.action_log }},\n  "web_trends": ""\n}'
  },
  {
    type: 'apiAction',
    label: 'Director',
    icon: <Clapperboard className="w-4 h-4 text-purple-400" />,
    endpoint: '/agents/director',
    payloadTemplate: '{\n  "observer_context": {{ narrator.action_log }},\n  "scripts": {{ scriptwriter.scripts }},\n  "sfx_library": "",\n  "music_library": ""\n}'
  },
  {
    type: 'apiAction',
    label: 'Editor',
    icon: <Scissors className="w-4 h-4 text-rose-400" />,
    endpoint: '/agents/editor',
    payloadTemplate: '{\n  "scripts_context": {{ scriptwriter.scripts }},\n  "director_vision": {{ director.director_rules }}\n}'
  },
  {
    type: 'apiAction',
    label: 'Specialist',
    icon: <Zap className="w-4 h-4 text-yellow-400" />,
    endpoint: '/agents/specialist',
    payloadTemplate: '{\n  "editor_breakdown": {{ editor.technical_directives }},\n  "math_report": "",\n  "youtube_rules": "",\n  "capabilities": ""\n}'
  },
  {
    type: 'apiAction',
    label: 'Builder',
    icon: <Wrench className="w-4 h-4 text-zinc-400" />,
    endpoint: '/agents/builder',
    payloadTemplate: '{\n  "validated_breakdown": {{ specialist.polished_breakdown }}\n}'
  },
  {
    type: 'apiAction',
    label: 'Generic API',
    icon: <Zap className="w-4 h-4 text-white" />,
    endpoint: '/agents/my_custom_agent',
    payloadTemplate: '{\n  "key": "value"\n}'
  }
];

export function Sidebar() {
  const onDragStart = (event: React.DragEvent, preset: typeof NODE_PRESETS[0]) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify(preset));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="w-64 glass-panel border-r border-zinc-800 flex flex-col h-full z-10 shrink-0">
      <div className="p-4 border-b border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-100">Components</h2>
        <p className="text-xs text-zinc-400 mt-1">Drag nodes to the canvas</p>
      </div>
      <div className="flex-1 p-4 overflow-y-auto custom-scrollbar flex flex-col gap-2">
        {NODE_PRESETS.map((preset) => (
          <div
            key={preset.label}
            className="glass-card p-3 rounded-lg flex items-center gap-3 cursor-grab hover:bg-zinc-800/80 transition-colors active:cursor-grabbing"
            onDragStart={(event) => onDragStart(event, preset)}
            draggable
          >
            {preset.icon}
            <span className="text-sm text-zinc-200">{preset.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
