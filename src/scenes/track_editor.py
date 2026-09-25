import pygame_ui as ui
from pygame_ui import Column

from core.update_checker import *
from entities.track import Track
from scenes.scene import Scene
from entities.camera import Camera
from entities.control_point import ControlPoint
from core.utils import *
from core.history import History

import json
import sqlite3

from jsonschema import validate

import pygame
import pygame.gfxdraw

import os
import webbrowser
import base64
import copy

import PIL.Image
from io import BytesIO

import platform
if platform.system() == "Windows":
    from tkinter.filedialog import askopenfilename
    import tkinter as tk
elif platform.system() == "Darwin":
    import Cocoa

class TrackEditor(Scene):
    def __init__(self, screen, ui_manager):
        super().__init__(screen, ui_manager, "Track Editor")

        self.running = True

        self.camera = Camera(0, 0)
        self.track = Track(screen, self.camera)
        self.track.set_action_performed_callback(self.save_track_snapshot)
        self.history = History()
        self.track_path = None

        self.layer = ui.Layer(self.ui_manager)

        self.pivotPos = None

        self.viewMode = "track"

        self.screenWidth = self.previousScreenWidth = self.screen.get_size()[0]
        self.screenHeight = self.previousScreenHeight = self.screen.get_size()[1]

        self.userSettingScale = False
        self.setScalePoint1 = None
        self.setScalePoint2 = None

        self.userSettingFinish = False
        self.finishIndex = None
        self.finishDir = None

        self.saveDirectory = None
        self.closeCount = 0
        self.newCaption = None
        self.lastCaption = None

        self.referenceImage = None
        self.referenceImageScale = 1
        self.referenceImageRect = None
        self.scaledReferenceImage = None
        self.referenceImageVisibility = True

        self.events = []
        self.UIClick = False

        self.checkedForUpdates = False
        self.updateNeeded = False
        self.latestCommitSHA = None

        self._movement_anchor = None

        # ------------ CONSTANTS ------------
        self.screenBorder = 5

        self.zoom_increment = 0.05

        self.colours = {"background"       : (20, 20, 20),
                        "curve"            : (128, 128, 128),
                        "controlPoint"     : (24, 150, 204),
                        "frontControlPoint": (204, 138, 24),
                        "grid"             : (27, 27, 27),
                        "white"            : (200, 200, 200),
                        "track"            : (100, 100, 100)}

        # ------------ UI SETUP ------------
        with ui.Column(self.layer, offset=(50, 50)) as col:
            self.mouse_x_label = ui.Label(col, "", stick="ne")
            self.mouse_y_label = ui.Label(col, "", stick="ne")
            self.zoom_label = ui.Label(col, "", stick="ne")

        self.config_accordion = ui.Accordion(self.layer, "Untitled Track", offset=(50, 50))

        with ui.Column(self.config_accordion, offset = (0, 50)) as col:
            with ui.Row(col) as row:
                ui.TextButton(row, "Save", dimensions=(125, None), action=self.save_track)
                ui.TextButton(row, "Save As", dimensions=(125, None), action=lambda: ui.FileSaver(row, TRACKS_DIR, "track", self.save_track_action))

            with ui.Row(col) as row:
                ui.TextButton(row, "Open", dimensions=(125, None), action=lambda: ui.FilePicker(row, "Tracks", TRACKS_DIR, "track", self.open_track))
                ui.TextButton(row, "New", dimensions=(125, None), action=self.new_track)

            with ui.Row(col) as row:
                set_finish = ui.Button(row, dimensions = (80, 60))
                image_col = ui.Column(set_finish, stick="nesw")
                ui.Image(image_col, asset_path("icons", "flag.png"), stick="ew", tag="icon")
                ui.Label(image_col, "Set Finish", stick="ew", tag="icon_subtitle")
                set_finish.set_content_element(image_col)

                set_scale = ui.Button(row, dimensions = (80, 60))
                image_col = ui.Column(set_scale, stick = "nesw")
                ui.Image(image_col, asset_path("icons", "scale.png"), stick = "ew", tag = "icon")
                ui.Label(image_col, "Scale Track", stick = "ew", tag = "icon_subtitle")
                set_scale.set_content_element(image_col)

                recenter = ui.Button(row, dimensions = (80, 60))
                image_col = ui.Column(recenter, stick = "nesw")
                ui.Image(image_col, asset_path("icons", "aim.png"), stick = "ew", tag = "icon")
                ui.Label(image_col, "Recenter", stick = "ew", tag = "icon_subtitle")
                recenter.set_content_element(image_col)

            with ui.Row(col) as row:
                ui.TextButton(row, "Set Reference Image", dimensions=(180, 30), styling={"font_size": 12})
                ui.ImageButton(row, asset_path("icons", "hide.png"), dimensions=(30, 30), disabled=False, hover_hint = "Hide the reference image")
                ui.ImageButton(row, asset_path("icons", "bin.png"), dimensions=(30, 30), disabled=False, hover_hint = "Delete the reference image")

            with ui.Row(col, offset=(0, 10)) as row:
                ui.Label(row, "View Mode", stick="ns")
                ui.Dropdown(row, ["Track", "Skeleton", "Curve", "Spline Dots"], dimensions=(150, 25), stick="ns")

            with ui.Row(col, offset=(0, 10)) as row:
                ui.Label(row, "Width", stick="ns")
                ui.Slider(row, (10, 30), bar_dimensions=(100, 6), value=self.track.width, suffix="m", action=self.track.change_width, finished_action=self.save_track_snapshot, stick="ns")

            with ui.Row(col, offset=(0, 20)) as row:
                ui.ImageButton(row, asset_path("icons", "undo.png"), dimensions=(30, 30), action=self.undo)
                ui.ImageButton(row, asset_path("icons", "redo.png"), dimensions=(30, 30), action=self.redo)

        self.trackScaleLabel = ui.Label(self.layer, "", (180, 30), "sw")

    def get_screen(self):
        return pygame.display.get_surface()

    def show_help(self):
        message = ["Click to add a point to the end of the track",
                   "Clicking on the track will insert a point at that location",
                   "Right-click on a point to remove it",
                   "Drag control_points to reposition them as needed",
                   "",
                   'Hold shift to add to point to start of track instead of the end',
                   '"Auto Res" selects the best resolution for the track',
                   '"Racing Line" displays the fastest path around the track',
                   'Select "Set Finish" to place the finish line',
                   '"Set Scale" scales the track using a real-world distance']
        Message(self.ui_layer, "Help", message, message_font_size = 13)

    def save_track_snapshot(self):
        self.history.save_snapshot(copy.deepcopy(self.track))

    def restore_track_snapshot(self, snapshot):
        self.track = snapshot
        self.track.update()

    #Handles undoing of track actions (control point moving, width changes etc.)
    def undo(self):
        snapshot = self.history.undo()
        if snapshot is not None:
            self.restore_track_snapshot(snapshot)

    #Handles redoing of previously undone actions
    def redo(self):
        snapshot = self.history.redo()
        if snapshot is not None:
            self.restore_track_snapshot(snapshot)

    def save_track(self):
        if self.track_path is None:
            FileSaver(self.ui_layer, TRACKS_DIR, "track", self.save_track_action)
        else:
            self.save_track_action(self.track_path)

    def save_track_action(self, save_path):
        track_save_state = self.track.get_save_state()
        try:
            with open(save_path, 'w', encoding = 'utf-8') as f:
                json.dump(track_save_state, f, ensure_ascii = False, indent = 4)
        except:
            Message(self.ui_layer, "Couldn't Save Track", "An error occurred while trying to save the track", ("Okay", None))

        self.track_path = save_path

    def open_track(self, track_path):
        track_name = Path(track_path).stem
        loading_modal = LabelModal(self.ui_layer, f"Opening {track_name}...")

        #This combo works but the file opening is still visible
        self.ui_layer.draw()
        pygame.display.flip()

        with open(track_path, 'r', encoding = 'utf-8') as f:
            track_data = json.load(f)

        self.track = Track(self.screen, self.camera, track_data["points"], track_data["properties"]["width"])
        self.track_path = track_path
        loading_modal.close()
        self.center_track()

        # loading_modal.close()
        # Message(self.ui_layer, "Couldn't Open Track", "An error occurred while trying to open the track", ("Okay", None))

    def new_track(self):
        self.track = Track(self.screen, self.camera)
        self.track_path = None

    def center_track(self):
        track_bounds_x, track_bounds_y = self.track.get_track_bounds()
        screen = pygame.display.get_surface()
        padding = 0.85

        track_w = track_bounds_x[1] - track_bounds_x[0]
        track_h = track_bounds_y[1] - track_bounds_y[0]

        zoom = min(screen.width / track_w * padding, screen.height / track_h * padding, self.camera.max_zoom)
        zoom = max(zoom, self.camera.min_zoom)

        self.camera.set_zoom(zoom)
        self.camera.set_center(mean(*track_bounds_x), mean(*track_bounds_y))

    #Algorithm to draw make background a grid
    def draw_grid(self, world_spacing, line_width, color):
        zoom = self.camera.get_zoom()
        cam_x, cam_y = self.camera.get_pos()
        screen = self.get_screen()

        start_col = int(cam_x // world_spacing)
        end_col = int((cam_x + screen.width / zoom) // world_spacing) + 1
        start_row = int(cam_y // world_spacing)
        end_row = int((cam_y + screen.height / zoom) // world_spacing) + 1

        for col in range(start_col, end_col + 1):
            x = (col * world_spacing - cam_x) * zoom
            pygame.draw.line(self.screen, color, (x, 0), (x, screen.height), line_width)

        for row in range(start_row, end_row + 1):
            y = (row * world_spacing - cam_y) * zoom
            pygame.draw.line(self.screen, color, (0, y), (screen.width, y), line_width)

    def handle_mouse_event(self, event):
        self.track.handle_mouse_event(event)
        mods = pygame.key.get_mods()

        # Left-click down
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if mods & pygame.KMOD_CTRL:
                self._movement_anchor = self.camera.screen_to_world(*pygame.mouse.get_pos())
            else:
                if self.track.control_point_hovering() is None:
                    insertion_index = -1
                    if (seg := self.track.hovering_segment()) is not None:
                        insertion_index = seg + 1
                    self.track.add(self.camera.screen_to_world(*pygame.mouse.get_pos()), insertion_index)

        # Left-click up
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._movement_anchor = None

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if (hovering_point := self.track.control_point_hovering()) is not None:
                if not(self.track.closed and hovering_point in (0, len(self.track.control_points) - 1)):
                    self.track.remove(hovering_point)

        # Scrolling
        elif event.type == pygame.MOUSEWHEEL:
            self.camera.zoom_by(self.zoom_increment * event.y, *pygame.mouse.get_pos())

    def update(self):
        # === PAN AND ZOOM ===
        if self._movement_anchor is not None:
            self.camera.pan_from_anchor(self._movement_anchor)

        # === DRAWING ===
        self.screen.fill((20, 20, 20))
        self.draw_grid(50, 1, (27, 27, 27))
        self.track.update()
        self.track.draw(self.get_screen(), "edit")