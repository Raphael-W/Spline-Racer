import os

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

# Paths
DB_PATH = os.path.join(ROOT_PATH, "spline-racer.db")
ASSETS_DIR = os.path.join(ROOT_PATH, "assets")
TRACKS_DIR = os.path.join(ROOT_PATH, "tracks")
FONT_PATH = os.path.join(ASSETS_DIR, "fonts", "MonoFont.ttf")

# Repo
GITHUB_REPO_URL = "https://github.com/Raphael-W/Spline-Racer"

# Settings
FPS = 600000
V_SYNC = False
DEFAULT_WINDOW_SIZE = (1280, 720)