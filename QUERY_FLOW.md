# Query Flow: Frontend to Backend

This document traces how a user's query is processed from the frontend UI through the entire backend system.

---

## 1. Frontend: User Submits Query

**File:** `frontend/script.js`

### Flow:
1. User types a question in the chat input and presses Enter or clicks "Send"
2. `sendMessage()` function is triggered
3. Frontend captures:
   - `query` - the user's question (trimmed)
   - `currentSessionId` - existing session ID (if available)

### API Call:
```javascript
const response = await fetch(`${API_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        query: query,
        session_id: currentSessionId
    })
});
```

- **Endpoint:** `/api/query` (POST)
- **Request Body:** `QueryRequest` model with query and optional session_id
- **Response:** `QueryResponse` with answer, sources, and session_id

### UI Updates:
- User message is displayed in chat
- Loading animation is shown
- Response replaces loading animation
- Sources are displayed in collapsible section
- New session_id is stored if this was the first query

---

## 2. Backend API: Request Handling

**File:** `backend/app.py`

### Endpoint Handler:
```python
@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
```

### Processing:
1. **Session Management**
   - Check if `session_id` is provided in request
   - If not, create new session: `rag_system.session_manager.create_session()`
   - Returns session ID in format: `session_1`, `session_2`, etc.

2. **Query Processing**
   - Call `rag_system.query(request.query, session_id)`
   - Returns tuple: `(answer: str, sources: List[str])`

3. **Response Construction**
   - Create `QueryResponse` with:
     - `answer` - the AI-generated response
     - `sources` - list of course/lesson references
     - `session_id` - for maintaining conversation

---

## 3. RAG System: Query Orchestration

**File:** `backend/rag_system.py`

### Core Logic:
```python
def query(self, query: str, session_id: Optional[str]) -> Tuple[str, List[str]]:
```

### Processing Steps:

#### Step 1: Conversation Context
- Retrieve conversation history if session exists
- `history = self.session_manager.get_conversation_history(session_id)`
- Returns formatted string of previous exchanges (limited by `MAX_HISTORY`)

#### Step 2: Create Prompt
- Wrap query in system instruction: `"Answer this question about course materials: {query}"`
- This prompt becomes the user message sent to Claude

#### Step 3: Generate Response with Tools
- Call `self.ai_generator.generate_response()`
- Pass:
  - `query` - the wrapped user prompt
  - `conversation_history` - previous context (optional)
  - `tools` - available tools (CourseSearchTool)
  - `tool_manager` - for executing tools

#### Step 4: Extract Sources
- Get sources from tool execution: `self.tool_manager.get_last_sources()`
- Reset sources for next query: `self.tool_manager.reset_sources()`

#### Step 5: Update Session History
- Add user query and AI response to conversation: `self.session_manager.add_exchange(session_id, query, response)`
- Conversation history is limited to `MAX_HISTORY` exchanges (default: 5)

#### Step 6: Return Results
- Return tuple: `(response_text, sources_list)`

---

## 4. AI Generator: Claude API Integration

**File:** `backend/ai_generator.py`

### System Prompt:
- Instructs Claude to:
  - Use search tool **only** for course-specific questions
  - Max one search per query
  - Synthesize results into fact-based responses
  - Answer general knowledge without searching
  - No meta-commentary about the search process

### Initial API Call:

```python
response = self.client.messages.create(
    model=model,
    temperature=0,
    max_tokens=800,
    messages=[{"role": "user", "content": query}],
    system=system_content,  # Includes conversation history if available
    tools=tools,  # Available tools passed if provided
    tool_choice={"type": "auto"}  # Let Claude choose when to use tools
)
```

### Tool Use Decision:
- Claude analyzes the query
- If tool use is needed (`response.stop_reason == "tool_use"`):
  - Continue to tool execution
- If direct answer is possible (`response.stop_reason == "end_turn"`):
  - Return response directly: `response.content[0].text`

---

## 5. Tool Execution: Search Tool

**File:** `backend/search_tools.py`

### Tool Definition:
The `CourseSearchTool` is registered with Claude with:
- **Name:** `search_course_content`
- **Parameters:**
  - `query` (required) - what to search for
  - `course_name` (optional) - filter by course
  - `lesson_number` (optional) - filter by lesson

### Execution Flow:

#### Step 1: Tool Manager Receives Request
- `ToolManager.execute_tool("search_course_content", query=..., course_name=..., lesson_number=...)`

#### Step 2: CourseSearchTool Executes
```python
def execute(self, query: str, course_name: Optional[str] = None, lesson_number: Optional[int] = None) -> str:
```

#### Step 3: Call Vector Store Search
- `self.store.search(query=query, course_name=course_name, lesson_number=lesson_number)`
- Vector store returns `SearchResults` object

#### Step 4: Format Results
- Loop through results and format with context:
  - `[CourseTitle - Lesson N]` headers
  - Content excerpt
- Extract metadata into sources: `"CourseTitle - Lesson N"`
- Store sources: `self.last_sources = sources`

#### Step 5: Return Formatted String
- Multi-part string with course/lesson headers and content
- This string is sent back to Claude

---

## 6. Vector Store: Semantic Search

**File:** `backend/vector_store.py`

### Initialization:
- Uses ChromaDB for persistent vector storage
- Two collections:
  1. **course_catalog** - course titles and metadata (for course resolution)
  2. **course_content** - actual course material chunks

### Search Process:

#### Step 1: Course Name Resolution (if provided)
```python
if course_name:
    course_title = self._resolve_course_name(course_name)
```
- Performs semantic search in `course_catalog` collection
- Matches user's course name to actual course title
- Handles partial matches (e.g., "MCP" → "Model Context Protocol Course")

#### Step 2: Build Filter
```python
filter_dict = self._build_filter(course_title, lesson_number)
```
- If course_title provided: filter by `{"course_title": course_title}`
- If lesson_number provided: filter by `{"lesson_number": lesson_number}`
- If both: combine with `$and` operator

#### Step 3: Semantic Search
```python
results = self.course_content.query(
    query_texts=[query],
    n_results=search_limit,  # Default: 5
    where=filter_dict
)
```
- Uses SentenceTransformer embeddings to find semantic matches
- Returns top N matching documents with:
  - Document text (content chunks)
  - Metadata (course_title, lesson_number, chunk_index)
  - Distances (similarity scores)

#### Step 4: Return Results
- Package into `SearchResults` dataclass
- Or return error message if no results found

---

## 7. Response Generation: AI Processes Tool Results

### Back in AI Generator:

#### Multi-turn Conversation:
1. **First Response:** Claude decides to use tool (or returns direct answer)
2. **Tool Execution:** Tool is executed and results collected
3. **Tool Result Message:** Results are formatted as a new user message
4. **Second API Call:** Claude processes tool results

```python
# Send tool results back to Claude
messages.append({"role": "user", "content": tool_results})

# Claude generates final response with tool context
final_response = self.client.messages.create(
    **api_params,
    messages=messages  # Now includes tool use and tool results
)
```

### Response Format:
- Claude synthesizes tool results into a natural, conversational answer
- No meta-commentary about the search process
- Direct, focused response to the original query

---

## 8. Response Flow Back to Frontend

### RAG System returns:
- `(response_text, sources_list)`

### Backend API constructs:
```python
QueryResponse(
    answer=response_text,
    sources=sources_list,
    session_id=session_id
)
```

### Frontend receives JSON:
```json
{
    "answer": "The answer to the user's question...",
    "sources": ["Course Title - Lesson 1", "Course Title - Lesson 2"],
    "session_id": "session_1"
}
```

### Frontend updates UI:
1. Remove loading animation
2. Display assistant message with markdown rendering
3. Show sources in collapsible details section
4. Save session_id for future queries in same conversation
5. Scroll to new message

---

## Summary: Complete Query Lifecycle

```
USER INPUT
    ↓
[Frontend] sendMessage() → POST /api/query
    ↓
[Backend] query_documents() → rag_system.query()
    ↓
[RAG System] Create context, call ai_generator.generate_response()
    ↓
[AI Generator] First Claude API call with tools
    ↓
[Decision] Does Claude need to search?
    ├─ YES → [Tool Execution]
    │         ↓
    │      [Vector Store] Search with embeddings
    │         ↓
    │      [Tool Results] Formatted search results
    │         ↓
    │      [AI Generator] Second Claude API call with results
    │         ↓
    └─ NO → [Direct Response] Return Claude's answer immediately
    ↓
[RAG System] Collect sources, update session history
    ↓
[Backend] Return QueryResponse (answer, sources, session_id)
    ↓
[Frontend] Update UI with response and sources
    ↓
USER SEES ANSWER
```

---

## Key Design Patterns

### 1. Session Management
- Sessions are created on-demand
- Conversation history is maintained per session
- Limited to last 5 exchanges to manage context window

### 2. Tool-Based Search
- Tools allow Claude to decide **when** to search
- RAG system doesn't force search; Claude chooses
- Sources are extracted after tool execution

### 3. Semantic Search
- Uses SentenceTransformer embeddings for semantic understanding
- Supports partial course name matching
- Filters by course and lesson metadata

### 4. Multi-turn API Calls
- First call: Claude decides on action
- Second call (if needed): Claude processes tool results
- Single response returned to user

### 5. Error Handling
- Frontend shows error messages
- Backend returns HTTP 500 on exceptions
- Vector store returns specific error messages

---

## Data Models

### Frontend ↔ Backend
- `QueryRequest`: {query, session_id?}
- `QueryResponse`: {answer, sources[], session_id}

### Internal
- `Course`: {title, instructor, course_link, lessons[]}
- `CourseChunk`: {content, course_title, lesson_number, chunk_index}
- `SearchResults`: {documents[], metadata[], distances[], error?}
- `Message`: {role, content}

---

## Performance Considerations

1. **Embedding Model**: SentenceTransformer loaded once, reused
2. **Claude API Calls**: Efficient parameter building, caching system prompt
3. **Vector Store**: ChromaDB persistent storage, quick semantic search
4. **Session History**: Limited to 5 exchanges to keep context manageable
5. **Tool Caching**: One search per query maximum (enforced by prompt)
