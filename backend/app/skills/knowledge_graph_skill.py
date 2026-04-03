"""
KnowledgeGraphSkill - 知识图谱查询

从内存中的图谱数据提供查询服务：
- 完整图谱
- 节点子图（BFS N 跳）
- 节点搜索
"""

from collections import defaultdict
from typing import Any

from app.skills.base_skill import BaseSkill
from app.utils.exceptions import GraphError


class KnowledgeGraphSkill(BaseSkill):
    name = "knowledge_graph"
    description = "知识图谱查询与节点关联分析"

    def __init__(self, graph_data: dict):
        """
        Args:
            graph_data: {"nodes": [...], "edges": [...]} 图谱数据
        """
        super().__init__()

        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self.adjacency: dict[str, list[tuple[str, dict]]] = defaultdict(list)

        if graph_data:
            self._load_graph(graph_data)

    def _load_graph(self, graph_data: dict) -> None:
        """加载图谱数据到内存结构"""
        for node in graph_data.get("nodes", []):
            self.nodes[node["id"]] = node

        self.edges = graph_data.get("edges", [])

        # 构建双向邻接表
        for edge in self.edges:
            src, tgt = edge["source"], edge["target"]
            self.adjacency[src].append((tgt, edge))
            self.adjacency[tgt].append((src, edge))

        self.logger.info(
            "图谱加载完成 nodes=%d edges=%d",
            len(self.nodes), len(self.edges),
        )

    def _execute_impl(self, params: dict) -> dict:
        """
        执行图谱查询。

        Args:
            params: {
                "action": "full_graph" | "node_subgraph" | "search_nodes",
                "node_id": str (action=node_subgraph 时),
                "depth": int (默认 2),
                "query": str (action=search_nodes 时)
            }
        """
        action = params.get("action", "full_graph")

        if action == "full_graph":
            return self.get_full_graph()
        elif action == "node_subgraph":
            node_id = params.get("node_id", "")
            depth = params.get("depth", 2)
            return self.get_node_subgraph(node_id, depth)
        elif action == "search_nodes":
            query = params.get("query", "")
            return self.search_nodes(query)
        else:
            raise GraphError(
                message=f"未知图谱操作: {action}",
                detail=f"可选: full_graph, node_subgraph, search_nodes",
            )

    def get_full_graph(self) -> dict:
        """返回完整图谱"""
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }

    def get_node_subgraph(self, node_id: str, depth: int = 2) -> dict:
        """
        BFS 获取节点的 N 跳子图。

        Args:
            node_id: 中心节点 ID
            depth: 搜索深度

        Returns:
            {"center_node": str, "depth": int, "nodes": [...], "edges": [...]}
        """
        if node_id not in self.nodes:
            self.logger.warning("节点不存在 node_id=%s", node_id)
            return {
                "center_node": node_id,
                "depth": depth,
                "nodes": [],
                "edges": [],
            }

        visited_nodes = {node_id}
        collected_edges = []
        current_layer = {node_id}

        for _ in range(depth):
            next_layer = set()
            for nid in current_layer:
                for neighbor_id, edge in self.adjacency.get(nid, []):
                    if neighbor_id not in visited_nodes:
                        visited_nodes.add(neighbor_id)
                        next_layer.add(neighbor_id)
                    # 收集边（只要两端都在已访问节点中）
                    collected_edges.append(edge)
            current_layer = next_layer

        # 去重边
        seen_edges = set()
        unique_edges = []
        for edge in collected_edges:
            key = (edge["source"], edge["target"], edge["relation"])
            if key not in seen_edges:
                seen_edges.add(key)
                src, tgt = edge["source"], edge["target"]
                if src in visited_nodes and tgt in visited_nodes:
                    unique_edges.append(edge)

        subgraph_nodes = [
            self.nodes[nid] for nid in visited_nodes if nid in self.nodes
        ]

        self.logger.debug(
            "子图提取 center=%s depth=%d nodes=%d edges=%d",
            node_id, depth, len(subgraph_nodes), len(unique_edges),
        )

        return {
            "center_node": node_id,
            "depth": depth,
            "nodes": subgraph_nodes,
            "edges": unique_edges,
        }

    def search_nodes(self, query: str) -> dict:
        """
        模糊搜索节点 label。

        Args:
            query: 搜索关键词

        Returns:
            {"nodes": [...]}
        """
        if not query:
            return {"nodes": []}

        query_lower = query.lower()
        matched = []

        for node in self.nodes.values():
            label = node.get("label", "").lower()
            if query_lower in label:
                matched.append(node)

        # 按匹配度排序（完全匹配优先，然后按 label 长度）
        matched.sort(key=lambda n: (
            0 if n["label"].lower() == query_lower else 1,
            len(n["label"]),
        ))

        self.logger.debug("节点搜索 query='%s' results=%d", query, len(matched))
        return {"nodes": matched[:20]}  # 最多返回 20 个
