# ==================== api_client.py ====================
import json
import re
import time
from typing import Dict
import requests

from config import Config

class DeepSeekAPI:
    """DeepSeek API调用封装"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.API_KEY}",
            "Content-Type": "application/json"
        })
        
    def generate_prompt(self, prompt_type: str, text: str, context: Dict = None) -> str:
        if prompt_type == "parse":
            return self._create_parse_prompt(text)
        elif prompt_type == "evaluate":
            return self._create_evaluate_prompt(text, context)
        elif prompt_type == "report":
            return self._create_report_prompt(text, context)
        else:
            raise ValueError(f"未知的提示类型: {prompt_type}")
    
    def _create_parse_prompt(self, text: str) -> str:
        return f"""你是一位资深需求工程师，请解析以下需求文档片段：

提取所有需求条目并按类别分类：
- 功能需求
- 非功能需求
- 接口需求

输出JSON格式：
{{
  "requirements": [
    {{
      "id": "自动生成的唯一ID",
      "text": "需求描述文本",
      "type": "功能需求|非功能需求|接口需求",
      "elements": {{}}
    }}
  ]
}}

文档片段：
{text[:5000]}
请开始解析："""
    
    def _create_evaluate_prompt(self, text: str, context: Dict) -> str:
        criteria = context.get("criteria", self.config.COMPLETENESS_CRITERIA)
        return f"""评估需求条目的完整性。

完整性评估标准：
{json.dumps(criteria, indent=2, ensure_ascii=False)}

输入数据：
{text}

输出JSON格式：
{{
  "requirements": [
    {{
      "id": "需求ID",
      "completeness_score": 85.5,
      "missing_elements": ["验收标准", "异常处理"],
      "improvement_suggestions": ["具体建议"]
    }}
  ]
}}
请开始评估："""
    
    def call_api(self, prompt: str, retry_count: int = 0) -> Dict:
        payload = {
            "model": self.config.MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.TEMPERATURE,
            "top_p": self.config.TOP_P,
            "max_tokens": self.config.MAX_TOKENS,
            "stream": False
        }
        
        try:
            response = self.session.post(
                self.config.API_URL,
                json=payload,
                timeout=self.config.TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            
            if "choices" not in result or len(result["choices"]) == 0:
                raise ValueError("API响应格式错误")
            return result
            
        except requests.exceptions.RequestException as e:
            if retry_count < self.config.MAX_RETRIES:
                wait_time = 2 ** retry_count
                time.sleep(wait_time)
                return self.call_api(prompt, retry_count + 1)
            else:
                raise Exception(f"API调用失败，已达最大重试次数: {e}")
    
    def extract_content(self, response: Dict) -> str:
        try:
            content = response["choices"][0]["message"]["content"].strip()
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json_match.group()
            return content
        except Exception as e:
            raise Exception(f"内容提取失败: {e}")