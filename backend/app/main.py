"""FastAPI 主应用"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, users, health_reports, recipes, preferences, chat

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表 + 播种知识库"""
    # 创建数据库表（幂等）
    Base.metadata.create_all(bind=engine)

    # 播种营养知识库（调用百炼 embedding 接口，失败不阻塞启动）
    try:
        from app.services.knowledge_base import KnowledgeBase
        from knowledge_base.default_data import DEFAULT_DOCUMENTS
        kb = KnowledgeBase()
        kb.add_documents(DEFAULT_DOCUMENTS)
        logger.info("营养知识库就绪，共 %d 条文档", kb.get_or_create_collection().count())
    except Exception as e:
        logger.warning("知识库播种失败（不影响启动，生成食谱前请检查网络/API Key）: %s", e)

    yield


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI营养师Agent - 智能个性化营养饮食管理系统",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(health_reports.router, prefix="/api")
app.include_router(recipes.router, prefix="/api")
app.include_router(preferences.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/")
def root():
    """根路径"""
    return {
        "message": "欢迎使用 AI营养师Agent",
        "version": settings.APP_VERSION,
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}
