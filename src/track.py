from utils import *
from history import *
from scipy.spatial import KDTree

import base64
import uuid

#Main mathematical formula for track curve
def calculateSpline(control_points, t):
    control_points = [control_points[1]] + control_points + [control_points[-2]]

    #Interpolate curve using Catmull Rom
    def interpolate(P0, P1, P2, P3, T):

        P0 = np.array(P0)
        P1 = np.array(P1)
        P2 = np.array(P2)
        P3 = np.array(P3)

        return (
            T * ((2 - T) * T - 1) * P0
            + (T * T * (3 * T - 5) + 2) * P1
            + T * ((4 - 3 * T) * T + 1) * P2
            + (T - 1) * T * T * P3) / 2

    segment = int(t * (len(control_points) - 3))
    t = (t * (len(control_points) - 3)) - segment
    p0, p1, p2, p3 = control_points[segment:segment+4]

    return interpolate(p0, p1, p2, p3, t)

#Used to determine whether the track is bending left or right
def trackDir(P1, P2, P3):
    v1 = (P2[0] - P1[0], P2[1] - P1[1])
    v2 = (P3[0] - P2[0], P3[1] - P2[1])

    crossProd = v1[0] * v2[1] - v1[1] * v2[0]
    return crossProd


class ControlPoint:
    def __init__(self, posX, posY):
        self.posX = posX
        self.posY = posY

        self.baseSize = 10
        self.size = self.baseSize

        self.new = True
        self.pointSelected = True
        self.mouseHovering = False
        self.mouseDownLast = False

        self.posAtClick = (posX, posY)
        self.posAtRelease = None

    #Returns the control point's pos in format [posX, posY]
    def getPos(self):
        return self.posX, self.posY

    #Move a control point to a specific location
    def move(self, newPos):
        self.posX = newPos[0]
        self.posY = newPos[1]

    #Calculates whether mouse is hovering, and whether user has selected point
    def update(self, mousePosX, mousePosY, zoom, screenWidth, screenHeight, screenBorder, pygame, offset):
        zoomedSize = self.size / zoom
        self.mouseHovering = ((self.posX + (zoomedSize + 2) > mousePosX > self.posX - (zoomedSize + 2)) and
                               (self.posY + (zoomedSize + 2) > mousePosY > self.posY - (zoomedSize + 2)))

        if self.mouseHovering:
            self.size = self.baseSize + 2
        else:
            self.size = self.baseSize

        if not pygame.mouse.get_pressed()[0]:
            self.pointSelected = False
            self.new = False
            if self.posAtClick is not None:
                self.posAtRelease = self.getPos()

        #Ensures control point can't go off the screen
        if self.pointSelected:
            if (screenBorder - offset[0]) / zoom < mousePosX < (screenWidth - screenBorder - offset[0]) / zoom:
                self.posX = mousePosX

            if (screenBorder - offset[1]) / zoom < mousePosY < (screenHeight - screenBorder - offset[1]) / zoom:
                self.posY = mousePosY

        if not self.pointSelected:
            self.pointSelected = (self.mouseHovering and pygame.mouse.get_pressed()[0] and not self.mouseDownLast)

        if self.pointSelected and not self.mouseDownLast and not self.new:
            self.posAtClick = self.getPos()

        self.mouseDownLast = pygame.mouse.get_pressed()[0]

    #Draws point to screen
    def draw(self, colour, screen, pygame, offset, zoom):
        newPos = offsetPoints((self.posX, self.posY), offset, zoom, single = True)
        newPos = [int(point) for point in newPos]

        if checkIfOnscreen(newPos, screen.get_size()):
            pygame.gfxdraw.aacircle(screen, newPos[0], newPos[1], self.size, colour)
            pygame.gfxdraw.filled_circle(screen, newPos[0], newPos[1], self.size, colour)

class Track:
    def __init__(self, resolution, pygame, screen, points = None):
        if points is None:
            points = []

        self.points = points
        self.splinePoints = []
        self.pointCoords = None
        self.pointTree = None

        for point in self.points:
            self.points.append(ControlPoint(point[0], point[1]))

        self.pygame = pygame
        self.screen = screen

        self.UUID = str(uuid.uuid1())

        #Visual Track Points
        self.__mainPolyLeftEdge = []
        self.__mainPolyRightEdge = []

        self.__leftBorderInnerEdge = []
        self.__leftBorderOuterEdge = []

        self.__rightBorderInnerEdge = []
        self.__rightBorderOuterEdge = []

        #Cached, offset - Visual Track Points
        self.__offset_mainPolyLeftEdge = []
        self.__offset_mainPolyRightEdge = []

        self.__offset_leftBorderInnerEdge = []
        self.__offset_leftBorderOuterEdge = []

        self.__offset_rightBorderInnerEdge = []
        self.__offset_rightBorderOuterEdge = []

        self.__offset_splinePoints = []

        self.offsetValue = (0, 0)
        self.zoomValue = 1

        self.pointsSelected = []
        self.mouseHovering = None
        self.closed = False

        self.perSegRes = resolution
        self.autoRes = False
        self.pointList = []
        self.scale = 0.2
        self.width = 12

        self.length = 0

        self.finishIndex = None
        self.finishDir = True

        self.referenceImageDir = None

        self.history = History(self)

        self.leftRacingLineSpline = []
        self.rightRacingLineSpline = []
        self.showRacingLine = False
        self.lastRacingLine = False

        self.offset_leftRacingLineSpline = []
        self.offset_rightRacingLineSpline = []

        self.slightBendLimit = 7000

        self.curbPoints = []

    #Clear track, and any settings
    def clear(self):
        autoResValue = self.autoRes
        self.__init__(20, self.pygame, self.screen)
        self.autoRes = autoResValue

    #Called when opening tracks from a save file, and is used to load in the track and its data
    def loadTrackPoints(self, pointCoords):
        self.clear()
        for point in pointCoords:
            self.add(ControlPoint(point[0], point[1]), update = False)

    def setAutoRes(self, value):
        self.autoRes = value
        if value:
            self.automaticallyAdjustRes()

    #Collects relevant data about track and combines it into a dictionary used for saving
    def getSaveState(self):
        referenceImageData = None
        if self.referenceImageDir is not None:
            with open(self.referenceImageDir, "rb") as img_file:
                referenceImageData = base64.b64encode(img_file.read()).decode('utf-8')

        points = self.returnPointCoords()
        properties = {"width"      : self.width,
                      "finishIndex": self.finishIndex,
                      "finishDir"  : self.finishDir,
                      "referenceImage": referenceImageData}

        return {"points"    : points,
                "UUID": self.UUID,
                "properties": properties}

    #Returns track edges
    def getEdgePoints(self):
        return [list(self.__leftBorderInnerEdge), list(self.__rightBorderInnerEdge)]

    #Used to check whether the track has been changed
    def getUniquenessToken(self):
        edgeCheck = self.returnPointCoords()
        finishCheck = self.getStartPos()[-2:]
        widthCheck = self.width
        return str(edgeCheck) + str(finishCheck) + str(widthCheck)

    #Returns coordinates of start line
    def getStartPos(self):
        if self.finishIndex is None:
            finishIndex = 5 / self.perSegRes
            finishDir = True
        else:
            finishIndex = self.finishIndex
            finishDir = self.finishDir

        finishCoord = self.splinePoints[int(finishIndex * self.perSegRes)]
        finishNeighbourCoord = self.splinePoints[int(finishIndex * self.perSegRes) + 1]

        trackAngle = 0 + math.degrees(math.atan2(finishCoord[0] - finishNeighbourCoord[0], (finishCoord[1] - finishNeighbourCoord[1]))) - 90
        startAngle = trackAngle + (finishDir * 180)

        return finishCoord, startAngle, int(finishIndex * self.perSegRes), finishDir

    def save(self):
        self.history.saveTrack()

    def isSaved(self):
        return self.history.saved

    def changeWidth(self, value):
        self.width = value
        self.computeTrackEdges()
        self.computeRacingLine()
        self.offsetAllTrackPoints()

    #Called when user stops setting width (lets go of track width slider)
    def changeWidthComplete(self, initialValue, slider):
        self.history.addAction("CHANGE WIDTH", [initialValue, self.width, slider])

    def changeRes(self, value):
        if int(value) != self.perSegRes:
            self.perSegRes = int(value)
            self.computeTrack()

    #Called when user stops setting track res (lets go of track resolution slider)
    def changeResComplete(self, initialValue, slider):
        self.history.addAction("CHANGE RESOLUTION", [initialValue, self.perSegRes, slider])

    #Calculates length of track by adding length of each segment
    def calculateLength(self):
        if self.scale is not None:
            self.length = 0
            for point in range(len(self.splinePoints) - 1):
                self.length += pointDistance(self.splinePoints[point], self.splinePoints[point + 1]) * self.scale

    #Multiplies each point by scale factor
    def scalePoints(self, scale):
        for point in self.points:
            newPosition = (point.posX * scale, point.posY * scale)
            point.move(newPosition)
        self.computeTrack()

    #Called when track is closed/unclosed
    def updateCloseStatus(self, value, update = False):
        if self.closed is not value:
            self.closed = value
            if update:
                self.computeTrack(updatePoints = [0])

    #Called in game loop, offsets points when user pans/zooms
    def updateOffsetValues(self, offset, zoom):
        offsetChanged = False
        if (offset != self.offsetValue) or (zoom != self.zoomValue):
            offsetChanged = True

        self.offsetValue = offset
        self.zoomValue = zoom

        if offsetChanged:
            self.offsetAllTrackPoints()

    #Offsets each point that makes up track edges by current values for offset and zoom
    def offsetAllTrackPoints(self, updatePoints = []):
        if len(self.points) >= 2:
            numOfSegments = len(self.points) - 1
            resolution = numOfSegments * self.perSegRes

            updateRanges = []
            for point in updatePoints:
                if len(updatePoints) > 0:
                    if self.closed: #Used to determine what points should be updated
                        lengthPoints = (len(self.points) - 1)

                        beforeJoinLowerBound = max(point - 2, 0)
                        beforeJoinUpperBound = min(point + 2, lengthPoints)
                        beforeJoinUpdateRange = [beforeJoinLowerBound * self.perSegRes, beforeJoinUpperBound * self.perSegRes]

                        afterJoinLowerBound = max((point + lengthPoints) - 2, 0)
                        afterJoinUpperBound = min((point + lengthPoints) + 2, lengthPoints)
                        afterJoinUpdateRange = [afterJoinLowerBound * self.perSegRes, afterJoinUpperBound * self.perSegRes]

                        if afterJoinLowerBound >= (lengthPoints + 2):
                            afterJoinLowerBound = max((point - lengthPoints) - 2, 0)
                            afterJoinUpperBound = max(min((point - lengthPoints) + 2, lengthPoints), 0)
                            afterJoinUpdateRange = [afterJoinLowerBound * self.perSegRes, afterJoinUpperBound * self.perSegRes]

                        updateRanges.append(beforeJoinUpdateRange)
                        updateRanges.append(afterJoinUpdateRange)

                    else:
                        lowerBound = max(point - 2, 0)
                        upperBound = min(point + 2, numOfSegments)
                        updateRange = (lowerBound * self.perSegRes, upperBound * self.perSegRes)

                        updateRanges.append(updateRange)

            if len(updatePoints) == 0: #Reset all points
                self.__offset_mainPolyLeftEdge = offsetPoints(self.__mainPolyLeftEdge, self.offsetValue, self.zoomValue)
                self.__offset_mainPolyRightEdge = offsetPoints(self.__mainPolyRightEdge, self.offsetValue, self.zoomValue)

                self.__offset_leftBorderInnerEdge = offsetPoints(self.__leftBorderInnerEdge, self.offsetValue, self.zoomValue)
                self.__offset_leftBorderOuterEdge = offsetPoints(self.__leftBorderOuterEdge, self.offsetValue, self.zoomValue)

                self.__offset_rightBorderInnerEdge = offsetPoints(self.__rightBorderInnerEdge, self.offsetValue, self.zoomValue)
                self.__offset_rightBorderOuterEdge = offsetPoints(self.__rightBorderOuterEdge, self.offsetValue, self.zoomValue)

                self.offset_leftRacingLineSpline = offsetPoints(self.leftRacingLineSpline, self.offsetValue, self.zoomValue)
                self.offset_rightRacingLineSpline = offsetPoints(self.rightRacingLineSpline, self.offsetValue, self.zoomValue)

                self.__offset_splinePoints = offsetPoints(self.splinePoints, self.offsetValue, self.zoomValue)

            else:
                for updateRange in updateRanges: #Reset points in specific range
                    self.__offset_mainPolyLeftEdge[updateRange[0]:updateRange[1]] = offsetPoints(self.__mainPolyLeftEdge[updateRange[0]:updateRange[1]], self.offsetValue, self.zoomValue)
                    self.__offset_mainPolyRightEdge[updateRange[0]:updateRange[1]] = offsetPoints(self.__mainPolyRightEdge[updateRange[0]:updateRange[1]], self.offsetValue, self.zoomValue)

                    self.__offset_leftBorderInnerEdge[updateRange[0]:updateRange[1]] = offsetPoints(self.__leftBorderInnerEdge[updateRange[0]:updateRange[1]], self.offsetValue, self.zoomValue)
                    self.__offset_leftBorderOuterEdge[updateRange[0]:updateRange[1]] = offsetPoints(self.__leftBorderOuterEdge[updateRange[0]:updateRange[1]], self.offsetValue, self.zoomValue)

                    self.__offset_rightBorderInnerEdge[updateRange[0]:updateRange[1]] = offsetPoints(self.__rightBorderInnerEdge[updateRange[0]:updateRange[1]], self.offsetValue, self.zoomValue)
                    self.__offset_rightBorderOuterEdge[updateRange[0]:updateRange[1]] = offsetPoints(self.__rightBorderOuterEdge[updateRange[0]:updateRange[1]], self.offsetValue, self.zoomValue)

                    self.offset_leftRacingLineSpline[updateRange[0]:updateRange[1]] = offsetPoints(self.leftRacingLineSpline[updateRange[0]:updateRange[1]], self.offsetValue, self.zoomValue)
                    self.offset_rightRacingLineSpline[updateRange[0]:updateRange[1]] = offsetPoints(self.rightRacingLineSpline[updateRange[0]:updateRange[1]], self.offsetValue, self.zoomValue)

                    self.__offset_splinePoints[updateRange[0]:updateRange[1]] = offsetPoints(self.splinePoints[updateRange[0]:updateRange[1]], self.offsetValue, self.zoomValue)

    #Checks if current mouse pos crosses the spline (for inserting points)
    def pointOnCurve(self, pointX, pointY, margin):
        smallestDistance = float('inf'), None
        segment = None
        nearestPointIndex = None

        for pointIndex in range(len(self.splinePoints) - 1):
            distanceToTrack, nearestPointOnTrack = lineToPointDistance(self.splinePoints[pointIndex], self.splinePoints[pointIndex + 1], (pointX, pointY))
            if distanceToTrack <= margin:
                if distanceToTrack < smallestDistance[0]:
                    smallestDistance = (distanceToTrack, nearestPointOnTrack)
                    nearestPointIndex = pointIndex
                    reconstructedT = (pointIndex / len(self.splinePoints))

                    numOfPoints = len(self.points) - 1
                    segment = int(reconstructedT * numOfPoints) + 1

        if segment is not None:
            return True, segment, smallestDistance[1], nearestPointIndex
        else:
            return False, None, None, None

    #Adds new control point
    def add(self, controlPoint, index = -1, update = True, userPerformed = False):
        if index == -1:
            index = len(self.points)

        self.points.insert(index, controlPoint)
        if userPerformed:
            self.history.addAction("ADD POINT", [index, controlPoint])
            self.calculateLength()
        if len(self.points) > 1:
            if self.finishIndex is not None:
                if index <= self.finishIndex:
                    self.finishIndex += 1

            if index > 0:
                self.splinePoints = self.splinePoints[:((index - 1) * self.perSegRes):] + ([''] * self.perSegRes) + self.splinePoints[((index - 1) * self.perSegRes):]

                self.__mainPolyLeftEdge = self.__mainPolyLeftEdge[:((index - 1) * self.perSegRes):] + ([''] * self.perSegRes) + self.__mainPolyLeftEdge[((index - 1) * self.perSegRes):]
                self.__mainPolyRightEdge = self.__mainPolyRightEdge[:((index - 1) * self.perSegRes):] + ([''] * self.perSegRes) + self.__mainPolyRightEdge[((index - 1) * self.perSegRes):]

                self.__leftBorderInnerEdge = self.__leftBorderInnerEdge[:((index - 1) * self.perSegRes)] + ([''] * self.perSegRes) + self.__leftBorderInnerEdge[((index - 1) * self.perSegRes):]
                self.__leftBorderOuterEdge = self.__leftBorderOuterEdge[:((index - 1) * self.perSegRes)] + ([''] * self.perSegRes) + self.__leftBorderOuterEdge[((index - 1) * self.perSegRes):]

                self.__rightBorderInnerEdge = self.__rightBorderInnerEdge[:((index - 1) * self.perSegRes)] + ([''] * self.perSegRes) + self.__rightBorderInnerEdge[((index - 1) * self.perSegRes):]
                self.__rightBorderOuterEdge = self.__rightBorderOuterEdge[:((index - 1) * self.perSegRes)] + ([''] * self.perSegRes) + self.__rightBorderOuterEdge[((index - 1) * self.perSegRes):]

                #Offsets:

                self.__offset_mainPolyLeftEdge = self.__offset_mainPolyLeftEdge[:((index - 1) * self.perSegRes):] + ([''] * self.perSegRes) + self.__offset_mainPolyLeftEdge[((index - 1) * self.perSegRes):]
                self.__offset_mainPolyRightEdge = self.__offset_mainPolyRightEdge[:((index - 1) * self.perSegRes):] + ([''] * self.perSegRes) + self.__offset_mainPolyRightEdge[((index - 1) * self.perSegRes):]

                self.__offset_leftBorderInnerEdge = self.__offset_leftBorderInnerEdge[:((index - 1) * self.perSegRes)] + ([''] * self.perSegRes) + self.__offset_leftBorderInnerEdge[((index - 1) * self.perSegRes):]
                self.__offset_leftBorderOuterEdge = self.__offset_leftBorderOuterEdge[:((index - 1) * self.perSegRes)] + ([''] * self.perSegRes) + self.__offset_leftBorderOuterEdge[((index - 1) * self.perSegRes):]

                self.__offset_rightBorderInnerEdge = self.__offset_rightBorderInnerEdge[:((index - 1) * self.perSegRes)] + ([''] * self.perSegRes) + self.__offset_rightBorderInnerEdge[((index - 1) * self.perSegRes):]
                self.__offset_rightBorderOuterEdge = self.__offset_rightBorderOuterEdge[:((index - 1) * self.perSegRes)] + ([''] * self.perSegRes) + self.__offset_rightBorderOuterEdge[((index - 1) * self.perSegRes):]

            else:
                self.splinePoints = ([''] * self.perSegRes) + self.splinePoints

                self.__mainPolyLeftEdge = ([''] * self.perSegRes) + self.__mainPolyLeftEdge
                self.__mainPolyRightEdge = ([''] * self.perSegRes) + self.__mainPolyRightEdge

                self.__leftBorderInnerEdge = ([''] * self.perSegRes) + self.__leftBorderInnerEdge
                self.__leftBorderOuterEdge = ([''] * self.perSegRes) + self.__leftBorderOuterEdge

                self.__rightBorderInnerEdge = ([''] * self.perSegRes) + self.__rightBorderInnerEdge
                self.__rightBorderOuterEdge = ([''] * self.perSegRes) + self.__rightBorderOuterEdge

                #Offsets:

                self.__offset_mainPolyLeftEdge = ([''] * self.perSegRes) + self.__offset_mainPolyLeftEdge
                self.__offset_mainPolyRightEdge = ([''] * self.perSegRes) + self.__offset_mainPolyRightEdge

                self.__offset_leftBorderInnerEdge = ([''] * self.perSegRes) + self.__offset_leftBorderInnerEdge
                self.__offset_leftBorderOuterEdge = ([''] * self.perSegRes) + self.__offset_leftBorderOuterEdge

                self.__offset_rightBorderInnerEdge = ([''] * self.perSegRes) + self.__offset_rightBorderInnerEdge
                self.__offset_rightBorderOuterEdge = ([''] * self.perSegRes) + self.__offset_rightBorderOuterEdge

        if update:
            self.computeTrack(updatePoints = [index])

    #Removes control point at index specified
    def remove(self, index = -1, update = True, userPerformed = False):
        if index == -1:
            index = len(self.points) - 1

        if len(self.points) - 1 >= index:
            removedPoint = self.points.pop(index)
            if userPerformed:
                self.history.addAction("REMOVE POINT", [index, removedPoint])
                self.calculateLength()

            if self.finishIndex is not None:
                if index <= self.finishIndex:
                    self.finishIndex -= 1

            if index > 0:
                self.splinePoints = self.splinePoints[:((index - 1) * self.perSegRes):] + self.splinePoints[(index * self.perSegRes):]

                self.__mainPolyLeftEdge = self.__mainPolyLeftEdge[:((index - 1) * self.perSegRes):] + self.__mainPolyLeftEdge[(index * self.perSegRes):]
                self.__mainPolyRightEdge = self.__mainPolyRightEdge[:((index - 1) * self.perSegRes):] + self.__mainPolyRightEdge[(index * self.perSegRes):]

                self.__leftBorderInnerEdge = self.__leftBorderInnerEdge[:((index - 1) * self.perSegRes)] + self.__leftBorderInnerEdge[(index * self.perSegRes):]
                self.__leftBorderOuterEdge = self.__leftBorderOuterEdge[:((index - 1) * self.perSegRes)] + self.__leftBorderOuterEdge[(index * self.perSegRes):]

                self.__rightBorderInnerEdge = self.__rightBorderInnerEdge[:((index - 1) * self.perSegRes)] + self.__rightBorderInnerEdge[(index * self.perSegRes):]
                self.__rightBorderOuterEdge = self.__rightBorderOuterEdge[:((index - 1) * self.perSegRes)] + self.__rightBorderOuterEdge[(index * self.perSegRes):]

                #Offsets:

                self.__offset_mainPolyLeftEdge = self.__offset_mainPolyLeftEdge[:((index - 1) * self.perSegRes):] + self.__offset_mainPolyLeftEdge[(index * self.perSegRes):]
                self.__offset_mainPolyRightEdge = self.__offset_mainPolyRightEdge[:((index - 1) * self.perSegRes):] + self.__offset_mainPolyRightEdge[(index * self.perSegRes):]

                self.__offset_leftBorderInnerEdge = self.__offset_leftBorderInnerEdge[:((index - 1) * self.perSegRes)] + self.__offset_leftBorderInnerEdge[(index * self.perSegRes):]
                self.__offset_leftBorderOuterEdge = self.__offset_leftBorderOuterEdge[:((index - 1) * self.perSegRes)] + self.__offset_leftBorderOuterEdge[(index * self.perSegRes):]

                self.__offset_rightBorderInnerEdge = self.__offset_rightBorderInnerEdge[:((index - 1) * self.perSegRes)] + self.__offset_rightBorderInnerEdge[(index * self.perSegRes):]
                self.__offset_rightBorderOuterEdge = self.__offset_rightBorderOuterEdge[:((index - 1) * self.perSegRes)] + self.__offset_rightBorderOuterEdge[(index * self.perSegRes):]

            else:
                self.splinePoints = self.splinePoints[((index + 1) * self.perSegRes):]

                self.__mainPolyLeftEdge = self.__mainPolyLeftEdge[((index + 1) * self.perSegRes):]
                self.__mainPolyRightEdge = self.__mainPolyRightEdge[((index + 1) * self.perSegRes):]

                self.__leftBorderInnerEdge = self.__leftBorderInnerEdge[((index + 1) * self.perSegRes):]
                self.__leftBorderOuterEdge = self.__leftBorderOuterEdge[((index + 1) * self.perSegRes):]

                self.__rightBorderInnerEdge = self.__rightBorderInnerEdge[((index + 1) * self.perSegRes):]
                self.__rightBorderOuterEdge = self.__rightBorderOuterEdge[((index + 1) * self.perSegRes):]

                #Offsets:

                self.__offset_mainPolyLeftEdge = self.__offset_mainPolyLeftEdge[((index + 1) * self.perSegRes):]
                self.__offset_mainPolyRightEdge = self.__offset_mainPolyRightEdge[((index + 1) * self.perSegRes):]

                self.__offset_leftBorderInnerEdge = self.__offset_leftBorderInnerEdge[((index + 1) * self.perSegRes):]
                self.__offset_leftBorderOuterEdge = self.__offset_leftBorderOuterEdge[((index + 1) * self.perSegRes):]

                self.__offset_rightBorderInnerEdge = self.__offset_rightBorderInnerEdge[((index + 1) * self.perSegRes):]
                self.__offset_rightBorderOuterEdge = self.__offset_rightBorderOuterEdge[((index + 1) * self.perSegRes):]

            if update:
                self.computeTrack(updatePoints = [index])

    #Handles undoing of track actions (control point moving, width changes etc.)
    def undo(self, actions):
        for action in actions:
            if action is not None:
                if action.command == "ADD POINT": #Handles the undoing of adding points
                    self.remove(action.params[0], update = False)
                    self.shouldTrackBeClosed()
                    self.calculateLength()
                    self.computeTrack(updatePoints = [action.params[0]])
                elif action.command == "REMOVE POINT": #Handles the undoing of removing points
                    self.add(action.params[1], action.params[0])
                    self.calculateLength()
                elif action.command == "MOVE POINT": #Handles the undoing of moving points
                    self.points[action.params[0]].move(action.params[1])
                    self.shouldTrackBeClosed()
                    self.calculateLength()
                    self.computeTrack(updatePoints = [action.params[0]])
                elif action.command == "CHANGE WIDTH": #Handles the undoing of changing the width of the track
                    self.changeWidth(action.params[0])
                    action.params[2].updateValue(self.width)
                elif action.command == "CHANGE RESOLUTION": #Handles the undoing of changing the resolution
                    self.changeRes(action.params[0])
                    action.params[2].updateValue(self.perSegRes)
                elif action.command == "SET SCALE": #Handles the undoing of setting the scale of the track
                    self.scalePoints(1 / (action.params[0] * (1 / self.scale)))
                    self.calculateLength()
                elif action.command == "SET FINISH": #Handles the undoing of setting the finish line
                    self.finishIndex = action.params[0][0]
                    self.finishDir = action.params[0][1]
        return actions

    #Handles redoing of previously undone actions
    def redo(self, actions):
        for action in actions:
            if action is not None:
                if action.command == "ADD POINT": #Handles the redoing of adding points
                    self.add(action.params[1], action.params[0], update = False)
                    self.shouldTrackBeClosed()
                    self.computeTrack(updatePoints = [action.params[0]])
                    self.calculateLength()
                elif action.command == "REMOVE POINT": #Handles the redoing of removing points
                    self.remove(action.params[0])
                    self.calculateLength()
                elif action.command == "MOVE POINT": #Handles the redoing of moving points
                    self.points[action.params[0]].move(action.params[2])
                    self.shouldTrackBeClosed()
                    self.calculateLength()
                    self.computeTrack(updatePoints = [action.params[0]])
                elif action.command == "CHANGE WIDTH": #Handles the redoing of changing the width of the track
                    self.changeWidth(action.params[1])
                    action.params[2].updateValue(self.width)
                elif action.command == "CHANGE RESOLUTION": #Handles the redoing of changing the resolution
                    self.changeRes(action.params[1])
                    action.params[2].updateValue(self.perSegRes)
                elif action.command == "SET SCALE": #Handles the redoing of setting the scale
                    self.scalePoints(action.params[0] * (1 / self.scale))
                    self.calculateLength()
                elif action.command == "SET FINISH": #Handles the redoing of setting the finish line
                    self.finishIndex = action.params[1][0]
                    self.finishDir = action.params[1][1]
        return actions

    #Returns a list of the control point coords
    def returnPointCoords(self, lazy = False):
        if (self.pointCoords is None) or not lazy:
            self.pointCoords = []
            for point in self.points:
                self.pointCoords.append(point.getPos())

            if len(self.pointCoords) >= 2:
                self.pointTree = KDTree(self.pointCoords)

            return list(self.pointCoords)
        else:
            return list(self.pointCoords)

    #Updates segments that make up main track curve. If no points are specified, whole track curve is updated
    def computeSpline(self, updatePoints = []):
        if len(self.points) >= 2:
            if self.closed: #Adding points makes the close join seamless and smooth
                first1 = self.points[1]
                first2 = self.points[2]
                last1 = self.points[-2]
                last2 = self.points[-3]

                self.add(last1, 0, False)
                self.add(last2, 0, False)
                self.add(first1, -1, False)
                self.add(first2, -1, False)

            numOfSegments = len(self.points) - 1
            resolution = numOfSegments * self.perSegRes

            updateRanges = []
            if self.closed and (0 in updatePoints) and (((len(self.points) - 1) - 4) in updatePoints):
                updatePoints.remove(0)

            for point in updatePoints:
                if len(updatePoints) > 0:
                    if self.closed: #Calculates the update range of the track to ensure only the minimum number of points are recalculated
                        lengthPoints = (len(self.points) - 1) - 4
                        point += 2

                        beforeJoinLowerBound = max(point - 2, 2)
                        beforeJoinUpperBound = min(point + 2, lengthPoints + 2)
                        beforeJoinUpdateRange = [beforeJoinLowerBound * self.perSegRes, beforeJoinUpperBound * self.perSegRes]

                        afterJoinLowerBound = max((point + lengthPoints) - 2, 2)
                        afterJoinUpperBound = min((point + lengthPoints) + 2, lengthPoints + 2)
                        afterJoinUpdateRange = [afterJoinLowerBound * self.perSegRes, afterJoinUpperBound * self.perSegRes]

                        if afterJoinLowerBound >= (lengthPoints + 2):
                            afterJoinLowerBound = max((point - lengthPoints) - 2, 2)
                            afterJoinUpperBound = max(min((point - lengthPoints) + 2, lengthPoints + 2), 2)
                            afterJoinUpdateRange = [afterJoinLowerBound * self.perSegRes, afterJoinUpperBound * self.perSegRes]

                        updateRanges.append(beforeJoinUpdateRange)
                        updateRanges.append(afterJoinUpdateRange)

                    else:
                        lowerBound = max(point - 2, 0)
                        upperBound = min(point + 2, numOfSegments)
                        updateRange = (lowerBound * self.perSegRes, upperBound * self.perSegRes)

                        updateRanges.append(updateRange)

            if len(updateRanges) == 0:
                updateRanges = [(0, resolution)]
                self.splinePoints = ([''] * resolution)

            pointCoords = self.returnPointCoords()
            for updateRange in updateRanges:
                for tInt in range(*updateRange):
                    t = tInt / resolution
                    self.splinePoints[tInt] = (calculateSpline(pointCoords, t))

            if self.closed: #Removes the points added at the top
                self.remove(0, False)
                self.remove(0, False)
                self.remove(-1, False)
                self.remove(-1, False)

    #Updates segments that make up visual track. If no points are specified, whole track is updated
    def computeTrackEdges(self, updatePoints = []):
        if len(self.points) >= 2:
            numOfSegments = len(self.points) - 1
            resolution = numOfSegments * self.perSegRes

            updateRanges = []
            for point in updatePoints:
                if len(updatePoints) > 0:
                    if self.closed: #Calculates the update range of the track to ensure only the minimum number of points are recalculated
                        lengthPoints = (len(self.points) - 1)

                        beforeJoinLowerBound = max(point - 2, 0)
                        beforeJoinUpperBound = min(point + 2, lengthPoints)
                        beforeJoinUpdateRange = [beforeJoinLowerBound * self.perSegRes, beforeJoinUpperBound * self.perSegRes]

                        afterJoinLowerBound = max((point + lengthPoints) - 2, 0)
                        afterJoinUpperBound = min((point + lengthPoints) + 2, lengthPoints)
                        afterJoinUpdateRange = [afterJoinLowerBound * self.perSegRes, afterJoinUpperBound * self.perSegRes]

                        if afterJoinLowerBound >= (lengthPoints + 2):
                            afterJoinLowerBound = max((point - lengthPoints) - 2, 0)
                            afterJoinUpperBound = max(min((point - lengthPoints) + 2, lengthPoints), 0)
                            afterJoinUpdateRange = [afterJoinLowerBound * self.perSegRes, afterJoinUpperBound * self.perSegRes]

                        updateRanges.append(beforeJoinUpdateRange)
                        updateRanges.append(afterJoinUpdateRange)

                    else:
                        lowerBound = max(point - 2, 0)
                        upperBound = min(point + 2, numOfSegments)
                        updateRange = (lowerBound * self.perSegRes, upperBound * self.perSegRes)

                        updateRanges.append(updateRange)

            if len(updatePoints) == 0: #Resets all points for recalculation
                updateRanges = [(0, resolution)]

                self.__mainPolyLeftEdge = self.__offset_mainPolyLeftEdge = ([''] * resolution)
                self.__mainPolyRightEdge = self.__offset_mainPolyRightEdge = ([''] * resolution)

                self.__leftBorderInnerEdge = self.__offset_leftBorderInnerEdge = ([''] * resolution)
                self.__leftBorderOuterEdge = self.__offset_leftBorderOuterEdge = ([''] * resolution)

                self.__rightBorderInnerEdge = self.__offset_rightBorderInnerEdge = ([''] * resolution)
                self.__rightBorderOuterEdge = self.__offset_rightBorderOuterEdge = ([''] * resolution)

            for updateRange in updateRanges: #Calculates the track edges from the update range above
                for point in range(*updateRange):
                    self.__mainPolyLeftEdge[point] = calculateSide(self.splinePoints, point, 5)
                    self.__mainPolyRightEdge[point] = calculateSide(self.splinePoints, point, -5)

                    self.__leftBorderInnerEdge[point] = calculateSide(self.splinePoints, point, (self.width * (1 / self.scale)))
                    self.__leftBorderOuterEdge[point] = calculateSide(self.splinePoints, point, (self.width * (1 / self.scale)) + 3)

                    self.__rightBorderInnerEdge[point] = calculateSide(self.splinePoints, point, -(self.width * (1 / self.scale)))
                    self.__rightBorderOuterEdge[point] = calculateSide(self.splinePoints, point, -((self.width * (1 / self.scale)) + 3))

    def computeRacingLine(self):
        racingLine = []
        racingLineControlPoints = []

        self.leftRacingLineSpline = []
        self.rightRacingLineSpline = []
        self.offset_leftRacingLineSpline = []
        self.offset_rightRacingLineSpline = []

        if len(self.points) >= 3:
            pointCoords = self.returnPointCoords()
            numOfSegs = len(pointCoords) - 1

            #Gets the direction of the track at each control point
            if self.closed:
                controlPointDirection = []
                pointCoords = pointCoords[:-1]
                for controlPIndex in range(len(pointCoords)):
                    controlPointDirection.append(trackDir(pointCoords[(controlPIndex - 1) % len(pointCoords)], pointCoords[controlPIndex], pointCoords[(controlPIndex + 1) % len(pointCoords)]))
                pointCoords = self.returnPointCoords()
            else:
                controlPointDirection = [0]
                for controlPIndex in range(1, numOfSegs):
                    controlPointDirection.append(trackDir(pointCoords[controlPIndex - 1], pointCoords[controlPIndex], pointCoords[controlPIndex + 1]))

            #Produces a late turn for corners
            if self.closed:
                for controlPDir in range(len(controlPointDirection)):
                    pointDirections = [controlPointDirection[controlPDir], controlPointDirection[(controlPDir + 1) % len(controlPointDirection)], controlPointDirection[(controlPDir + 2) % len(controlPointDirection)]]
                    largeCurve = all([abs(point) >= self.slightBendLimit for point in pointDirections]) and sameSign(pointDirections) and (not sameSign([controlPointDirection[(controlPDir + 2) % len(controlPointDirection)], controlPointDirection[(controlPDir + 3) % len(controlPointDirection)]]))
                    if largeCurve:
                        controlPointDirection[controlPDir] *= -1
            else:
                controlPointDirection.append(0)
                for controlPDir in range(1, len(controlPointDirection) - 1):
                    if 2 <= controlPDir <= len(controlPointDirection) - 3:
                        pointDirections = [controlPointDirection[controlPDir], controlPointDirection[(controlPDir + 1) % len(controlPointDirection)], controlPointDirection[(controlPDir + 2) % len(controlPointDirection)]]
                        largeCurve = all([abs(point) >= self.slightBendLimit for point in pointDirections]) and sameSign(pointDirections) and (not sameSign([controlPointDirection[(controlPDir + 2) % len(controlPointDirection)], controlPointDirection[(controlPDir + 3) % len(controlPointDirection)]]))
                        if largeCurve:
                            controlPointDirection[controlPDir] *= -1

            #Produces list of all points on the racing line
            lastDir = 0
            for controlPDirIndex in range(numOfSegs):
                lineEnds = getPaddedLineEnds(self.__leftBorderInnerEdge[controlPDirIndex * self.perSegRes],
                                             self.__rightBorderInnerEdge[controlPDirIndex * self.perSegRes], 10)
                currentDir = controlPointDirection[controlPDirIndex]

                if (currentDir > self.slightBendLimit) or ((-self.slightBendLimit < currentDir < self.slightBendLimit) and lastDir == 1):
                    racingLineControlPoints.append(lineEnds[0])
                    lastDir = 1
                elif (currentDir < -self.slightBendLimit) or ((-self.slightBendLimit < currentDir < self.slightBendLimit) and lastDir == -1):
                    racingLineControlPoints.append(lineEnds[1])
                    lastDir = -1
                else:
                    racingLineControlPoints.append(pointCoords[controlPDirIndex])

            if self.closed:
                racingLineControlPoints.append(racingLineControlPoints[0])
            else:
                racingLineControlPoints.append(pointCoords[-1])

            if self.closed:
                racingLineControlPoints = racingLineControlPoints[-3:-1] + racingLineControlPoints + racingLineControlPoints[1:3]

            #Computes the spline points of the racing line
            resolution = (len(racingLineControlPoints) - 1) * self.perSegRes
            for tInt in range(resolution):
                t = tInt / resolution
                racingLine.append(calculateSpline(racingLineControlPoints, t))

            if self.closed:
                racingLine = racingLine[(2 * self.perSegRes):-(2 * self.perSegRes)]

            for pointIndex in range(len(racingLine)):
                self.leftRacingLineSpline.append(calculateSide(racingLine, pointIndex, -3))
                self.rightRacingLineSpline.append(calculateSide(racingLine, pointIndex, 3))

            self.offset_leftRacingLineSpline = offsetPoints(self.leftRacingLineSpline, self.offsetValue, self.zoomValue)
            self.offset_rightRacingLineSpline = offsetPoints(self.rightRacingLineSpline, self.offsetValue, self.zoomValue)

    #Runs all functions necessary to compute track
    def computeTrack(self, updatePoints = []):
        self.computeSpline(updatePoints = updatePoints)
        self.computeTrackEdges(updatePoints = updatePoints)
        if self.showRacingLine:
            self.computeRacingLine()

        self.offsetAllTrackPoints(updatePoints = updatePoints)

    #Takes the corner angle, and applies a precalculated formula to work out the maximum speed a car can take
    def calculateMaxCorneringSpeed(self, cornerAngle):
        grad = 0.24 + (0.005 * (self.width - 12))
        yInt = 165.3 - (grad * 680)

        maxCorneringSpeed = ((cornerAngle - yInt) / grad)
        return maxCorneringSpeed

    #Returns the index of a point n distance away
    def getIndexFromDistance(self, currentIndex, distance, reverse = False, closed = True):
        totalDistance = 0
        index = currentIndex
        if index is None: return None
        while totalDistance < distance:
            nextIndex = (index + 1) % len(self.splinePoints)
            if not closed and abs(index - nextIndex) > 1:
                return None

            if reverse:
                nextIndex = (index - 1) % len(self.splinePoints)
            totalDistance += pointDistance(self.splinePoints[index], self.splinePoints[nextIndex])
            index = nextIndex
        return index

    #Checks whether track should be closed based off of whether end and start points are at the same positions
    def shouldTrackBeClosed(self):
        pointCoords = self.returnPointCoords()
        closedStatusBefore = self.closed
        if len(self.points) > 0:
            if pointCoords[0] == pointCoords[-1]:
                self.closed = True
                self.computeTrack(updatePoints = [0])
            else:
                closedBefore = self.closed
                self.closed = False
                if closedBefore:
                    self.computeTrack(updatePoints = [0, len(self.points) - 1])

        return [closedStatusBefore, self.closed]

    #Uses a precalculated formula to ensure that when "auto-res" is turned on, the resolution is adjusted so that the track always looks smooth
    def automaticallyAdjustRes(self):
        if len(self.points) >= 3:
            angles = []
            trackPoints = self.returnPointCoords()
            for i in range(1, len(self.points) - 1):
                angles.append(angle(trackPoints[i - 1], trackPoints[i], trackPoints[i + 1]))
            smallestAngle = (180 - (min(angles) - 10)) / 10
            newRes = 10.289 * (math.e ** (0.1238 * smallestAngle))
            self.changeRes(min(max(newRes, 10), 100))

    #Returns a surface, with the rendered track on it.
    def renderToSurface(self, programColours, zoom):
        xPoints = [point[0] for point in self.splinePoints]
        yPoints = [point[1] for point in self.splinePoints]

        width = (max(xPoints) - min(xPoints))
        height = (max(yPoints) - min(yPoints))

        pixelTrackWidth = ((self.width + 5) * (1 / self.scale))
        trackSurface = self.pygame.Surface(((width + pixelTrackWidth) * zoom, (height + pixelTrackWidth) * zoom), self.pygame.SRCALPHA)

        self.zoomValue = zoom
        self.offsetValue = ((-min(xPoints) + (pixelTrackWidth / 2)) * zoom, (-min(yPoints) + (pixelTrackWidth / 2)) * zoom)
        self.offsetAllTrackPoints()
        self.draw(programColours, False, "Display", False, trackSurface)
        return trackSurface, self.offsetValue

    def update(self, mousePosX, mousePosY, zoom, screenWidth, screenHeight, screenBorder, offset, screenRect):
        self.pointsSelected = [[self.points[point], point] for point in range(len(self.points)) if self.points[point].pointSelected]

        #If track is closed, then moving join will select both points. This unselects one of the points
        for point in range(len(self.pointsSelected)):
            if not(point == 0 or (((self.pointsSelected[point][1] == 0) or (self.pointsSelected[point][1] == len(self.points) - 1)) and self.closed)):
                self.pointsSelected[point][0].pointSelected = False

        if self.closed and self.points[0].pointSelected:
            self.points[-1].pointSelected = True

        elif self.closed and self.points[-1].pointSelected:
            self.points[0].pointSelected = True

        self.mouseHovering = None
        for point in self.points:
            if point.mouseHovering: self.mouseHovering = self.points.index(point)

        #Updates control points
        groupMove = False
        for pointIndex in range(len(self.points)):
            point = self.points[pointIndex]
            if screenRect.collidepoint(offsetPoints(point.getPos(), offset, zoom, True)):
                point.update(mousePosX, mousePosY, zoom, screenWidth, screenHeight, screenBorder, self.pygame, offset)

                if (point.posAtClick is not None) and (point.posAtRelease is not None):
                    newPoint = False
                    if len(self.history.undoStack) > 0:
                        newPoint = (self.history.undoStack.peak().command == "ADD POINT") and (self.history.undoStack.peak().params[0] == pointIndex)
                    if (point.posAtClick != point.posAtRelease) and not newPoint:
                        self.history.addAction("MOVE POINT", [pointIndex, point.posAtClick, point.posAtRelease], group = groupMove)
                        self.pointCoords = None
                    self.calculateLength()
                    groupMove = True
                    point.posAtClick = None
                    point.posAtRelease = None

                #Prevents points that are next to each-other from touching
                if point.pointSelected and len(self.points) >= 2:
                    allButOnePoint = self.returnPointCoords(lazy = True)
                    allButOnePoint.pop(pointIndex)
                    nearestPoint, nearestIndex = findNearest(allButOnePoint, point.getPos())
                    if abs(nearestIndex - pointIndex) == 1:
                        distance = pointDistance(nearestPoint, point.getPos())
                        minimumDistance = (self.width * (1 / self.scale))
                        if (distance <= minimumDistance) and distance != 0:
                            point.posX = (nearestPoint[0] + (minimumDistance * (point.posX - nearestPoint[0]) / distance))
                            point.posY = (nearestPoint[1] + (minimumDistance * (point.posY - nearestPoint[1]) / distance))

        #Handles when the end control point and start control point should connect
        if len(self.points) >= 5:
            snapThreshold = 50
            if self.points[0].pointSelected and (-snapThreshold <= self.points[0].posX - self.points[-1].posX <= snapThreshold) and (-snapThreshold <= self.points[0].posY - self.points[-1].posY <= snapThreshold) and not(self.pygame.key.get_mods() & self.pygame.KMOD_LSHIFT):
                self.points[0].posX, self.points[0].posY = self.points[-1].posX, self.points[-1].posY
                self.updateCloseStatus(value = True)

            elif self.points[-1].pointSelected and (-snapThreshold <= self.points[-1].posX - self.points[0].posX <= snapThreshold) and (-snapThreshold <= self.points[-1].posY - self.points[0].posY <= snapThreshold) and not(self.pygame.key.get_mods() & self.pygame.KMOD_LSHIFT):
                self.points[-1].posX, self.points[-1].posY = self.points[0].posX, self.points[0].posY
                self.updateCloseStatus(value = True)

            if (self.points[0].pointSelected or self.points[-1].pointSelected) and (self.pygame.key.get_mods() & self.pygame.KMOD_LSHIFT):
                self.updateCloseStatus(value = False)

        else:
            self.updateCloseStatus(value = False)

        #Updates track
        if len(self.pointsSelected) > 0:
            updatePoints = [point[1] for point in self.pointsSelected]
            self.computeTrack(updatePoints = updatePoints)

        if not self.pygame.mouse.get_pressed()[0] and self.autoRes:
            if self.returnPointCoords() != self.pointList:
                self.pointList = self.returnPointCoords()
                self.automaticallyAdjustRes()

    #Main rendering algorithm for drawing track
    def draw(self, programColours, switchFront, viewMode, antialiasing, surface = None):
        if surface is None:
            surface = self.screen

        if len(self.points) >= 2:
            if viewMode in ["Track", "Skeleton", "Display"]: #Draws outer track edge
                for point in range(len(self.points) - 1):
                    leftTrackEdgePolygon = formPolygon(self.__offset_leftBorderInnerEdge, self.__offset_leftBorderOuterEdge, slice((point * self.perSegRes), ((point + 1) * self.perSegRes) + 1), ((point == len(self.points) - 2) and self.closed))
                    rightTrackEdgePolygon = formPolygon(self.__offset_rightBorderInnerEdge, self.__offset_rightBorderOuterEdge, slice((point * self.perSegRes), ((point + 1) * self.perSegRes) + 1), ((point == len(self.points) - 2) and self.closed))

                    if antialiasing:
                        self.pygame.gfxdraw.aapolygon(surface, leftTrackEdgePolygon, programColours["white"])
                    self.pygame.gfxdraw.filled_polygon(surface, leftTrackEdgePolygon, programColours["white"])

                    if antialiasing:
                        self.pygame.gfxdraw.aapolygon(surface, rightTrackEdgePolygon, programColours["white"])
                    self.pygame.gfxdraw.filled_polygon(surface, rightTrackEdgePolygon, programColours["white"])

            if viewMode in ["Track", "Display"]: #Draws filled-in part of track
                for point in range(len(self.points) - 1):
                    mainTrackPolygon = formPolygon(self.__offset_leftBorderInnerEdge, self.__offset_rightBorderInnerEdge, slice((point * self.perSegRes), ((point + 1) * self.perSegRes) + 1), ((point == len(self.points) - 2) and self.closed))

                    if antialiasing:
                        self.pygame.gfxdraw.aapolygon(surface, mainTrackPolygon, programColours["track"])
                    self.pygame.gfxdraw.filled_polygon(surface, mainTrackPolygon, programColours["track"])

            if viewMode in ["Track", "Skeleton", "Curve"]: #Draws the main track curve
                for point in range(len(self.points) - 1):
                    mainCurvePolygon = formPolygon(self.__offset_mainPolyLeftEdge, self.__offset_mainPolyRightEdge, slice((point * self.perSegRes), ((point + 1) * self.perSegRes) + 1), ((point == len(self.points) - 2) and self.closed))

                    if antialiasing:
                        self.pygame.gfxdraw.aapolygon(surface, mainCurvePolygon, programColours["curve"])
                    self.pygame.gfxdraw.filled_polygon(surface, mainCurvePolygon, programColours["curve"])

            if viewMode in ["Display"]: #Draws the checkered finish line
                checkeredHeight = (1 * self.zoomValue * (1 / self.scale))
                checkeredWidthCount = round((self.width * (1 / self.scale) * self.zoomValue) / checkeredHeight)
                checkeredWidth = (self.width * (1 / self.scale) * self.zoomValue) / checkeredWidthCount
                checkeredHeight = checkeredWidth

                startPos, startAngle, startIndex, startDir = self.getStartPos()

                if self.finishDir:
                    startLeftCoord = int(self.__offset_leftBorderInnerEdge[startIndex][0]), int(
                        self.__offset_leftBorderInnerEdge[startIndex][1])
                else:
                    startLeftCoord = int(self.__offset_rightBorderInnerEdge[startIndex][0]), int(
                        self.__offset_rightBorderInnerEdge[startIndex][1])

                for y in range(-1, 1):
                    for x in range(checkeredWidthCount):
                        topLeft = startLeftCoord[0] - (cosDeg(startAngle) * (checkeredHeight * y)) - (
                                sinDeg(startAngle) * (checkeredWidth * x)), startLeftCoord[1] + (
                                          sinDeg(startAngle) * (checkeredHeight * y)) - (
                                          cosDeg(startAngle) * (checkeredWidth * x))

                        corner1 = topLeft
                        corner2 = topLeft[0] - (cosDeg(startAngle) * checkeredHeight), topLeft[1] + (
                                sinDeg(startAngle) * checkeredHeight)
                        corner3 = topLeft[0] - (cosDeg(startAngle) * checkeredHeight) - (
                                sinDeg(startAngle) * checkeredWidth), topLeft[1] + (
                                          sinDeg(startAngle) * checkeredHeight) - (cosDeg(startAngle) * checkeredWidth)
                        corner4 = topLeft[0] - (sinDeg(startAngle) * checkeredWidth), topLeft[1] - (
                                cosDeg(startAngle) * checkeredWidth)

                        if (x + y) % 2 == 0:
                            checkeredColour = (0, 0, 0)
                        else:
                            checkeredColour = (200, 200, 200)

                        checkeredSquarePoints = [corner1, corner2, corner3, corner4]
                        self.pygame.draw.polygon(surface, checkeredColour, checkeredSquarePoints)

            if viewMode in ["Spline Dots"]: #Draws spline dots
                for dot in self.__offset_splinePoints:
                    if antialiasing:
                        self.pygame.gfxdraw.aacircle(surface, int(dot[0]), int(dot[1]), 4, programColours["curve"])
                    self.pygame.gfxdraw.filled_circle(surface, int(dot[0]), int(dot[1]), 4, programColours["curve"])

        if viewMode in ["Track", "Skeleton", "Curve", "Spline Dots"]: #Draws the control points
            for pointIndex in range(len(self.points)):
                point = self.points[pointIndex]

                if (not switchFront and pointIndex == len(self.points) - 1) or (switchFront and pointIndex == 0) or (self.closed and ((pointIndex == 0) or (pointIndex == len(self.points) - 1))):
                    colour = programColours["frontControlPoint"]
                else:
                    colour = programColours["controlPoint"]

                point.draw(colour, surface, self.pygame, self.offsetValue, self.zoomValue)

        if self.lastRacingLine is not self.showRacingLine:
            self.computeRacingLine()
            self.lastRacingLine = self.showRacingLine

        #Draw racing line
        if len(self.points) >= 3 and self.showRacingLine:
            racingLinePolygon = formPolygon(self.offset_leftRacingLineSpline, self.offset_rightRacingLineSpline, close = self.closed)
            if antialiasing:
                self.pygame.gfxdraw.aapolygon(surface, racingLinePolygon, (140, 32, 32))
            self.pygame.gfxdraw.filled_polygon(surface, racingLinePolygon, (140, 32, 32))

        curbCoords = [self.splinePoints[i] for i in self.curbPoints]
        offsetCurbPoints = offsetPoints(curbCoords, self.offsetValue, self.zoomValue)
        for i in offsetCurbPoints:
            self.pygame.draw.circle(self.screen, (200, 0, 0), i, 3)
