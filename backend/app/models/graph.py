"""
Pydantic 数据模型 - 知识图谱相关
"""

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """图谱节点"""
    id: str
    type: str = Field(..., description="节点类型: concept/algorithm/chapter")
    label: str = ""
    subject_code: str | None = None
    chapter: str | None = None
    chunk_id: str | None = None


class GraphEdge(BaseModel):
    """图谱边"""
    source: str
    target: str
    relation: str = Field(..., description="关系类型: 属于/依赖/相关")
    weight: float = 1.0


class KnowledgeGraphResponse(BaseModel):
    """完整图谱响应"""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    node_count: int = 0
    edge_count: int = 0


class NodeSubgraphResponse(BaseModel):
    """节点子图响应"""
    center_node: str
    depth: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphSearchResult(BaseModel):
    """图谱搜索结果"""
    nodes: list[GraphNode]
