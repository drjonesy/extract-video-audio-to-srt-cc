#!/usr/bin/env python3
"""
MP3 & SRT Maker — batch desktop app that turns video files into MP3 audio and/or
SRT closed captions (via OpenAI Whisper). Each table row is an independent job
that can be started, stopped, and removed. Uses pywebview for a native window.
"""

# Prevent macOS segfault with MKL/OpenMP threading conflicts
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import json
import shutil
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


def build_srt(segments: list[dict]) -> str:
    lines: list[str] = []
    for i, seg in enumerate(segments, 1):
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


class JobCancelled(Exception):
    """Raised to abort a job when the user presses Stop."""


# --- Whisper transcription progress hook ---------------------------------
# Whisper drives a tqdm bar over audio frames inside transcribe(). We swap in
# this shim so each pbar.update() reports a real completion fraction to the UI.
# The hook is stored per-thread so concurrent rows route progress (and cancel)
# to their own job without racing on a shared global.
_thread_local = threading.local()


class _ProgressTqdm:
    def __init__(self, *args, total=0, **kwargs):
        self.total = total or 0
        self.n = 0

    def update(self, n=1):
        self.n += n
        hook = getattr(_thread_local, "hook", None)
        if hook and self.total:
            hook(min(self.n / self.total, 1.0))

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _TqdmModuleShim:
    """Stands in for the `tqdm` module: exposes `.tqdm` like the real one."""
    tqdm = _ProgressTqdm


class Api:
    """Python API exposed to JavaScript via window.pywebview.api"""

    def __init__(self, window_ref):
        self._window_ref = window_ref
        # job_id -> {"cancel": bool, "proc": Popen|None}
        self._jobs = {}

    def get_cwd(self):
        return os.getcwd()

    def pick_videos(self):
        """Open native file picker; returns a list of selected video paths."""
        result = self._window_ref[0].create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=True,
            file_types=("Video Files (*.mp4;*.mov;*.avi;*.mkv;*.webm)",),
        )
        return list(result) if result else []

    def pick_directory(self):
        """Open native folder picker."""
        result = self._window_ref[0].create_file_dialog(webview.FileDialog.FOLDER)
        if result and len(result) > 0:
            return result[0]
        return ""

    def start_job(self, job_id, video_path, output_dir, model_name, language,
                  create_srt, create_mp3, new_folder, move_video):
        """Run one table row's selected steps in a background thread."""
        self._jobs[job_id] = {"cancel": False, "proc": None}
        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, video_path, output_dir, model_name, language,
                  create_srt, create_mp3, new_folder, move_video),
            daemon=True,
        )
        thread.start()

    def stop_job(self, job_id):
        """Flag a job to cancel and kill any ffmpeg subprocess it is running."""
        job = self._jobs.get(job_id)
        if not job:
            return
        job["cancel"] = True
        proc = job.get("proc")
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    def _check_cancel(self, job_id):
        if self._jobs.get(job_id, {}).get("cancel"):
            raise JobCancelled()

    def _run_ff(self, job_id, cmd):
        """Run an ffmpeg command as a killable subprocess registered to the job."""
        job = self._jobs.get(job_id, {})
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        job["proc"] = proc
        proc.wait()
        job["proc"] = None
        if job.get("cancel"):
            raise JobCancelled()
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)

    def _run_job(self, job_id, video_path, output_dir, model_name, language,
                 create_srt, create_mp3, new_folder, move_video):
        window = self._window_ref[0]
        temp_audio = None

        try:
            self._check_cancel(job_id)
            stem = Path(video_path).stem

            # Resolve output directory. Optionally nest in a folder named
            # after the video file.
            out_dir = Path(output_dir) if output_dir else Path(video_path).parent
            if new_folder:
                out_dir = out_dir / stem
            out_dir.mkdir(parents=True, exist_ok=True)

            # Step 1: MP3. Made when requested; also reused as the SRT audio
            # source so we never extract twice.
            mp3_path = None
            if create_mp3:
                mp3_path = out_dir / f"{stem}.mp3"
                self._send_progress(job_id, "extracting",
                                    "Creating MP3...", percent=4)
                self._run_ff(job_id, [
                    "ffmpeg", "-i", str(video_path), "-vn", "-ar", "44100",
                    "-ac", "2", "-b:a", "192k", str(mp3_path), "-y",
                ])

            # Step 2: SRT (optional). Skips the whole Whisper pipeline when off.
            srt_path = None
            transcript_text = ""
            detected_lang = "unknown"
            segment_count = 0
            if create_srt:
                self._check_cancel(job_id)
                # Pick an audio source for Whisper: reuse the MP3 if we made one,
                # otherwise extract a throwaway WAV.
                if mp3_path:
                    audio_source = str(mp3_path)
                else:
                    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    temp_audio = tmp.name
                    tmp.close()
                    self._send_progress(job_id, "extracting",
                                        "Extracting audio...", percent=4)
                    self._run_ff(job_id, [
                        "ffmpeg", "-i", str(video_path), "-ar", "16000",
                        "-ac", "1", "-c:a", "pcm_s16le", temp_audio, "-y",
                    ])
                    audio_source = temp_audio

                # load model
                self._send_progress(job_id, "loading",
                                    f"Loading model '{model_name}'...", percent=10)
                import sys
                import whisper
                import whisper.transcribe  # ensure submodule is in sys.modules
                # NOTE: the `whisper.transcribe` attribute is the re-exported
                # transcribe() function, not the module. Patch the real module so
                # transcribe()'s globals see our progress shim.
                sys.modules["whisper.transcribe"].tqdm = _TqdmModuleShim

                self._check_cancel(job_id)
                model = whisper.load_model(model_name)

                # transcribe (real progress from the tqdm hook, 10% -> 95%).
                # Raising inside the hook aborts transcribe() when Stop is hit.
                def on_frac(frac):
                    if self._jobs.get(job_id, {}).get("cancel"):
                        raise JobCancelled()
                    pct = 10 + frac * 85
                    self._send_progress(job_id, "transcribing",
                                        f"Transcribing... {int(pct)}%", percent=pct)

                _thread_local.hook = on_frac
                self._send_progress(job_id, "transcribing",
                                    "Transcribing...", percent=10)
                try:
                    result = model.transcribe(
                        audio_source,
                        language=language if language else None,
                    )
                finally:
                    _thread_local.hook = None

                # write SRT
                self._send_progress(job_id, "writing", "Writing SRT...", percent=96)
                srt_content = build_srt(result["segments"])
                srt_path = out_dir / f"{stem}.srt"
                srt_path.write_text(srt_content, encoding="utf-8")

                transcript_text = result.get("text", "").strip()
                detected_lang = result.get("language", "unknown")
                segment_count = len(result["segments"])

            # Optionally move the source video into the new folder, after the
            # outputs exist. Only applies when a new folder was created.
            final_video_path = video_path
            video_moved = False
            if move_video and new_folder:
                dest = out_dir / Path(video_path).name
                if Path(video_path).resolve() != dest.resolve():
                    self._send_progress(job_id, "moving",
                                        "Moving video...", percent=98)
                    shutil.move(str(video_path), str(dest))
                    final_video_path = str(dest)
                    video_moved = True

            done_data = json.dumps({
                "job_id": job_id,
                "status": "done",
                "message": "Complete",
                "srt_path": str(srt_path) if srt_path else "",
                "mp3_path": str(mp3_path) if mp3_path else "",
                "video_path": str(final_video_path),
                "moved_video": video_moved,
                "transcript": transcript_text,
                "language": detected_lang,
                "segments": segment_count,
                "has_srt": bool(srt_path),
                "percent": 100,
            })
            window.evaluate_js(f"onProgress({done_data})")

        except JobCancelled:
            data = json.dumps({"job_id": job_id, "status": "stopped",
                               "message": "Stopped"})
            window.evaluate_js(f"onProgress({data})")

        except Exception as exc:
            err_data = json.dumps({"job_id": job_id, "status": "error",
                                   "message": str(exc)})
            window.evaluate_js(f"onProgress({err_data})")

        finally:
            self._jobs.pop(job_id, None)
            if temp_audio:
                try:
                    os.unlink(temp_audio)
                except OSError:
                    pass

    def _send_progress(self, job_id, status, message, percent=None):
        data = json.dumps({"job_id": job_id, "status": status,
                           "message": message, "percent": percent})
        self._window_ref[0].evaluate_js(f"onProgress({data})")


def main():
    window_ref = [None]
    api = Api(window_ref)

    base_dir = os.path.dirname(__file__)
    html_path = os.path.join(base_dir, "templates", "index.html")
    icon_path = os.path.join(base_dir, "icon.png")

    window = webview.create_window(
        "MP3 & SRT Maker",
        url=html_path,
        js_api=api,
        width=1240,
        height=820,
        min_size=(900, 500),
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
