# RAG Chatbot Query Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND (script.js)                          │
│                                                                           │
│  User Input → sendMessage()                                              │
│  ├─ Disable input fields                                                 │
│  ├─ Display user message in chat                                         │
│  ├─ Show loading animation                                               │
│  └─ POST /api/query                                                      │
│     {                                                                     │
│       "query": "What is Python?",                                        │
│       "session_id": "abc123"                                             │
│     }                                                                     │
└────────────────────────────────┬──────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        BACKEND API (app.py:56)                           │
│                                                                           │
│  @app.post("/api/query")                                                 │
│  ├─ Validate request                                                     │
│  ├─ Create/get session_id                                                │
│  └─ Call rag_system.query(query, session_id)                            │
└────────────────────────────────┬──────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    RAG SYSTEM ORCHESTRATOR (rag_system.py:102)           │
│                                                                           │
│  query() method:                                                         │
│  ├─ Get conversation history from SessionManager                         │
│  ├─ Prepare prompt                                                       │
│  ├─ Call ai_generator.generate_response()                                │
│  │   ├─ Pass query                                                       │
│  │   ├─ Pass conversation history                                        │
│  │   ├─ Pass tool definitions (search_course_content)                    │
│  │   └─ Pass tool_manager                                                │
│  ├─ Collect sources from tool_manager                                    │
│  ├─ Update conversation history                                          │
│  └─ Return (answer, sources)                                             │
└────────────────────────────────┬──────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    AI GENERATOR (ai_generator.py:43)                     │
│                                                                           │
│  generate_response():                                                    │
│  ├─ Build system prompt + conversation history                           │
│  ├─ Prepare API parameters with tools                                    │
│  ├─ Call Claude API (anthropic.messages.create)                          │
│  └─ Check response.stop_reason                                           │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ If stop_reason == "tool_use":                                    │   │
│  │                                                                   │   │
│  │  _handle_tool_execution():                                       │   │
│  │  ├─ Extract tool calls from Claude's response                    │   │
│  │  ├─ Execute each tool via tool_manager ──────────┐              │   │
│  │  ├─ Collect tool results                         │              │   │
│  │  ├─ Send results back to Claude                  │              │   │
│  │  └─ Get final synthesized response               │              │   │
│  └──────────────────────────────────────────────────┼──────────────┘   │
└───────────────────────────────────────────────────────┼──────────────────┘
                                                        │
                                                        ▼
                        ┌───────────────────────────────────────────┐
                        │   TOOL MANAGER (search_tools.py:135)      │
                        │                                            │
                        │   execute_tool(name, **kwargs):           │
                        │   └─ Route to CourseSearchTool.execute()  │
                        └─────────────────┬─────────────────────────┘
                                          │
                                          ▼
                        ┌───────────────────────────────────────────┐
                        │  COURSE SEARCH TOOL (search_tools.py:52)  │
                        │                                            │
                        │  execute(query, course_name, lesson_num): │
                        │  ├─ Call vector_store.search()            │
                        │  ├─ Format results with context           │
                        │  ├─ Track sources for UI                  │
                        │  └─ Return formatted search results        │
                        └─────────────────┬─────────────────────────┘
                                          │
                                          ▼
                        ┌───────────────────────────────────────────┐
                        │    VECTOR STORE (vector_store.py:61)      │
                        │                                            │
                        │  search(query, course_name, lesson_num):  │
                        │  ├─ Resolve course name (if provided)     │
                        │  │  └─ Semantic search in course_catalog  │
                        │  ├─ Build ChromaDB filter                 │
                        │  ├─ Search course_content collection      │
                        │  │  └─ Query with embeddings              │
                        │  └─ Return SearchResults                  │
                        │     (documents, metadata, distances)      │
                        └───────────────────────────────────────────┘

                                    RESPONSE PATH ↑

┌─────────────────────────────────────────────────────────────────────────┐
│                         RESPONSE FLOW (Upward)                           │
│                                                                           │
│  Vector Store Results                                                    │
│     ↓                                                                     │
│  Tool formats results → returns to AI Generator                          │
│     ↓                                                                     │
│  Claude synthesizes final answer from tool results                       │
│     ↓                                                                     │
│  RAG System collects answer + sources                                    │
│     ↓                                                                     │
│  API returns JSON:                                                       │
│     {                                                                     │
│       "answer": "Python is a high-level programming language...",        │
│       "sources": ["Introduction to Python - Lesson 1"],                  │
│       "session_id": "abc123"                                             │
│     }                                                                     │
│     ↓                                                                     │
│  Frontend receives response                                              │
│     ├─ Remove loading animation                                          │
│     ├─ Render answer with markdown                                       │
│     ├─ Display collapsible sources section                               │
│     └─ Re-enable input fields                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Data Structures

### Request Flow
```
User Query → QueryRequest → RAG Query → AI Generation → Tool Execution → Vector Search
```

### Response Flow
```
SearchResults → Tool Response → Claude Synthesis → QueryResponse → UI Display
```

## Component Interactions

| Component | Input | Output | Key Methods |
|-----------|-------|--------|-------------|
| **Frontend** | User text | HTTP POST | `sendMessage()`, `addMessage()` |
| **API** | QueryRequest | QueryResponse | `query_documents()` |
| **RAG System** | query, session_id | answer, sources | `query()` |
| **AI Generator** | prompt, tools, history | response text | `generate_response()` |
| **Tool Manager** | tool_name, params | tool result | `execute_tool()` |
| **Search Tool** | query, filters | formatted results | `execute()` |
| **Vector Store** | query, filters | SearchResults | `search()` |

## Session & Context Management

```
SessionManager (session_manager.py)
├─ create_session() → new session_id
├─ get_conversation_history(session_id) → previous exchanges
└─ add_exchange(session_id, query, response) → update history

Conversation Flow:
1. First query: No session_id → Create new session
2. Subsequent queries: Use existing session_id → Load history
3. History included in AI context for coherent responses
```
