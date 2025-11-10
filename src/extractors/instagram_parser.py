import json
import logging
import re
from typing import Any, Dict, Optional

from .utils_request import HttpClient

logger = logging.getLogger(__name__)

class InstagramParser:
    """
    Fetches and parses public Instagram profile metrics.
    Tries multiple strategies:
      1) Web profile API endpoint (may work without auth intermittently)
      2) Embedded JSON within HTML (ld+json / shared data)
      3) Lightweight HTML heuristics as a last resort

    Returns a normalized dict or None if all strategies fail.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.http = HttpClient(config=config)

    def fetch_profile(self, username: str) -> Optional[Dict[str, Any]]:
        username = username.strip().lstrip("@")
        if not username:
            return None

        # Try official-ish web endpoint first
        api_url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        resp = self.http.get(
            api_url,
            headers={
                "User-Agent": self.http.user_agent,
                "X-IG-App-ID": "936619743392459",
                "Accept": "application/json",
                "Referer": f"https://www.instagram.com/{username}/",
            },
            allow_redirects=True,
        )
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                user = (
                    data.get("data", {})
                    .get("user", {})
                )
                if user:
                    return self._normalize_from_user(user)
            except Exception as e:
                logger.debug("API JSON parse failed: %s", e)

        # Fallback: fetch HTML and parse embedded JSON
        page_url = f"https://www.instagram.com/{username}/"
        resp = self.http.get(
            page_url,
            headers={"User-Agent": self.http.user_agent, "Accept": "text/html"},
            allow_redirects=True,
        )
        if resp and resp.status_code == 200 and resp.text:
            # Try ld+json
            normalized = self._parse_ld_json(resp.text)
            if normalized:
                return normalized

            # Try sharedData / additionalDataLoaded legacy blobs
            normalized = self._parse_shared_data(resp.text)
            if normalized:
                return normalized

            # Heuristic fallback
            normalized = self._heuristic_counts(resp.text, username)
            if normalized:
                return normalized

        logger.warning("All strategies failed for '%s'", username)
        return None

    # ------------------ Parsers ------------------

    def _normalize_from_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        def _get(*keys, default=None):
            node = user
            for k in keys:
                if node is None:
                    return default
                node = node.get(k)
            return node if node is not None else default

        return {
            "username": _get("username", default=""),
            "full_name": _get("full_name", default=""),
            "followers_count": _get("edge_followed_by", "count", default=_get("follower_count", default=0)),
            "following_count": _get("edge_follow", "count", default=_get("following_count", default=0)),
            "bio": _get("biography", default=""),
            "profile_url": f"https://www.instagram.com/{_get('username', default='')}/",
            "posts_count": _get("edge_owner_to_timeline_media", "count", default=_get("media_count", default=0)),
            "engagement_rate": None,  # cannot compute without recent posts; left None here
            "is_verified": bool(_get("is_verified", default=False)),
            "profile_image": _get("profile_pic_url_hd", default=_get("profile_pic_url", default=None)),
        }

    def _parse_ld_json(self, html: str) -> Optional[Dict[str, Any]]:
        # Instagram sometimes embeds JSON-LD with basic attributes
        for m in re.finditer(