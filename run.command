#!/usr/bin/env bash
#
# Double-click launcher for the Caption Generator.
# Activates the existing venv and runs the app. Closes the Terminal on exit.
#
cd "$(dirname "$0")"

source venv/bin/activate
python app.py

# App closed — close this Terminal window (macOS).
# Detach the close so the shell exits first; avoids the
# "terminate running processes" prompt.
if command -v osascript >/dev/null 2>&1; then
  MY_TTY="$(tty)"
  ( osascript - "$MY_TTY" >/dev/null 2>&1 <<'EOF'
on run argv
  set myTTY to item 1 of argv
  tell application "Terminal"
    repeat with w in windows
      repeat with t in tabs of w
        if tty of t is myTTY then close w saving no
      end repeat
    end repeat
  end tell
end run
EOF
  ) &
  disown
fi
exit 0
