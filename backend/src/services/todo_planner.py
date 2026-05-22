from __future__ import annotations

import json
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from backend.src.models import Subtask


def _parse_json(text: str) -> dict:
    decoder = json.JSONDecoder()
    for i, c in enumerate(text):
        if c in ('{', '['):
            try:
                obj, _ = decoder.raw_decode(text[i:])
                return obj
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError("No valid JSON found in response", text, 0)


class TODOPlanner:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个研究规划专家。将用户的研究主题分解为 {count} 个具体的、可独立搜索的子任务。\n\n"
                "要求：\n"
                "- 每个子任务覆盖主题的**不同维度**，互不重叠\n"
                "- **维度平衡**：避免过于宽泛（如'XX的概述'）或过于狭窄（如'XX的具体实现细节'），控制在中等颗粒度\n"
                "- 子任务标题（title）用中文，概括该维度的核心问题，**必须是完整句子的形式**（如'量子计算在金融领域的应用现状'而非'金融应用'）\n"
                "- 搜索关键词（query）用英文，精准、具体，建议用引号括起关键短语，便于搜索引擎返回高质量结果\n"
                "- 确保 {count} 个子任务从整体上覆盖主题的各个关键方面\n"
                "- **互斥性检查**：如果两个子任务可能搜到相同内容，合并或调整其中一个\n\n"
                "必须输出严格的 JSON 格式（不含 markdown 代码块标记）：\n"
                '{{"subtasks": [{{"title": "子任务标题（完整句式）", "query": "精准英文搜索词"}}]}}',
            ),
            ("human", "研究主题：{topic}"),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

    async def aplan(self, topic: str, count: int = 3) -> list[Subtask]:
        response = await self.chain.ainvoke({"topic": topic, "count": count})
        raw = response.strip()

        json_str = raw
        if "```" in raw:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if match:
                json_str = match.group(1).strip()

        data = _parse_json(json_str)
        return [
            Subtask(id=i, title=item["title"], query=item["query"])
            for i, item in enumerate(data["subtasks"], 1)
        ]
