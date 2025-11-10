import re
from typing import Any, Dict

def normalize_username(raw: str) -> str:
    """
    Clean up a raw username input: trim spaces, remove leading @,
    strip trailing slashes and query parameters, and lower-case it.
    """
    text = (raw or "").strip()
    if not text:
        return ""

    # Remove URL prefix if the user pasted a full Instagram URL
    text = re.sub(r"^https?://(www\.)?instagram\.com/", "", text, flags=re.IGNORECASE)

    # Remove any URL path/query fragments
    text = text.split("?")[0]
    text = text.strip().lstrip("@").strip("/")

    return text.lower()

def _ensure_int(value: Any, field: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if cleaned.isdigit():
            return int(cleaned)
    raise ValueError(f"Invalid integer for {field}: {value!r}")

def validate_and_clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize a scraped record to ensure consistent structure.
    """
    required_fields = ["username", "followersCount", "followingCount", "profileUrl", "timestamp"]
    for field in required_fields:
        if field not in record:
            raise ValueError(f"Missing field '{field}' in record: {record}")

    username = normalize_username(record["username"])
    if not username:
        raise ValueError(f"Username is empty after normalization: {record.get('username')!r}")

    followers = _ensure_int(record["followersCount"], "followersCount")
    following = _ensure_int(record["followingCount"], "followingCount")

    profile_url = str(record["profileUrl"]).strip()
    if not profile_url.startswith("http"):
        profile_url = f"https://www.instagram.com/{username}/"

    timestamp = str(record["timestamp"]).strip()
    if not timestamp:
        raise ValueError("Timestamp cannot be empty")

    # Return a new, sanitized dict
    return {
        "username": username,
        "followersCount": followers,
        "followingCount": following,
        "profileUrl": profile_url,
        "timestamp": timestamp,
    }