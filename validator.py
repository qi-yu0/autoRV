# ==================== validator.py ====================
import os
import time
import hashlib
import json
import re
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from config import Config
from models import Requirement, DocumentSegment, ValidationResult
from preprocessor import DocumentPreprocessor
from api_client import DeepSeekAPI
from parser import ResultParser
from report_generator import ReportGenerator

class RequirementValidator:
    """需求完整性验证主控制器"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        
        self.preprocessor = DocumentPreprocessor(self.config.MAX_SEGMENT_LENGTH)
        self.api_client = DeepSeekAPI(self.config)
        self.parser = ResultParser(self.config.COMPLETENESS_CRITERIA)
        self.report_generator = ReportGenerator()
        
        os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.config.CACHE_DIR, exist_ok=True)
    
    def validate_document(self, file_path: str) -> ValidationResult:
        start_time = time.time()
        document_name = Path(file_path).name
        
        try:
            segments = self.preprocessor.process_document(file_path)
            all_requirements = []
            
            with ThreadPoolExecutor(max_workers=self.config.BATCH_SIZE) as executor:
                future_to_segment = {
                    executor.submit(self._process_segment, segment): segment
                    for segment in segments
                }
                
                for future in as_completed(future_to_segment):
                    segment = future_to_segment[future]
                    try:
                        segment_requirements = future.result()
                        for req in segment_requirements:
                            req.segment_id = segment.id
                        all_requirements.extend(segment_requirements)
                    except Exception as e:
                        print(f"片段处理失败 {segment.id}: {e}")
            
            evaluated_requirements = self._evaluate_requirements(all_requirements)
            result = self._calculate_results(
                document_name=document_name,
                requirements=evaluated_requirements,
                validation_time=time.time() - start_time
            )
            
            self._generate_reports(result, document_name)
            return result
            
        except Exception as e:
            raise Exception(f"文档验证失败 {document_name}: {e}")
    
    def validate_batch(self, input_dir: str = None) -> List[ValidationResult]:
        input_dir = input_dir or self.config.INPUT_DIR
        results = []
        
        supported_extensions = ['.pdf', '.doc', '.docx', '.txt']
        doc_files = []
        
        for ext in supported_extensions:
            doc_files.extend(Path(input_dir).glob(f"*{ext}"))
            doc_files.extend(Path(input_dir).glob(f"*{ext.upper()}"))
        
        if not doc_files:
            print(f"未找到文档文件: {input_dir}")
            return results
        
        for doc_file in doc_files:
            try:
                result = self.validate_document(str(doc_file))
                results.append(result)
            except Exception as e:
                print(f"文档验证失败 {doc_file}: {e}")
        
        if results:
            self._generate_batch_report(results)
        
        return results
    
    def _process_segment(self, segment: DocumentSegment) -> List[Requirement]:
        try:
            cache_key = f"{segment.id}_{hashlib.md5(segment.text.encode()).hexdigest()[:16]}"
            cache_file = Path(self.config.CACHE_DIR) / f"{cache_key}.json"
            
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    return [Requirement(**data) for data in cached_data]
            
            parse_prompt = self.api_client.generate_prompt("parse", segment.text)
            parse_response = self.api_client.call_api(parse_prompt)
            parse_content = self.api_client.extract_content(parse_response)
            
            requirements = self.parser.parse_requirements(parse_content)
            
            if requirements:
                eval_context = {
                    "criteria": self.config.COMPLETENESS_CRITERIA,
                    "requirements": [
                        {
                            "id": req.id,
                            "text": req.text,
                            "type": req.req_type.value,
                            "elements": req.elements
                        }
                        for req in requirements
                    ]
                }
                
                eval_prompt = self.api_client.generate_prompt(
                    "evaluate", 
                    json.dumps(eval_context, ensure_ascii=False),
                    eval_context
                )
                
                eval_response = self.api_client.call_api(eval_prompt)
                eval_content = self.api_client.extract_content(eval_response)
                requirements = self.parser.parse_evaluation(eval_content, requirements)
            
            cache_data = [
                {
                    "id": req.id,
                    "text": req.text,
                    "req_type": req.req_type.value,
                    "segment_id": req.segment_id,
                    "position": req.position,
                    "elements": req.elements,
                    "completeness_score": req.completeness_score,
                    "missing_elements": req.missing_elements,
                    "improvement_suggestions": req.improvement_suggestions
                }
                for req in requirements
            ]
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            return requirements
            
        except Exception as e:
            print(f"片段处理失败 {segment.id}: {e}")
            return []
    
    def _evaluate_requirements(self, requirements: List[Requirement]) -> List[Requirement]:
        for requirement in requirements:
            expected_elements = self.config.COMPLETENESS_CRITERIA.get(
                requirement.req_type.value, []
            )
            
            missing_from_config = [
                elem for elem in expected_elements 
                if elem not in requirement.elements
            ]
            
            requirement.missing_elements = list(set(
                requirement.missing_elements + missing_from_config
            ))
            
            if expected_elements:
                requirement.completeness_score = max(
                    requirement.completeness_score,
                    (1 - len(missing_from_config) / len(expected_elements)) * 100
                )
        return requirements
    
    def _calculate_results(self, document_name: str, 
                          requirements: List[Requirement],
                          validation_time: float) -> ValidationResult:
        complete_requirements = [
            req for req in requirements 
            if not req.missing_elements
        ]
        
        if requirements:
            overall_score = sum(req.completeness_score for req in requirements) / len(requirements)
        else:
            overall_score = 0.0
        
        missing_by_type = {}
        for req in requirements:
            if req.missing_elements:
                req_type = req.req_type.value
                if req_type not in missing_by_type:
                    missing_by_type[req_type] = {}
                for elem in req.missing_elements:
                    missing_by_type[req_type][elem] = missing_by_type[req_type].get(elem, 0) + 1
        
        doc_id = hashlib.md5(f"{document_name}_{time.time()}".encode()).hexdigest()[:12]
        
        return ValidationResult(
            document_id=doc_id,
            document_name=document_name,
            total_requirements=len(requirements),
            complete_requirements=len(complete_requirements),
            completeness_score=overall_score,
            missing_elements_by_type=missing_by_type,
            requirements_details=requirements,
            validation_time=validation_time,
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )
    
    def _generate_reports(self, result: ValidationResult, base_name: str):
        base_name_clean = re.sub(r'[^\w\-_\. ]', '_', base_name)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        word_path = Path(self.config.OUTPUT_DIR) / f"{base_name_clean}_验证报告_{timestamp}.docx"
        self.report_generator.generate_word_report(result, str(word_path))
        
        excel_path = Path(self.config.OUTPUT_DIR) / f"{base_name_clean}_详细清单_{timestamp}.xlsx"
        self.report_generator.generate_excel_report(result, str(excel_path))
    
    def _generate_batch_report(self, results: List[ValidationResult]):
        if not results:
            return
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        batch_path = Path(self.config.OUTPUT_DIR) / f"批量验证汇总_{timestamp}.xlsx"
        
        summary_data = []
        for result in results:
            summary_data.append({
                "文档名称": result.document_name,
                "总需求数": result.total_requirements,
                "完整需求数": result.complete_requirements,
                "完整性得分": f"{result.completeness_score:.2f}%",
                "验证耗时(秒)": f"{result.validation_time:.2f}",
                "生成时间": result.generated_at
            })
        
        df = pd.DataFrame(summary_data)
        with pd.ExcelWriter(str(batch_path), engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='批量汇总', index=False)