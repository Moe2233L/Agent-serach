from __future__ import annotations

import asyncio
import json
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from backend.src.agent import ResearchAgent
from backend.src.models import FollowupRequest, ResearchRequest

# 配置日志格式
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = FastAPI(title="Research Agent API", version="1.0.0")

# SSE 心跳保活间隔（秒）
_HEARTBEAT_INTERVAL = 10

# 配置 CORS 中间件，允许所有来源的跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局研究 Agent 实例
research_agent: ResearchAgent | None = None


# 应用启动时初始化 ResearchAgent
@app.on_event("startup")
async def startup():
    global research_agent

    research_agent = ResearchAgent()
    logging.info("ResearchAgent 初始化完成")


# 健康检查端点
@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok"})


# 将 (event, data) 元组格式化为 SSE 协议文本
# 格式：event: xxx\ndata: {"key": "value"}\n\n
def _format_sse(event_item: tuple[str, dict] | str) -> str:
    if isinstance(event_item, str):
        return event_item
    event, data = event_item
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# 异步生成 SSE 事件流，内置心跳保活机制（10 秒间隔）
# 若 10 秒无新事件则发送心跳注释行，防止连接超时断开
async def _stream_events(event_generator, raw_request: Request):
    async def heartbeat_wrapper():
        while True:
            try:
                # 等待下一个事件（最多等 _HEARTBEAT_INTERVAL 秒）
                done, pending = await asyncio.wait(
                    [asyncio.create_task(event_generator.__anext__())],
                    timeout=_HEARTBEAT_INTERVAL,
                )
                if done:
                    for task in done:
                        try:
                            yield task.result()
                        except StopAsyncIteration:
                            return
                else:
                    # 超时无事件 → 检查客户端是否断开，发送心跳
                    if await raw_request.is_disconnected():
                        return
                    yield ": heartbeat\n\n"  # SSE 注释行，仅作保活
            except StopAsyncIteration:
                return
            except Exception:
                break

    async for event_json in heartbeat_wrapper():
        if await raw_request.is_disconnected():
            break
        yield _format_sse(event_json)


# 发起研究的 POST 端点，返回 SSE 事件流
@app.post("/research/stream")
async def research_stream(request: ResearchRequest, raw_request: Request):
    if not research_agent:
        return JSONResponse(
            {"error": "ResearchAgent 未初始化"},
            status_code=500,
        )

    topic = request.topic.strip()
    if not topic:
        return JSONResponse(
            {"error": "研究主题不能为空"},
            status_code=400,
        )

    # 返回 SSE 流式响应，带上防缓存和禁用代理缓冲的头部
    return StreamingResponse(
        _stream_events(research_agent.run(topic=topic, max_results=request.max_results, subtask_count=request.subtask_count, deep_mode=request.deep_mode), raw_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# 对已完成研究发起追问的 POST 端点
@app.post("/research/{research_id}/followup")
async def research_followup(research_id: str, request: FollowupRequest, raw_request: Request):
    if not research_agent:
        return JSONResponse(
            {"error": "ResearchAgent 未初始化"},
            status_code=500,
        )

    question = request.question.strip()
    if not question:
        return JSONResponse(
            {"error": "追问内容不能为空"},
            status_code=400,
        )

    # 查找该研究的状态对象
    state = research_agent.get_state(research_id)
    if not state:
        return JSONResponse(
            {"error": "研究不存在或已过期"},
            status_code=404,
        )

    return StreamingResponse(
        _stream_events(research_agent.followup(research_id, question), raw_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# 直接运行时启动 uvicorn 服务器
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
