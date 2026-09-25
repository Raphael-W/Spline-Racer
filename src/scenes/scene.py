import pygame

class Scene:
    def __init__(self, screen, ui_manager, scene_name = "Scene"):
        self.scene_name = scene_name
        self.screen = screen
        self.ui_manager = ui_manager

    def update(self):
        pass

    def handle_mouse_event(self, event):
        pass

    def handle_keyboard_event(self, event):
        pass