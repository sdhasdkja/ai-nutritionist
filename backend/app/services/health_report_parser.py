"""体检报告解析服务

从体检报告文本中提取关键健康指标，并基于参考范围进行初步评估。
采用正则提取 + 规则评估，无需调用 LLM，结果确定且零成本。
"""
import re
from typing import Dict, Any, List, Optional


# 指标定义: (指标键, 中文名列表, 参考范围下限, 上限, 单位, 偏高建议, 偏低建议)
INDICATORS = [
    {
        "key": "blood_glucose",
        "names": ["空腹血糖", "空腹葡萄糖", "血糖", "GLU"],
        "low": 3.9, "high": 6.1, "unit": "mmol/L",
        "high_advice": "血糖偏高，建议控制精制碳水摄入，选择低GI主食，增加膳食纤维",
        "low_advice": "血糖偏低，注意规律进餐，避免长时间空腹",
    },
    {
        "key": "blood_pressure_systolic",
        "names": ["收缩压", "高压"],
        "low": 90, "high": 140, "unit": "mmHg",
        "high_advice": "收缩压偏高，建议低盐饮食（每日食盐<5g），控制体重",
        "low_advice": "收缩压偏低，注意充足饮水和均衡营养",
    },
    {
        "key": "blood_pressure_diastolic",
        "names": ["舒张压", "低压"],
        "low": 60, "high": 90, "unit": "mmHg",
        "high_advice": "舒张压偏高，建议减少钠盐摄入，增加钾摄入（新鲜蔬果）",
        "low_advice": "舒张压偏低，适当增加营养摄入",
    },
    {
        "key": "uric_acid",
        "names": ["尿酸", "血尿酸", "UA"],
        "low": 150, "high": 420, "unit": "μmol/L",
        "high_advice": "尿酸偏高，避免高嘌呤食物（动物内脏、海鲜、浓肉汤），戒酒，多饮水",
        "low_advice": "尿酸偏低，一般无需特殊处理",
    },
    {
        "key": "cholesterol",
        "names": ["总胆固醇", "胆固醇", "TC"],
        "low": 2.8, "high": 5.2, "unit": "mmol/L",
        "high_advice": "胆固醇偏高，减少饱和脂肪和反式脂肪摄入，增加燕麦、豆类等可溶性膳食纤维",
        "low_advice": "胆固醇偏低，注意均衡脂类营养摄入",
    },
    {
        "key": "triglycerides",
        "names": ["甘油三酯", "甘油三脂", "TG"],
        "low": 0.4, "high": 1.7, "unit": "mmol/L",
        "high_advice": "甘油三酯偏高，限制酒精、精制糖和油炸食品摄入，控制总热量",
        "low_advice": "甘油三酯偏低，一般无需特殊处理",
    },
]


class HealthReportParser:
    """体检报告解析器"""

    def parse(self, content: str) -> Dict[str, Any]:
        """解析报告内容，返回结构化分析结果

        返回格式:
        {
            "indicators": [ {key, name, value, unit, status, advice}, ... ],
            "abnormal_count": 2,
            "summary": "共提取 6 项指标，2 项异常（血糖偏高、尿酸偏高）",
            ...各指标数值平铺 (blood_glucose=6.5, ...)
        }
        """
        indicators: List[Dict[str, Any]] = []
        result: Dict[str, Any] = {}
        handled = set()

        # 血压组合格式优先："血压 128/82" 一次提取收缩压和舒张压
        bp = self._extract_blood_pressure(content)
        if bp:
            for key, (value, status, advice) in bp.items():
                ind_def = next(i for i in INDICATORS if i["key"] == key)
                indicators.append({
                    "key": key,
                    "name": ind_def["names"][0],
                    "value": value,
                    "unit": ind_def["unit"],
                    "status": status,
                    "advice": advice,
                })
                result[key] = value
                handled.add(key)

        for ind in INDICATORS:
            if ind["key"] in handled:
                continue

            value = self._extract_value(content, ind["names"])
            if value is not None:
                status, advice = self._assess(value, ind)
                indicators.append({
                    "key": ind["key"],
                    "name": ind["names"][0],
                    "value": value,
                    "unit": ind["unit"],
                    "status": status,
                    "advice": advice,
                })
                result[ind["key"]] = value

        abnormal = [i for i in indicators if i["status"] != "normal"]
        result["indicators"] = indicators
        result["abnormal_count"] = len(abnormal)

        if not indicators:
            result["summary"] = "未能从报告中识别出关键指标，请检查报告内容格式"
        elif not abnormal:
            result["summary"] = f"共提取 {len(indicators)} 项指标，全部正常"
        else:
            abnormal_desc = "、".join(f"{i['name']}{'偏高' if i['status'] == 'high' else '偏低'}" for i in abnormal)
            result["summary"] = f"共提取 {len(indicators)} 项指标，{len(abnormal)} 项异常（{abnormal_desc}）"

        return result

    @staticmethod
    def _extract_blood_pressure(content: str):
        """提取 "血压 128/82" / "血压：135/88mmHg" 组合格式"""
        match = re.search(r"血压\s*[:：]?\s*(\d{2,3})\s*/\s*(\d{2,3})", content)
        if not match:
            return None
        systolic, diastolic = int(match.group(1)), int(match.group(2))
        out = {}
        for key, value in [("blood_pressure_systolic", systolic), ("blood_pressure_diastolic", diastolic)]:
            ind = next(i for i in INDICATORS if i["key"] == key)
            status, advice = HealthReportParser._assess(value, ind)
            out[key] = (value, status, advice)
        return out

    @staticmethod
    def _extract_value(content: str, names: List[str]) -> Optional[float]:
        """从文本中提取指标数值，兼容常见体检报告格式：
        "空腹血糖 6.5 mmol/L"、"空腹血糖: 6.5"、"空腹血糖 结果 6.5" 等
        """
        for name in names:
            escaped = re.escape(name)
            patterns = [
                # 名称 + 可选分隔符 + 数字（跳过可能的"结果"字样）
                rf"{escaped}\s*[:：]?\s*(?:结果)?\s*[:：]?\s*(\d+(?:\.\d+)?)",
                # 数字 + 单位 + 名称（少见格式）
                rf"(\d+(?:\.\d+)?)\s*(?:mmol/L|μmol/L|mmHg|umol/L)?\s*{escaped}",
            ]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    try:
                        return float(match.group(1))
                    except ValueError:
                        continue
        return None

    @staticmethod
    def _assess(value: float, ind: Dict) -> tuple:
        """基于参考范围评估指标状态"""
        if value > ind["high"]:
            return "high", ind["high_advice"]
        if value < ind["low"]:
            return "low", ind["low_advice"]
        return "normal", "指标正常，保持当前饮食习惯"
