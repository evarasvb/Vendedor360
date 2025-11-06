"""Resilience helpers for the Vendedor360 automation suite."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, TypeVar
import logging
import random
import time


_T = TypeVar("_T")


@dataclass
class RetryPolicy:
    """Configuration for retry/backoff logic."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0
    jitter: float = 0.15

    def get_delay(self, attempt: int) -> float:
        """Return the delay (in seconds) for a given attempt."""

        delay = self.initial_delay * (self.backoff_factor ** max(0, attempt - 1))
        delay = min(delay, self.max_delay)
        if self.jitter:
            jitter_range = (1 - self.jitter, 1 + self.jitter)
            delay *= random.uniform(*jitter_range)
        return delay


class ResilienceError(RuntimeError):
    """Custom error raised when retries are exhausted."""


def execute_with_retry(
    func: Callable[[], _T],
    *,
    policy: RetryPolicy | None = None,
    exceptions: Iterable[type[BaseException]] | None = None,
    logger: logging.Logger | None = None,
) -> _T:
    """Execute ``func`` retrying transient failures."""

    policy = policy or RetryPolicy()
    allowed = tuple(exceptions or (Exception,))
    attempt = 1
    while True:
        try:
            return func()
        except allowed as exc:  # type: ignore[arg-type]
            if attempt >= policy.max_attempts:
                raise ResilienceError("max retries exceeded") from exc
            delay = policy.get_delay(attempt)
            if logger:
                logger.warning(
                    "Retry %s/%s after error: %s. Waiting %.2fs",
                    attempt,
                    policy.max_attempts,
                    exc,
                    delay,
                )
            time.sleep(delay)
            attempt += 1


def retryable(policy: RetryPolicy | None = None, **kwargs):
    """Decorator applying :func:`execute_with_retry` to the wrapped callable."""

    def decorator(func: Callable[..., _T]):
        def wrapper(*args, **inner_kwargs):
            return execute_with_retry(
                lambda: func(*args, **inner_kwargs),
                policy=policy,
                **kwargs,
            )

        return wrapper

    return decorator
