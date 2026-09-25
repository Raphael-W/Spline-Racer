import pygame.mouse

class Camera:
    def __init__(self, x, y, zoom = 1, change_action = None):
        self.x = x
        self.y = y
        self.zoom = zoom

        self.max_zoom = 2.5
        self.min_zoom = 0.1

        self.change_action = change_action

    def trigger_change(self):
        if self.change_action is not None:
            self.change_action()

    def goto(self, x, y):
        self.x = x
        self.y = y

    def set_center(self, x, y):
        screen = pygame.display.get_surface()
        center_x = x - (screen.width / 2) / self.zoom
        center_y = y - (screen.height / 2) / self.zoom
        self.goto(center_x, center_y)

    def set_zoom(self, new_zoom):
        self.zoom = new_zoom

    def get_zoom(self):
        return self.zoom

    def get_pos(self):
        return self.x, self.y

    def zoom_to(self, new_zoom, point_x, point_y):
        clamped_zoom = max(min(new_zoom, self.max_zoom), self.min_zoom)

        new_x = self.x + point_x * (1 / self.zoom - 1 / clamped_zoom)
        new_y = self.y + point_y * (1 / self.zoom - 1 / clamped_zoom)

        self.goto(new_x, new_y)
        self.set_zoom(clamped_zoom)
        self.trigger_change()

    def pan_from_anchor(self, world_anchor):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        self.goto(world_anchor[0] - mouse_x / self.zoom, world_anchor[1] - mouse_y / self.zoom)

    def zoom_by(self, zoom_increment, point_x, point_y):
        self.zoom_to(self.zoom + zoom_increment, point_x, point_y)

    def world_to_screen(self, x, y):
        return (x - self.x) * self.zoom, (y - self.y) * self.zoom

    def screen_to_world(self, x, y):
        return (x / self.zoom) + self.x, (y / self.zoom) + self.y