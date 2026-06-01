"""Bounded fetch concurrency, per-domain throttling, and retry helpers."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, Semaphore
from time import monotonic, sleep
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class FetchConcurrencyConfig:
    """Concurrency limits for real source acquisition."""

    max_workers: int = 64
    sec_domain_concurrency: int = 8
    other_domain_concurrency: int = 16
    sec_requests_per_second: float = 8.0
    other_requests_per_second: float = 16.0
    retry_attempts: int = 3
    retry_backoff_seconds: float = 0.5


class DomainFetchLimiter:
    """Per-domain semaphore plus rate pacing for synchronous fetch workers."""

    def __init__(self, config: FetchConcurrencyConfig) -> None:
        self.config = config
        self._lock = Lock()
        self._semaphores: dict[str, Semaphore] = {}
        self._next_request_at: dict[str, float] = {}

    def run[T](self, source_uri: str, operation: Callable[[], T]) -> T:
        domain = domain_key(source_uri)
        if domain == "local":
            return operation()
        semaphore = self._semaphore(domain)
        with semaphore:
            self._pace(domain)
            return operation()

    def _semaphore(self, domain: str) -> Semaphore:
        with self._lock:
            semaphore = self._semaphores.get(domain)
            if semaphore is None:
                semaphore = Semaphore(self._domain_concurrency(domain))
                self._semaphores[domain] = semaphore
            return semaphore

    def _domain_concurrency(self, domain: str) -> int:
        if is_sec_domain(domain):
            return max(1, self.config.sec_domain_concurrency)
        return max(1, self.config.other_domain_concurrency)

    def _pace(self, domain: str) -> None:
        rate = self._domain_rate(domain)
        if rate <= 0:
            return
        interval = 1.0 / rate
        with self._lock:
            now = monotonic()
            next_request_at = self._next_request_at.get(domain, now)
            delay = max(0.0, next_request_at - now)
            self._next_request_at[domain] = max(now, next_request_at) + interval
        if delay:
            sleep(delay)

    def _domain_rate(self, domain: str) -> float:
        if is_sec_domain(domain):
            return self.config.sec_requests_per_second
        return self.config.other_requests_per_second


def fetch_with_retries[T](
    operation: Callable[[], T],
    *,
    attempts: int,
    backoff_seconds: float,
) -> T:
    """Retry transient HTTP failures with exponential backoff."""

    last_error: Exception | None = None
    for attempt in range(max(1, attempts)):
        try:
            return operation()
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if attempt == max(1, attempts) - 1:
                break
            sleep(backoff_seconds * (2**attempt))
    if last_error is not None:
        raise last_error
    return operation()


def domain_key(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    if parsed.scheme in {"", "file", "."}:
        return "local"
    return (parsed.hostname or "unknown").lower()


def is_sec_domain(domain: str) -> bool:
    return domain == "sec.gov" or domain.endswith(".sec.gov")
