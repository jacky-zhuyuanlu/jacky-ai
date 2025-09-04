#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试生成器模块
负责根据代码分析结果生成单元测试，并执行验证（加分项功能）
"""

import os
import json
import subprocess
import tempfile
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger(__name__)

class TestGenerator:
    """测试代码生成器和验证器"""
    
    def __init__(self):
        """初始化测试生成器"""
        # 初始化OpenAI客户端，支持自定义base_url和模型
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("未设置OPENAI_API_KEY环境变量")
        
        base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    def generate_and_verify_tests(self, project_path: str, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成测试代码并执行验证
        
        Args:
            project_path: 项目代码路径
            analysis_result: 代码分析结果
            
        Returns:
            包含测试代码和执行结果的字典
        """
        logger.info("开始生成功能验证测试")
        
        try:
            # 1. 分析项目类型，确定测试策略
            project_info = analysis_result.get('project_info', {})
            test_strategy = self._determine_test_strategy(project_info)
            
            # 2. 生成测试代码
            test_code = self._generate_test_code(analysis_result, test_strategy, project_path)
            
            # 3. 执行测试（如果可能）
            execution_result = self._execute_tests(test_code, project_path, test_strategy)
            
            return {
                "generated_test_code": test_code,
                "execution_result": execution_result,
                "test_strategy": test_strategy
            }
            
        except Exception as e:
            logger.error(f"测试生成和验证失败: {e}")
            return {
                "generated_test_code": "",
                "execution_result": {
                    "tests_passed": False,
                    "log": f"测试生成失败: {str(e)}"
                },
                "test_strategy": "unknown"
            }
    
    def _determine_test_strategy(self, project_info: Dict[str, Any]) -> str:
        """确定测试策略"""
        project_type = project_info.get('type', 'unknown')
        framework = project_info.get('framework', 'unknown')
        main_language = project_info.get('main_language', 'unknown')
        
        if project_type == 'graphql_api' or framework == 'nestjs':
            return 'graphql_api_test'
        elif project_type == 'web_backend' and main_language == 'javascript':
            return 'nodejs_api_test'
        elif project_type == 'web_backend' and main_language == 'python':
            return 'python_api_test'
        elif project_type == 'web_frontend':
            return 'frontend_component_test'
        else:
            return 'generic_function_test'
    
    def _generate_test_code(self, analysis_result: Dict[str, Any], test_strategy: str, project_path: str) -> str:
        """使用AI生成测试代码"""
        
        # 构建测试生成提示
        prompt = self._build_test_generation_prompt(analysis_result, test_strategy, project_path)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的测试工程师。请根据代码分析结果生成完整的、可执行的测试代码。测试代码应该能够验证所有主要功能是否正常工作。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=3000
            )
            
            test_code = response.choices[0].message.content
            
            # 清理和格式化测试代码
            test_code = self._clean_test_code(test_code)
            
            logger.info("测试代码生成完成")
            return test_code
            
        except Exception as e:
            logger.error(f"AI生成测试代码失败: {e}")
            return self._generate_fallback_test_code(analysis_result, test_strategy)
    
    def _build_test_generation_prompt(self, analysis_result: Dict[str, Any], test_strategy: str, project_path: str) -> str:
        """构建测试生成提示"""
        
        feature_analysis = analysis_result.get('feature_analysis', [])
        project_info = analysis_result.get('project_info', {})
        execution_plan = analysis_result.get('execution_plan_suggestion', '')
        
        # 读取项目配置文件以了解依赖
        config_info = self._read_project_config(project_path)
        
        prompt = f"""
请根据以下代码分析结果生成完整的功能验证测试代码。

## 项目信息：
- 项目类型: {project_info.get('type', 'unknown')}
- 主要语言: {project_info.get('main_language', 'unknown')}
- 框架: {project_info.get('framework', 'unknown')}
- 测试策略: {test_strategy}

## 功能分析结果：
{json.dumps(feature_analysis, ensure_ascii=False, indent=2)}

## 执行建议：
{execution_plan}

## 项目配置信息：
{config_info}

## 测试要求：
1. 根据测试策略 "{test_strategy}" 生成相应的测试代码
2. 测试代码应该能够验证所有已识别的功能
3. 包含必要的依赖导入和配置
4. 测试代码应该是完整的、可执行的
5. 包含适当的断言和错误处理

## 针对不同策略的具体要求：

### 如果是 graphql_api_test：
- 生成GraphQL查询和变更测试
- 使用supertest或类似工具进行HTTP测试
- 测试主要的GraphQL操作

### 如果是 nodejs_api_test：
- 生成REST API测试
- 使用supertest、jest或mocha
- 测试主要的API端点

### 如果是 python_api_test：
- 生成Python API测试
- 使用pytest、requests或unittest
- 测试主要的API端点

### 如果是 frontend_component_test：
- 生成组件测试
- 使用Jest、React Testing Library或Vue Test Utils
- 测试主要的UI组件功能

### 如果是 generic_function_test：
- 生成通用函数测试
- 根据主要语言选择合适的测试框架
- 测试主要的业务逻辑函数

请只返回测试代码，不要包含其他说明文字。
"""
        
        return prompt
    
    def _read_project_config(self, project_path: str) -> str:
        """读取项目配置信息"""
        config_info = []
        
        # 常见配置文件
        config_files = ['package.json', 'requirements.txt', 'pyproject.toml', 'pom.xml', 'Cargo.toml']
        
        for config_file in config_files:
            config_path = os.path.join(project_path, config_file)
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        config_info.append(f"--- {config_file} ---\n{content[:1000]}{'...(truncated)' if len(content) > 1000 else ''}")
                except Exception as e:
                    logger.warning(f"读取配置文件失败 {config_file}: {e}")
        
        return '\n\n'.join(config_info) if config_info else "未找到配置文件"
    
    def _clean_test_code(self, test_code: str) -> str:
        """清理和格式化测试代码"""
        # 移除markdown代码块标记
        if '```' in test_code:
            lines = test_code.split('\n')
            cleaned_lines = []
            in_code_block = False
            
            for line in lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                if in_code_block or not line.strip().startswith('```'):
                    cleaned_lines.append(line)
            
            test_code = '\n'.join(cleaned_lines)
        
        return test_code.strip()
    
    def _generate_fallback_test_code(self, analysis_result: Dict[str, Any], test_strategy: str) -> str:
        """生成备用测试代码"""
        logger.info("生成备用测试代码")
        
        project_info = analysis_result.get('project_info', {})
        main_language = project_info.get('main_language', 'javascript')
        
        if main_language == 'javascript':
            return self._generate_javascript_fallback_test(analysis_result)
        elif main_language == 'python':
            return self._generate_python_fallback_test(analysis_result)
        else:
            return "// 无法生成测试代码：不支持的语言类型"
    
    def _generate_javascript_fallback_test(self, analysis_result: Dict[str, Any]) -> str:
        """生成JavaScript备用测试代码"""
        return """
const request = require('supertest');
const assert = require('assert');

describe('API功能测试', () => {
  const server = 'http://localhost:3000';
  
  it('应用启动测试', async () => {
    try {
      const response = await request(server).get('/');
      console.log('服务器响应状态:', response.status);
      assert(response.status < 500, '服务器应该正常响应');
    } catch (error) {
      console.log('连接测试失败:', error.message);
      assert(false, '无法连接到服务器');
    }
  });
  
  // 根据分析结果添加更多测试...
});
"""
    
    def _generate_python_fallback_test(self, analysis_result: Dict[str, Any]) -> str:
        """生成Python备用测试代码"""
        return """
import requests
import pytest
import json

class TestAPI:
    base_url = 'http://localhost:8000'
    
    def test_server_health(self):
        '''测试服务器健康状态'''
        try:
            response = requests.get(f'{self.base_url}/')
            print(f'服务器响应状态: {response.status_code}')
            assert response.status_code < 500, '服务器应该正常响应'
        except requests.exceptions.ConnectionError:
            print('连接测试失败：无法连接到服务器')
            pytest.fail('无法连接到服务器')
    
    # 根据分析结果添加更多测试...

if __name__ == '__main__':
    pytest.main([__file__])
"""
    
    def _execute_tests(self, test_code: str, project_path: str, test_strategy: str) -> Dict[str, Any]:
        """执行测试代码"""
        logger.info("开始执行测试代码")
        
        try:
            # 创建临时测试文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js' if 'javascript' in test_strategy else '.py', 
                                           delete=False, encoding='utf-8') as test_file:
                test_file.write(test_code)
                test_file_path = test_file.name
            
            # 根据测试策略执行测试
            if 'javascript' in test_strategy or 'nodejs' in test_strategy or 'graphql' in test_strategy:
                return self._execute_javascript_tests(test_file_path, project_path)
            elif 'python' in test_strategy:
                return self._execute_python_tests(test_file_path, project_path)
            else:
                return {
                    "tests_passed": False,
                    "log": "不支持的测试策略，无法执行测试"
                }
                
        except Exception as e:
            logger.error(f"执行测试失败: {e}")
            return {
                "tests_passed": False,
                "log": f"测试执行失败: {str(e)}"
            }
        finally:
            # 清理临时文件
            try:
                if 'test_file_path' in locals():
                    os.unlink(test_file_path)
            except:
                pass
    
    def _execute_javascript_tests(self, test_file_path: str, project_path: str) -> Dict[str, Any]:
        """执行JavaScript测试"""
        try:
            # 检查是否有package.json和node_modules
            package_json_path = os.path.join(project_path, 'package.json')
            node_modules_path = os.path.join(project_path, 'node_modules')
            
            if not os.path.exists(package_json_path):
                return {
                    "tests_passed": False,
                    "log": "未找到package.json文件，无法执行JavaScript测试"
                }
            
            # 如果没有node_modules，尝试安装依赖
            if not os.path.exists(node_modules_path):
                logger.info("安装npm依赖...")
                install_result = subprocess.run(
                    ['npm', 'install'],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if install_result.returncode != 0:
                    return {
                        "tests_passed": False,
                        "log": f"npm install失败: {install_result.stderr}"
                    }
            
            # 执行测试
            test_result = subprocess.run(
                ['npx', 'mocha', test_file_path, '--timeout', '10000'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "tests_passed": test_result.returncode == 0,
                "log": test_result.stdout + test_result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "tests_passed": False,
                "log": "测试执行超时"
            }
        except Exception as e:
            return {
                "tests_passed": False,
                "log": f"JavaScript测试执行失败: {str(e)}"
            }
    
    def _execute_python_tests(self, test_file_path: str, project_path: str) -> Dict[str, Any]:
        """执行Python测试"""
        try:
            # 检查是否有requirements.txt
            requirements_path = os.path.join(project_path, 'requirements.txt')
            
            if os.path.exists(requirements_path):
                logger.info("安装Python依赖...")
                install_result = subprocess.run(
                    ['pip', 'install', '-r', 'requirements.txt'],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if install_result.returncode != 0:
                    logger.warning(f"pip install警告: {install_result.stderr}")
            
            # 执行测试
            test_result = subprocess.run(
                ['python', test_file_path],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "tests_passed": test_result.returncode == 0,
                "log": test_result.stdout + test_result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "tests_passed": False,
                "log": "测试执行超时"
            }
        except Exception as e:
            return {
                "tests_passed": False,
                "log": f"Python测试执行失败: {str(e)}"
            }
