#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码分析器模块
负责分析项目代码结构，识别功能实现位置，生成分析报告
"""

import os
import ast
import json
import re
from typing import Dict, List, Any, Optional, Tuple
import logging
from pathlib import Path
import subprocess

from openai import OpenAI
from utils.file_parser import FileParser
from utils.project_scanner import ProjectScanner

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """代码分析器主类"""
    
    def __init__(self):
        """初始化代码分析器"""
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
        self.file_parser = FileParser()
        self.project_scanner = ProjectScanner()
        
    def analyze_project(self, project_path: str, problem_description: str) -> Dict[str, Any]:
        """
        分析项目代码，生成功能定位报告
        
        Args:
            project_path: 项目代码路径
            problem_description: 功能需求描述
            
        Returns:
            包含分析结果的字典
        """
        logger.info(f"开始分析项目: {project_path}")
        
        try:
            # 1. 扫描项目结构
            project_structure = self.project_scanner.scan_project(project_path)
            
            # 2. 解析关键代码文件
            code_files = self._extract_code_files(project_path, project_structure)
            
            # 3. 分析项目类型和技术栈
            project_info = self._analyze_project_type(project_structure, code_files)
            
            # 4. 使用AI分析功能实现位置
            feature_analysis = self._analyze_features_with_ai(
                problem_description, 
                project_structure, 
                code_files,
                project_info
            )
            
            # 5. 生成执行建议
            execution_plan = self._generate_execution_plan(project_info, project_structure)
            
            # 6. 构建最终报告
            report = {
                "feature_analysis": feature_analysis,
                "execution_plan_suggestion": execution_plan,
                "project_info": project_info,
                "analysis_metadata": {
                    "total_files": len(code_files),
                    "project_type": project_info.get("type", "unknown"),
                    "main_language": project_info.get("main_language", "unknown")
                }
            }
            
            logger.info("项目分析完成")
            return report
            
        except Exception as e:
            logger.error(f"项目分析失败: {e}")
            raise
    
    def _extract_code_files(self, project_path: str, project_structure: Dict) -> Dict[str, str]:
        """提取并读取关键代码文件内容"""
        code_files = {}
        
        # 定义需要分析的文件扩展名
        code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.cs', 
            '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.vue',
            '.json', '.yaml', '.yml', '.md', '.txt'
        }
        
        for file_path in project_structure.get('files', []):
            file_ext = Path(file_path).suffix.lower()
            if file_ext in code_extensions:
                full_path = os.path.join(project_path, file_path)
                try:
                    content = self.file_parser.read_file_content(full_path)
                    if content and len(content.strip()) > 0:
                        code_files[file_path] = content
                except Exception as e:
                    logger.warning(f"读取文件失败 {file_path}: {e}")
        
        logger.info(f"成功读取 {len(code_files)} 个代码文件")
        return code_files
    
    def _analyze_project_type(self, project_structure: Dict, code_files: Dict[str, str]) -> Dict[str, Any]:
        """分析项目类型和技术栈"""
        project_info = {
            "type": "unknown",
            "main_language": "unknown",
            "framework": "unknown",
            "package_managers": [],
            "entry_points": []
        }
        
        files = project_structure.get('files', [])
        
        # 检测包管理器和配置文件
        if 'package.json' in files:
            project_info["package_managers"].append("npm")
            project_info["main_language"] = "javascript"
            
            # 分析package.json内容
            package_content = code_files.get('package.json', '')
            if package_content:
                try:
                    package_data = json.loads(package_content)
                    deps = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
                    
                    # 检测框架
                    if 'react' in deps:
                        project_info["framework"] = "react"
                        project_info["type"] = "web_frontend"
                    elif 'vue' in deps:
                        project_info["framework"] = "vue"
                        project_info["type"] = "web_frontend"
                    elif 'express' in deps:
                        project_info["framework"] = "express"
                        project_info["type"] = "web_backend"
                    elif '@nestjs/core' in deps:
                        project_info["framework"] = "nestjs"
                        project_info["type"] = "web_backend"
                    elif 'graphql' in deps or '@apollo/server' in deps:
                        project_info["type"] = "graphql_api"
                        
                except json.JSONDecodeError:
                    pass
        
        if 'requirements.txt' in files or 'pyproject.toml' in files or 'setup.py' in files:
            project_info["package_managers"].append("pip")
            project_info["main_language"] = "python"
            
            # 检测Python框架
            req_content = code_files.get('requirements.txt', '') + code_files.get('pyproject.toml', '')
            if 'django' in req_content.lower():
                project_info["framework"] = "django"
                project_info["type"] = "web_backend"
            elif 'flask' in req_content.lower():
                project_info["framework"] = "flask"
                project_info["type"] = "web_backend"
            elif 'fastapi' in req_content.lower():
                project_info["framework"] = "fastapi"
                project_info["type"] = "web_backend"
        
        if 'pom.xml' in files or 'build.gradle' in files:
            project_info["main_language"] = "java"
            project_info["package_managers"].append("maven" if 'pom.xml' in files else "gradle")
        
        if 'Cargo.toml' in files:
            project_info["main_language"] = "rust"
            project_info["package_managers"].append("cargo")
        
        if 'go.mod' in files:
            project_info["main_language"] = "go"
            project_info["package_managers"].append("go_modules")
        
        # 寻找入口点文件
        entry_candidates = ['main.py', 'app.py', 'server.py', 'index.js', 'main.js', 'app.js', 'server.js']
        for candidate in entry_candidates:
            if candidate in files:
                project_info["entry_points"].append(candidate)
        
        return project_info
    
    def _analyze_features_with_ai(self, problem_description: str, project_structure: Dict, 
                                 code_files: Dict[str, str], project_info: Dict) -> List[Dict[str, Any]]:
        """使用AI分析功能实现位置"""
        
        # 构建代码上下文，限制长度避免token超限
        code_context = self._build_code_context(code_files, max_length=15000)
        
        # 构建分析提示
        prompt = self._build_analysis_prompt(
            problem_description, 
            project_structure, 
            code_context, 
            project_info
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的代码分析专家。请仔细分析提供的代码和需求，准确识别每个功能的实现位置。返回格式必须是有效的JSON。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            ai_response = response.choices[0].message.content
            logger.info("AI分析完成")
            
            # 解析AI返回的JSON
            try:
                # 提取JSON部分
                json_start = ai_response.find('[')
                json_end = ai_response.rfind(']') + 1
                if json_start != -1 and json_end != -1:
                    json_str = ai_response[json_start:json_end]
                    feature_analysis = json.loads(json_str)
                else:
                    # 如果没有找到数组，尝试解析整个响应
                    feature_analysis = json.loads(ai_response)
                
                return feature_analysis if isinstance(feature_analysis, list) else [feature_analysis]
                
            except json.JSONDecodeError as e:
                logger.error(f"AI返回的JSON格式错误: {e}")
                logger.error(f"AI原始响应: {ai_response}")
                
                # 返回基础分析结果
                return self._fallback_analysis(problem_description, code_files)
                
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            return self._fallback_analysis(problem_description, code_files)
    
    def _build_code_context(self, code_files: Dict[str, str], max_length: int = 15000) -> str:
        """构建代码上下文，控制长度"""
        context_parts = []
        current_length = 0
        
        # 优先包含重要文件
        priority_files = []
        regular_files = []
        
        for file_path, content in code_files.items():
            # 判断文件重要性
            if any(keyword in file_path.lower() for keyword in 
                   ['main', 'app', 'index', 'server', 'controller', 'service', 'resolver', 'router']):
                priority_files.append((file_path, content))
            else:
                regular_files.append((file_path, content))
        
        # 先处理优先文件
        for file_path, content in priority_files + regular_files:
            file_info = f"\n--- {file_path} ---\n{content[:2000]}{'...(truncated)' if len(content) > 2000 else ''}\n"
            
            if current_length + len(file_info) > max_length:
                break
                
            context_parts.append(file_info)
            current_length += len(file_info)
        
        return "".join(context_parts)
    
    def _build_analysis_prompt(self, problem_description: str, project_structure: Dict, 
                              code_context: str, project_info: Dict) -> str:
        """构建AI分析提示"""
        
        prompt = f"""
请分析以下项目代码，根据功能需求描述，准确识别每个功能的实现位置。

## 功能需求描述：
{problem_description}

## 项目信息：
- 项目类型: {project_info.get('type', 'unknown')}
- 主要语言: {project_info.get('main_language', 'unknown')}
- 框架: {project_info.get('framework', 'unknown')}
- 入口文件: {', '.join(project_info.get('entry_points', []))}

## 项目结构：
文件总数: {len(project_structure.get('files', []))}
主要目录: {', '.join(project_structure.get('directories', [])[:10])}

## 代码内容：
{code_context}

## 分析要求：
1. 仔细阅读功能需求，识别出需要实现的具体功能点
2. 对于每个功能点，在代码中找到对应的实现位置
3. 准确标注文件路径、函数名和行号范围
4. 特别关注GraphQL的resolver、mutation、query实现
5. 注意数据库操作、业务逻辑的实现位置

## 分析示例：
如果是GraphQL项目，请重点分析：
- Mutation resolvers（如createChannel, createMessage）
- Query resolvers（如channels, messages）
- 数据库操作函数
- Schema定义

## 返回格式：
请返回一个JSON数组，格式如下：
[
  {{
    "feature_description": "实现`具体功能名称`功能",
    "implementation_location": [
      {{
        "file": "文件路径",
        "function": "函数名或方法名",
        "lines": "起始行-结束行"
      }}
    ]
  }}
]

注意：
- 只返回JSON数组，不要包含其他文字说明
- 确保JSON格式正确
- 功能描述要具体明确，如"实现`创建频道`功能"
- 行号范围要尽量准确，基于代码内容估算
- 每个功能都要有对应的实现位置
"""
        
        return prompt
    
    def _fallback_analysis(self, problem_description: str, code_files: Dict[str, str]) -> List[Dict[str, Any]]:
        """当AI分析失败时的备用分析方法"""
        logger.info("使用备用分析方法")
        
        # 简单的关键词匹配分析
        features = []
        
        # 从需求描述中提取可能的功能关键词
        feature_keywords = re.findall(r'实现[`"]?([^`"，。]+)[`"]?功能', problem_description)
        
        for keyword in feature_keywords:
            implementation_locations = []
            
            # 在代码文件中搜索相关实现
            for file_path, content in code_files.items():
                if keyword.lower() in content.lower():
                    # 简单的函数匹配
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if keyword.lower() in line.lower() and ('def ' in line or 'function ' in line or 'class ' in line):
                            implementation_locations.append({
                                "file": file_path,
                                "function": line.strip(),
                                "lines": f"{i+1}-{i+5}"
                            })
            
            if implementation_locations:
                features.append({
                    "feature_description": f"实现`{keyword}`功能",
                    "implementation_location": implementation_locations
                })
        
        return features if features else [{
            "feature_description": "功能分析",
            "implementation_location": []
        }]
    
    def _generate_execution_plan(self, project_info: Dict, project_structure: Dict) -> str:
        """生成项目执行建议"""
        
        main_language = project_info.get('main_language', 'unknown')
        framework = project_info.get('framework', 'unknown')
        package_managers = project_info.get('package_managers', [])
        
        if main_language == 'javascript' and 'npm' in package_managers:
            if framework == 'nestjs':
                return "要执行此项目，应首先执行 `npm install` 安装依赖，然后执行 `npm run start:dev` 来启动开发服务器。如果是GraphQL API，通常可以在 http://localhost:3000/graphql 访问GraphQL Playground。"
            elif framework == 'react':
                return "要执行此项目，应首先执行 `npm install` 安装依赖，然后执行 `npm start` 来启动开发服务器。应用通常会在 http://localhost:3000 启动。"
            elif framework == 'express':
                return "要执行此项目，应首先执行 `npm install` 安装依赖，然后执行 `npm start` 或 `node server.js` 来启动服务器。"
            else:
                return "要执行此项目，应首先执行 `npm install` 安装依赖，然后根据package.json中的scripts执行相应的启动命令。"
        
        elif main_language == 'python':
            if framework == 'django':
                return "要执行此项目，应首先执行 `pip install -r requirements.txt` 安装依赖，然后执行 `python manage.py runserver` 来启动Django开发服务器。"
            elif framework == 'flask':
                return "要执行此项目，应首先执行 `pip install -r requirements.txt` 安装依赖，然后执行 `python app.py` 或 `flask run` 来启动Flask应用。"
            elif framework == 'fastapi':
                return "要执行此项目，应首先执行 `pip install -r requirements.txt` 安装依赖，然后执行 `uvicorn main:app --reload` 来启动FastAPI应用。"
            else:
                return "要执行此项目，应首先执行 `pip install -r requirements.txt` 安装依赖，然后执行主入口文件。"
        
        elif main_language == 'java':
            if 'maven' in package_managers:
                return "要执行此项目，应首先执行 `mvn clean install` 编译项目，然后执行 `mvn spring-boot:run` 或 `java -jar target/*.jar` 来启动应用。"
            elif 'gradle' in package_managers:
                return "要执行此项目，应首先执行 `./gradlew build` 编译项目，然后执行 `./gradlew bootRun` 来启动应用。"
        
        elif main_language == 'go':
            return "要执行此项目，应首先执行 `go mod tidy` 安装依赖，然后执行 `go run main.go` 来启动应用。"
        
        return "请根据项目的README文件或配置文件确定具体的执行方式。通常需要先安装依赖，然后执行主入口文件。"
