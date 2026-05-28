from app.core.errors import AppError


class RateLimitExceededError(AppError):
    """Error raised when a user exceeds the allowed rate limit."""

    def __init__(self, retry_after_seconds: int | None = None) -> None:
        super().__init__(
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded. Please retry after {retry_after_seconds} seconds."
            if retry_after_seconds is not None
            else "Rate limit exceeded. Please retry after some time.",
        )
        self.retry_after_seconds = retry_after_seconds
