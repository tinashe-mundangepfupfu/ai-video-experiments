import os
import subprocess
from typing import Any, Optional

import requests

from video_gen.exceptions import VideoGenerationError
from video_gen.models import RequestMetadata


NARRATION_SYSTEM_PROMPT = (
    "You are a professional narration scriptwriter for short AI-generated videos. "
    "Write concise, engaging narration (1-3 sentences) that describes the scene in the video. "
    "Match the tone and style of the prompt. Do not exceed 100 words."
)


class AudioClient:
    """Client for OpenRouter TTS, narration generation, and local audio operations."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise VideoGenerationError("OPENROUTER_API_KEY is not set.")

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def _apply_metadata(self, payload: dict[str, Any], metadata: RequestMetadata | None) -> dict[str, Any]:
        if metadata is not None:
            payload.update(metadata.to_dict())
        return payload

    def generate_narration(
        self,
        prompt: str,
        model: str = "openai/gpt-4o-mini",
        system_prompt: str = NARRATION_SYSTEM_PROMPT,
        metadata: RequestMetadata | None = None,
    ) -> str:
        """Generate a narration script from a video prompt using a chat model."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Video prompt: {prompt}"},
            ],
            "max_tokens": 200,
            "temperature": 0.7,
        }
        payload = self._apply_metadata(payload, metadata)

        response = self._session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise VideoGenerationError("No narration generated.")
        return choices[0]["message"]["content"].strip()

    def generate_speech(
        self,
        text: str,
        output_path: str = "output.mp3",
        model: str = "deepgram/flux-tts:free",
        voice: Optional[str] = None,
        response_format: str = "mp3",
        speed: Optional[float] = None,
        metadata: RequestMetadata | None = None,
    ) -> str:
        """Generate speech from text and save to a file."""
        payload: dict[str, Any] = {
            "model": model,
            "input": text,
            "response_format": response_format,
        }
        if voice is not None:
            payload["voice"] = voice
        if speed is not None:
            payload["speed"] = speed

        payload = self._apply_metadata(payload, metadata)

        response = self._session.post(
            "https://openrouter.ai/api/v1/audio/speech",
            json=payload,
            timeout=120,
        )

        if response.status_code == 400:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise VideoGenerationError(
                f"TTS request failed with 400 Bad Request: {body}",
                details={"model": model, "voice": voice, "response_format": response_format},
            )

        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

        return output_path

    def generate_narration_audio(
        self,
        prompt: str,
        output_path: str = "narration.mp3",
        chat_model: str = "openai/gpt-4o-mini",
        tts_model: str = "deepgram/flux-tts:free",
        voice: str = "flux-alexis-en",
        metadata: RequestMetadata | None = None,
    ) -> tuple[str, str]:
        """Generate narration script from prompt, then synthesize speech. Returns (script_path, audio_path)."""
        script = self.generate_narration(prompt, model=chat_model, metadata=metadata)

        script_path = output_path.replace(".mp3", ".txt")
        with open(script_path, "w") as f:
            f.write(script)

        audio_path = self.generate_speech(
            text=script,
            output_path=output_path,
            model=tts_model,
            voice=voice,
            metadata=metadata,
        )

        return script_path, audio_path

    @staticmethod
    def merge_audio_video(
        video_path: str,
        audio_path: str,
        output_path: str,
        replace_audio: bool = True,
    ) -> str:
        """Merge audio into a video using ffmpeg."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise VideoGenerationError(
                "ffmpeg is not installed or not in PATH. Install it to merge audio and video."
            ) from exc

        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ac", "2",
            "-ar", "44100",
        ]

        if replace_audio:
            cmd.extend(["-map", "0:v:0", "-map", "1:a:0", "-shortest"])
        else:
            cmd.extend(["-map", "0:v:0", "-map", "0:a:0", "-map", "1:a:0", "-shortest"])

        cmd.append(output_path)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise VideoGenerationError(
                f"ffmpeg failed: {result.stderr}",
                details={"stderr": result.stderr},
            )

        return output_path

    @staticmethod
    def normalize_audio(
        input_path: str,
        output_path: str,
        target_level: float = -20.0,
    ) -> str:
        """Normalize audio volume using ffmpeg loudnorm filter."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise VideoGenerationError(
                "ffmpeg is not installed or not in PATH."
            ) from exc

        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-af", f"loudnorm=I={target_level}:TP=-1.5:LRA=11",
            "-ar", "44100",
            "-ac", "2",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise VideoGenerationError(
                f"ffmpeg normalization failed: {result.stderr}",
                details={"stderr": result.stderr},
            )

        return output_path

    def close(self) -> None:
        """Close the underlying session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
