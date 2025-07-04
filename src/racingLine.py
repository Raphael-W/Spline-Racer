from utils import *
class RacingLine:
    def __init__(self, track, car):
        self.track = track
        self.car = car

    def splitIntoPoints(self, splinePosition, pointCount, speed):
        points = []
        edgePoints = self.track.getEdgePoints()
        leftSide = edgePoints[0][splinePosition]
        rightSide = edgePoints[1][splinePosition]

        for i in range(pointCount + 1):
            x = ((rightSide[0] - leftSide[0]) * (i / pointCount)) + leftSide[0]
            y = (rightSide[1] - leftSide[1]) * (i / pointCount) + leftSide[1]
            points.append([x, y, speed])

        return points

    def create3DGridOnTrack(self, maxSpeed):
        gridReference = []

        speedIntervals = maxSpeed / 10
        for speedIndex in range(1, 10):
            speed = speedIndex * speedIntervals
            for splinePoint in range(0, len(self.track.splinePoints), 1):
                rawPoints = self.splitIntoPoints(splinePoint, 5, speed)
                gridReference.append(rawPoints)
        return gridReference

    def rotationValid(self, pointBefore, pointNow, pointNext):
        averageSpeed = (pointNow[2] + pointNext[2]) / 2
        facingAngle = angle(pointBefore[:2], pointNow[:2], pointNext[:2])
        turningRadius = (self.car.wheelBase / math.sin(self.car.maxTurningAngle * (1 / 6)) + ((averageSpeed / 10) ** 1.5))

        x = pointNow[0] + (-turningRadius * cosDeg(90 - facingAngle))
        y = pointNow[1] + (-turningRadius * sinDeg(90 - facingAngle))
        pointOfRotation = (x, y)

        return pointDistance(pointNext[:2], pointOfRotation) >= turningRadius

    def accelerationValid(self, pointNow, pointNext):
        distance = pointDistance(pointNow[:2], pointNext[:2])
        acceleration = abs(((pointNext[2] ** 2) - (pointNow[2] ** 2)) / (2 * distance)) #SUVAT
        return acceleration <= self.car.maxAcceleration

    def calculateTimeBetweenPoints(self, pointBefore, pointNow, pointNext):
        isRotationValid = self.rotationValid(pointBefore, pointNow, pointNext)
        isAccelerationValid = self.accelerationValid(pointNow, pointNext)
        validMove = isRotationValid and isAccelerationValid

        if validMove:
            distance = pointDistance(pointNow[:2], pointNext[:2])
            timeTaken = distance / (0.5 * (pointNow[2] + pointNext[2])) #SUVAT
            return timeTaken

        return 1000000000000000 #Very big number

    def calculateRacingLine(self):
        gridReference = self.create3DGridOnTrack(self.car.maxSpeed)
        startPoint = []
