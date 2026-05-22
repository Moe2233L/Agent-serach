from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


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

    async def asummarize(self, title: str, query: str, search_results: str) -> str:
        return await self.chain.ainvoke({
            "title": title,
            "query": query,
            "search_results": search_results,
        })
