# 项目摘要

## 项目概览
**课程材料 RAG 系统** - 一个基于检索增强生成（RAG）的全栈应用，使用语义搜索和 AI 驱动响回答课程相关问题。

## 技术栈
| 类型 | 技术 |
|------|------|
| 后端 | Python 3.13+, FastAPI |
| 前端 | HTML/JS/CSS（原生） |
| 向量数据库 | ChromaDB |
| 嵌入模型 | sentence-transformers |
| AI 引擎 | Anthropic Claude API |
| 包管理 | uv |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/app.py` | FastAPI 主应用，API 端点 |
| `backend/rag_system.py` | RAG 系统核心逻辑 |
| `backend/vector_store.py` | ChromaDB 向量存储管理 |
| `backend/ai_generator.py` | Claude AI 响应生成 |
| `backend/document_processor.py` | 文档解析和分块处理 |
| `backend/session_manager.py` | 对话会话和历史管理 |
| `backend/search_tools.py` | Anthropic 工具调用定义 |
| `backend/config.py` | 配置管理 |
| `frontend/index.html` | 前端入口 |
| `frontend/script.js` | 前端交互逻辑 |
| `frontend/style.css` | 样式表 |
| `run.sh` | 启动脚本 |

## 核心功能
- 课程材料语义搜索
- AI 驱动的问答响应
- 会话历史管理
- 课程和章节过滤
- 向量存储（两个集合：course_catalog, course_content）

## 启动命令
```bash
uv sync                           # 安装依赖
uv run uvicorn app:app --reload --port 8000  # 启动服务
# 或使用 ./run.sh
```

服务地址：`http://localhost:8000`

---
*生成时间：2026-03-25*
