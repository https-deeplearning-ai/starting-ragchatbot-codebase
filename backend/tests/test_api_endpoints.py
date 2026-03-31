"""
Tests for the FastAPI endpoints in app.py.

Fixtures (client, mock_rag) are provided by conftest.py.
Each test configures mock_rag return values/side effects for the scenario
under test, then inspects the HTTP response.

Endpoints covered:
  POST /api/query
  GET  /api/courses
  POST /api/clear-session
"""


class TestQueryEndpoint:

    def test_returns_200_for_valid_request(self, client, mock_rag):
        mock_rag.query.return_value = ("ML is a subset of AI.", ["Course A - Lesson 1"])
        mock_rag.session_manager.create_session.return_value = "new-session"

        response = client.post("/api/query", json={"query": "What is ML?"})

        assert response.status_code == 200

    def test_response_body_has_answer_sources_session_id(self, client, mock_rag):
        mock_rag.query.return_value = ("ML is a subset of AI.", ["Course A - Lesson 1"])
        mock_rag.session_manager.create_session.return_value = "new-session"

        data = client.post("/api/query", json={"query": "What is ML?"}).json()

        assert data["answer"] == "ML is a subset of AI."
        assert data["sources"] == ["Course A - Lesson 1"]
        assert data["session_id"] == "new-session"

    def test_creates_session_when_none_provided(self, client, mock_rag):
        mock_rag.query.return_value = ("Answer.", [])
        mock_rag.session_manager.create_session.return_value = "generated-id"

        data = client.post("/api/query", json={"query": "Hello"}).json()

        mock_rag.session_manager.create_session.assert_called_once()
        assert data["session_id"] == "generated-id"

    def test_uses_provided_session_id_without_creating_new_one(self, client, mock_rag):
        mock_rag.query.return_value = ("Answer.", [])

        data = client.post(
            "/api/query", json={"query": "Hello", "session_id": "existing-sess"}
        ).json()

        mock_rag.session_manager.create_session.assert_not_called()
        assert data["session_id"] == "existing-sess"

    def test_passes_query_and_session_id_to_rag_system(self, client, mock_rag):
        mock_rag.query.return_value = ("Answer.", [])

        client.post("/api/query", json={"query": "Test query", "session_id": "sess-1"})

        mock_rag.query.assert_called_once_with("Test query", "sess-1")

    def test_returns_500_when_rag_raises(self, client, mock_rag):
        mock_rag.session_manager.create_session.return_value = "sess"
        mock_rag.query.side_effect = RuntimeError("DB unavailable")

        response = client.post("/api/query", json={"query": "Fail"})

        assert response.status_code == 500

    def test_returns_422_when_query_field_missing(self, client, mock_rag):
        response = client.post("/api/query", json={"session_id": "sess"})

        assert response.status_code == 422

    def test_empty_sources_list_is_valid(self, client, mock_rag):
        mock_rag.query.return_value = ("General answer.", [])
        mock_rag.session_manager.create_session.return_value = "s"

        data = client.post("/api/query", json={"query": "Hello"}).json()

        assert data["sources"] == []

    def test_multiple_sources_are_returned(self, client, mock_rag):
        mock_rag.query.return_value = (
            "Answer citing two lessons.",
            ["Course A - Lesson 1", "Course B - Lesson 3"],
        )
        mock_rag.session_manager.create_session.return_value = "s"

        data = client.post("/api/query", json={"query": "Multi-source question"}).json()

        assert len(data["sources"]) == 2
        assert "Course A - Lesson 1" in data["sources"]
        assert "Course B - Lesson 3" in data["sources"]


class TestCoursesEndpoint:

    def test_returns_200(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 1,
            "course_titles": ["Intro to AI"],
        }

        response = client.get("/api/courses")

        assert response.status_code == 200

    def test_response_contains_total_courses_and_titles(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["AI Basics", "ML Fundamentals"],
        }

        data = client.get("/api/courses").json()

        assert data["total_courses"] == 2
        assert data["course_titles"] == ["AI Basics", "ML Fundamentals"]

    def test_empty_catalog_returns_zero_courses(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        data = client.get("/api/courses").json()

        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_returns_500_when_analytics_raises(self, client, mock_rag):
        mock_rag.get_course_analytics.side_effect = RuntimeError("ChromaDB error")

        response = client.get("/api/courses")

        assert response.status_code == 500

    def test_title_count_matches_total_courses_field(self, client, mock_rag):
        titles = ["Course A", "Course B", "Course C"]
        mock_rag.get_course_analytics.return_value = {
            "total_courses": len(titles),
            "course_titles": titles,
        }

        data = client.get("/api/courses").json()

        assert data["total_courses"] == len(data["course_titles"])


class TestClearSessionEndpoint:

    def test_returns_200_with_ok_status(self, client, mock_rag):
        response = client.post("/api/clear-session", json={"session_id": "sess-abc"})

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_delegates_to_session_manager(self, client, mock_rag):
        client.post("/api/clear-session", json={"session_id": "sess-to-clear"})

        mock_rag.session_manager.clear_session.assert_called_once_with("sess-to-clear")

    def test_returns_422_when_session_id_missing(self, client, mock_rag):
        response = client.post("/api/clear-session", json={})

        assert response.status_code == 422

    def test_different_session_ids_are_forwarded_correctly(self, client, mock_rag):
        for session_id in ["alpha", "beta", "gamma"]:
            mock_rag.session_manager.clear_session.reset_mock()
            client.post("/api/clear-session", json={"session_id": session_id})
            mock_rag.session_manager.clear_session.assert_called_once_with(session_id)
