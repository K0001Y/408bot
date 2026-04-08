"""
应用配置模块

通过 Pydantic Settings 加载 config.yaml + 环境变量，
提供全局单例配置对象。
"""

import os
from pathlib import Path
from functools import lru_cache
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


# 后端根目录
BACKEND_DIR = Path(__file__).parent.parent.resolve()


class OpenAIConfig(BaseModel):
    model: str = "gpt-4"
    api_key: str = ""
    base_url: str | None = None   # OpenAI 兼容接口地址，如 dashscope/deepseek 等
    temperature: float = 0


class OllamaConfig(BaseModel):
    model: str = "qwen2.5:14b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0


class LLMConfig(BaseModel):
    provider: str = "ollama"
    openai: OpenAIConfig = OpenAIConfig()
    ollama: OllamaConfig = OllamaConfig()


class EmbeddingConfig(BaseModel):
    model_name: str = "BAAI/bge-large-zh-v1.5"
    device: str = "auto"


class VectorDBConfig(BaseModel):
    persist_directory: str = "./data/vector_db"
    collection_name: str = "408_knowledge"

    @property
    def abs_persist_directory(self) -> Path:
        return (BACKEND_DIR / self.persist_directory).resolve()


class GraphConfig(BaseModel):
    graph_json_path: str = "./data/graph/knowledge_graph.json"
    max_depth: int = 2

    @property
    def abs_graph_json_path(self) -> Path:
        return (BACKEND_DIR / self.graph_json_path).resolve()


class MistakesConfig(BaseModel):
    db_path: str = "./data/mistakes.db"

    @property
    def abs_db_path(self) -> Path:
        return (BACKEND_DIR / self.db_path).resolve()


class DataConfig(BaseModel):
    chunks_dir: str = "./data_process/processed"

    @property
    def abs_chunks_dir(self) -> Path:
        return (BACKEND_DIR / self.chunks_dir).resolve()


class LoggingConfig(BaseModel):
    level: str = "INFO"
    log_file: str = "./logs/app.log"
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 7

    @property
    def abs_log_file(self) -> Path:
        return (BACKEND_DIR / self.log_file).resolve()


class AppConfig(BaseModel):
    name: str = "408考研辅助Agent"
    version: str = "0.1.0"
    debug: bool = True
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


class Settings(BaseModel):
    """全局配置，从 config.yaml 加载"""

    app: AppConfig = AppConfig()
    llm: LLMConfig = LLMConfig()
    # 角色专属 LLM 覆盖（可选）。未配置时均 fallback 到 llm。
    rag_llm: LLMConfig | None = None     # Agentic RAG 专用
    answer_llm: LLMConfig | None = None  # 问答 / Quiz 专用
    embedding: EmbeddingConfig = EmbeddingConfig()
    vector_db: VectorDBConfig = VectorDBConfig()
    graph: GraphConfig = GraphConfig()
    mistakes: MistakesConfig = MistakesConfig()
    data: DataConfig = DataConfig()
    logging: LoggingConfig = LoggingConfig()


def _resolve_env_vars(value: str) -> str:
    """解析字符串中的 ${ENV_VAR} 占位符"""
    if isinstance(value, str) and "${" in value:
        import re
        pattern = r'\$\{(\w+)\}'
        def replacer(match):
            env_var = match.group(1)
            return os.environ.get(env_var, "")
        return re.sub(pattern, replacer, value)
    return value


def _resolve_env_in_dict(d: dict) -> dict:
    """递归解析字典中所有字符串的环境变量"""
    resolved = {}
    for key, value in d.items():
        if isinstance(value, dict):
            resolved[key] = _resolve_env_in_dict(value)
        elif isinstance(value, list):
            resolved[key] = [
                _resolve_env_vars(v) if isinstance(v, str) else v
                for v in value
            ]
        elif isinstance(value, str):
            resolved[key] = _resolve_env_vars(value)
        else:
            resolved[key] = value
    return resolved


@lru_cache()
def get_settings() -> Settings:
    """
    加载并返回全局配置单例。

    优先级: 环境变量 > config.yaml > 默认值
    """
    config_path = BACKEND_DIR / "config.yaml"

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}
        config_data = _resolve_env_in_dict(raw_config)
        return Settings(**config_data)

    return Settings()
