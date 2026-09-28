"""应用配置模块"""
import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    # 应用配置
    APP_NAME: str = "AI营养师Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:root@localhost:3306/ai_nutritionist?charset=utf8mb4"

    # JWT 配置
    SECRET_KEY: str = "ainutritionist-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时，方便开发调试

    # LLM 配置（阿里云百炼 OpenAI 兼容接口，默认读取环境变量 DASHSCOPE_API_KEY）
    LLM_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL: str = "qwen-plus"          # 食谱生成等多Agent工作流（保质量）
    LLM_CHAT_MODEL: str = "qwen-flash"    # 营养师问答（低延迟，价格约qwen-plus的1/10）
    VISION_MODEL: str = "qwen-vl-max"  # 体检报告照片识别

    # Embedding 配置（百炼 text-embedding-v3）
    EMBEDDING_MODEL: str = "text-embedding-v3"
    EMBEDDING_BATCH_SIZE: int = 10  # 百炼 /embeddings 接口单次批量上限

    # ChromaDB 配置
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
