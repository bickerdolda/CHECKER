"""
Async Utilities Module - Python 3.12+ Compatible
Enhanced async/await patterns and error handling
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Callable, Any, TypeVar, Coroutine
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncContextManager:
    """Base async context manager for resource management"""

    async def __aenter__(self):
        """Async enter context"""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit context"""
        await self.cleanup()

    async def setup(self):
        """Override this method for setup logic"""
        pass

    async def cleanup(self):
        """Override this method for cleanup logic"""
        pass


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Decorator for retrying async functions with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception

        return wrapper

    return decorator


def async_timeout(
    timeout_seconds: float = 30.0,
) -> Callable:
    """
    Decorator for adding timeout to async functions

    Args:
        timeout_seconds: Timeout in seconds
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {timeout_seconds}s")
                raise

        return wrapper

    return decorator


@asynccontextmanager
async def async_timer(name: str = "Operation") -> AsyncGenerator[None, None]:
    """
    Context manager for timing async operations

    Usage:
        async with async_timer("Database Query"):
            await db.query()
    """
    import time

    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        logger.info(f"{name} completed in {elapsed:.3f}s")


class AsyncQueue:
    """Thread-safe async queue with rate limiting"""

    def __init__(self, max_size: int = 100, rate_limit: Optional[float] = None):
        """
        Initialize async queue

        Args:
            max_size: Maximum queue size
            rate_limit: Minimum delay between items (seconds)
        """
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.rate_limit = rate_limit
        self._last_process_time = 0.0

    async def put(self, item: Any) -> None:
        """Add item to queue"""
        await self.queue.put(item)

    async def get(self) -> Any:
        """Get item from queue with rate limiting"""
        import time

        item = await self.queue.get()

        if self.rate_limit:
            elapsed = time.perf_counter() - self._last_process_time
            if elapsed < self.rate_limit:
                await asyncio.sleep(self.rate_limit - elapsed)

            self._last_process_time = time.perf_counter()

        return item

    async def process(self, handler: Callable[[Any], Coroutine]) -> None:
        """Process all items in queue"""
        while True:
            item = await self.get()
            try:
                await handler(item)
            except Exception as e:
                logger.error(f"Error processing queue item: {e}")


class AsyncPoolExecutor:
    """Simple async pool for concurrent task execution"""

    def __init__(self, max_workers: int = 5):
        """Initialize executor with max workers"""
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)

    async def run_task(self, coro: Coroutine) -> Any:
        """Run task with semaphore control"""
        async with self.semaphore:
            return await coro

    async def run_tasks(self, coros: list[Coroutine]) -> list[Any]:
        """Run multiple tasks concurrently"""
        return await asyncio.gather(
            *[self.run_task(coro) for coro in coros],
            return_exceptions=False,
        )


@async_retry(max_attempts=3, delay=0.5)
async def resilient_operation(func: Callable, *args, **kwargs) -> Any:
    """Execute operation with automatic retry on failure"""
    return await func(*args, **kwargs)


async def gather_with_limit(
    coros: list[Coroutine],
    limit: int = 5,
) -> list[Any]:
    """
    Execute coroutines with concurrency limit

    Args:
        coros: List of coroutines
        limit: Maximum concurrent operations
    """
    executor = AsyncPoolExecutor(max_workers=limit)
    return await executor.run_tasks(coros)
