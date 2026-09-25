import math
import pygame
import os
import sqlite3
from pathlib import Path
from config import *

#Calculates distance between 2 control_points
def point_distance(point1, point2):
    x1, y1 = point1
    x2, y2 = point2

    return math.sqrt(((y2 - y1) ** 2) + ((x1 - x2) ** 2))

#Finds the coords of the nearest point to targetCoord
def findNearest(coords, targetCoord):
    nearestPoint = min(coords, key=lambda x: (x[0] - targetCoord[0])**2 + (x[1] - targetCoord[1])**2)
    nearestIndex = coords.index(nearestPoint)
    return nearestPoint, nearestIndex

#Calculate the angle between 3 control_points
def angle(point1, point2, point3):
    distance12 = point_distance(point1, point2)
    distance23 = point_distance(point2, point3)
    distance31 = point_distance(point3, point1)

    cosAngle = ((distance12 ** 2) + (distance23 ** 2) - (distance31 ** 2)) / (2 * distance12 * distance23)
    cosAngle = max(min(cosAngle, 1), -1)
    angleRad = math.acos(cosAngle)
    angleDegrees = angleRad * (180.0 / math.pi)

    return angleDegrees

#Finds the shortest distance between a point and a line
def lineToPointDistance(lineA, lineB, point):
    a = pygame.math.Vector2(lineA)
    b = pygame.math.Vector2(lineB)
    p = pygame.math.Vector2(point)

    l2 = point_distance(lineA, lineB) ** 2
    if l2 == 0:
        return point_distance(point, lineA), lineA

    t = max(0, min(1, (p - a).dot(b - a) / l2))
    projection = a + t * (b - a)
    return point_distance(point, projection), projection

#Extends a list of control_points back by taking the length and gradient of the last segment and inserting it at the end
def extendPointsBack(points):
    xExtBack= (points[-1][0] - points[-2][0])
    yExtBack = (points[-1][1] - points[-2][1])
    pointExtBack = (points[-1][0] + xExtBack, points[-1][1] + yExtBack)

    extendedSplinePoints = points + [pointExtBack]

    return extendedSplinePoints

def get_mirrored_point(point1, point2):
    x_ext = (point2[0] - point1[0])
    y_ext = (point2[1] - point1[1])
    return point2[0] + x_ext, point2[1] + y_ext

#Extends a list of control_points forward by taking the length and gradient of the last segment and inserting it at the end
def extendPointsFront(points):
    xExtFront = (points[1][0] - points[0][0])
    yExtFront = (points[1][1] - points[0][1])
    pointExtFront = (points[0][0] - xExtFront, points[0][1] - yExtFront)

    extendedSplinePoints = [pointExtFront] + points

    return extendedSplinePoints

#Extends a list of control_points at both ends by taking the length and gradient of the last segments and inserting it at the end
def extendPoints(points):
    return extendPointsFront(extendPointsBack(points))

#Offsets a list of control_points, or a singular point
def offsetPoints(points, offset, zoom, single = False, reverse = False):
    if not reverse:
        if not single:
            return [((point[0] * zoom) + offset[0], (point[1] * zoom) + offset[1]) for point in points]
        else:
            return (points[0] * zoom) + offset[0], (points[1] * zoom) + offset[1]
    else:
        if not single:
            return [((point[0] - offset[0]) / zoom, (point[1] - offset[1]) / zoom) for point in points]
        else:
            return (points[0] - offset[0]) / zoom, (points[1] - offset[1]) / zoom

#Calculates a point, a certain distance away from another point
def calculateSide(points, pointIndex, width):
    width = width / 2
    points = extendPointsBack(points)

    distance = point_distance(points[pointIndex], points[pointIndex + 1])
    if distance == 0:
        return points[pointIndex][0], points[pointIndex][1]
    else:
        sideX = ((width * (points[pointIndex][1] - points[pointIndex + 1][1])) / distance) + points[pointIndex][0]
        sideY = ((width * (points[pointIndex + 1][0] - points[pointIndex][0])) / distance) + points[pointIndex][1]

    return sideX, sideY

def calculate_normal(from_point, to_point):
    dx = to_point[0] - from_point[0]
    dy = to_point[1] - from_point[1]

    nx, ny = -dy, dx
    length = point_distance(from_point, to_point)
    return pygame.Vector2(nx / length, ny / length)


#Used to combine two sides of a polygon (in the form of a list of control_points), to make one shape
def formPolygon(leftSide, rightSide, selectRange = None, closed = False):
    if selectRange is None:
        newLeftSide = leftSide
        newRightSide = rightSide
    else:
        newLeftSide = leftSide[selectRange]
        newRightSide = rightSide[selectRange]

    if closed:
        newLeftSide = newLeftSide + [leftSide[0]]
        newRightSide = newRightSide + [rightSide[0]]

    return newLeftSide + list(reversed(newRightSide))

def point_at_normal_distance(point, normal, n):
    nx, ny = normal
    return point[0] + nx * n, point[1] + ny * n

def shift_segment(segment, normals, width):
    shifted_segment = []
    for i in range(len(segment)):
        shifted_segment.append(point_at_normal_distance(segment[i], normals[i], width))
    return shifted_segment


#Checks whether a given point is on the screen
def checkIfOnscreen(pos, screenDimensions):
    return (0 <= pos[0] <= screenDimensions[0]) and (0 <= pos[1] <= screenDimensions[1])

#Converts meters to pixels using a scale
def mToPix(metres, pixelInMetres):
    return metres * (1 / pixelInMetres)

def sinDeg(degrees):
    return math.sin(degrees * math.pi / 180)
def cosDeg(degrees):
    return math.cos(degrees * math.pi / 180)

#Converts pixels to miles using a pix -> meters scale
def pixToMiles(pixels, scale):
    meters = pixels * scale
    return int(meters * 2.237)

#Takes seconds and output pretty version
def secondToRaceTimer(inputSeconds):
    mins = "{:02}".format(int(inputSeconds // 60))
    secs =  f"{(inputSeconds % 60):06.3f}"

    return f"{mins}:{secs}"

#Calculates the bearing off two control_points.
def bearing(pos1, pos2):
    changeX = pos2[0] - pos1[0]
    changeY = pos2[1] - pos1[1]

    bearingAngle = math.atan2(changeX, changeY)
    bearingAngle = math.degrees(bearingAngle)
    return bearingAngle % 360

#Returns track name when in "<track>.track" format
def getTrackName(fullName):
    return fullName[:-(len('.track'))]

def asset_path(asset_type, file_name):
    return os.path.join(ASSETS_DIR, asset_type, file_name)

def root_path(*paths):
    return os.path.join(ROOT_PATH, *paths)

def get_value(values, condition, single = True):
    result = [(values[i], i) for i in range(len(values)) if condition(values[i])]
    if single:
        if len(result) > 0:
            return result[0]
        return None
    return result

def deleteTrackTimes(UUID):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM TIMES WHERE TrackUUID = ?", UUID)
    conn.commit()
    conn.close()

#Used to determine whether the track is bending left or right
def trackDir(P1, P2, P3):
    v1 = (P2[0] - P1[0], P2[1] - P1[1])
    v2 = (P3[0] - P2[0], P3[1] - P2[1])

    crossProd = v1[0] * v2[1] - v1[1] * v2[0]
    return crossProd

def get_precision(value):
    str_value = str(value)
    split_value = str_value.split('.')
    if len(split_value) == 2:
        return len(split_value[1])
    return 1

def mult_color(color, mult):
    return tuple(max(0, min(int(c * mult), 255)) for c in color)

def mean(n1, n2):
    return (n1 + n2) / 2