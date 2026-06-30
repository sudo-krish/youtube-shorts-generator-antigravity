import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  BackgroundVariant,
  ReactFlowProvider
} from '@xyflow/react';
import type { Connection, Edge, Node } from '@xyflow/react';
import { ApiActionNode } from './nodes/ApiActionNode';
import { NodeInspector } from './NodeInspector';
import { Sidebar } from './Sidebar';
import { genericApi } from '../../api/generic';
import { api } from '../../api';

const initialNodes: Node[] = [
  {
    id: 'global',
    type: 'apiAction',
    position: { x: 250, y: 50 },
    data: { 
      label: 'Global Context', 
      endpoint: '/mock/context',
      payloadTemplate: '{\n  "video_path": "/home/krish/projects/youtube-shorts-generator-antigravity/assets/input.mp4"\n}',
      status: 'success'
    },
  }
];

const initialEdges: Edge[] = [];

function PipelineCanvasContent() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeOutputs, setNodeOutputs] = useState<Record<string, any>>({
    'global': { video_path: "/home/krish/projects/youtube-shorts-generator-antigravity/assets/input.mp4" }
  });
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  useEffect(() => {
    const fetchLatestVideo = async () => {
      try {
        const res = await api.getUploadedVideos();
        if (res.videos && res.videos.length > 0) {
          const latest = res.videos[0];
          setNodes((nds) => 
            nds.map(node => {
              if (node.id === 'global') {
                return {
                  ...node,
                  data: {
                    ...node.data,
                    payloadTemplate: `{\n  "video_path": "${latest.video_path}"\n}`
                  }
                };
              }
              return node;
            })
          );
          setNodeOutputs(prev => ({
            ...prev,
            'global': { video_path: latest.video_path }
          }));
        }
      } catch (err) {
        console.error("Failed to fetch latest video for testing context", err);
      }
    };
    fetchLatestVideo();
  }, [setNodes]);

  const updateNodeStatus = (id: string, status: 'idle' | 'running' | 'success' | 'error') => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === id) {
          return { ...node, data: { ...node.data, status } };
        }
        return node;
      })
    );
  };

  const updateNodePayload = (id: string, payloadStr: string) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === id) {
          return { ...node, data: { ...node.data, payloadTemplate: payloadStr } };
        }
        return node;
      })
    );
  };

  const resolveTemplate = (template: string, currentNodes: Node[], currentOutputs: Record<string, any>) => {
    return template.replace(/\{\{\s*([\w.-]+)\s*\}\}/g, (_match, pathStr) => {
      const parts = pathStr.split('.');
      const sourceLabelOrId = parts[0];
      
      // Try to find the source node by label first (e.g., 'narrator'), then by exact ID
      const sourceNode = currentNodes.find(n => (n.data.label as string).toLowerCase() === sourceLabelOrId.toLowerCase() || n.id === sourceLabelOrId);
      const sourceId = sourceNode ? sourceNode.id : sourceLabelOrId;
      
      const output = currentOutputs[sourceId];
      if (!output) return 'null';
      
      let val = output;
      for (let i = 1; i < parts.length; i++) {
        if (val === undefined || val === null) break;
        val = val[parts[i]];
      }
      
      if (typeof val === 'object') return JSON.stringify(val);
      if (typeof val === 'string') return `"${val}"`;
      return String(val);
    });
  };

  const handleRunNode = async (nodeId: string) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return;

    updateNodeStatus(nodeId, 'running');
    try {
      // 1. Resolve template
      const resolvedTemplate = resolveTemplate(node.data.payloadTemplate as string, nodes, nodeOutputs);
      
      // 2. Parse payload
      let payload;
      try {
        payload = JSON.parse(resolvedTemplate);
      } catch (e) {
        throw new Error(`Invalid JSON payload after resolving template: ${resolvedTemplate}`);
      }

      // 3. Execute API (using a prefix if it's a known agent/transformer, or generically)
      // Since our endpoints are defined like "/transformers/yolo" or "/agents/narrator", 
      // we append them to the base API path if they start with a slash.
      const endpoint = node.data.endpoint as string;
      const apiPath = endpoint.startsWith('/') ? `/api/ai${endpoint}` : endpoint;
      
      let res;
      if (node.id === 'global') {
        // Mock global context node execution
        res = payload;
      } else {
        res = await genericApi.executeNode(apiPath, payload);
      }

      setNodeOutputs(prev => ({ ...prev, [nodeId]: res }));
      updateNodeStatus(nodeId, 'success');
    } catch (err) {
      console.error(err);
      updateNodeStatus(nodeId, 'error');
      setNodeOutputs(prev => ({ ...prev, [nodeId]: { error: String(err) } }));
    }
  };

  const nodeTypes = useMemo(() => ({
    apiAction: (props: any) => {
      const onRun = () => handleRunNode(props.id);
      return <ApiActionNode {...props} data={{ ...props.data, onRun }} />;
    }
  }), [nodes, nodeOutputs]);

  const onConnect = useCallback(
    (params: Connection | Edge) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      if (!reactFlowWrapper.current || !reactFlowInstance) return;

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const presetStr = event.dataTransfer.getData('application/reactflow');
      
      if (!presetStr) return;
      const preset = JSON.parse(presetStr);

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      // Generate an ID based on label for easier referencing in templates
      const baseId = preset.label.toLowerCase().replace(/\s+/g, '-');
      const existingCount = nodes.filter(n => n.id.startsWith(baseId)).length;
      const newNodeId = existingCount > 0 ? `${baseId}-${existingCount + 1}` : baseId;

      const newNode: Node = {
        id: newNodeId,
        type: preset.type,
        position,
        data: {
          label: preset.label,
          endpoint: preset.endpoint,
          payloadTemplate: preset.payloadTemplate,
          status: 'idle',
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, nodes, setNodes]
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  const selectedNode = nodes.find(n => n.id === selectedNodeId);

  return (
    <div className="w-full h-full flex relative overflow-hidden bg-zinc-950/50 rounded-xl border border-zinc-800/50">
      <Sidebar />
      <div className="flex-1 h-full relative" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          className="testing-canvas"
        >
          <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#3f3f46" />
          <Controls className="!bg-zinc-900 !border-zinc-800 !fill-zinc-400" />
          <MiniMap 
            nodeColor="#52525b" 
            maskColor="rgba(9, 9, 11, 0.8)" 
            className="!bg-zinc-900 !border-zinc-800"
          />
        </ReactFlow>

        <NodeInspector
          nodeId={selectedNodeId}
          nodeData={selectedNode?.data}
          outputData={selectedNodeId ? nodeOutputs[selectedNodeId] : null}
          onUpdatePayload={(payloadStr) => {
            if (selectedNodeId) updateNodePayload(selectedNodeId, payloadStr);
          }}
          onClose={() => setSelectedNodeId(null)}
        />
      </div>
    </div>
  );
}

export function PipelineCanvas() {
  return (
    <ReactFlowProvider>
      <PipelineCanvasContent />
    </ReactFlowProvider>
  );
}
