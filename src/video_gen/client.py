import os
import time
from typing import Callable, Self
from urllib.parse import urljoin

from dotenv import load_dotenv

import requests

from video_gen.exceptions import (
    JobFailedError,
    JobTimeoutError,
    RateLimitError,
    VideoGenerationError,
)
from video_gen.models import VideoGenerationConfig, VideoJob, VideoModel

load_dotenv()


TERMINAL_ERROR_STATES = {"failed", "cancelled", "expired"}
DEFAULT_POLL_INTERVAL = 30.0
DEFAULT_POLL_TIMEOUT = 3600.0


class VideoClient:
    """Client for interacting with the OpenRouter Video Generation API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        poll_timeout: float = DEFAULT_POLL_TIMEOUT,
    ):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise VideoGenerationError("OPENROUTER_API_KEY is not set.")

        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def list_models(self) -> list[VideoModel]:
        """Query available video models and their capabilities."""
        response = self._session.get(
            self._url("/videos/models"),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        models = data.get("data", [])
        return [VideoModel.from_api_response(m) for m in models]

    def submit_job(self, config: VideoGenerationConfig) -> VideoJob:
        """Submit a new video generation job."""
        response = self._session.post(
            self._url("/videos"),
            json=config.to_payload(),
            timeout=60,
        )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(retry_after=float(retry_after) if retry_after else None)

        response.raise_for_status()
        return VideoJob.from_api_response(response.json())

    def get_job(self, job_id: str) -> VideoJob:
        """Fetch the current status of a job."""
        response = self._session.get(
            self._url(f"/videos/{job_id}"),
            timeout=30,
        )
        response.raise_for_status()
        return VideoJob.from_api_response(response.json())

    def poll_job(
        self,
        job: VideoJob,
        interval: float | None = None,
        timeout: float | None = None,
        on_status: Callable[[VideoJob], None] | None = None,
    ) -> VideoJob:
        """Poll a job until completion or terminal error state."""
        interval = interval if interval is not None else self.poll_interval
        timeout = timeout if timeout is not None else self.poll_timeout

        polling_url = urljoin(f"{self.base_url}/", job.polling_url)
        deadline = time.monotonic() + timeout
        current = job

        while True:
            if on_status:
                on_status(current)

            status = current.status

            if status == "completed":
                return current

            if status in TERMINAL_ERROR_STATES:
                raise JobFailedError(
                    job_id=current.id,
                    status=status,
                    error=current.error,
                )

            if status not in {"pending", "in_progress"}:
                raise VideoGenerationError(
                    f"Received unexpected job status: {status}",
                    status=status,
                )

            if time.monotonic() >= deadline:
                raise JobTimeoutError(job_id=current.id, timeout=timeout)

            time.sleep(interval)

            try:
                response = self._session.get(polling_url, timeout=30)
                response.raise_for_status()
                current = VideoJob.from_api_response(response.json())
            except requests.exceptions.RequestException as exc:
                raise VideoGenerationError(
                    f"Polling request failed: {exc}"
                ) from exc

    def download_video(
        self,
        job: VideoJob,
        output_path: str,
        index: int = 0,
        chunk_size: int = 1024 * 1024,
    ) -> str:
        """Download the generated video to a local file."""
        if not job.is_completed:
            raise VideoGenerationError(
                f"Job {job.id} is not completed (status: {job.status})."
            )

        download_url = (
            job.unsigned_urls[index]
            if len(job.unsigned_urls) > index
            else self._url(f"/videos/{job.id}/content?index={index}")
        )

        response = self._session.get(
            download_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            stream=True,
            timeout=180,
        )
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

        return output_path

    def generate_video(
        self,
        config: VideoGenerationConfig,
        output_path: str,
        on_status: Callable[[VideoJob], None] | None = None,
    ) -> VideoJob:
        """High-level method that submits, polls, and downloads in one call."""
        job = self.submit_job(config)
        completed = self.poll_job(job, on_status=on_status)
        self.download_video(completed, output_path)
        return completed

    def close(self) -> None:
        """Close the underlying session."""
        self._session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
