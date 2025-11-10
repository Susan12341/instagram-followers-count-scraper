import csv
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

CSV_FIELDS = [
    "username",
    "full_name",
    "followers_count",
    "following_count",
    "bio",
    "profile_url",
    "posts_count",
    "engagement_rate",
    "is_verified",
    "profile_image",
    "fetched_at",
    "source",
]

def export_csv(records: List[Dict[str, Any]], path: Path) -> None:
    try:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for r in records:
                writer.writerow({k: r.get(k) for k in CSV_FIELDS})
        logger.info("Wrote CSV to %s (%d records)", path, len(records))
    except Exception as e:
        logger.error("Failed to write CSV to %s: %s", path, e)
        raise