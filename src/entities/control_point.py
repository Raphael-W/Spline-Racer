import pygame
from pygame import gfxdraw

from core.utils import mult_color
from entities.camera import Camera

class ControlPoint:
    def __init__(self, x, y, camera = None, start_selected = True):
        self.x = x
        self.y = y

        self.base_size = 10
        self.size = self.base_size

        self.camera = camera

        self.selected = start_selected
        self.mouse_hovering = False

        self.pos_at_click = (x, y)
        self.pos_at_release = None

        self.move_callback = None

    #Returns the control point's pos in format [x, y]
    def get_pos(self):
        return self.x, self.y

    def get_size(self):
        return self.size

    #Move a control point to a specific location
    def move(self, newPos):
        self.x = newPos[0]
        self.y = newPos[1]

    def handle_mouse_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.selected and self.mouse_hovering:
                self.selected = True
            self.pos_at_click = self.get_pos()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.selected:
                self.pos_at_release = self.get_pos()
                if self.move_callback is not None:
                    self.move_callback(self, self.pos_at_click, self.pos_at_release)
                    self.pos_at_click = None
                    self.pos_at_release = None

            self.selected = False

    def __repr__(self):
        return str((self.x, self.y))

    def set_move_callback(self, func):
        self.move_callback = func

    #Calculates whether mouse is hovering, and whether user has selected point
    def update(self):
        world_mouse_x, world_mouse_y = self.camera.screen_to_world(*pygame.mouse.get_pos())
        screen_x, screen_y = self.camera.world_to_screen(self.x, self.y)
        hover_radius = self.size + 2

        self.mouse_hovering = ((self.x - hover_radius <= world_mouse_x <= self.x + hover_radius) and
                               (self.y - hover_radius <= world_mouse_y <= self.y + hover_radius))

        self.size = self.base_size
        if self.mouse_hovering:
            self.size = self.base_size + 2

        #Ensures control point can't go off the screen
        if self.selected:
            screen = pygame.display.get_surface()
            if self.size <= screen_x <= (screen.width - self.size):
                self.x = world_mouse_x

            if self.size <= screen_y <= (screen.height - self.size):
                self.y = world_mouse_y

    #Draws point to screen
    def draw(self, surface, color):
        screen_pos = self.camera.world_to_screen(self.x, self.y)
        pygame.gfxdraw.aacircle(surface, int(screen_pos[0]), int(screen_pos[1]), self.size, color)
        pygame.gfxdraw.filled_circle(surface, int(screen_pos[0]), int(screen_pos[1]), self.size, color)
