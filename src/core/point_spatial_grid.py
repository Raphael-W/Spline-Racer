from core.utils import point_distance
class PointSpatialGrid:
    def __init__(self, points = [], grid_size=100):
        self.grid_size = grid_size
        self.points = points

        self.grid = {}
        self._create_grid()

    def _cell_from_point(self, point):
        x, y = point
        return int(x // self.grid_size), int(y // self.grid_size)

    def _add_point(self, coord, index):
        cell = self._cell_from_point(coord)
        self.grid.setdefault(cell, set()).add(index)

    def _create_grid(self):
        for index, coord in enumerate(self.points):
            self._add_point(coord, index)

    def _get_ring_cells(self, cell, ring):
        if ring == 0: return [cell]

        x, y = cell
        side_range = range(-ring, ring + 1)
        n = [(x + i, y + ring) for i in side_range]
        e = [(x + ring, y + i) for i in side_range]
        s = [(x + i, y - ring) for i in side_range]
        w = [(x - ring, y + i) for i in side_range]

        return n + e + s + w

    def _distance_to_point(self, point, point_index):
        return point_distance(self.points[point_index], point)

    def query(self, point, exclude_indexes = []):
        point_cell = self._cell_from_point(point)

        ring = 0
        while ring <= 3:
            closest_index = None
            closest_point_distance = float('inf')

            for cell in self._get_ring_cells(point_cell, ring):
                points = self.grid.get(cell, set())
                for seg in points:
                    excluded = seg in exclude_indexes
                    if (not excluded) and ((check := self._distance_to_point(point, seg)) < closest_point_distance):
                        closest_index = seg
                        closest_point_distance = check

            if closest_index is not None:
                return closest_point_distance, closest_index

            ring += 1
        return None
