"""Smoke tests for stage 4 (quality / regression)."""

from database import Profile, Gender
from profile_helpers import calculate_completeness, parse_photo_keys
from ranking import PRIMARY_WEIGHT, BEHAVIORAL_WEIGHT


def test_completeness_empty():
    p = Profile()
    assert calculate_completeness(p) == 0.0


def test_completeness_full():
    p = Profile(
        name="n",
        age=25,
        gender=Gender.MALE,
        city="c",
        description="d",
        interests="i",
    )
    assert calculate_completeness(p) == 1.0


def test_combined_weights_sum():
    assert abs(PRIMARY_WEIGHT + BEHAVIORAL_WEIGHT - 1.0) < 1e-9


def test_parse_photo_keys_empty():
    assert parse_photo_keys(None) == []
    assert parse_photo_keys("") == []


def test_parse_photo_keys_json():
    assert parse_photo_keys('["a/b/1.jpg", "a/b/2.jpg"]') == ["a/b/1.jpg", "a/b/2.jpg"]


def test_celery_app_importable():
    import tasks

    assert tasks.app is not None
    assert tasks.recalculate_all_ratings_task.name == "tasks.recalculate_all_ratings_task"
