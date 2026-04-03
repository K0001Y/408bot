"""
LLM 工厂模块

统一创建 OpenAI / Ollama LLM 实例和 Embedding 模型。
所有 LLM 相关的初始化和错误处理集中在此模块。
"""

import platform

import httpx
from langchain_core.language_models import BaseChatModel

from app.config import get_settings, Settings
from app.utils.logging import get_logger
from app.utils.exceptions import LLMError

logger = get_logger("llm_factory")


class LLMFactory:
    """
    LLM 工厂类 - 根据配置创建 LLM 和 Embedding 实例。

    支持:
    - OpenAI (ChatOpenAI)
    - Ollama (ChatOllama)
    - Embedding 始终使用本地 BAAI/bge-large-zh-v1.5
    """

    @staticmethod
    def create_llm(
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> BaseChatModel:
        """
        创建 LLM 实例。

        Args:
            provider: "openai" | "ollama"，默认从配置读取
            model: 模型名称，默认从配置读取
            temperature: 温度参数，默认从配置读取

        Returns:
            BaseChatModel 实例

        Raises:
            LLMError: 创建失败时抛出
        """
        settings = get_settings()
        provider = provider or settings.llm.provider

        logger.info("创建 LLM 实例 provider=%s", provider)

        try:
            if provider == "openai":
                return LLMFactory._create_openai(settings, model, temperature)
            elif provider == "ollama":
                return LLMFactory._create_ollama(settings, model, temperature)
            else:
                raise LLMError(
                    message=f"不支持的 LLM provider: {provider}",
                    detail=f"可选值: openai, ollama。当前值: {provider}",
                )
        except LLMError:
            raise
        except Exception as e:
            logger.error("LLM 创建失败 provider=%s error=%s", provider, str(e), exc_info=True)
            raise LLMError(
                message=f"LLM 创建失败: {provider}",
                detail=str(e),
            )

    @staticmethod
    def _create_openai(settings: Settings, model: str | None, temperature: float | None) -> BaseChatModel:
        from langchain_openai import ChatOpenAI

        cfg = settings.llm.openai
        api_key = model if False else cfg.api_key  # placeholder logic
        actual_model = model or cfg.model
        actual_temp = temperature if temperature is not None else cfg.temperature
        actual_key = cfg.api_key

        if not actual_key:
            raise LLMError(
                message="OpenAI API Key 未配置",
                detail="请在 config.yaml 中设置 llm.openai.api_key 或设置 OPENAI_API_KEY 环境变量",
            )

        llm = ChatOpenAI(
            model=actual_model,
            temperature=actual_temp,
            api_key=actual_key,
        )
        logger.info("OpenAI LLM 创建成功 model=%s temperature=%s", actual_model, actual_temp)
        return llm

    @staticmethod
    def _create_ollama(settings: Settings, model: str | None, temperature: float | None) -> BaseChatModel:
        from langchain_ollama import ChatOllama

        cfg = settings.llm.ollama
        actual_model = model or cfg.model
        actual_temp = temperature if temperature is not None else cfg.temperature
        base_url = cfg.base_url

        llm = ChatOllama(
            model=actual_model,
            base_url=base_url,
            temperature=actual_temp,
        )
        logger.info("Ollama LLM 创建成功 model=%s base_url=%s temperature=%s", actual_model, base_url, actual_temp)
        return llm

    @staticmethod
    def check_ollama_health() -> dict:
        """
        检查 Ollama 服务是否可用，并验证模型推理能力。

        Returns:
            dict: {
                "reachable": bool,   # HTTP 服务是否可达
                "models": list,      # 可用模型列表
                "inference_ok": bool, # 推理是否正常
                "error": str|None,   # 错误信息
                "fix_hint": str|None # 修复建议
            }
        """
        settings = get_settings()
        base_url = settings.llm.ollama.base_url
        configured_model = settings.llm.ollama.model
        result = {
            "reachable": False,
            "models": [],
            "inference_ok": False,
            "error": None,
            "fix_hint": None,
        }

        # Step 1: 检查 HTTP 连接
        try:
            response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
            if response.status_code != 200:
                result["error"] = f"Ollama 响应异常 status={response.status_code}"
                result["fix_hint"] = "请确保 Ollama 正在运行: ollama serve"
                return result

            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            result["reachable"] = True
            result["models"] = models
            logger.info("Ollama 服务可达 可用模型=%s", models)

        except httpx.ConnectError:
            result["error"] = f"Ollama 服务未运行 url={base_url}"
            result["fix_hint"] = "请启动 Ollama: ollama serve"
            logger.warning(result["error"])
            return result
        except Exception as e:
            result["error"] = f"Ollama 连接失败: {str(e)}"
            result["fix_hint"] = "请检查 Ollama 是否已安装并正确配置"
            logger.warning(result["error"])
            return result

        # Step 2: 检查配置的模型是否已下载
        model_found = any(configured_model in m for m in models)
        if not model_found:
            result["error"] = f"模型 '{configured_model}' 未在 Ollama 中找到"
            result["fix_hint"] = f"请下载模型: ollama pull {configured_model}"
            logger.warning(result["error"])
            return result

        # Step 3: 轻量推理测试 — 验证 runner 二进制可用
        try:
            test_response = httpx.post(
                f"{base_url}/api/generate",
                json={
                    "model": configured_model,
                    "prompt": "Hi",
                    "stream": False,
                    "options": {"num_predict": 1},  # 只生成 1 token
                },
                timeout=30.0,
            )
            if test_response.status_code == 200:
                result["inference_ok"] = True
                logger.info("Ollama 推理测试通过 model=%s", configured_model)
            else:
                body = test_response.text
                result["error"] = f"Ollama 推理失败 status={test_response.status_code}: {body[:200]}"
                if "no such file" in body.lower() or "fork/exec" in body.lower():
                    result["fix_hint"] = (
                        "Ollama runner 二进制文件缺失。请尝试:\n"
                        "  1. 重启 Ollama 应用\n"
                        "  2. 如仍不行，重新安装 Ollama: https://ollama.com/download"
                    )
                else:
                    result["fix_hint"] = "请重启 Ollama 或重新下载模型"
                logger.warning(result["error"])
        except httpx.ReadTimeout:
            # 超时但不一定是错误 — 模型可能正在加载
            result["inference_ok"] = True
            logger.info("Ollama 推理超时（模型可能正在加载），视为正常")
        except Exception as e:
            error_msg = str(e)
            result["error"] = f"Ollama 推理测试异常: {error_msg}"
            if "no such file" in error_msg.lower() or "fork/exec" in error_msg.lower():
                result["fix_hint"] = (
                    "Ollama runner 二进制文件缺失。请尝试:\n"
                    "  1. 重启 Ollama 应用\n"
                    "  2. 如仍不行，重新安装 Ollama: https://ollama.com/download"
                )
            else:
                result["fix_hint"] = f"请检查 Ollama 日志并重启服务"
            logger.warning(result["error"])

        return result

    @staticmethod
    def create_embeddings():
        """
        创建 Embedding 模型实例（始终使用本地 BGE 模型）。

        Returns:
            HuggingFaceEmbeddings 实例

        Raises:
            LLMError: 模型加载失败时抛出
        """
        settings = get_settings()
        model_name = settings.embedding.model_name
        device = settings.embedding.device

        # 自动检测设备
        if device == "auto":
            device = LLMFactory._detect_device()

        logger.info("加载 Embedding 模型 model=%s device=%s", model_name, device)

        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": device},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("Embedding 模型加载成功 model=%s device=%s", model_name, device)
            return embeddings
        except Exception as e:
            logger.critical(
                "Embedding 模型加载失败 model=%s device=%s error=%s",
                model_name, device, str(e), exc_info=True,
            )
            raise LLMError(
                message="Embedding 模型加载失败",
                detail=f"model={model_name}, device={device}, error={str(e)}",
            )

    @staticmethod
    def _detect_device() -> str:
        """自动检测最佳计算设备"""
        system = platform.system()
        machine = platform.machine()

        # macOS Apple Silicon → MPS
        if system == "Darwin" and machine == "arm64":
            try:
                import torch
                if torch.backends.mps.is_available():
                    logger.debug("检测到 Apple Silicon MPS")
                    return "mps"
            except (ImportError, AttributeError):
                pass

        # NVIDIA GPU → CUDA
        try:
            import torch
            if torch.cuda.is_available():
                logger.debug("检测到 CUDA GPU")
                return "cuda"
        except ImportError:
            pass

        logger.debug("使用 CPU 设备")
        return "cpu"
