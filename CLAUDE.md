# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于 FastAPI 的 RAG (Retrieval-Augmented Generation) 系统，用于回答关于课程材料的问题。核心组件：

- **ChromaDB** - 向量存储，用于语义搜索
- **MiniMax** - AI 生成模型
- **FastAPI** - Web 框架和 API

## 运行命令

```bash
# 快速启动
./run.sh

# 手动启动
cd backend && uv run uvicorn app:app --reload --port 8000

# 安装依赖
uv sync
```

## 架构要点

- `backend/rag_system.py` - 主协调器，整合所有组件
- `backend/ai_generator.py` - 调用 MiniMax API，处理工具执行
- `backend/search_tools.py` - 语义搜索工具，基于 ChromaDB
- `backend/document_processor.py` - 文档分块 (chunk_size=1000, overlap=200)
- `backend/session_manager.py` - 维护对话历史

## 配置

需要 `.env` 文件包含 `MINMAX_API_KEY`。使用 `.env.example` 作为模板。

## API 端点

- `POST /api/query` - 处理查询，返回答案和来源
- `GET /api/courses` - 获取课程统计信息