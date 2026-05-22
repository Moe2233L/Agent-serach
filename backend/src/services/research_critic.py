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
    return {}


_REPORT_DIMENSIONS = ["structure", "depth", "citation_accuracy", "readability", "completeness"]
_SUBTASK_DIMENSIONS = ["relevance", "depth", "clarity", "citation_quality"]


def _ensure_dimensions(result: dict, expected: list[str]) -> dict:
    dims = result.get("dimensions", {})
    if not isinstance(dims, dict):
        dims = {}
    for key in expected:
        val = dims.get(key)
        if not isinstance(val, (int, float)) or val < 1 or val > 10:
            dims[key] = 7
    result["dimensions"] = dims
    scores = [v for v in dims.values() if isinstance(v, (int, float))]
    raw = result.get("overall_score")
    if not isinstance(raw, (int, float)) or raw < 1 or raw > 10:
        result["overall_score"] = round(sum(scores) / len(scores)) if scores else 7
    for field in ("strengths", "weaknesses", "suggestions"):
        if not isinstance(result.get(field), list):
            result[field] = []
    return result


class ResearchCritic:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

        self.subtask_critic_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个研究质量评审专家。对单个子任务的研究总结进行质量评审。\n\n"
                "**输出格式（严格执行）：**\n"
                "必须输出严格的 JSON 格式（不含 markdown 代码块标记），结构如下：\n"
                "{{\n"
                '  "overall_score": <1-10的整数>,\n'
                '  "dimensions": {{\n'
                '    "relevance": <1-10>,\n'
                '    "depth": <1-10>,\n'
                '    "clarity": <1-10>,\n'
                '    "citation_quality": <1-10>\n'
                "  }},\n"
                '  "strengths": ["优点1", "优点2"],\n'
                '  "weaknesses": ["不足1", "不足2"],\n'
                '  "suggestions": ["改进建议1", "改进建议2"]\n'
                "}}\n\n"
                "**评分标准（严格执行）：**\n"
                "每个维度 1-10 分，参考以下指南：\n"
                "| 分数 | 含义 |\n"
                "|------|------|\n"
                "| 9-10 | 优秀 — 完全满足要求，无可挑剔 |\n"
                "| 7-8  | 良好 — 满足要求，有少量可改进空间 |\n"
                "| 5-6  | 及格 — 基本满足但存在明显不足 |\n"
                "| 3-4  | 较差 — 多项未达标 |\n"
                "| 1-2  | 很差 — 几乎未满足任何要求 |\n\n"
                "**维度定义：**\n"
                "- relevance（相关性）：总结是否紧扣子任务主题，是否覆盖核心方面。\n"
                '  ✅ 好：子任务「量子计算在金融领域的应用」，总结聚焦于金融场景的具体应用案例\n'
                "  ❌ 差：大段描述量子计算基础原理，与金融应用无关\n"
                "- depth（深度）：是否有具体事实、数据、案例支撑，而非空泛描述。\n"
                '  ✅ 好：「据摩根大通 2024 年报告，量子计算预计将为金融业节省 120 亿美元/年」\n'
                '  ❌ 差：「量子计算在金融领域有广阔的应用前景」（无数据无案例）\n'
                "- clarity（清晰度）：逻辑是否清晰，表述是否准确，结构是否合理。\n"
                "  ✅ 好：分点阐述，每点有主题句 + 支撑证据 + 引用\n"
                "  ❌ 差：段落混乱，概念跳跃，前后矛盾\n"
                "- citation_quality（引用质量）：引用是否真实，引用格式是否正确。\n"
                '  ✅ 好：每条引用标注编号，文末列出「来源标题(URL)」\n'
                "  ❌ 差：引用无编号、无来源、或来源与摘要不匹配\n\n"
                "overall_score 综合上述维度加权后取整数（四舍五入），而非简单平均。\n\n"
                "**优点/不足/改进建议规则：**\n"
                '  - strengths（优点）：列出 1-3 个具体的优点，描述格式为「XX做得好：（具体说明）」。\n'
                "  如果无可列优点，返回空数组 []\n"
                '  - weaknesses（不足）：列出 1-3 个具体不足，描述格式为「XX不足：（具体说明）」。\n'
                "  如果无不足，返回空数组 []（不要为凑数而编造）\n"
                "  - suggestions（改进建议）：列出 1-3 个可操作的改进建议。\n"
                "  如果无需改进，返回空数组 []\n\n"
                "**反例（违反即不合格）：**\n"
                '❌ 输出带 markdown 代码块的 JSON：```json {{"overall_score": 8}}```\n'
                '❌ 评分理由空泛：「信息比较充分，质量还可以」\n'
                '❌ strengths/weaknesses/suggestions 内容模糊：「内容很好」「需要改进」\n'
                "❌ 所有维度给相同分数（如全是 8）—— 不同维度应独立评分\n"
                '❌ 不足和建议写的是同一件事 —— 不足是「什么有问题」，建议是「怎么改」',
            ),
            (
                "human",
                "子任务标题：{title}\n搜索关键词：{query}\n\n研究总结：\n{summary}\n\n请对该总结进行质量评审，严格按照上述要求输出 JSON。",
            ),
        ])
        self.subtask_critic_chain = self.subtask_critic_prompt | self.llm | StrOutputParser()

        self.report_critic_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个研究报告评审专家。对整份研究报告进行质量评审。\n\n"
                "**输出格式（严格执行）：**\n"
                "必须输出严格的 JSON 格式（不含 markdown 代码块标记），结构如下：\n"
                "{{\n"
                '  "overall_score": <1-10的整数>,\n'
                '  "dimensions": {{\n'
                '    "structure": <1-10>,\n'
                '    "depth": <1-10>,\n'
                '    "citation_accuracy": <1-10>,\n'
                '    "readability": <1-10>,\n'
                '    "completeness": <1-10>\n'
                "  }},\n"
                '  "strengths": ["优点1", "优点2"],\n'
                '  "weaknesses": ["不足1", "不足2"],\n'
                '  "suggestions": ["改进建议1", "改进建议2"]\n'
                "}}\n\n"
                "**评分标准（严格执行）：**\n"
                "每个维度 1-10 分，参考以下指南：\n"
                "| 分数 | 含义 |\n"
                "|------|------|\n"
                "| 9-10 | 优秀 — 完全满足要求，无可挑剔 |\n"
                "| 7-8  | 良好 — 满足要求，有少量可改进空间 |\n"
                "| 5-6  | 及格 — 基本满足但存在明显不足 |\n"
                "| 3-4  | 较差 — 多项未达标 |\n"
                "| 1-2  | 很差 — 几乎未满足任何要求 |\n\n"
                "**维度定义：**\n"
                "- structure（结构）：标题、摘要、正文、结论、参考文献是否完整，段落组织是否合理。\n"
                "  ✅ 好：标题准确反映主题，摘要概括核心发现，正文分段清晰，结论总结到位，参考文献独立成节\n"
                "  ❌ 差：缺少摘要或结论，各节无标题，段落过长无分段，参考文献缺失\n"
                "- depth（深度）：是否有具体数据、案例、引用支撑，是否避免空泛概括。\n"
                "  ✅ 好：每节包含至少 1 个具体数据或案例，用事实而非泛泛而谈支撑观点\n"
                '  ❌ 差：大量「前景广阔」「具有重要意义」「受到广泛关注」等空泛表述\n'
                "- citation_accuracy（引用准确性）：引用格式是否正确，正文引用与参考文献是否对应。\n"
                "  ✅ 好：正文用 [1] [2] 编号引用，参考文献列出 [来源标题](完整URL)，来源真实可查\n"
                '  ❌ 差：正文引用编号与参考文献不匹配，来源 URL 缺失或明显伪造，正文出现「[来源1]」\n'
                "- readability（可读性）：语言是否流畅，排版是否清晰，是否使用表格/列表增强可读性。\n"
                "  ✅ 好：语言简洁正式（无口语），适当使用列表/表格呈现对比数据，引用块标注重要引用\n"
                "  ❌ 差：长段落连续超过 300 字无分段，通篇无列表/表格等辅助结构\n"
                "- completeness（完整性）：是否覆盖所有子任务发现，结论是否总结了核心发现和局限性。\n"
                "  ✅ 好：正文覆盖每个子任务的关键发现，结论包含核心总结、研究局限性和未来方向\n"
                "  ❌ 差：部分子任务的分析未出现在报告中，结论只重复摘要内容\n\n"
                "overall_score 综合上述维度加权后取整数（四舍五入）。\n\n"
                "**优点/不足/改进建议规则：**\n"
                '  - strengths：列出 1-3 个具体的优点，描述格式「XX做得好：（具体说明）」\n'
                '  - weaknesses：列出 1-3 个具体不足，描述格式「XX不足：（具体说明）」\n'
                "  - suggestions：列出 1-3 个可操作的改进建议\n\n"
                "**反例（违反即不合格）：**\n"
                '❌ 输出带 markdown 代码块的 JSON\n'
                '❌ 评分理由空泛：「整体质量不错」「还需要加强」\n'
                '❌ 所有维度给相同分数\n'
                '❌ 不足和建议内容雷同',
            ),
            (
                "human",
                "研究主题：{topic}\n\n研究报告：\n{report}\n\n请对该报告进行质量评审，严格按照上述要求输出 JSON。",
            ),
        ])
        self.report_critic_chain = self.report_critic_prompt | self.llm | StrOutputParser()

        self.rewrite_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个研究报告撰写专家。根据评审反馈对研究报告进行重写改进。\n\n"
                "**要求（严格执行）：**\n"
                "- 保留原有所有正确的事实、数据、引用和参考文献，**不得修改或删除**\n"
                "- 重点改进评审中指出的不足，采纳改进建议\n"
                "- 维持 Markdown 格式\n"
                "- 保持 1500-3000 字的篇幅\n"
                "**引用规则（违反即不合格）：**\n"
                '✅ 正文用 `[1]` 放在事实陈述句末即可\n'
                '✅ 例："据估计全球碳市场价值已超过 9000 亿美元[1]"\n'
                '✅ 多个来源并列用逗号分隔，如"...[1][2]" 或 "...[1,2]"\n'
                '❌ 禁止："根据文献[1]指出"、"文献显示"、"研究表明"、"有文献提到"\n'
                '❌ 禁止正文中出现任何超链接 `[文字](URL)`\n'
                '❌ 禁止出现"[来源1]"、"[1]指出"等引用在前的方式\n\n'
                "- 不要改变原文的引用编号方式（保持 [1] [2] 等编号不变）\n"
                "- 如果评审指出结构问题（如缺少摘要、结论），必须补充完整\n"
                "- 如果评审指出引用问题（如格式不规范、编号不匹配），必须修正\n"
                "- 未经评审指出的部分尽量保持原样，不做无谓的改动",
            ),
            (
                "human",
                "研究主题：{topic}\n\n当前报告：\n{report}\n\n评审反馈：\n{critic_feedback}\n\n请根据上述反馈对报告进行重写改进。",
            ),
        ])
        self.rewrite_chain = self.rewrite_prompt | self.llm | StrOutputParser()

    async def acritic_subtask_summary(self, title: str, query: str, summary: str) -> dict:
        response = await self.subtask_critic_chain.ainvoke({
            "title": title,
            "query": query,
            "summary": summary,
        })
        raw = response.strip()
        if "```" in raw:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if match:
                raw = match.group(1).strip()
        return _ensure_dimensions(_parse_json(raw), _SUBTASK_DIMENSIONS)

    async def acritic_report(self, topic: str, report: str) -> dict:
        response = await self.report_critic_chain.ainvoke({
            "topic": topic,
            "report": report,
        })
        raw = response.strip()
        if "```" in raw:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if match:
                raw = match.group(1).strip()
        return _ensure_dimensions(_parse_json(raw), _REPORT_DIMENSIONS)

    async def arewrite_report_stream(self, topic: str, report: str, critic_feedback: str):
        async for chunk in self.rewrite_chain.astream({
            "topic": topic,
            "report": report,
            "critic_feedback": critic_feedback,
        }):
            yield chunk
