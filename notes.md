# Notes

## MCP Servers (Model Context Protocol)

MCP stands for Model Context Protocol — an open standard that lets Claude connect to external tools and data sources, acting like a plugin system.

By default Claude Code can read files, run bash commands, search code, etc. MCP servers extend that with new capabilities.

**What we used:** The Playwright MCP server gave Claude browser control tools — `browser_navigate`, `browser_take_screenshot`, and `browser_evaluate` — allowing Claude to interact with a live browser directly instead of asking the user to describe what they see.

**Other examples of MCP servers:**
- Gmail — read/send emails
- Google Calendar — check/create events
- Databases — query Postgres or SQLite
- Slack — post messages

**How they work:**
1. An MCP server runs as a separate process on your machine (or remotely)
2. Claude Code connects to it via the `/mcp` command or settings
3. The server exposes tools that Claude can call just like any built-in tool

## run.sh vs Manual uvicorn Command

Both `./run.sh` and `cd backend && uv run uvicorn app:app --reload --port 8000` start the same server. The difference is that `run.sh` adds safety checks before launching:

1. Creates the `/docs` directory if it doesn't exist (`mkdir -p docs`)
2. Validates that the `backend/` directory exists and exits with an error if not
3. Prints a reminder to check your `ANTHROPIC_API_KEY`

Then it runs the identical `uvicorn` command. Use `./run.sh` for day-to-day startup; use the manual command only if the script fails or you need to customize flags.

## Setting Up a Custom Skill (/log command)

Custom slash commands in Claude Code are called **skills** and must follow a specific folder structure to be recognized.

**Correct structure:**
```
.claude/skills/<skill-name>/SKILL.md
```

**SKILL.md requires two parts:**
1. YAML frontmatter (between `---` markers) with fields like `name`, `description`, and `disable-model-invocation: true` to only trigger on explicit use
2. Markdown instructions telling Claude what to do when the skill is invoked

**What didn't work:**
- `.claude/commands/log.md` — the old format, no longer supported

**Important:** Claude Code only scans for skills on startup — a full restart is required after creating a new skill for it to be recognized.

## Adding a Second Tool to the RAG System (CourseOutlineTool)

New tools in this RAG system must implement the `Tool` ABC defined in `search_tools.py` (two methods: `get_tool_definition()` and `execute()`), then be registered with `ToolManager.register_tool()` in `rag_system.py`.

**What was built:** `CourseOutlineTool` — answers "what lessons does course X have?" queries without doing a content search. It takes a course name (partial matches work), fuzzy-resolves it via `VectorStore._resolve_course_name()`, then fetches structured metadata (title, course link, lesson numbers and titles) from the `course_catalog` ChromaDB collection.

**Key design points:**
- Course metadata is already stored in `course_catalog` with a `lessons_json` field (a JSON string of `[{lesson_number, lesson_title, lesson_link}]`) — no re-indexing needed
- `VectorStore.get_course_outline()` was added as a public method that resolves the name and parses `lessons_json` into a clean dict
- The system prompt in `ai_generator.py` was updated to distinguish the two tools: use `get_course_outline` for structure/outline queries, `search_course_content` for content queries
- The tool is registered alongside `CourseSearchTool` in `RAGSystem.__init__()`

## tools vs tool_manager in the Anthropic Tool-Calling Flow

These are two separate things that work together when Claude uses a tool.

**`tools`** is a plain list of JSON schema definitions sent to the Anthropic API. It tells Claude what tools exist, what they do, and what inputs they accept. Claude reads these and decides on its own whether to call one. Produced by `ToolManager.get_tool_definitions()` in `search_tools.py`.

**`tool_manager`** is the Python `ToolManager` object that holds the actual tool instances and executes them. When Claude replies with `stop_reason = "tool_use"`, `AIGenerator` calls `tool_manager.execute_tool(name, **inputs)`, which routes to the right tool's `execute()` method and returns real results.

**Why they're separate:** Claude only ever sees the JSON schema (`tools`) — it has no access to your Python code. The five-step loop is:
1. Send Claude the tool schemas
2. Claude replies: "call tool X with these inputs"
3. Your code runs `tool_manager.execute_tool(...)` locally
4. You send Claude the result
5. Claude synthesizes the final answer

Both `tools` and `tool_manager` pre-existed the test files added today — the tests only verify their behavior.

## Defensive Gap: stop_reason="tool_use" Without a tool_manager

In `ai_generator.py`, the condition that routes to tool execution is:

```python
if response.stop_reason == "tool_use" and tool_manager:
    return self._handle_tool_execution(...)
return response.content[0].text  # ← danger zone
```

If Claude decides to use a tool but `tool_manager` is None, the `and` makes the whole condition False and the code falls through to `.text` on a tool-use content block — which has no `.text` attribute in real Anthropic responses → `AttributeError` crash.

**Why it doesn't crash in production:** `RAGSystem.query()` always passes both `tools` and `tool_manager` together, so the None path is never reached through the browser UI.

**Why the test missed it:** `MagicMock()` auto-creates any attribute accessed on it, so `mock_block.text` returns another MagicMock instead of raising `AttributeError`. The test expected a crash but got silent success.

**The fix:** Split the `and` into nested `if` statements so the missing-tool_manager case returns a graceful error message instead of crashing. Update the test to assert the error message rather than expecting `AttributeError`.

## Plan A: Sequential Tool Calling via Loop in `_handle_tool_execution`

The approach to support up to 2 chained tool calls per query (Plan A) keeps the existing method name and converts its body into a bounded loop.

**Key design decisions:**
- `MAX_ROUNDS = 2` as a class constant on `AIGenerator` — policy decision, not a runtime param
- `_handle_tool_execution` signature stays the same; `base_params` already contains `tools` and `tool_choice` from `generate_response`
- Each loop iteration: execute tools → append assistant + tool_result messages → check stop conditions
- **3 stop conditions:** (a) Claude returns no tool_use mid-loop → early return from inside loop; (b) tool raises exception → break to forced final call; (c) MAX_ROUNDS exhausted → break to forced final call
- Intermediate calls include `tools` so Claude can chain; the forced final call always strips them
- Tool returning an error *string* is NOT an error — it's valid content Claude can reason about; only exceptions trigger early exit
- System prompt updated: remove "one tool call max", add guidance that chaining is allowed when the second call depends on the first

**API call counts by scenario:**

| Scenario | API calls | Tool calls |
|---|---|---|
| Direct answer | 1 | 0 |
| 1 tool → answer | 2 | 1 |
| 2 tools → answer | 3 | 2 |
| Tool error string | 2 | 1 |
| Tool exception | 2 | 1 |

## Semantic vs. Fuzzy Course Name Resolution

`_resolve_course_name()` in `vector_store.py` is sometimes called "fuzzy matching" but it's actually **semantic/vector search** — more powerful than traditional fuzzy string matching (e.g. Levenshtein distance).

**How it works:**
1. Your input (e.g. `"RAG"`) is converted to an embedding vector by `sentence-transformers`
2. ChromaDB finds the course title vector with the highest cosine similarity
3. That title is returned — even if the input words don't appear in the title at all

So `"retrieval augmented generation course"` resolves to `"Introduction to RAG"` purely on semantic similarity, not string overlap.

**Important limitation:** There is no similarity threshold — it always returns the closest match even for completely unrelated queries. This is why `test_get_course_outline_returns_none_for_empty_catalog` tests the empty-catalog case (guaranteed None) rather than an "unrelated query" case (which would still return *something*).

## Why .claude/settings.local.json Is Not Committed with Feature Changes

`.claude/settings.local.json` holds local IDE preferences, permissions, and hook settings personal to one machine. Even though it is a tracked file, it should not be bundled into feature commits — doing so would add noise and could overwrite another developer's local configuration. It is staged and committed separately, only when its changes are intentional.
