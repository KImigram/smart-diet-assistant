"""Application configuration loaded from environment variables.

Real credentials belong in a local ``.env`` file or the process environment.
The repository intentionally contains no usable API key or database password.
"""

import os

from dotenv import load_dotenv


load_dotenv()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


# Database
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": _env_int("DB_PORT", 3306),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "nutritious_diet"),
    "charset": "utf8mb4",
}
DB_POOL_SIZE = _env_int("DB_POOL_SIZE", 5)


# Cloud LLM. Compatibility aliases are retained until llm_client is rewritten.
DEEPSEEK_API_KEY = os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
DEEPSEEK_BASE_URL = os.getenv(
    "LLM_BASE_URL", os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
)
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# Legacy RAG still uses Ollama until the LangChain pipeline replaces it.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


# MiniCPM dual-model recognition service
FINETUNE_API_URL = os.getenv(
    "FINETUNE_API_URL", "http://127.0.0.1:8002/recognize"
)
FINETUNE_MODEL = os.getenv("FINETUNE_MODEL", "minicpm-v-4.6")
FINETUNE_TIMEOUT_SECONDS = _env_int("FINETUNE_TIMEOUT_SECONDS", 300)


# Application
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = _env_int("APP_PORT", 8001)
DEFAULT_USER_ID = _env_int("DEFAULT_USER_ID", 1)

