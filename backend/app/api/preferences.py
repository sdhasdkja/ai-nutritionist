"""口味偏好接口模块"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.recipe import TastePreference
from app.schemas.recipe import TastePreferenceCreate, TastePreferenceResponse

router = APIRouter(prefix="/preferences", tags=["口味偏好"])


@router.get("", response_model=List[TastePreferenceResponse])
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户口味偏好列表"""
    return db.query(TastePreference).filter(
        TastePreference.user_id == current_user.id,
    ).order_by(TastePreference.created_at.desc()).all()


@router.post("", response_model=TastePreferenceResponse)
def create_preference(
    data: TastePreferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加口味偏好"""
    # 避免完全重复的记录
    existing = db.query(TastePreference).filter(
        TastePreference.user_id == current_user.id,
        TastePreference.preference_type == data.preference_type,
        TastePreference.preference_value == data.preference_value,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该偏好已存在")

    preference = TastePreference(
        user_id=current_user.id,
        preference_type=data.preference_type,
        preference_value=data.preference_value,
    )
    db.add(preference)
    db.commit()
    db.refresh(preference)
    return preference


@router.delete("/{preference_id}")
def delete_preference(
    preference_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除口味偏好"""
    preference = db.query(TastePreference).filter(
        TastePreference.id == preference_id,
        TastePreference.user_id == current_user.id,
    ).first()

    if not preference:
        raise HTTPException(status_code=404, detail="偏好不存在")
    db.delete(preference)
    db.commit()
    return {"message": "删除成功"}
