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
                "引用规则（重要，必须遵守）：\n"
                "- 正文中**绝对禁止**出现任何可点击的超链接，包括 `[文字](URL)` 格式\n"
                "- 正文引用来源时，统一使用编号格式：`[1]`、`[2]`、`[3]`（纯文本，不加链接）\n"
                "- 所有带有 URL 的链接**只允许**出现在最后的参考文献章节\n"
                "- 参考文献区域使用编号列表，格式：`[1] 来源标题 - 完整URL`，URL 用 Markdown 格式 `[来源标题](完整URL)`\n"
                "- 每条参考文献必须使用下方提供的搜索结果中的真实 URL，不得编造\n\n"
                "参考文献格式示例（仅用于参考文献区域）：\n"
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

        self.followup_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个研究问答助手，根据已知的研究报告和搜索结果回答问题。\n\n"
                "回答要求：\n"
                "1. 基于已有研究报告的上下文回答，保持一致的风格和引用编号\n"
                "2. 如果新搜索结果中有相关信息，引用新来源时使用继续递增的编号 `[N]`\n"
                "3. 直接输出答案内容即可，不要重复已有的报告\n"
                "4. 语言简洁专业\n\n"
                "约束：\n"
                "- 严格基于已有报告和搜索结果回答，不得编造\n"
                "- 正文中禁止出现任何可点击的超链接\n"
                "- 如果搜索结果不足以回答，请如实说明",
            ),
            (
                "human",
                "研究主题：{topic}\n\n已有研究报告：\n{existing_report}\n\n"
                "用户追问：{question}\n\n以下是针对追问的新搜索结果：\n{search_results}\n\n"
                "请回答用户的问题。",
            ),
        ])
        self.followup_chain = self.followup_prompt | self.llm | StrOutputParser()

    async def awrite_stream(self, topic: str, summaries: str, search_results: str = ""):
        async for chunk in self.chain.astream({"topic": topic, "summaries": summaries, "search_results": search_results}):
            yield chunk

    async def afollowup_stream(self, topic: str, question: str, search_results: str, existing_report: str = ""):
        async for chunk in self.followup_chain.astream({
            "topic": topic, "question": question, "search_results": search_results, "existing_report": existing_report,
        }):
            yield chunk
