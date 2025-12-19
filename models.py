# ==================== models.py ====================
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum

class RequirementType(Enum):
    FUNCTIONAL = "功能需求"
    NON_FUNCTIONAL = "非功能需求"
    INTERFACE = "接口需求"
    UNKNOWN = "未知类型"

@dataclass
class Requirement:
    """需求项数据模型"""
    id: str
    text: str
    req_type: RequirementType
    segment_id: str
    position: Tuple[int, int]
    
    elements: Dict[str, str] = None
    completeness_score: float = 0.0
    missing_elements: List[str] = None
    improvement_suggestions: List[str] = None
    
    def __post_init__(self):
        if self.elements is None:
            self.elements = {}
        if self.missing_elements is None:
            self.missing_elements = []
        if self.improvement_suggestions is None:
            self.improvement_suggestions = []

@dataclass
class DocumentSegment:
    """文档片段"""
    id: str
    text: str
    original_file: str
    page_range: Optional[Tuple[int, int]] = None
    requirements: List[Requirement] = None
    
    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []

@dataclass
class ValidationResult:
    """验证结果"""
    document_id: str
    document_name: str
    total_requirements: int
    complete_requirements: int
    completeness_score: float
    missing_elements_by_type: Dict[str, Dict[str, int]]
    requirements_details: List[Requirement]
    validation_time: float
    generated_at: str