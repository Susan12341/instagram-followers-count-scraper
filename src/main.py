import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Local imports
from extractors.instagram_parser import InstagramParser
from outputs.exporter_json import export_json
from outputs.exporter_csv import export_csv

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_USERNAMES_FILE = DATA_DIR / "usernames_sample.txt"
DEFAULT_OUTPUT_JSON = DATA_DIR / "sample_output.json"
DEFAULT_OUTPUT_CSV = DATA_DIR / "sample_output.csv"
CONFIG_EXAMPLE = ROOT / "src" / "config" / "settings.example.json"

def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

def load_usernames(path: Path) -> List[str]:
    if not path.exists():
        logging.warning("Usernames file %s does not exist. Falling back to sample list.", path)
        return ["instagram", "natgeo", "nike"]
    usernames = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            usernames.append(line)
    return usernames

def ensure_config(path: Path) -> Dict[str, Any]:
    """
    Loads configuration. If a custom settings.json is not found next to example,
    it will use the example as defaults.
    """
    example = CONFIG_EXAMPLE
    candidate = example.with_name("settings.json")
    src = candidate if candidate.exists() else example
    try:
        with src.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        logging.info("Loaded config from %s", src)
        return cfg
    except Exception as e:
        logging.warning("Failed to load config (%s). Using safe defaults.", e)
        return {
            "request": {
                "timeout_seconds": 15,
                "retries": 2,
                "concurrency": 5,
                "proxies": None,
                "user_agent": None,
                "delay_ms_min": 250,
                "delay_ms_max": 750
            }
        }

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Instagram Followers Count Scraper - public profile metrics collector"
    )
    p.add_argument(
        "-i", "--input",
        type=Path,
        default=DEFAULT_USERNAMES_FILE,
        help=f"Path to a text file with one username per line. Default: {DEFAULT_USERNAMES_FILE}"
    )
    p.add_argument(
        "-o", "--out-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help=f"Path to write JSON results. Default: {DEFAULT_OUTPUT_JSON}"
    )
    p.add_argument(
        "-c", "--out-csv",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
        help=f"Path to write CSV results. Default: {DEFAULT_OUTPUT_CSV}"
    )
    p.add_argument(
        "--no-network",
        action="store_true",
        help="Do not call Instagram; instead, load data from existing JSON if present or return mock results."
    )
    p.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv)."
    )
    return p.parse_args(argv)

def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)
    logger = logging.getLogger("main")

    cfg = ensure_config(CONFIG_EXAMPLE)
    usernames = load_usernames(args.input)
    if not usernames:
        logger.error("No usernames provided. Exiting.")
        return 2

    parser = InstagramParser(config=cfg.get("request", {}))

    results: List[Dict[str, Any]] = []
    ts = datetime.utcnow().isoformat() + "Z"

    if args.no_network:
        # Try to load cached output; else build mock results so the pipeline runs end-to-end.
        if args.out_json.exists():
            try:
                with args.out_json.open("r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if isinstance(cached, list):
                        results = cached
                        logger.info("Loaded %d cached records from %s", len(results), args.out_json)
            except Exception as e:
                logger.warning("Failed to read cached JSON (%s). Using mock data.", e)

        if not results:
            for u in usernames:
                results.append({
                    "username": u,
                    "full_name": u.capitalize(),
                    "followers_count": 12345,
                    "following_count": 150,
                    "bio": f"Mock bio for {u}",
                    "profile_url": f"https://www.instagram.com/{u}/",
                    "posts_count": 50,
                    "engagement_rate": 2.1,
                    "is_verified": False,
                    "profile_image": f"https://instagram.com/{u}/profile.jpg",
                    "fetched_at": ts,
                    "source": "mock"
                })
            logger.info("Generated %d mock records (no-network mode).", len(results))
    else:
        for username in usernames:
            try:
                profile = parser.fetch_profile(username)
                if not profile:
                    logger.warning("Could not fetch profile for '%s'. Skipping.", username)
                    continue
                profile["fetched_at"] = ts
                profile["source"] = "live"
                results.append(profile)
            except Exception as e:
                logger.exception("Error processing '%s': %s", username, e)

    if not results:
        logger.error("No results were produced. Exiting with failure.")
        return 1

    # Ensure output directory exists
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)

    export_json(results, args.out_json)
    export_csv(results, args.out_csv)

    logger.info("Done. JSON -> %s, CSV -> %s", args.out_json, args.out_csv)
    print(f"✅ Wrote {len(results)} records\nJSON: {args.out_json}\nCSV:  {args.out_csv}")
    return 0

if __name__ == "__main__":
    sys.exit(main())