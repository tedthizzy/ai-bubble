"""Resolve the anonymous export header from PJM's published public application."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

import httpx

if TYPE_CHECKING:
    from collections.abc import Callable

PAGE = "https://www.pjm.com/planning/service-requests/serial-service-request-status"
EXPORT = "https://services.pjm.com/PJMPlanningApi/api/Queue/ExportToXls"


def public_export_headers(fetch: Callable[[str], str] | None = None) -> dict[str, str]:
    def get(url: str) -> str:
        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()
        return response.text

    read = fetch or get
    sources = re.findall(r'<script[^>]+src=["\']([^"\']+)', read(PAGE))
    bundle = next((src for src in sources if "/dist/interconnectionqueues." in src), None)
    if bundle is None:
        raise ValueError("PJM public page did not name its queue application")
    url = urljoin(PAGE, bundle)
    if urlparse(url).hostname != "www.pjm.com":
        raise ValueError("PJM queue application is outside its publisher's domain")
    source = read(url)
    pattern = r'(?:apiSubscriptionKey|["\']api-subscription-key["\']|subscriptionKey)\s*:\s*["\']([^"\']+)'
    match = re.search(pattern, source, re.IGNORECASE)
    if not match:
        raise ValueError("Anonymous PJM export header was not found in the public application")
    # This identifier is served to every anonymous visitor. Do not log or store
    # it in catalog metadata; resolve it again on the next acquisition.
    return {"api-subscription-key": match[1], "Origin": "https://www.pjm.com", "Referer": "https://www.pjm.com/"}
