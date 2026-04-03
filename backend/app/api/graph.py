"""
知识图谱 API 路由

端点:
- GET /          - 完整图谱
- GET /node/{id} - 节点子图（BFS N 跳）
- GET /search    - 搜索节点
"""

from fastapi import APIRouter, Request, Query

from app.models.graph import (
    KnowledgeGraphResponse, NodeSubgraphResponse,
    GraphSearchResult, GraphNode, GraphEdge,
)
from app.utils.logging import get_logger
from app.utils.dependencies import get_app_state, AppState
from app.utils.exceptions import GraphError

logger = get_logger("api.graph")

router = APIRouter()


@router.get("/", response_model=KnowledgeGraphResponse)
async def get_full_graph(request: Request):
    """获取完整知识图谱"""
    state: AppState = get_app_state(request)
    skill = state.get_skill("knowledge_graph")

    logger.info("获取完整知识图谱")

    result = skill.execute({"action": "full_graph"})

    return KnowledgeGraphResponse(
        nodes=[GraphNode(**n) for n in result.get("nodes", [])],
        edges=[GraphEdge(**e) for e in result.get("edges", [])],
        node_count=result.get("node_count", 0),
        edge_count=result.get("edge_count", 0),
    )


@router.get("/node/{node_id}", response_model=NodeSubgraphResponse)
async def get_node_subgraph(
    node_id: str,
    request: Request,
    depth: int = Query(2, ge=1, le=5, description="搜索深度"),
):
    """获取节点子图（BFS N 跳邻居）"""
    state: AppState = get_app_state(request)
    skill = state.get_skill("knowledge_graph")

    logger.info("获取节点子图 node_id=%s depth=%d", node_id, depth)

    result = skill.execute({
        "action": "node_subgraph",
        "node_id": node_id,
        "depth": depth,
    })

    return NodeSubgraphResponse(
        center_node=result.get("center_node", node_id),
        depth=result.get("depth", depth),
        nodes=[GraphNode(**n) for n in result.get("nodes", [])],
        edges=[GraphEdge(**e) for e in result.get("edges", [])],
    )


@router.get("/search", response_model=GraphSearchResult)
async def search_nodes(
    request: Request,
    q: str = Query("", description="搜索关键词"),
):
    """搜索图谱节点"""
    state: AppState = get_app_state(request)
    skill = state.get_skill("knowledge_graph")

    logger.info("节点搜索 q='%s'", q)

    result = skill.execute({
        "action": "search_nodes",
        "query": q,
    })

    return GraphSearchResult(
        nodes=[GraphNode(**n) for n in result.get("nodes", [])],
    )
