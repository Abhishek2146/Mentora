import apiClient from "@/lib/api";

export interface MindMapNode {
  id: string;
  label: string;
  type: string;
  description?: string;
}

export interface MindMapEdge {
  source: string;
  target: string;
  relationship?: string;
}

export interface MindMap {
  id: number;
  user_id: number;
  source_type: string;
  source_id: number;
  title: string;
  nodes: MindMapNode[];
  edges: MindMapEdge[];
  created_at: string;
  updated_at?: string;
}

export const mindmapService = {
  async getMindMaps(): Promise<MindMap[]> {
    const res = await apiClient.get("/api/v1/mindmap/");
    return res.data;
  },

  async getMindMap(id: number): Promise<MindMap> {
    const res = await apiClient.get(`/api/v1/mindmap/${id}`);
    return res.data;
  },

  async generateMindMap(sourceType: "syllabus" | "note", sourceId: number): Promise<MindMap> {
    const res = await apiClient.post("/api/v1/mindmap/generate", {
      source_type: sourceType,
      source_id: sourceId,
    });
    return res.data;
  },
};
