"""
Chunk 数据导入脚本

功能:
1. 从 processed/*.json 加载 chunk 数据
2. 过滤垃圾 chunks（subsection 为 None 的前言/版权页等）
3. 修正 content_type 误分类（根据 subsection_title 关键词）
4. 构建搜索增强文本（prepend 上下文头）
5. 使用 BGE 模型编码并导入 ChromaDB

用法:
    cd backend && uv run python scripts/ingest_chunks.py
"""

import json
import logging
import os
import re
import sys
import time
from pathlib import Path

# 将 backend 目录加入 sys.path
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR.parent.resolve()
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings, BACKEND_DIR as APP_BACKEND_DIR
from app.utils.logging import setup_logging

setup_logging()
logger = logging.getLogger("ingest_chunks")

# ──────────── 科目名称映射 ────────────

SUBJECT_NAMES = {
    "ds": "数据结构",
    "os": "操作系统",
    "co": "计算机组成原理",
    "cn": "计算机网络",
}

# ──────────── Content Type 修正规则 ────────────

CONTENT_TYPE_RULES = [
    # (subsection_title 关键词列表, 修正后的 content_type)
    (["本节小结", "本章小结", "总结", "本章总结"], "summary"),
    (["习题精选", "试题精选", "本节习题", "本节试题", "练习题", "习题", "试题"], "exercise"),
    (["答案与解析", "参考答案", "答案", "解析"], "answer"),
]

# 代码检测模式
CODE_INDICATORS = [
    r"#include",
    r"int\s+main\s*\(",
    r"void\s+\w+\s*\(",
    r"struct\s+\w+\s*\{",
    r"typedef\s+",
    r"return\s+\d+;",
]


def reclassify_content_type(chunk: dict) -> str:
    """
    根据 subsection_title 和内容特征重新分类 content_type。

    修正策略:
    1. 优先匹配 subsection_title 关键词
    2. 其次检测代码特征
    3. 默认为 concept

    Args:
        chunk: 原始 chunk 数据

    Returns:
        修正后的 content_type
    """
    title = chunk.get("subsection_title", "") or ""

    # 按规则匹配 subsection_title
    for keywords, ctype in CONTENT_TYPE_RULES:
        for kw in keywords:
            if kw in title:
                return ctype

    # 检测代码内容
    content = chunk.get("content", "")
    if chunk.get("has_code", False):
        code_score = 0
        for pattern in CODE_INDICATORS:
            if re.search(pattern, content):
                code_score += 1
        if code_score >= 2:
            return "code"

    # 保留原始 table 分类（如果确实有表格结构）
    if chunk.get("has_table", False) and chunk.get("content_type") == "table":
        # 验证是否真的有表格特征（至少有对齐的列结构）
        lines = content.split("\n")
        table_lines = sum(1 for line in lines if "\t" in line or "  " in line.strip())
        if table_lines > 3:
            return "table"

    return "concept"


def build_search_text(chunk: dict) -> str:
    """
    构建搜索增强文本，在原始内容前添加结构化上下文头。

    格式:
    [科目: 操作系统 | 章: 第3章 内存管理 | 节: 3.2 虚拟内存 | 小节: 3.2.4 页面置换算法]
    {原始内容}

    Args:
        chunk: chunk 数据

    Returns:
        增强后的文本
    """
    parts = []

    subject_name = SUBJECT_NAMES.get(chunk.get("subject_code", ""), "")
    if subject_name:
        parts.append(f"科目: {subject_name}")

    chapter_num = chunk.get("chapter_number", "")
    chapter_title = chunk.get("chapter_title", "")
    if chapter_num and chapter_title:
        parts.append(f"章: 第{chapter_num}章 {chapter_title}")

    section_num = chunk.get("section_number", "")
    section_title = chunk.get("section_title", "")
    if section_num and section_title:
        parts.append(f"节: {section_num} {section_title}")

    subsection = chunk.get("subsection", "")
    subsection_title = chunk.get("subsection_title", "")
    if subsection and subsection_title:
        parts.append(f"小节: {subsection} {subsection_title}")

    header = "[" + " | ".join(parts) + "]" if parts else ""
    content = chunk.get("content", "")

    if header:
        return f"{header}\n{content}"
    return content


def is_valid_chunk(chunk: dict) -> bool:
    """
    检查 chunk 是否有效（应被导入）。

    过滤条件:
    - subsection 为 None（扉页、版权页等）
    - chunk_id 含 'None'
    - 内容过短（< 50 字符）

    Args:
        chunk: chunk 数据

    Returns:
        True 如果有效
    """
    if chunk.get("subsection") is None:
        return False

    chunk_id = chunk.get("chunk_id", "")
    if "None" in str(chunk_id):
        return False

    content = chunk.get("content", "")
    if len(content) < 50:
        return False

    return True


def load_chunks(chunks_dir: Path) -> list[dict]:
    """
    从 processed/ 目录加载所有 chunk 数据。

    Returns:
        (有效 chunks 列表, 统计信息)
    """
    all_chunks = []
    stats = {
        "total_loaded": 0,
        "total_filtered": 0,
        "total_valid": 0,
        "per_subject": {},
        "content_type_corrections": 0,
        "content_type_distribution": {},
    }

    json_files = sorted(chunks_dir.glob("*_chunks.json"))
    if not json_files:
        logger.error("未找到 chunk JSON 文件 dir=%s", chunks_dir)
        return [], stats

    for json_file in json_files:
        subject_code = json_file.stem.replace("_chunks", "")
        subject_name = SUBJECT_NAMES.get(subject_code, subject_code)

        logger.info("加载 %s (%s) ...", json_file.name, subject_name)

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                chunks = json.load(f)
        except Exception as e:
            logger.error("加载失败 file=%s error=%s", json_file, str(e), exc_info=True)
            continue

        loaded = len(chunks)
        valid_chunks = []

        for chunk in chunks:
            if not is_valid_chunk(chunk):
                stats["total_filtered"] += 1
                continue

            # 修正 content_type
            original_type = chunk.get("content_type", "")
            corrected_type = reclassify_content_type(chunk)
            if corrected_type != original_type:
                stats["content_type_corrections"] += 1
                logger.debug(
                    "content_type 修正 chunk_id=%s '%s' -> '%s' title='%s'",
                    chunk.get("chunk_id"), original_type, corrected_type,
                    chunk.get("subsection_title", ""),
                )
            chunk["content_type"] = corrected_type

            # 统计 content_type 分布
            ct = corrected_type
            stats["content_type_distribution"][ct] = stats["content_type_distribution"].get(ct, 0) + 1

            valid_chunks.append(chunk)

        filtered = loaded - len(valid_chunks)
        stats["total_loaded"] += loaded
        stats["total_valid"] += len(valid_chunks)
        stats["per_subject"][subject_code] = {
            "loaded": loaded,
            "valid": len(valid_chunks),
            "filtered": filtered,
        }

        logger.info(
            "  %s: 加载 %d, 有效 %d, 过滤 %d",
            subject_name, loaded, len(valid_chunks), filtered,
        )

        all_chunks.extend(valid_chunks)

    return all_chunks, stats


def ingest_to_chromadb(chunks: list[dict]) -> None:
    """
    将 chunks 导入 ChromaDB。

    步骤:
    1. 加载 SentenceTransformer 模型
    2. 构建搜索增强文本
    3. 编码为 embedding
    4. 批量写入 ChromaDB
    """
    settings = get_settings()

    # 加载 embedding 模型
    logger.info("加载 Embedding 模型...")
    t0 = time.time()
    from app.utils.embeddings import load_sentence_transformer, encode_documents, BGEEmbeddingFunction
    model = load_sentence_transformer()
    logger.info("Embedding 模型加载完成 elapsed=%.2fs", time.time() - t0)

    # 初始化 ChromaDB
    import chromadb

    persist_dir = str(settings.vector_db.abs_persist_directory)
    os.makedirs(persist_dir, exist_ok=True)

    client = chromadb.PersistentClient(path=persist_dir)
    collection_name = settings.vector_db.collection_name

    # 删除旧 collection（如果存在）
    try:
        client.delete_collection(collection_name)
        logger.info("已删除旧 collection '%s'", collection_name)
    except Exception:
        pass

    # 创建新 collection（使用 BGE embedding 函数）
    embedding_fn = BGEEmbeddingFunction(model=model)
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("创建 ChromaDB collection '%s'", collection_name)

    # 构建数据
    logger.info("构建搜索增强文本并编码...")
    t0 = time.time()

    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", "")
        search_text = build_search_text(chunk)

        ids.append(chunk_id)
        documents.append(search_text)
        metadatas.append({
            "chunk_id": chunk_id,
            "subject_code": chunk.get("subject_code", ""),
            "chapter_number": chunk.get("chapter_number", ""),
            "section_number": chunk.get("section_number", ""),
            "subsection": chunk.get("subsection", ""),
            "subsection_title": chunk.get("subsection_title", ""),
            "content_type": chunk.get("content_type", ""),
            "page_start": chunk.get("page_start", 0),
            "page_end": chunk.get("page_end", 0),
        })

    # 检查 ID 唯一性
    id_set = set()
    duplicates = []
    unique_ids = []
    unique_documents = []
    unique_metadatas = []

    for i, cid in enumerate(ids):
        if cid in id_set:
            duplicates.append(cid)
            # 添加索引后缀使其唯一
            new_id = f"{cid}_dup{len(duplicates)}"
            unique_ids.append(new_id)
            logger.warning("重复 chunk_id '%s' 已重命名为 '%s'", cid, new_id)
        else:
            unique_ids.append(cid)
        id_set.add(unique_ids[-1])
        unique_documents.append(documents[i])
        unique_metadatas.append(metadatas[i])

    if duplicates:
        logger.warning("发现 %d 个重复 chunk_id", len(duplicates))

    # 批量导入
    batch_size = 50
    total = len(unique_ids)

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch_ids = unique_ids[start:end]
        batch_docs = unique_documents[start:end]
        batch_meta = unique_metadatas[start:end]

        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_meta,
        )

        progress = end / total * 100
        logger.info("导入进度: %d/%d (%.1f%%)", end, total, progress)

    elapsed = time.time() - t0
    logger.info("ChromaDB 导入完成 total=%d elapsed=%.2fs", total, elapsed)


def verify_ingestion() -> None:
    """
    验证导入结果：运行示例查询，检查 top-5 结果。
    """
    settings = get_settings()
    import chromadb
    from app.utils.embeddings import load_sentence_transformer, encode_query, BGEEmbeddingFunction

    client = chromadb.PersistentClient(path=str(settings.vector_db.abs_persist_directory))
    model = load_sentence_transformer()
    embedding_fn = BGEEmbeddingFunction(model=model)

    collection = client.get_collection(
        name=settings.vector_db.collection_name,
        embedding_function=embedding_fn,
    )

    total = collection.count()
    logger.info("验证: collection 文档总数 = %d", total)

    # 示例查询
    test_queries = [
        ("虚拟内存页面置换算法", "os"),
        ("二叉树遍历", "ds"),
        ("TCP三次握手", "cn"),
    ]

    for query, expected_subject in test_queries:
        query_embedding = encode_query(model, query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
        )

        logger.info("查询: '%s'", query)
        if results["ids"] and results["ids"][0]:
            for i, (doc_id, meta) in enumerate(zip(results["ids"][0], results["metadatas"][0])):
                distance = results["distances"][0][i] if results.get("distances") else "N/A"
                logger.info(
                    "  #%d id=%s subject=%s title='%s' distance=%s",
                    i + 1, doc_id, meta.get("subject_code"),
                    meta.get("subsection_title", ""), distance,
                )
        else:
            logger.warning("  无结果!")

    logger.info("验证完成")


def save_stats(stats: dict) -> None:
    """保存导入统计到 JSON 文件"""
    settings = get_settings()
    stats_path = settings.vector_db.abs_persist_directory.parent / "ingestion_stats.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)

    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    logger.info("统计数据已保存到 %s", stats_path)


def main():
    """主入口"""
    logger.info("=" * 60)
    logger.info("开始 Chunk 数据导入")
    logger.info("=" * 60)

    settings = get_settings()
    chunks_dir = settings.data.abs_chunks_dir

    logger.info("数据源目录: %s", chunks_dir)

    if not chunks_dir.exists():
        logger.error("数据目录不存在: %s", chunks_dir)
        sys.exit(1)

    # 1. 加载并清洗数据
    t_total = time.time()
    chunks, stats = load_chunks(chunks_dir)

    if not chunks:
        logger.error("没有有效的 chunk 数据，退出")
        sys.exit(1)

    logger.info(
        "数据加载汇总: 总加载=%d, 有效=%d, 过滤=%d, content_type修正=%d",
        stats["total_loaded"], stats["total_valid"],
        stats["total_filtered"], stats["content_type_corrections"],
    )
    logger.info("content_type 分布: %s", stats["content_type_distribution"])

    # 2. 导入 ChromaDB
    ingest_to_chromadb(chunks)

    # 3. 验证
    verify_ingestion()

    # 4. 保存统计
    total_elapsed = time.time() - t_total
    stats["total_elapsed_seconds"] = round(total_elapsed, 2)
    save_stats(stats)

    logger.info("=" * 60)
    logger.info("导入完成! 总耗时: %.2fs", total_elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
