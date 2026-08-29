import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from video_gen import AudioClient


MODEL = os.environ.get("TTS_MODEL", "deepgram/flux-tts:free")
VOICE = os.environ.get("TTS_VOICE", "flux-alexis-en")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "output.mp3")
TEXT = os.environ.get("TTS_TEXT", "Welcome to this Kubernetes architecture overview.")


def main() -> None:
    client = AudioClient()
    path = client.generate_speech(
        text=TEXT,
        output_path=OUTPUT_PATH,
        model=MODEL,
        voice=VOICE,
    )
    print(f"Audio saved to {path}")


if __name__ == "__main__":
    main()
