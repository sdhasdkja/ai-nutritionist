"""AI Agent 工作流（LangGraph 多Agent协作）

流程: 健康分析 → 营养规划(RAG检索) → 食谱生成 → 质量审核
      审核不通过 → 回到食谱生成修改（最多3轮），通过 → 完成

适配说明：文档基于 langgraph 0.0.26，此处使用新版 API
（TypedDict 状态、START 入口、节点返回增量更新）。
提示词一律用模板变量传值（{xxx}），避免报告内容中的花括号被误解析。
"""
import json
import logging
import re
import time
from typing import Any, Dict, List, TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

from app.core.config import settings
from app.services.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

SEP = "=" * 64
SUB_SEP = "-" * 64


class WorkflowState(TypedDict, total=False):
    """工作流状态"""
    health_report_content: str   # 体检报告内容
    user_profile: str            # 用户基本信息描述
    preferences: str             # 口味偏好描述
    health_analysis: str         # 健康分析Agent输出
    nutrition_plan: str          # 营养规划Agent输出
    recipe_description: str      # 食谱生成Agent输出
    review_feedback: str         # 质量审核Agent输出
    iteration_count: int         # 当前迭代轮次
    review_passed: bool          # 是否通过审核


class NutritionAgentWorkflow:
    """AI营养师 Agent 工作流"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            temperature=0.7,
            max_retries=2,
        )
        self.knowledge_base = KnowledgeBase()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> Any:
        """构建 Agent 工作流"""
        workflow = StateGraph(WorkflowState)

        # 添加节点
        workflow.add_node("health_analysis", self._health_analysis_agent)
        workflow.add_node("nutrition_planning", self._nutrition_planning_agent)
        workflow.add_node("recipe_generation", self._recipe_generation_agent)
        workflow.add_node("quality_review", self._quality_review_agent)

        # 设置边：健康分析 → 营养规划 → 食谱生成 → 质量审核
        workflow.add_edge(START, "health_analysis")
        workflow.add_edge("health_analysis", "nutrition_planning")
        workflow.add_edge("nutrition_planning", "recipe_generation")
        workflow.add_edge("recipe_generation", "quality_review")
        workflow.add_conditional_edges(
            "quality_review",
            self._should_revise,
            {"revise": "recipe_generation", "complete": END},
        )

        return workflow.compile()

    # ---------- Agent 1: 健康分析 ----------

    def _health_analysis_agent(self, state: WorkflowState) -> Dict[str, Any]:
        """健康分析 Agent"""
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "你是一位专业的健康分析师。请根据体检报告分析用户的健康状况。"
             "要求：1) 逐项指出异常指标及其严重程度；2) 说明这些指标异常反映的健康风险；"
             "3) 输出200-400字的简明分析结论，供下游营养规划使用。不要输出寒暄。"),
            ("user",
             "用户基本信息：{user_profile}\n\n"
             "体检报告内容：\n{report_content}"),
        ])

        logger.info("[1/4 健康分析Agent] 开始 -> 解析体检报告，逐项评估异常指标...")
        t0 = time.time()
        response = self.llm.invoke(prompt.format_messages(
            user_profile=state.get("user_profile", "未提供"),
            report_content=state.get("health_report_content", "无"),
        ))
        logger.info("[1/4 健康分析Agent] 完成 (%.1fs) | 分析结论: %s",
                    time.time() - t0, response.content[:60].replace("\n", " "))
        return {"health_analysis": response.content, "iteration_count": 0}

    # ---------- Agent 2: 营养规划（RAG 检索） ----------

    def _nutrition_planning_agent(self, state: WorkflowState) -> Dict[str, Any]:
        """营养规划 Agent"""
        health_analysis = state.get("health_analysis", "")
        logger.info("[2/4 营养规划Agent] 开始 -> 语义检索营养知识库(RAG)...")
        t0 = time.time()

        # RAG 检索相关营养知识
        knowledge = self.knowledge_base.search(health_analysis, n_results=3)
        knowledge_text = "\n".join(f"- {k['content']}" for k in knowledge)
        hit_categories = "、".join(dict.fromkeys(
            k["metadata"].get("category", "?") for k in knowledge)) or "无"
        logger.info("[2/4 营养规划Agent] RAG命中知识: [%s]，结合健康分析制定营养方案...", hit_categories)

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "你是一位营养规划专家。请根据健康分析结果和营养学知识制定营养方案。"
             "要求明确：1) 每日总热量目标；2) 三大营养素分配（蛋白质/碳水/脂肪克数）；"
             "3) 需要限制和推荐的食物类别；4) 结合用户口味偏好调整。输出300-500字。"),
            ("user",
             "健康分析：\n{health_analysis}\n\n"
             "相关营养知识：\n{knowledge_text}\n\n"
             "用户偏好：{preferences}"),
        ])

        response = self.llm.invoke(prompt.format_messages(
            health_analysis=health_analysis,
            knowledge_text=knowledge_text or "无",
            preferences=state.get("preferences", "无特殊偏好"),
        ))
        logger.info("[2/4 营养规划Agent] 完成 (%.1fs) | 营养方案已生成: %s",
                    time.time() - t0, response.content[:60].replace("\n", " "))
        return {"nutrition_plan": response.content}

    # ---------- Agent 3: 食谱生成 ----------

    def _recipe_generation_agent(self, state: WorkflowState) -> Dict[str, Any]:
        """食谱生成 Agent"""
        iteration = state.get("iteration_count", 0)
        revise_hint = state.get("review_feedback", "")
        logger.info("[3/4 食谱生成Agent] 开始 -> 第%d轮生成%s...",
                    iteration + 1,
                    "（按上轮审核意见修订）" if iteration > 0 and revise_hint else "")
        t0 = time.time()

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "你是一位专业厨师和营养师。请根据营养方案生成一份详细的个性化食谱（一日三餐+可选加餐）。"
             "要求：1) 每餐列出菜品名称、主要食材和分量、简要做法；2) 估算每餐热量并汇总全天总热量；"
             "3) 严格符合营养方案中的限制（如低嘌呤、低GI、低盐）；4) 尊重用户口味偏好，严禁出现过敏食物。"
             "使用清晰的markdown结构输出，最后一行以「全天总热量：XXXXkcal」格式给出总热量。"),
            ("user",
             "营养方案：\n{nutrition_plan}\n\n"
             "用户偏好：{preferences}"),
        ])

        # 修订轮：附加审核意见
        if not revise_hint:
            revise_hint = state.get("review_feedback", "")

        response = self.llm.invoke(prompt.format_messages(
            nutrition_plan=state.get("nutrition_plan", ""),
            preferences=state.get("preferences", "无特殊偏好") + (
                f"\n\n【上一轮审核意见，请针对性改进】：\n{revise_hint}" if revise_hint else ""
            ),
        ))
        logger.info("[3/4 食谱生成Agent] 完成 (%.1fs) | 产出食谱 %d 字",
                    time.time() - t0, len(response.content))
        return {"recipe_description": response.content}

    # ---------- Agent 4: 质量审核 ----------

    def _quality_review_agent(self, state: WorkflowState) -> Dict[str, Any]:
        """质量审核 Agent"""
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "你是一位资深营养师，负责审核AI生成的食谱。请从以下维度审核："
             "1) 是否符合健康分析中的饮食限制；2) 营养素结构是否合理；"
             "3) 菜品是否可执行、食材是否常见；4) 是否尊重用户偏好、是否规避了过敏食物。"
             "审核通过时，回复以【PASS】开头并简述理由；"
             "不通过时，回复以【REVISE】开头并列出具体修改要求。"),
            ("user",
             "健康分析：\n{health_analysis}\n\n"
             "营养方案：\n{nutrition_plan}\n\n"
             "待审核食谱：\n{recipe}"),
        ])

        logger.info("[4/4 质量审核Agent] 开始 -> 四维度审核（健康契合/营养结构/可执行性/偏好尊重）...")
        t0 = time.time()
        response = self.llm.invoke(prompt.format_messages(
            health_analysis=state.get("health_analysis", ""),
            nutrition_plan=state.get("nutrition_plan", ""),
            recipe=state.get("recipe_description", ""),
        ))
        content = response.content
        passed = content.strip().startswith("【PASS】")

        iteration_count = state.get("iteration_count", 0) + 1
        # 通过，或已达最大轮次强制通过，避免无限循环
        review_passed = passed or iteration_count >= 3

        logger.info("[4/4 质量审核Agent] 完成 (%.1fs) | 第%d轮审核: %s | 意见: %s",
                    time.time() - t0, iteration_count,
                    "通过" if review_passed else "不通过，打回重写",
                    content[:50].replace("\n", " "))
        return {
            "review_feedback": content,
            "review_passed": review_passed,
            "iteration_count": iteration_count,
        }

    def _should_revise(self, state: WorkflowState) -> str:
        """判断是否需要修改"""
        if state.get("review_passed", False):
            return "complete"
        return "revise"

    # ---------- 对外入口 ----------

    def run(self, health_report, preferences, user_info) -> Dict[str, Any]:
        """运行工作流

        Args:
            health_report: HealthReport ORM 对象
            preferences: TastePreference ORM 对象列表
            user_info: User ORM 对象
        Returns:
            食谱结果字典 {name, description, nutrition_info, total_calories}
        """
        # 组装用户画像
        user_profile = self._build_user_profile(user_info)
        preference_text = self._build_preference_text(preferences)
        report_text = (
            f"报告名称：{health_report.report_name}\n"
            f"规则解析结果：{json.dumps(health_report.analysis_result, ensure_ascii=False) if health_report.analysis_result else '无'}\n"
            f"报告原文：\n{health_report.report_content or '无'}"
        )

        pref_values = [p.preference_value for p in (preferences or [])]
        logger.info(SEP)
        logger.info("[Agent工作流启动] 用户: %s | 画像: %s", getattr(user_info, "username", "?"), user_profile)
        logger.info("[Agent工作流启动] 报告: 《%s》 | 偏好: %s",
                    health_report.report_name, "、".join(pref_values) or "无")
        logger.info("[Agent工作流启动] 流程: 健康分析 -> 营养规划(RAG) -> 食谱生成 -> 质量审核")
        logger.info(SUB_SEP)
        t_start = time.time()

        initial_state: WorkflowState = {
            "health_report_content": report_text,
            "user_profile": user_profile,
            "preferences": preference_text,
        }

        result = self.workflow.invoke(initial_state)

        logger.info(SEP)
        logger.info("[Agent工作流完成] 质量审核%d轮%s | 总耗时 %.1fs | 食谱待入库",
                    result.get("iteration_count", 0),
                    "通过" if result.get("review_passed") else "(达上限)",
                    time.time() - t_start)
        logger.info(SEP)

        description = result.get("recipe_description", "")
        return {
            "name": "AI个性化食谱",
            "description": description,
            "nutrition_info": self._extract_nutrition(description),
            "total_calories": self._extract_calories(description),
            "review_feedback": result.get("review_feedback", ""),
            "iterations": result.get("iteration_count", 0),
        }

    @staticmethod
    def _build_user_profile(user_info) -> str:
        """构建用户画像描述"""
        parts = []
        if getattr(user_info, "age", None):
            parts.append(f"{user_info.age}岁")
        if getattr(user_info, "gender", None):
            gender_map = {"male": "男性", "female": "女性", "other": "其他"}
            raw = user_info.gender.value if hasattr(user_info.gender, "value") else user_info.gender
            parts.append(gender_map.get(raw, ""))
        if getattr(user_info, "height", None):
            parts.append(f"身高{user_info.height}cm")
        if getattr(user_info, "weight", None):
            parts.append(f"体重{user_info.weight}kg")
        return "、".join(p for p in parts if p) or "未提供"

    @staticmethod
    def _build_preference_text(preferences) -> str:
        """构建口味偏好描述"""
        type_map = {
            "favorite_food": "喜欢的食物",
            "disliked_food": "不喜欢的食物",
            "cuisine": "偏好菜系",
            "allergy": "过敏食物",
        }
        if not preferences:
            return "无特殊偏好"
        lines = []
        for p in preferences:
            label = type_map.get(p.preference_type, p.preference_type)
            lines.append(f"{label}: {p.preference_value}")
        return "；".join(lines)

    @staticmethod
    def _extract_calories(text: str) -> int:
        """从食谱文本中提取总热量"""
        patterns = [
            r"[总全]天?共?计?热量?[约：:\s]*(\d{3,4})\s*(?:kcal|千卡|大卡)",
            r"(\d{3,4})\s*(?:kcal|千卡|大卡)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 2000

    @staticmethod
    def _extract_nutrition(text: str) -> Dict[str, Any]:
        """从食谱文本中提取营养素信息"""
        nutrition = {}
        for key, label in [("protein", "蛋白质"), ("carbs", "碳水"), ("fat", "脂肪")]:
            match = re.search(rf"{label}\s*[约：:\s]*(\d+(?:\.\d+)?)\s*g", text)
            if match:
                nutrition[key] = float(match.group(1))
        nutrition["source"] = "AI估算"
        return nutrition
