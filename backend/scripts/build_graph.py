"""
知识图谱构建脚本

从 processed/*.json 的 chunk 数据自动构建知识图谱。

节点类型:
- chapter: 章节节点
- concept: 概念节点（默认）
- algorithm: 算法节点

边类型:
- 属于: 概念/算法 → 所属章节
- 相关: 同一 section 下的概念关联
- 依赖: 文本中提取的先修关系

用法:
    cd backend && uv run python scripts/build_graph.py
"""

import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR.parent.resolve()
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.utils.logging import setup_logging

setup_logging()
logger = logging.getLogger("build_graph")

SUBJECT_NAMES = {
    "ds": "数据结构",
    "os": "操作系统",
    "co": "计算机组成原理",
    "cn": "计算机网络",
}

# 算法关键词
ALGORITHM_KEYWORDS = [
    "算法", "排序", "查找", "搜索", "调度", "置换",
    "遍历", "哈希", "散列", "路由", "编码",
]

# 依赖关系匹配模式
DEPENDENCY_PATTERNS = [
    r"要理解(.{2,15}?)，需要先了解(.{2,15})",
    r"(.{2,15}?)的前提是(.{2,15})",
    r"在学习(.{2,15}?)之前，必须先掌握(.{2,15})",
    r"(.{2,15}?)是(.{2,15}?)的基础",
    r"(.{2,15}?)依赖于(.{2,15})",
]


def load_valid_chunks(chunks_dir: Path) -> list[dict]:
    """加载所有有效 chunks（过滤垃圾数据）"""
    all_chunks = []
    for json_file in sorted(chunks_dir.glob("*_chunks.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        for chunk in chunks:
            if chunk.get("subsection") is not None and "None" not in str(chunk.get("chunk_id", "")):
                all_chunks.append(chunk)
    logger.info("加载有效 chunks: %d", len(all_chunks))
    return all_chunks


def is_algorithm_node(title: str) -> bool:
    """判断是否为算法节点"""
    for kw in ALGORITHM_KEYWORDS:
        if kw in title:
            return True
    return False


def extract_nodes(chunks: list[dict]) -> dict[str, dict]:
    """
    提取图谱节点。

    返回 {node_id: node_data} 字典。
    """
    nodes = {}

    # 1. 章节节点
    chapter_set = set()
    for chunk in chunks:
        subject = chunk.get("subject_code", "")
        ch_num = chunk.get("chapter_number", "")
        ch_title = chunk.get("chapter_title", "")
        if ch_num and ch_title:
            key = (subject, ch_num, ch_title)
            if key not in chapter_set:
                chapter_set.add(key)
                node_id = f"{subject}_ch{ch_num}"
                nodes[node_id] = {
                    "id": node_id,
                    "type": "chapter",
                    "label": f"第{ch_num}章 {ch_title}",
                    "subject_code": subject,
                    "chapter": ch_num,
                    "chunk_id": None,
                }

    # 2. 概念/算法节点
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", "")
        subsection = chunk.get("subsection", "")
        title = chunk.get("subsection_title", "")
        subject = chunk.get("subject_code", "")
        chapter = chunk.get("chapter_number", "")

        if not subsection or not title:
            continue

        # 过滤习题/答案/目录等节点
        skip_keywords = ["习题精选", "试题精选", "答案与解析", "参考答案", "目录"]
        if any(kw in title for kw in skip_keywords):
            continue

        node_id = chunk_id
        node_type = "algorithm" if is_algorithm_node(title) else "concept"

        nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "label": title,
            "subject_code": subject,
            "chapter": chapter,
            "chunk_id": chunk_id,
        }

    logger.info(
        "节点提取完成: total=%d (chapter=%d, concept=%d, algorithm=%d)",
        len(nodes),
        sum(1 for n in nodes.values() if n["type"] == "chapter"),
        sum(1 for n in nodes.values() if n["type"] == "concept"),
        sum(1 for n in nodes.values() if n["type"] == "algorithm"),
    )
    return nodes


def extract_edges(chunks: list[dict], nodes: dict[str, dict]) -> list[dict]:
    """
    提取图谱边。

    三种关系:
    1. 属于: 概念/算法 → 章节
    2. 相关: 同 section 下的概念
    3. 依赖: 文本中的先修关系
    """
    edges = []
    edge_set = set()  # 去重

    def add_edge(source: str, target: str, relation: str, weight: float):
        if source == target:
            return
        key = (source, target, relation)
        if key not in edge_set:
            edge_set.add(key)
            edges.append({
                "source": source,
                "target": target,
                "relation": relation,
                "weight": round(weight, 2),
            })

    # 1. 属于关系
    for node_id, node in nodes.items():
        if node["type"] in ("concept", "algorithm"):
            chapter_node_id = f"{node['subject_code']}_ch{node['chapter']}"
            if chapter_node_id in nodes:
                add_edge(node_id, chapter_node_id, "属于", 1.0)

    logger.info("属于边: %d", len(edges))
    belongs_count = len(edges)

    # 2. 相关关系（同 section 下的概念）
    section_groups = defaultdict(list)
    for chunk in chunks:
        section = chunk.get("section_number", "")
        subject = chunk.get("subject_code", "")
        chunk_id = chunk.get("chunk_id", "")
        if section and chunk_id in nodes:
            section_groups[(subject, section)].append(chunk_id)

    for (subject, section), node_ids in section_groups.items():
        for i, n1 in enumerate(node_ids):
            for n2 in node_ids[i + 1:]:
                if nodes.get(n1, {}).get("type") != "chapter" and nodes.get(n2, {}).get("type") != "chapter":
                    add_edge(n1, n2, "相关", 0.6)

    related_count = len(edges) - belongs_count
    logger.info("相关边: %d", related_count)

    # 3. 依赖关系（文本模式匹配）
    # 构建 title → node_id 映射
    title_to_id = {}
    for node_id, node in nodes.items():
        if node["type"] != "chapter":
            title_to_id[node["label"]] = node_id

    dep_count = 0
    for chunk in chunks:
        content = chunk.get("content", "")
        for pattern in DEPENDENCY_PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                concept_a = match[0].strip()
                concept_b = match[1].strip()

                # 尝试匹配节点
                id_a = title_to_id.get(concept_a)
                id_b = title_to_id.get(concept_b)

                if not id_a:
                    for title, nid in title_to_id.items():
                        if concept_a in title:
                            id_a = nid
                            break
                if not id_b:
                    for title, nid in title_to_id.items():
                        if concept_b in title:
                            id_b = nid
                            break

                if id_a and id_b:
                    add_edge(id_a, id_b, "依赖", 0.8)
                    dep_count += 1

    logger.info("依赖边: %d (从文本中提取)", dep_count)
    logger.info("总边数: %d", len(edges))

    return edges


def main():
    logger.info("=" * 60)
    logger.info("开始知识图谱构建")
    logger.info("=" * 60)

    settings = get_settings()
    chunks_dir = settings.data.abs_chunks_dir

    # 加载数据
    chunks = load_valid_chunks(chunks_dir)
    if not chunks:
        logger.error("无有效数据")
        sys.exit(1)

    # 提取节点
    nodes = extract_nodes(chunks)

    # 提取边
    edges = extract_edges(chunks, nodes)

    # 构建输出
    graph_data = {
        "nodes": list(nodes.values()),
        "edges": edges,
    }

    # 保存
    output_path = settings.graph.abs_graph_json_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, ensure_ascii=False, indent=2)

    logger.info("知识图谱已保存到 %s", output_path)
    logger.info("节点数: %d, 边数: %d", len(graph_data["nodes"]), len(graph_data["edges"]))
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
