import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))

    search_max_results: int = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
    search_proxy: str | None = os.getenv("SEARCH_PROXY") or None

    llm_timeout: int = int(os.getenv("LLM_TIMEOUT", "60"))

    subtask_count: int = int(os.getenv("SUBTASK_COUNT", "3"))


settings = Settings()
