#!/bin/sh
# Love Quest: A Castle for Two
# Double-click this file to play. Uses a Tkinter GUI.
# Run it in a graphical desktop session.
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    exec python3 main.py
elif command -v python >/dev/null 2>&1; then
    exec python main.py
else
    echo "Python 3 was not found on this machine."
    echo "Install it from https://www.python.org/downloads/ and try again."
    read -r _
fi
