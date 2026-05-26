from __future__ import annotations

import os
from dotenv import load_dotenv

# 加载 .env 环境变量文件
load_dotenv()


class Settings:
    # OpenAI / LLM 相关配置
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")  # API 密钥（必填）
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")  # API 基础地址
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")  # 模型名称
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))  # 生成温度（0-2）

    # 搜索引擎配置
    search_max_results: int = int(os.getenv("SEARCH_MAX_RESULTS", "5"))  # 每子任务搜索结果上限
    search_proxy: str | None = os.getenv("SEARCH_PROXY") or None  # 搜索代理（国内需配置）

    # LLM 请求超时（秒）
    llm_timeout: int = int(os.getenv("LLM_TIMEOUT", "60"))

    # 默认子任务数量
    subtask_count: int = int(os.getenv("SUBTASK_COUNT", "3"))


# 全局单例
settings = Settings()
