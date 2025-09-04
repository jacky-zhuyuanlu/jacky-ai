#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI代码分析Agent测试脚本
用于演示和测试Agent的功能
"""

import requests
import json
import os
import time

def test_health_check():
    """测试健康检查接口"""
    print("🔍 测试健康检查接口...")
    try:
        response = requests.get("http://localhost:5001/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查成功: {data['service']}")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False

def test_api_info():
    """测试API信息接口"""
    print("\n📋 获取API信息...")
    try:
        response = requests.get("http://localhost:5001/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API信息获取成功")
            print(f"   服务: {data['service']}")
            print(f"   版本: {data['version']}")
            print(f"   描述: {data['description']}")
            return True
        else:
            print(f"❌ API信息获取失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API信息获取异常: {e}")
        return False

def test_code_analysis():
    """测试代码分析功能"""
    print("\n🔍 测试代码分析功能...")
    
    # 准备测试数据
    problem_description = """
    实现一个聊天室GraphQL API，包含以下功能：
    1. 创建频道功能
    2. 在频道中发送消息功能  
    3. 按时间倒序列出频道中的消息功能
    4. 删除频道和消息功能
    """
    
    zip_file_path = "test_project.zip"
    
    if not os.path.exists(zip_file_path):
        print(f"❌ 测试文件不存在: {zip_file_path}")
        return False
    
    try:
        # 准备请求数据
        files = {
            'code_zip': ('test_project.zip', open(zip_file_path, 'rb'), 'application/zip')
        }
        data = {
            'problem_description': problem_description,
            'include_tests': 'true'  # 包含测试生成
        }
        
        print("📤 发送分析请求...")
        response = requests.post(
            "http://localhost:5001/analyze",
            files=files,
            data=data,
            timeout=120  # 2分钟超时
        )
        
        files['code_zip'][1].close()  # 关闭文件
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 代码分析成功!")
            
            # 显示分析结果
            print("\n📊 分析结果:")
            print("=" * 50)
            
            # 功能分析
            if 'feature_analysis' in result:
                print("\n🎯 功能分析:")
                for i, feature in enumerate(result['feature_analysis'], 1):
                    print(f"\n{i}. {feature['feature_description']}")
                    if feature['implementation_location']:
                        for loc in feature['implementation_location']:
                            print(f"   📁 {loc['file']}")
                            print(f"   🔧 {loc['function']} (行 {loc['lines']})")
                    else:
                        print("   ❌ 未找到实现位置")
            
            # 执行建议
            if 'execution_plan_suggestion' in result:
                print(f"\n🚀 执行建议:")
                print(f"   {result['execution_plan_suggestion']}")
            
            # 项目信息
            if 'project_info' in result:
                info = result['project_info']
                print(f"\n📋 项目信息:")
                print(f"   类型: {info.get('type', 'unknown')}")
                print(f"   语言: {info.get('main_language', 'unknown')}")
                print(f"   框架: {info.get('framework', 'unknown')}")
            
            # 功能验证（加分项）
            if 'functional_verification' in result:
                verification = result['functional_verification']
                print(f"\n🧪 功能验证:")
                print(f"   测试策略: {verification.get('test_strategy', 'unknown')}")
                
                if verification.get('generated_test_code'):
                    print(f"   ✅ 已生成测试代码 ({len(verification['generated_test_code'])} 字符)")
                
                exec_result = verification.get('execution_result', {})
                if exec_result.get('tests_passed'):
                    print(f"   ✅ 测试执行成功")
                else:
                    print(f"   ❌ 测试执行失败")
                
                if exec_result.get('log'):
                    print(f"   📝 执行日志: {exec_result['log'][:100]}...")
            
            # 保存详细结果到文件
            with open('analysis_result.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 详细结果已保存到: analysis_result.json")
            
            return True
            
        else:
            print(f"❌ 代码分析失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   错误信息: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   响应内容: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时，分析可能需要更长时间")
        return False
    except Exception as e:
        print(f"❌ 代码分析异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 AI代码分析Agent测试开始")
    print("=" * 50)
    
    # 等待服务启动
    print("⏳ 等待服务启动...")
    time.sleep(2)
    
    # 执行测试
    tests = [
        ("健康检查", test_health_check),
        ("API信息", test_api_info), 
        ("代码分析", test_code_analysis)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        if test_func():
            passed += 1
        time.sleep(1)
    
    # 测试总结
    print(f"\n{'='*50}")
    print(f"🎯 测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("✅ 所有测试通过！AI代码分析Agent工作正常")
    else:
        print("❌ 部分测试失败，请检查服务状态")
    
    print("\n📝 使用说明:")
    print("1. 确保设置了有效的OPENAI_API_KEY环境变量")
    print("2. 服务运行在 http://localhost:5001")
    print("3. 可以通过浏览器访问API文档和健康检查")
    print("4. 使用curl或其他工具测试API接口")

if __name__ == "__main__":
    main()
