"""Per-host rate limit + circuit breaker for MIC fetch."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


def host_from_url(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


@dataclass
class HostState:
    last_request_at: float = 0.0
    consecutive_failures: int = 0
    circuit_open_until: float = 0.0
    total_success: int = 0
    total_failure: int = 0


@dataclass
class RateLimitCircuit:
    """
    Simple sequential rate limiter + circuit breaker.

    - min_interval_ms_per_host: sleep if requests are closer than this
    - circuit_break_failures: open circuit after N consecutive failures
    - circuit_open_seconds: keep circuit open this long
    """

    min_interval_ms: float = 1200.0
    failure_threshold: int = 5
    open_seconds: float = 300.0
    _hosts: dict[str, HostState] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def from_cfg(cls, mi_cfg: dict[str, Any] | None = None) -> "RateLimitCircuit":
        mi = mi_cfg or {}
        fetch = mi.get("fetch") if isinstance(mi.get("fetch"), dict) else {}
        fetch = fetch or {}
        min_ms = float(
            fetch.get("min_interval_ms_per_host")
            or mi.get("min_interval_ms_per_host")
            or 1200
        )
        fail_n = int(
            fetch.get("circuit_break_failures")
            or mi.get("circuit_break_failures")
            or 5
        )
        open_s = float(
            fetch.get("circuit_open_seconds")
            or mi.get("circuit_open_seconds")
            or 300
        )
        return cls(
            min_interval_ms=min_ms,
            failure_threshold=max(1, fail_n),
            open_seconds=max(1.0, open_s),
        )

    def _state(self, host: str) -> HostState:
        h = (host or "unknown").lower()
        if h not in self._hosts:
            self._hosts[h] = HostState()
        return self._hosts[h]

    def is_open(self, url_or_host: str) -> bool:
        host = host_from_url(url_or_host) if "://" in (url_or_host or "") else (
            url_or_host or "unknown"
        ).lower()
        with self._lock:
            st = self._state(host)
            if st.circuit_open_until <= 0:
                return False
            if time.monotonic() >= st.circuit_open_until:
                # Half-open: allow one attempt
                st.circuit_open_until = 0.0
                return False
            return True

    def remaining_open_s(self, url_or_host: str) -> float:
        host = host_from_url(url_or_host) if "://" in (url_or_host or "") else (
            url_or_host or "unknown"
        ).lower()
        with self._lock:
            st = self._state(host)
            if st.circuit_open_until <= 0:
                return 0.0
            return max(0.0, st.circuit_open_until - time.monotonic())

    def wait_turn(self, url_or_host: str) -> float:
        """Block until min interval elapsed; return seconds slept."""
        host = host_from_url(url_or_host) if "://" in (url_or_host or "") else (
            url_or_host or "unknown"
        ).lower()
        slept = 0.0
        with self._lock:
            st = self._state(host)
            now = time.monotonic()
            min_gap = self.min_interval_ms / 1000.0
            if st.last_request_at > 0 and min_gap > 0:
                elapsed = now - st.last_request_at
                if elapsed < min_gap:
                    slept = min_gap - elapsed
        if slept > 0:
            time.sleep(slept)
        with self._lock:
            self._state(host).last_request_at = time.monotonic()
        return slept

    def record_success(self, url_or_host: str) -> None:
        host = host_from_url(url_or_host) if "://" in (url_or_host or "") else (
            url_or_host or "unknown"
        ).lower()
        with self._lock:
            st = self._state(host)
            st.consecutive_failures = 0
            st.circuit_open_until = 0.0
            st.total_success += 1

    def record_failure(self, url_or_host: str) -> bool:
        """
        Record failure. Returns True if circuit just opened (or is open).
        """
        host = host_from_url(url_or_host) if "://" in (url_or_host or "") else (
            url_or_host or "unknown"
        ).lower()
        with self._lock:
            st = self._state(host)
            st.consecutive_failures += 1
            st.total_failure += 1
            if st.consecutive_failures >= self.failure_threshold:
                st.circuit_open_until = time.monotonic() + self.open_seconds
                return True
            return st.circuit_open_until > time.monotonic()

    def reset(self, host: str | None = None) -> None:
        with self._lock:
            if host is None:
                self._hosts.clear()
            else:
                self._hosts.pop(host.lower(), None)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                h: {
                    "consecutive_failures": s.consecutive_failures,
                    "circuit_open": s.circuit_open_until > time.monotonic(),
                    "total_success": s.total_success,
                    "total_failure": s.total_failure,
                }
                for h, s in self._hosts.items()
            }


# Process-wide default (tests may construct their own)
_DEFAULT: RateLimitCircuit | None = None


def get_default_limiter(mi_cfg: dict[str, Any] | None = None) -> RateLimitCircuit:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = RateLimitCircuit.from_cfg(mi_cfg)
    return _DEFAULT


def reset_default_limiter() -> None:
    global _DEFAULT
    _DEFAULT = None
