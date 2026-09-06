import sys

from smartlane.pipeline import SmartLanePipeline


def main():
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "python -m smartlane.run <video_path>"
        )
        raise SystemExit(1)

    video_path = sys.argv[1]

    pipeline = SmartLanePipeline(video_path)

    pipeline.run()


if __name__ == "__main__":
    main()