import json
import logging
from pathlib import Path
from typing import Any, List, Dict

logger = logging.getLogger(__name__)

def export_json(records: List[Dict[str, Any]], path: Path) -> None:
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        logger.info("Wrote JSON to %s (%d records)", path, len(records))
    except Exception as e:
        logger.error("Failed to write JSON to %s: %s", path, e)
        raise