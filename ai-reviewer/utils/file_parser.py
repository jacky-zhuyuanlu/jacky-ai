#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件解析器模块
负责读取和解析各种类型的代码文件
"""

import os
import chardet
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class FileParser:
    """文件解析器类"""
    
    def __init__(self):
        """初始化文件解析器"""
        # 支持的文本文件扩展名
        self.text_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.cs',
            '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.vue',
            '.html', '.css', '.scss', '.sass', '.less', '.xml', '.yaml', '.yml',
            '.json', '.md', '.txt', '.sql', '.sh', '.bat', '.ps1', '.dockerfile',
            '.gitignore', '.env', '.ini', '.cfg', '.conf', '.toml'
        }
        
        # 二进制文件扩展名（需要跳过）
        self.binary_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg', '.webp',
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm',
            '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma',
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.exe', '.dll', '.so', '.dylib', '.bin', '.dat'
        }
    
    def read_file_content(self, file_path: str) -> Optional[str]:
        """
        读取文件内容，自动检测编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容字符串，如果读取失败返回None
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.warning(f"文件不存在: {file_path}")
                return None
            
            # 检查文件大小，避免读取过大的文件
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB限制
                logger.warning(f"文件过大，跳过: {file_path} ({file_size} bytes)")
                return None
            
            # 检查文件扩展名
            file_ext = Path(file_path).suffix.lower()
            if file_ext in self.binary_extensions:
                logger.debug(f"跳过二进制文件: {file_path}")
                return None
            
            # 检测文件编码
            encoding = self._detect_encoding(file_path)
            if not encoding:
                logger.warning(f"无法检测文件编码: {file_path}")
                return None
            
            # 读取文件内容
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
            
            # 检查内容是否为文本
            if not self._is_text_content(content):
                logger.debug(f"文件内容不是文本: {file_path}")
                return None
            
            return content
            
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return None
    
    def _detect_encoding(self, file_path: str) -> Optional[str]:
        """检测文件编码"""
        try:
            # 读取文件的前几KB来检测编码
            with open(file_path, 'rb') as f:
                raw_data = f.read(8192)  # 读取前8KB
            
            if not raw_data:
                return 'utf-8'  # 空文件默认使用utf-8
            
            # 使用chardet检测编码
            detection = chardet.detect(raw_data)
            encoding = detection.get('encoding')
            confidence = detection.get('confidence', 0)
            
            # 如果置信度太低，尝试常见编码
            if confidence < 0.7:
                common_encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'ascii']
                for enc in common_encodings:
                    try:
                        raw_data.decode(enc)
                        return enc
                    except UnicodeDecodeError:
                        continue
            
            # 处理一些特殊情况
            if encoding:
                encoding = encoding.lower()
                if encoding in ['gb2312', 'gbk']:
                    return 'gbk'  # 统一使用gbk处理中文
                elif encoding.startswith('iso-8859'):
                    return 'latin-1'  # 统一使用latin-1处理西欧字符
                else:
                    return encoding
            
            return 'utf-8'  # 默认使用utf-8
            
        except Exception as e:
            logger.warning(f"编码检测失败 {file_path}: {e}")
            return 'utf-8'
    
    def _is_text_content(self, content: str) -> bool:
        """判断内容是否为文本"""
        if not content:
            return True
        
        # 检查是否包含过多的控制字符或不可打印字符
        printable_chars = sum(1 for c in content if c.isprintable() or c.isspace())
        total_chars = len(content)
        
        if total_chars == 0:
            return True
        
        # 如果可打印字符比例低于80%，认为不是文本文件
        printable_ratio = printable_chars / total_chars
        return printable_ratio >= 0.8
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含文件信息的字典
        """
        try:
            stat = os.stat(file_path)
            path_obj = Path(file_path)
            
            return {
                'name': path_obj.name,
                'extension': path_obj.suffix.lower(),
                'size': stat.st_size,
                'modified_time': stat.st_mtime,
                'is_text': path_obj.suffix.lower() in self.text_extensions,
                'is_binary': path_obj.suffix.lower() in self.binary_extensions
            }
            
        except Exception as e:
            logger.error(f"获取文件信息失败 {file_path}: {e}")
            return {}
    
    def extract_functions_and_classes(self, content: str, file_extension: str) -> Dict[str, Any]:
        """
        从代码内容中提取函数和类的信息
        
        Args:
            content: 文件内容
            file_extension: 文件扩展名
            
        Returns:
            包含函数和类信息的字典
        """
        result = {
            'functions': [],
            'classes': [],
            'imports': [],
            'exports': []
        }
        
        try:
            if file_extension in ['.py']:
                result = self._extract_python_structures(content)
            elif file_extension in ['.js', '.ts', '.jsx', '.tsx']:
                result = self._extract_javascript_structures(content)
            elif file_extension in ['.java']:
                result = self._extract_java_structures(content)
            # 可以继续添加其他语言的支持
            
        except Exception as e:
            logger.error(f"提取代码结构失败: {e}")
        
        return result
    
    def _extract_python_structures(self, content: str) -> Dict[str, Any]:
        """提取Python代码结构"""
        import ast
        
        result = {
            'functions': [],
            'classes': [],
            'imports': [],
            'exports': []
        }
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    result['functions'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'is_async': isinstance(node, ast.AsyncFunctionDef)
                    })
                elif isinstance(node, ast.ClassDef):
                    result['classes'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'bases': [ast.unparse(base) for base in node.bases] if hasattr(ast, 'unparse') else []
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            result['imports'].append({
                                'module': alias.name,
                                'alias': alias.asname,
                                'line': node.lineno
                            })
                    else:  # ImportFrom
                        for alias in node.names:
                            result['imports'].append({
                                'module': node.module,
                                'name': alias.name,
                                'alias': alias.asname,
                                'line': node.lineno
                            })
                            
        except SyntaxError as e:
            logger.warning(f"Python语法错误: {e}")
        except Exception as e:
            logger.error(f"解析Python代码失败: {e}")
        
        return result
    
    def _extract_javascript_structures(self, content: str) -> Dict[str, Any]:
        """提取JavaScript/TypeScript代码结构（简单实现）"""
        import re
        
        result = {
            'functions': [],
            'classes': [],
            'imports': [],
            'exports': []
        }
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 提取函数定义
            func_match = re.search(r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\(.*?\)\s*=>))', line)
            if func_match:
                func_name = func_match.group(1) or func_match.group(2)
                result['functions'].append({
                    'name': func_name,
                    'line': i,
                    'is_async': 'async' in line
                })
            
            # 提取类定义
            class_match = re.search(r'class\s+(\w+)', line)
            if class_match:
                result['classes'].append({
                    'name': class_match.group(1),
                    'line': i
                })
            
            # 提取导入
            import_match = re.search(r'import\s+(?:{([^}]+)}|\*\s+as\s+(\w+)|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]', line)
            if import_match:
                result['imports'].append({
                    'module': import_match.group(4),
                    'line': i
                })
            
            # 提取导出
            export_match = re.search(r'export\s+(?:default\s+)?(?:function\s+(\w+)|class\s+(\w+)|(?:const|let|var)\s+(\w+))', line)
            if export_match:
                export_name = export_match.group(1) or export_match.group(2) or export_match.group(3)
                result['exports'].append({
                    'name': export_name,
                    'line': i
                })
        
        return result
    
    def _extract_java_structures(self, content: str) -> Dict[str, Any]:
        """提取Java代码结构（简单实现）"""
        import re
        
        result = {
            'functions': [],
            'classes': [],
            'imports': [],
            'exports': []
        }
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 提取类定义
            class_match = re.search(r'(?:public\s+|private\s+|protected\s+)?class\s+(\w+)', line)
            if class_match:
                result['classes'].append({
                    'name': class_match.group(1),
                    'line': i
                })
            
            # 提取方法定义
            method_match = re.search(r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+\s*)?{?', line)
            if method_match and not class_match:  # 避免将类构造函数误识别为方法
                result['functions'].append({
                    'name': method_match.group(1),
                    'line': i
                })
            
            # 提取导入
            import_match = re.search(r'import\s+(?:static\s+)?([^;]+);', line)
            if import_match:
                result['imports'].append({
                    'module': import_match.group(1),
                    'line': i
                })
        
        return result
