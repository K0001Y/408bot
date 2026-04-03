"""
Agent 主类

Skills 注册表 + 任务调度。统一管理所有 Skill 实例。
"""

from typing import Any

from app.utils.logging import get_logger
from app.utils.exceptions import AppError

logger = get_logger("agent")


class Agent:
    """
    408 考研辅助 Agent。
    根据任务类型灵活调用 Skills。
    """

    def __init__(self):
        self.skills: dict[str, Any] = {}
        logger.info("Agent 初始化")

    def register_skill(self, skill: Any) -> None:
        """注册一个 Skill"""
        self.skills[skill.name] = skill
        logger.info("注册 Skill: %s (%s)", skill.name, skill.description)

    def execute(self, task_type: str, params: dict) -> Any:
        """
        根据任务类型调用对应 Skill。

        Args:
            task_type: Skill 名称
            params: Skill 参数

        Returns:
            Skill 执行结果

        Raises:
            AppError: 未知任务类型或执行失败
        """
        skill = self.skills.get(task_type)
        if not skill:
            available = list(self.skills.keys())
            logger.error("未知任务类型 task_type=%s available=%s", task_type, available)
            raise AppError(
                code=4001,
                message=f"未知任务类型: {task_type}",
                detail=f"可用类型: {available}",
            )

        logger.info("Agent 调度 task_type=%s", task_type)
        return skill.execute(params)

    @property
    def available_skills(self) -> list[str]:
        """返回所有已注册的 Skill 名称"""
        return list(self.skills.keys())
