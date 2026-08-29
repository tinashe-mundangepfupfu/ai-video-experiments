import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from video_gen import AudioClient, VideoClient, VideoGenerationConfig, VideoGenerationError


MODEL = os.environ.get("VIDEO_MODEL", "bytedance/seedance-2.0")
PROMPT = (
    "A paper boat drifting down a rain-slicked gutter at night, "
    "neon reflections, slow tracking shot, cinematic lighting"
)
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "out.mp4")


def main() -> None:
    client = VideoClient()

    try:
        with client:
            models = client.list_models()
            print(f"Available models: {len(models)}")
            for m in models[:5]:
                print(f"  - {m.id}")

            config = VideoGenerationConfig(
                model=MODEL,
                prompt=PROMPT,
                duration=4,
                resolution="720p",
                aspect_ratio="16:9",
                generate_audio=False,
            )

            print(f"\nSubmitting job with model: {MODEL}")
            job = client.submit_job(config)
            print(f"Job ID: {job.id}")
            print(f"Status: {job.status}")

            def on_status(current_job):
                print(f"Status: {current_job.status}")

            completed = client.poll_job(job, on_status=on_status)
            print(f"Job completed. Downloading to {OUTPUT_PATH}")

            client.download_video(completed, OUTPUT_PATH)
            print(f"Saved video to {OUTPUT_PATH}")

            usage = completed.usage or {}
            print(f"Generation cost: {usage.get('cost')}")

    except VideoGenerationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
