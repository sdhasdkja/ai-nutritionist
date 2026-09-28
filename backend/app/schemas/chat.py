"""对话 Pydantic 模式"""
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """单条对话消息"""
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(min_length=1, max_length=2000)
    history: List[ChatMessage] = Field(default_factory=list, max_length=20)


class ChatSource(BaseModel):
    """引用的知识来源"""
    category: str
    content: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource] = []
