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
                "你是一个专业的研究报告撰写专家。将所有子任务总结整合成一份高质量、有深度的研究报告。\n\n"
                "**字数要求（严格执行）：**\n"
                "- 摘要：150-250 字\n"
                "- 结论：150-300 字\n"
                "- **整份报告控制在 1500-3000 字**\n\n"
                "**结构：**\n"
                "1. 标题 — 简明扼要，体现研究主题的广度与深度\n"
                "2. 摘要 — 150-250 字概述研究背景、核心发现和结论\n"
                "3. 正文 — 按子任务分段，每段包含：具体事实 + 数据/案例 + 分析\n"
                "4. 结论 — 总结核心发现，指出研究局限性和未来方向\n"
                "5. 参考文献 — 末尾列出所有来源，勿遗漏\n\n"
                "**内容质量要求：**\n"
                "- 每节必须包含至少 1 个具体数据、案例或引用\n"
                "- 避免空泛概括，如'这是一个重要的领域'、'受到了广泛关注'\n"
                "- 如果某些搜索结果包含**完整文章全文**，优先基于全文内容进行分析，而非仅依赖摘要片段\n"
                "- 有全文的来源在引用时标注'[N] 来源标题（全文分析）'\n\n"
                "**引用规则（违反即不合格）：**\n"
                '✅ 正文用 `[1]` 放在事实陈述句末即可\n'
                '✅ 例："据估计全球碳市场价值已超过 9000 亿美元[1]"\n'
                '✅ 多个来源并列用逗号分隔，如"...[1][2]" 或 "...[1,2]"\n'
                '❌ 禁止："根据文献[1]指出"、"文献显示"、"研究表明"、"有文献提到"\n'
                '❌ 禁止正文中出现任何超链接 `[文字](URL)`\n'
                '❌ 禁止出现"[来源1]"、"[1]指出"等引用在前的方式\n\n'
                "**参考文献格式：**\n"
                "- [来源标题](完整URL)\n"
                "- 必须使用搜索结果中提供的真实 URL，不得编造\n"
                "- 如果同一来源在多个子任务中出现，只列一次\n\n"
                "使用中文、Markdown 格式。适当用表格/列表/引用块增强可读性。",
            ),
            (
                "human",
                "研究主题：{topic}\n\n以下是各子任务的研究总结：\n{summaries}\n\n"
                "以下是各子任务的原始搜索结果（含真实 URL，用于生成参考文献链接）：\n{search_results}\n\n"
                "请生成一份完整、专业的研究报告，严格遵守上述字数要求。",
            ),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

        self.followup_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个研究问答助手。基于已有研究报告和搜索结果回答追问。\n\n"
                "规则（严格执行）：\n"
                "1. 仅基于已有报告和搜索结果回答，不得编造任何信息\n"
                "2. 直接输出答案，不要重复报告全文，不要加'以下是回答'等前缀\n"
                "3. 引用来源时用 `[1]` 放在句末，禁止'根据文献''文献指出'等引导语\n"
                "4. **引用具体原文段落**：当引用某个发现时，从搜索结果的 '全文内容' 或 'body' 字段中截取原文支撑语句，格式：\n"
                '   > "原文引用内容" —— [1]\n'
                "5. 如果搜索结果不足以回答，如实说明'现有资料中未找到相关信息'，不要猜测\n"
                "6. 回答长度控制在 300-800 字，简洁聚焦\n"
                "7. 如果用户的问题涉及报告中已经覆盖的内容，直接引用报告中的对应段落",
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
