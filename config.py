# ==================== config.py ====================
import os
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class Config:
    """系统配置"""
    # DeepSeek API配置
    API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
    API_URL: str = "https://api.deepseek.com/v1/chat/completions"
    MODEL_NAME: str = "deepseek-chat"
    
    # API调用参数
    TEMPERATURE: float = 0.2
    TOP_P: float = 0.9
    MAX_TOKENS: int = 2048
    TIMEOUT: int = 60
    
    # 文本处理配置
    MAX_SEGMENT_LENGTH: int = 30000
    BATCH_SIZE: int = 5
    MAX_RETRIES: int = 3
    
    # 路径配置
    INPUT_DIR: str = "input_docs"
    OUTPUT_DIR: str = "output_reports"
    CACHE_DIR: str = "cache"
    
    # 验证标准配置
    COMPLETENESS_CRITERIA: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.COMPLETENESS_CRITERIA is None:
            self.COMPLETENESS_CRITERIA = {
                "功能需求": ["触发条件", "处理逻辑", "输出结果", "验收标准", "异常处理"],
                "非功能需求": ["量化指标", "测量场景", "达标条件"],
                "接口需求": ["接口名称", "输入参数", "输出格式", "调用频率"]
            }