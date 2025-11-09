# RAG System API Tests

This directory contains comprehensive API endpoint tests for the RAG chatbot system.

## Overview

The test suite covers all FastAPI endpoints with mocked dependencies to ensure fast, reliable testing without requiring external services (ChromaDB, Anthropic API, etc.).

## Test Structure

```
backend/tests/
├── conftest.py              # Shared fixtures and test configuration
├── test_api_query.py        # Tests for POST /api/query endpoint
├── test_api_courses.py      # Tests for GET /api/courses endpoint
├── test_api_root.py         # Tests for GET / (root) endpoint
└── README.md                # This file
```

## Running Tests

### Run All API Tests

```bash
# From project root
uv run pytest backend/tests/test_api_*.py -v
```

### Run Specific Test File

```bash
uv run pytest backend/tests/test_api_query.py -v
```

### Run Tests by Marker

```bash
# Run only API tests
uv run pytest -m api

# Run unit tests
uv run pytest -m unit

# Run integration tests
uv run pytest -m integration
```

### Run Specific Test

```bash
uv run pytest backend/tests/test_api_query.py::TestQueryEndpoint::test_query_without_session_id -v
```

## Test Coverage

### `/api/query` Endpoint (13 tests)

Tests for the query processing endpoint:

- **Session Management**: Tests with/without session_id
- **Response Structure**: Validates response format and types
- **Error Handling**: Invalid JSON, missing fields, RAG system errors
- **Edge Cases**: Empty queries, long queries, special/unicode characters
- **Functionality**: Multiple requests, session persistence, sources matching

### `/api/courses` Endpoint (13 tests)

Tests for the course statistics endpoint:

- **Successful Retrieval**: Basic course list fetching
- **Response Structure**: Type validation and field presence
- **Data Consistency**: Total count matches list length
- **Edge Cases**: Empty catalog, large catalogs (100+ courses)
- **Error Handling**: RAG system failures
- **Special Characters**: Unicode and HTML characters in titles
- **HTTP Methods**: Verify only GET is allowed

### `/` Root Endpoint (9 tests)

Tests for the health check endpoint:

- **Basic Functionality**: Status and message validation
- **Response Format**: JSON content type verification
- **Consistency**: Multiple requests return same data
- **Performance**: Fast response time check (< 1 second)
- **Side Effects**: No state modification
- **HTTP Methods**: Verify proper method restrictions

## Test Fixtures

### Core Fixtures (conftest.py)

**`mock_rag_system`**: Mock RAG system with pre-configured responses
- Simulates query processing
- Returns sample course analytics
- Handles session management

**`test_app`**: FastAPI test application
- Defines API endpoints inline
- Avoids static file mounting issues
- Uses mock RAG system for all operations

**`async_client`**: Async HTTP client for API testing
- Built with httpx.AsyncClient
- Configured to use test_app
- Supports all HTTP methods

### Data Fixtures

**`sample_course`**: Example course with 2 lessons
**`sample_chunks`**: Example course content chunks
**`sample_search_results`**: Mock vector search results
**`empty_search_results`**: Empty search results
**`error_search_results`**: Error state results

## Key Design Decisions

### Why Inline API Definitions?

The `test_app` fixture defines FastAPI endpoints inline rather than importing from `app.py` to avoid:

1. **Static file mounting errors**: The production app mounts `../frontend` which doesn't exist in test environment
2. **Database initialization**: Tests don't need real ChromaDB
3. **Startup events**: Tests don't need document loading
4. **API key requirements**: Tests use mocked Anthropic client

This approach ensures:
- Fast test execution (no external dependencies)
- Reliable tests (no network calls)
- Isolated testing (no side effects between tests)

### Mock Strategy

All tests use mocked dependencies:
- **RAG System**: Returns predefined responses
- **Vector Store**: No real ChromaDB connection
- **AI Generator**: No actual API calls to Anthropic
- **Session Manager**: In-memory session handling

Benefits:
- Tests run in < 1 second
- No API costs during testing
- Deterministic test results
- Can test error conditions easily

## Test Markers

Tests use pytest markers for categorization:

- `@pytest.mark.api`: API endpoint tests (all tests in this suite)
- `@pytest.mark.unit`: Unit tests for individual components
- `@pytest.mark.integration`: Integration tests across components

## Configuration

Test configuration is in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["backend/tests"]
asyncio_mode = "auto"
addopts = ["-v", "--strict-markers", "--tb=short"]
```

## Writing New Tests

### Adding API Endpoint Tests

1. Create new test file: `test_api_<endpoint_name>.py`
2. Import fixtures: `from httpx import AsyncClient`
3. Mark tests with `@pytest.mark.api`
4. Use `async_client` fixture for HTTP requests
5. Use `mock_rag_system` fixture to configure responses

Example:

```python
@pytest.mark.api
class TestNewEndpoint:
    async def test_new_endpoint_success(self, async_client: AsyncClient):
        response = await async_client.get("/api/new")
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
```

### Modifying Mock Responses

To change mock behavior in a specific test:

```python
async def test_custom_behavior(self, async_client, mock_rag_system):
    # Override default mock behavior
    mock_rag_system.query.return_value = (
        "Custom answer",
        ["Custom source"],
        ["https://custom.link"]
    )

    response = await async_client.post(
        "/api/query",
        json={"query": "test"}
    )

    assert "Custom answer" in response.json()["answer"]
```

## Continuous Integration

To integrate with CI/CD:

```yaml
# .github/workflows/test.yml
- name: Run API Tests
  run: |
    uv sync --dev
    uv run pytest backend/tests/test_api_*.py -v --junitxml=test-results.xml
```

## Troubleshooting

### Tests Not Found

If pytest can't find tests:
```bash
# Check test discovery
uv run pytest --collect-only backend/tests/

# Ensure you're in project root
pwd  # Should show .../starting-ragchatbot-codebase
```

### Fixture Not Found

If fixtures are missing:
```bash
# Verify conftest.py is in same directory
ls backend/tests/conftest.py

# Check fixture is defined
uv run pytest --fixtures backend/tests/ | grep <fixture_name>
```

### Import Errors

If tests can't import modules:
```bash
# Ensure backend modules are importable
cd backend
uv run python -c "import models, vector_store, search_tools"
```

## Future Enhancements

Potential additions to test suite:

1. **Performance Tests**: Measure response times under load
2. **Parameterized Tests**: Test multiple inputs with @pytest.mark.parametrize
3. **Contract Tests**: Verify API matches OpenAPI schema
4. **End-to-End Tests**: Tests with real dependencies (optional)
5. **Coverage Reports**: Add pytest-cov for coverage metrics

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [httpx testing](https://www.python-httpx.org/advanced/testing/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
