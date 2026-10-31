#!/usr/bin/env python3
"""
Love Quest: A Castle for Two
============================

COMP9001 final project - a side-scrolling platformer written with the Python
standard library. Tkinter draws the GUI.

How to run
----------
    python3 main.py

Requires Python 3.8 or newer.  No pip installs, no image files, no sound
files - everything is drawn with canvas primitives.

Controls
--------
    Arrow keys / A D     move
    Space / W / Up       jump  (hold for a higher jump)
    Esc                  pause
    R                    retry after losing all hearts
    Enter                confirm / advance

Personalise it
--------------
Open ``game/settings.py`` and change PLAYER_NAME, PARTNER_NAME and STORY.
"""

import os
import sys

# Make sure the "game" package is importable no matter which folder
# the file is run from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    try:
        import tkinter as tk
    except ImportError:                                   # pragma: no cover
        print("This game needs tkinter for its GUI.\n"
              "On Linux you may need:  sudo apt install python3-tk")
        return 1

    from game.app import LoveQuestApp

    root = tk.Tk()
    try:
        root.iconname("Love Quest")
    except Exception:
        pass

    smoke = "--smoke" in argv
    app = LoveQuestApp(root, smoke=smoke)

    if smoke:
        app.smoke_test()
        return 0

    # Bring the window to the front on launch (macOS likes to open new Tk
    # windows behind whatever is already focused).
    try:
        root.update_idletasks()
        root.lift()
        root.focus_force()
    except Exception:
        pass

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
