from models import SourceItem


class TestQueryEndpoint:

    def test_returns_answer_and_sources(self, client, mock_rag):
        mock_rag.session_manager.create_session.return_value = "sess-1"
        mock_rag.query.return_value = (
            "Python is a general-purpose language.",
            [SourceItem(label="Lesson 1: Intro", url="http://example.com/l1")],
        )

        resp = client.post("/api/query", json={"query": "What is Python?"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "Python is a general-purpose language."
        assert body["session_id"] == "sess-1"
        assert body["sources"] == [{"label": "Lesson 1: Intro", "url": "http://example.com/l1"}]

    def test_auto_generates_session_when_none_provided(self, client, mock_rag):
        mock_rag.session_manager.create_session.return_value = "auto-123"

        resp = client.post("/api/query", json={"query": "Hello"})

        assert resp.status_code == 200
        assert resp.json()["session_id"] == "auto-123"
        mock_rag.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id(self, client, mock_rag):
        resp = client.post(
            "/api/query", json={"query": "Hello", "session_id": "my-session"}
        )

        assert resp.status_code == 200
        assert resp.json()["session_id"] == "my-session"
        mock_rag.session_manager.create_session.assert_not_called()

    def test_passes_query_text_to_rag_system(self, client, mock_rag):
        client.post("/api/query", json={"query": "What courses exist?"})

        positional_args = mock_rag.query.call_args[0]
        assert "What courses exist?" in positional_args

    def test_passes_session_id_to_rag_system(self, client, mock_rag):
        client.post("/api/query", json={"query": "Q", "session_id": "s42"})

        positional_args = mock_rag.query.call_args[0]
        assert "s42" in positional_args

    def test_returns_empty_sources_list(self, client, mock_rag):
        mock_rag.query.return_value = ("Answer.", [])

        resp = client.post("/api/query", json={"query": "Q"})

        assert resp.status_code == 200
        assert resp.json()["sources"] == []

    def test_returns_500_on_rag_failure(self, client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("DB connection lost")

        resp = client.post("/api/query", json={"query": "Any question"})

        assert resp.status_code == 500
        assert "DB connection lost" in resp.json()["detail"]

    def test_missing_query_field_returns_422(self, client):
        resp = client.post("/api/query", json={"session_id": "s1"})

        assert resp.status_code == 422

    def test_empty_query_string_is_accepted(self, client, mock_rag):
        # Validation of empty strings is the RAG layer's responsibility
        mock_rag.query.return_value = ("Nothing found.", [])

        resp = client.post("/api/query", json={"query": ""})

        assert resp.status_code == 200


class TestCoursesEndpoint:

    def test_returns_course_stats(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["Python 101", "Data Science", "ML Basics"],
        }

        resp = client.get("/api/courses")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_courses"] == 3
        assert body["course_titles"] == ["Python 101", "Data Science", "ML Basics"]

    def test_returns_zero_when_no_courses_loaded(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        resp = client.get("/api/courses")

        assert resp.status_code == 200
        assert resp.json() == {"total_courses": 0, "course_titles": []}

    def test_returns_500_on_analytics_failure(self, client, mock_rag):
        mock_rag.get_course_analytics.side_effect = RuntimeError("Chroma unavailable")

        resp = client.get("/api/courses")

        assert resp.status_code == 500
        assert "Chroma unavailable" in resp.json()["detail"]
