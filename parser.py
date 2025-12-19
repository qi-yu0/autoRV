# ==================== parser.py ====================
import json
import re
import hashlib
from typing import List, Dict, Optional

from models import Requirement, RequirementType

class ResultParser:
    """结果解析器"""
    
    def __init__(self, criteria: Dict[str, List[str]]):
        self.criteria = criteria
        
    def parse_requirements(self, api_response: str) -> List[Requirement]:
        try:
            data = json.loads(api_response)
            requirements = []
            
            for req_data in data.get("requirements", []):
                req_type = self._map_requirement_type(req_data.get("type", "未知类型"))
                
                requirement = Requirement(
                    id=req_data.get("id", f"REQ-{hashlib.md5(str(req_data).encode()).hexdigest()[:8]}"),
                    text=req_data.get("text", ""),
                    req_type=req_type,
                    segment_id="",
                    position=(0, 0),
                    elements=req_data.get("elements", {})
                )
                
                requirements.append(requirement)
            return requirements
            
        except json.JSONDecodeError:
            fixed_json = self._fix_json_format(api_response)
            if fixed_json:
                return self.parse_requirements(fixed_json)
            return []
    
    def parse_evaluation(self, api_response: str, requirements: List[Requirement]) -> List[Requirement]:
        try:
            data = json.loads(api_response)
            eval_map = {}
            
            for eval_data in data.get("requirements", []):
                req_id = eval_data.get("id")
                if req_id:
                    eval_map[req_id] = {
                        "score": eval_data.get("completeness_score", 0),
                        "missing": eval_data.get("missing_elements", []),
                        "suggestions": eval_data.get("improvement_suggestions", [])
                    }
            
            for requirement in requirements:
                if requirement.id in eval_map:
                    eval_result = eval_map[requirement.id]
                    requirement.completeness_score = eval_result["score"]
                    requirement.missing_elements = eval_result["missing"]
                    requirement.improvement_suggestions = eval_result["suggestions"]
            
            return requirements
        except Exception:
            return requirements
    
    def _map_requirement_type(self, type_str: str) -> RequirementType:
        type_str_lower = type_str.lower()
        if "功能" in type_str_lower:
            return RequirementType.FUNCTIONAL
        elif "非功能" in type_str_lower or "性能" in type_str_lower or "安全" in type_str_lower:
            return RequirementType.NON_FUNCTIONAL
        elif "接口" in type_str_lower:
            return RequirementType.INTERFACE
        else:
            return RequirementType.UNKNOWN
    
    def _fix_json_format(self, text: str) -> Optional[str]:
        try:
            fixed = text.replace("'", '"')
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            fixed = fixed.replace('\n', '\\n').replace('\t', '\\t')
            json.loads(fixed)
            return fixed
        except Exception:
            return None