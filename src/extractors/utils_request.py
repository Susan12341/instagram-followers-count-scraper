import logging
import random
import time
from typing import Any, Dict, Optional

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

_DEFAULT_UAS = [
    # A small pool of realistic desktop UAs
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

class HttpClient:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.timeout = float(config.get("timeout_seconds", 15))
        self.retries = int(config.get("retries", 2))
        self.proxies = config.get("proxies")
        self.user_agent = config.get("user_agent") or random.choice(_DEFAULT_UAS)
        self.delay_ms_min = int(config.get("delay_ms_min", 300))
        self.delay_ms_max = int(config.get("delay_ms_max", 900))

        self.session = requests.Session()
        retry = Retry(
            total=self.retries,
            connect=self.retries,
            read=self.retries,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "HEAD"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=20)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _sleep_jitter(self) -> None: