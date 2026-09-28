"""食谱 Pydantic 模式"""
from typing import Optional, Any, Dict

from pydantic import BaseModel, Field


class RecipeGenerate(BaseModel):
    """生成食谱请求"""
    health_report_id: int


class RecipeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    nutrition_info: Optional[Dict[str, Any]] = None
    total_calories: int = 0
    status: str
    health_report_id: Optional[int] = None
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class TastePreferenceCreate(BaseModel):
    """创建口味偏好"""
    preference_type: str = Field(pattern="^(favorite_food|disliked_food|cuisine|allergy)$")
    preference_value: str = Field(min_length=1, max_length=200)


class TastePreferenceResponse(BaseModel):
    id: int
    preference_type: str
    preference_value: str
    created_at: Any

    class Config:
        from_attributes = True
