from entities.camera import Camera

class TrackLine:
    def __init__(self, camera):
        self.points = []
        self.screen_points = []
        self.resolution = 20
        self.camera = camera

        self.old_camera_pos = self.camera.get_pos()
        self.old_camera_zoom = self.camera.get_zoom()

    def insert(self, index, segment):
        self.points.insert(index, segment)
        self.screen_points.insert(index, self.__world_to_screen_segment(segment))

    def pop(self, index):
        self.points.pop(index)
        self.screen_points.pop(index)

    def replace(self, index, segment):
        self.points[index] = segment
        self.screen_points[index] = self.__world_to_screen_segment(segment)

    def reset(self):
        self.points = []
        self.screen_points = []

    def get(self, index):
        return self.points[index]

    def __getitem__(self, index):
        return self.get(index)

    def coord_from_t(self, t: float):
        flat_index = int(t * self.resolution)
        segment_index = int(t)
        return self.points[segment_index][flat_index % segment_index]

    def flat_to_2d(self, index):
        segment = index // self.resolution
        index_in_segment = index % segment

        return segment, index_in_segment

    def update_resolution(self, new_res):
        self.resolution = new_res

    def flatten_points(self):
        flat_list = []
        for segment in self.points:
            flat_list += segment
        return flat_list

    def flatten_screen_points(self):
        flat_list = []
        for segment in self.screen_points:
            flat_list += segment
        return flat_list

    def __world_to_screen_segment(self, segment):
        offset_segment = []
        for point in segment:
            offset_segment.append(self.camera.world_to_screen(point[0], point[1]))
        return offset_segment

    def get_screen(self, flatten = False):
        if flatten:
            return self.flatten_screen_points()
        return self.screen_points

    def get_points(self, flatten = False):
        if flatten:
            return self.flatten_points()
        return self.points

    def __len__(self):
        return len(self.points)

    def recalculate_screen(self):
        new_screen = []
        for segment in self.points:
            new_screen.append(self.__world_to_screen_segment(segment))
        self.screen_points = new_screen

    def update(self):
        pos_changed = self.old_camera_pos != self.camera.get_pos()
        zoom_changed = self.old_camera_zoom != self.camera.get_zoom()
        if pos_changed or zoom_changed:
            self.recalculate_screen()