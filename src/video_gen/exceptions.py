class VideoGenerationError(Exception):
    """Base exception for video generation failures."""

    def __init__(self, message: str, status: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.status = status
        self.details = details or {}

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.status:
            parts.append(f"Status: {self.status}")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


class JobTimeoutError(VideoGenerationError):
    """Raised when a video generation job exceeds the timeout."""

    def __init__(self, job_id: str, timeout: float):
        super().__init__(
            f"Job {job_id} did not complete within {timeout} seconds.",
            status="timeout",
        )


class JobFailedError(VideoGenerationError):
    """Raised when a video generation job fails."""

    def __init__(self, job_id: str, status: str, error: str | None = None):
        super().__init__(
            f"Video generation job {job_id} ended with status '{status}'.",
            status=status,
            details={"error": error} if error else {},
        )


class RateLimitError(VideoGenerationError):
    """Raised when the API rate limit is hit."""

    def __init__(self, retry_after: float | None = None):
        super().__init__(
            "Rate limit exceeded.",
            status="rate_limited",
            details={"retry_after": retry_after} if retry_after is not None else {},
        )
