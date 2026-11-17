"""Very small in-memory limiter for failed login attempts.

It slows down password-guessing against a single account from a single client.
State lives in process memory, so it resets on restart and is not shared
between multiple server processes (documented limitation).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class LoginAttemptLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 600) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    @staticmethod
    def key(client_ip: str | None, identifier: str) -> str:
        return f"{client_ip or 'unknown'}|{identifier.strip().lower()}"

    def _prune(self, attempts: deque[float], now: float) -> None:
        while attempts and now - attempts[0] > self.window_seconds:
            attempts.popleft()

    def is_blocked(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            attempts = self._failures.get(key)
            if not attempts:
                return False
            self._prune(attempts, now)
            return len(attempts) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            attempts = self._failures[key]
            self._prune(attempts, now)
            attempts.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_limiter = LoginAttemptLimiter()
