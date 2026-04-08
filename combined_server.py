#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore")

#!/usr/bin/env python3
import warnings
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn

# 全局常量
DEFAULT_SESSION_ID = "default-session"

app = FastAPI(title="Combined RAG App")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Pydantic 模型
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: str

class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]

# API 端点
@app.post("/api/query", status_code=status.HTTP_200_OK)
async def query_documents(request: QueryRequest):
    """处理文档查询请求"""
    try:
        # 基本验证
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="查询内容不能为空")

        # 这里可以添加实际的 RAG 逻辑
        answer = "正在处理查询..."
        sources = ["暂无数据"]
        session_id = request.session_id or DEFAULT_SESSION_ID
        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/courses", status_code=status.HTTP_200_OK)
async def get_course_stats():
    """获取课程统计信息"""
    try:
        return CourseStats(
            total_courses=5,
            course_titles=[
                "MCP: Build Rich-Context AI Apps with Anthropic",
                "Introduction to Python",
                "Advanced Machine Learning",
                "Building Towards Computer Use with Anthropic",
                "Prompt Compression and Query Optimization"
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# 调试端点
@app.get("/debug")
async def debug():
    """调试接口"""
    return {"message": "Debug endpoint working"}

# 静态文件服务
@app.get("/", include_in_schema=False)
async def serve_static():
    """主路由，用于服务静态文件"""
    try:
        return FileResponse("frontend/index.html")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# 增强调试功能
@app.get("/debug/config")
async def debug_config():
    """获取当前配置信息"""
    return {
        "app_name": app.title,
        "host": "0.0.0.0",
        "port": 8002,
        "default_session_id": DEFAULT_SESSION_ID,
        "cors_allowed_origins": ["*"]
    }

if __name__ == "__main__":
    print("Starting combined server on http://localhost:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=False)