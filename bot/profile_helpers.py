import json

from database import Profile


def parse_photo_keys(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def calculate_completeness(profile: Profile) -> float:
    fields = [
        profile.name,
        profile.age,
        profile.gender,
        profile.city,
        profile.description,
        profile.interests,
    ]
    filled = sum(1 for f in fields if f)
    return filled / len(fields)
