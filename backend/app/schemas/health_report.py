"""健康报告 Pydantic 模式"""
from typing import Optional, Any, Dict

from pydantic import BaseModel, Field


class HealthReportCreate(BaseModel):
    report_name: str = Field(min_length=1, max_length=200)
    report_content: str = Field(min_length=10)


class HealthReportResponse(BaseModel):
    id: int
    report_name: str
    report_content: Optional[str] = None
    analysis_result: Optional[Dict[str, Any]] = None
    blood_glucose: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    uric_acid: Optional[float] = None
    cholesterol: Optional[float] = None
    triglycerides: Optional[float] = None
    created_at: Any

    class Config:
        from_attributes = True
