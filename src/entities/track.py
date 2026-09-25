import core.utils as u
from core.history import *
from core.track_spatial_grid import TrackSpatialGrid
from core.point_spatial_grid import PointSpatialGrid
from entities.camera import Camera
from entities.control_point import ControlPoint
from entities.track_line import TrackLine

import pygame
import pygame.gfxdraw

import base64
import uuid
import json
from hashlib import sha256
import math

class Track:
    def __init__(self, screen, camera, points = None, width = 12):
        self.screen = screen
        self.camera = camera

        self.control_points: list[ControlPoint] = []
        self.spline = TrackLine(camera)
        self.normals = []
        self.track_lines = {"curve_left": TrackLine(camera),
                            "curve_right": TrackLine(camera),
                            "inner_edge_left": TrackLine(camera),
                            "inner_edge_right": TrackLine(camera),
                            "outer_edge_left": TrackLine(camera),
                            "outer_edge_right": TrackLine(camera)}

        self.spline_spatial_grid = TrackSpatialGrid()
        self.control_point_spatial_grid = PointSpatialGrid()

        self.UUID = str(uuid.uuid1())

        self.closed = False
        self.resolution = 20
        self.scale = 0.2
        self.width = width
        self.length = 0

        self.action_performed_callback = None

        self.point_index_selected = None

        self.finishIndex = None
        self.finishDir = True

        self.referenceImageDir = None

        self.colours = {"curve"            : (128, 128, 128),
                        "edge"             : (200, 200, 200),
                        "track"            : (100, 100, 100),
                        "control"          : (24, 150, 204),
                        "front_control"    : (204, 138, 24)}

        self.edit = True
        self.switch_front = False

        if points is not None:
            for point in points:
                self.add(point, update = False)
            self.compute_track()
            self.update_positional_caches()

    def set_action_performed_callback(self, action):
        self.action_performed_callback = action

    def action_performed(self):
        if self.action_performed_callback is not None:
            self.action_performed_callback()

    def control_point_hovering(self):
        nearest_point = self.control_point_spatial_grid.query(pygame.mouse.get_pos())
        if nearest_point is not None:
            if self.control_points[nearest_point[1]].mouse_hovering:
                return nearest_point[1]
        return None

    #Collects relevant data about track and combines it into a dictionary used for saving
    def get_save_state(self):
        reference_image_data = None
        if self.referenceImageDir is not None:
            with open(self.referenceImageDir, "rb") as img_file:
                reference_image_data = base64.b64encode(img_file.read()).decode('utf-8')

        points = self.control_point_coords()
        properties = {"width"      : self.width,
                      "finishIndex": self.finishIndex,
                      "finishDir"  : self.finishDir,
                      "referenceImage": reference_image_data}

        return {"points"           : points,
                "UUID"             : self.UUID,
                "properties"       : properties}

    #Used to check whether the track has been changed
    def getUniquenessToken(self):
        data = {
            "points": self.control_point_coords(),
            "width": self.width,
            "finish": self.getStartPos()
        }

        encoded = json.dumps(data, sort_keys = True).encode()
        return sha256(encoded).hexdigest()

    #Returns coordinates of start line
    def getStartPos(self):
        if self.finishIndex is None:
            finishIndex = 5 / self.resolution
            finishDir = True
        else:
            finishIndex = self.finishIndex
            finishDir = self.finishDir

        finishCoord = self.spline.coord_from_t(finishIndex)
        finishNeighbourCoord = self.spline.coord_from_t(finishIndex + (1 / self.resolution)) # next one

        trackAngle = 0 + math.degrees(math.atan2(finishCoord[0] - finishNeighbourCoord[0], (finishCoord[1] - finishNeighbourCoord[1]))) - 90
        startAngle = trackAngle + (finishDir * 180)

        return finishCoord, startAngle, int(finishIndex * self.resolution), finishDir

    def change_width(self, value):
        self.width = value
        self.compute_track_lines()

    #Calculates length of track by adding length of each segment
    def calculateLength(self):
        if self.scale is not None:
            flat_points = self.spline.flatten_points()
            self.length = 0

            for point in range(len(flat_points) - 1):
                self.length += u.point_distance(flat_points[point], flat_points[point + 1]) * self.scale

    #Multiplies each point by scale factor
    def scalePoints(self, scale):
        for point in self.control_points:
            newPosition = (point.x * scale, point.y * scale)
            point.move(newPosition)
        self.compute_track()

    #Called when track is closed/unclosed
    def updateCloseStatus(self, value, update = False):
        if self.closed is not value:
            self.closed = value
            if update:
                self.compute_track(updatePoints = [0])

    def hovering_segment(self):
        if self.spline_spatial_grid is None:
            return None
        world_mouse = self.camera.screen_to_world(*pygame.mouse.get_pos())
        return self.spline_spatial_grid.query(world_mouse, 15)

    def get_track_bounds(self):
        if self.spline_spatial_grid is None:
            return (0, 0), (0, 0)
        return self.spline_spatial_grid.query_bound_coords()

    #Adds new control point
    def add(self, pos, index = -1, update = True, user_performed = True):
        control_point = ControlPoint(*pos, self.camera, start_selected = user_performed)
        if index == -1:
            index = len(self.control_points)

        self.control_points.insert(index, control_point)
        control_point.set_move_callback(self.control_point_move_callback)

        if user_performed:
            self.action_performed()
            self.calculateLength()

        if len(self.control_points) > 1:
            if (self.finishIndex is not None) and (index <= self.finishIndex):
                self.finishIndex += 1

            self.spline.insert(index - 1, [])
            self.normals.insert(index - 1, [])
            for line_name, line in self.track_lines.items():
                line.insert(index - 1, [])

        if update:
            self.compute_track(update_index = index)

        return control_point

    #Removes control point at index specified
    def remove(self, index, update = True, userPerformed = False):
        if len(self.control_points) >= index - 1:
            removedPoint = self.control_points.pop(index)

            if userPerformed:
                self.action_performed()
                self.calculateLength()

            if self.finishIndex is not None:
                if index <= self.finishIndex:
                    self.finishIndex -= 1

            if len(self.control_points) > 0:
                self.spline.pop(index - 1)
                self.normals.pop(index - 1)
                for line_name, line in self.track_lines.items():
                    line.pop(index - 1)

            if update:
                self.update_positional_caches()
                self.compute_track(update_index = None)

    def control_point_move_callback(self, point, pos_at_click, pos_at_release):
        self.update_positional_caches()

        if pos_at_click != pos_at_release:
            self.action_performed()
        self.calculateLength()

    def update_positional_caches(self):
        self.spline_spatial_grid = TrackSpatialGrid(self.spline.points)
        self.control_point_spatial_grid = PointSpatialGrid(self.control_point_coords())

    #Returns a list of the control point coords
    def control_point_coords(self):
        return [p.get_pos() for p in self.control_points]

    def extended_control_points(self):
        p = self.control_points

        if self.closed:
            trimmed_p = p[:-1]
            return trimmed_p[-2:] + trimmed_p + trimmed_p[:2], 1

        else:
            front = ControlPoint(*u.get_mirrored_point(p[1].get_pos(), p[0].get_pos()))
            back = ControlPoint(*u.get_mirrored_point(p[-2].get_pos(), p[-1].get_pos()))
            return [front] + p + [back], 0


    #Main mathematical formula for track curve
    def calculate_spline(self, t):
        extended_control_points, extend_offset = self.extended_control_points()

        #Interpolate curve using Catmull Rom
        def interpolate(P0: ControlPoint, P1: ControlPoint, P2: ControlPoint, P3: ControlPoint, T: float):
            p0 = pygame.math.Vector2(P0.get_pos())
            p1 = pygame.math.Vector2(P1.get_pos())
            p2 = pygame.math.Vector2(P2.get_pos())
            p3 = pygame.math.Vector2(P3.get_pos())

            point = (
                T * ((2 - T) * T - 1) * p0
                + (T * T * (3 * T - 5) + 2) * p1
                + T * ((4 - 3 * T) * T + 1) * p2
                + (T - 1) * T * T * p3) / 2

            return point

        num_segments = len(self.control_points) - 1
        segment = min(int(t), num_segments - 1)
        t = t - segment
        return interpolate(*extended_control_points[segment + extend_offset:segment + extend_offset + 4], t)

    def get_scaled_width(self):
        return self.width / self.scale

    def get_point_range(self, from_i, to_i):
        segment_count = len(self.control_points) - 1
        if not self.closed:
            from_i = max(from_i, 0)
            to_i = min(to_i, segment_count)

        return [i % segment_count for i in range(from_i, to_i)]

    #Computes the points that make up the track spline.
    def compute_track(self, update_index=None):
        if len(self.control_points) >= 2:
            update_segments = list(range(len(self.spline)))

            if (update_index is not None) and (len(self.control_points) >= 4):
                update_segments = self.get_point_range(update_index - 2, update_index + 2)

            for segment_index in update_segments:
                # Spline computation
                segment_resolution = self.calculate_resolution(segment_index)
                spline_segment = []
                t_list = []
                for tInt in range(segment_resolution):
                    # Using (res - 1) ensures last point is 1 (res/res)
                    t = segment_index + (tInt / (segment_resolution - 1))
                    t_list.append(t)
                    spline_segment.append(self.calculate_spline(t))
                self.spline.replace(segment_index, list(spline_segment))

                # Normals computation (require index + 1, so extra point is added to segment)
                normals_segment = []
                spline_segment.append(self.calculate_spline((segment_index + 1) + (1 / segment_resolution)))
                for point in range(segment_resolution):
                    normals_segment.append(u.calculate_normal(spline_segment[point], spline_segment[point + 1]))
                self.normals[segment_index] = normals_segment

                # Track edges
                self.compute_track_lines(segment_index)

    def compute_track_lines(self, update_index = None):
        scaled_half_width = self.get_scaled_width() / 2
        lines = {
            "curve"     : 2,
            "inner_edge": scaled_half_width,
            "outer_edge": scaled_half_width + 2,
        }

        update_from = update_index if update_index is not None else 0
        update_to = update_index + 1 if update_index is not None else len(self.spline)

        for segment_index in range(update_from, update_to):
            spline_segment = self.spline.get(segment_index)
            normals_segment = self.normals[segment_index]

            for name, distance in lines.items():
                self.track_lines[f"{name}_left"].replace(segment_index, u.shift_segment(spline_segment, normals_segment, distance))
                self.track_lines[f"{name}_right"].replace(segment_index, u.shift_segment(spline_segment, normals_segment, -distance))

    def recalculate_line_offsets(self):
        self.spline.update()
        for line_name, line in self.track_lines.items():
            line.update()

    #Takes the corner angle, and applies a precalculated formula to work out the maximum speed a car can take
    def calculateMaxCorneringSpeed(self, cornerAngle):
        grad = 0.24 + (0.005 * (self.width - 12))
        yInt = 165.3 - (grad * 680)

        maxCorneringSpeed = ((cornerAngle - yInt) / grad)
        return maxCorneringSpeed

    #Returns the index of a point n distance away
    def getIndexFromDistance(self, currentIndex, distance, reverse = False):
        totalDistance = 0
        index = currentIndex
        if index is None: return None
        flat_points = self.spline.flatten_points()
        while totalDistance < distance:
            nextIndex = (index + 1) % len(self.spline)
            if not self.closed and abs(index - nextIndex) > 1:
                return None

            if reverse:
                nextIndex = (index - 1) % len(self.spline)
            totalDistance += u.point_distance(flat_points[index], flat_points[nextIndex])
            index = nextIndex
        return index

    #Checks whether track should be closed based off of whether end and start control_points are at the same positions
    def should_be_closed(self):
        pointCoords = self.control_point_coords()
        closedStatusBefore = self.closed
        if len(self.control_points) > 0:
            if pointCoords[0] == pointCoords[-1]:
                self.closed = True
                self.compute_track(update_index = [0])
            else:
                closedBefore = self.closed
                self.closed = False
                if closedBefore:
                    self.compute_track(update_index = [0, len(self.control_points) - 1])

        return [closedStatusBefore, self.closed]

    #Uses a precalculated formula to calculate the resolution of a track segment so that it looks smooth
    def calculate_resolution(self, segment_index):
        return 70
        if self.closed:
            p = self.control_points[1:]
        else:
            p = self.control_points

        smallest_angle = 180
        print(self.get_point_range(segment_index - 1, segment_index + 3))
        for i in self.get_point_range(segment_index - 1, segment_index + 3):
            if (angle := u.angle(p[i - 1].get_pos(), p[i].get_pos(), p[i + 1].get_pos())) < smallest_angle:
                smallest_angle = angle

        return int(max(abs(180 - smallest_angle) / 2, 2))

    def handle_mouse_event(self, event):
        for control_point in self.control_points:
            control_point.handle_mouse_event(event)

    def update(self):
        self.recalculate_line_offsets()

        # Limits points selected to just one
        point_index_selected = None
        for i in range(len(self.control_points)):
            point = self.control_points[i]
            if point_index_selected is not None:
                point.selected = False
            elif point.selected:
                point_index_selected = i

        # Selects both "join" points if one is selected
        if self.closed and (self.control_points[0].selected or self.control_points[-1].selected):
            self.control_points[-1].selected = True
            self.control_points[0].selected = True

        #Updates control_points
        for point_index in range(len(self.control_points)):
            point = self.control_points[point_index]
            point.update()

            #Prevents control_points that are next to each-other from touching
            if point.selected and len(self.control_points) > 1:
                nearest_point = self.control_point_spatial_grid.query(point.get_pos(), exclude_indexes = [point_index])
                if nearest_point is not None:
                    distance, nearest_index = nearest_point
                    nearest_point = self.control_points[nearest_index]
                    if abs(nearest_index - point_index) == 1:
                        min_distance = self.get_scaled_width()
                        if distance <= min_distance:
                            point.x = (nearest_point.x + (min_distance * (point.x - nearest_point.x) / distance))
                            point.y = (nearest_point.y + (min_distance * (point.y - nearest_point.y) / distance))

        #Handles when the end control point and start control point should connect
        if len(self.control_points) >= 5:
            snapThreshold = 50
            distance_between_ends = u.point_distance(self.control_points[0].get_pos(), self.control_points[-1].get_pos())
            holding_shift = pygame.key.get_mods() & pygame.KMOD_LSHIFT

            if (point_index_selected in (0, len(self.control_points) - 1)) and (distance_between_ends <= snapThreshold) and not holding_shift:
                selected_point = self.control_points[point_index_selected]
                other_point = self.control_points[0 if selected_point == -1 else -1]
                other_point.move(selected_point.get_pos())
                self.updateCloseStatus(value = True)

            if (point_index_selected in (0, -1)) and holding_shift:
                self.updateCloseStatus(value = False)

        else:
            self.updateCloseStatus(value = False)

        #Updates track
        if self.point_index_selected is not None:
            self.compute_track(update_index = self.point_index_selected)


    #Main rendering algorithm for drawing track
    def draw(self, surface, mode, positioning = "screen"):
        if mode not in ("edit", "race"):
            raise ValueError("Please enter a valid render mode")

        if positioning == "screen":
            get_coords = lambda seg, i: seg.get_screen()[i]
        elif positioning == "world":
            get_coords = lambda seg, i: seg.get_points()[i]
        else:
            raise ValueError("Please enter a valid positioning system")

        if len(self.control_points) >= 2:

            # Track edges
            for segment in range(len(self.spline)):
                left_edge_polygon = u.formPolygon(get_coords(self.track_lines["outer_edge_left"], segment),
                                                get_coords(self.track_lines["inner_edge_left"], segment))
                right_edge_polygon = u.formPolygon(get_coords(self.track_lines["outer_edge_right"], segment),
                                                 get_coords(self.track_lines["inner_edge_right"], segment))

                pygame.gfxdraw.aapolygon(surface, left_edge_polygon, self.colours["edge"])
                pygame.gfxdraw.filled_polygon(surface, left_edge_polygon, self.colours["edge"])

                pygame.gfxdraw.aapolygon(surface, right_edge_polygon, self.colours["edge"])
                pygame.gfxdraw.filled_polygon(surface, right_edge_polygon, self.colours["edge"])

            # Fill in track
            for segment in range(len(self.spline)):
                fill_polygon = u.formPolygon(get_coords(self.track_lines["inner_edge_left"], segment),
                                           get_coords(self.track_lines["inner_edge_right"], segment))

                pygame.gfxdraw.aapolygon(surface, fill_polygon, self.colours["track"])
                pygame.gfxdraw.filled_polygon(surface, fill_polygon, self.colours["track"])


            # Centre curve
            if mode == "edit":
                for segment in range(len(self.spline)):
                    center_curve_polygon = u.formPolygon(get_coords(self.track_lines["curve_left"], segment),
                                                       get_coords(self.track_lines["curve_right"], segment))

                    pygame.gfxdraw.aapolygon(surface, center_curve_polygon, self.colours["curve"])
                    pygame.gfxdraw.filled_polygon(surface, center_curve_polygon, self.colours["curve"])

            # if display_settings["finish"]: #Draws the checkered finish line
            #     checkeredHeight = (1 * self.zoomValue * (1 / self.scale))
            #     checkeredWidthCount = round((self.width * (1 / self.scale) * self.zoomValue) / checkeredHeight)
            #     checkeredWidth = (self.width * (1 / self.scale) * self.zoomValue) / checkeredWidthCount
            #     checkeredHeight = checkeredWidth
            #
            #     startPos, startAngle, startIndex, startDir = self.getStartPos()
            #
            #     if self.finishDir:
            #         startLeftCoord = int(self.__offset_leftBorderInnerEdge[startIndex][0]), int(
            #             self.__offset_leftBorderInnerEdge[startIndex][1])
            #     else:
            #         startLeftCoord = int(self.__offset_rightBorderInnerEdge[startIndex][0]), int(
            #             self.__offset_rightBorderInnerEdge[startIndex][1])
            #
            #     for y in range(-1, 1):
            #         for x in range(checkeredWidthCount):
            #             topLeft = startLeftCoord[0] - (cosDeg(startAngle) * (checkeredHeight * y)) - (
            #                     sinDeg(startAngle) * (checkeredWidth * x)), startLeftCoord[1] + (
            #                               sinDeg(startAngle) * (checkeredHeight * y)) - (
            #                               cosDeg(startAngle) * (checkeredWidth * x))
            #
            #             corner1 = topLeft
            #             corner2 = topLeft[0] - (cosDeg(startAngle) * checkeredHeight), topLeft[1] + (
            #                     sinDeg(startAngle) * checkeredHeight)
            #             corner3 = topLeft[0] - (cosDeg(startAngle) * checkeredHeight) - (
            #                     sinDeg(startAngle) * checkeredWidth), topLeft[1] + (
            #                               sinDeg(startAngle) * checkeredHeight) - (cosDeg(startAngle) * checkeredWidth)
            #             corner4 = topLeft[0] - (sinDeg(startAngle) * checkeredWidth), topLeft[1] - (
            #                     cosDeg(startAngle) * checkeredWidth)
            #
            #             if (x + y) % 2 == 0:
            #                 checkeredColour = (0, 0, 0)
            #             else:
            #                 checkeredColour = (200, 200, 200)
            #
            #             checkeredSquarePoints = [corner1, corner2, corner3, corner4]
            #             pygame.draw.polygon(surface, checkeredColour, checkeredSquarePoints)

        # Draw guide point when hovering on segment
        if ((segment := self.hovering_segment()) is not None) and (self.control_point_hovering() is None):# and (self.point_index_selected is None):
            shortest_distance = float('inf')
            shortest_point = None
            points = self.spline.get(segment)
            world_mouse = self.camera.screen_to_world(*pygame.mouse.get_pos())
            for i in range(len(points) - 1):
                distance, coord = u.lineToPointDistance(points[i], points[i + 1], world_mouse)
                if distance < shortest_distance:
                    shortest_distance = distance
                    shortest_point = coord

            if shortest_point is not None:
                ControlPoint(*shortest_point, self.camera).draw(surface, (19, 111, 150, 150))

        # Draws the control control_points
        if mode == "edit":
            for pointIndex in range(len(self.control_points)):
                point = self.control_points[pointIndex]

                if (not self.switch_front and pointIndex == len(self.control_points) - 1) or (self.switch_front and pointIndex == 0) or (self.closed and ((pointIndex == 0) or (pointIndex == len(self.control_points) - 1))):
                    colour = self.colours["front_control"]
                else:
                    colour = self.colours["control"]

                point.draw(surface, colour)

    def render_to_screen(self, viewMode, antialiasing):
        self.draw(self.screen, viewMode, antialiasing)

    #Returns a surface, with the rendered track on it.
    #TODO: Fix box_size, which has just been placed there without any thought
    def render_to_surface(self, box_size):
        flat_points = self.spline.flatten_points()

        left_most_point = min(flat_points, key=lambda p: p[0])
        right_most_point = max(flat_points, key = lambda p: p[0])
        up_most_point = min(flat_points, key = lambda p: p[1])
        down_most_point = max(flat_points, key = lambda p: p[1])

        width = right_most_point[0] - left_most_point[0]
        height = down_most_point[1] - up_most_point[1]

        pixelTrackWidth = ((self.width + 5) / self.scale)
        trackSurface = pygame.Surface(((width + pixelTrackWidth) * box_size, (height + pixelTrackWidth) * box_size), pygame.SRCALPHA)

        self.draw(trackSurface, "Display", False)
        return trackSurface
