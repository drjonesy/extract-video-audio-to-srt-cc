#!/usr/bin/env python3
"""
Desktop app for generating closed captions (SRT) from video files using OpenAI Whisper.
Uses pywebview for a native window with the existing HTML/CSS/JS UI.
"""

# Prevent macOS segfault with MKL/OpenMP threading conflicts
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import json
import subprocess
import tempfile
import threading
from pathlib import Path

import webview

ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}


def format_timestamp(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def build_srt(segments: list[dict], word_level: bool) -> str:
    lines: list[str] = []
    if word_level:
        counter = 1
        for seg in segments:
            if "words" not in seg:
                continue
            for w in seg["words"]:
                start = format_timestamp(w["start"])
                end = format_timestamp(w["end"])
                word = w["word"].strip()
                lines.append(f"{counter}\n{start} --> {end}\n{word}\n")
                counter += 1
    else:
        for i, seg in enumerate(segments, 1):
            start = format_timestamp(seg["start"])
            end = format_timestamp(seg["end"])
            text = seg["text"].strip()
            lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def extract_audio(video_path: str, audio_path: str) -> None:
    subprocess.run(
        ["ffmpeg", "-i", video_path, "-ar", "16000", "-ac", "1",
         "-c:a", "pcm_s16le", audio_path, "-y"],
        capture_output=True, check=True,
    )


class Api:
    """Python API exposed to JavaScript via window.pywebview.api"""

    def __init__(self, window_ref):
        self._window_ref = window_ref

    def get_cwd(self):
        return os.getcwd()

    def pick_video(self):
        """Open native file picker for video files."""
        result = self._window_ref[0].create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("Video Files (*.mp4;*.mov;*.avi;*.mkv;*.webm)",),
        )
        if result and len(result) > 0:
            return result[0]
        return ""

    def pick_directory(self):
        """Open native folder picker."""
        result = self._window_ref[0].create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            return result[0]
        return ""

    def generate(self, video_path, output_dir, model_name, word_timestamps, language):
        """Run transcription in a background thread, pushing progress to the UI."""
        thread = threading.Thread(
            target=self._transcribe,
            args=(video_path, output_dir, model_name, word_timestamps, language),
            daemon=True,
        )
        thread.start()

    def _transcribe(self, video_path, output_dir, model_name, word_timestamps, language):
        window = self._window_ref[0]
        audio_path = None

        try:
            # Step 1: extract audio
            self._send_progress(window, "extracting", "Extracting audio from video...")
            audio_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            audio_path = audio_tmp.name
            audio_tmp.close()
            extract_audio(video_path, audio_path)

            # Step 2: load model
            self._send_progress(window, "loading", f"Loading Whisper model '{model_name}'...")
            import whisper
            model = whisper.load_model(model_name)

            # Step 3: transcribe
            self._send_progress(window, "transcribing", "Transcribing audio... this may take a while.")
            result = model.transcribe(
                audio_path,
                language=language if language else None,
                word_timestamps=word_timestamps,
            )

            # Step 4: write SRT
            self._send_progress(window, "writing", "Writing SRT file...")
            srt_content = build_srt(result["segments"], word_timestamps)

            stem = Path(video_path).stem
            out_dir = Path(output_dir) if output_dir else Path.cwd()
            out_dir.mkdir(parents=True, exist_ok=True)
            srt_path = out_dir / f"{stem}.srt"
            srt_path.write_text(srt_content, encoding="utf-8")

            transcript_text = result.get("text", "").strip()
            detected_lang = result.get("language", "unknown")

            done_data = json.dumps({
                "status": "done",
                "message": "Transcription complete!",
                "srt_path": str(srt_path),
                "transcript": transcript_text,
                "language": detected_lang,
                "segments": len(result["segments"]),
            })
            window.evaluate_js(f"onProgress({done_data})")

        except Exception as exc:
            err_data = json.dumps({"status": "error", "message": str(exc)})
            window.evaluate_js(f"onProgress({err_data})")

        finally:
            if audio_path:
                try:
                    os.unlink(audio_path)
                except OSError:
                    pass

    def _send_progress(self, window, status, message):
        data = json.dumps({"status": status, "message": message})
        window.evaluate_js(f"onProgress({data})")


def main():
    window_ref = [None]
    api = Api(window_ref)

    base_dir = os.path.dirname(__file__)
    html_path = os.path.join(base_dir, "templates", "index.html")
    icon_path = os.path.join(base_dir, "icon.png")

    window = webview.create_window(
        "Caption Generator",
        url=html_path,
        js_api=api,
        width=780,
        height=850,
        min_size=(500, 600),
    )
    window_ref[0] = window

    def on_started():
        if os.path.isfile(icon_path):
            try:
                from AppKit import NSApplication, NSImage
                from PyObjCTools import AppHelper
                def _set():
                    ns_app = NSApplication.sharedApplication()
                    ns_image = NSImage.alloc().initWithContentsOfFile_(icon_path)
                    if ns_image:
                        ns_app.setApplicationIconImage_(ns_image)
                AppHelper.callAfter(_set)
            except ImportError:
                pass

    webview.start(func=on_started, debug=False)


if __name__ == "__main__":
    main()
