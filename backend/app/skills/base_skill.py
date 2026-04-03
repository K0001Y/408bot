"""
Skill 基类

所有 Skills 继承此基类，提供统一的接口和日志/错误处理模式。
"""

import time
from abc import ABC, abstractmethod
from typing import Any

from app.utils.logging import get_logger


class BaseSkill(ABC):
    """
    Skill 抽象基类。

    子类需实现:
    - name: Skill 名称标识
    - description: Skill 功能描述
    - _execute_impl(params): 具体执行逻辑
    """

    name: str = "base_skill"
    description: str = ""

    def __init__(self):
        self.logger = get_logger(f"skill.{self.name}")

    def execute(self, params: dict) -> dict:
        """
        执行 Skill（带日志和错误处理包装）。

        记录入口参数摘要、出口结果摘要和耗时。
        异常时记录完整 traceback。

        Args:
            params: Skill 参数字典

        Returns:
            执行结果字典

        Raises:
            AppError: 业务异常
        """
        # 参数摘要（截断过长的值）
        param_summary = self._summarize_params(params)
        self.logger.info("执行开始 params=%s", param_summary)
        t0 = time.time()

        try:
            result = self._execute_impl(params)
            elapsed = time.time() - t0
            result_summary = self._summarize_result(result)
            self.logger.info("执行完成 elapsed=%.3fs result=%s", elapsed, result_summary)
            return result
        except Exception as e:
            elapsed = time.time() - t0
            self.logger.error(
                "执行失败 elapsed=%.3fs error=%s params=%s",
                elapsed, str(e), param_summary, exc_info=True,
            )
            raise

    @abstractmethod
    def _execute_impl(self, params: dict) -> dict:
        """子类实现的具体执行逻辑"""
        ...

    def _summarize_params(self, params: dict) -> str:
        """生成参数摘要（截断长值）"""
        items = []
        for k, v in params.items():
            sv = str(v)
            if len(sv) > 80:
                sv = sv[:77] + "..."
            items.append(f"{k}={sv}")
        return "{" + ", ".join(items) + "}"

    def _summarize_result(self, result: Any) -> str:
        """生成结果摘要"""
        if isinstance(result, dict):
            items = []
            for k, v in result.items():
                if isinstance(v, list):
                    items.append(f"{k}=[{len(v)} items]")
                elif isinstance(v, str) and len(v) > 80:
                    items.append(f"{k}='{v[:77]}...'")
                else:
                    sv = str(v)
                    if len(sv) > 80:
                        sv = sv[:77] + "..."
                    items.append(f"{k}={sv}")
            return "{" + ", ".join(items) + "}"
        return str(result)[:200]
