from __future__ import annotations

import json
import re


# 从 LLM 回复中提取 JSON 代码块（兼容多种格式）
def extract_json_block(text: str) -> str:
    raw = text.strip()
    # 如果回复包含 markdown 代码块标记，提取其中的内容
    if "```" in raw:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            raw = match.group(1).strip()
    return raw


# 从文本中解析出第一个合法的 JSON 对象
def parse_json(text: str) -> dict:
    decoder = json.JSONDecoder()
    # 逐字符扫描，找到 JSON 起始位置
    for i, c in enumerate(text):
        if c in ('{', '['):
            try:
                obj, _ = decoder.raw_decode(text[i:])
                return obj
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError("No valid JSON found in response", text, 0)
