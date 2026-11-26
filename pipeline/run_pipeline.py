import argparse
from pathlib import Path
from common import REPO_ROOT, load_storyboard
import script_stage
import keyframes_stage
import shots_stage
import music_stage
import narration_stage
import assemble_stage


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Heritage Short AI pipeline")
    parser.add_argument(
        "--stage",
        choices=["all", "script", "keyframes", "shots", "music", "narration", "assemble"],
        default="all",
    )
    parser.add_argument("--storyboard", type=Path, default=REPO_ROOT / "storyboard.json")
    parser.add_argument("--force", action="store_true", help="Ignore input-hash cache and regenerate")
    args = parser.parse_args()

    # Always validate contract before any stage runs
    load_storyboard(args.storyboard)

    if args.stage in ("all", "script"):
        script_stage.run(args.storyboard, force=args.force)
    if args.stage in ("all", "keyframes"):
        keyframes_stage.run(args.storyboard, force=args.force)
    if args.stage in ("all", "shots"):
        shots_stage.run(args.storyboard, force=args.force)
    if args.stage in ("all", "music"):
        music_stage.run(args.storyboard, force=args.force)
    if args.stage in ("all", "narration"):
        narration_stage.run(args.storyboard, force=args.force)
    if args.stage in ("all", "assemble"):
        assemble_stage.run(args.storyboard, force=args.force)


if __name__ == "__main__":
    main()
