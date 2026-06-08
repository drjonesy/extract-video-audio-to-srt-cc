#!/usr/bin/env bash
# Double-clickable launcher: activate the virtualenv and launch the app.
set -e

cd "$(dirname "$0")"
source venv/bin/activate
python app.py

# Close this Terminal window now that the app has exited.
osascript -e 'tell application "Terminal" to close (every window whose tty is "'"$(tty)"'")' &
exit 0
