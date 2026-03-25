# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个课程材料RAG（检索增强生成）系统，旨在使用语义搜索和AI驱动的响应来回答关于教育课程材料的问题。该系统使用ChromaDB进行向量存储，Anthropic的Claude进行AI生成，并提供一个Web界面进行交互。

## 架构概述

系统遵循模块化架构，包含以下主要组件：

1. **后端服务**（基于Python的FastAPI应用程序）
   - 处理API请求并协调RAG工作流程
   - 管理会话状态和对话历史
   - 提供RESTful端点用于查询课程材料

2. **核心RAG组件**
   - `vector_store.py`：管理ChromaDB向量存储用于课程内容和元数据
   - `document_processor.py`：处理文本分块和课程文档解析
   - `ai_generator.py`：与Anthropic的Claude API接口进行响应生成
   - `session_manager.py`：管理对话会话和历史

3. **搜索工具**
   - `search_tools.py`：实现Anthropic工具调用的工具定义
   - 提供带有课程和章节过滤的语义搜索能力

## 开发命令

### 常用命令

```bash
# 安装依赖
uv sync

# 运行开发服务器
uv run uvicorn app:app --reload --port 8000

# 运行应用程序
chmod +x run.sh
./run.sh

# 运行测试
uv run pytest -x
```

### 测试

```bash
# 运行单元测试
uv run pytest -x

# 运行特定测试文件
uv run pytest tests/test_*.py
```

### 构建与运行

```bash
# 构建并运行应用程序
uv run uvicorn app:app --reload --port 8000
```

## 关键组件

### 1. 配置

- 配置通过`config.py`管理，使用环境变量
- 关键设置包括：
  - `CHROMA_PATH`：ChromaDB存储路径
  - `EMBEDDING_MODEL`：用于嵌入的Sentence-transformer模型
  - `MAX_RESULTS`：返回的搜索结果数量
  - `MAX_HISTORY`：保留的对话历史最大数量

### 2. 文档处理

- `document_processor.py`处理课程文档解析
- 预期文档格式：
  - 第一行：课程标题
  - 第二行：课程链接
  - 第三行：课程讲师
  - 后续行：章节标记和内容

### 3. 向量存储

- 使用ChromaDB进行基于向量的语义搜索
- 两个集合：
  - `course_catalog`：用于语义匹配的课程元数据存储
  - `course_content`：用于内容搜索的实际文本块存储

### 4. AI生成

- 与Anthropic的Claude API接口
- 使用工具调用功能
- 提供上下文感知的响应，包含对话历史

## 使用示例

### 查询课程材料

```python
# 示例API调用
import requests

response = requests.post(
    "http://localhost:8000/api/query",
    json={
        "query": "课程第2课的主要主题是什么？",
        "session_id": "session_1"
    }
)
print(response.json())
```

### 添加课程文档

```python
# 添加单个课程文档
from backend.rag_system import RAGSystem

rag = RAGSystem(config)
rag.add_course_document("path/to/course.pdf")
```

### 清除数据

```python
# 清除所有现有数据
from backend.vector_store import VectorStore

store = VectorStore(config.CHROMA_PATH)
store.clear_all_data()
```

## API端点

### 查询端点
- `POST /api/query`
  - 查询课程材料
  - 返回答案和来源

### 课程端点
- `GET /api/courses`
  - 获取课程分析和统计信息

### 前端
- 从`../frontend`目录提供
- 可访问于`http://localhost:8000`

## 故障排除

常见问题和解决方案：
1. **缺少ChromaDB数据**：运行`rag_system.add_course_folder(docs_path)`重建
2. **API密钥错误**：验证`.env`文件中是否设置了`ANTHROPIC_API_KEY`
3. **空搜索结果**：检查是否已将课程添加到向量存储中
4. **会话问题**：确保会话正确创建和管理
```
