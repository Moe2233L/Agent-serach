from __future__ import annotations

import json
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


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


class TaskSummarizer:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个研究总结专家。根据搜索结果对特定子任务进行总结。\n\n"
                "输出结构（Markdown 格式）：\n"
                "1. **核心发现**：列出 3-5 条关键发现，每条用 `- ` 开头\n"
                "2. **详细分析**：对每条发现展开阐述，引用来源时使用编号形式 `[1]`、`[2]` 等\n"
                "3. **争议与不足**：如果不同来源存在矛盾或信息不充分，在此说明\n\n"
                "约束：\n"
                "- 严格基于搜索结果，不得编造任何信息\n"
                "- 每个搜索结果条目以 `[1]` `[2]` 编号开头，下方有 URL 和正文\n"
                "- 文末**必须附上引用来源列表**，格式：`[N] [来源标题](完整URL)`\n"
                "- 用中文输出\n"
                "- 语言简洁、客观、专业\n"
                "- 如果搜索结果不足以得出结论，请如实说明，不要猜测",
            ),
            (
                "human",
                "子任务：{title}\n搜索关键词：{query}\n\n以下是搜索结果：\n{search_results}\n\n请按上述要求对该子任务进行总结。",
            ),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

        self.gap_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个研究质量评估专家。判断当前研究总结是否充分，如果不够，生成更精准的下一轮搜索词。\n\n"
                "输出严格的 JSON 格式（不含 markdown 代码块标记）：\n"
                '{{"sufficient": true/false, "reason": "判断理由", "next_queries": ["搜索词1", "搜索词2"]}}\n\n'
                "判断规则（按优先级）：\n"
                "1. 默认 sufficient: true，除非明确满足以下条件才判 false\n"
                "2. 判 false 的唯一标准：搜索结果为 0 条，或总结中明确说了'未找到相关信息'\n"
                "3. 如果有 2 条以上不同来源的信息且没有重大矛盾 → 直接判 true\n"
                "4. 第 2 轮及以后倾向于判 true，不要无限制迭代\n\n"
                "next_queries：\n"
                "- 仅当 sufficient: false 时生成\n"
                "- 1-2 个英文搜索词，针对上次搜索的盲区\n"
                "- 如果判 true，next_queries 返回空数组 []\n\n"
                "正确示例：\n"
                '{{"sufficient": true, "reason": "有3条不同来源覆盖了核心方面，信息充分", "next_queries": []}}\n'
                '{{"sufficient": false, "reason": "搜索结果仅1条且内容不相关", "next_queries": ["specific term in English"]}}',
            ),
            (
                "human",
                "子任务：{title}\n当前搜索关键词：{query}\n当前总结（第 {iteration} 轮）：\n{summary}\n\n请评估信息是否充分。",
            ),
        ])
        self.gap_chain = self.gap_prompt | self.llm | StrOutputParser()

    async def asummarize(self, title: str, query: str, search_results: str) -> str:
        return await self.chain.ainvoke({
            "title": title,
            "query": query,
            "search_results": search_results,
        })

    async def aevaluate_gaps(self, title: str, query: str, summary: str, iteration: int) -> dict:
        response = await self.gap_chain.ainvoke({
            "title": title,
            "query": query,
            "summary": summary,
            "iteration": iteration,
        })
        raw = response.strip()
        if "```" in raw:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if match:
                raw = match.group(1).strip()
        return _parse_json(raw)
