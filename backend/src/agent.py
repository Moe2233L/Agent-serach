from __future__ import annotations

import asyncio
import re
import uuid
from collections import OrderedDict

from backend.src.config import settings
from backend.src.models import (
    LogEntry,
    ResearchPhase,
    ResearchState,
    ResearchStatus,
    Subtask,
    SubtaskStatus,
)
from backend.src.services.search_tool import search_web
from backend.src.services.content_extractor import fetch_page_content
from backend.src.services.todo_planner import TODOPlanner
from backend.src.services.task_summarizer import TaskSummarizer
from backend.src.services.report_writer import ReportWriter
from backend.src.services.research_critic import ResearchCritic
from langchain_openai import ChatOpenAI


# 正则：匹配 Markdown 链接 [文字](URL) → 文字
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
# 最多保留的研究状态数（防止内存泄漏）
_MAX_STATES = 50


# 研究流程的核心编排器
# 包含三个阶段：规划 → 执行 → 报告
class ResearchAgent:
    def __init__(self):
        # 初始化 LLM 实例
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            request_timeout=settings.llm_timeout,
        )
        # 初始化各服务组件
        self.todo_planner = TODOPlanner(llm)          # 任务规划
        self.task_summarizer = TaskSummarizer(llm)     # 任务总结
        self.report_writer = ReportWriter(llm)         # 报告撰写
        self.research_critic = ResearchCritic(llm)     # 质量评审
        # 研究状态字典（有序，支持按 ID 查找）
        self.research_states: OrderedDict[str, ResearchState] = OrderedDict()

    # 按 research_id 查找研究状态
    def get_state(self, research_id: str) -> ResearchState | None:
        return self.research_states.get(research_id)

    # 入口：发起一次完整的研究，返回 SSE 事件流
    async def run(self, topic: str, max_results: int = 5, subtask_count: int = 3, deep_mode: bool = False):
        research_id = uuid.uuid4().hex[:12]
        state = ResearchState(research_id=research_id, topic=topic, deep_mode=deep_mode)

        try:
            # 依次执行三阶段
            async for event in self._execute(state, max_results, subtask_count):
                yield event
        except Exception as e:
            # 全局异常捕获，通过 SSE 推送错误
            state.status = ResearchStatus.error
            state.error = str(e)
            yield self._make_event("error", {"error": str(e)})

    # 追问入口：对已完成的研究进行追问，返回 SSE 事件流
    async def followup(self, research_id: str, question: str, max_results: int = 5):
        state = self.research_states.get(research_id)
        if not state:
            yield self._make_event("error", {"error": "研究不存在或已过期"})
            return

        if state.status != ResearchStatus.completed:
            yield self._make_event("error", {"error": "只能在研究完成后追问"})
            return

        state.phase = ResearchPhase.executing

        yield self._make_event("followup_start", {"question": question})
        yield self._make_event("log", {"phase": "executing", "message": f"搜索并回答: {question}"})

        # 对追问内容执行搜索（最多重试 2 次）
        search_results: list[dict] = []
        for attempt in range(1, 3):
            try:
                search_results = await search_web(question)
                break
            except Exception:
                if attempt < 2:
                    yield self._make_event(
                        "log",
                        {"phase": "executing", "message": f"追问搜索第{attempt}次失败，正在重试..."},
                    )
                    await asyncio.sleep(1)

        yield self._make_event("log", {"phase": "executing", "message": "正在生成回答..."})

        # 将搜索结果格式化为文本，追加到已有报告后
        search_text = _format_search_results(search_results, question)
        prefix = f"\n\n---\n\n## 追问：{question}\n\n"
        yield self._make_event("report_append_prefix", {"prefix": prefix})

        # 流式生成追问回答
        full_answer = ""
        existing_report = _strip_md_links(state.report) if state.report else ""
        async for chunk in self.report_writer.afollowup_stream(state.topic, question, search_text, existing_report):
            full_answer += chunk
            yield self._make_event("report_chunk", {"chunk": chunk})

        # 更新研究状态
        state.report = (state.report or "") + prefix + full_answer
        yield self._make_event("log", {"phase": "executing", "message": "追问回答完成"})
        yield self._make_event("followup_completed", {"answer": full_answer})

    # 执行完整的三阶段研究流程
    async def _execute(self, state: ResearchState, max_results: int, subtask_count: int):
        # 阶段 1：规划
        async for event in self._planning_phase(state, subtask_count):
            yield event

        # 阶段 2：执行（搜索 + 总结）
        async for event in self._execution_phase(state, max_results, state.deep_mode):
            yield event

        # 阶段 3：报告（撰写 + 评审 + 重写）
        async for event in self._reporting_phase(state):
            yield event

        # 保存完成状态
        state.status = ResearchStatus.completed
        self.research_states[state.research_id] = state
        # 超过上限时移除最早的状态
        if len(self.research_states) > _MAX_STATES:
            self.research_states.popitem(last=False)
        yield self._make_event("completed", {"research_id": state.research_id})

    # 阶段 1：规划 → 将主题分解为子任务列表
    async def _planning_phase(self, state: ResearchState, subtask_count: int):
        state.phase = ResearchPhase.planning
        state.status = ResearchStatus.planning
        state.logs.append(
            LogEntry(phase=ResearchPhase.planning, message=f"开始规划研究主题: {state.topic}")
        )
        yield self._make_event(
            "log", {"phase": "planning", "message": f"开始规划研究主题: {state.topic}"}
        )

        # 调用 TODOPlanner 分解子任务
        subtasks = await self.todo_planner.aplan(state.topic, subtask_count)
        state.subtasks = subtasks

        state.logs.append(
            LogEntry(phase=ResearchPhase.planning, message=f"规划完成，已分解为 {len(subtasks)} 个子任务")
        )
        yield self._make_event(
            "subtasks",
            {
                "subtasks": [
                    {"id": s.id, "title": s.title, "query": s.query}
                    for s in subtasks
                ]
            },
        )

    # 阶段 2：执行 → 并发搜索、全文提取、总结、质量评审
    async def _execution_phase(self, state: ResearchState, max_results: int, deep_mode: bool = False):
        state.phase = ResearchPhase.executing
        state.status = ResearchStatus.searching

        yield self._make_event("phase", {"phase": "executing"})
        yield self._make_event("log", {"phase": "executing", "message": "开始执行子任务搜索与总结..."})

        MAX_ITERATIONS = 3  # 深度模式下最多迭代 3 轮搜索
        # 异步队列，用于 worker 子任务向主循环发送事件
        queue: asyncio.Queue[tuple[str, dict] | None] = asyncio.Queue(maxsize=200)

        # 单个子任务的执行 Worker
        async def worker(subtask):
            try:
                for iteration in range(1, MAX_ITERATIONS + 1):
                    subtask.iteration = iteration

                    # 阶段 2a：搜索
                    subtask.status = SubtaskStatus.searching
                    await queue.put(self._make_event(
                        "subtask_status",
                        {"id": subtask.id, "status": "searching", "title": subtask.title, "iteration": iteration},
                    ))

                    if deep_mode and iteration > 1:
                        await queue.put(self._make_event(
                            "log",
                            {"phase": "executing", "message": f"子任务 {subtask.id} 第{iteration}轮深度搜索: {subtask.query}"},
                        ))

                    # 执行搜索（最多重试 2 次）
                    search_results: list[dict] = []
                    for attempt in range(1, 3):
                        try:
                            search_results = await search_web(subtask.query)
                            break
                        except Exception:
                            if attempt < 2:
                                await queue.put(self._make_event(
                                    "log",
                                    {"phase": "executing", "message": f"子任务 {subtask.id} 第{attempt}次搜索失败，正在重试..."},
                                ))
                                await asyncio.sleep(1)

                    subtask.search_results = search_results

                    # 阶段 2b：URL 价值评估 + 全文提取
                    if search_results:
                        url_eval_text = _format_search_results(search_results, subtask.query)
                        try:
                            selected_urls = await self.task_summarizer.aevaluate_urls(
                                subtask.title, url_eval_text,
                            )
                        except Exception:
                            selected_urls = []

                        if selected_urls:
                            await queue.put(self._make_event(
                                "log",
                                {"phase": "executing", "message": f"子任务 {subtask.id} 正在提取 {len(selected_urls)} 个网页全文..."},
                            ))
                            # 并发抓取多个 URL 的全文
                            contents = await asyncio.gather(
                                *[fetch_page_content(url) for url in selected_urls],
                                return_exceptions=True,
                            )
                            full_content_parts = []
                            for url, content in zip(selected_urls, contents):
                                if isinstance(content, str) and len(content) > 50:
                                    full_content_parts.append(f"全文内容（{url}）：\n{content}")
                            if full_content_parts:
                                subtask.full_contents = {selected_urls[i]: c for i, c in enumerate(contents) if isinstance(c, str) and len(c) > 50}
                                await queue.put(self._make_event(
                                    "log",
                                    {"phase": "executing", "message": f"子任务 {subtask.id} 提取完成，获得 {len(full_content_parts)} 篇完整文章"},
                                ))

                    # 阶段 2c：总结
                    subtask.status = SubtaskStatus.summarizing
                    await queue.put(self._make_event(
                        "subtask_status",
                        {"id": subtask.id, "status": "summarizing", "title": subtask.title, "iteration": iteration},
                    ))

                    # 准备总结用的文本（搜索摘要 + 全文内容）
                    search_text = _format_search_results(search_results, subtask.query)
                    if hasattr(subtask, 'full_contents') and subtask.full_contents:
                        full_parts = []
                        for url, content in subtask.full_contents.items():
                            full_parts.append(f"全文内容（{url}）：\n{content}")
                        search_text += "\n\n" + "\n\n".join(full_parts)
                    # 调用 LLM 生成深度总结
                    summary = await self.task_summarizer.asummarize(
                        subtask.title, subtask.query, search_text,
                    )
                    subtask.summary = summary

                    # 阶段 2d：子任务总结质量评审
                    critic_feedback = None
                    try:
                        critic_result = await self.research_critic.acritic_subtask_summary(
                            subtask.title, subtask.query, summary,
                        )
                        critic_feedback = {
                            "id": subtask.id,
                            "overall_score": critic_result.get("overall_score", 0),
                            "dimensions": critic_result.get("dimensions", {}),
                            "strengths": critic_result.get("strengths", []),
                            "weaknesses": critic_result.get("weaknesses", []),
                            "suggestions": critic_result.get("suggestions", []),
                        }
                        await queue.put(self._make_event("subtask_critic", critic_feedback))
                    except Exception:
                        pass

                    # 深度模式：判断信息是否充分，不足则继续下一轮搜索
                    if not deep_mode or iteration >= MAX_ITERATIONS:
                        break

                    gap_result = await self.task_summarizer.aevaluate_gaps(
                        subtask.title, subtask.query, summary, iteration,
                    )

                    if gap_result.get("sufficient", False):
                        await queue.put(self._make_event(
                            "log",
                            {"phase": "executing", "message": f"子任务 {subtask.id} 信息已充分，结束迭代"},
                        ))
                        break

                    # 信息不足：使用新搜索词继续搜索
                    next_queries = gap_result.get("next_queries", [])
                    if not next_queries:
                        break

                    subtask.query = next_queries[0]
                    await queue.put(self._make_event(
                        "log",
                        {"phase": "executing", "message": f"子任务 {subtask.id} 信息不足，进行第{iteration + 1}轮搜索: {subtask.query}"},
                    ))

                # 子任务完成
                subtask.status = SubtaskStatus.completed
                await queue.put(self._make_event(
                    "subtask_completed",
                    {"id": subtask.id, "title": subtask.title, "summary": subtask.summary, "iteration": subtask.iteration},
                ))
            except Exception as e:
                # 子任务异常
                subtask.status = SubtaskStatus.error
                await queue.put(self._make_event("error", {"error": f"子任务 {subtask.id} 出错[{type(e).__name__}]: {e or '无详细信息'}"}))
            finally:
                # 通知主循环该 worker 已结束
                await queue.put(None)

        # 并发启动所有子任务的 worker
        tasks = [asyncio.create_task(worker(s)) for s in state.subtasks]
        done_count = 0
        total = len(tasks)

        # 主事件循环：从 queue 中读取 worker 发来的事件，逐个 yield
        while done_count < total:
            event = await queue.get()
            if event is None:
                done_count += 1
            else:
                yield event

    # 阶段 3：报告 → 流式生成报告 → 质量评审 → 低于阈值则重写
    async def _reporting_phase(self, state: ResearchState):
        state.phase = ResearchPhase.reporting
        state.status = ResearchStatus.writing

        yield self._make_event("phase", {"phase": "reporting"})
        yield self._make_event("log", {"phase": "reporting", "message": "正在生成研究报告..."})

        # 将所有子任务的总结组装成大文本
        summaries_text = "\n\n".join(
            f"## {s.title}\n{_strip_md_links(s.summary)}" for s in state.subtasks
        )
        search_results_text = _format_all_sources(state.subtasks)

        # 流式生成报告
        state.report = ""
        async for chunk in self.report_writer.awrite_stream(state.topic, summaries_text, search_results_text):
            state.report += chunk
            yield self._make_event("report_chunk", {"chunk": chunk})

        # 质量评审
        try:
            critic_result = await self.research_critic.acritic_report(state.topic, state.report)
            overall_score = critic_result.get("overall_score", 0)

            yield self._make_event("report_critic", {
                "overall_score": overall_score,
                "dimensions": critic_result.get("dimensions", {}),
                "strengths": critic_result.get("strengths", []),
                "weaknesses": critic_result.get("weaknesses", []),
                "suggestions": critic_result.get("suggestions", []),
            })

            # 如果评分低于 7 分，自动重写改进
            if isinstance(overall_score, (int, float)) and overall_score < 7:
                weaknesses = critic_result.get("weaknesses", [])
                suggestions = critic_result.get("suggestions", [])
                critic_text = f"总体评分: {overall_score}/10\n"
                if weaknesses:
                    critic_text += "\n不足:\n- " + "\n- ".join(weaknesses)
                if suggestions:
                    critic_text += "\n\n改进建议:\n- " + "\n- ".join(suggestions)

                yield self._make_event("log", {
                    "phase": "reporting",
                    "message": f"报告质量评分 {overall_score}/10，正在进行改进重写...",
                })
                yield self._make_event("report_rewriting", {
                    "reason": f"质量评分 {overall_score}/10，优化中",
                })

                # 重写报告
                old_report = state.report
                state.report = ""
                async for chunk in self.research_critic.arewrite_report_stream(
                    state.topic, old_report, critic_text,
                ):
                    state.report += chunk
                    yield self._make_event("report_chunk", {"chunk": chunk})
        except Exception:
            pass

        yield self._make_event("log", {"phase": "reporting", "message": "研究报告生成完成"})
        yield self._make_event("report", {"report": state.report})

    # 辅助：创建 SSE 事件元组
    def _make_event(self, event: str, data: dict) -> tuple[str, dict]:
        return (event, data)


# 从搜索结果字典中提取标准字段
def _extract_result(r: dict) -> dict:
    return {"title": r.get("title", ""), "url": r.get("url", ""), "body": r.get("body", "")}


# 将搜索结果列表格式化为 LLM 可读的文本
def _format_search_results(results: list[dict], query: str) -> str:
    if not results:
        return "未搜索到相关结果。"

    lines = []
    for i, r in enumerate(results, 1):
        item = _extract_result(r)
        lines.append(f"[{i}] {item['title']}\n    URL: {item['url']}\n    {item['body']}")
    return "\n\n".join(lines)


# 格式化所有子任务的原始搜索结果（用于报告参考文献）
def _format_all_sources(subtasks: list) -> str:
    parts = []
    for s in subtasks:
        if not s.search_results:
            continue
        sources = []
        for r in s.search_results:
            item = _extract_result(r)
            sources.append(f"- [{item['title']}]({item['url']})\n  {item['body']}")
        if sources:
            parts.append(f"## {s.title}\n" + "\n".join(sources))
    return "\n\n".join(parts)


# 去除文本中的 Markdown 链接标记，只保留链接文字
def _strip_md_links(text: str) -> str:
    return _MD_LINK_RE.sub(r"\1", text)
