import { useCallback, useEffect, useState, useMemo } from 'react';
import ReactFlow, {
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Node as FlowNode,
  Edge as FlowEdge,
  Position,
  Handle
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { MindMap } from '@/services/mindmapService';
import { Book, Maximize2, Minimize2, Tag, Layers, Database } from 'lucide-react';

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 250;
const nodeHeight = 80;

const getLayoutedElements = (nodes: FlowNode[], edges: FlowEdge[], direction = 'LR') => {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction, nodesep: 60, ranksep: 100 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? Position.Left : Position.Top;
    node.sourcePosition = isHorizontal ? Position.Right : Position.Bottom;

    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };

    return node;
  });

  return { nodes: layoutedNodes, edges };
};

interface CustomNodeData {
  label: string;
  type: string;
  description?: string;
  onSelect: (data: any) => void;
}

export default function MindMapCanvas({ mindMapData }: { mindMapData: MindMap }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodeData, setSelectedNodeData] = useState<CustomNodeData | null>(null);

  // Parse MindMap data into ReactFlow format
  useEffect(() => {
    if (!mindMapData) return;

    const flowNodes: FlowNode[] = mindMapData.nodes.map((n) => ({
      id: n.id,
      data: {
        label: n.label,
        type: n.type,
        description: n.description,
      },
      position: { x: 0, y: 0 },
      type: 'customNode', // We use a default custom type or just default node styling
    }));

    const flowEdges: FlowEdge[] = mindMapData.edges.map((e, idx) => ({
      id: `e-${e.source}-${e.target}-${idx}`,
      source: e.source,
      target: e.target,
      label: e.relationship,
      animated: true,
      style: { stroke: '#818cf8', strokeWidth: 2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#818cf8',
      },
    }));

    const layouted = getLayoutedElements(flowNodes, flowEdges, 'LR');
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
    setSelectedNodeData(null);
  }, [mindMapData]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: FlowNode) => {
    setSelectedNodeData(node.data as CustomNodeData);
  }, []);

  const nodeTypes = useMemo(() => ({ customNode: CustomNode }), []);

  return (
    <div className="flex w-full h-full relative">
      {/* ReactFlow Canvas */}
      <div className="flex-1 h-full">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          attributionPosition="bottom-left"
        >
          <Controls className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-lg rounded-lg overflow-hidden" />
          <Background color="#cbd5e1" gap={20} size={1.5} />
        </ReactFlow>
      </div>

      {/* Side Panel for Node Details */}
      {selectedNodeData && (
        <div className="w-80 border-l border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex flex-col absolute right-0 top-0 bottom-0 shadow-2xl z-10 animate-in slide-in-from-right-8 duration-200">
          <div className="p-4 border-b border-slate-100 dark:border-slate-700/60 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/50">
            <h3 className="font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
              <Book className="w-4 h-4 text-primary-500" /> Topic Details
            </h3>
            <button
              onClick={() => setSelectedNodeData(null)}
              className="text-slate-400 hover:text-slate-600 transition-colors"
            >
              <Maximize2 className="w-4 h-4 rotate-45" />
            </button>
          </div>
          
          <div className="p-5 flex-1 overflow-y-auto space-y-4">
            <div>
              <span className="inline-block text-[10px] font-bold px-2 py-1 rounded bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 mb-2 uppercase tracking-wider">
                {selectedNodeData.type}
              </span>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                {selectedNodeData.label}
              </h2>
            </div>
            
            {selectedNodeData.description && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Definition</h4>
                <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-700/60 text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {selectedNodeData.description}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Custom Node Component
function CustomNode({ data }: { data: CustomNodeData }) {
  // Styles based on node type
  let colors = "bg-white border-slate-200 text-slate-800 dark:bg-slate-800 dark:border-slate-600 dark:text-slate-100";
  let icon = <Database className="w-4 h-4" />;
  
  const type = data.type?.toLowerCase() || '';
  if (type === 'root') {
    colors = "bg-primary-50 border-primary-300 text-primary-900 dark:bg-primary-900/30 dark:border-primary-700 dark:text-primary-100 ring-2 ring-primary-500/20";
    icon = <Book className="w-5 h-5 text-primary-600 dark:text-primary-400" />;
  } else if (type === 'unit' || type === 'chapter') {
    colors = "bg-secondary-50 border-secondary-300 text-secondary-900 dark:bg-secondary-900/30 dark:border-secondary-700 dark:text-secondary-100";
    icon = <Layers className="w-4 h-4 text-secondary-600 dark:text-secondary-400" />;
  } else if (type === 'topic') {
    colors = "bg-emerald-50 border-emerald-300 text-emerald-900 dark:bg-emerald-900/30 dark:border-emerald-700 dark:text-emerald-100";
    icon = <Tag className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />;
  }

  return (
    <div className={`px-4 py-3 rounded-xl border-2 shadow-sm min-w-[180px] max-w-[280px] ${colors}`}>
      <Handle type="target" position={Position.Left} className="w-2 h-2 bg-slate-400" />
      <div className="flex items-center gap-2 mb-1.5">
        {icon}
        <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">
          {data.type}
        </span>
      </div>
      <div className="font-bold text-sm leading-tight break-words">
        {data.label}
      </div>
      <Handle type="source" position={Position.Right} className="w-2 h-2 bg-slate-400" />
    </div>
  );
}
