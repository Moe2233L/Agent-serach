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
                "你是一个专业的研究报告撰写专家。将所有子任务总结整合成一份报告。\n\n"
                "**字数：整份报告 1000-3000 字，语言精炼**\n\n"
                "**结构：**\n"
                "1. 标题 — 简明扼要\n"
                "2. 摘要 — 100-200 字概述\n"
                "3. 正文 — 按子任务分段阐述\n"
                "4. 结论 — 核心发现总结\n"
                "5. 参考文献 — 末尾列出所有来源\n\n"
                "**引用规则（违反即不合格）：**\n"
                '✅ 正文用 `[1]` 放在事实陈述句末即可\n'
                '✅ 例："据估计全球碳市场价值已超过 9000 亿美元[1]"\n'
                '❌ 禁止："根据文献[1]指出"、"文献显示"、"研究表明"\n'
                "❌ 禁止正文中出现任何超链接 `[文字](URL)`\n\n"
                "**参考文献格式：**\n"
                "- [来源标题](完整URL)\n"
                "- 必须使用搜索结果中提供的真实 URL\n\n"
                "使用中文、Markdown 格式，适当用表格/列表增强可读性。",
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
                "你是一个研究问答助手。基于已有研究报告和搜索结果回答追问。\n\n"
                "规则：\n"
                "1. 基于已有报告回答，风格保持一致\n"
                "2. 直接输出答案，不要重复报告全文\n"
                "3. 引用来源时用 `[1]` 放在句末，禁止'根据文献''文献指出'等引导语\n"
                "4. 严格基于已有素材，不得编造\n"
                "5. 搜索不足时如实说明",
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
