"""营养师对话接口模块（RAG 知识库问答）"""
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.services.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["营养师对话"])

# 系统提示词
SYSTEM_PROMPT = (
    "你是「AI营养师」，一位专业、亲切的营养健康顾问。"
    "回答时优先依据下面提供的【营养知识库】内容，做到科学、具体、可执行；"
    "如果问题超出知识库范围，可以基于通用营养学常识回答，但要说明这一点。"
    "涉及疾病治疗的问题，提醒用户咨询医生。回答使用中文，适当分点，控制在300字以内。"
)


def _build_llm() -> ChatOpenAI:
    """构建对话 LLM（问答用低延迟的 chat 专用模型）"""
    return ChatOpenAI(
        model=settings.LLM_CHAT_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=0.5,
        max_retries=2,
        streaming=True,
    )


def _prepare_messages(data: ChatRequest):
    """RAG 检索 + 组装消息（检索与组装复用）"""
    kb = KnowledgeBase()
    knowledge = kb.search(data.message, n_results=4)
    knowledge_block = "\n\n".join(
        f"【{k['metadata'].get('category', '通用')}】{k['content']}"
        for k in knowledge
    ) or "（本次未检索到直接相关知识）"

    sources = [ChatSource(category=k["metadata"].get("category", "通用"),
                          content=k["content"][:80] + "...") for k in knowledge]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT + "\n\n【营养知识库】\n" + knowledge_block),
    ]
    # 仅携带最近6轮，控制上下文长度
    for m in data.history[-6:]:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        else:
            messages.append(AIMessage(content=m.content))
    messages.append(HumanMessage(content=data.message))
    return messages, sources


@router.post("", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """基于营养知识库的智能问答（RAG，非流式）"""
    messages, sources = _prepare_messages(data)
    response = _build_llm().invoke(messages)
    logger.info("[营养师对话] 用户: %s... | 引用 %d 条知识", data.message[:20], len(sources))
    return ChatResponse(answer=response.content, sources=sources)


@router.post("/stream")
def chat_stream(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """流式问答（SSE）：先推送引用来源，再逐段推送回答内容"""
    messages, sources = _prepare_messages(data)
    llm = _build_llm()

    def event_stream():
        # 1) 元信息：引用的知识类目
        meta = {"type": "meta", "sources": [s.model_dump() for s in sources]}
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"
        # 2) 逐段回答
        try:
            for chunk in llm.stream(messages):
                if chunk.content:
                    delta = {"type": "delta", "content": chunk.content}
                    yield f"data: {json.dumps(delta, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("流式生成中断")
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e)}, ensure_ascii=False)}\n\n"
            return
        # 3) 结束标记
        yield "data: {\"type\": \"done\"}\n\n"
        logger.info("[营养师对话-流式] 用户: %s... | 引用 %d 条知识", data.message[:20], len(sources))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
