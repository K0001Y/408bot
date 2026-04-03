"""
QuestionLocationSkill - 习题定位

从 ChromaDB 中检索教材习题和答案。
利用 ingestion 阶段修正后的 content_type='exercise'/'answer' 进行过滤，
同时支持 subsection_title 关键词匹配作为补充。
"""

from typing import Any

from app.skills.base_skill import BaseSkill
from app.utils.exceptions import VectorSearchError, QuestionNotFoundError
from app.utils.embeddings import encode_query


# 习题相关的 subsection_title 关键词（兜底匹配）
EXERCISE_KEYWORDS = ["习题精选", "本节试题", "练习", "习题", "思考题", "自测题"]


class QuestionLocationSkill(BaseSkill):
    name = "question_location"
    description = "定位教材中的习题及答案"

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
        查找教材习题。

        Args:
            params: {
                "subject": str|None - 科目代码 ds/os/co/cn,
                "chapter": str|None - 章节号,
                "query": str|None - 搜索关键词（可选，用于语义检索）,
                "top_k": int - 返回数量 (默认 20),
                "include_answers": bool - 是否同时返回答案 (默认 True)
            }

        Returns:
            {"exercises": [...], "answers": [...], "total": int}
        """
        subject = params.get("subject")
        chapter = params.get("chapter")
        query = params.get("query")
        top_k = params.get("top_k", 20)
        include_answers = params.get("include_answers", True)

        self.logger.info(
            "习题检索 subject=%s chapter=%s query=%s top_k=%d",
            subject, chapter, query and query[:30], top_k,
        )

        exercises = []
        answers = []

        if query:
            # 语义检索模式: 结合 content_type 过滤 + 语义相似度
            exercises = self._search_by_query(query, subject, chapter, "exercise", top_k)
            if include_answers:
                answers = self._search_by_query(query, subject, chapter, "answer", top_k)
        else:
            # 直接过滤模式: 按 content_type + subject/chapter 获取
            exercises = self._get_by_type(subject, chapter, "exercise", top_k)
            if include_answers:
                answers = self._get_by_type(subject, chapter, "answer", top_k)

        self.logger.info(
            "习题检索完成 exercises=%d answers=%d",
            len(exercises), len(answers),
        )

        return {
            "exercises": exercises,
            "answers": answers,
            "total": len(exercises),
        }

    def get_exercise_detail(self, chunk_id: str) -> dict | None:
        """
        获取单条习题/答案的完整内容。

        Args:
            chunk_id: chunk 唯一标识

        Returns:
            习题详情字典，未找到返回 None
        """
        self.logger.debug("获取习题详情 chunk_id=%s", chunk_id)

        try:
            results = self.collection.get(
                ids=[chunk_id],
                include=["documents", "metadatas"],
            )
        except Exception as e:
            self.logger.error("习题查询失败 chunk_id=%s error=%s", chunk_id, str(e))
            raise VectorSearchError(
                message=f"获取习题详情失败: {chunk_id}",
                detail=str(e),
            )

        if not results["ids"]:
            self.logger.warning("习题不存在 chunk_id=%s", chunk_id)
            return None

        doc = results["documents"][0] if results["documents"] else ""
        meta = results["metadatas"][0] if results["metadatas"] else {}

        content = self._strip_context_header(doc)

        return {
            "chunk_id": chunk_id,
            "subject_code": meta.get("subject_code", ""),
            "chapter_number": meta.get("chapter_number", ""),
            "subsection": meta.get("subsection", ""),
            "subsection_title": meta.get("subsection_title", ""),
            "content_type": meta.get("content_type", ""),
            "page_start": meta.get("page_start", 0),
            "page_end": meta.get("page_end", 0),
            "content": content,
        }

    def _search_by_query(
        self,
        query: str,
        subject: str | None,
        chapter: str | None,
        content_type: str,
        top_k: int,
    ) -> list[dict]:
        """语义检索 + content_type 过滤"""
        where = self._build_where(subject, chapter, content_type)

        try:
            query_embedding = encode_query(self.embedding_model, query)

            query_params: dict = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                query_params["where"] = where

            results = self.collection.query(**query_params)
            return self._format_results(results)
        except Exception as e:
            self.logger.error(
                "语义习题检索失败 type=%s error=%s",
                content_type, str(e), exc_info=True,
            )
            raise VectorSearchError(
                message="习题检索失败",
                detail=f"content_type={content_type}, error={str(e)}",
            )

    def _get_by_type(
        self,
        subject: str | None,
        chapter: str | None,
        content_type: str,
        top_k: int,
    ) -> list[dict]:
        """直接按 metadata 过滤获取"""
        where = self._build_where(subject, chapter, content_type)
        if not where:
            # 至少需要 content_type 过滤
            where = {"content_type": {"$eq": content_type}}

        try:
            results = self.collection.get(
                where=where,
                limit=top_k,
                include=["documents", "metadatas"],
            )
            return self._format_get_results(results)
        except Exception as e:
            self.logger.error(
                "习题列表获取失败 type=%s error=%s",
                content_type, str(e), exc_info=True,
            )
            raise VectorSearchError(
                message="习题列表获取失败",
                detail=f"content_type={content_type}, error={str(e)}",
            )

    def _build_where(
        self,
        subject: str | None,
        chapter: str | None,
        content_type: str | None,
    ) -> dict | None:
        """构建 ChromaDB where 子句"""
        conditions = []

        if content_type:
            conditions.append({"content_type": {"$eq": content_type}})
        if subject:
            conditions.append({"subject_code": {"$eq": subject}})
        if chapter:
            conditions.append({"chapter_number": {"$eq": chapter}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _format_results(self, results: dict) -> list[dict]:
        """格式化 query() 结果"""
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                doc = results["documents"][0][i] if results["documents"] else ""
                distance = results["distances"][0][i] if results.get("distances") else 0.0

                content = self._strip_context_header(doc)

                formatted.append({
                    "chunk_id": meta.get("chunk_id", doc_id),
                    "subsection": meta.get("subsection", ""),
                    "subsection_title": meta.get("subsection_title", ""),
                    "subject_code": meta.get("subject_code", ""),
                    "chapter_number": meta.get("chapter_number", ""),
                    "content_type": meta.get("content_type", ""),
                    "content": content,
                    "preview": content[:300] + "..." if len(content) > 300 else content,
                    "score": round(1.0 - distance, 4) if distance else 0.0,
                })
        return formatted

    def _format_get_results(self, results: dict) -> list[dict]:
        """格式化 get() 结果"""
        formatted = []
        if results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                meta = results["metadatas"][i] if results.get("metadatas") else {}
                doc = results["documents"][i] if results.get("documents") else ""

                content = self._strip_context_header(doc)

                formatted.append({
                    "chunk_id": meta.get("chunk_id", doc_id),
                    "subsection": meta.get("subsection", ""),
                    "subsection_title": meta.get("subsection_title", ""),
                    "subject_code": meta.get("subject_code", ""),
                    "chapter_number": meta.get("chapter_number", ""),
                    "content_type": meta.get("content_type", ""),
                    "content": content,
                    "preview": content[:300] + "..." if len(content) > 300 else content,
                })
        return formatted

    @staticmethod
    def _strip_context_header(doc: str) -> str:
        """去掉 ingest 时添加的搜索增强上下文头"""
        if doc.startswith("["):
            newline_idx = doc.find("\n")
            if newline_idx != -1:
                return doc[newline_idx + 1:]
        return doc
