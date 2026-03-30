"""Token-bucket rate limiter for Anthropic API calls."""
import asyncio
import time


class TokenBucketRateLimiter:
    def __init__(self, requests_per_minute: int = 50):
        self._rate = requests_per_minute / 60.0
        self._tokens = float(requests_per_minute)
        self._max_tokens = float(requests_per_minute)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(self._max_tokens, self._tokens + elapsed * self._rate)
            self._last_update = now
            if self._tokens < 1:
                wait_time = (1 - self._tokens) / self._rate
                await asyncio.sleep(wait_time)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


# Singleton used by claude_service
_limiter = TokenBucketRateLimiter(requests_per_minute=50)


async def acquire() -> None:
    await _limiter.acquire()
