"""食谱接口模块"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.health_report import HealthReport
from app.models.recipe import Recipe, TastePreference
from app.schemas.recipe import RecipeResponse, RecipeGenerate
from app.agents.workflow import NutritionAgentWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recipes", tags=["食谱"])


@router.post("/generate", response_model=RecipeResponse)
def generate_recipe(
    generate_data: RecipeGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI生成个性化食谱（多Agent工作流，耗时约1-3分钟）"""
    # 获取健康报告
    health_report = db.query(HealthReport).filter(
        HealthReport.id == generate_data.health_report_id,
        HealthReport.user_id == current_user.id,
    ).first()

    if not health_report:
        raise HTTPException(status_code=404, detail="健康报告不存在")

    # 获取用户偏好
    preferences = db.query(TastePreference).filter(
        TastePreference.user_id == current_user.id,
    ).all()

    # 运行Agent工作流
    try:
        workflow = NutritionAgentWorkflow()
        result = workflow.run(
            health_report=health_report,
            preferences=preferences,
            user_info=current_user,
        )
    except Exception as e:
        logger.exception("食谱生成失败")
        raise HTTPException(status_code=502, detail=f"AI生成失败: {str(e)}")

    # 保存食谱
    recipe = Recipe(
        user_id=current_user.id,
        health_report_id=health_report.id,
        name=result["name"],
        description=result["description"],
        nutrition_info={
            **(result.get("nutrition_info") or {}),
            "review_feedback": result.get("review_feedback", ""),
            "iterations": result.get("iterations", 0),
        },
        total_calories=result.get("total_calories", 2000),
        status="active",
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("", response_model=List[RecipeResponse])
def get_recipes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的食谱列表"""
    return db.query(Recipe).filter(
        Recipe.user_id == current_user.id,
    ).order_by(Recipe.created_at.desc()).all()


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个食谱详情"""
    recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id,
        Recipe.user_id == current_user.id,
    ).first()

    if not recipe:
        raise HTTPException(status_code=404, detail="食谱不存在")
    return recipe


@router.delete("/{recipe_id}")
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除食谱"""
    recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id,
        Recipe.user_id == current_user.id,
    ).first()

    if not recipe:
        raise HTTPException(status_code=404, detail="食谱不存在")
    db.delete(recipe)
    db.commit()
    return {"message": "删除成功"}
