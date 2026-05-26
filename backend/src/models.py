from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


# 研究整体状态枚举
class ResearchStatus(str, Enum):
    planning = "planning"      # 规划阶段
    searching = "searching"    # 搜索阶段
    summarizing = "summarizing"  # 总结阶段
    writing = "writing"        # 报告撰写阶段
    completed = "completed"    # 完成
    error = "error"            # 出错


# 研究阶段枚举
class ResearchPhase(str, Enum):
    planning = "planning"      # 规划
    executing = "executing"    # 执行
    reporting = "reporting"    # 报告


# 子任务状态枚举
class SubtaskStatus(str, Enum):
    pending = "pending"          # 待处理
    searching = "searching"      # 搜索中
    summarizing = "summarizing"  # 总结中
    completed = "completed"      # 完成
    error = "error"              # 出错


# 单个子任务的数据模型
class Subtask(BaseModel):
    id: int                                               # 子任务编号
    title: str                                            # 子任务标题（中文）
    query: str                                            # 搜索关键词（英文）
    status: SubtaskStatus = SubtaskStatus.pending         # 当前状态
    summary: str = ""                                     # 研究总结
    search_results: list[dict] = Field(default_factory=list)  # 原始搜索结果列表
    iteration: int = 1                                    # 当前迭代轮次（深度模式用）
    full_contents: dict[str, str] = Field(default_factory=dict)  # 提取的网页全文


# 日志条目数据模型
class LogEntry(BaseModel):
    phase: ResearchPhase   # 所属阶段
    message: str           # 日志内容


# 一次完整研究的状态数据模型
class ResearchState(BaseModel):
    research_id: str                                             # 研究唯一标识
    topic: str                                                   # 研究主题
    status: ResearchStatus = ResearchStatus.planning             # 整体状态
    phase: ResearchPhase = ResearchPhase.planning                # 当前阶段
    subtasks: list[Subtask] = Field(default_factory=list)        # 子任务列表
    report: str = ""                                             # 最终报告
    logs: list[LogEntry] = Field(default_factory=list)           # 日志列表
    error: str = ""                                              # 错误信息
    deep_mode: bool = False                                      # 是否开启深度研究


# 发起研究的请求体
class ResearchRequest(BaseModel):
    topic: str                                                              # 研究主题（必填）
    max_results: int = Field(default=5, ge=1, le=20)                        # 搜索结果数量（1-20）
    subtask_count: int = Field(default=3, ge=1, le=8)                       # 子任务分解数（1-8）
    deep_mode: bool = False                                                 # 是否深度模式


# 追问的请求体
class FollowupRequest(BaseModel):
    question: str  # 追问内容
