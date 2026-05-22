from __future__ import annotations

import asyncio
import json
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from backend.src.agent import ResearchAgent
from backend.src.models import FollowupRequest, ResearchRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = FastAPI(title="Research Agent API", version="1.0.0")

_HEARTBEAT_INTERVAL = 10

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

research_agent: ResearchAgent | None = None


@app.on_event("startup")
async def startup():
    global research_agent

    research_agent = ResearchAgent()
    logging.info("ResearchAgent 初始化完成")


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok"})


def _format_sse(event_tuple: tuple[str, dict]) -> str:
    event, data = event_tuple
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_events(event_generator, raw_request: Request):
    async def heartbeat_wrapper():
        while True:
            try:
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
                    if await raw_request.is_disconnected():
                        return
                    yield ": heartbeat\n\n"
            except StopAsyncIteration:
                return
            except Exception:
                break

    async for event_json in heartbeat_wrapper():
        if await raw_request.is_disconnected():
            break
        yield _format_sse(event_json)


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

    return StreamingResponse(
        _stream_events(research_agent.run(topic=topic, max_results=request.max_results, subtask_count=request.subtask_count, deep_mode=request.deep_mode), raw_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
