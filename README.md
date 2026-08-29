# AI Video Experiments

Foundation project for AI video generation via OpenRouter's Video Generation API. Built to experiment with software architecture videos (Kubernetes, etc.).

## Setup

```bash
cp .env.example .env
```

Edit `.env` and add your `OPENROUTER_API_KEY`.

For audio merging, install `ffmpeg`:

```bash
sudo pacman -S ffmpeg
```

## Usage

```bash
# List available video models
uv run python examples/list_models.py

# Generate a video
uv run python examples/basic_generate.py

# Generate narration audio
uv run python examples/generate_audio.py

# Add narration to a video
uv run python examples/add_audio_to_video.py

# End-to-end: video + narration + merge
uv run python examples/video_with_narration.py
```

## Audio Options

### 1. Model-generated audio

Set `generate_audio=True` in `VideoGenerationConfig`. Supported models may include audio directly in the video output.

### 2. Separate TTS narration

Use `AudioClient` to generate speech via OpenRouter's `/api/v1/audio/speech` endpoint, then merge with `AudioClient.merge_audio_video()`.

```python
from video_gen import AudioClient

audio = AudioClient()
audio.generate_speech(
    text="Your narration here",
    output_path="narration.mp3",
    model="deepgram/flux-tts:free",
    voice="flux-alexis-en",
)

audio.merge_audio_video("out.mp4", "narration.mp3", "final.mp4")
```

Note: `voice` and `speed` are optional and model-dependent. Only pass them if the model supports them. You can query available TTS models via:

```bash
curl "https://openrouter.ai/api/v1/models?output_modalities=speech" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

### 3. Auto-generate narration from video prompt

Generate a narration script from the video prompt using a chat model, then synthesize speech and merge:

```python
from video_gen import AudioClient

audio = AudioClient()
script_path, audio_path = audio.generate_narration_audio(
    prompt="A paper boat drifting down a rain-slicked gutter...",
    output_path="narration.mp3",
    chat_model="openai/gpt-4o-mini",
    tts_model="deepgram/flux-tts:free",
    voice="flux-alexis-en",
)
audio.merge_audio_video("out.mp4", audio_path, "final.mp4")
```

Or just generate the script without audio:

```python
script = audio.generate_narration(
    prompt="A paper boat drifting down a rain-slicked gutter...",
    model="openai/gpt-4o-mini",
)
```

## LangSmith Tracing

Traces can be enabled through OpenRouter's Broadcast feature. Configure it in the [OpenRouter Observability Settings](https://openrouter.ai/settings/observability):

1. Enable **Broadcast**
2. Add a **LangSmith** destination with your API key and project name

Alternatively, pass tracing metadata directly in the request using `RequestMetadata`:

```python
from video_gen import AudioClient, RequestMetadata, VideoClient, VideoGenerationConfig

metadata = RequestMetadata(
    trace_name="video-narration-pipeline",
    span_name="generate-video",
    generation_name="video-generation",
    environment="experiments",
    tags=["kubernetes", "architecture"],
)

config = VideoGenerationConfig(
    model="bytedance/seedance-2.0",
    prompt="...",
    metadata=metadata,
)

job = client.submit_job(config)
```

Supported fields: `trace_id`, `trace_name`, `span_name`, `generation_name`, `parent_span_id`, `environment`, `team`, `user`, `session_id`, `tags`, `metadata`. See the [OpenRouter LangSmith docs](https://openrouter.ai/docs/guides/features/broadcast/langsmith).
