from __future__ import annotations

import json
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from backend.src.agent import ResearchAgent
from backend.src.models import ResearchRequest

app = FastAPI(title="Research Agent API", version="1.0.0")

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

    async def event_generator():
        async for event_json in research_agent.run(
            topic=topic,
            max_results=request.max_results,
            subtask_count=request.subtask_count,
        ):
            if await raw_request.is_disconnected():
                break
            parsed = json.loads(event_json)
            yield f"event: {parsed['event']}\ndata: {json.dumps(parsed['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
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
