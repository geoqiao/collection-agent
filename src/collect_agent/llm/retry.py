import random
from dataclasses import dataclass


@dataclass
class RetryConfig:
    max_retries: int = 1
    base_delay: float = 1.0
    max_delay: float = 30.0

    def should_retry(self, status_code: int, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        # Don't retry auth errors
        if status_code in (401, 403):
            return False
        # Retry server errors and rate limits
        return bool(status_code >= 500 or status_code == 429)

    def get_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (2**attempt), self.max_delay)
        return delay * (0.5 + random.random())  # Jitter
