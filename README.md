<h1><img src="icon.png" style="width: 30px"> Caption Generator</h1>

Turn a video into captions (subtitles) on your own computer. You pick a video,
press a button, and it makes a **.srt** caption file you can upload to YouTube.
It can also save an **.mp3** of the sound. Great for YouTube Shorts.

It runs locally using [OpenAI Whisper](https://github.com/openai/whisper) — your
videos never leave your computer.

---

## What it can do

- 🎬 Pick a video with one button (mp4, mov, avi, mkv, webm)
- 📝 Make a **.srt** caption file
- 🎵 Also save an **.mp3** of the audio (on by default)
- 📁 Put the results in a new folder named after your video (on by default)
- 📦 Optionally move the video into that folder too, so everything stays together
- 📂 Saves next to your video automatically (you can change where)
- ⏳ A progress bar that fills up and shows a percent
- 🌍 Auto-detects the language (or you can pick one)

---

## Setup — do this **once**

You only have to do these steps the first time. Take your time. 🙂

### Step 1 — Install Python

Python is the program that runs this app.

1. Go to **https://www.python.org/downloads/**
2. Click the big yellow **Download Python** button.
3. Open the file you downloaded and click **Install**.
   - On Windows, **check the box that says "Add Python to PATH"** before installing.

### Step 2 — Install ffmpeg

ffmpeg is a helper that reads the sound out of videos.

| Your computer | Type this in the Terminal |
| ------------- | ------------------------- |
| **Mac**       | `brew install ffmpeg`     |
| **Windows**   | `winget install ffmpeg`   |
| **Linux**     | `sudo apt install ffmpeg` |

> On a Mac, if `brew` doesn't work, install Homebrew first from **https://brew.sh**.

### Step 3 — Get the app ready

1. Download this project (green **Code** button → **Download ZIP**) and unzip it.
2. Open the **Terminal** app.
3. Go into the project folder. Type `cd ` (with a space), then drag the folder
   into the Terminal window and press **Enter**.
4. Copy and paste these lines, one at a time, pressing **Enter** after each:

**Mac / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows:**

```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

This makes a private workspace (`venv`) and installs everything the app needs.

> The very first time you make captions, it also downloads the Whisper "brain"
> (about 1.5 GB for the default model). This happens once, then it's saved.

✅ **You're done setting up!**

---

## How to start the app

### Mac — the easy way

**Double-click `run.command`.** That's it. A window opens with the app.

> First time only: if Mac says it can't open it, **right-click** `run.command`
> → **Open** → **Open**. You only do this once.

### Any computer — the manual way

In the Terminal, inside the project folder:

**Mac / Linux:**

```bash
source venv/bin/activate
python app.py
```

**Windows:**

```cmd
venv\Scripts\activate.bat
python app.py
```

---

## How to make captions

1. Click **Select video file** and choose your video.
2. The output folder fills in by itself (where your video is). Change it with
   **Browse** if you want.
3. Leave the two switches on (they're on by default):
   - **Create an MP3 first** — also saves the sound as an .mp3
   - **Save output in a new folder** — keeps things tidy in their own folder
4. Pick a **model** (bigger = better but slower) and a **language** (or leave blank).
5. Click **Generate Captions** and watch the bar fill up.
6. When it's done, you'll see the words and where your files were saved.

### Which model should I pick?

| Model      | Size  | Speed    | Notes          |
| ---------- | ----- | -------- | -------------- |
| `tiny`     | 39 MB | Fastest  | Quick drafts   |
| `base`     | 74 MB | Fast     | Okay quality   |
| `small`    | 244 MB| Medium   | Good quality   |
| `medium`   | 1.5 GB| Slower   | **Default**    |
| `large-v3` | 3 GB  | Slowest  | Best quality   |

---

## Command-line version (optional, for grown-ups)

You can also make captions without the window:

```bash
source venv/bin/activate
python3 generate_captions.py "path/to/video.mp4"
```

Handy options:

```bash
python3 generate_captions.py "video.mp4" --model large-v3 # best quality
python3 generate_captions.py "video.mp4" --language en    # force a language
```

---

## Help! Something went wrong

- **"No module named webview" (or whisper)** — you forgot to install the
  requirements. Run `pip install -r requirements.txt` after activating `venv`.
- **"ffmpeg not found"** — do Step 2 above.
- **The Mac won't open `run.command`** — right-click it → **Open** → **Open**.
- **It's slow** — that's normal for big models. Try the `tiny` or `base` model.
