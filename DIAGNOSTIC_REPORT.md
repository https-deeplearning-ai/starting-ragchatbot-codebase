# RAG系统诊断报告

## 执行摘要

RAG系统返回"query failed"的**根本原因**是：**向量存储中没有课程数据**

## 诊断结果

### 1. 系统组件状态

| 组件 | 状态 | 说明 |
|------|------|------|
| CourseSearchTool | ✓ 正常 | 正确处理空结果和有效结果 |
| AIGenerator | ✓ 正常 | 成功导入，可以调用Claude API |
| RAGSystem | ✓ 正常 | 成功导入，所有组件初始化正常 |
| SessionManager | ✓ 正常 | 会话管理工作正常 |
| VectorStore | ✓ 可访问 | 但**数据为空** ⚠️ |
| ANTHROPIC_API_KEY | ✓ 已设置 | 环境配置正确 |

### 2. 关键发现

**向量存储状态：**
```
Current course count: 0
No course data in vector store
```

**这导致的问题链：**
1. 用户发送查询 → `/api/query`
2. RAGSystem调用AIGenerator
3. AIGenerator调用Claude API，提供CourseSearchTool
4. Claude可能调用search_course_content工具
5. CourseSearchTool调用vector_store.search()
6. **向量存储返回空结果** ← 问题所在
7. CourseSearchTool返回："No relevant content found"
8. Claude收到空的搜索结果，无法生成有意义的答案
9. API返回500错误或"query failed"

### 3. 测试验证

**测试1：空结果处理**
- ✓ PASS: CourseSearchTool正确处理空结果

**测试2：有效结果处理**
- ✓ PASS: 当有数据时，系统正确格式化结果

**测试3：模拟数据测试**
- ✓ PASS: 使用模拟课程数据时，系统工作正常
- 结果：`[Python 101 - Lesson 1] Python is a programming language...`

**测试4：完整查询流程**
- ✓ PASS: 所有组件协调工作正常

## 根本原因分析

### 为什么向量存储为空？

1. **应用启动时没有加载课程数据**
   - `app.py`中的`startup_event()`被跳过了
   - 代码显示：`print("跳过文档加载")`

2. **docs目录中有课程文件，但没有被加载**
   ```
   docs/
   ├── course1_script.txt
   ├── course2_script.txt
   ├── course3_script.txt
   └── course4_script.txt
   ```

3. **缺少初始化步骤**
   - 需要调用`rag_system.add_course_folder('docs')`来加载课程

## 修复方案

### 方案1：在应用启动时自动加载课程（推荐）

**修改 `backend/app.py` 中的 `startup_event()`：**

```python
@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup"""
    docs_path = "../docs"
    if os.path.exists(docs_path):
        print("Loading initial documents...")
        try:
            courses, chunks = rag_system.add_course_folder(docs_path)
            print(f"Loaded {courses} courses with {chunks} chunks")
        except Exception as e:
            print(f"Error loading documents: {e}")
    else:
        print(f"Warning: docs directory not found at {docs_path}")
```

**优点：**
- 应用启动时自动加载数据
- 用户无需手动操作
- 确保系统始终有数据

**缺点：**
- 启动时间可能增加
- 如果docs目录很大，可能影响启动性能

### 方案2：提供API端点来加载课程

**添加新的API端点：**

```python
@app.post("/api/admin/load-courses")
async def load_courses(folder_path: str = "docs"):
    """Load courses from a folder"""
    try:
        courses, chunks = rag_system.add_course_folder(folder_path)
        return {
            "status": "success",
            "courses_loaded": courses,
            "chunks_created": chunks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**优点：**
- 灵活，可以按需加载
- 不影响应用启动时间
- 可以重新加载数据

**缺点：**
- 需要手动调用
- 用户可能忘记调用

### 方案3：结合两种方案

**推荐方案：**
1. 在启动时尝试加载课程
2. 如果加载失败或没有数据，提供API端点来手动加载
3. 添加日志记录加载状态

## 实施步骤

### 步骤1：修复启动事件

编辑 `backend/app.py`，修改 `startup_event()` 函数：

```python
@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup"""
    docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
    if os.path.exists(docs_path):
        print("Loading initial documents...")
        try:
            courses, chunks = rag_system.add_course_folder(docs_path)
            print(f"Successfully loaded {courses} courses with {chunks} chunks")
        except Exception as e:
            print(f"Error loading documents: {e}")
    else:
        print(f"Warning: docs directory not found at {docs_path}")
```

### 步骤2：测试修复

1. 重启服务器
2. 检查启动日志中是否显示"Successfully loaded X courses"
3. 调用 `/api/courses` 端点验证课程已加载
4. 发送查询请求测试是否返回结果

### 步骤3：验证查询工作

```bash
# 测试查询
curl -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the main topic of course 1?"}'
```

## 预期结果

### 修复前
```
POST /api/query
Response: 500 Internal Server Error
或
Response: {"answer": "query failed", ...}
```

### 修复后
```
POST /api/query
Response: 200 OK
{
  "answer": "Based on the course materials, ...",
  "sources": ["Course 1 - Lesson 1", "Course 1 - Lesson 2"],
  "session_id": "session_1"
}
```

## 其他建议

### 1. 改进错误处理

在 `app.py` 中添加更详细的错误日志：

```python
@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Process a query and return response with sources"""
    try:
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()
        
        answer, sources = rag_system.query(request.query, session_id)
        
        if not answer or answer == "query failed":
            print(f"[WARNING] Query returned empty or failed: {request.query}")
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except Exception as e:
        print(f"[ERROR] Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. 添加健康检查端点

```python
@app.get("/api/health")
async def health_check():
    """Check system health"""
    course_count = rag_system.vector_store.get_course_count()
    return {
        "status": "healthy" if course_count > 0 else "warning",
        "courses_loaded": course_count,
        "api_key_set": bool(config.ANTHROPIC_API_KEY)
    }
```

### 3. 改进日志记录

在 `rag_system.py` 中添加日志：

```python
def query(self, query: str, session_id: Optional[str] = None) -> Tuple[str, List[str]]:
    """Process a user query using the RAG system with tool-based search."""
    print(f"[DEBUG] Query received: {query}")
    print(f"[DEBUG] Session ID: {session_id}")
    
    # ... rest of the code
    
    print(f"[DEBUG] Response generated: {response[:100]}...")
    return response, sources
```

## 总结

| 问题 | 原因 | 解决方案 |
|------|------|--------|
| "query failed" 错误 | 向量存储为空 | 在启动时加载课程数据 |
| 500 Internal Server Error | 无课程数据导致AI无法生成答案 | 修复startup_event()函数 |
| 搜索返回"No relevant content found" | 向量存储中没有数据 | 调用add_course_folder()加载数据 |

## 验证清单

- [ ] 修改 `backend/app.py` 中的 `startup_event()` 函数
- [ ] 重启服务器
- [ ] 检查启动日志中的"Successfully loaded X courses"消息
- [ ] 调用 `/api/courses` 验证课程已加载
- [ ] 发送测试查询验证系统工作正常
- [ ] 检查 `/api/health` 端点显示正确的课程数量

