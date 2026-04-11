"""知识图谱路由集成测试"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


class TestKnowledgeGraphRouter:
    """知识图谱路由测试"""

    def test_get_word_relations_get(self, client: TestClient) -> None:
        r = client.get("/api/v1/knowledge-graph/relations/happy?limit=5")
        assert r.status_code == 200
        data = r.json()
        assert data["word"] == "happy"
        assert isinstance(data["relations"], list)
        assert isinstance(data["total"], int)

    def test_post_word_relations(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/knowledge-graph/relations",
            json={"word": "unhappy", "relation_type": "antonym", "limit": 5},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["word"] == "unhappy"
        assert isinstance(data["relations"], list)

    def test_analyze_cognates(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/knowledge-graph/cognates/analyze",
            json={"word": "unhappy"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["word"] == "unhappy"
        assert isinstance(data["cognates"], list)
        assert data["total"] >= 1

    def test_recommend_vocabulary(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/knowledge-graph/recommend",
            json={
                "user_id": "user_test_001",
                "count": 5,
                "user_level": 2,
                "weak_points": ["happy"],
                "learned_words": ["sad"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["user_id"] == "user_test_001"
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) <= 5
        assert isinstance(data["total"], int)

    def test_add_word_relation(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/knowledge-graph/relations/add",
            json={
                "source": "test_word_a",
                "target": "test_word_b",
                "relation_type": "synonym",
                "strength": 0.9,
            },
        )
        assert r.status_code == 200
        data = r.json()
        # 无 Neo4j 时可能返回 False，但接口应正常响应
        assert "success" in data

    def test_learning_path(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/knowledge-graph/learning-path",
            json={"start_word": "happy", "target_word": "joy", "max_depth": 5},
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
