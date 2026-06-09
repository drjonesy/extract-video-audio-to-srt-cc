#!/usr/bin/env python3
"""
Generate closed captions (SRT) from video files using OpenAI Whisper.
Designed for YouTube Shorts (under 1 minute).

Usage:
    python3 generate_captions.py <video_file>
    python3 generate_captions.py <video_file> --model large-v3
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def check_dependencies():
    try:
        import whisper  # noqa: F401
    except ImportError:
        print("Whisper not installed. Run:\n  pip3 install openai-whisper")
        sys.exit(1)

    result = subprocess.run(["which", "ffmpeg"], capture_output=True)
    if result.returncode != 0:
        print("ffmpeg not found. Install with:\n  brew install ffmpeg")
        sys.exit(1)


def extract_audio(video_path, audio_path):
    """Extract audio from video as WAV for Whisper."""
    subprocess.run(
        ["ffmpeg", "-i", str(video_path), "-ar", "16000", "-ac", "1",
         "-c:a", "pcm_s16le", str(audio_path), "-y"],
        capture_output=True,
        check=True,
    )


def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def write_srt(segments, output_path):
    """Write segments to an SRT file."""
    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start = format_timestamp(seg["start"])
            end = format_timestamp(seg["end"])
            text = seg["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate captions from video using Whisper"
    )
    parser.add_argument("video", help="Path to video file")
    parser.add_argument(
        "--model", default="medium",
        help="Whisper model: tiny, base, small, medium, large-v3 (default: medium)"
    )
    parser.add_argument(
        "--language", default=None,
        help="Language code (e.g. 'en'). Auto-detected if not set."
    )
    args = parser.parse_args()

    check_dependencies()

    video_path = Path(args.video).resolve()
    if not video_path.exists():
        print(f"File not found: {video_path}")
        sys.exit(1)

    output_srt = video_path.with_suffix(".srt")

    print(f"Loading Whisper model '{args.model}'...")
    import whisper
    model = whisper.load_model(args.model)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        print("Extracting audio...")
        extract_audio(video_path, tmp.name)

        print("Transcribing...")
        result = model.transcribe(
            tmp.name,
            language=args.language,
        )

    write_srt(result["segments"], output_srt)

    print(f"\nDone! Caption file saved to:\n  {output_srt}")
    print(f"\nDetected language: {result.get('language', 'unknown')}")
    print(f"Segments: {len(result['segments'])}")


if __name__ == "__main__":
    main()
