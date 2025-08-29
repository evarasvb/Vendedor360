import asyncio
import random
import time
from functools import wraps
from typing import Any, Callable, Iterable, Tuple, Type


def retry_with_exponential_backoff(
	*,
	max_retries: int = 5,
	initial_delay_seconds: float = 0.5,
	max_delay_seconds: float = 8.0,
	exceptions: Tuple[Type[BaseException], ...] = (Exception,),
	jitter: float = 0.2,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
	def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
		if asyncio.iscoroutinefunction(func):
			@wraps(func)
			async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
				delay = initial_delay_seconds
				attempt = 0
				while True:
					try:
						return await func(*args, **kwargs)
					except exceptions as exc:
						attempt += 1
						if attempt > max_retries:
							raise
						j = random.uniform(-jitter, jitter) if jitter else 0
						await asyncio.sleep(min(max_delay_seconds, max(0.0, delay + j)))
						delay = min(max_delay_seconds, delay * 2)

			return async_wrapper

		@wraps(func)
		def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
			delay = initial_delay_seconds
			attempt = 0
			while True:
				try:
					return func(*args, **kwargs)
				except exceptions as exc:
					attempt += 1
					if attempt > max_retries:
						raise
					j = random.uniform(-jitter, jitter) if jitter else 0
					time.sleep(min(max_delay_seconds, max(0.0, delay + j)))
					delay = min(max_delay_seconds, delay * 2)

		return sync_wrapper

	return decorator