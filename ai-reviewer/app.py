#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI代码分析Agent主应用
功能：接收代码压缩包和需求描述，生成结构化的代码功能分析报告
"""

from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
import zipfile
import tempfile
import shutil
import json
from typing import Dict, List, Any
import logging
from datetime import datetime

from code_analyzer import CodeAnalyzer
from test_generator import TestGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB最大文件大小

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'zip'}

def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_zip_file(zip_path: str, extract_to: str) -> bool:
    """解压zip文件到指定目录"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        return True
    except Exception as e:
        logger.error(f"解压文件失败: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'AI Code Reviewer Agent'
    })

@app.route('/analyze', methods=['POST'])
def analyze_code():
    """
    主要的代码分析接口
    接收multipart/form-data请求，包含：
    - problem_description: 项目功能描述
    - code_zip: 代码压缩包
    """
    try:
        # 检查请求数据
        if 'problem_description' not in request.form:
            return jsonify({'error': '缺少problem_description字段'}), 400
        
        if 'code_zip' not in request.files:
            return jsonify({'error': '缺少code_zip文件'}), 400
        
        problem_description = request.form['problem_description']
        code_zip = request.files['code_zip']
        
        # 验证文件
        if code_zip.filename == '':
            return jsonify({'error': '未选择文件'}), 400
        
        if not allowed_file(code_zip.filename):
            return jsonify({'error': '不支持的文件格式，仅支持zip文件'}), 400
        
        logger.info(f"开始分析代码，需求描述长度: {len(problem_description)}")
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存上传的zip文件
            zip_filename = secure_filename(code_zip.filename)
            zip_path = os.path.join(temp_dir, zip_filename)
            code_zip.save(zip_path)
            
            # 解压代码文件
            extract_dir = os.path.join(temp_dir, 'extracted_code')
            os.makedirs(extract_dir, exist_ok=True)
            
            if not extract_zip_file(zip_path, extract_dir):
                return jsonify({'error': '解压代码文件失败'}), 500
            
            # 初始化代码分析器
            analyzer = CodeAnalyzer()
            
            # 执行代码分析
            analysis_result = analyzer.analyze_project(
                project_path=extract_dir,
                problem_description=problem_description
            )
            
            # 检查是否需要生成测试代码（加分项）
            include_tests = request.form.get('include_tests', 'false').lower() == 'true'
            
            if include_tests:
                logger.info("开始生成功能验证测试")
                test_generator = TestGenerator()
                test_result = test_generator.generate_and_verify_tests(
                    project_path=extract_dir,
                    analysis_result=analysis_result
                )
                analysis_result['functional_verification'] = test_result
            
            logger.info("代码分析完成")
            return jsonify(analysis_result)
            
    except Exception as e:
        logger.error(f"分析过程中发生错误: {e}")
        return jsonify({'error': f'分析失败: {str(e)}'}), 500

@app.route('/', methods=['GET'])
def index():
    """主页 - 显示Web界面"""
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"启动AI代码分析Agent服务，端口: {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
