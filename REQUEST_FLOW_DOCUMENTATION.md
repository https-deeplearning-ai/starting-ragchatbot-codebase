# RAG Chatbot Request Flow Documentation

This document provides a complete trace of how a user request flows through the RAG chatbot system, from frontend input to displayed response.

---

## Complete User Request Trace

Here's the end-to-end flow of a user query through the system with exact code references:

### **1. Frontend → API Request**

**File:** `frontend/script.js:45-96`

```javascript
// User types "What is prompt caching?" and clicks Send
sendMessage() {
    query = "What is prompt caching?"

    // POST to backend
    fetch('/api/query', {
        method: 'POST',
        body: JSON.stringify({
            query: "What is prompt caching?",
            session_id: "session_1"  // or null for first query
        })
    })
}
```

**Payload sent:**
```json
{
  "query": "What is prompt caching?",
  "session_id": "session_1"
}
```

---

### **2. API Endpoint Receives Request**

**File:** `backend/app.py:56-74`

```python
@app.post("/api/query")
async def query_documents(request: QueryRequest):
    # Create session if not provided
    session_id = request.session_id or rag_system.session_manager.create_session()

    # Process query using RAG system
    answer, sources = rag_system.query(request.query, session_id)

    return QueryResponse(
        answer=answer,
        sources=sources,
        session_id=session_id
    )
```

**Execution:** `app.py:66` → Calls `rag_system.query()`

---

### **3. RAG System Orchestrates**

**File:** `backend/rag_system.py:102-140`

```python
def query(self, query: str, session_id: Optional[str] = None):
    # Step 1: Build prompt
    prompt = f"Answer this question about course materials: {query}"

    # Step 2: Get conversation history (last 2 exchanges)
    history = self.session_manager.get_conversation_history(session_id)
    # Returns formatted string like:
    # "User: previous question\nAssistant: previous answer"

    # Step 3: Generate response with AI + tools
    response = self.ai_generator.generate_response(
        query=prompt,
        conversation_history=history,
        tools=self.tool_manager.get_tool_definitions(),
        tool_manager=self.tool_manager
    )

    # Step 4: Extract sources from tool usage
    sources = self.tool_manager.get_last_sources()

    # Step 5: Update session history
    self.session_manager.add_exchange(session_id, query, response)

    return response, sources
```

---

### **4. Session Manager Retrieves History**

**File:** `backend/session_manager.py:42-56`

```python
def get_conversation_history(self, session_id):
    messages = self.sessions[session_id]  # List of Message objects

    formatted = []
    for msg in messages:
        formatted.append(f"{msg.role.title()}: {msg.content}")

    return "\n".join(formatted)
```

**Output:** String containing last 2 exchanges (4 messages max)

---

### **5. AI Generator Calls Claude**

**File:** `backend/ai_generator.py:43-87`

```python
def generate_response(self, query, conversation_history, tools, tool_manager):
    # Build system prompt with history
    system_content = f"{SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"

    # Call Claude with tools
    response = self.client.messages.create(
        model="claude-sonnet-4-20250514",
        temperature=0,
        max_tokens=800,
        system=system_content,
        messages=[{"role": "user", "content": query}],
        tools=tools,  # search_course_content tool definition
        tool_choice={"type": "auto"}
    )

    # Claude decides to use tool
    if response.stop_reason == "tool_use":
        return self._handle_tool_execution(response, ...)
```

**Claude's decision:** Uses `search_course_content` tool

---

### **6. Tool Execution Flow**

**File:** `backend/ai_generator.py:89-135`

```python
def _handle_tool_execution(self, initial_response, base_params, tool_manager):
    # Extract tool use from Claude's response
    for content_block in initial_response.content:
        if content_block.type == "tool_use":
            # Claude wants to search with these parameters:
            # name: "search_course_content"
            # input: {
            #   "query": "prompt caching",
            #   "course_name": "Building Toward Computer Use"
            # }

            # Execute tool
            tool_result = tool_manager.execute_tool(
                content_block.name,  # "search_course_content"
                **content_block.input  # query="prompt caching", course_name="..."
            )
```

**File:** `backend/search_tools.py:135-140`

```python
def execute_tool(self, tool_name: str, **kwargs):
    return self.tools[tool_name].execute(**kwargs)
    # Calls CourseSearchTool.execute()
```

---

### **7. Course Search Tool Executes**

**File:** `backend/search_tools.py:52-86`

```python
def execute(self, query: str, course_name: Optional[str], lesson_number: Optional[int]):
    # Delegate to vector store
    results = self.store.search(
        query="prompt caching",
        course_name="Building Toward Computer Use",
        lesson_number=None
    )

    # Format results
    return self._format_results(results)
```

---

### **8. Vector Store Searches**

**File:** `backend/vector_store.py:61-100`

```python
def search(self, query, course_name, lesson_number):
    # Step 1: Resolve fuzzy course name to exact title
    course_title = self._resolve_course_name(course_name)
    # Searches course_catalog collection with semantic matching
    # "Building Toward Computer Use" → exact match

    # Step 2: Build filter
    filter_dict = {"course_title": course_title}

    # Step 3: Search course content with embeddings
    results = self.course_content.query(
        query_texts=["prompt caching"],
        n_results=5,  # MAX_RESULTS from config
        where={"course_title": "Building Toward Computer Use with Anthropic"}
    )

    return SearchResults.from_chroma(results)
```

**ChromaDB operations:**
- Generates embedding for "prompt caching" using SentenceTransformer
- Performs cosine similarity search against stored chunk embeddings
- Filters by course_title metadata
- Returns top 5 most similar chunks

---

### **9. Format Search Results**

**File:** `backend/search_tools.py:88-114`

```python
def _format_results(self, results: SearchResults):
    formatted = []
    sources = []

    for doc, meta in zip(results.documents, results.metadata):
        # Build source attribution
        header = f"[{meta['course_title']} - Lesson {meta['lesson_number']}]"
        source = f"{meta['course_title']} - Lesson {meta['lesson_number']}"

        sources.append(source)
        formatted.append(f"{header}\n{doc}")

    # Store sources for UI
    self.last_sources = sources

    return "\n\n".join(formatted)
```

**Returns to Claude:**
```
[Building Toward Computer Use with Anthropic - Lesson 2]
Prompt caching allows you to reuse previously processed context...

[Building Toward Computer Use with Anthropic - Lesson 3]
When using prompt caching, prefixes of your prompts are cached...
```

---

### **10. Claude Generates Final Response**

**File:** `backend/ai_generator.py:124-135`

```python
# Add tool results to conversation
messages.append({
    "role": "user",
    "content": [{"type": "tool_result", "content": search_results}]
})

# Get final response from Claude
final_response = self.client.messages.create(
    messages=messages,
    system=system_content
    # No tools this time - just generate answer
)

return final_response.content[0].text
```

**Claude's response:**
```
Prompt caching allows you to reuse previously processed context, which reduces
latency and costs. When using prompt caching, prefixes of your prompts are
cached and can be reused across multiple requests...
```

---

### **11. Extract Sources**

**File:** `backend/rag_system.py:129-133`

```python
# Get sources from search tool
sources = self.tool_manager.get_last_sources()
# Returns: [
#   "Building Toward Computer Use with Anthropic - Lesson 2",
#   "Building Toward Computer Use with Anthropic - Lesson 3"
# ]

self.tool_manager.reset_sources()
```

---

### **12. Update Session History**

**File:** `backend/rag_system.py:136-137`

```python
self.session_manager.add_exchange(
    session_id="session_1",
    user_message="What is prompt caching?",
    assistant_message="Prompt caching allows you to reuse..."
)
```

**File:** `backend/session_manager.py:37-40`

```python
def add_exchange(self, session_id, user_message, assistant_message):
    self.add_message(session_id, "user", user_message)
    self.add_message(session_id, "assistant", assistant_message)
    # Keeps last 4 messages (2 exchanges) in memory
```

---

### **13. API Returns Response**

**File:** `backend/app.py:68-72`

```python
return QueryResponse(
    answer="Prompt caching allows you to reuse...",
    sources=[
        "Building Toward Computer Use with Anthropic - Lesson 2",
        "Building Toward Computer Use with Anthropic - Lesson 3"
    ],
    session_id="session_1"
)
```

**JSON Response:**
```json
{
  "answer": "Prompt caching allows you to reuse previously processed context...",
  "sources": [
    "Building Toward Computer Use with Anthropic - Lesson 2",
    "Building Toward Computer Use with Anthropic - Lesson 3"
  ],
  "session_id": "session_1"
}
```

---

### **14. Frontend Displays Response**

**File:** `frontend/script.js:76-85`

```javascript
const data = await response.json();

// Update session ID
currentSessionId = data.session_id;

// Remove loading indicator
loadingMessage.remove();

// Add AI response with sources
addMessage(data.answer, 'assistant', data.sources);
```

**File:** `frontend/script.js:113-138`

```javascript
function addMessage(content, type, sources) {
    // Parse markdown to HTML
    displayContent = marked.parse(content);

    // Build message HTML
    html = `<div class="message-content">${displayContent}</div>`;

    // Add collapsible sources section
    if (sources && sources.length > 0) {
        html += `
            <details class="sources-collapsible">
                <summary>Sources</summary>
                <div>${sources.join(', ')}</div>
            </details>
        `;
    }

    chatMessages.appendChild(messageDiv);
}
```

---

## Summary: Complete Request Flow

```
User Input (Frontend)
    ↓
POST /api/query (script.js:63)
    ↓
FastAPI Endpoint (app.py:56)
    ↓
RAGSystem.query() (rag_system.py:102)
    ↓
SessionManager.get_conversation_history() (session_manager.py:42)
    ↓
AIGenerator.generate_response() (ai_generator.py:43)
    ↓
Claude API Call #1 (with tools)
    ↓
Claude decides: tool_use → "search_course_content"
    ↓
ToolManager.execute_tool() (search_tools.py:135)
    ↓
CourseSearchTool.execute() (search_tools.py:52)
    ↓
VectorStore.search() (vector_store.py:61)
    ├─ _resolve_course_name() (semantic matching)
    └─ course_content.query() (ChromaDB vector search)
    ↓
Format results with sources (search_tools.py:88)
    ↓
Return to Claude as tool_result
    ↓
Claude API Call #2 (generate final answer)
    ↓
Extract sources from tool (rag_system.py:129)
    ↓
Update session history (session_manager.py:37)
    ↓
Return JSON response (app.py:68)
    ↓
Frontend displays message + sources (script.js:85)
```

**Key Data Transformations:**
1. User query → API request (JSON)
2. Query → System prompt + history (string)
3. Query → Tool parameters (dict)
4. Query → Vector embedding (float array)
5. ChromaDB results → Formatted text (string)
6. Tool results → Claude context
7. Claude response → JSON API response
8. Markdown → HTML (frontend)

---

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (JavaScript)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Types: "What is prompt caching?"                                      │
│       │                                                                      │
│       ▼                                                                      │
│  ┌──────────────────────┐                                                   │
│  │  script.js:sendMessage()  │                                              │
│  └──────────┬───────────┘                                                   │
│             │                                                                │
│             │  POST /api/query                                               │
│             │  {                                                             │
│             │    "query": "What is prompt caching?",                         │
│             │    "session_id": "session_1"                                   │
│             │  }                                                             │
│             │                                                                │
└─────────────┼────────────────────────────────────────────────────────────────┘
              │
              │ HTTP Request
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND (Python)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  app.py:query_documents()                                          │    │
│  │  • Validates request                                               │    │
│  │  • Creates/retrieves session_id                                    │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            │ Calls rag_system.query(query, session_id)                      │
│            ▼                                                                 │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  rag_system.py:query()                                             │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │ Step 1: Build prompt                                         │  │    │
│  │  │         "Answer this question about course materials: ..."   │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  │            │                                                        │    │
│  │            ▼                                                        │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │ Step 2: Get conversation history                             │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └────────────┼───────────────────────────────────────────────────────┘    │
│               │                                                              │
│               │ Calls session_manager.get_conversation_history()             │
│               ▼                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  session_manager.py:get_conversation_history()                     │    │
│  │  • Retrieves last 2 exchanges (4 messages max)                     │    │
│  │  • Formats as: "User: ...\nAssistant: ...\n..."                   │    │
│  │  Returns: "User: previous q\nAssistant: previous a"               │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            │ Returns formatted history string                                │
│            ▼                                                                 │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  rag_system.py (continued)                                         │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │ Step 3: Generate AI response with tools                      │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └────────────┼───────────────────────────────────────────────────────┘    │
│               │                                                              │
│               │ Calls ai_generator.generate_response(query, history, tools)  │
│               ▼                                                              │
└───────────────┼──────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       AI GENERATOR & TOOL EXECUTION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  ai_generator.py:generate_response()                               │    │
│  │  • Builds system prompt with history                               │    │
│  │  • Prepares tool definitions                                       │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            │ ╔═══════════════════════════════════════════════╗              │
│            └─▶ CLAUDE API CALL #1 (Initial Request)          ║              │
│              ║  model: claude-sonnet-4-20250514              ║              │
│              ║  system: <prompt> + <history>                 ║              │
│              ║  messages: [{"role": "user", "content": ...}] ║              │
│              ║  tools: [search_course_content definition]    ║              │
│              ║  tool_choice: auto                            ║              │
│              ╚══════════════════┬════════════════════════════╝              │
│                                 │                                            │
│                                 ▼                                            │
│              ╔═══════════════════════════════════════════════╗              │
│              ║  CLAUDE DECIDES: "I need to search"           ║              │
│              ║  stop_reason: "tool_use"                      ║              │
│              ║  content: [                                   ║              │
│              ║    {                                          ║              │
│              ║      type: "tool_use",                        ║              │
│              ║      name: "search_course_content",           ║              │
│              ║      input: {                                 ║              │
│              ║        "query": "prompt caching",             ║              │
│              ║        "course_name": "Building Toward..."    ║              │
│              ║      }                                        ║              │
│              ║    }                                          ║              │
│              ║  ]                                            ║              │
│              ╚══════════════════┬════════════════════════════╝              │
│                                 │                                            │
│  ┌──────────────────────────────▼───────────────────────────────────────┐  │
│  │  ai_generator.py:_handle_tool_execution()                            │  │
│  │  • Extracts tool call parameters                                     │  │
│  │  • Calls tool_manager.execute_tool(name, **params)                   │  │
│  └─────────┬────────────────────────────────────────────────────────────┘  │
│            │                                                                 │
│            │ Calls tool_manager.execute_tool("search_course_content", ...)  │
│            ▼                                                                 │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  search_tools.py:ToolManager.execute_tool()                        │    │
│  │  • Routes to CourseSearchTool                                      │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            │ Calls search_tool.execute(query, course_name, lesson_number)   │
│            ▼                                                                 │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  search_tools.py:CourseSearchTool.execute()                        │    │
│  │  • Delegates to vector_store.search()                              │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
└────────────┼─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VECTOR STORE & CHROMADB                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  vector_store.py:search()                                          │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │ Phase 1: Resolve Course Name (Semantic Matching)            │  │    │
│  │  │  Input: "Building Toward..."                                │  │    │
│  │  │  ▼                                                           │  │    │
│  │  │  Query course_catalog collection                            │  │    │
│  │  │  • Generate embedding for "Building Toward..."              │  │    │
│  │  │  • Find closest course title                                │  │    │
│  │  │  ▼                                                           │  │    │
│  │  │  Returns: "Building Toward Computer Use with Anthropic"     │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  │            │                                                        │    │
│  │            ▼                                                        │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │ Phase 2: Search Course Content (Vector Similarity)          │  │    │
│  │  │  Input: query="prompt caching"                               │  │    │
│  │  │         filter={"course_title": "Building Toward..."}        │  │    │
│  │  │  ▼                                                           │  │    │
│  │  │  ┌────────────────────────────────────────────────────┐     │  │    │
│  │  │  │  CHROMADB: course_content collection              │     │  │    │
│  │  │  │  1. Generate embedding for "prompt caching"       │     │  │    │
│  │  │  │     using SentenceTransformer                     │     │  │    │
│  │  │  │  2. Compute cosine similarity with all chunks     │     │  │    │
│  │  │  │  3. Apply course_title filter                     │     │  │    │
│  │  │  │  4. Return top 5 most similar chunks              │     │  │    │
│  │  │  └────────────────────────────────────────────────────┘     │  │    │
│  │  │  ▼                                                           │  │    │
│  │  │  Returns: {                                                  │  │    │
│  │  │    documents: ["chunk1", "chunk2", ...],                    │  │    │
│  │  │    metadata: [{course_title: "...", lesson_number: 2}, ...],│  │    │
│  │  │    distances: [0.23, 0.31, ...]                             │  │    │
│  │  │  }                                                           │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            │ Returns SearchResults object                                   │
│            ▼                                                                 │
└────────────┼─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACK TO SEARCH TOOL                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  search_tools.py:_format_results()                                 │    │
│  │  For each result:                                                  │    │
│  │    • Build header: "[Course - Lesson X]"                           │    │
│  │    • Track source: "Course - Lesson X"                             │    │
│  │    • Combine: header + content                                     │    │
│  │                                                                     │    │
│  │  Returns formatted string:                                         │    │
│  │  ┌─────────────────────────────────────────────────────────────┐  │    │
│  │  │ [Building Toward Computer Use - Lesson 2]                   │  │    │
│  │  │ Prompt caching allows you to reuse previously processed...  │  │    │
│  │  │                                                              │  │    │
│  │  │ [Building Toward Computer Use - Lesson 3]                   │  │    │
│  │  │ When using prompt caching, prefixes of your prompts...      │  │    │
│  │  └─────────────────────────────────────────────────────────────┘  │    │
│  │                                                                     │    │
│  │  Also stores: last_sources = [                                     │    │
│  │    "Building Toward Computer Use - Lesson 2",                      │    │
│  │    "Building Toward Computer Use - Lesson 3"                       │    │
│  │  ]                                                                  │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            │ Returns formatted string to AI Generator                        │
│            ▼                                                                 │
└────────────┼─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BACK TO AI GENERATOR (Final Response)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  ai_generator.py:_handle_tool_execution() (continued)              │    │
│  │  • Add tool results to conversation:                               │    │
│  │    messages.append({                                               │    │
│  │      role: "user",                                                 │    │
│  │      content: [{                                                   │    │
│  │        type: "tool_result",                                        │    │
│  │        tool_use_id: "...",                                         │    │
│  │        content: "[Course - Lesson 2]\nPrompt caching allows..."    │    │
│  │      }]                                                            │    │
│  │    })                                                              │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            │ ╔═══════════════════════════════════════════════╗              │
│            └─▶ CLAUDE API CALL #2 (Final Generation)         ║              │
│              ║  model: claude-sonnet-4-20250514              ║              │
│              ║  system: <same as before>                     ║              │
│              ║  messages: [                                  ║              │
│              ║    {role: "user", content: original query},   ║              │
│              ║    {role: "assistant", content: tool_use},    ║              │
│              ║    {role: "user", content: tool_results}      ║              │
│              ║  ]                                            ║              │
│              ║  NO TOOLS this time                           ║              │
│              ╚══════════════════┬════════════════════════════╝              │
│                                 │                                            │
│                                 ▼                                            │
│              ╔═══════════════════════════════════════════════╗              │
│              ║  CLAUDE GENERATES FINAL ANSWER                ║              │
│              ║  stop_reason: "end_turn"                      ║              │
│              ║  content: [{                                  ║              │
│              ║    type: "text",                              ║              │
│              ║    text: "Prompt caching allows you to..."    ║              │
│              ║  }]                                           ║              │
│              ╚══════════════════┬════════════════════════════╝              │
│                                 │                                            │
│  ┌──────────────────────────────▼───────────────────────────────────────┐  │
│  │  Returns final_response.content[0].text                              │  │
│  │  "Prompt caching allows you to reuse previously processed..."        │  │
│  └─────────┬────────────────────────────────────────────────────────────┘  │
│            │                                                                 │
└────────────┼─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BACK TO RAG SYSTEM (Finalization)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  rag_system.py:query() (continued)                                 │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │ Step 4: Extract sources                                      │  │    │
│  │  │  sources = tool_manager.get_last_sources()                   │  │    │
│  │  │  Returns: ["Course - Lesson 2", "Course - Lesson 3"]         │  │    │
│  │  │  tool_manager.reset_sources()                                │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  │            │                                                        │    │
│  │            ▼                                                        │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │ Step 5: Update session history                               │  │    │
│  │  │  session_manager.add_exchange(                               │  │    │
│  │  │    session_id,                                               │  │    │
│  │  │    "What is prompt caching?",                                │  │    │
│  │  │    "Prompt caching allows you to..."                         │  │    │
│  │  │  )                                                            │  │    │
│  │  │  • Stores in sessions["session_1"]                           │  │    │
│  │  │  • Keeps last 4 messages (2 exchanges)                       │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  │            │                                                        │    │
│  │            ▼                                                        │    │
│  │  Returns: (response, sources)                                      │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
└────────────┼─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BACK TO FASTAPI                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  app.py:query_documents() (continued)                              │    │
│  │  Returns QueryResponse:                                            │    │
│  │  {                                                                 │    │
│  │    "answer": "Prompt caching allows you to reuse...",              │    │
│  │    "sources": [                                                    │    │
│  │      "Building Toward Computer Use - Lesson 2",                    │    │
│  │      "Building Toward Computer Use - Lesson 3"                     │    │
│  │    ],                                                              │    │
│  │    "session_id": "session_1"                                       │    │
│  │  }                                                                 │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            │ HTTP Response (JSON)                                            │
│            ▼                                                                 │
└────────────┼─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BACK TO FRONTEND (Display)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  script.js:sendMessage() (continued)                               │    │
│  │  const data = await response.json()                                │    │
│  │                                                                     │    │
│  │  • Store session_id for next query                                 │    │
│  │  • Remove loading indicator                                        │    │
│  │  • Call addMessage(data.answer, 'assistant', data.sources)         │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            ▼                                                                 │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  script.js:addMessage()                                            │    │
│  │  • Parse markdown to HTML using marked.js                          │    │
│  │  • Create message div with formatted content                       │    │
│  │  • Add collapsible sources section if sources exist                │    │
│  │  • Append to chat messages container                               │    │
│  │  • Auto-scroll to bottom                                           │    │
│  └─────────┬──────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            ▼                                                                 │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    USER SEES RESPONSE                               │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │  Prompt caching allows you to reuse previously processed     │  │    │
│  │  │  context, which reduces latency and costs. When using        │  │    │
│  │  │  prompt caching, prefixes of your prompts are cached...      │  │    │
│  │  │                                                               │  │    │
│  │  │  ▼ Sources                                                    │  │    │
│  │  │    Building Toward Computer Use - Lesson 2,                  │  │    │
│  │  │    Building Toward Computer Use - Lesson 3                   │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                              KEY DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

  User Query (string)
       ↓
  JSON Request
       ↓
  RAG System Orchestration
       ↓
  Session History (string) ─────────┐
       ↓                            │
  Claude API Call #1 (with tools) ←─┘
       ↓
  Tool Use Decision
       ↓
  Vector Search (query → embedding → similarity)
       ↓
  Formatted Results (string)
       ↓
  Claude API Call #2 (no tools)
       ↓
  Final Answer (string)
       ↓
  Extract Sources (list)
       ↓
  Update Session History
       ↓
  JSON Response
       ↓
  Markdown → HTML
       ↓
  Display to User

═══════════════════════════════════════════════════════════════════════════════
                         STORAGE & STATE MANAGEMENT
═══════════════════════════════════════════════════════════════════════════════

┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│   ChromaDB Files     │  │   Session Memory     │  │   Frontend State     │
│   (Persistent)       │  │   (In-Memory)        │  │   (Browser)          │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ course_catalog:      │  │ sessions = {         │  │ currentSessionId     │
│  - Course metadata   │  │   "session_1": [     │  │ chatMessages (DOM)   │
│  - Embeddings        │  │     Message(...),    │  │                      │
│                      │  │     Message(...),    │  │                      │
│ course_content:      │  │     ...              │  │                      │
│  - Text chunks       │  │   ]                  │  │                      │
│  - Embeddings        │  │ }                    │  │                      │
│  - Metadata          │  │                      │  │                      │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

---

## Key Highlights

### Two-Phase Claude Interaction

The system uses Claude's tool-calling pattern with two distinct API calls:

1. **Call #1 (Tool Use)**: Claude receives the query and decides to use the `search_course_content` tool
2. **Call #2 (Generation)**: Claude receives search results and generates the final answer

### Vector Search Mechanics

The vector search involves:

1. **Course Name Resolution**: Fuzzy matching of course names using semantic search on the `course_catalog` collection
2. **Content Search**: Embedding-based similarity search on the `course_content` collection with metadata filtering
3. **Result Formatting**: Chunks are formatted with course and lesson context headers

### Session Management

- Maintains last 2 exchanges (4 messages) per session
- Formatted as context string for Claude
- Session ID persisted across requests

### Source Attribution

- Search tool tracks sources during execution
- Sources extracted after response generation
- Displayed in collapsible UI element
- Reset after each query to prevent leakage

---

## File Reference Index

| Component | File | Key Functions |
|-----------|------|---------------|
| Frontend Entry | `frontend/script.js` | `sendMessage()`, `addMessage()` |
| API Layer | `backend/app.py` | `query_documents()`, `get_course_stats()` |
| Orchestration | `backend/rag_system.py` | `query()`, `add_course_folder()` |
| AI Integration | `backend/ai_generator.py` | `generate_response()`, `_handle_tool_execution()` |
| Tool System | `backend/search_tools.py` | `CourseSearchTool.execute()`, `ToolManager.execute_tool()` |
| Vector Search | `backend/vector_store.py` | `search()`, `_resolve_course_name()` |
| Session Tracking | `backend/session_manager.py` | `get_conversation_history()`, `add_exchange()` |

---

Generated: 2025-12-12
