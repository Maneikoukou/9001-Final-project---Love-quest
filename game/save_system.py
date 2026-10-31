"""
Persistence layer
=================

The game keeps a small amount of data between sessions in ``save_data.json``
next to ``main.py``:

    {
      "best_times":  {"Sunlit Meadow": 42.5, ...},
      "total_tokens": 37,
      "finished": true,
      "leaderboard": [{"name": "...", "time": 120.4, "tokens": 37, "date": "..."}]
    }

Two things worth noting:

* **File I/O** - reading and writing JSON with the standard library.
* **Exception handling** - a missing, empty, or hand-edited save file must
  never crash the game, so every read is wrapped in ``try / except`` and
  falls back to sensible defaults.
* **Algorithms** - the leaderboard is ordered with a hand-written
  *insertion sort* (``sort_records``) rather than ``list.sort``.
"""

import json
import os
import time as _time

from .settings import LEADERBOARD_SIZE

# save_data.json lives in the project root (one level above this package)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(_ROOT, "save_data.json")


class SaveData:
    """Plain container for everything we persist."""

    def __init__(self):
        self.best_times = {}     # level name -> best seconds
        self.total_tokens = 0
        self.finished = False
        self.leaderboard = []    # list of record dicts, fastest first

    # -- helpers ----------------------------------------------------------
    def best_time(self, level_name):
        return self.best_times.get(level_name)

    def record_time(self, level_name, seconds):
        """Store ``seconds`` if it beats the previous best.  Returns True on a PB."""
        previous = self.best_times.get(level_name)
        if previous is None or seconds < previous:
            self.best_times[level_name] = round(seconds, 2)
            return True
        return False

    def to_dict(self):
        return {
            "best_times": self.best_times,
            "total_tokens": self.total_tokens,
            "finished": self.finished,
            "leaderboard": self.leaderboard,
        }

    @classmethod
    def from_dict(cls, raw):
        """Rebuild from JSON, ignoring anything that looks wrong."""
        data = cls()
        if not isinstance(raw, dict):
            return data

        times = raw.get("best_times", {})
        if isinstance(times, dict):
            for name, value in times.items():
                try:
                    data.best_times[str(name)] = float(value)
                except (TypeError, ValueError):
                    continue

        try:
            data.total_tokens = int(raw.get("total_tokens", 0))
        except (TypeError, ValueError):
            data.total_tokens = 0

        data.finished = bool(raw.get("finished", False))

        board = raw.get("leaderboard", [])
        if isinstance(board, list):
            for entry in board:
                if not isinstance(entry, dict):
                    continue
                try:
                    data.leaderboard.append({
                        "name": str(entry.get("name", "Player"))[:18],
                        "time": float(entry["time"]),
                        "tokens": int(entry.get("tokens", 0)),
                        "date": str(entry.get("date", "")),
                    })
                except (KeyError, TypeError, ValueError):
                    continue
        data.leaderboard = sort_records(data.leaderboard)[:LEADERBOARD_SIZE]
        return data


def sort_records(records):
    """Insertion sort by finishing time (fastest first).

    Implemented by hand on purpose: it shows a real algorithm rather than
    calling ``sorted()``.  Insertion sort is O(n^2) but the leaderboard is
    capped at five rows, so that is completely fine here.
    """
    items = list(records)
    for i in range(1, len(items)):
        current = items[i]
        j = i - 1
        while j >= 0 and items[j]["time"] > current["time"]:
            items[j + 1] = items[j]
            j -= 1
        items[j + 1] = current
    return items


class SaveSystem:
    """Load / save :class:`SaveData` with defensive error handling."""

    @staticmethod
    def load(path=DATA_FILE):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            return SaveData.from_dict(raw)
        except FileNotFoundError:
            return SaveData()                     # first run - perfectly normal
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            # Corrupted or unreadable file: keep playing with a clean slate
            # rather than crashing on a bad save file.
            return SaveData()

    @staticmethod
    def save(data, path=DATA_FILE):
        """Write atomically so a crash mid-write cannot corrupt the save."""
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(data.to_dict(), handle, indent=2)
            os.replace(tmp, path)
            return True
        except OSError:
            return False

    @staticmethod
    def add_score(data, name, seconds, tokens, path=DATA_FILE):
        """Push a finished run onto the leaderboard and persist it."""
        data.leaderboard.append({
            "name": name,
            "time": round(seconds, 2),
            "tokens": tokens,
            "date": _time.strftime("%Y-%m-%d"),
        })
        data.leaderboard = sort_records(data.leaderboard)[:LEADERBOARD_SIZE]
        SaveSystem.save(data, path)
        return data.leaderboard


def format_time(seconds):
    """``83.4`` -> ``"1:23"``."""
    if seconds is None:
        return "--:--"
    total = int(round(seconds))
    return f"{total // 60}:{total % 60:02d}"
