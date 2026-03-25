#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Mock RAG API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
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

# Mock data
MOCK_ANSWER = "这是一个测试回复。后端 API 需要修复导入问题才能正常工作。"

# Endpoints
@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    return QueryResponse(
        answer=MOCK_ANSWER,
        sources=["course1.pdf", "course2.pdf"],
        session_id=request.session_id or "test-session-123"
    )

@app.get("/api/courses", response_model=CourseStats)
async def get_course_stats():
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

if __name__ == "__main__":
    uvicorn.run("mock_api:app", host="0.0.0.0", port=8000, reload=True)