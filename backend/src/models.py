from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class ResearchStatus(str, Enum):
    planning = "planning"
    searching = "searching"
    summarizing = "summarizing"
    writing = "writing"
    completed = "completed"
    error = "error"


class ResearchPhase(str, Enum):
    planning = "planning"
    executing = "executing"
    reporting = "reporting"


class SubtaskStatus(str, Enum):
    pending = "pending"
    searching = "searching"
    summarizing = "summarizing"
    completed = "completed"
    error = "error"


class Subtask(BaseModel):
    id: int
    title: str
    query: str
    status: SubtaskStatus = SubtaskStatus.pending
    summary: str = ""
    search_results: list[dict] = Field(default_factory=list)
    iteration: int = 1
    full_contents: dict[str, str] = Field(default_factory=dict)


class LogEntry(BaseModel):
    phase: ResearchPhase
    message: str


class ResearchState(BaseModel):
    research_id: str
    topic: str
    status: ResearchStatus = ResearchStatus.planning
    phase: ResearchPhase = ResearchPhase.planning
    subtasks: list[Subtask] = Field(default_factory=list)
    report: str = ""
    logs: list[LogEntry] = Field(default_factory=list)
    error: str = ""
    deep_mode: bool = False


class ResearchRequest(BaseModel):
    topic: str
    max_results: int = Field(default=5, ge=1, le=20)
    subtask_count: int = Field(default=3, ge=1, le=8)
    deep_mode: bool = False


class FollowupRequest(BaseModel):
    question: str


class SubtaskPlan(BaseModel):
    title: str = Field(description="子任务标题")
    query: str = Field(description="用于搜索的关键词")


class ResearchPlan(BaseModel):
    subtasks: list[SubtaskPlan] = Field(description="研究子任务列表")
