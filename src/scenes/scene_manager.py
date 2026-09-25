import pygame

class SceneManager:
    def __init__(self, *scenes):
        self.scenes = list(scenes)
        self.currentScene = 0

    def add_scene(self, scene):
        self.scenes.append(scene)

    def set_scene(self, scene):
        # if self.currentScene == 1 and not self.scenes[1].pause:
        #     self.scenes[1].setPause()
        # elif self.currentScene == 0 and self.scenes[1].pause and not self.scenes[1].userPaused:
        #     self.scenes[1].setPause()

        self.currentScene = scene

    def get_scene_index(self, name):
        return self.getSceneNames().index(name)

    def get_scene(self, name=None):
        if name is None:
            return self.scenes[self.currentScene]
        return self.scenes[self.get_scene_index(name)]

    def handle_events(self, events):
        mouse_events = [e for e in events if e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL)]
        keyboard_events = [e for e in events if e.type in (pygame.KEYDOWN, pygame.KEYUP, pygame.TEXTINPUT)]

        self.handle_keyboard_events(keyboard_events)
        self.handle_mouse_events(mouse_events)

    def handle_keyboard_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    nextScene = (self.currentScene + 1) % len(self.scenes)
                    self.set_scene(nextScene)
            self.get_scene().handle_keyboard_event(event)

    def handle_mouse_events(self, events):
        for event in events:
            self.get_scene().handle_mouse_event(event)

    def on_quit(self):
        trackEditorSceneIndex = self.get_scene_index("Track Editor")
        if not self.scenes[trackEditorSceneIndex].track.isSaved():
            self.set_scene(0)


    def update(self):
        #Updates just the visible scene, each scene "pauses" when not visible
        if len(self.scenes) > 0:
            self.get_scene().update()

    def getSceneNames(self):
        return [scene.name for scene in self.scenes]