import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from video_gen import AudioClient


VIDEO_PATH = os.environ.get("VIDEO_PATH", "out.mp4")
AUDIO_PATH = os.environ.get("AUDIO_PATH", "output.mp3")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "final.mp4")
TARGET_LEVEL = float(os.environ.get("TARGET_LEVEL", "-20.0"))


def main() -> None:
    client = AudioClient()

    normalized = "normalized.mp3"
    if not os.path.exists(AUDIO_PATH):
        print(f"Audio file not found: {AUDIO_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Normalizing audio to {TARGET_LEVEL} dB...")
    client.normalize_audio(AUDIO_PATH, normalized, target_level=TARGET_LEVEL)

    print(f"Merging audio into video...")
    result = client.merge_audio_video(VIDEO_PATH, normalized, OUTPUT_PATH)

    print(f"Final video saved to {result}")


if __name__ == "__main__":
    main()
