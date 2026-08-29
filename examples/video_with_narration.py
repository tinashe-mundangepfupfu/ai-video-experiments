import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from video_gen import AudioClient, RequestMetadata, VideoClient, VideoGenerationConfig, VideoGenerationError


VIDEO_MODEL = os.environ.get("VIDEO_MODEL", "bytedance/seedance-2.0")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "openai/gpt-4o-mini")
TTS_MODEL = os.environ.get("TTS_MODEL", "deepgram/flux-tts:free")
TTS_VOICE = os.environ.get("TTS_VOICE", "flux-alexis-en")
PROMPT = (
    "A paper boat drifting down a rain-slicked gutter at night, "
    "neon reflections, slow tracking shot, cinematic lighting"
)
VIDEO_OUTPUT = os.environ.get("VIDEO_OUTPUT", "out.mp4")
AUDIO_OUTPUT = os.environ.get("AUDIO_OUTPUT", "narration.mp3")
FINAL_OUTPUT = os.environ.get("FINAL_OUTPUT", "final.mp4")


def main() -> None:
    metadata = RequestMetadata(
        trace_name="video-narration-pipeline",
        span_name="generate-video",
        generation_name="video-generation",
        environment="experiments",
        tags=["kubernetes", "architecture", "video-experiment"],
    )

    video_client = VideoClient()
    audio_client = AudioClient()

    try:
        with video_client:
            print("=== Step 1: Generate video ===")
            config = VideoGenerationConfig(
                model=VIDEO_MODEL,
                prompt=PROMPT,
                duration=4,
                resolution="720p",
                aspect_ratio="16:9",
                generate_audio=False,
                metadata=metadata,
            )

            job = video_client.submit_job(config)
            print(f"Video job ID: {job.id}")

            def on_status(current_job):
                print(f"Video status: {current_job.status}")

            completed = video_client.poll_job(job, on_status=on_status)
            video_client.download_video(completed, VIDEO_OUTPUT)
            print(f"Video saved to {VIDEO_OUTPUT}")

        print("\n=== Step 2: Generate narration from prompt ===")
        narration_metadata = RequestMetadata(
            trace_name="video-narration-pipeline",
            span_name="generate-narration",
            generation_name="narration-generation",
            parent_span_id="generate-video",
            environment="experiments",
            tags=["kubernetes", "architecture", "video-experiment"],
        )

        script_path, audio_path = audio_client.generate_narration_audio(
            prompt=PROMPT,
            output_path=AUDIO_OUTPUT,
            chat_model=CHAT_MODEL,
            tts_model=TTS_MODEL,
            voice=TTS_VOICE,
            metadata=narration_metadata,
        )
        print(f"Narration script saved to {script_path}")
        print(f"Narration audio saved to {audio_path}")

        print("\n=== Step 3: Merge audio into video ===")
        result = audio_client.merge_audio_video(
            video_path=VIDEO_OUTPUT,
            audio_path=audio_path,
            output_path=FINAL_OUTPUT,
        )
        print(f"Final video with narration: {result}")

    except VideoGenerationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
