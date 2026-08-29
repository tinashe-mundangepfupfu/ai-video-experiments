from dataclasses import dataclass, field
from typing import Any, Literal, Self


VideoJobStatus = Literal["pending", "in_progress", "completed", "failed", "cancelled", "expired"]


@dataclass
class RequestMetadata:
    """LangSmith / OpenRouter Broadcast tracing metadata.

    See https://openrouter.ai/docs/guides/features/broadcast/langsmith
    """

    trace_id: str | None = None
    trace_name: str | None = None
    span_name: str | None = None
    generation_name: str | None = None
    parent_span_id: str | None = None
    environment: str | None = None
    team: str | None = None
    user: str | None = None
    session_id: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.trace_id is not None:
            payload["trace_id"] = self.trace_id
        if self.trace_name is not None:
            payload["trace_name"] = self.trace_name
        if self.span_name is not None:
            payload["span_name"] = self.span_name
        if self.generation_name is not None:
            payload["generation_name"] = self.generation_name
        if self.parent_span_id is not None:
            payload["parent_span_id"] = self.parent_span_id
        if self.environment is not None:
            payload["environment"] = self.environment
        if self.team is not None:
            payload["team"] = self.team
        if self.user is not None:
            payload["user"] = self.user
        if self.session_id is not None:
            payload["session_id"] = self.session_id
        if self.tags:
            payload["tags"] = self.tags
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass
class VideoGenerationConfig:
    """Configuration for a video generation request."""

    model: str
    prompt: str
    duration: int = 4
    resolution: str = "720p"
    aspect_ratio: str = "16:9"
    generate_audio: bool = False
    seed: int | None = None
    callback_url: str | None = None
    provider_options: dict[str, dict] = field(default_factory=dict)
    metadata: RequestMetadata | None = None

    def to_payload(self) -> dict:
        payload: dict = {
            "model": self.model,
            "prompt": self.prompt,
            "duration": self.duration,
            "resolution": self.resolution,
            "aspect_ratio": self.aspect_ratio,
            "generate_audio": self.generate_audio,
        }

        if self.seed is not None:
            payload["seed"] = self.seed
        if self.callback_url:
            payload["callback_url"] = self.callback_url
        if self.provider_options:
            payload["provider"] = {"options": self.provider_options}
        if self.metadata is not None:
            payload.update(self.metadata.to_dict())

        return payload


@dataclass
class VideoModel:
    """Represents a supported video model and its capabilities."""

    id: str
    name: str
    supported_resolutions: list[str] = field(default_factory=list)
    supported_durations: list[int] = field(default_factory=list)
    supported_aspect_ratios: list[str] = field(default_factory=list)
    supports_audio: bool = False
    pricing_skus: list[dict] = field(default_factory=list)
    provider: str | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> Self:
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            supported_resolutions=data.get("supported_resolutions", []),
            supported_durations=data.get("supported_durations", []),
            supported_aspect_ratios=data.get("supported_aspect_ratios", []),
            supports_audio=data.get("supports_audio", False),
            pricing_skus=data.get("pricing_skus", []),
            provider=data.get("provider"),
        )


@dataclass
class VideoJob:
    """Represents a video generation job returned by the API."""

    id: str
    status: VideoJobStatus
    polling_url: str
    unsigned_urls: list[str] = field(default_factory=list)
    error: str | None = None
    usage: dict | None = None
    model: str | None = None

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def is_terminal_error(self) -> bool:
        return self.status in {"failed", "cancelled", "expired"}

    @property
    def is_active(self) -> bool:
        return self.status in {"pending", "in_progress"}

    @property
    def download_url(self) -> str | None:
        if self.unsigned_urls:
            return self.unsigned_urls[0]
        return None

    @classmethod
    def from_api_response(cls, data: dict) -> Self:
        return cls(
            id=data["id"],
            status=data["status"],
            polling_url=data["polling_url"],
            unsigned_urls=data.get("unsigned_urls", []),
            error=data.get("error"),
            usage=data.get("usage"),
            model=data.get("model"),
        )
