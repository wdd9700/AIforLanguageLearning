from __future__ import annotations

from datetime import datetime, timedelta

from app.domain.srs.sm2 import calculate_next_review


def test_calculate_next_review_correct() -> None:
    level = 0
    correct = True
    new_level, next_review = calculate_next_review(level, correct)
    assert new_level == 1
    expected_min = datetime.utcnow() + timedelta(days=1) - timedelta(seconds=5)
    assert next_review >= expected_min


def test_calculate_next_review_incorrect() -> None:
    level = 3
    correct = False
    new_level, next_review = calculate_next_review(level, correct)
    assert new_level == 2
    expected_min = datetime.utcnow() + timedelta(minutes=10) - timedelta(seconds=5)
    assert next_review >= expected_min


def test_calculate_next_review_multiple_correct() -> None:
    level = 0
    for i, expected in enumerate([1, 2, 3, 4, 5]):
        level, _ = calculate_next_review(level, True)
        assert level == expected
