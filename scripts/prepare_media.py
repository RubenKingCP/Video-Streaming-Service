# argparse: reads command-line options such as --input and --test
import argparse

# re: regular expressions, to check that the video id is valid
import re

# shutil: used to check that the ffmpeg program can be found
import shutil

# subprocess: runs ffmpeg as an external program
import subprocess

# sys: used to exit with an error code
import sys

# Path: handles file paths the same way on Windows and Linux
from pathlib import Path

# Project root: this file is in <root>/scripts/, so go up one level
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Folder where the original videos are kept
SOURCE_DIR = PROJECT_ROOT / "media" / "source"

# Folder where the HLS output goes (one subfolder per video)
HLS_DIR = PROJECT_ROOT / "media" / "hls"

# Same rule as video_service.py: the id may only contain letters, digits, _ and -
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


# Reads the command-line options
def parse_args() -> argparse.Namespace:
    # The parser also creates an automatic --help
    parser = argparse.ArgumentParser(description="Convert a video to HLS for the streaming service.")
    # Input video file (relative paths are taken from the project root)
    parser.add_argument("--input", default=str(SOURCE_DIR / "sample.mp4"), help="video file to convert")
    # Name of the output folder, which becomes the id in the URL (/videos/<id>/index.m3u8)
    parser.add_argument("--id", dest="video_id", help="video id (default: the input file name without extension)")
    # Segment length in seconds
    parser.add_argument("--segment", type=int, default=4, help="segment length in seconds (default: 4)")
    # Generate a synthetic test video instead of converting a file
    parser.add_argument("--test", action="store_true", help="generate a test pattern instead of using --input")
    # Length of the test video in seconds
    parser.add_argument("--duration", type=int, default=60, help="length of the --test video in seconds (default: 60)")
    # Return all options as one object (args.input, args.video_id, ...)
    return parser.parse_args()


# Builds the ffmpeg input options: either a real file or a generated test pattern
def input_options(args: argparse.Namespace) -> list[str]:
    # Test mode: no file needed
    if args.test:
        return [
            # "lavfi" is ffmpeg's built-in generator. testsrc = moving color bars with a timer
            "-f", "lavfi", "-i", f"testsrc=duration={args.duration}:size=1280x720:rate=25",
            # A sine tone as the audio track
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={args.duration}",
        ]

    # Real file: relative paths are resolved from the project root
    source = Path(args.input)
    if not source.is_absolute():
        source = PROJECT_ROOT / source
    # Stop with a clear message if the file doesn't exist
    if not source.is_file():
        sys.exit(f"Input video not found: {source}\nPut a video there, pass --input <file>, or use --test.")
    # Normal ffmpeg input
    return ["-i", str(source)]


# Main program
def main() -> None:
    # Read the options
    args = parse_args()

    # ffmpeg must be installed, otherwise nothing can be converted
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg was not found. Install it and add it to PATH (check with: ffmpeg -version).")

    # Choose the video id: given with --id, "test" in test mode, otherwise the file name without extension
    video_id = args.video_id or ("test" if args.test else Path(args.input).stem)
    # The id must follow the same rule the service uses, or the service would refuse to serve it
    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        sys.exit(f"Invalid video id '{video_id}': use only letters, digits, _ and -. Pass a valid one with --id.")

    # Output folder for this video, e.g. media/hls/sample/
    out_dir = HLS_DIR / video_id
    # Create it (and its parents) if needed; ffmpeg does not create folders
    out_dir.mkdir(parents=True, exist_ok=True)
    # Remove old segments, so a shorter new video doesn't leave stale files behind
    for old in out_dir.glob("*.ts"):
        old.unlink()

    # The full ffmpeg command, as a list (safe with spaces in paths, on Windows and Linux)
    command = [
        # The program, -y = overwrite existing output without asking
        "ffmpeg", "-y",
        # Only print errors and warnings, not the full progress output
        "-hide_banner", "-loglevel", "warning", "-stats",
        # Input: real file or test pattern
        *input_options(args),
        # Video codec H.264: supported by every browser
        "-c:v", "libx264",
        # Encoding speed/size trade-off; veryfast is fine for a demo video
        "-preset", "veryfast",
        # Quality (lower = better, larger). 23 is the usual default
        "-crf", "23",
        # Pixel format every player supports
        "-pix_fmt", "yuv420p",
        # Put a keyframe exactly every <segment> seconds, so every segment has the same length
        "-force_key_frames", f"expr:gte(t,n_forced*{args.segment})",
        # Audio codec AAC (ignored if the input has no audio)
        "-c:a", "aac", "-b:a", "128k",
        # Stop at the end of the shortest input (needed for the test pattern + tone)
        "-shortest",
        # Output format HLS
        "-f", "hls",
        # Target segment length in seconds
        "-hls_time", str(args.segment),
        # Video on demand: complete playlist that ends with #EXT-X-ENDLIST
        "-hls_playlist_type", "vod",
        # Segment file names: seg_000.ts, seg_001.ts, ...
        "-hls_segment_filename", str(out_dir / "seg_%03d.ts"),
        # The playlist file
        str(out_dir / "index.m3u8"),
    ]

    # Show what is happening
    print(f"Creating HLS for '{video_id}' in {out_dir} ...")
    # Run ffmpeg and wait for it to finish
    result = subprocess.run(command)
    # A non-zero exit code means ffmpeg failed
    if result.returncode != 0:
        sys.exit(f"ffmpeg failed with exit code {result.returncode}.")

    # Count the segments that were created
    segments = sorted(out_dir.glob("seg_*.ts"))
    # Total size in megabytes
    size_mb = sum(s.stat().st_size for s in segments) / 1_000_000
    # Final summary and the URL to use
    print(f"Done: {len(segments)} segments, {size_mb:.1f} MB")
    print(f"Playlist: {out_dir / 'index.m3u8'}")
    print(f"URL once the server runs: http://localhost:8000/videos/{video_id}/index.m3u8")


# Run main() only when the file is executed directly (not when imported)
if __name__ == "__main__":
    main()
