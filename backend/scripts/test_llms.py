"""
LLM 综合测试脚本

测试范围：
  1. rag_llm  (Ollama deepseek-r1:8b)   —— 直接调用 + AgenticRAGSkill 链路
  2. answer_llm (OpenAI-compat qwen3-max) —— 直接调用 + AnswerGenerationSkill / QuizGenerationSkill 链路

运行方式（在 backend 目录下）：
    uv run python scripts/test_llms.py
"""

import sys
import time
import textwrap
from pathlib import Path

# 确保能 import app 包
BACKEND_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BACKEND_DIR))

from langchain_core.messages import HumanMessage

# ──────────── 颜色输出 ────────────

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}✔ PASS{RESET}  {msg}")
def fail(msg):  print(f"  {RED}✘ FAIL{RESET}  {msg}")
def info(msg):  print(f"  {CYAN}ℹ{RESET}  {msg}")
def warn(msg):  print(f"  {YELLOW}⚠ WARN{RESET}  {msg}")
def header(msg): print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}\n{BOLD}{msg}{RESET}")


# ──────────── 结果统计 ────────────

results = {"pass": 0, "fail": 0, "skip": 0}

def record(passed: bool, skip=False):
    if skip:
        results["skip"] += 1
    elif passed:
        results["pass"] += 1
    else:
        results["fail"] += 1


# ──────────── Mock 检索 Skill ────────────

class MockRetrievalSkill:
    """
    最小化的假检索 Skill，仅用于测试 LLM 链路，
    返回固定的计算机网络知识片段。
    """
    def execute(self, params: dict) -> dict:
        return {
            "results": [
                {
                    "subsection": "3.1",
                    "subsection_title": "数据链路层概述",
                    "preview": (
                        "数据链路层的主要功能是在相邻节点之间可靠地传输数据帧。"
                        "它将物理层提供的比特流封装成帧，并通过差错检测（CRC 校验）"
                        "和流量控制（滑动窗口协议）保证传输的可靠性。"
                        "常见的数据链路层协议有 PPP、HDLC、Ethernet 等。"
                    ),
                },
                {
                    "subsection": "3.2",
                    "subsection_title": "停止等待协议",
                    "preview": (
                        "停止等待协议（Stop-and-Wait）是最简单的流量控制协议。"
                        "发送方发送一帧后，必须等待接收方的确认（ACK）才能发送下一帧。"
                        "信道利用率 = T_data / (T_data + RTT + T_ack)。"
                    ),
                },
            ]
        }


# ──────────── 测试函数 ────────────

def test_llm_direct(role: str, llm, label: str):
    """直接向 LLM 发送一条简单消息，验证连通性与基本推理。"""
    header(f"[{label}] 直连测试 — role={role}")
    prompt = "用一句话介绍计算机网络中的「三次握手」。不需要思考过程，只给结论。"
    info(f"Prompt: {prompt}")
    try:
        t0 = time.time()
        resp = llm.invoke([HumanMessage(content=prompt)])
        elapsed = time.time() - t0
        answer = resp.content.strip()
        # 过滤掉 deepseek-r1 的 <think> 块
        if "<think>" in answer:
            start = answer.find("</think>")
            answer = answer[start + len("</think>"):].strip() if start != -1 else answer
        preview = textwrap.shorten(answer, width=120, placeholder="…")
        ok(f"响应成功 ({elapsed:.1f}s): {preview}")
        record(True)
    except Exception as e:
        fail(f"调用失败: {e}")
        record(False)


def test_answer_generation_skill(llm):
    """测试 AnswerGenerationSkill 的 LLM 链路（使用 Mock 检索）。"""
    header("[AnswerGenerationSkill] 标准 RAG 问答链路测试")
    from app.skills.answer_generation_skill import AnswerGenerationSkill

    retrieval = MockRetrievalSkill()
    skill = AnswerGenerationSkill(retrieval, llm)
    info("问题: 请解释数据链路层的主要功能。")
    try:
        t0 = time.time()
        result = skill.execute({"query": "请解释数据链路层的主要功能", "top_k": 2})
        elapsed = time.time() - t0
        answer = result.get("answer", "")
        preview = textwrap.shorten(answer, width=150, placeholder="…")
        ok(f"回答生成成功 ({elapsed:.1f}s): {preview}")
        record(True)
    except Exception as e:
        fail(f"AnswerGenerationSkill 执行失败: {e}")
        record(False)


def test_quiz_generation_skill(llm):
    """测试 QuizGenerationSkill 的 LLM 链路（使用 Mock 检索）。"""
    header("[QuizGenerationSkill] 出题链路测试")
    from app.skills.quiz_generation_skill import QuizGenerationSkill

    retrieval = MockRetrievalSkill()
    skill = QuizGenerationSkill(retrieval, llm)
    info("出题: 数据链路层，选择题×1，简单难度。")
    try:
        t0 = time.time()
        result = skill.execute({
            "topic": "数据链路层",
            "quiz_type": "choice",
            "count": 1,
            "difficulty": "easy",
            "top_k": 2,
        })
        elapsed = time.time() - t0
        content = result.get("quiz_content", "")
        preview = textwrap.shorten(content, width=150, placeholder="…")
        ok(f"出题成功 ({elapsed:.1f}s): {preview}")
        record(True)
    except Exception as e:
        fail(f"QuizGenerationSkill 执行失败: {e}")
        record(False)


def test_agentic_rag_skill(llm):
    """测试 AgenticRAGSkill 的 ReAct Agent 链路（使用 Mock 检索）。"""
    header("[AgenticRAGSkill] Agentic RAG ReAct 链路测试")
    from app.skills.agentic_rag_skill import AgenticRAGSkill

    retrieval = MockRetrievalSkill()
    skill = AgenticRAGSkill(retrieval, llm)
    info("问题: 停止等待协议的信道利用率如何计算？")
    try:
        t0 = time.time()
        result = skill.execute({"query": "停止等待协议的信道利用率如何计算？"})
        elapsed = time.time() - t0
        answer = result.get("answer", "")
        steps = result.get("intermediate_steps", [])
        preview = textwrap.shorten(answer, width=150, placeholder="…")
        ok(f"Agentic RAG 成功 ({elapsed:.1f}s), 中间步骤数={len(steps)}: {preview}")
        record(True)
    except Exception as e:
        fail(f"AgenticRAGSkill 执行失败: {e}")
        record(False)


# ──────────── 主入口 ────────────

def main():
    print(f"\n{BOLD}{'='*60}")
    print("  408bot LLM 综合测试")
    print(f"{'='*60}{RESET}")

    # ── 加载配置 ──
    from app.config import get_settings
    from app.llm_factory import LLMFactory

    settings = get_settings()
    info(f"默认 LLM provider : {settings.llm.provider} / {settings.llm.ollama.model if settings.llm.provider=='ollama' else settings.llm.openai.model}")
    if settings.rag_llm:
        info(f"rag_llm provider  : {settings.rag_llm.provider} / {settings.rag_llm.ollama.model if settings.rag_llm.provider=='ollama' else settings.rag_llm.openai.model}")
    if settings.answer_llm:
        info(f"answer_llm provider: {settings.answer_llm.provider} / {settings.answer_llm.ollama.model if settings.answer_llm.provider=='ollama' else settings.answer_llm.openai.model}")

    # ── 创建两个 LLM 实例 ──
    print(f"\n{BOLD}▶ 初始化 LLM 实例…{RESET}")
    try:
        rag_llm = LLMFactory.create_llm_for_role("rag")
        ok("rag_llm 实例创建成功")
        record(True)
    except Exception as e:
        fail(f"rag_llm 创建失败: {e}")
        record(False)
        rag_llm = None

    try:
        answer_llm = LLMFactory.create_llm_for_role("answer")
        ok("answer_llm 实例创建成功")
        record(True)
    except Exception as e:
        fail(f"answer_llm 创建失败: {e}")
        record(False)
        answer_llm = None

    # ────────────────────────────────
    # 第一部分：直连测试
    # ────────────────────────────────
    if rag_llm:
        test_llm_direct("rag", rag_llm, "rag_llm · Ollama")
    else:
        warn("rag_llm 不可用，跳过直连测试")
        record(False, skip=True)

    if answer_llm:
        test_llm_direct("answer", answer_llm, "answer_llm · OpenAI-compat")
    else:
        warn("answer_llm 不可用，跳过直连测试")
        record(False, skip=True)

    # ────────────────────────────────
    # 第二部分：Skill 链路测试
    # ────────────────────────────────
    # AnswerGenerationSkill & QuizGenerationSkill 使用 answer_llm
    if answer_llm:
        test_answer_generation_skill(answer_llm)
        test_quiz_generation_skill(answer_llm)
    else:
        warn("answer_llm 不可用，跳过 AnswerGenerationSkill / QuizGenerationSkill 测试")
        record(False, skip=True)
        record(False, skip=True)

    # AgenticRAGSkill 使用 rag_llm
    if rag_llm:
        test_agentic_rag_skill(rag_llm)
    else:
        warn("rag_llm 不可用，跳过 AgenticRAGSkill 测试")
        record(False, skip=True)

    # ────────────────────────────────
    # 汇总
    # ────────────────────────────────
    total = results["pass"] + results["fail"] + results["skip"]
    print(f"\n{BOLD}{'='*60}")
    print(f"  测试完成  PASS={GREEN}{results['pass']}{RESET}{BOLD}  "
          f"FAIL={RED}{results['fail']}{RESET}{BOLD}  "
          f"SKIP={YELLOW}{results['skip']}{RESET}{BOLD}  (共 {total} 项)")
    print(f"{'='*60}{RESET}\n")

    sys.exit(0 if results["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
