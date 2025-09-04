#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目扫描器模块
负责扫描项目目录结构，识别项目类型和重要文件
"""

import os
import logging
from typing import Dict, List, Any, Set
from pathlib import Path

logger = logging.getLogger(__name__)

class ProjectScanner:
    """项目扫描器类"""
    
    def __init__(self):
        """初始化项目扫描器"""
        # 需要忽略的目录
        self.ignore_dirs = {
            'node_modules', '.git', '.svn', '.hg', '__pycache__', '.pytest_cache',
            'venv', 'env', '.env', 'virtualenv', '.venv',
            'target', 'build', 'dist', 'out', 'bin', 'obj',
            '.idea', '.vscode', '.vs', '.settings',
            'logs', 'log', 'tmp', 'temp', '.tmp',
            'coverage', '.coverage', '.nyc_output'
        }
        
        # 需要忽略的文件
        self.ignore_files = {
            '.DS_Store', 'Thumbs.db', '.gitignore', '.gitkeep',
            '*.log', '*.tmp', '*.cache', '*.pid', '*.lock'
        }
        
        # 重要的配置文件
        self.important_files = {
            'package.json', 'package-lock.json', 'yarn.lock',
            'requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile',
            'pom.xml', 'build.gradle', 'gradle.properties',
            'Cargo.toml', 'Cargo.lock',
            'go.mod', 'go.sum',
            'composer.json', 'composer.lock',
            'Gemfile', 'Gemfile.lock',
            'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
            'README.md', 'README.txt', 'README.rst',
            '.env.example', 'config.json', 'config.yaml', 'config.yml'
        }
    
    def scan_project(self, project_path: str, max_depth: int = 10) -> Dict[str, Any]:
        """
        扫描项目目录结构
        
        Args:
            project_path: 项目根目录路径
            max_depth: 最大扫描深度
            
        Returns:
            包含项目结构信息的字典
        """
        logger.info(f"开始扫描项目目录: {project_path}")
        
        if not os.path.exists(project_path):
            raise ValueError(f"项目路径不存在: {project_path}")
        
        if not os.path.isdir(project_path):
            raise ValueError(f"项目路径不是目录: {project_path}")
        
        result = {
            'root_path': project_path,
            'directories': [],
            'files': [],
            'important_files': [],
            'file_types': {},
            'total_files': 0,
            'total_directories': 0,
            'project_indicators': []
        }
        
        try:
            self._scan_directory(project_path, project_path, result, 0, max_depth)
            
            # 分析文件类型统计
            result['file_types'] = self._analyze_file_types(result['files'])
            
            # 识别项目类型指示器
            result['project_indicators'] = self._identify_project_indicators(result['important_files'])
            
            logger.info(f"项目扫描完成: {result['total_files']} 文件, {result['total_directories']} 目录")
            
        except Exception as e:
            logger.error(f"项目扫描失败: {e}")
            raise
        
        return result
    
    def _scan_directory(self, current_path: str, root_path: str, result: Dict[str, Any], 
                       current_depth: int, max_depth: int):
        """递归扫描目录"""
        
        if current_depth > max_depth:
            return
        
        try:
            items = os.listdir(current_path)
        except PermissionError:
            logger.warning(f"无权限访问目录: {current_path}")
            return
        except Exception as e:
            logger.warning(f"读取目录失败 {current_path}: {e}")
            return
        
        for item in items:
            item_path = os.path.join(current_path, item)
            relative_path = os.path.relpath(item_path, root_path)
            
            try:
                if os.path.isdir(item_path):
                    # 检查是否需要忽略此目录
                    if item in self.ignore_dirs:
                        continue
                    
                    result['directories'].append(relative_path)
                    result['total_directories'] += 1
                    
                    # 递归扫描子目录
                    self._scan_directory(item_path, root_path, result, current_depth + 1, max_depth)
                
                elif os.path.isfile(item_path):
                    # 检查是否需要忽略此文件
                    if self._should_ignore_file(item):
                        continue
                    
                    result['files'].append(relative_path)
                    result['total_files'] += 1
                    
                    # 检查是否为重要文件
                    if item in self.important_files:
                        result['important_files'].append(relative_path)
                
            except Exception as e:
                logger.warning(f"处理项目 {item_path} 失败: {e}")
                continue
    
    def _should_ignore_file(self, filename: str) -> bool:
        """判断是否应该忽略文件"""
        # 检查确切文件名
        if filename in self.ignore_files:
            return True
        
        # 检查文件扩展名和模式
        for pattern in self.ignore_files:
            if pattern.startswith('*.'):
                ext = pattern[1:]  # 移除*
                if filename.endswith(ext):
                    return True
        
        # 忽略隐藏文件（以.开头的文件，但保留重要的配置文件）
        if filename.startswith('.') and filename not in self.important_files:
            return True
        
        return False
    
    def _analyze_file_types(self, files: List[str]) -> Dict[str, int]:
        """分析文件类型统计"""
        file_types = {}
        
        for file_path in files:
            ext = Path(file_path).suffix.lower()
            if not ext:
                ext = 'no_extension'
            
            file_types[ext] = file_types.get(ext, 0) + 1
        
        # 按数量排序
        return dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True))
    
    def _identify_project_indicators(self, important_files: List[str]) -> List[str]:
        """识别项目类型指示器"""
        indicators = []
        
        file_names = [os.path.basename(f) for f in important_files]
        
        # JavaScript/Node.js项目
        if 'package.json' in file_names:
            indicators.append('nodejs')
            if 'package-lock.json' in file_names:
                indicators.append('npm')
            if 'yarn.lock' in file_names:
                indicators.append('yarn')
        
        # Python项目
        if any(f in file_names for f in ['requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile']):
            indicators.append('python')
            if 'requirements.txt' in file_names:
                indicators.append('pip')
            if 'pyproject.toml' in file_names:
                indicators.append('poetry_or_setuptools')
            if 'Pipfile' in file_names:
                indicators.append('pipenv')
        
        # Java项目
        if 'pom.xml' in file_names:
            indicators.extend(['java', 'maven'])
        if any(f in file_names for f in ['build.gradle', 'gradle.properties']):
            indicators.extend(['java', 'gradle'])
        
        # Rust项目
        if 'Cargo.toml' in file_names:
            indicators.extend(['rust', 'cargo'])
        
        # Go项目
        if 'go.mod' in file_names:
            indicators.extend(['go', 'go_modules'])
        
        # PHP项目
        if 'composer.json' in file_names:
            indicators.extend(['php', 'composer'])
        
        # Ruby项目
        if 'Gemfile' in file_names:
            indicators.extend(['ruby', 'bundler'])
        
        # Docker项目
        if any(f in file_names for f in ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml']):
            indicators.append('docker')
        
        return indicators
    
    def get_project_summary(self, scan_result: Dict[str, Any]) -> Dict[str, Any]:
        """获取项目摘要信息"""
        summary = {
            'total_files': scan_result['total_files'],
            'total_directories': scan_result['total_directories'],
            'main_file_types': list(scan_result['file_types'].keys())[:5],  # 前5种文件类型
            'project_types': scan_result['project_indicators'],
            'has_config_files': len(scan_result['important_files']) > 0,
            'config_files': scan_result['important_files']
        }
        
        # 估算项目规模
        if scan_result['total_files'] < 10:
            summary['project_size'] = 'small'
        elif scan_result['total_files'] < 100:
            summary['project_size'] = 'medium'
        else:
            summary['project_size'] = 'large'
        
        # 分析目录结构复杂度
        if scan_result['total_directories'] < 5:
            summary['structure_complexity'] = 'simple'
        elif scan_result['total_directories'] < 20:
            summary['structure_complexity'] = 'moderate'
        else:
            summary['structure_complexity'] = 'complex'
        
        return summary
    
    def find_entry_points(self, scan_result: Dict[str, Any]) -> List[str]:
        """查找可能的项目入口点"""
        entry_points = []
        files = scan_result['files']
        
        # 常见的入口点文件名
        entry_candidates = [
            'main.py', 'app.py', 'server.py', 'run.py', '__main__.py',
            'main.js', 'app.js', 'server.js', 'index.js',
            'Main.java', 'Application.java', 'App.java',
            'main.go', 'main.rs', 'main.cpp', 'main.c'
        ]
        
        for candidate in entry_candidates:
            matching_files = [f for f in files if os.path.basename(f) == candidate]
            entry_points.extend(matching_files)
        
        # 查找package.json中的main字段指定的文件
        package_json_files = [f for f in files if os.path.basename(f) == 'package.json']
        if package_json_files:
            # 这里可以进一步解析package.json来找到main字段
            pass
        
        return entry_points
    
    def get_directory_tree(self, scan_result: Dict[str, Any], max_items: int = 50) -> str:
        """生成目录树字符串表示"""
        directories = scan_result['directories']
        files = scan_result['files']
        
        # 合并并排序所有路径
        all_paths = directories + files
        all_paths.sort()
        
        # 限制显示数量
        if len(all_paths) > max_items:
            all_paths = all_paths[:max_items]
            truncated = True
        else:
            truncated = False
        
        tree_lines = []
        for path in all_paths:
            depth = path.count(os.sep)
            indent = "  " * depth
            name = os.path.basename(path)
            if path in directories:
                tree_lines.append(f"{indent}{name}/")
            else:
                tree_lines.append(f"{indent}{name}")
        
        if truncated:
            tree_lines.append("... (更多文件被截断)")
        
        return "\n".join(tree_lines)
