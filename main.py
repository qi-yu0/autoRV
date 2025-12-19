# ==================== main.py ====================
import os
from pathlib import Path
from docx import Document

from config import Config
from validator import RequirementValidator

def create_sample_document(output_path: str = "示例需求文档.docx"):
    """创建示例需求文档"""
    content = """
# 需求规格说明书
## 项目名称：智能办公系统

### 1. 功能需求
1.1 用户登录功能
系统应支持用户使用用户名和密码登录。

1.2 文件上传功能
用户应能上传各种格式的文件。

### 2. 非功能需求
2.1 系统性能
系统应具有良好性能。

### 3. 接口需求
3.1 邮件通知接口
系统需要与邮件服务器交互。
"""
    
    doc = Document()
    doc.add_paragraph(content)
    doc.save(output_path)
    print(f"示例文档已创建: {output_path}")
    return output_path

def main():
    """主函数"""
    print("=== 需求完整性自动化验证系统 ===")
    
    # 配置
    config = Config()
    api_key = input("请输入DeepSeek API密钥（或留空使用环境变量）: ").strip()
    if api_key:
        config.API_KEY = api_key
    elif config.API_KEY == "your-api-key-here":
        print("错误: 未设置API密钥")
        return
    
    # 创建验证器
    validator = RequirementValidator(config)
    
    print("\n请选择模式:")
    print("1. 示例演示")
    print("2. 验证单个文档")
    print("3. 批量验证")
    
    choice = input("请输入选择: ").strip()
    
    if choice == "1":
        # 示例演示
        print("\n运行示例演示...")
        sample_path = create_sample_document()
        result = validator.validate_document(sample_path)
        
        print(f"\n验证完成!")
        print(f"文档名称: {result.document_name}")
        print(f"完整性得分: {result.completeness_score:.2f}%")
        print(f"总需求数: {result.total_requirements}")
        print(f"完整需求数: {result.complete_requirements}")
        print(f"报告已保存至: {config.OUTPUT_DIR}")
    
    elif choice == "2":
        # 单个文档验证
        doc_path = input("请输入文档路径: ").strip()
        if not os.path.exists(doc_path):
            print(f"文件不存在: {doc_path}")
            return
        
        result = validator.validate_document(doc_path)
        print(f"\n验证完成!")
        print(f"完整性得分: {result.completeness_score:.2f}%")
    
    elif choice == "3":
        # 批量验证
        input_dir = input("请输入文档目录（直接回车使用默认目录）: ").strip()
        if not input_dir:
            input_dir = config.INPUT_DIR
        
        if not os.path.exists(input_dir):
            os.makedirs(input_dir, exist_ok=True)
            create_sample_document(os.path.join(input_dir, "示例需求文档.docx"))
        
        results = validator.validate_batch(input_dir)
        print(f"\n批量验证完成!")
        print(f"共处理 {len(results)} 个文档")
    
    else:
        print("无效选择")

if __name__ == "__main__":
    main()