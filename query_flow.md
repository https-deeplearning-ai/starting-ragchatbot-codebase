# 用户查询处理流程图

```mermaid
graph TD
    A["👤 用户输入查询"] -->|输入问题| B["📱 前端 script.js"]

    B -->|sendMessage| C["🔄 构建请求"]
    C -->|POST /api/query| D["🖥️ 后端 app.py"]

    D -->|query_documents| E["⚙️ RAG系统"]

    E -->|初始化| F["📊 核心组件"]
    F -->|1. 获取会话历史| G["💾 SessionManager"]
    F -->|2. 生成提示词| H["🤖 AIGenerator"]
    F -->|3. 准备工具| I["🔧 ToolManager"]

    H -->|第一次调用| J["🌐 Claude API"]
    J -->|stop_reason| K{需要搜索?}

    K -->|是: tool_use| L["🔍 执行工具"]
    K -->|否: end_turn| M["✅ 直接返回答案"]

    L -->|调用search_tool| N["🔎 CourseSearchTool"]
    N -->|语义搜索| O["📚 VectorStore"]

    O -->|1. 解析课程名| P["🏷️ 课程匹配"]
    O -->|2. 构建过滤| Q["🎯 过滤条件"]
    O -->|3. ChromaDB查询| R["🔗 向量相似度"]

    R -->|返回chunks| S["📄 搜索结果"]
    S -->|格式化| T["📋 结果文本"]
    T -->|保存来源| U["📌 Sources列表"]

    U -->|工具结果| V["🔄 第二次调用"]
    V -->|Claude API| W["💬 最终答案"]

    M -->|答案| X["📤 返回响应"]
    W -->|答案| X

    X -->|QueryResponse| Y["📱 前端处理"]
    Y -->|显示答案| Z["🎨 渲染UI"]
    Z -->|显示来源| AA["📚 Sources面板"]

    U -->|保存到会话| AB["💾 SessionManager"]
    AB -->|下次对话使用| G

    style A fill:#e1f5ff
    style B fill:#fff3e0
    style D fill:#f3e5f5
    style E fill:#e8f5e9
    style J fill:#fce4ec
    style O fill:#e0f2f1
    style Z fill:#fff9c4
```

## 流程说明

### 1️⃣ 前端层（script.js）
- 用户输入查询 → 点击发送
- 构建请求：`{query, session_id}`
- POST到 `/api/query`
- 显示加载动画

### 2️⃣ 后端API层（app.py）
- 接收 `QueryRequest`
- 创建或使用现有 `session_id`
- 调用 `rag_system.query()`
- 返回 `QueryResponse {answer, sources, session_id}`

### 3️⃣ RAG系统核心（rag_system.py）
- 获取会话历史（用于多轮对话）
- 调用 AI 生成器，传入工具定义
- 从工具管理器获取来源
- 保存会话交互

### 4️⃣ AI生成层（ai_generator.py）
**第一次调用：**
- 构建系统提示词
- 发送查询 + 工具定义到 Claude API
- Claude 判断是否需要搜索

**两种情况：**
- ✅ `stop_reason == "end_turn"` → 直接返回答案
- 🔍 `stop_reason == "tool_use"` → 执行工具

**第二次调用（如需搜索）：**
- 执行工具获得搜索结果
- 将结果发回 Claude
- Claude 基于搜索结果生成最终答案

### 5️⃣ 工具执行层（search_tools.py）
- `CourseSearchTool.execute()` 调用向量存储
- 格式化搜索结果
- 保存来源信息供前端显示

### 6️⃣ 向量搜索层（vector_store.py）
- 解析课程名（如有指定）
- 构建过滤条件（课程、课时）
- 使用 ChromaDB 进行语义搜索
- 返回最相关的 chunks

### 7️⃣ 会话管理（session_manager.py）
- 创建新会话或使用现有会话
- 保存对话历史
- 下次查询时提供上下文

### 8️⃣ 前端响应（script.js）
- 接收 `{answer, sources, session_id}`
- 用 marked.js 将 Markdown 转为 HTML
- 显示答案
- 显示可折叠的 Sources 面板
- 启用输入框，聚焦光标

## 关键设计点

| 设计 | 优势 |
|------|------|
| Claude 作为编排器 | 自动决定是否需要搜索，减少不必要的API调用 |
| 工具调用模式 | 搜索结果只在需要时获取，节省成本 |
| 会话管理 | 支持多轮对话，保持上下文 |
| 向量搜索 | 语义理解，比关键词搜索更准确 |
| 来源追踪 | 用户可验证答案的信息来源 |

## 成本优化

1. **单次搜索**：系统提示词限制每个查询最多一次搜索
2. **缓存利用**：会话历史避免重复处理
3. **智能决策**：Claude 判断何时需要搜索，何时用已知知识回答
