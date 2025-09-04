# AI代码分析Agent

**基于 Fay 平台重构的 MCP 能力平台核心模块**

这是一个智能代码分析Agent，能够接收项目代码和功能需求描述，自动分析代码结构并生成详细的功能实现位置报告。作为 Fay MCP (Model Context Protocol) 能力平台的核心组件，集成了先进的 AI 代码分析和自动化测试生成能力。

## 功能特点

- 🔍 **智能代码分析**: 使用AI技术深度分析代码结构和功能实现
- 📊 **结构化报告**: 生成JSON格式的详细分析报告
- 🧪 **自动测试生成**: 可选的功能验证测试代码生成和执行
- 🐳 **Docker化部署**: 提供完整的容器化部署方案
- 🌐 **RESTful API**: 简单易用的HTTP接口
- 🔧 **多语言支持**: 支持JavaScript/TypeScript、Python、Java等主流编程语言

## 快速开始

### 使用Docker（推荐）

1. **克隆项目**
```bash
git clone <repository-url>
cd ai-reviewer
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑.env文件，设置你的OpenAI API Key
```

3. **使用Docker Compose启动**
```bash
docker-compose up -d
```

4. **验证服务**
```bash
curl http://localhost:5001/health
```

### 本地开发

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **设置环境变量**
```bash
export OPENAI_API_KEY="sk-********************************"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export OPENAI_MODEL="deepseek-chat"
python app.py
```

## API使用说明

### 分析代码接口

**POST /analyze**

上传代码压缩包和功能需求描述，获取分析报告。

**请求参数：**
- `problem_description` (string, form field): 项目功能需求描述
- `code_zip` (file, form upload): 包含项目代码的zip压缩文件
- `include_tests` (string, optional): 是否生成测试代码，值为"true"或"false"

**请求示例：**
```bash
curl -X POST \
  -F "problem_description=实现用户管理和消息系统功能" \
  -F "code_zip=@project.zip" \
  -F "include_tests=true" \
  http://localhost:5001/analyze
```

**响应示例：**
```json
{
  "feature_analysis": [
    {
      "feature_description": "实现`用户注册`功能",
      "implementation_location": [
        {
          "file": "src/controllers/user.controller.js",
          "function": "register",
          "lines": "15-28"
        },
        {
          "file": "src/services/user.service.js",
          "function": "createUser",
          "lines": "42-67"
        }
      ]
    }
  ],
  "execution_plan_suggestion": "要执行此项目，应首先执行 `npm install` 安装依赖，然后执行 `npm run start:dev` 来启动开发服务器。",
  "functional_verification": {
    "generated_test_code": "// 生成的测试代码...",
    "execution_result": {
      "tests_passed": true,
      "log": "1 passing (2s)"
    }
  }
}
```

### 健康检查接口

**GET /health**

检查服务状态。

**响应示例：**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "AI Code Reviewer Agent"
}
```

## 支持的项目类型

- **Node.js项目**: Express、NestJS、React、Vue等
- **Python项目**: Django、Flask、FastAPI等
- **Java项目**: Spring Boot、Maven、Gradle项目
- **其他语言**: Go、Rust、PHP、Ruby等

## 分析报告说明

### 核心报告结构

```json
{
  "feature_analysis": [
    {
      "feature_description": "功能描述",
      "implementation_location": [
        {
          "file": "文件路径",
          "function": "函数/方法名",
          "lines": "起始行-结束行"
        }
      ]
    }
  ],
  "execution_plan_suggestion": "项目执行建议",
  "project_info": {
    "type": "项目类型",
    "main_language": "主要编程语言",
    "framework": "使用的框架"
  }
}
```

### 加分项：功能验证

当设置`include_tests=true`时，系统会额外生成：

```json
{
  "functional_verification": {
    "generated_test_code": "生成的测试代码",
    "execution_result": {
      "tests_passed": true/false,
      "log": "测试执行日志"
    },
    "test_strategy": "测试策略类型"
  }
}
```

## 配置说明

### 环境变量

- `OPENAI_API_KEY`: OpenAI API密钥（必需）
- `DEBUG`: 调试模式，默认false
- `PORT`: 服务端口，默认5001
- `LOG_LEVEL`: 日志级别，默认INFO

### 文件上传限制

- 最大文件大小: 100MB
- 支持格式: ZIP压缩文件
- 单个代码文件大小限制: 10MB

## 开发说明

### 项目结构

```
ai-reviewer/
├── app.py                 # 主应用入口
├── code_analyzer.py       # 代码分析器
├── test_generator.py      # 测试生成器
├── utils/                 # 工具模块
│   ├── file_parser.py     # 文件解析器
│   └── project_scanner.py # 项目扫描器
├── requirements.txt       # Python依赖
├── Dockerfile            # Docker镜像配置
├── docker-compose.yml    # Docker Compose配置
└── README.md            # 项目文档
```

### 扩展支持

要添加新的编程语言支持：

1. 在`utils/file_parser.py`中添加对应的代码解析逻辑
2. 在`code_analyzer.py`中更新项目类型识别逻辑
3. 在`test_generator.py`中添加对应的测试生成策略

## 故障排除

### 常见问题

1. **OpenAI API调用失败**
   - 检查API密钥是否正确设置
   - 确认API密钥有足够的使用额度
   - 检查网络连接

2. **文件解压失败**
   - 确认上传的是有效的ZIP文件
   - 检查文件大小是否超过限制
   - 确认ZIP文件没有损坏

3. **测试执行失败**
   - 检查项目依赖是否完整
   - 确认项目结构符合标准规范
   - 查看详细的错误日志

### 日志查看

```bash
# Docker环境
docker-compose logs ai-reviewer

# 本地环境
tail -f logs/app.log
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 联系方式

如有问题或建议，请通过GitHub Issues联系我们。
