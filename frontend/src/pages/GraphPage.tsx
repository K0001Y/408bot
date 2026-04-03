import { useState, useEffect, useRef, useCallback } from "react";
import { Search, Loader2, Maximize2, ZoomIn, ZoomOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { SubjectPicker } from "@/components/SubjectPicker";
import { api, type GraphNode, type GraphData } from "@/lib/api";
import { useLoading } from "@/hooks/useLoading";
import cytoscape, { type Core } from "cytoscape";

const NODE_COLORS: Record<string, string> = {
  chapter: "#f59e0b",
  concept: "#6366f1",
  algorithm: "#10b981",
};

const EDGE_COLORS: Record<string, string> = {
  "属于": "#374151",
  "相关": "#4b5563",
  "依赖": "#dc2626",
};

export function GraphPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<GraphNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [subject, setSubject] = useState<string | null>(null);
  const { loading, run } = useLoading();
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    run(async () => {
      const data = await api.getFullGraph();
      setGraphData(data);
    });
  }, [run]);

  useEffect(() => {
    if (!graphData || !containerRef.current) return;

    const filteredNodes = subject
      ? graphData.nodes.filter((n) => n.subject_code === subject || n.type === "chapter")
      : graphData.nodes;
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = graphData.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
    );

    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...filteredNodes.map((n) => ({
          data: { id: n.id, label: n.label, type: n.type, subject: n.subject_code },
        })),
        ...filteredEdges.map((e, i) => ({
          data: { id: `e${i}`, source: e.source, target: e.target, relation: e.relation },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-size": "10px",
            color: "#d1d5db",
            "text-valign": "bottom",
            "text-margin-y": 6,
            "background-color": (ele: cytoscape.NodeSingular) =>
              NODE_COLORS[ele.data("type")] ?? "#6366f1",
            width: (ele: cytoscape.NodeSingular) => (ele.data("type") === "chapter" ? 28 : 16),
            height: (ele: cytoscape.NodeSingular) => (ele.data("type") === "chapter" ? 28 : 16),
            "border-width": 2,
            "border-color": "#1e1e2e",
          } as cytoscape.Css.Node,
        },
        {
          selector: "edge",
          style: {
            width: 1,
            "line-color": (ele: cytoscape.EdgeSingular) =>
              EDGE_COLORS[ele.data("relation")] ?? "#4b5563",
            "target-arrow-color": (ele: cytoscape.EdgeSingular) =>
              EDGE_COLORS[ele.data("relation")] ?? "#4b5563",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.5,
          } as cytoscape.Css.Edge,
        },
        {
          selector: "node:selected",
          style: {
            "border-color": "#f59e0b",
            "border-width": 3,
          },
        },
        {
          selector: ".highlighted",
          style: {
            "border-color": "#f59e0b",
            "border-width": 3,
            "background-color": "#f59e0b",
          },
        },
      ],
      layout: {
        name: "cose",
        animate: false,
        nodeOverlap: 20,
        idealEdgeLength: () => 80,
        nodeRepulsion: () => 8000,
      },
    });

    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      setSelectedNode({
        id: node.data("id"),
        type: node.data("type"),
        label: node.data("label"),
        subject_code: node.data("subject"),
      });
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) setSelectedNode(null);
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [graphData, subject]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    const result = await run(() => api.searchNodes(searchQuery.trim()));
    if (result) {
      setSearchResults(result.nodes);
      // Highlight first result
      if (result.nodes.length > 0 && cyRef.current) {
        const cy = cyRef.current;
        cy.elements().removeClass("highlighted");
        const el = cy.getElementById(result.nodes[0].id);
        if (el.length) {
          el.addClass("highlighted");
          cy.animate({ center: { eles: el }, zoom: 1.5 } as cytoscape.AnimationOptions, { duration: 400 });
        }
      }
    }
  };

  const focusNode = useCallback((nodeId: string) => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    cy.elements().removeClass("highlighted");
    const el = cy.getElementById(nodeId);
    if (el.length) {
      el.addClass("highlighted");
      cy.animate({ center: { eles: el }, zoom: 1.8 } as cytoscape.AnimationOptions, { duration: 400 });
      setSelectedNode({
        id: el.data("id"),
        type: el.data("type"),
        label: el.data("label"),
        subject_code: el.data("subject"),
      });
    }
    setSearchResults([]);
  }, []);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-foreground">知识图谱</h1>
          <p className="text-xs text-muted-foreground">
            {graphData ? `${graphData.node_count} 个知识点 / ${graphData.edge_count} 条关联` : "加载中..."}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <SubjectPicker value={subject} onChange={setSubject} />
          <form
            onSubmit={(e) => { e.preventDefault(); handleSearch(); }}
            className="flex items-center gap-1"
          >
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索知识点..."
              className="w-48"
            />
            <Button type="submit" size="icon" variant="ghost" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            </Button>
          </form>
        </div>
      </header>

      {/* Graph + Panel */}
      <div className="relative flex-1">
        {/* Cytoscape container */}
        <div ref={containerRef} className="h-full w-full bg-background" />

        {/* Zoom controls */}
        <div className="absolute bottom-4 right-4 flex flex-col gap-1">
          <Button size="icon" variant="outline" className="h-8 w-8" onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.3)}>
            <ZoomIn className="h-3.5 w-3.5" />
          </Button>
          <Button size="icon" variant="outline" className="h-8 w-8" onClick={() => cyRef.current?.zoom(cyRef.current.zoom() / 1.3)}>
            <ZoomOut className="h-3.5 w-3.5" />
          </Button>
          <Button size="icon" variant="outline" className="h-8 w-8" onClick={() => cyRef.current?.fit(undefined, 40)}>
            <Maximize2 className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* Legend */}
        <div className="absolute left-4 top-4 flex gap-3 rounded-lg border border-border bg-card/90 px-3 py-2 backdrop-blur-sm">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-[10px] text-muted-foreground">
                {type === "chapter" ? "章节" : type === "concept" ? "概念" : "算法"}
              </span>
            </div>
          ))}
        </div>

        {/* Search results dropdown */}
        {searchResults.length > 0 && (
          <div className="absolute right-6 top-2 z-10 w-60 rounded-lg border border-border bg-card shadow-lg">
            <div className="max-h-60 overflow-y-auto p-1">
              {searchResults.map((n) => (
                <button
                  key={n.id}
                  onClick={() => focusNode(n.id)}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-xs transition-smooth hover:bg-secondary"
                >
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: NODE_COLORS[n.type] ?? "#6366f1" }} />
                  <span className="flex-1 truncate text-foreground">{n.label}</span>
                  <Badge variant="secondary" className="text-[10px]">{n.type}</Badge>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Selected node info */}
        {selectedNode && (
          <div className="absolute bottom-4 left-4 w-64 animate-slide-in-left rounded-lg border border-border bg-card p-4 shadow-lg">
            <div className="mb-2 flex items-center gap-2">
              <span className="h-3 w-3 rounded-full" style={{ backgroundColor: NODE_COLORS[selectedNode.type] ?? "#6366f1" }} />
              <span className="text-sm font-medium text-foreground">{selectedNode.label}</span>
            </div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <p>类型: {selectedNode.type === "chapter" ? "章节" : selectedNode.type === "concept" ? "概念" : "算法"}</p>
              {selectedNode.subject_code && <p>科目: {selectedNode.subject_code.toUpperCase()}</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}