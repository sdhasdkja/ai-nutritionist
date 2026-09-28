"""营养知识库服务（ChromaDB + 百炼 text-embedding-v3）"""
import logging
from typing import List, Dict

import chromadb
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """营养知识库管理类"""

    _instance = None

    def __new__(cls):
        """单例：避免重复初始化 ChromaDB 客户端和 embedding 模型"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        # 初始化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            chunk_size=settings.EMBEDDING_BATCH_SIZE,  # 百炼 embedding 批量上限
            check_embedding_ctx_length=False,  # 发送原始字符串而非token数组（百炼不支持token输入）
        )
        self.collection_name = "nutrition_knowledge"
        self._initialized = True

    def get_or_create_collection(self):
        """获取或创建集合"""
        return self.client.get_or_create_collection(name=self.collection_name)

    def add_documents(self, documents: List[Dict]):
        """添加文档到知识库（按主键幂等：已存在的不重复添加）"""
        collection = self.get_or_create_collection()

        # 按自增偏移生成稳定 ID，避免重复导入
        existing = collection.count()
        docs_to_add = documents[existing:]
        if not docs_to_add:
            return

        ids = [str(existing + i) for i in range(len(docs_to_add))]
        texts = [doc["content"] for doc in docs_to_add]
        metadatas = [{"source": doc.get("source", ""), "category": doc.get("category", "")}
                     for doc in docs_to_add]

        # 生成嵌入向量
        embeddings = self.embeddings.embed_documents(texts)

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.info("知识库新增 %d 条文档", len(docs_to_add))

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """语义检索知识库"""
        collection = self.get_or_create_collection()
        if collection.count() == 0:
            return []

        # 生成查询嵌入
        query_embedding = self.embeddings.embed_query(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
        )

        documents = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                documents.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })

        return documents
