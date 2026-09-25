class TrackRacing(Scene):
    def __init__(self, screen, trackEditor):
        super().__init__(screen)

        self.name = "Racing"

        self.trackEditor = trackEditor
        self.track = self.trackEditor.track

        self.screenBorder = 5
        self.uniquenessToken = None
        self.previousTrackUUID = None

        self.offsetPosition = (0, 0)
        self.zoom = 2
        self.upperZoomLimit = 3
        self.lowerZoomLimit = 0.5

        self.screenWidth, self.screenHeight = screen.get_size()
        self.mousePosX = 0
        self.mousePosY = 0

        self.events = []

        self.deltaTime = 0

        self.steeringInput = [0, 0]
        self.accelerationInput = [0, 0]

        self.colours = {"background"  : (101, 126, 51),
                        "controlPoint": (24, 150, 204),
                        "white"       : (200, 200, 200),
                        "track"       : (100, 100, 100)}

        self.mainFont = directories["mainFont"]

        self.UILayer = Layer(screen, pygame, mainFont, directories)

        self.speedometer = Label(self.UILayer, 30, (180, 100), "SE", "121mph", self.colours["white"], bold = True)
        self.timer = Label(self.UILayer, 17, (180, 65), "SE", "00:00.00", self.colours["white"])
        self.ranking = Label(self.UILayer, 17, (180, 45), "SE", "1st", self.colours["white"], show = False)

        self.speedometer2 = Label(self.UILayer, 30, (180, 100), "SW", "121mph", self.colours["white"], bold = True)
        self.timer2 = Label(self.UILayer, 17, (180, 65), "SW", "00:00.00", self.colours["white"])
        self.ranking2 = Label(self.UILayer, 17, (180, 45), "SH", "2nd", self.colours["white"], show = False)

        self.racePos = Label(self.UILayer, 30, (0, 80), "NW", "1st", (215, 183, 64), True)

        self.slowSign = pygame.Surface((150, 50), pygame.SRCALPHA)
        pygame.draw.rect(self.slowSign, (130, 0, 0), (0, 0, 150, 50))
        font = pygame.freetype.Font(directories["mainFont"], 30)
        font.strong = True
        textSize = font.get_rect("SLOW!")
        font.render_to(self.slowSign, ((150 // 2) - (textSize.width // 2), (50 // 2) - (textSize.height // 2)), "SLOW!",
                       self.colours["white"])

        #Settings accordion
        self.viewLeaderboardButton = Button(self.UILayer, (90, 310), "SW", (200, 40), "View Leaderboard", 15,
                                            (100, 100, 100), action = self.viewLeaderboard)
        self.leaderboardView = None

        self.viewControlsButton = Button(self.UILayer, (90, 260), "SW", (200, 40), "View Controls", 15, (100, 100, 100),
                                         action = self.viewControls)
        self.controlsView = None

        self.deleteRaceTimesButton = Button(self.UILayer, (105, 335), "SE", (30, 30), "", 12, (66, 41, 41),
                                            action = self.deleteRaceTimes, show = False)
        self.deleteRaceTimesIcon = Image(self.UILayer,
                                         (self.deleteRaceTimesButton.posX - 1, self.deleteRaceTimesButton.posY - 1),
                                         "SE", directories["bin"], 0.7, colour = self.colours["white"], show = False)

        self.zoomAdjustmentSlider = Slider(self.UILayer, 15, self.colours["white"], self.colours["controlPoint"],
                                           (140, 190), "SW", 1, 105, (self.lowerZoomLimit, self.upperZoomLimit), 2.0001,
                                           precision = 1, increment = 0.1, action = self.updateZoom, suffix = 'x',
                                           finishedUpdatingAction = lambda x = None,
                                                                           y = None: self.updateUserPreferences())
        self.zoomAdjustmentLabel = Label(self.UILayer, 15, (80, 192), "SW", "Zoom", self.colours["white"])

        self.multiplayerSwitch = Switch(self.UILayer, (250, 160), "SW", 0.8, value = False,
                                        action = self.toggleMultiplayer)
        self.multiplayerLabel = Label(self.UILayer, 15, (98, 158), "SW", "Split-screen", self.colours["white"])
        self.multiplayerSwitch.trueColour = (38, 87, 38)

        self.speedWarningSwitch = Switch(self.UILayer, (250, 130), "SW", 0.8, value = False,
                                         action = self.toggleSpeedWarnings)
        self.speedWarningLabel = Label(self.UILayer, 15, (80, 128), "SW", "Speed Warnings", self.colours["white"])
        self.speedWarningSwitch.trueColour = (38, 87, 38)

        self.racingLineSwitch = Switch(self.UILayer, (250, 100), "SW", 0.8, value = False,
                                       action = self.toggleRacingLine)
        self.racingLineLabel = Label(self.UILayer, 15, (107, 98), "SW", "Racing Line", self.colours["white"])
        self.racingLineSwitch.trueColour = (38, 87, 38)

        self.settingsAccordion = Accordion(self.UILayer, (50, 50), "SW", (280, 325), "Settings",
                                           [self.viewLeaderboardButton, self.viewControlsButton,
                                            self.zoomAdjustmentSlider,
                                            self.zoomAdjustmentLabel, self.multiplayerSwitch, self.multiplayerLabel,
                                            self.speedWarningSwitch,
                                            self.speedWarningLabel, self.racingLineSwitch, self.racingLineLabel],
                                           openDir = "r")

        #Controls page keys
        self.controlsKeyW = KeyboardKeyIcon(self.UILayer, (0, 120), "vh", "W", show = False)
        self.controlsKeyA = KeyboardKeyIcon(self.UILayer, (32, 88), "vh", "A", show = False)
        self.controlsKeyS = KeyboardKeyIcon(self.UILayer, (0, 88), "vh", "S", show = False)
        self.controlsKeyD = KeyboardKeyIcon(self.UILayer, (-32, 88), "vh", "D", show = False)

        self.orLabel = Label(self.UILayer, 15, (-80, 98), "vh", "OR", self.colours["white"], bold = True, show = False)

        self.controlsKeyUp = KeyboardKeyIcon(self.UILayer, (-150, 120), "vh", "↑", show = False)
        self.controlsKeyLeft = KeyboardKeyIcon(self.UILayer, (-118, 88), "vh", "←", show = False)
        self.controlsKeyDown = KeyboardKeyIcon(self.UILayer, (-150, 88), "vh", "↓", show = False)
        self.controlsKeyRight = KeyboardKeyIcon(self.UILayer, (-182, 88), "vh", "→", show = False)

        self.controlsKeyR = KeyboardKeyIcon(self.UILayer, (0, 26), "vh", "R", show = False)
        self.controlsKeyP = KeyboardKeyIcon(self.UILayer, (0, -24), "vh", "P", show = False)
        self.controlsKeyL = KeyboardKeyIcon(self.UILayer, (0, -74), "vh", "L", show = False)
        self.controlsKeyC = KeyboardKeyIcon(self.UILayer, (0, -124), "vh", "C", show = False)

        self.movementLabel = Label(self.UILayer, 20, (169, 90), "vh", "Movement:", self.colours["white"], show = False)
        self.resetLabel = Label(self.UILayer, 20, (133, 20), "vh", "Reset:", self.colours["white"], show = False)
        self.pauseLabel = Label(self.UILayer, 20, (133, -30), "vh", "Pause:", self.colours["white"], show = False)
        self.viewLeaderboardLabel = Label(self.UILayer, 20, (205, -80), "vh", "Leaderboard:", self.colours["white"],
                                          show = False)
        self.viewControlsLabel = Label(self.UILayer, 20, (169, -130), "vh", "Controls:", self.colours["white"],
                                       show = False)

        self.controlsUI = [self.controlsKeyW, self.controlsKeyA, self.controlsKeyS, self.controlsKeyD,
                           self.controlsKeyUp, self.controlsKeyLeft, self.controlsKeyDown, self.controlsKeyRight,
                           self.controlsKeyP, self.controlsKeyL, self.controlsKeyR, self.controlsKeyC,
                           self.orLabel, self.movementLabel, self.resetLabel, self.pauseLabel,
                           self.viewLeaderboardLabel, self.viewControlsLabel]

        self.car = Car(pygame, screen, directories, self.trackEditor.track)
        self.car2 = Car(pygame, screen, directories, self.trackEditor.track)
        self.speedWarnings = False

        self.pauseImg = Image(self.UILayer, (13, 13), "vh", directories["pause"], 5, self.colours["white"], False)
        self.pause = False
        self.pauseStart = None
        self.userPaused = False
        self.lastStartTimeCar = None
        self.lastStartTimeCar2 = None

        self.minimapPoints = []
        self.miniMapSurface = pygame.Surface((0, 0))
        self.miniMapScale = 0
        self.topLeftCornerMiniMap = (0, 0)
        self.miniMapThickness = 0
        self.miniMapHeightOffset = 0

        self.splitScreen = False
        self.winner = self.car

        self.trackSurface = pygame.Surface((0, 0))
        self.originOffset = (0, 0)

    def updateUserPreferences(self):
        with open(directories["preferences"]) as loadFile:
            preferenceData = json.load(loadFile)

        preferenceData["racingZoom"] = self.zoom
        preferenceData["racingLine"] = self.racingLineSwitch.value
        preferenceData["speedWarnings"] = self.speedWarningSwitch.value

        with open(directories["preferences"], "w") as outputFile:
            json.dump(preferenceData, outputFile, indent = 4)

    def getUserPreferences(self):
        with open(directories["preferences"]) as loadFile:
            preferenceData = json.load(loadFile)
            self.zoomAdjustmentSlider.set_value(preferenceData["racingZoom"])
            self.racingLineSwitch.set_value(preferenceData["racingLine"])
            self.speedWarningSwitch.set_value(preferenceData["speedWarnings"])

    #Changes the zoom value
    def updateZoom(self, value):
        self.zoom = round(value, 1)
        self.reloadTrackSurface()

    #Called when the track is changed, re-renders the track
    def reloadTrackSurface(self):
        self.track.showRacingLine = self.racingLineSwitch.value
        self.trackSurface, self.originOffset = self.track.render_to_surface(self.colours)

    #Resets the position of the cars back to the start line
    def reset(self):
        self.car.reset(2 * int(self.splitScreen))
        self.car2.reset(-2 * int(self.splitScreen))
        self.offsetPosition = ((-self.car.position.x * self.zoom) + (self.screenWidth / 2),
                               (-self.car.position.y * self.zoom) + (self.screenHeight / 2))

        self.car.dead = False
        self.timer.text = secondToRaceTimer(0)
        self.timer.color = self.colours["white"]
        self.ranking.show = False

        self.timer2.text = secondToRaceTimer(0)
        self.timer2.color = self.colours["white"]
        self.ranking2.show = False

    #Deletes the race times for the currently open track
    def deleteRaceTimes(self):
        def delete():
            deleteTrackTimes(self.track.UUID)
            self.viewLeaderboard()

        def cancel():
            self.viewLeaderboard()

        self.leaderboardView.remove()
        self.deleteRaceTimesButton.show = False
        self.deleteRaceTimesIcon.show = False

        Message(self.UILayer, "Sure?", "You are about to delete the race times for this track", "Cancel", cancel,
                "grey", "Delete", delete, "red")

    #Upload a new race time to the currently open track
    def uploadTime(self, raceTime):
        conn = sqlite3.connect(directories["raceTimes"])
        cursor = conn.cursor()
        cursor.execute(f'''INSERT INTO TIMES VALUES ('{self.track.UUID}', {raceTime}, datetime('now','localtime'))''')
        conn.commit()
        conn.remove()

    #Returns what ranking (e.g. 1st, 3rd, 54th) a race time is, and returns the corresponding color (e.g. gold for first)
    def getRaceTimeRanking(self, raceTime):
        firstColour = (191, 161, 0)  #Gold
        secondColour = (160, 160, 160)  #Silver
        thirdColour = (205, 127, 50)  #Bronze
        otherColour = self.colours["white"]  #White

        allTimes = self.getTimes(self.track.UUID, excludeDate = True)
        ranking = allTimes.index(raceTime) + 1
        suffix = "th"
        onesNumbers = str(ranking)[-1]
        tensNumbers = str(ranking)[-2:]
        if onesNumbers == "1" and tensNumbers != "11":
            suffix = "st"
        elif onesNumbers == "2" and tensNumbers != "12":
            suffix = "nd"
        elif onesNumbers == "3" and tensNumbers != "13":
            suffix = "rd"

        if ranking == 1:
            colour = firstColour
        elif ranking == 2:
            colour = secondColour
        elif ranking == 3:
            colour = thirdColour
        else:
            colour = otherColour

        return f"{ranking}{suffix}", colour

    #Fetches the race times for the currently open track
    def getTimes(self, UUID, excludeDate = False):
        conn = sqlite3.connect(directories["raceTimes"])
        cursor = conn.cursor()
        if excludeDate:
            cursor.execute(f"SELECT time FROM TIMES WHERE TrackUUID = '{UUID}' ORDER BY time")
            times = [timeTuple[0] for timeTuple in cursor.fetchall()]
        else:
            cursor.execute(f"SELECT time, date FROM TIMES WHERE TrackUUID = '{UUID}' ORDER BY time, date")
            times = cursor.fetchall()
        return times

    def toggleMultiplayer(self, value):
        self.splitScreen = value
        self.reset()

    def toggleSpeedWarnings(self, value):
        self.speedWarnings = value
        self.updateUserPreferences()

    def toggleRacingLine(self, value):
        self.track.showRacingLine = value
        self.updateUserPreferences()
        self.reloadTrackSurface()

    def closeLeaderboard(self):
        self.deleteRaceTimesButton.show = False
        self.deleteRaceTimesIcon.show = False
        self.leaderboardView.remove()

    def viewLeaderboard(self):
        if self.controlsView in self.UILayer.elements:  #Closes controls view if opened
            self.closeControls()

        if self.leaderboardView in self.UILayer.elements:  #Closes leaderboard view if already opened
            self.closeLeaderboard()
        else:
            times = self.getTimes(self.track.UUID)

            leaderboardMessages = []
            if len(times) == 0:
                leaderboardMessages = ['', '', '', '', 'No times yet...']
            else:
                for i in range(10):
                    if len(times) > i:
                        splitDate = (times[i][1].split(' ')[0]).split('-')
                        date = f"{splitDate[2]}/{splitDate[1]}/{splitDate[0][-2:]}"
                        number = "{:>2}".format(i + 1)
                        lineText = f"{number}.  {secondToRaceTimer(times[i][0])}     {date}"
                        leaderboardMessages.append(lineText)
                    else:
                        number = "{:>2}".format(i + 1)
                        formattedNumber = "{:<16}".format(f"{number}.")
                        lineText = f"{formattedNumber}-          "
                        leaderboardMessages.append(lineText)

            self.leaderboardView = Message(self.UILayer, "Leaderboard", leaderboardMessages, dimensions = (400, 270),
                                           closeAction = self.closeLeaderboard, layerIndex = 0)
            if len(times) > 0:
                self.deleteRaceTimesButton.show = True
                self.deleteRaceTimesIcon.show = True

    def closeControls(self):
        for element in self.controlsUI:
            element.show = False
        self.controlsView.remove()

    def viewControls(self):
        if self.leaderboardView in self.UILayer.elements:  #Closes leaderboard view if opened
            self.closeLeaderboard()

        if self.controlsView in self.UILayer.elements:  #Closes controls view if already opened
            self.closeControls()
        else:
            for element in self.controlsUI:
                element.show = True

            self.controlsView = Message(self.UILayer, "Controls", "", dimensions = (500, 370), layerIndex = 0,
                                        closeAction = self.closeControls)

    #Pauses and un-pauses the timer
    def setPause(self, newValue = None, userPaused = False):
        if newValue is None:
            self.pause = not self.pause
        else:
            self.pause = newValue

        if self.pause:
            self.userPaused = userPaused
            self.pauseStart = time.time()
        else:
            for car in [self.car, self.car2]:
                if car.timerStart is not None and car.timerEnd is None:
                    car.timerStart += (time.time() - self.pauseStart)

            self.pauseStart = None

    #Called if track changes, used to update what control_points make up the minimap.
    #This includes scaling the control_points so that the minimap always remains the same size
    def updateMiniMapPoints(self, width, height, thickness):
        self.miniMapThickness = thickness
        self.miniMapSurface = pygame.Surface((width, height), pygame.SRCALPHA)
        trackPoints = self.track.spline
        xPoints = [point[0] for point in trackPoints]
        yPoints = [point[1] for point in trackPoints]
        self.topLeftCornerMiniMap = (min(xPoints), min(yPoints))

        trackWidth = max(xPoints) - min(xPoints)
        trackHeight = max(yPoints) - min(yPoints)

        if (width / trackWidth) < (height / trackHeight):
            self.miniMapScale = ((width - (thickness * 2)) / trackWidth)
        else:
            self.miniMapScale = ((height - (thickness * 2)) / trackHeight)

        self.miniMapHeightOffset = height - (trackHeight * self.miniMapScale)

        self.minimapPoints = []
        for point in trackPoints:
            newPosition = (((point[0] - self.topLeftCornerMiniMap[0]) * self.miniMapScale) + thickness, ((point[1] -
                                                                                                          self.topLeftCornerMiniMap[
                                                                                                              1]) * self.miniMapScale) - thickness + self.miniMapHeightOffset)
            self.minimapPoints.append(newPosition)

        leftSide = []
        rightSide = []
        for pIndex in range(len(self.minimapPoints)):
            leftSide.append(calculateSide(self.minimapPoints, pIndex, -(thickness / 2)))
            rightSide.append(calculateSide(self.minimapPoints, pIndex, (thickness / 2)))

        polygon = formPolygon(leftSide, rightSide, close = self.track.closed)

        pygame.draw.aalines(self.miniMapSurface, self.colours["white"], self.track.closed, leftSide)
        pygame.draw.aalines(self.miniMapSurface, self.colours["white"], self.track.closed, rightSide)
        pygame.draw.polygon(self.miniMapSurface, self.colours["white"], polygon)

    def displayMiniMap(self, pos, positions):
        actualX = self.screenWidth - pos[0]
        actualY = self.screenHeight - pos[1]
        miniMapWithCarSurface = self.miniMapSurface.copy()
        colours = [(0, 0, 200), (200, 0, 0)]
        for car in range(len(positions)):
            carPos = (((positions[car][0] - self.topLeftCornerMiniMap[0]) * self.miniMapScale) + self.miniMapThickness,
                      ((positions[car][1] - self.topLeftCornerMiniMap[
                          1]) * self.miniMapScale) - self.miniMapThickness + self.miniMapHeightOffset)
            pygame.gfxdraw.aacircle(miniMapWithCarSurface, int(carPos[0]), int(carPos[1]), 4, colours[car % 2])
            pygame.gfxdraw.filled_circle(miniMapWithCarSurface, int(carPos[0]), int(carPos[1]), 4, colours[car % 2])

        screen.blit(miniMapWithCarSurface, (actualX, actualY))

    #Where all the events are passed to be processed
    def handleEvents(self, events):
        global running

        self.accelerationInput = 0
        self.steeringInput = 0

        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_RIGHT] or keys[pygame.K_LEFT] or keys[
            pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]:
            self.accelerationInput = [0, 0]
            self.steeringInput = [0, 0]

        self.accelerationInput = [int(keys[pygame.K_UP]) - int(keys[pygame.K_DOWN]),
                                  int(keys[pygame.K_w]) - 2 * int(keys[pygame.K_s])]
        self.steeringInput = [int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT]),
                              int(keys[pygame.K_d]) - int(keys[pygame.K_a])]

        if bool(keys[pygame.K_DOWN]):
            self.accelerationInput[0] = -1
        if bool(keys[pygame.K_s]):
            self.accelerationInput[1] = -1

        self.events = events
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    if (self.accelerationInput[0] + self.accelerationInput[1] == 0) or not self.splitScreen:
                        self.reset()
                if event.key == pygame.K_p:
                    self.setPause(userPaused = True)
                if event.key == pygame.K_l:
                    self.viewLeaderboard()
                if event.key == pygame.K_c:
                    self.viewControls()

            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    self.zoomAdjustmentSlider.set_value(
                        float(min(self.upperZoomLimit, max(self.zoom + 0.1, self.lowerZoomLimit))),
                        runFinalAction = True)

                elif event.y < 0:
                    if self.zoom > self.lowerZoomLimit:
                        self.zoomAdjustmentSlider.set_value(
                            float(min(self.upperZoomLimit, max(self.zoom - 0.1, self.lowerZoomLimit))),
                            runFinalAction = True)

    def update(self):
        self.offsetPosition = ((-self.car.position.x * self.zoom) + (self.screenWidth / 2),
                               (-self.car.position.y * self.zoom) + (self.screenHeight / 2))

        self.screenWidth, self.screenHeight = screen.get_size()
        self.mousePosX = pygame.mouse.get_pos()[0]
        self.mousePosY = pygame.mouse.get_pos()[1]

        self.splitScreen = self.multiplayerSwitch.value

        screen.fill(self.colours["background"])

        if self.uniquenessToken != self.track.getUniquenessToken():  #Track has changed
            if len(self.track.control_points) >= 2:
                self.reset()
                self.getUserPreferences()
                self.updateMiniMapPoints(200, 200, 6)

                self.reloadTrackSurface()

            self.uniquenessToken = self.track.getUniquenessToken()
            self.previousTrackUUID = self.track.UUID

        #If the start-timer has started for either of the cars, minimise the settings.
        if (self.lastStartTimeCar != self.car.timerStart) or (self.lastStartTimeCar2 != self.car2.timerStart):
            if (self.car.timerStart is not None) or (self.car2.timerStart is not None):
                self.settingsAccordion.set_expanded(True)
            else:
                self.settingsAccordion.set_expanded(False)

            self.lastStartTimeCar = self.car.timerStart
            self.lastStartTimeCar2 = self.car2.timerStart

        if self.splitScreen:
            acceleration = self.accelerationInput[0]
            if self.car.timerStart is None and self.accelerationInput[
                1] == 0:  #Stop car1 from moving if car2 hasn't started yet
                acceleration = 0
            self.car.visible_update()

            self.offsetPosition = ((-self.car.position.x * self.zoom) + (1 * (self.screenWidth / 4)),
                                   (-self.car.position.y * self.zoom) + (self.screenHeight / 2))
            rightSide = pygame.Surface(((self.screenWidth / 2), self.screenHeight), pygame.SRCALPHA)
            rightSide.blit(self.trackSurface, (self.offsetPosition[0] - self.originOffset[0],
                                               self.offsetPosition[1] - self.originOffset[1]))

            acceleration = self.accelerationInput[1]
            if self.car2.timerStart is None and self.accelerationInput[
                0] == 0:  #Stop car2 from moving if car1 hasn't started yet
                acceleration = 0
            self.car2.visible_update()

            self.offsetPosition = ((-self.car2.position.x * self.zoom) + (self.screenWidth / 4),
                                   (-self.car2.position.y * self.zoom) + (self.screenHeight / 2))
            leftSide = pygame.Surface(((self.screenWidth / 2), self.screenHeight), pygame.SRCALPHA)
            leftSide.blit(self.trackSurface, (self.offsetPosition[0] - self.originOffset[0],
                                              self.offsetPosition[1] - self.originOffset[1]))

            self.car.draw(,
            self.car2.draw(,

            self.car.draw(,
            self.car2.draw(,

            screen.blit(leftSide, (0, 0))
            screen.blit(rightSide, ((self.screenWidth / 2), 0))

            pygame.draw.line(screen, self.colours["white"], ((self.screenWidth / 2) - 1, 0),
                             ((self.screenWidth / 2) - 1, self.screenHeight), 10)

        else:
            steering = min(self.steeringInput[0] + self.steeringInput[1], 1)
            acceleration = min(self.accelerationInput[0] + self.accelerationInput[1], 1)
            self.car.visible_update()
            self.car2.visible_update()

            self.offsetPosition = ((-self.car.position.x * self.zoom) + (self.screenWidth / 2),
                                   (-self.car.position.y * self.zoom) + (self.screenHeight / 2))
            screen.blit(self.trackSurface,
                        (self.offsetPosition[0] - self.originOffset[0], self.offsetPosition[1] - self.originOffset[1]))
            self.car.draw(,

        def closeMessage():
            self.setPause(newValue = False)

        #Update for each car
        for car in [self.car, self.car2]:
            if car.crossedFinishLine:
                if (car.timerEnd is None) and (car.timerStart is not None) and (not car.offTrack):
                    car.timerEnd = time.time()
                    validTime = not car.dead
                    if validTime:
                        raceTime = float("{:.3f}".format(car.timerEnd - car.timerStart))

                        times = self.getTimes(self.track.UUID)
                        if len(times) > 0:
                            if times[0][0] > raceTime:
                                timeDifference = float("{:.3f}".format(times[0][0] - raceTime))
                                self.setPause(newValue = True, userPaused = True)
                                Message(self.UILayer, "New Highscore!",
                                        f"You beat the current highscore ({secondToRaceTimer(times[0][0])}) by {timeDifference}s",
                                        "Continue", closeMessage, (100, 100, 100), linePadding = 10,
                                        closeAction = closeMessage)

                        self.uploadTime(raceTime)
                        rankText, labelColour = self.getRaceTimeRanking(raceTime)
                        if car is self.car:
                            rankingLabel = self.ranking
                        else:
                            rankingLabel = self.ranking2

                        rankingLabel.text = rankText
                        labelWidth = rankingLabel.textSize[0]
                        rankingLabel.color = labelColour
                        rankingLabel.posX = (136 + (labelWidth / 2))
                        rankingLabel.show = True

        self.speedometer.text = f"{pixToMiles(self.car.velocity.x, self.car.scale)} mph"
        self.speedometer.posX = (self.speedometer.textSize[0] / 2) + (self.timer.posX - (self.timer.textSize[0] / 2))

        self.timer2.posX = (self.screenWidth / 2) - 184
        self.speedometer2.text = f"{pixToMiles(self.car2.velocity.x, self.car2.scale)} mph"
        self.speedometer2.posX = -(self.speedometer2.textSize[0] / 2) + (
                self.timer2.posX + (self.timer2.textSize[0] / 2))

        if self.splitScreen:
            self.speedometer2.show = True
            self.timer2.show = True
            if self.car.timerStart is not None and (not self.car.dead or not self.car2.dead):
                self.racePos.show = True
            else:
                self.racePos.show = False

            #Compares positions of both cars and determines which is winning
            if (self.car.timerStart is not None) and (self.car.timerEnd is None):  #if car is still racing
                startIndex = self.track.getStartPos()[2]
                numOfPoints = len(self.track.spline)
                if self.car.nearestSplineIndex != self.car2.nearestSplineIndex:
                    if self.winner is self.car:
                        aheadCheck = (((self.car2.nearestSplineIndex - startIndex) % numOfPoints) > (
                                (self.car.nearestSplineIndex - startIndex) % numOfPoints))
                        if not self.track.finishDir:
                            aheadCheck = not aheadCheck

                        if (aheadCheck and not self.car2.dead) or self.car.dead:
                            self.winner = self.car2
                    else:
                        aheadCheck = (((self.car.nearestSplineIndex - startIndex) % numOfPoints) > (
                                (self.car2.nearestSplineIndex - startIndex) % numOfPoints))
                        if not self.track.finishDir:
                            aheadCheck = not aheadCheck

                        if (aheadCheck and not self.car.dead) or self.car2.dead:
                            self.winner = self.car

                if self.winner is self.car:
                    self.racePos.posX = (self.screenWidth / 2) + 50
                else:
                    self.racePos.posX = 50

        else:
            self.speedometer2.show = False
            self.timer2.show = False
            self.racePos.show = False

        if not self.pause or (self.pause and self.car.timerEnd is not None):  #Update timer text
            if self.car.timerStart is not None:
                timerEnd = time.time()
                if self.car.timerEnd is not None:
                    timerEnd = self.car.timerEnd
                timerValue = timerEnd - self.car.timerStart
                self.timer.text = secondToRaceTimer(timerValue)

            if (self.car.timerStart is not None) and (self.car.timerEnd is None):
                if self.car.dead:
                    self.timer.color = (200, 0, 0)
                else:
                    self.timer.color = self.colours["white"]

        if self.splitScreen:
            if not self.pause or (self.pause and car.timerEnd is not None):
                if car.timerStart is not None:
                    timerEnd = time.time()
                    if car.timerEnd is not None:
                        timerEnd = car.timerEnd
                    timerValue = timerEnd - car.timerStart
                    self.timer2.text = secondToRaceTimer(timerValue)

                if (car.timerStart is not None) and (car.timerEnd is None):
                    if car.dead:
                        self.timer2.color = (200, 0, 0)
                    else:
                        self.timer2.color = self.colours["white"]

        if self.pause:
            transparentSurface = pygame.Surface((self.screenWidth, self.screenHeight), pygame.SRCALPHA)
            pygame.draw.rect(transparentSurface, (50, 50, 50, 200), (0, 0, self.screenWidth, self.screenHeight))
            screen.blit(transparentSurface, (0, 0))
            self.pauseImg.show = True
        else:
            self.pauseImg.show = False

        if self.deleteRaceTimesButton.show:
            self.deleteRaceTimesButton.posX = (self.screenWidth / 2) + 180
            self.deleteRaceTimesButton.posY = (self.screenHeight / 2) + 120

            self.deleteRaceTimesIcon.posX = self.deleteRaceTimesButton.posX - 1
            self.deleteRaceTimesIcon.posY = self.deleteRaceTimesButton.posY - 1

        carPositions = [self.track.spline[self.car.nearestSplineIndex]]
        if self.splitScreen:
            carPositions.append(self.track.spline[self.car2.nearestSplineIndex])

        self.displayMiniMap((241, 320), carPositions)
        if self.splitScreen:
            self.displayMiniMap(((self.screenWidth / 2) + 241, 320), carPositions[::-1])
        self.UILayer.draw(,

        controlPoints = self.track.control_point_coords()
        if self.track.closed:
            controlPoints = controlPoints[:-1]

        cars = [self.car]
        if self.splitScreen:
            cars = [self.car, self.car2]

        for car in cars:
            if len(controlPoints) >= 3 and self.speedWarnings:
                splinePoints = self.track.spline
                distanceToBreak = ((100 ** 2) - (car.velocity.x ** 2)) / (-2 * car.brakeDeceleration)
                futureIndex = self.track.getIndexFromDistance(car.nearestSplineIndex, 200 + distanceToBreak,
                                                              not self.track.finishDir, self.track.closed)

                if futureIndex is not None:
                    carBearing = bearing(splinePoints[car.nearestSplineIndex],
                                         splinePoints[(car.nearestSplineIndex + 1) % len(splinePoints)])
                    futureBearing = bearing(splinePoints[futureIndex],
                                            splinePoints[(futureIndex + 1) % len(splinePoints)])
                    bearingDifference = abs(futureBearing - carBearing)

                    #If car is going too fast for corner, show slow sign
                    if (self.track.calculateMaxCorneringSpeed(
                        180 - bearingDifference) < car.velocity.x) and not car.offTrack:
                        posX = (self.screenWidth / 2) - 25
                        if self.splitScreen:
                            if car is self.car:
                                posX = (3 * (self.screenWidth / 4)) - 25
                            if car is self.car2:
                                posX = (1 * (self.screenWidth / 4)) - 25

                        screen.blit(self.slowSign, (posX, self.screenHeight - 80))

        self.handleEvents(pygame.event.get())
