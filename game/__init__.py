"""Love Quest: A Castle for Two - a small platformer with a Tkinter GUI.

Modules
-------
settings    all tunable constants and the colour palettes
entities    Entity base class + Player / Slime / Coin / MovingPlatform ...
levels      the level builder API and the three levels of the campaign
save_system JSON persistence, exception-safe loading and the leaderboard sort
art         procedural drawing helpers (no image files are needed)
app         the tkinter window, game loop, state machine and cutscenes
"""

__version__ = "1.0"
