from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

class ReportWriter:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个专业的研究报告撰写专家。将所有子任务总结整合成一份完整、专业的研究报告。\n\n"
                "报告结构：\n"
                "1. **标题**：简明扼要的研究报告标题\n"
                "2. **摘要**：对整个研究的简要概述（100-200 字）\n"
                "3. **正文**：对每个子任务的发现进行详细阐述，分段呈现\n"
                "4. **结论**：总结主要发现和洞见\n"
                "5. **参考文献**：在报告末尾列出所有引用的来源\n\n"
                "引用规则（重要）：\n"
                "- 正文中**禁止出现任何可点击的超链接**\n"
                "- 正文引用来源时，统一使用编号格式：`[1]`、`[2]`、`[3]`……\n"
                "- 参考文献区域使用编号列表，格式：`[1] 来源标题 - 完整URL`，URL 用 Markdown 格式 `[来源标题](完整URL)`\n"
                "- 每条参考文献必须使用下方提供的搜索结果中的真实 URL，不得编造\n\n"
                "参考文献格式示例：\n"
                "- `[1] [Pathways to Carbon Neutrality](https://example.com/carbon-neutrality)`\n"
                "- `[2] [Renewable Energy - Wikipedia](https://en.wikipedia.org/wiki/Renewable_energy)`\n\n"
                "格式要求：\n"
                "- 使用中文输出，语言流畅专业\n"
                "- 使用 Markdown 格式\n"
                "- 适当使用表格、列表等增强可读性",
            ),
            (
                "human",
                "研究主题：{topic}\n\n以下是各子任务的研究总结：\n{summaries}\n\n"
                "以下是各子任务的原始搜索结果（含真实 URL，用于生成参考文献链接）：\n{search_results}\n\n"
                "请生成一份完整、专业的研究报告。",
            ),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

    def write(self, topic: str, summaries: str, search_results: str = "") -> str:
        return self.chain.invoke({"topic": topic, "summaries": summaries, "search_results": search_results})

    async def awrite(self, topic: str, summaries: str, search_results: str = "") -> str:
        return await self.chain.ainvoke({"topic": topic, "summaries": summaries, "search_results": search_results})

    async def awrite_stream(self, topic: str, summaries: str, search_results: str = ""):
        async for chunk in self.chain.astream({"topic": topic, "summaries": summaries, "search_results": search_results}):
            yield chunk
