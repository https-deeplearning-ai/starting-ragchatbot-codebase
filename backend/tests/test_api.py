"""4. FastAPI endpoints: request validation, response shape, error handling (RAGSystem mocked)."""
from conftest import INDEX_TITLE, MCP


# --- POST /api/query ----------------------------------------------------------

def test_query_with_session_returns_answer_sources_and_same_session(client, mock_rag):
    resp = client.post("/api/query", json={"query": "What is MCP?", "session_id": "abc"})

    assert resp.status_code == 200
    assert resp.json() == {
        "answer": "MCP is a protocol.",
        "sources": [{"label": f"{MCP} - Lesson 1", "url": "https://example.com/mcp/lesson1"}],
        "session_id": "abc",
    }
    mock_rag.query.assert_called_once_with("What is MCP?", "abc")
    mock_rag.session_manager.create_session.assert_not_called()


def test_query_without_session_creates_one(client, mock_rag):
    resp = client.post("/api/query", json={"query": "What is MCP?"})

    assert resp.status_code == 200
    assert resp.json()["session_id"] == "session_1"
    mock_rag.session_manager.create_session.assert_called_once_with()
    mock_rag.query.assert_called_once_with("What is MCP?", "session_1")


def test_query_source_without_url_serializes_as_null(client, mock_rag):
    mock_rag.query.return_value = ("Answer.", [{"label": MCP, "url": None}])

    resp = client.post("/api/query", json={"query": "q"})

    assert resp.json()["sources"] == [{"label": MCP, "url": None}]


def test_query_with_no_sources(client, mock_rag):
    """General questions skip search, so sources come back empty."""
    mock_rag.query.return_value = ("Hello!", [])

    resp = client.post("/api/query", json={"query": "hi"})

    assert resp.status_code == 200
    assert resp.json()["sources"] == []


def test_query_missing_query_field_is_rejected(client, mock_rag):
    resp = client.post("/api/query", json={"session_id": "abc"})

    assert resp.status_code == 422
    mock_rag.query.assert_not_called()


def test_query_non_json_body_is_rejected(client, mock_rag):
    resp = client.post("/api/query", content="not json",
                       headers={"Content-Type": "application/json"})

    assert resp.status_code == 422
    mock_rag.query.assert_not_called()


def test_query_error_becomes_500_with_detail(client, mock_rag):
    mock_rag.query.side_effect = RuntimeError("boom")

    resp = client.post("/api/query", json={"query": "q"})

    assert resp.status_code == 500
    assert resp.json() == {"detail": "boom"}


def test_query_wrong_method_falls_through_to_static_404(client, mock_rag):
    """Not 405: the catch-all static mount at "/" claims GET /api/query and finds no file."""
    assert client.get("/api/query").status_code == 404
    mock_rag.query.assert_not_called()


# --- GET /api/courses ---------------------------------------------------------

def test_courses_returns_stats(client):
    resp = client.get("/api/courses")

    assert resp.status_code == 200
    assert resp.json() == {"total_courses": 2, "course_titles": [MCP, "Other Course"]}


def test_courses_error_becomes_500_with_detail(client, mock_rag):
    mock_rag.get_course_analytics.side_effect = RuntimeError("chroma down")

    resp = client.get("/api/courses")

    assert resp.status_code == 500
    assert resp.json() == {"detail": "chroma down"}


# --- DELETE /api/session/{id} -------------------------------------------------

def test_delete_existing_session(client, mock_rag):
    resp = client.delete("/api/session/abc")

    assert resp.status_code == 200
    assert resp.json() == {"deleted": True}
    mock_rag.session_manager.delete_session.assert_called_once_with("abc")


def test_delete_unknown_session(client, mock_rag):
    mock_rag.session_manager.delete_session.return_value = False

    assert client.delete("/api/session/nope").json() == {"deleted": False}


# --- GET / (static frontend) --------------------------------------------------

def test_root_serves_index_html(client):
    resp = client.get("/")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert INDEX_TITLE in resp.text


def test_unknown_path_is_404(client):
    assert client.get("/does-not-exist.js").status_code == 404
