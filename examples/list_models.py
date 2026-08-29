import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from video_gen import VideoClient


def main() -> None:
    client = VideoClient()

    try:
        with client:
            models = client.list_models()
            print(f"{'Model':<40} {'Audio':<8} {'Resolutions'}")
            print("-" * 80)
            for m in models:
                resolutions = ", ".join(m.supported_resolutions) if m.supported_resolutions else "N/A"
                audio = "Yes" if m.supports_audio else "No"
                print(f"{m.id:<40} {audio:<8} {resolutions}")
    except Exception as exc:
        print(f"Error listing models: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
