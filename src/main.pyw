from pygameUIElements import *
from track import *
from car import *
from updateChecker import *
from utils import *

import json
import math
import sqlite3
import time

from jsonschema import validate

import pygame
import pygame.gfxdraw
import pygame.freetype

from tkinter.filedialog import askopenfilename
import tkinter as tk

import os
import webbrowser

import PIL.Image
from io import BytesIO

if os.name == "nt":
    import ctypes

    appID = 'Raphael-W, Spline-Racer' # Arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appID) #Makes taskbar icon same as window icon (Sets app as "individual app", not linked to python)

pygame.init()
screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE, pygame.SCALED, vsync=1)
clock = pygame.time.Clock()

pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN])

running = True

githubRepoAddress = "https://github.com/Raphael-W/Spline-Racer"

executionDir = os.path.dirname(os.path.dirname(__file__))
directories = {"mainFont": "assets/fonts/MonoFont.ttf",
               "trackSchema": "assets/JSON/trackSchema.json",
               "preferences": "assets/JSON/preferences.json",
               "raceTimes": "databases/raceTimes.db",
               "recentreButton": "assets/icons/aim.png",
               "finishLine": "assets/icons/flag.png",
               "scale": "assets/icons/scale.png",
               "minus": "assets/icons/minus.png",
               "plus": "assets/icons/plus.png",
               "cross": "assets/icons/cross.png",
               "arrow": "assets/icons/arrow.png",
               "undo": "assets/icons/undo.png",
               "redo": "assets/icons/redo.png",
               "down": "assets/icons/down.png",
               "bin": "assets/icons/bin.png",
               "hide": "assets/icons/hide.png",
               "show": "assets/icons/show.png",
               "pause": "assets/icons/pause.png",
               "rename": "assets/icons/rename.png",
               "f1Car": "assets/sprites/f1_car.png",
               "f1Wheel": "assets/sprites/f1_wheel.png",
               "logo": "assets/icons/logo.png",
               "tracks": "tracks/"}

#Makes above relative paths absolute
directories = {item: os.path.normpath(os.path.join(executionDir, directory)) for (item, directory) in directories.items()}

icon = pygame.image.load(directories["logo"])
pygame.display.set_icon(icon)

mainFont = directories["mainFont"]
programUI = Layer(screen, pygame, mainFont, directories)

fpsLabel = Label(programUI, 15, (118, 30), "NE", "", (200, 200, 200))

def deleteTrackTimes(UUID):
    conn = sqlite3.connect(directories["raceTimes"])
    cursor = conn.cursor()
    cursor.execute(f'''DELETE FROM TIMES WHERE TrackUUID = "{UUID}"''')
    conn.commit()
    conn.close()

class Scene:
    def __init__(self):
        self.name = "Scene"

    def update(self):
        screen.fill((20, 20, 20))

    def handleEvents(self, events):
        global running

        #Default scene is able to handle quitting
        for event in events:
            if event.type == pygame.QUIT:
                running = False

class SceneManager:
    def __init__(self):
        self.scenes = []
        self.currentScene = 0

        #Drop-down for selecting different scenes
        self.changeSceneDropdown = Dropdown(programUI, (30, 30), "", (200, 25), self.getSceneNames(), self.currentScene, colour = (80, 80, 80), action = self.setScene)

    def addScene(self, scene, name):
        scene.name = name
        self.scenes.append(scene)
        self.changeSceneDropdown.values = self.getSceneNames()

    def setScene(self, newScene):
        if self.currentScene == 1 and not self.scenes[1].pause:
            self.scenes[1].setPause()
        elif self.currentScene == 0 and self.scenes[1].pause and not self.scenes[1].userPaused:
            self.scenes[1].setPause()

        if isinstance(newScene, str):
            self.currentScene = self.getSceneIndex(newScene)
        else:
            self.currentScene = newScene

        while self.currentScene in self.changeSceneDropdown.disabledIndexes:
            self.currentScene = (self.currentScene + 1) % len(self.scenes)

        self.changeSceneDropdown.index = self.currentScene

    def getSceneIndex(self, name):
        return self.getSceneNames().index(name)

    #Updates just the visible scene, each scene "pauses" when not visible
    def updateCurrentScene(self):
        if len(self.scenes) > 0:
            self.scenes[self.currentScene].update()

    def programUpdate(self):
        if len(self.scenes[self.getSceneIndex("Track Editor")].track.points) <= 1:
            self.changeSceneDropdown.disabledIndexes = [self.getSceneIndex("Racing")]
        else:
            self.changeSceneDropdown.disabledIndexes = []

    #Events are passed from main loop to current scene
    def distributeEvents(self, events):
        global running

        for event in events:
            if event.type == pygame.QUIT:
                trackEditorSceneIndex = self.getSceneIndex("Track Editor")
                if not self.scenes[trackEditorSceneIndex].track.isSaved():
                    self.setScene(0)
                else:
                    running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    nextScene = (self.currentScene + 1) % len(self.scenes)
                    self.setScene(nextScene)

        if len(self.scenes) > 0:
            self.scenes[self.currentScene].handleEvents(events)

    def getSceneNames(self):
        return [scene.name for scene in self.scenes]

class TrackEditor (Scene):
    def __init__(self):
        super().__init__()
        self.screenBorder = 5

        self.offsetPosition = (0, 0)
        self.pivotPos = None
        self.pivotPos = None

        self.zoom = 1
        self.zoomIncrement = 0.05
        self.upperZoomLimit = 2.5
        self.lowerZoomLimit = 0.1

        self.viewMode = "Track"

        self.trackRes = 20
        self.track = Track(self.trackRes, pygame, screen)

        self.screenWidth = self.previousScreenWidth = screen.get_size()[0]
        self.screenHeight = self.previousScreenHeight = screen.get_size()[1]

        self.mousePosX = 0
        self.mousePosY = 0

        self.userSettingScale = False
        self.setScalePoint1 = None
        self.setScalePoint2 = None

        self.userSettingFinish = False
        self.finishIndex = None
        self.finishDir = None

        self.saveDirectory = None
        self.closeCount = 0
        self.newCaption = None
        self.lastCaption = None

        self.referenceImage = None
        self.referenceImageScale = 1
        self.referenceImageRect = None
        self.scaledReferenceImage = None
        self.referenceImageVisibility = True

        self.events = []
        self.UIClick = False

        self.colours = {"background": (20, 20, 20),
                        "curve": (128, 128, 128),
                        "controlPoint": (24, 150, 204),
                        "frontControlPoint": (204, 138, 24),
                        "grid": (27, 27, 27),
                        "white": (200, 200, 200),
                        "track": (100, 100, 100)}

        self.mainFont = directories["mainFont"]

        self.UILayer = Layer(screen, pygame, mainFont, directories)
        self.trackLayer = Layer(screen, pygame, self.mainFont, directories)

        with open(directories["trackSchema"]) as trackSchema:
            self.trackFileSchema = json.load(trackSchema)

        self.mouseXLabel = Label(self.UILayer, 15, (100, 60), "NE", "", self.colours["white"])
        self.mouseYLabel = Label(self.UILayer, 15, (100, 80), "NE", "", self.colours["white"])
        self.scaleLabel = Label(self.UILayer, 15, (127, 100), "NE", "", self.colours["white"])

        # ------------ CONFIG ACCORDION ------------

        self.saveButton = Button(self.UILayer, (330, 522.5), "SE", (123.75, 30), "Save", 12, (100, 100, 100), action = self.saveTrack)
        self.saveAsButton = Button(self.UILayer, (198.75, 522.5), "SE", (123.75, 30), "Save As", 12, (100, 100, 100), action = lambda: self.saveTrack(
            save_as = True))
        self.openTrackButton = Button(self.UILayer, (330, 485), "SE", (123.75, 30), "Open", 12, (100, 100, 100), action = self.openTrack)
        self.newTrackButton = Button(self.UILayer, (198.75, 485), "SE", (123.75, 30), "New", 12, (100, 100, 100), action = self.newTrack)

        self.setFinishButton = Button(self.UILayer, (330, 440), "SE", (80, 60), "Set Finish", 10, (100, 100, 100), (0, -18), action = self.setFinish)
        self.setFinishImage = Image(self.UILayer, (self.setFinishButton.posX - 28, self.setFinishButton.posY - 10), "SE", directories["finishLine"], 1, colour = (30, 30, 30))

        self.setScaleButton = Button(self.UILayer, (242.5, 440), "SE", (80, 60), "Scale Track", 10, (100, 100, 100), (0, -18), action = self.setScale)
        self.scaleImage = Image(self.UILayer, (self.setScaleButton.posX - 28, self.setScaleButton.posY - 10), "SE", directories["scale"], 1, colour = (30, 30, 30))

        self.recentreButton = Button(self.UILayer, (155, 440), "SE", (80, 60), "Recentre", 10, (100, 100, 100), (0, -18), action = self.recentreFrame)
        self.recentreImage = Image(self.UILayer, (self.recentreButton.posX - 27, self.recentreButton.posY - 10), "SE", directories["recentreButton"], 1, colour = (30, 30, 30))

        self.setReferenceImageButton = Button(self.UILayer, (330, 365), "SE", (185, 30), "Set Reference Image", 12, (100, 100, 100), textOffset = (0, -1), action = self.setReferenceImage)

        self.removeReferenceImageButton = Button(self.UILayer, (105, 365), "SE", (30, 30), "", 12, (66, 41, 41), action = self.clearReferenceImage)
        self.removeReferenceImageIcon = Image(self.UILayer, (self.removeReferenceImageButton.posX - 1, self.removeReferenceImageButton.posY - 1), "SE", directories["bin"], 0.7, colour = self.colours["white"])

        self.hideReferenceImageButton = Button(self.UILayer, (140, 365), "SE", (30, 30), "", 12, (100, 100, 100), action = self.toggleReferenceImageVisibility)
        self.hideReferenceImageIcon = Image(self.UILayer, (self.hideReferenceImageButton.posX - 1, self.hideReferenceImageButton.posY - 1), "SE", directories["hide"], 0.7, colour = self.colours["white"])

        self.trackResSlider = Slider(self.UILayer, 15, self.colours["white"], self.colours["controlPoint"], (225, 308), "SE", 1, 100, (10, 100), value = self.track.perSegRes, action = self.track.changeRes, finishedUpdatingAction = self.track.changeResComplete, increment = 1)
        self.trackResLabel = Label(self.UILayer, 15, (330, 313), "SE", "Track Res", self.colours["white"])

        self.trackWidthSlider = Slider(self.UILayer, 15, self.colours["white"], self.colours["controlPoint"], (224, 273), "SE", 1, 100, (10, 30), value = self.track.width, suffix = 'm', action = self.track.changeWidth, finishedUpdatingAction = self.track.changeWidthComplete)
        self.trackWidthLabel = Label(self.UILayer, 15, (295, 278), "SE", "Width", self.colours["white"])

        self.racingLineSwitch = Switch(self.UILayer, (130, 205), "SE", 0.8, value = False)
        self.racingLineLabel = Label(self.UILayer, 15, (290, 203), "SE", "Racing Line", self.colours["white"])

        self.antialiasingSwitch = Switch(self.UILayer, (130, 177), "SE", 0.8, value = False)
        self.antialiasingLabel = Label(self.UILayer, 15, (299, 175), "SE", "Antialiasing", self.colours["white"])

        self.switchEndsSwitch = Switch(self.UILayer, (130, 147), "SE", 0.8, value = False)
        self.switchEndsLabel = Label(self.UILayer, 15, (298, 145), "SE", "Switch Front", self.colours["white"])

        self.autoResSwitch = Switch(self.UILayer, (130, 117), "SE", 0.8, value = False, action = self.setAutoRes)
        self.autoResLabel = Label(self.UILayer, 15, (263, 115), "SE", "Auto Res", self.colours["white"])

        self.undoButton = Button(self.UILayer, (330, 95), "SE", (30, 30), "", 12, (100, 100, 100), action = self.undo)
        self.undoIcon = Image(self.UILayer, (self.undoButton.posX - 2, self.undoButton.posY - 2), "SE", directories["undo"], 0.8, colour = self.colours["white"])

        self.redoButton = Button(self.UILayer, (295, 95), "SE", (30, 30), "", 12, (100, 100, 100), action = self.redo)
        self.redoIcon = Image(self.UILayer, (self.redoButton.posX - 2, self.redoButton.posY - 2), "SE", directories["redo"], 0.8, colour = self.colours["white"])

        self.viewModeDropdown = Dropdown(self.UILayer, (225, 240), "SE", (150, 25),["Track", "Skeleton", "Curve", "Spline Dots"], 0, action = self.setViewMode)
        self.viewModeLabel = Label(self.UILayer, 15, (330, 235), "SE", "View Mode", self.colours["white"])

        self.configAccordion = Accordion(self.UILayer, (50, 50), "SE", (305, 535), "Untitled Track",
                                         [self.saveButton, self.saveAsButton, self.openTrackButton, self.newTrackButton,
                                          self.setFinishButton, self.setFinishImage, self.setScaleButton,
                                          self.scaleImage, self.recentreButton, self.recentreImage,
                                          self.setReferenceImageButton, self.removeReferenceImageButton,
                                          self.removeReferenceImageIcon, self.hideReferenceImageButton,
                                          self.hideReferenceImageIcon,self.trackResSlider,
                                          self.trackResLabel, self.trackWidthSlider, self.trackWidthLabel,
                                          self.viewModeDropdown, self.viewModeLabel, self.racingLineSwitch, self.racingLineLabel,
                                          self.antialiasingSwitch, self.antialiasingLabel, self.switchEndsSwitch,
                                          self.switchEndsLabel, self.autoResSwitch, self.autoResLabel, self.undoButton, self.undoIcon,
                                          self.redoButton, self.redoIcon])

        self.trackScaleLabel = Label(self.UILayer, 15, (180, 30), "S", "", self.colours["white"])
        self.scalingErrorLabel = Label(self.UILayer, 12, (20, 60), "S", "", (227, 65, 50), show = False)

        self.finishIcon = Image(self.trackLayer, (0, 0), "", directories["finishLine"], 1, colour = (self.colours["white"]), show = False)
        self.finishDirIcon = Image(self.trackLayer, (0, 0), "", directories["arrow"], 1, colour = (self.colours["white"]), show = False)

        self.realDistanceTextInput = TextInput(self.UILayer, (20, 120), "S", (180, 50), 15, "Real Distance (m)", "", "m", ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '.'], enterAction = self.completeScaling, show = False)
        self.scalingHelpLabel = Label(self.UILayer, 14, (0, 70), "NW", "Select two points in space, then type their real-world distance. ESC to exit", (150, 150, 150), show = False)
        self.finishHelpLabel = Label(self.UILayer, 14, (0, 70), "NW", "Select a point on the track, then click in the direction the track should go. ESC to exit", (150, 150, 150), show = False)

        self.helpButton = Button(self.UILayer, (240, 30), "NW", (25, 25), "?", 16, (80, 80, 80), action = self.showHelp)
        self.helpWindow = None

        self.getUserPreferences()
        self.userValues = self.returnUserValues()

        self.createDatabase()
        self.checkForDeletedTracks()

        self.checkedForUpdates = False
        self.updateNeeded = False
        self.latestCommitSHA = None

    def showHelp(self):
        if self.helpWindow in self.UILayer.elements:
            self.helpWindow.close()
        else:
            self.helpWindow = Message(self.UILayer, "Help", ["Click to add a point to the end of the track",
                                                         "Clicking on the track will insert a point at that location",
                                                         "Right-click on a point to remove it",
                                                         "Drag points to reposition them as needed",
                                                         "",
                                                         '"Switch Front" changes which end new points are added to',
                                                         '"Auto Res" selects the best resolution for the track',
                                                         '"Racing Line" displays the fastest path around the track',
                                                         'Select "Set Finish" to place the finish line',
                                                         '"Set Scale" scales the track using a real-world distance'], dimensions = (550, 315), messageFontSize = 13, align = "left", lineSpacing = 23)

    #An update has been detected, the user is prompted to update
    def askToUpdate(self):
        def ignoreUpdate():
            with open(directories["preferences"]) as loadFile:
                preferenceData = json.load(loadFile)

            preferenceData["latestCommitSHA"] = self.latestCommitSHA

            with open(directories["preferences"], "w") as outputFile:
                json.dump(preferenceData, outputFile, indent = 4)
        
        Message(self.UILayer, "Update Available", "Download the latest version from GitHub now", "Ignore", ignoreUpdate, "grey", "View", lambda: webbrowser.open(githubRepoAddress), "grey")

    #Determines whether user should be prompted to update (e.g. has the current update already been ignored)
    def setUpdateNeeded(self, sha):
        self.latestCommitSHA = sha
        with open(directories["preferences"]) as loadFile:
            preferenceData = json.load(loadFile)
            savedCommitSHA = preferenceData["latestCommitSHA"]
        if savedCommitSHA != sha:
            self.updateNeeded = True

    def updateUserPreferences(self):
        trackRes = self.track.perSegRes
        if self.autoResSwitch.value:
            trackRes = "auto"

        with open(directories["preferences"]) as loadFile:
            preferenceData = json.load(loadFile)

        preferenceData["trackRes"] = trackRes
        preferenceData["antialiasing"] = self.antialiasingSwitch.value

        with open(directories["preferences"], "w") as outputFile:
            json.dump(preferenceData, outputFile, indent = 4)

    def getUserPreferences(self):
        with open(directories["preferences"]) as loadFile:
            preferenceData = json.load(loadFile)
            if preferenceData["trackRes"] == "auto":
                self.autoResSwitch.updateValue(True)
            else:
                self.trackResSlider.updateValue(preferenceData["trackRes"])

            self.antialiasingSwitch.updateValue(preferenceData["antialiasing"])

    #Returns values used in user preferences
    def returnUserValues(self):
        return [self.trackResSlider.value, self.autoResSwitch.value, self.antialiasingSwitch.value, self.racingLineSwitch.value]

    #Checks (on startup) whether any tracks have been deleted. If so, its leaderboard is deleted
    def checkForDeletedTracks(self):
        def SQLReady(UUID):
            return f'"{UUID}"'

        fileList = []
        tracksDirectory = directories["tracks"]

        for item in os.listdir(tracksDirectory):
            fullDir = os.path.join(tracksDirectory, item)
            isFile = os.path.isfile(fullDir)
            isCorrectExtension = os.path.splitext(fullDir)[1] == ".track"
            isValid = self.validateTrackFile(fullDir)
            if isFile and isCorrectExtension and isValid:
                fileList.append(os.path.join(tracksDirectory, item))

        UUIDlist = []
        for track in fileList:
            with open(track) as loadFile:
                UUIDlist.append(json.load(loadFile)["UUID"])
        SQLUUIDlist = ', '.join(map(SQLReady, UUIDlist))

        conn = sqlite3.connect(directories["raceTimes"])
        cursor = conn.cursor()
        cursor.execute(f'''DELETE FROM TIMES WHERE TrackUUID NOT IN ({SQLUUIDlist})''')
        conn.commit()
        conn.close()

    def createDatabase(self):
        databaseDir = os.path.dirname(directories["raceTimes"])
        if not os.path.exists(databaseDir):
            os.makedirs(databaseDir)
        conn = sqlite3.connect(directories["raceTimes"])
        cursor = conn.cursor()
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS TIMES (TrackUUID TEXT, time REAL, date TEXT)''')
        conn.commit()
        conn.close()

    #Ensures file is a valid track
    def validateTrackFile(self, directory):
        valid = True
        try:
            with open(directory) as loadFile:
                try:
                    trackData = json.load(loadFile)
                    validate(instance = trackData, schema = self.trackFileSchema)
                except:
                    valid = False
        except:
            valid = False

        return valid

    #Fit track to screen, in the middle
    def recentreFrame(self):
        minX = minY = float('inf')
        maxX = maxY = float('-inf')

        if len(self.track.points) >= 1:
            for point in self.track.returnPointCoords():
                if point[0] > maxX:
                    maxX = point[0]
                if point[0] < minX:
                    minX = point[0]

                if point[1] > maxY:
                    maxY = point[1]
                if point[1] < minY:
                    minY = point[1]
        else:
            minX = maxX = minY = maxY = 0

        centreX = (maxX + minX) / 2
        centreY = (maxY + minY) / 2

        zoomPercentage = (max((maxX - minX) / self.screenWidth, (maxY - minY) / self.screenHeight) * 1.05) + 0.3
        self.zoom = 1 / zoomPercentage
        self.zoom = min(max(self.zoom, self.lowerZoomLimit), self.upperZoomLimit)
        if len(self.track.points) == 0:
            self.zoom = 1

        self.offsetPosition = ((((self.screenWidth / self.zoom) / 2) - centreX) * self.zoom, (((self.screenHeight / self.zoom) / 2) - centreY) * self.zoom)
        if self.referenceImage is not None:
            self.scaledReferenceImage = pygame.transform.scale_by(self.referenceImage, (self.zoom * self.referenceImageScale))

    #Sets up variables, ready for scaling
    def setScale(self):
        self.userSettingScale = True
        self.setScalePoint1 = None
        self.setScalePoint2 = None

    #Asks user for actual distance of scale, and sets scale accordingly
    def completeScaling(self, text):
        try:
            actualDistance = float(text)
        except:
            actualDistance = None
            self.scalingErrorLabel.show = True
            self.scalingErrorLabel.text = "Please enter a valid number"

        if actualDistance is not None:
            if actualDistance == 0:
                self.scalingErrorLabel.show = True
                self.scalingErrorLabel.text = "Please enter a number greater than 0"
            else:
                screenDistance = pointDistance(self.setScalePoint1, self.setScalePoint2)
                trackScale = actualDistance / screenDistance
                self.track.scalePoints(trackScale * (1 / self.track.scale))
                self.scaleReferenceImage(trackScale * (1 / self.track.scale))
                self.realDistanceTextInput.show = False
                self.userSettingScale = False
                self.track.calculateLength()
                self.scalingErrorLabel.show = False
                self.track.history.addAction("SET SCALE", [trackScale])

                self.recentreFrame()

    #Sets up variables, ready for scaling
    def setFinish(self):
        self.userSettingFinish = True
        self.finishIndex = None
        self.finishDir = None

    #Sets finish line index
    def completeFinish(self):
        self.track.history.addAction("SET FINISH", [[self.track.finishIndex, self.track.finishDir], [self.finishIndex, self.finishDir]])

        self.track.finishIndex = self.finishIndex
        self.track.finishDir = self.finishDir

        self.userSettingFinish = False

    def setAutoRes(self, value):
        self.track.setAutoRes(value)

    def setViewMode(self, mode):
        self.viewMode = mode

    #Allows user to choose reference image. Image is checked before being placed
    def setReferenceImage(self, imageDirectory = None, userPerformed = True):
        def openImage(directory):
            imageError = validateImageFile(directory)
            if imageError is None:
                if userPerformed:
                    self.track.history.addAction("SET REFERENCE IMAGE", [directory, self.track.referenceImageDir])
                self.track.referenceImageDir = directory
                self.referenceImage = pygame.image.load(directory)

                self.scaleReferenceImage()
                self.referenceImageRect = self.referenceImage.get_rect()

            else:
                Message(self.UILayer, "Invalid File", imageError, "OK", "close", "grey")
        def validateImageFile(directory):
            error = None
            try:
                PIL.Image.open(directory)

            except Exception as errorMessage:
                error = errorMessage

            return error
        def getFileName():
            try:
                root = tk.Tk()
                logo = tk.PhotoImage(file = directories["logo"])
                root.iconphoto(True, logo)

                root.withdraw()
                root.wm_attributes('-topmost', 1)
                imageExtensions = r"*.png *.jpeg *.jpg *.ppm *.gif *.tiff *.bmp"
                fileSelected = askopenfilename(title = "Open Image", filetypes = [("Images", imageExtensions)])
                root.destroy()
                return fileSelected
            except:
                return None

        if imageDirectory is None:
            tempDirectory = getFileName()
            if tempDirectory is None:
                Message(self.UILayer, "Error", "There was a problem setting the reference image", "OK", "close", "grey")
            elif tempDirectory != '':
                validDir = os.path.isfile(tempDirectory)
                if not validDir:
                    Message(self.UILayer, "Invalid File", "Please select a valid file", "OK", "close", "grey")
                else:
                    openImage(tempDirectory)

        else:
            openImage(imageDirectory)

    #Adjust scale of reference image to match scale of track
    def scaleReferenceImage(self, scaleFactor = 1):
        if self.track.referenceImageDir is not None:
            self.referenceImageScale *= scaleFactor
            self.scaledReferenceImage = pygame.transform.scale_by(self.referenceImage, (self.zoom * self.referenceImageScale))

    def toggleReferenceImageVisibility(self):
        self.referenceImageVisibility = not self.referenceImageVisibility
        if self.referenceImageVisibility:
            self.hideReferenceImageIcon.updateImage(directories["hide"])
        else:
            self.hideReferenceImageIcon.updateImage(directories["show"])

    def clearReferenceImage(self):
        self.track.referenceImageDir = None

    #Algorithm to draw make background a grid
    def drawGrid(self, offset, frequency, lineWidth, lineColor):
        columns = math.ceil(self.screenWidth / frequency)
        rows = math.ceil(self.screenHeight / frequency)

        startCol = int(-offset[0] // frequency)
        endCol = startCol + columns
        startRow = int(-offset[1] // frequency)
        endRow = startRow + rows

        for line in range(startCol, endCol + 1):
            x = line * frequency + offset[0]
            pygame.draw.line(screen, lineColor, (x, 0), (x, self.screenHeight), lineWidth)

        for line in range(startRow, endRow + 1):
            y = line * frequency + offset[1]
            pygame.draw.line(screen, lineColor, (0, y), (self.screenWidth, y), lineWidth)

    #Saves track to directory specified by user.
    def saveTrack(self, save_as = False, postSaveAction = None):
        trackData = self.track.getSaveState()
        trackData["properties"]["referenceImageScale"] = self.referenceImageScale

        def saveToFile(receivedName):
            try:
                with open(receivedName, "w") as outputFile:
                    json.dump(trackData, outputFile, indent = 4)
                    pygame.display.set_caption(os.path.splitext(os.path.basename(receivedName))[0] + " - " + receivedName)
                    self.saveDirectory = receivedName
                    self.track.save()
                    if postSaveAction is not None:
                        postSaveAction()

            except Exception as error:
                Message(self.UILayer, "Can't Save", str(error), "OK", "close", "grey")
                self.saveDirectory = None

        def saveTrackFirst():
            saveToFile(self.saveDirectory)
            saveLogic()

        def saveLogic():
            if save_as or self.saveDirectory is None:
                actionText = None
                if save_as:
                    actionText = "Save As"
                FileSaver(self.UILayer, directories["tracks"], saveToFile, actionText = actionText)
            else:
                saveToFile(self.saveDirectory)

        if save_as and not self.track.isSaved():
            Message(self.UILayer, "Save Track First?", "This track has unsaved changes", "Save", saveTrackFirst,
                    "grey", "Discard", saveLogic, "red")
        else:
            saveLogic()

    #Opens track from specific directory specified by user. Track is checked first
    def openTrack(self, tempDirectory = None):
        def loadTrack(directory):
            with open(directory) as loadFile:
                trackData = json.load(loadFile)
                trackProperties = trackData["properties"]
                pointCoords = trackData["points"]

                if len(pointCoords) == 0:
                    trackClosed = False
                else:
                    if pointCoords[0] == pointCoords[-1]:
                        trackClosed = True
                    else:
                        trackClosed = False

                self.track.loadTrackPoints(pointCoords)

                self.trackWidthSlider.updateValue(trackProperties["width"], update = False)
                self.track.width = trackProperties["width"]

                self.track.finishIndex = trackProperties["finishIndex"]
                if self.track.finishIndex is not None:
                    if self.track.finishIndex >= (len(pointCoords) - 1):
                        self.track.finishIndex = None

                self.track.finishDir = trackProperties["finishDir"]
                if self.track.finishIndex is None:
                    self.track.finishDir = True

                self.track.updateCloseStatus(trackClosed, update = False)

                self.referenceImageScale = trackProperties["referenceImageScale"]

                self.track.UUID = trackData["UUID"]

                if trackProperties["referenceImage"] is not None:
                    try:
                        referenceImageData = PIL.Image.open(BytesIO(base64.b64decode(trackProperties["referenceImage"])))
                        referenceImageSaveDir = os.path.normpath(os.path.join(executionDir, "temp"))

                        if not os.path.exists(referenceImageSaveDir):
                            os.makedirs(referenceImageSaveDir)

                        referenceImageSaveDir = os.path.normpath(os.path.join(executionDir, "temp/referenceImage.png"))
                        referenceImageData.save(referenceImageSaveDir)
                        self.track.referenceImageDir = referenceImageSaveDir
                        self.setReferenceImage(referenceImageSaveDir, userPerformed = False)
                    except:
                        self.track.referenceImageDir = None

                self.getUserPreferences()

                self.track.computeTrack()
                self.track.save()

                self.saveDirectory = directory
                self.recentreFrame()

        def directoryReceived(receivedDir):
            def saveTrackFirst():
                self.saveTrack(postSaveAction = lambda: loadTrack(receivedDir))

            def discardTrack():
                if self.saveDirectory is None:
                    deleteTrackTimes(self.track.UUID)
                loadTrack(receivedDir)

            if receivedDir != '' and not self.track.isSaved():
                Message(self.UILayer, "Save Track First?", "You currently have an unsaved track open", "Save", saveTrackFirst,
                        "grey", "Discard", discardTrack, "red")
            else:
                loadTrack(receivedDir)

        if tempDirectory is None:
            FilePicker(self.UILayer, "Tracks", directories["tracks"], [".track"], directoryReceived, self.validateTrackFile, deleteTrackAction = self.deleteTrack, renameTrackAction = self.renameTrack)
        else:
            directoryReceived(tempDirectory)

    #Clears current track, asks user before clearing
    def newTrack(self, force = False):
        def saveTrackFirst():
            self.saveTrack(postSaveAction = clearTrackSequence)


        def discardTrack():
            if self.saveDirectory is None:
                deleteTrackTimes(self.track.UUID)
            clearTrackSequence()

        def clearTrackSequence():
            self.track.clear()
            self.recentreFrame()

            self.trackResSlider.updateValue(self.track.perSegRes, update = False)
            self.trackWidthSlider.updateValue(self.track.width, update = False)

            self.viewModeDropdown.index = 0
            self.viewMode = self.viewModeDropdown.values[0]

            self.switchEndsSwitch.value = False
            self.getUserPreferences()

            self.saveDirectory = None

        if force:
            if self.saveDirectory is not None:
                clearTrackSequence()
            else:
                self.recentreFrame()

        if not self.track.isSaved():
            Message(self.UILayer, "Save Track First?", "You currently have an unsaved track open", "Save", saveTrackFirst, "grey",
                    "Discard", discardTrack, "red")

        elif self.saveDirectory is not None:
            self.saveTrack()
            clearTrackSequence()

        else:
            self.recentreFrame()

    def deleteTrack(self, fileDir):
        with open(fileDir) as trackFile:
            trackUUID = json.load(trackFile)["UUID"]
            deleteTrackTimes(trackUUID)

        os.remove(fileDir)
        if fileDir == self.saveDirectory:
            self.newTrack(force = True)

    def renameTrack(self, oldFileDir, newFileDir):
        os.rename(oldFileDir, newFileDir)
        if oldFileDir == self.saveDirectory:
            self.saveDirectory = newFileDir

    def closeTrack(self):
        def closeError():
            self.closeCount = 0

        def saveTrackFirst():
            global running
            self.saveTrack()
            running = False

        def discardTrack():
            global running
            if self.saveDirectory is None:
                deleteTrackTimes(self.track.UUID)
            running = False

        if self.closeCount == 0:
            Message(self.UILayer, "Save Track First?", "You currently have an unsaved track open", "Save",
                                        saveTrackFirst, "grey", "Discard", discardTrack, "red", closeError)
        self.closeCount += 1

    #Undoes previous action
    def undo(self):
        undoActions = self.track.history.undo()
        for action in undoActions:
            if action.command == "SET REFERENCE IMAGE":
                self.track.referenceImageDir = action.params[1]
                if self.track.referenceImageDir is not None:
                    self.setReferenceImage(self.track.referenceImageDir, userPerformed = False)

        undoActions = self.track.undo(undoActions)
        for action in undoActions:
            if action.command == "SET SCALE":
                self.scaleReferenceImage(1 / (action.params[0] * (1 / self.track.scale)))
                self.recentreFrame()

    #Redoes previously undone action
    def redo(self):
        redoActions = self.track.history.redo()
        for action in redoActions:
            if action.command == "SET REFERENCE IMAGE":
                self.track.referenceImageDir = action.params[0]
                if self.track.referenceImageDir is not None:
                    self.setReferenceImage(self.track.referenceImageDir, userPerformed = False)

        redoActions = self.track.redo(redoActions)
        for action in redoActions:
            if action.command == "SET SCALE":
                self.scaleReferenceImage(action.params[0] * (1 / self.track.scale))
                self.recentreFrame()

    #Where all the events are passed to be processed
    def handleEvents(self, events):
        global running

        self.track.history.checkIfSaved()

        self.events = events
        for event in events:
            if event.type == pygame.QUIT:
                if not self.track.isSaved():
                    self.closeTrack()

                if self.track.isSaved() or self.closeCount > 1:
                    running = False

            #Adding control point
            if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed()[0] and (self.track.mouseHovering is None) and (not self.UILayer.mouseOnLayer((self.mousePosX, self.mousePosY))) and (not programUI.mouseOnLayer((self.mousePosX, self.mousePosY))) and not (self.userSettingScale or self.userSettingFinish) and (not self.UIClick):
                index = -1
                if self.switchEndsSwitch.value:
                    index = 0

                onLine = False
                if len(self.track.points) >= 2:
                    onLine, nearPointSegment, nearestPoint, nearPointIndex = self.track.pointOnCurve((self.mousePosX - self.offsetPosition[0]) / self.zoom, (self.mousePosY - self.offsetPosition[1]) / self.zoom, 20)
                    if onLine:
                        index = nearPointSegment

                validPlacement = (not self.track.closed or onLine)
                if validPlacement:
                    self.track.add(ControlPoint((self.mousePosX - self.offsetPosition[0]) / self.zoom,
                                                (self.mousePosY - self.offsetPosition[1]) / self.zoom),
                                   index = index, userPerformed = True)

            #Removing control point
            if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed()[2] and (self.track.mouseHovering is not None) and (not self.UILayer.mouseOnLayer((self.mousePosX, self.mousePosY))) and (not programUI.mouseOnLayer((self.mousePosX, self.mousePosY))) and not (self.userSettingScale or self.userSettingFinish) and (not self.UIClick):
                index = self.track.mouseHovering
                if not(self.track.closed and ((index == 0) or (index == len(self.track.points) - 1))):
                    self.track.remove(index = index, userPerformed = True)

            #Set offset pivot
            if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed()[1]:
                self.pivotPos = (self.mousePosX - self.offsetPosition[0], self.mousePosY - self.offsetPosition[1])

            if event.type == pygame.MOUSEBUTTONDOWN and (self.UILayer.mouseOnLayer((self.mousePosX, self.mousePosY))):
                self.UIClick = True

            #Set offset pivot
            if event.type == pygame.MOUSEWHEEL and not(self.UILayer.mouseOnLayer((self.mousePosX, self.mousePosY))):
                if event.y > 0:
                    if self.zoom < self.upperZoomLimit:
                        beforeZoom = self.zoom
                        self.zoom *= 1 + self.zoomIncrement

                        if self.zoom > self.upperZoomLimit:
                            self.zoom = self.upperZoomLimit

                        zoomDifference = (self.zoom/beforeZoom) - 1
                        self.offsetPosition = (int(self.offsetPosition[0] - (self.mousePosX - self.offsetPosition[0]) * zoomDifference), int(self.offsetPosition[1] - (self.mousePosY - self.offsetPosition[1]) * zoomDifference))

                        if self.track.referenceImageDir is not None:
                            self.scaledReferenceImage = pygame.transform.scale_by(self.referenceImage, (self.zoom * self.referenceImageScale))

                elif event.y < 0:
                    if self.zoom > self.lowerZoomLimit:
                        beforeZoom = self.zoom
                        self.zoom *= 1 - self.zoomIncrement

                        if self.zoom < self.lowerZoomLimit:
                            self.zoom = self.lowerZoomLimit

                        zoomDifference = (beforeZoom/self.zoom) - 1
                        self.offsetPosition = (int(self.offsetPosition[0] + (self.mousePosX - self.offsetPosition[0]) * zoomDifference), int(self.offsetPosition[1] + (self.mousePosY - self.offsetPosition[1]) * zoomDifference))

                        if self.track.referenceImageDir is not None:
                            self.scaledReferenceImage = pygame.transform.scale_by(self.referenceImage, (self.zoom * self.referenceImageScale))

            #Handling key presses
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_LCTRL and not(pygame.key.get_mods() & pygame.KMOD_LSHIFT):
                    self.undo()

                if event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_LCTRL and pygame.key.get_mods() & pygame.KMOD_LSHIFT:
                    self.redo()

                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_LCTRL:
                    self.saveTrack()

                if event.key == pygame.K_o and pygame.key.get_mods() & pygame.KMOD_LCTRL:
                    self.openTrack()

                if event.key == pygame.K_n and pygame.key.get_mods() & pygame.KMOD_LCTRL:
                    self.newTrack()

            #Logic for setting scale
            if self.userSettingScale:
                if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed()[0] and (not self.UILayer.mouseOnLayer((self.mousePosX, self.mousePosY))) and (not programUI.mouseOnLayer((self.mousePosX, self.mousePosY))):
                    if self.setScalePoint1 is None:
                        self.setScalePoint1 = ((self.mousePosX - self.offsetPosition[0]) / self.zoom, (self.mousePosY - self.offsetPosition[1]) / self.zoom)
                    elif self.setScalePoint2 is None:
                        self.setScalePoint2 = ((self.mousePosX - self.offsetPosition[0]) / self.zoom, (self.mousePosY - self.offsetPosition[1]) / self.zoom)
                        self.realDistanceTextInput.show = True
                        self.realDistanceTextInput.text = ""

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.realDistanceTextInput.show = False
                        self.scalingErrorLabel.show = False
                        self.userSettingScale = False

            #Logic for setting finish
            if self.userSettingFinish:
                if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed()[0] and (not self.UILayer.mouseOnLayer((self.mousePosX, self.mousePosY))) and (not programUI.mouseOnLayer((self.mousePosX, self.mousePosY))):
                    if self.finishIndex is None:
                        self.finishIndex = ((self.mousePosX - self.offsetPosition[0]) / self.zoom, (self.mousePosY - self.offsetPosition[1]) / self.zoom)
                        onLine, nearPointSegment, nearestPointCoords, nearestPoint = self.track.pointOnCurve(self.finishIndex[0], self.finishIndex[1], (self.track.width / 2))
                        if onLine:
                            nearestPoint = max(5, nearestPoint)
                            self.finishIndex = nearestPoint / self.track.perSegRes
                        else:
                            self.finishIndex = None

                    elif self.finishIndex is not None:
                        self.completeFinish()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.userSettingFinish = False

    def update(self):
        self.track.updateOffsetValues(self.offsetPosition, self.zoom)

        self.previousScreenWidth = self.screenWidth
        self.previousScreenHeight = self.screenHeight

        self.screenWidth, self.screenHeight = screen.get_size()
        self.mousePosX = pygame.mouse.get_pos()[0]
        self.mousePosY = pygame.mouse.get_pos()[1]

        screen.fill(self.colours["background"])

        #Checks if update is available
        if not self.checkedForUpdates:
            isUpdateRequired(__file__, githubRepoAddress, self.setUpdateNeeded)
            self.checkedForUpdates = True

        if self.updateNeeded:
            self.updateNeeded = False
            self.askToUpdate()

        #Ensures track remains the same size when the user changes the window size (maximises/minimises)
        if ((self.previousScreenWidth != self.screenWidth) or (self.previousScreenHeight != self.screenHeight)) and (len(self.track.points) >= 1):
            widthDiff = abs(self.screenWidth - self.previousScreenWidth)
            heightDiff = abs(self.screenHeight - self.previousScreenHeight)
            if widthDiff > heightDiff:
                self.zoom *= (self.screenHeight / self.previousScreenHeight)
            else:
                self.zoom *= (self.screenWidth / self.previousScreenWidth)

            self.zoom = min(max(self.zoom, self.lowerZoomLimit), self.upperZoomLimit)
            self.offsetPosition = ((self.screenWidth / self.previousScreenWidth) * self.offsetPosition[0],
                                   (self.screenHeight / self.previousScreenHeight) * self.offsetPosition[1])

        #Allows screen to be moved around pivot
        if pygame.mouse.get_pressed()[1]:
            if self.pivotPos is not None:
                self.offsetPosition = (self.mousePosX - self.pivotPos[0], self.mousePosY - self.pivotPos[1])
        else:
            self.pivotPos = None

        if not(any(pygame.mouse.get_pressed())):
            self.UIClick = False

        self.track.showRacingLine = self.racingLineSwitch.value

        self.drawGrid(self.offsetPosition, 50 * self.zoom, 1, self.colours["grid"])

        screenRect = pygame.Rect((0, 0), (self.screenWidth + 15, self.screenHeight + 15))

        #Draws reference image to screen
        if (self.track.referenceImageDir is not None) and self.referenceImageVisibility:
            self.referenceImageRect = self.scaledReferenceImage.get_rect(center = self.offsetPosition)
            screen.blit(self.scaledReferenceImage, self.referenceImageRect)

        if self.track.referenceImageDir is None:
            self.hideReferenceImageButton.disabled = True
            self.removeReferenceImageButton.disabled = True
            self.hideReferenceImageIcon.updateImage(directories["hide"])
        else:
            self.hideReferenceImageButton.disabled = False
            self.removeReferenceImageButton.disabled = False

        if not (self.userSettingScale or self.userSettingFinish) and (not self.UIClick):
            self.track.update((self.mousePosX - self.offsetPosition[0]) / self.zoom, (self.mousePosY - self.offsetPosition[1]) / self.zoom, self.zoom, self.screenWidth, self.screenHeight, self.screenBorder, self.offsetPosition, screenRect)
        self.track.draw(self.colours, self.switchEndsSwitch.value, self.viewMode, self.antialiasingSwitch.value)

        #Algorithm for setting track scale - draw line between 2 mouse positions
        self.scalingHelpLabel.show = False
        if self.userSettingScale:
            helpLabelX = (screenWidth / 2) - (self.scalingHelpLabel.textSize[0] / 2)
            self.scalingHelpLabel.posX = helpLabelX
            self.scalingHelpLabel.show = True

            transparentSurface = pygame.Surface((self.screenWidth, self.screenHeight), pygame.SRCALPHA)
            pygame.draw.rect(transparentSurface, (50, 50, 50, 100), (0, 0, self.screenWidth, self.screenHeight))
            screen.blit(transparentSurface, (0, 0))

            if self.setScalePoint1 is not None:
                lineStart = (
                (self.setScalePoint1[0] * self.zoom) + self.offsetPosition[0], (self.setScalePoint1[1] * self.zoom) + self.offsetPosition[1])
                if self.setScalePoint2 is None:
                    lineEnd = (self.mousePosX, self.mousePosY)
                else:
                    lineEnd = ((self.setScalePoint2[0] * self.zoom) + self.offsetPosition[0], (self.setScalePoint2[1] * self.zoom) + self.offsetPosition[1])

                lineStart_EndStop = [calculateSide([lineStart, lineEnd], 0, 20),
                                     calculateSide([lineStart, lineEnd], 0, -20)]

                lineEnd_EndStop = [calculateSide([lineStart, lineEnd], 1, 20),
                                   calculateSide([lineStart, lineEnd], 1, -20)]

                pygame.draw.line(screen, self.colours["white"], lineStart, lineEnd, 5)
                pygame.draw.line(screen, self.colours["white"], lineStart_EndStop[0], lineStart_EndStop[1], 5)
                pygame.draw.line(screen, self.colours["white"], lineEnd_EndStop[0], lineEnd_EndStop[1], 5)

        #Allows user to set whether track is clockwise or anticlockwise
        self.finishHelpLabel.show = False
        if self.userSettingFinish:
            helpLabelX = (screenWidth / 2) - (self.finishHelpLabel.textSize[0] / 2)
            self.finishHelpLabel.posX = helpLabelX
            self.finishHelpLabel.show = True

            transparentSurface = pygame.Surface((self.screenWidth, self.screenHeight), pygame.SRCALPHA)
            pygame.draw.rect(transparentSurface, (50, 50, 50, 100), (0, 0, self.screenWidth, self.screenHeight))
            screen.blit(transparentSurface, (0, 0))

            if self.finishIndex is not None:
                if angle(offsetPoints((self.mousePosX, self.mousePosY), self.offsetPosition, self.zoom, True, True),
                         self.track.splinePoints[int(self.finishIndex * self.track.perSegRes)],
                         extendPointsBack(self.track.splinePoints)[int(self.finishIndex * self.track.perSegRes) + 1]) < 90:
                    self.finishDir = True
                else:
                    self.finishDir = False

        else:
            self.finishIndex = self.track.finishIndex
            self.finishDir = self.track.finishDir

        #Resets finish line position if invalid
        if self.finishIndex is not None:
            if ((len(self.track.points) - 1) < self.finishIndex) or (self.finishIndex < 0):
                self.track.finishIndex = None
                self.track.finishDir = None

                self.finishIndex = None
                self.finishDir = None

        if self.finishIndex is not None and self.viewMode != "Display":
            self.finishIcon.show = True
            self.finishDirIcon.show = True
        else:
            self.finishIcon.show = False
            self.finishDirIcon.show = False

        #Sets visuals for track finish line setup - drawing direction arrow, finish line icon
        if self.finishIndex is not None:
            finishPointCoords = (self.track.splinePoints[int(self.finishIndex * self.track.perSegRes)])
            finishPointNeighbourCoords = (extendPointsBack(self.track.splinePoints)[int(self.finishIndex * self.track.perSegRes) + 1])
            finishPointNeighboursDistance = pointDistance(finishPointNeighbourCoords, finishPointCoords)

            arrowEndExtX = ((finishPointNeighbourCoords[0] - finishPointCoords[
                0]) / finishPointNeighboursDistance) / self.zoom
            arrowEndExtY = ((finishPointNeighbourCoords[1] - finishPointCoords[
                1]) / finishPointNeighboursDistance) / self.zoom
            arrowPos = (finishPointCoords[0] + (arrowEndExtX * 80 * self.finishDir) - (arrowEndExtX * 40),
                        finishPointCoords[1] + (arrowEndExtY * 80 * self.finishDir) - (arrowEndExtY * 40))

            trackAngle = 0 + math.degrees(math.atan2(finishPointCoords[0] - finishPointNeighbourCoords[0],
                                                     (finishPointCoords[1] - finishPointNeighbourCoords[1]))) - 90

            finishIconSize = self.finishIcon.getSize()
            finishDirIconSize = self.finishDirIcon.getSize()

            self.finishIcon.posX, self.finishIcon.posY = (
            finishPointCoords[0] - (finishIconSize[0] / 2), finishPointCoords[1] - (finishIconSize[1] / 2))
            self.finishDirIcon.posX, self.finishDirIcon.posY = (
            arrowPos[0] - (finishDirIconSize[0] / 2), arrowPos[1] - (finishDirIconSize[1] / 2))
            self.finishDirIcon.angle = trackAngle + (self.finishDir * 180)

        if self.track.isSaved():
            saveCharacter = ""
        else:
            saveCharacter = "*"

        if self.saveDirectory is None:
            newCaption = "Untitled Track" + saveCharacter
            self.configAccordion.titleText = "Untitled Track" + saveCharacter
        else:
            newCaption = str(os.path.splitext(os.path.basename(self.saveDirectory))[0] + saveCharacter)
            self.configAccordion.titleText = str(os.path.splitext(os.path.basename(self.saveDirectory))[0] + saveCharacter)

        if self.lastCaption != newCaption:
            pygame.display.set_caption(newCaption)

        self.lastCaption = newCaption
        self.mouseXLabel.text = ("x: " + str(int(((self.mousePosX * 1) - self.offsetPosition[0]) / self.zoom)))
        self.mouseYLabel.text = ("y: " + str(int(((self.mousePosY * 1) - self.offsetPosition[1]) / self.zoom)))
        self.scaleLabel.text = ("view: " + str(int(self.zoom * 100)) + "%")

        if self.track.autoRes:
            self.trackResSlider.disabled = True
            self.trackResSlider.updateValue(self.track.perSegRes, False)
        else:
            self.trackResSlider.disabled = False

        if (self.userValues != self.returnUserValues()) and not pygame.mouse.get_pressed()[0]:
            self.updateUserPreferences()
            self.userValues = self.returnUserValues()

        #Checks if there are any items left to undo
        if len(self.track.history.undoStack) == 0:
            self.undoButton.disabled = True
            self.undoIcon.colour = (90, 90, 90)
        else:
            self.undoButton.disabled = False
            self.undoIcon.colour = self.colours["white"]

        #Checks if there are any items left to redo
        if len(self.track.history.redoStack) == 0:
            self.redoButton.disabled = True
            self.redoIcon.colour = (90, 90, 90)
        else:
            self.redoButton.disabled = False
            self.redoIcon.colour = self.colours["white"]

        if (len(self.track.points) < 2) or self.userSettingScale:
            self.setFinishButton.disabled = True
        else:
            self.setFinishButton.disabled = False

        if self.userSettingFinish:
            self.setScaleButton.disabled = True
        else:
            self.setScaleButton.disabled = False

        if self.saveDirectory is None:
            self.saveAsButton.disabled = True
        else:
            self.saveAsButton.disabled = False

        #Determines whether track length should be in m or km
        if self.track.scale is not None:
            trackScaleReduced = int((self.track.scale * 150) / self.zoom)

            if self.track.length > 1000:
                lengthText = "length: " + str(int(self.track.length) / 1000) + "km"
            else:
                lengthText = "length: " + str(int(self.track.length)) + "m"

            self.trackScaleLabel.text = str(trackScaleReduced) + "m  | " + lengthText

            pygame.draw.line(screen, self.colours["white"], (20, self.screenHeight - 35), (20, self.screenHeight - 20), 2)
            pygame.draw.line(screen, self.colours["white"], (20, self.screenHeight - 20), (170, self.screenHeight - 20), 2)
            pygame.draw.line(screen, self.colours["white"], (170, self.screenHeight - 35), (170, self.screenHeight - 20), 2)
        else:
            self.trackScaleLabel.text = ""

        self.trackLayer.display(self.screenWidth, self.screenHeight, self.events, self.offsetPosition, self.zoom)
        self.UILayer.display(self.screenWidth, self.screenHeight, self.events)

class TrackRacing (Scene):
    def __init__(self, trackEditor):
        super().__init__()
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

        self.colours = {"background": (101, 126, 51),
                        "controlPoint": (24, 150, 204),
                        "white": (200, 200, 200),
                        "track": (100, 100, 100)}

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
        font.render_to(self.slowSign, ((150 // 2) - (textSize.width // 2), (50 // 2) - (textSize.height // 2)), "SLOW!", self.colours["white"])

        #Settings accordion
        self.viewLeaderboardButton = Button(self.UILayer, (90, 310), "SW", (200, 40), "View Leaderboard", 15, (100, 100, 100), action = self.viewLeaderboard)
        self.leaderboardView = None

        self.viewControlsButton = Button(self.UILayer, (90, 260), "SW", (200, 40), "View Controls", 15, (100, 100, 100), action = self.viewControls)
        self.controlsView = None

        self.deleteRaceTimesButton = Button(self.UILayer, (105, 335), "SE", (30, 30), "", 12, (66, 41, 41), action = self.deleteRaceTimes, show = False)
        self.deleteRaceTimesIcon = Image(self.UILayer, (self.deleteRaceTimesButton.posX - 1, self.deleteRaceTimesButton.posY - 1), "SE", directories["bin"], 0.7, colour = self.colours["white"], show = False)

        self.zoomAdjustmentSlider = Slider(self.UILayer, 15, self.colours["white"], self.colours["controlPoint"], (140, 190), "SW", 1, 105, (self.lowerZoomLimit, self.upperZoomLimit), 2.0001, precision = 1, increment = 0.1, action = self.updateZoom, suffix = 'x', finishedUpdatingAction = lambda x = None, y = None: self.updateUserPreferences())
        self.zoomAdjustmentLabel = Label(self.UILayer, 15, (80, 192), "SW", "Zoom", self.colours["white"])

        self.multiplayerSwitch = Switch(self.UILayer, (250, 160), "SW", 0.8, value = False, action = self.toggleMultiplayer)
        self.multiplayerLabel = Label(self.UILayer, 15, (98, 158), "SW", "Split-screen", self.colours["white"])
        self.multiplayerSwitch.trueColour = (38, 87, 38)

        self.speedWarningSwitch = Switch(self.UILayer, (250, 130), "SW", 0.8, value = False, action = self.toggleSpeedWarnings)
        self.speedWarningLabel = Label(self.UILayer, 15, (80, 128), "SW", "Speed Warnings", self.colours["white"])
        self.speedWarningSwitch.trueColour = (38, 87, 38)

        self.racingLineSwitch = Switch(self.UILayer, (250, 100), "SW", 0.8, value = False, action = self.toggleRacingLine)
        self.racingLineLabel = Label(self.UILayer, 15, (107, 98), "SW", "Racing Line", self.colours["white"])
        self.racingLineSwitch.trueColour = (38, 87, 38)

        self.settingsAccordion = Accordion(self.UILayer, (50, 50), "SW", (280, 325), "Settings",
                                           [self.viewLeaderboardButton, self.viewControlsButton, self.zoomAdjustmentSlider,
                                            self.zoomAdjustmentLabel, self.multiplayerSwitch, self.multiplayerLabel, self.speedWarningSwitch,
                                            self.speedWarningLabel, self.racingLineSwitch, self.racingLineLabel], openDir = "r")


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
        self.viewLeaderboardLabel = Label(self.UILayer, 20, (205, -80), "vh", "Leaderboard:", self.colours["white"], show = False)
        self.viewControlsLabel = Label(self.UILayer, 20, (169, -130), "vh", "Controls:", self.colours["white"], show = False)

        self.controlsUI = [self.controlsKeyW, self.controlsKeyA, self.controlsKeyS, self.controlsKeyD,
                           self.controlsKeyUp, self.controlsKeyLeft, self.controlsKeyDown, self.controlsKeyRight,
                           self.controlsKeyP, self.controlsKeyL, self.controlsKeyR, self.controlsKeyC,
                           self.orLabel, self.movementLabel, self.resetLabel, self.pauseLabel, self.viewLeaderboardLabel, self.viewControlsLabel]

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
            self.zoomAdjustmentSlider.updateValue(preferenceData["racingZoom"])
            self.racingLineSwitch.updateValue(preferenceData["racingLine"])
            self.speedWarningSwitch.updateValue(preferenceData["speedWarnings"])

    #Changes the zoom value
    def updateZoom(self, value):
        self.zoom = round(value, 1)
        self.reloadTrackSurface()

    #Called when the track is changed, re-renders the track
    def reloadTrackSurface(self):
        self.track.showRacingLine = self.racingLineSwitch.value
        self.trackSurface, self.originOffset = self.track.renderToSurface(self.colours, self.zoom)

    #Resets the position of the cars back to the start line
    def reset(self):
        self.car.reset(2 * int(self.splitScreen))
        self.car2.reset(-2 * int(self.splitScreen))
        self.offsetPosition = ((-self.car.position.x * self.zoom) + (self.screenWidth / 2), (-self.car.position.y * self.zoom) + (self.screenHeight / 2))

        self.car.dead = False
        self.timer.text = secondToRaceTimer(0)
        self.timer.colour = self.colours["white"]
        self.ranking.show = False

        self.timer2.text = secondToRaceTimer(0)
        self.timer2.colour = self.colours["white"]
        self.ranking2.show = False

    #Deletes the race times for the currently open track
    def deleteRaceTimes(self):
        def delete():
            deleteTrackTimes(self.track.UUID)
            self.viewLeaderboard()

        def cancel():
            self.viewLeaderboard()

        self.leaderboardView.close()
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
        conn.close()

    #Returns what ranking (e.g. 1st, 3rd, 54th) a race time is, and returns the corresponding colour (e.g. gold for first)
    def getRaceTimeRanking(self, raceTime):
        firstColour = (191, 161, 0) #Gold
        secondColour = (160, 160, 160) #Silver
        thirdColour = (205, 127, 50) #Bronze
        otherColour = self.colours["white"] #White

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
        self.leaderboardView.close()

    def viewLeaderboard(self):        
        if self.controlsView in self.UILayer.elements: #Closes controls view if opened
            self.closeControls()

        if self.leaderboardView in self.UILayer.elements: #Closes leaderboard view if already opened
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

            self.leaderboardView = Message(self.UILayer, "Leaderboard", leaderboardMessages, dimensions = (400, 270), closeAction = self.closeLeaderboard, layerIndex = 0)
            if len(times) > 0:
                self.deleteRaceTimesButton.show = True
                self.deleteRaceTimesIcon.show = True

    def closeControls(self):
        for element in self.controlsUI:
            element.show = False
        self.controlsView.close()

    def viewControls(self):
        if self.leaderboardView in self.UILayer.elements: #Closes leaderboard view if opened
            self.closeLeaderboard()

        if self.controlsView in self.UILayer.elements: #Closes controls view if already opened
            self.closeControls()
        else:
            for element in self.controlsUI:
                element.show = True

            self.controlsView = Message(self.UILayer, "Controls", "", dimensions = (500, 370), layerIndex = 0, closeAction = self.closeControls)

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

    #Called if track changes, used to update what points make up the minimap.
    #This includes scaling the points so that the minimap always remains the same size
    def updateMiniMapPoints(self, width, height, thickness):
        self.miniMapThickness = thickness
        self.miniMapSurface = pygame.Surface((width, height), pygame.SRCALPHA)
        trackPoints = self.track.splinePoints
        xPoints = [point[0] for point in trackPoints]
        yPoints = [point[1] for point in trackPoints]
        self.topLeftCornerMiniMap = (min(xPoints), min(yPoints))

        trackWidth = max(xPoints) - min(xPoints)
        trackHeight = max(yPoints) - min(yPoints)

        if (width/trackWidth) < (height/trackHeight):
            self.miniMapScale = ((width - (thickness * 2))/trackWidth)
        else:
            self.miniMapScale = ((height - (thickness * 2))/trackHeight)

        self.miniMapHeightOffset = height - (trackHeight * self.miniMapScale)

        self.minimapPoints = []
        for point in trackPoints:
            newPosition = (((point[0] - self.topLeftCornerMiniMap[0]) * self.miniMapScale) + thickness, ((point[1] - self.topLeftCornerMiniMap[1]) * self.miniMapScale) - thickness + self.miniMapHeightOffset)
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
            carPos = (((positions[car][0] - self.topLeftCornerMiniMap[0]) * self.miniMapScale) + self.miniMapThickness, ((positions[car][1] - self.topLeftCornerMiniMap[1]) * self.miniMapScale) - self.miniMapThickness + self.miniMapHeightOffset)
            pygame.gfxdraw.aacircle(miniMapWithCarSurface, int(carPos[0]), int(carPos[1]), 4, colours[car % 2])
            pygame.gfxdraw.filled_circle(miniMapWithCarSurface, int(carPos[0]), int(carPos[1]), 4, colours[car % 2])

        screen.blit(miniMapWithCarSurface, (actualX, actualY))

    #Where all the events are passed to be processed
    def handleEvents(self, events):
        global running

        self.accelerationInput = 0
        self.steeringInput = 0

        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_RIGHT] or keys[pygame.K_LEFT] or keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]:
            self.accelerationInput = [0, 0]
            self.steeringInput = [0, 0]

        self.accelerationInput = [int(keys[pygame.K_UP]) - int(keys[pygame.K_DOWN]), int(keys[pygame.K_w]) - 2 * int(keys[pygame.K_s])]
        self.steeringInput = [int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT]), int(keys[pygame.K_d]) - int(keys[pygame.K_a])]

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
                    self.zoomAdjustmentSlider.updateValue(float(min(self.upperZoomLimit, max(self.zoom + 0.1, self.lowerZoomLimit))), runFinalAction = True)

                elif event.y < 0:
                    if self.zoom > self.lowerZoomLimit:
                        self.zoomAdjustmentSlider.updateValue(float(min(self.upperZoomLimit, max(self.zoom - 0.1, self.lowerZoomLimit))), runFinalAction = True)

    def update(self):
        self.offsetPosition = ((-self.car.position.x * self.zoom) + (self.screenWidth / 2), (-self.car.position.y * self.zoom) + (self.screenHeight / 2))

        self.screenWidth, self.screenHeight = screen.get_size()
        self.mousePosX = pygame.mouse.get_pos()[0]
        self.mousePosY = pygame.mouse.get_pos()[1]

        self.splitScreen = self.multiplayerSwitch.value

        screen.fill(self.colours["background"])

        if self.uniquenessToken != self.track.getUniquenessToken(): #Track has changed
            if len(self.track.points) >= 2:
                self.reset()
                self.getUserPreferences()
                self.updateMiniMapPoints(200, 200, 6)

                self.reloadTrackSurface()

            self.uniquenessToken = self.track.getUniquenessToken()
            self.previousTrackUUID = self.track.UUID

        #If the start-timer has started for either of the cars, minimise the settings.
        if (self.lastStartTimeCar != self.car.timerStart) or (self.lastStartTimeCar2 != self.car2.timerStart):
            if (self.car.timerStart is not None) or (self.car2.timerStart is not None):
                self.settingsAccordion.setCollapseStatus(True)
            else:
                self.settingsAccordion.setCollapseStatus(False)

            self.lastStartTimeCar = self.car.timerStart
            self.lastStartTimeCar2 = self.car2.timerStart

        if self.splitScreen:
            acceleration = self.accelerationInput[0]
            if self.car.timerStart is None and self.accelerationInput[1] == 0: #Stop car1 from moving if car2 hasn't started yet
                acceleration = 0
            self.car.update(self.steeringInput[0], acceleration, deltaTime, self.pause)

            self.offsetPosition = ((-self.car.position.x * self.zoom) + (1 * (self.screenWidth / 4)), (-self.car.position.y * self.zoom) + (self.screenHeight / 2))
            rightSide = pygame.Surface(((self.screenWidth / 2), self.screenHeight), pygame.SRCALPHA)
            rightSide.blit(self.trackSurface, (self.offsetPosition[0] - self.originOffset[0], self.offsetPosition[1] - self.originOffset[1]))

            acceleration = self.accelerationInput[1]
            if self.car2.timerStart is None and self.accelerationInput[0] == 0: #Stop car2 from moving if car1 hasn't started yet
                acceleration = 0
            self.car2.update(self.steeringInput[1], acceleration, deltaTime, self.pause)

            self.offsetPosition = ((-self.car2.position.x * self.zoom) + (self.screenWidth / 4), (-self.car2.position.y * self.zoom) + (self.screenHeight / 2))
            leftSide = pygame.Surface(((self.screenWidth / 2), self.screenHeight), pygame.SRCALPHA)
            leftSide.blit(self.trackSurface, (self.offsetPosition[0] - self.originOffset[0], self.offsetPosition[1] - self.originOffset[1]))

            self.car.display(((-self.car.position.x * self.zoom) + (self.screenWidth / 4), (-self.car.position.y * self.zoom) + (self.screenHeight / 2)), self.zoom, appearance = 0, surface = rightSide)
            self.car2.display(((-self.car.position.x * self.zoom) + (self.screenWidth / 4), (-self.car.position.y * self.zoom) + (self.screenHeight / 2)), self.zoom, appearance = 1, bodyColour = (200, 0, 0), surface = rightSide)

            self.car.display(((-self.car2.position.x * self.zoom) + (1 * (self.screenWidth / 4)), (-self.car2.position.y * self.zoom) + (self.screenHeight / 2)), self.zoom, appearance = 1, bodyColour = (200, 0, 0), surface = leftSide)
            self.car2.display(((-self.car2.position.x * self.zoom) + (1 * (self.screenWidth / 4)), (-self.car2.position.y * self.zoom) + (self.screenHeight / 2)), self.zoom, appearance = 0, surface = leftSide)

            screen.blit(leftSide, (0, 0))
            screen.blit(rightSide, ((self.screenWidth / 2), 0))

            pygame.draw.line(screen, self.colours["white"], ((self.screenWidth / 2) - 1, 0),((self.screenWidth / 2) - 1, self.screenHeight), 10)

        else:
            steering = min(self.steeringInput[0] + self.steeringInput[1], 1)
            acceleration = min(self.accelerationInput[0] + self.accelerationInput[1], 1)
            self.car.update(steering, acceleration, deltaTime, self.pause)
            self.car2.update(0, 0, deltaTime, self.pause)

            self.offsetPosition = ((-self.car.position.x * self.zoom) + (self.screenWidth / 2), (-self.car.position.y * self.zoom) + (self.screenHeight / 2))
            screen.blit(self.trackSurface, (self.offsetPosition[0] - self.originOffset[0], self.offsetPosition[1] - self.originOffset[1]))
            self.car.display(self.offsetPosition, self.zoom)

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
                                Message(self.UILayer, "New Highscore!", f"You beat the current highscore ({secondToRaceTimer(times[0][0])}) by {timeDifference}s" , "Continue", closeMessage, (100, 100, 100), linePadding = 10, closeAction = closeMessage)

                        self.uploadTime(raceTime)
                        rankText, labelColour = self.getRaceTimeRanking(raceTime)
                        if car is self.car:
                            rankingLabel = self.ranking
                        else:
                            rankingLabel = self.ranking2

                        rankingLabel.text = rankText
                        labelWidth = rankingLabel.textSize[0]
                        rankingLabel.colour = labelColour
                        rankingLabel.posX = (136 + (labelWidth / 2))
                        rankingLabel.show = True

        self.speedometer.text = f"{pixToMiles(self.car.velocity.x, self.car.scale)} mph"
        self.speedometer.posX = (self.speedometer.textSize[0] / 2) + (self.timer.posX - (self.timer.textSize[0] / 2))

        self.timer2.posX = (self.screenWidth / 2) - 184
        self.speedometer2.text = f"{pixToMiles(self.car2.velocity.x, self.car2.scale)} mph"
        self.speedometer2.posX = -(self.speedometer2.textSize[0] / 2) + (self.timer2.posX + (self.timer2.textSize[0] / 2))

        if self.splitScreen:
            self.speedometer2.show = True
            self.timer2.show = True
            if self.car.timerStart is not None and (not self.car.dead or not self.car2.dead):
                self.racePos.show = True
            else:
                self.racePos.show = False

            #Compares positions of both cars and determines which is winning
            if (self.car.timerStart is not None) and (self.car.timerEnd is None): #if car is still racing
                startIndex = self.track.getStartPos()[2]
                numOfPoints = len(self.track.splinePoints)
                if self.car.nearestSplineIndex != self.car2.nearestSplineIndex:
                    if self.winner is self.car:
                        aheadCheck = (((self.car2.nearestSplineIndex - startIndex) % numOfPoints) > ((self.car.nearestSplineIndex - startIndex) % numOfPoints))
                        if not self.track.finishDir:
                            aheadCheck = not aheadCheck

                        if (aheadCheck and not self.car2.dead) or self.car.dead:
                            self.winner = self.car2
                    else:
                        aheadCheck = (((self.car.nearestSplineIndex - startIndex) % numOfPoints) > ((self.car2.nearestSplineIndex - startIndex) % numOfPoints))
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

        if not self.pause or (self.pause and self.car.timerEnd is not None): #Update timer text
            if self.car.timerStart is not None:
                timerEnd = time.time()
                if self.car.timerEnd is not None:
                    timerEnd = self.car.timerEnd
                timerValue = timerEnd - self.car.timerStart
                self.timer.text = secondToRaceTimer(timerValue)

            if (self.car.timerStart is not None) and (self.car.timerEnd is None):
                if self.car.dead:
                    self.timer.colour = (200, 0, 0)
                else:
                    self.timer.colour = self.colours["white"]

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
                        self.timer2.colour = (200, 0, 0)
                    else:
                        self.timer2.colour = self.colours["white"]

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

        carPositions = [self.track.splinePoints[self.car.nearestSplineIndex]]
        if self.splitScreen:
            carPositions.append(self.track.splinePoints[self.car2.nearestSplineIndex])

        self.displayMiniMap((241, 320), carPositions)
        if self.splitScreen:
            self.displayMiniMap(((self.screenWidth / 2) + 241, 320), carPositions[::-1])
        self.UILayer.display(self.screenWidth, self.screenHeight, self.events)


        controlPoints = self.track.returnPointCoords()
        if self.track.closed:
            controlPoints = controlPoints[:-1]

        cars = [self.car]
        if self.splitScreen:
            cars = [self.car, self.car2]

        for car in cars:
            if len(controlPoints) >= 3 and self.speedWarnings:
                splinePoints = self.track.splinePoints
                distanceToBreak = ((100 ** 2) - (car.velocity.x ** 2)) / (-2 * car.brakeDeceleration)
                futureIndex = self.track.getIndexFromDistance(car.nearestSplineIndex, 200 + distanceToBreak, not self.track.finishDir, self.track.closed)

                if futureIndex is not None:
                    carBearing = bearing(splinePoints[car.nearestSplineIndex], splinePoints[(car.nearestSplineIndex + 1) % len(splinePoints)])
                    futureBearing = bearing(splinePoints[futureIndex], splinePoints[(futureIndex + 1) % len(splinePoints)])
                    bearingDifference = abs(futureBearing - carBearing)

                    #If car is going too fast for corner, show slow sign
                    if (self.track.calculateMaxCorneringSpeed(180 - bearingDifference) < car.velocity.x) and not car.offTrack:
                        posX = (self.screenWidth / 2) - 25
                        if self.splitScreen:
                            if car is self.car:
                                posX = (3 * (self.screenWidth / 4)) - 25
                            if car is self.car2:
                                posX = (1 * (self.screenWidth / 4)) - 25

                        screen.blit(self.slowSign, (posX, self.screenHeight - 80))

trackEditorScene = TrackEditor()
trackRacingScene = TrackRacing(trackEditorScene)

ProgramSceneManager = SceneManager()
ProgramSceneManager.addScene(trackEditorScene, "Track Editor")
ProgramSceneManager.addScene(trackRacingScene, "Racing")

ProgramSceneManager.setScene(0)

while running:
    screenWidth, screenHeight = screen.get_size()

    ProgramSceneManager.distributeEvents(pygame.event.get())

    ProgramSceneManager.updateCurrentScene()
    programUI.display(screenWidth, screenHeight, [])
    ProgramSceneManager.programUpdate()

    fpsLabel.text = ("fps: " + str(int(clock.get_fps())))

    pygame.display.flip()
    deltaTime = clock.tick(60) / 1000 #Refresh Rate

pygame.quit()
