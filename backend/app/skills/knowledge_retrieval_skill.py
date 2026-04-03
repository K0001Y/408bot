"""
KnowledgeRetrievalSkill - 知识检索

从 ChromaDB 向量数据库检索相关知识。
支持按科目、章节、内容类型过滤。
"""

from typing import Any

from app.skills.base_skill import BaseSkill
from app.utils.exceptions import VectorSearchError
from app.utils.embeddings import encode_query


class KnowledgeRetrievalSkill(BaseSkill):
    name = "knowledge_retrieval"
    description = "从向量数据库检索相关知识"

    def __init__(self, collection: Any, embedding_model: Any):
        """
        Args:
            collection: ChromaDB collection 实例
            embedding_model: SentenceTransformer 模型实例
        """
        super().__init__()
        self.collection = collection
        self.embedding_model = embedding_model

    def _execute_impl(self, params: dict) -> dict:
        """
        执行知识检索。

        Args:
            params: {
                "query": str - 搜索关键词,
                "subject": str|None - 科目代码 ds/os/co/cn,
                "chapter": str|None - 章节号,
                "content_type": str|None - 内容类型,
                "top_k": int - 返回数量 (默认 10)
            }

        Returns:
            {"results": [...], "total": int}
        """
        query = params.get("query", "")
        if not query:
            return {"results": [], "total": 0}

        subject = params.get("subject")
        chapter = params.get("chapter")
        content_type = params.get("content_type")
        top_k = params.get("top_k", 10)

        # 构建 ChromaDB where 子句
        where_clause = self._build_where_clause(subject, chapter, content_type)

        try:
            # 使用 BGE 查询前缀编码查询
            query_embedding = encode_query(self.embedding_model, query)

            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if where_clause:
                query_params["where"] = where_clause

            self.logger.debug(
                "ChromaDB 查询 query='%s' where=%s top_k=%d",
                query[:50], where_clause, top_k,
            )

            results = self.collection.query(**query_params)

        except Exception as e:
            self.logger.error("ChromaDB 查询失败 error=%s", str(e), exc_info=True)
            raise VectorSearchError(
                message="向量检索失败",
                detail=f"query='{query}', error={str(e)}",
            )

        # 格式化结果
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                doc = results["documents"][0][i] if results["documents"] else ""
                distance = results["distances"][0][i] if results.get("distances") else 0.0

                # 从增强文本中提取原始内容（去掉上下文头）
                content = doc
                if content.startswith("["):
                    newline_idx = content.find("\n")
                    if newline_idx != -1:
                        content = content[newline_idx + 1:]

                formatted.append({
                    "chunk_id": meta.get("chunk_id", doc_id),
                    "subsection": meta.get("subsection", ""),
                    "subsection_title": meta.get("subsection_title", ""),
                    "subject_code": meta.get("subject_code", ""),
                    "chapter_number": meta.get("chapter_number", ""),
                    "content_type": meta.get("content_type", ""),
                    "preview": content[:200] + "..." if len(content) > 200 else content,
                    "score": round(1.0 - distance, 4) if distance else 0.0,
                })

        self.logger.debug("检索返回 %d 条结果", len(formatted))
        return {"results": formatted, "total": len(formatted)}

    def get_chunk_detail(self, chunk_id: str) -> dict | None:
        """
        按 ID 获取 chunk 完整内容。

        Args:
            chunk_id: chunk 唯一标识

        Returns:
            chunk 详情字典，未找到返回 None
        """
        self.logger.debug("获取 chunk 详情 chunk_id=%s", chunk_id)

        try:
            results = self.collection.get(
                ids=[chunk_id],
                include=["documents", "metadatas"],
            )
        except Exception as e:
            self.logger.error("chunk 查询失败 chunk_id=%s error=%s", chunk_id, str(e))
            raise VectorSearchError(
                message=f"获取 chunk 详情失败: {chunk_id}",
                detail=str(e),
            )

        if not results["ids"]:
            self.logger.warning("chunk 不存在 chunk_id=%s", chunk_id)
            return None

        doc = results["documents"][0] if results["documents"] else ""
        meta = results["metadatas"][0] if results["metadatas"] else {}

        # 提取原始内容
        content = doc
        if content.startswith("["):
            newline_idx = content.find("\n")
            if newline_idx != -1:
                content = content[newline_idx + 1:]

        return {
            "chunk_id": chunk_id,
            "subject_code": meta.get("subject_code", ""),
            "chapter_number": meta.get("chapter_number", ""),
            "section_number": meta.get("section_number", ""),
            "subsection": meta.get("subsection", ""),
            "subsection_title": meta.get("subsection_title", ""),
            "content_type": meta.get("content_type", ""),
            "page_start": meta.get("page_start", 0),
            "page_end": meta.get("page_end", 0),
            "content": content,
        }

    def _build_where_clause(
        self,
        subject: str | None,
        chapter: str | None,
        content_type: str | None,
    ) -> dict | None:
        """
        构建 ChromaDB where 过滤子句。

        ChromaDB 多条件需使用 $and 运算符。
        """
        conditions = []

        if subject:
            conditions.append({"subject_code": {"$eq": subject}})
        if chapter:
            conditions.append({"chapter_number": {"$eq": chapter}})
        if content_type:
            conditions.append({"content_type": {"$eq": content_type}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}
