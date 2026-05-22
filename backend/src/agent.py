from __future__ import annotations

import asyncio
import json
import re
import uuid

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
from backend.src.services.todo_planner import TODOPlanner
from backend.src.services.task_summarizer import TaskSummarizer
from backend.src.services.report_writer import ReportWriter
from langchain_openai import ChatOpenAI


class ResearchAgent:
    def __init__(self):
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.todo_planner = TODOPlanner(llm)
        self.task_summarizer = TaskSummarizer(llm)
        self.report_writer = ReportWriter(llm)
        self.research_states: dict[str, ResearchState] = {}

    def get_state(self, research_id: str) -> ResearchState | None:
        return self.research_states.get(research_id)

    async def run(self, topic: str, max_results: int = 5, subtask_count: int = 3):
        research_id = uuid.uuid4().hex[:12]
        state = ResearchState(research_id=research_id, topic=topic)

        try:
            async for event in self._execute(state, max_results, subtask_count):
                yield event
        except Exception as e:
            state.status = ResearchStatus.error
            state.error = str(e)
            yield self._make_event("error", {"error": str(e)})

    async def followup(self, research_id: str, question: str, max_results: int = 5):
        state = self.research_states.get(research_id)
        if not state:
            yield self._make_event("error", {"error": "研究不存在或已过期"})
            return

        state.phase = ResearchPhase.executing

        yield self._make_event("followup_start", {"question": question})
        yield self._make_event("log", {"phase": "executing", "message": f"搜索并回答: {question}"})

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

        search_text = _format_search_results(search_results, question)
        prefix = f"\n\n---\n\n## 追问：{question}\n\n"
        yield self._make_event("report_append_prefix", {"prefix": prefix})

        full_answer = ""
        existing_report = _strip_md_links(state.report) if state.report else ""
        async for chunk in self.report_writer.afollowup_stream(state.topic, question, search_text, existing_report):
            full_answer += chunk
            yield self._make_event("report_chunk", {"chunk": chunk})

        yield self._make_event("log", {"phase": "executing", "message": "追问回答完成"})
        yield self._make_event("followup_completed", {"answer": full_answer})

    async def _execute(self, state: ResearchState, max_results: int, subtask_count: int):
        async for event in self._planning_phase(state, subtask_count):
            yield event

        async for event in self._execution_phase(state, max_results):
            yield event

        async for event in self._reporting_phase(state):
            yield event

        state.status = ResearchStatus.completed
        self.research_states[state.research_id] = state
        yield self._make_event("completed", {"research_id": state.research_id})

    async def _planning_phase(self, state: ResearchState, subtask_count: int):
        state.phase = ResearchPhase.planning
        state.status = ResearchStatus.planning
        state.logs.append(
            LogEntry(phase=ResearchPhase.planning, message=f"开始规划研究主题: {state.topic}")
        )
        yield self._make_event(
            "log", {"phase": "planning", "message": f"开始规划研究主题: {state.topic}"}
        )

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

    async def _execution_phase(self, state: ResearchState, max_results: int):
        state.phase = ResearchPhase.executing
        state.status = ResearchStatus.searching

        yield self._make_event("phase", {"phase": "executing"})
        yield self._make_event("log", {"phase": "executing", "message": "开始执行子任务搜索与总结..."})

        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def worker(subtask):
            try:
                subtask.status = SubtaskStatus.searching
                await queue.put(self._make_event(
                    "subtask_status",
                    {"id": subtask.id, "status": "searching", "title": subtask.title},
                ))

                search_results: list[dict] = []
                for attempt in range(1, 3):
                    try:
                        search_results = await search_web(subtask.query)
                        break
                    except Exception as e:
                        if attempt < 2:
                            await queue.put(self._make_event(
                                "log",
                                {"phase": "executing", "message": f"子任务 {subtask.id} 第{attempt}次搜索失败，正在重试..."},
                            ))
                            await asyncio.sleep(1)

                subtask.search_results = search_results

                subtask.status = SubtaskStatus.summarizing
                await queue.put(self._make_event(
                    "subtask_status",
                    {"id": subtask.id, "status": "summarizing", "title": subtask.title},
                ))

                search_text = _format_search_results(search_results, subtask.query)
                summary = await self.task_summarizer.asummarize(
                    subtask.title, subtask.query, search_text,
                )
                subtask.summary = summary
                subtask.status = SubtaskStatus.completed

                await queue.put(self._make_event(
                    "subtask_completed",
                    {"id": subtask.id, "title": subtask.title, "summary": summary},
                ))
            except Exception as e:
                subtask.status = SubtaskStatus.error
                await queue.put(self._make_event("error", {"error": f"子任务 {subtask.id} 出错: {e}"}))
            finally:
                await queue.put(None)

        tasks = [asyncio.create_task(worker(s)) for s in state.subtasks]
        done_count = 0
        total = len(tasks)

        while done_count < total:
            event = await queue.get()
            if event is None:
                done_count += 1
            else:
                yield event

    async def _reporting_phase(self, state: ResearchState):
        state.phase = ResearchPhase.reporting
        state.status = ResearchStatus.writing

        yield self._make_event("phase", {"phase": "reporting"})
        yield self._make_event("log", {"phase": "reporting", "message": "正在生成研究报告..."})

        summaries_text = "\n\n".join(
            f"## {s.title}\n{_strip_md_links(s.summary)}" for s in state.subtasks
        )
        search_results_text = _format_all_sources(state.subtasks)

        state.report = ""
        async for chunk in self.report_writer.awrite_stream(state.topic, summaries_text, search_results_text):
            state.report += chunk
            yield self._make_event("report_chunk", {"chunk": chunk})

        yield self._make_event("log", {"phase": "reporting", "message": "研究报告生成完成"})
        yield self._make_event("report", {"report": state.report})

    def _make_event(self, event: str, data: dict) -> str:
        return json.dumps({"event": event, "data": data}, ensure_ascii=False)


def _format_search_results(results: list[dict], query: str) -> str:
    if not results:
        return "未搜索到相关结果。"

    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("url", "")
        body = r.get("body", "")
        lines.append(f"[{i}] {title}\n    URL: {url}\n    {body}")
    return "\n\n".join(lines)


def _format_all_sources(subtasks: list) -> str:
    parts = []
    for s in subtasks:
        if not s.search_results:
            continue
        sources = []
        for r in s.search_results:
            title = r.get("title", "")
            url = r.get("url", "")
            body = r.get("body", "")
            sources.append(f"- [{title}]({url})\n  {body}")
        if sources:
            parts.append(f"## {s.title}\n" + "\n".join(sources))
    return "\n\n".join(parts)


def _strip_md_links(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
