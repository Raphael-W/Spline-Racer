import math
import numpy as np

#Calculates distance between 2 points
def pointDistance(point1, point2):
    x1, y1 = point1
    x2, y2 = point2

    return math.sqrt(((y2 - y1) ** 2) + ((x1 - x2) ** 2))

def gradient(point1, point2):
    x1, y1 = point1
    x2, y2 = point2
    if (x2 - x1) == 0:
        return 0
    return (y2 - y1) / (x2 - x1)

def angle(point1, point2, point3):
    distance12 = pointDistance(point1, point2)
    distance23 = pointDistance(point2, point3)
    distance31 = pointDistance(point3, point1)

    cosAngle = ((distance12 ** 2) + (distance23 ** 2) - (distance31 ** 2)) / (2 * distance12 * distance23)
    cosAngle = max(min(cosAngle, 1), -1)
    angleRad = math.acos(cosAngle)
    angleDegrees = angleRad * (180.0 / math.pi)

    return angleDegrees

def lineToPointDistance(lineA, lineB, point):
    lineA = np.array(lineA)
    lineB = np.array(lineB)
    point = np.array(point)

    l2 = pointDistance(lineA, lineB) ** 2
    if l2 == 0:
        return pointDistance(point, lineA)

    t = max(0, min(1, np.dot(point - lineA, lineB - lineA) / l2))
    projection = lineA + t * (lineB - lineA)
    return pointDistance(point, projection)

def extendPoints(points):
    xExt = (points[-1][0] - points[-2][0])
    yExt = (points[-1][1] - points[-2][1])
    pointExt = (points[-1][0] + xExt, points[-1][1] + yExt)
    extendedSplinePoints = points + [pointExt]

    return extendedSplinePoints

def offsetPoints(points, offset, zoom, single = False):
    if not single:
        return [((point[0] * zoom) + offset[0], (point[1] * zoom) + offset[1]) for point in points]
    else:
        return (points[0] * zoom) + offset[0], (points[1] * zoom) + offset[1]

def calculateSide(points, pointIndex, width):
    width = width / 2
    points = extendPoints(points)

    distance = pointDistance(points[pointIndex], points[pointIndex + 1])
    if distance == 0:
        return points[pointIndex][0], points[pointIndex][1]
    else:
        sideX = ((width * (points[pointIndex][1] - points[pointIndex + 1][1])) / distance) + points[pointIndex][0]
        sideY = ((width * (points[pointIndex + 1][0] - points[pointIndex][0])) / distance) + points[pointIndex][1]

    return sideX, sideY

def formPolygon(leftSide, rightSide):
     return leftSide + list(reversed(rightSide))