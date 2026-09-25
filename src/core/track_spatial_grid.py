from core.utils import lineToPointDistance

class TrackSpatialGrid:
    def __init__(self, points = [], grid_size=100):
        self.grid_size = grid_size
        self.points = points

        self.grid = {}
        self._create_grid()

    def _cell_from_point(self, point):
        x, y = point
        return int(x // self.grid_size), int(y // self.grid_size)

    def _cells_from_line(self, a, b):
        x0, y0 = a
        x1, y1 = b

        ix0, iy0 = int(x0 // self.grid_size), int(y0 // self.grid_size)
        ix1, iy1 = int(x1 // self.grid_size), int(y1 // self.grid_size)

        dx = x1 - x0
        dy = y1 - y0

        step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
        step_y = 0 if dy == 0 else (1 if dy > 0 else -1)

        # how far (in t) you travel to cross one cell boundary in x / y
        t_delta_x = abs(self.grid_size / dx) if dx != 0 else float('inf')
        t_delta_y = abs(self.grid_size / dy) if dy != 0 else float('inf')

        # t value of first crossing
        next_x_boundary = (ix0 + (1 if step_x > 0 else 0)) * self.grid_size
        next_y_boundary = (iy0 + (1 if step_y > 0 else 0)) * self.grid_size
        t_max_x = abs((next_x_boundary - x0) / dx) if dx != 0 else float('inf')
        t_max_y = abs((next_y_boundary - y0) / dy) if dy != 0 else float('inf')

        cx, cy = ix0, iy0
        cells = [(cx, cy)]

        while (cx, cy) != (ix1, iy1):
            if t_max_x < t_max_y:
                t_max_x += t_delta_x
                cx += step_x
            else:
                t_max_y += t_delta_y
                cy += step_y
            cells.append((cx, cy))

        return cells

    def _add_line(self, a, b, segment):
        cells = self._cells_from_line(a, b)
        for cell in cells:
            self.grid.setdefault(cell, set()).add(segment)

    def _create_grid(self):
        for index, segment in enumerate(self.points):
            for point_index in range(len(segment) - 1):
                self._add_line(segment[point_index], segment[point_index + 1], index)

    def _get_ring_cells(self, cell, ring):
        if ring == 0: return [cell]

        x, y = cell
        side_range = range(-ring, ring + 1)
        n = [(x + i, y + ring) for i in side_range]
        e = [(x + ring, y + i) for i in side_range]
        s = [(x + i, y - ring) for i in side_range]
        w = [(x - ring, y + i) for i in side_range]

        return n + e + s + w

    def _distance_to_segment(self, point, segment_index):
        seg = self.points[segment_index]
        distance = float('inf')
        for i in range(len(seg) - 1):
            if (check := lineToPointDistance(seg[i], seg[i + 1], point)[0]) < distance:
                distance = check
        return distance

    def query(self, point, threshold):
        point_cell = self._cell_from_point(point)

        ring = 0
        while ring <= 2:
            closest_segment = None
            closest_segment_distance = float('inf')
            for cell in self._get_ring_cells(point_cell, ring):
                segments = self.grid.get(cell, set())
                for seg in segments:
                    if (check := self._distance_to_segment(point, seg)) < closest_segment_distance:
                        closest_segment = seg
                        closest_segment_distance = check

            if closest_segment_distance < threshold:
                return closest_segment

            ring += 1
        return None

    # Return tuple(x_min, x_max), tuple(y_min, y_max)
    def query_bound_coords(self):
        grid_keys = list(self.grid.keys())
        grid_keys_x = [i[0] for i in grid_keys]
        grid_keys_y = [i[1] for i in grid_keys]

        min_x = min(grid_keys_x) * self.grid_size
        max_x = (max(grid_keys_x) + 1) * self.grid_size

        min_y = min(grid_keys_y) * self.grid_size
        max_y = (max(grid_keys_y) + 1) * self.grid_size

        return (min_x, max_x), (min_y, max_y)
