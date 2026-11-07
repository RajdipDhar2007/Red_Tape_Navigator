"""Retry with backoff, timeouts and a circuit breaker for scrapers and LLM calls."""
import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.reset_seconds = reset_seconds
        self.failures = 0
        self.opened_at: float | None = None

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        return "half-open" if time.monotonic() - self.opened_at >= self.reset_seconds else "open"

    def allow(self) -> bool:
        return self.state != "open"

    def success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.monotonic()


async def call_with_resilience(
    fn: Callable[[], Awaitable[T]],
    *,
    breaker: CircuitBreaker | None = None,
    retries: int = 2,
    timeout: float = 20.0,
    base_delay: float = 0.4,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    if breaker and not breaker.allow():
        raise CircuitOpenError("circuit open")
    last: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            result = await asyncio.wait_for(fn(), timeout=timeout)
            if breaker:
                breaker.success()
            return result
        except retry_on as exc:
            last = exc
            if breaker:
                breaker.failure()
                if not breaker.allow():
                    break
            if attempt < retries:
                await asyncio.sleep(base_delay * (2**attempt) + random.random() * 0.05)  # noqa: S311
    assert last is not None
    raise last
