from scenes.scene_manager import SceneManager
from scenes.track_editor import TrackEditor
#from scenes.track_racing import TrackRacing

import pygame_ui as ui
from core.utils import *
from config import *

from jsonschema import validate

from assets.themes.ui import theme

import pygame
import pygame.gfxdraw
import pygame.freetype

import platform
if platform.system() == "Windows":
    import ctypes
    appID = 'Raphael-W, Spline-Racer' # Arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appID) #Makes taskbar icon same as window icon (Sets app as "individual app", not linked to python)

# --- PYGAME INIT ---
pygame.init()
screen = pygame.display.set_mode(DEFAULT_WINDOW_SIZE, pygame.RESIZABLE, vsync=int(V_SYNC))
clock = pygame.time.Clock()

icon = pygame.image.load(asset_path("icons", "logo.png"))
pygame.display.set_icon(icon)

# --- UI INIT ---
ui_manager = ui.UI(screen, theme)
layer = ui.Layer(ui_manager)
fps_label = ui.Label(layer, "", (50, 30), "ne")

# --- SCENE INIT ---
trackEditorScene = TrackEditor(screen, ui_manager)
#trackRacingScene = TrackRacing(screen, trackEditorScene)

scene_changer = ui.Dropdown(layer, ["Track Editor", "Racing"], (30, 30), dimensions=(200, 25))

scene_manager = SceneManager()
scene_manager.add_scene(trackEditorScene)
#scene_manager.addScene(trackRacingScene)

scene_manager.set_scene(0)

running = True
while running:
    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.WINDOWRESIZED:
            layer.on_resize()

    fps_label.set_text(f"fps: {int(clock.get_fps())}")

    unused_events = ui_manager.handle_events(events)

    scene_manager.update()
    scene_manager.handle_events(unused_events)

    ui_manager.draw()

    pygame.display.flip()
    deltaTime = clock.tick(FPS) / 1000 #Refresh Rate

pygame.quit()
