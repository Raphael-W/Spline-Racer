import json
import sqlite3
import time

from jsonschema import validate

import pygame
import pygame.gfxdraw
import pygame.freetype

from tkinter.filedialog import asksaveasfilename, askopenfilename
import tkinter as tk

import os
import sys

import PIL.Image
from io import BytesIO

from pygameUIElements import *
from track import *
from car import *

if os.name == "nt":
    import ctypes

    appID = 'Raphael Wreford, Racing-Line-Finder' # Arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appID) #Makes taskbar icon same as window icon (Sets app as "individual app", not linked to python)

pygame.init()
pygame.display.set_caption("Racing Line Finder")
screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
clock = pygame.time.Clock()

pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN])

running = True

deltaTime = 0

#executionDir = os.path.dirname(os.path.dirname(sys.executable))
executionDir = os.path.dirname(os.path.dirname(__file__))
directories = {"mainFont": "assets/fonts/MonoFont.ttf",
               "trackSchema": "assets/schemas/trackSchema.json",
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
               "play": "assets/icons/play.png",
               "f1Car": "assets/sprites/f1_car.png",
               "f1Wheel": "assets/sprites/f1_wheel.png",
               "logo": "assets/icons/logo.png"}

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
    cursor.execute(f'''DELETE FROM TIMES WHERE UUID = "{UUID}"''')
    conn.commit()
    conn.close()

class Scene:
    def __init__(self):
        self.name = "Scene"

    def update(self):
        screen.fill((20, 20, 20))

    def handleEvents(self, events):
        global running

        for event in events:
            if event.type == pygame.QUIT:
                running = False

class SceneManager:
    def __init__(self):
        self.scenes = []
        self.currentScene = 0

        self.changeSceneDropdown = Dropdown(programUI, (30, 30), "", (190, 25), self.getSceneNames(), self.currentScene, action = self.setScene)

    def addScene(self, scene, name):
        scene.name = name
        self.scenes.append(scene)
        self.changeSceneDropdown.values = self.getSceneNames()

    def setScene(self, newScene):
        if self.currentScene == 1 and not self.scenes[1].pause:
            self.scenes[1].togglePause()
        elif self.currentScene == 0 and self.scenes[1].pause and not self.scenes[1].userPaused:
            self.scenes[1].togglePause()

        if isinstance(newScene, str):
            self.currentScene = self.getSceneIndex(newScene)
        else:
            self.currentScene = newScene

        while self.currentScene in self.changeSceneDropdown.disabledIndexes:
            self.currentScene = (self.currentScene + 1) % len(self.scenes)

        self.changeSceneDropdown.index = self.currentScene

    def getSceneIndex(self, name):
        return self.getSceneNames().index(name)

    def updateCurrentScene(self):
        if len(self.scenes[self.getSceneIndex("Track Editor")].mainTrack.points) <= 1:
            self.changeSceneDropdown.disabledIndexes = [self.getSceneIndex("Racing")]
        else:
            self.changeSceneDropdown.disabledIndexes = []

        if len(self.scenes) > 0:
            self.scenes[self.currentScene].update()

    #Events are passed from main loop to current scene
    def distributeEvents(self, events):
        global running

        for event in events:
            if event.type == pygame.QUIT:
                trackEditorSceneIndex = self.getSceneIndex("Track Editor")
                if not self.scenes[trackEditorSceneIndex].mainTrack.isSaved():
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

        self.zoom = 1
        self.zoomIncrement = 0.05
        self.upperZoomLimit = 2.5
        self.lowerZoomLimit = 0.1

        self.viewMode = "Track"

        self.trackRes = 20
        self.mainTrack = Track(self.trackRes, pygame, screen)

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
                        "mainGrid": (30, 30, 30),
                        "innerGrid": (25, 25, 25),
                        "white": (200, 200, 200),
                        "mainTrack": (100, 100, 100)}

        self.mainFont = directories["mainFont"]

        self.UILayer = Layer(screen, pygame, mainFont, directories)
        self.trackLayer = Layer(screen, pygame, self.mainFont, directories)

        with open(directories["trackSchema"]) as trackSchema:
            self.trackFileSchema = json.load(trackSchema)

        self.mouseXLabel = Label(self.UILayer, 15, (100, 60), "NE", "", self.colours["white"])
        self.mouseYLabel = Label(self.UILayer, 15, (100, 80), "NE", "", self.colours["white"])
        self.scaleLabel = Label(self.UILayer, 15, (127, 100), "NE", "", self.colours["white"])

        # ------------ CONFIG ACCORDION ------------

        self.saveButton = Button(self.UILayer, (330, 492.5), "SE", (123.75, 30), "Save", 12, (100, 100, 100), action = self.saveTrack)
        self.saveAsButton = Button(self.UILayer, (198.75, 492.5), "SE", (123.75, 30), "Save As", 12, (100, 100, 100), action = lambda: self.saveTrack(saveNewDirectory = True))
        self.openTrackButton = Button(self.UILayer, (330, 455), "SE", (123.75, 30), "Open", 12, (100, 100, 100), action = self.openTrack)
        self.newTrackButton = Button(self.UILayer, (198.75, 455), "SE", (123.75, 30), "New", 12, (100, 100, 100), action = self.newTrack)

        self.setFinishButton = Button(self.UILayer, (330, 410), "SE", (80, 60), "Set Finish", 10, (100, 100, 100), (0, -18), action = self.setFinish)
        self.setFinishImage = Image(self.UILayer, (self.setFinishButton.posX - 28, self.setFinishButton.posY - 10), "SE", directories["finishLine"], 1, colour = (30, 30, 30))

        self.setScaleButton = Button(self.UILayer, (242.5, 410), "SE", (80, 60), "Set Scale", 10, (100, 100, 100), (0, -18), action = self.setScale)
        self.scaleImage = Image(self.UILayer, (self.setScaleButton.posX - 28, self.setScaleButton.posY - 10), "SE", directories["scale"], 1, colour = (30, 30, 30))

        self.recentreButton = Button(self.UILayer, (155, 410), "SE", (80, 60), "Recentre", 10, (100, 100, 100), (0, -18), action = self.recentreFrame)
        self.recentreImage = Image(self.UILayer, (self.recentreButton.posX - 27, self.recentreButton.posY - 10), "SE", directories["recentreButton"], 1, colour = (30, 30, 30))

        self.setReferenceImageButton = Button(self.UILayer, (330, 335), "SE", (185, 30), "Set Reference Image", 12, (100, 100, 100), textOffset = (0, -1), action = self.setReferenceImage)

        self.removeReferenceImageButton = Button(self.UILayer, (105, 335), "SE", (30, 30), "", 12, (66, 41, 41), action = self.clearReferenceImage)
        self.removeReferenceImageIcon = Image(self.UILayer, (self.removeReferenceImageButton.posX - 1, self.removeReferenceImageButton.posY - 1), "SE", directories["bin"], 0.7, colour = (200, 200, 200))

        self.hideReferenceImageButton = Button(self.UILayer, (140, 335), "SE", (30, 30), "", 12, (100, 100, 100), action = self.toggleReferenceImageVisibility)
        self.hideReferenceImageIcon = Image(self.UILayer, (self.hideReferenceImageButton.posX - 1, self.hideReferenceImageButton.posY - 1), "SE", directories["hide"], 0.7, colour = (200, 200, 200))

        self.trackResSlider = Slider(self.UILayer, 15, self.colours["white"], self.colours["controlPoint"], (225, 278), "SE", 1, 100, (10, 100), value = self.mainTrack.perSegRes, action = self.mainTrack.changeRes, finishedUpdatingAction = self.mainTrack.changeResComplete, increment = 1)
        self.trackResLabel = Label(self.UILayer, 15, (330, 283), "SE", "Track Res", self.colours["white"])

        self.trackWidthSlider = Slider(self.UILayer, 15, self.colours["white"], self.colours["controlPoint"],(224, 243), "SE", 1, 100, (10, 30), value = self.mainTrack.width, suffix = 'm', action = self.mainTrack.changeWidth, finishedUpdatingAction = self.mainTrack.changeWidthComplete)
        self.trackWidthLabel = Label(self.UILayer, 15, (295, 248), "SE", "Width", self.colours["white"])

        self.racingLineSwitch = Switch(self.UILayer, (130, 175), "SE", 0.8, value = False)
        self.racingLineLabel = Label(self.UILayer, 15, (290, 173), "SE", "Racing Line", self.colours["white"])

        self.antialiasingSwitch = Switch(self.UILayer, (130, 147), "SE", 0.8, value = False)
        self.antialiasingLabel = Label(self.UILayer, 15, (300, 145), "SE", "Antialiasing", self.colours["white"])

        self.switchEndsSwitch = Switch(self.UILayer, (130, 117), "SE", 0.8, value = False)
        self.switchEndsLabel = Label(self.UILayer, 15, (299, 115), "SE", "Switch front", self.colours["white"])

        self.undoButton = Button(self.UILayer, (330, 95), "SE", (30, 30), "", 12, (100, 100, 100), action = self.undo)
        self.undoIcon = Image(self.UILayer, (self.undoButton.posX - 2, self.undoButton.posY - 2), "SE", directories["undo"], 0.8, colour = self.colours["white"])

        self.redoButton = Button(self.UILayer, (295, 95), "SE", (30, 30), "", 12, (100, 100, 100), action = self.redo)
        self.redoIcon = Image(self.UILayer, (self.redoButton.posX - 2, self.redoButton.posY - 2), "SE", directories["redo"], 0.8, colour = self.colours["white"])

        self.viewModeDropdown = Dropdown(self.UILayer, (225, 210), "SE", (150, 25),["Track", "Skeleton", "Curve", "Spline Dots", "Display"], 0, action = self.setViewMode)
        self.viewModeLabel = Label(self.UILayer, 15, (330, 205), "SE", "View Mode", (200, 200, 200))

        self.configAccordion = Accordion(self.UILayer, (50, 50), "SE", (305, 505), "Untitled Track",
                                         [self.saveButton, self.saveAsButton, self.openTrackButton, self.newTrackButton,
                                          self.setFinishButton, self.setFinishImage, self.setScaleButton,
                                          self.scaleImage, self.recentreButton, self.recentreImage,
                                          self.setReferenceImageButton, self.removeReferenceImageButton,
                                          self.removeReferenceImageIcon, self.hideReferenceImageButton,
                                          self.hideReferenceImageIcon,self.trackResSlider,
                                          self.trackResLabel, self.trackWidthSlider, self.trackWidthLabel,
                                          self.viewModeDropdown, self.viewModeLabel, self.racingLineSwitch, self.racingLineLabel,
                                          self.antialiasingSwitch, self.antialiasingLabel, self.switchEndsSwitch,
                                          self.switchEndsLabel, self.undoButton, self.undoIcon,
                                          self.redoButton, self.redoIcon],
                                          layerIndex = 0)

        self.trackScaleLabel = Label(self.UILayer, 15, (180, 30), "S", "", self.colours["white"])
        self.scalingErrorLabel = Label(self.UILayer, 12, (20, 60), "S", "", (227, 65, 50))

        self.finishIcon = Image(self.trackLayer, (0, 0), "", directories["finishLine"], 1, colour = (self.colours["white"]), show = False)
        self.finishDirIcon = Image(self.trackLayer, (0, 0), "", directories["arrow"], 1, colour = (self.colours["white"]), show = False)

        self.realDistanceTextInput = TextInput(self.UILayer, (20, 120), "S", (180, 50), 15, "Real Distance (m)", "", "m", ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '.'], enterAction = self.completeScaling, show = False)

        if len(sys.argv) > 1:
            self.openTrack(sys.argv[1])

    #Fit track to screen, in the middle
    def recentreFrame(self):
        minX = minY = float('inf')
        maxX = maxY = float('-inf')

        if len(self.mainTrack.points) >= 1:
            for point in self.mainTrack.returnPointCoords():
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
        if len(self.mainTrack.points) == 0:
            self.zoom = 1

        self.offsetPosition = ((((self.screenWidth / self.zoom) / 2) - centreX) * self.zoom, (((self.screenHeight / self.zoom) / 2) - centreY) * self.zoom)
        if self.referenceImage is not None:
            self.scaledReferenceImage = pygame.transform.scale_by(self.referenceImage, (self.zoom * self.referenceImageScale))

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
            self.scalingErrorLabel.text = "Please enter a valid number"

        if actualDistance is not None:
            if actualDistance == 0:
                self.scalingErrorLabel.text = "Please enter a number greater than 0"
            else:
                screenDistance = pointDistance(self.setScalePoint1, self.setScalePoint2)
                trackScale = actualDistance / screenDistance
                self.mainTrack.scalePoints(trackScale * (1 / self.mainTrack.scale))
                self.scaleReferenceImage(trackScale * (1 / self.mainTrack.scale))
                self.realDistanceTextInput.show = False
                self.userSettingScale = False
                self.mainTrack.calculateLength()
                self.scalingErrorLabel.text = ""
                self.mainTrack.history.addAction("SET SCALE", [trackScale])

                self.recentreFrame()

    def setFinish(self):
        self.userSettingFinish = True
        self.finishIndex = None
        self.finishDir = None

    #Sets finish line index
    def completeFinish(self):
        self.mainTrack.history.addAction("SET FINISH", [[self.mainTrack.finishIndex, self.mainTrack.finishDir], [self.finishIndex, self.finishDir]])

        self.mainTrack.finishIndex = self.finishIndex
        self.mainTrack.finishDir = self.finishDir

        self.userSettingFinish = False

    def setViewMode(self, mode):
        self.viewMode = mode

    #Allows user to choose reference image. Image is checked before being placed
    def setReferenceImage(self, imageDirectory = None, userPerformed = True):
        def openImage(directory):
            imageError = validateImageFile(directory)
            if imageError is None:
                if userPerformed:
                    self.mainTrack.history.addAction("SET REFERENCE IMAGE", [directory, self.mainTrack.referenceImageDir])
                self.mainTrack.referenceImageDir = directory
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
            root = tk.Tk()
            logo = tk.PhotoImage(file = directories["logo"])
            root.iconphoto(True, logo)

            root.withdraw()
            root.wm_attributes('-topmost', 1)
            imageExtensions = r"*.png *.jpeg *.jpg *.ppm *.gif *.tiff *.bmp"
            fileSelected = askopenfilename(title = "Open Image", filetypes = [("Images", imageExtensions)])
            root.destroy()
            return fileSelected

        if imageDirectory is None:
            tempDirectory = getFileName()
            if tempDirectory != '':
                validDir = os.path.isfile(tempDirectory)
                if not validDir:
                    Message(self.UILayer, "Invalid File", "Please select a valid file", "OK", "close", "grey")
                else:
                    openImage(tempDirectory)

        else:
            openImage(imageDirectory)

    #Adjust scale of reference image to match scale of track
    def scaleReferenceImage(self, scaleFactor = 1):
        if self.mainTrack.referenceImageDir is not None:
            self.referenceImageScale *= scaleFactor
            self.scaledReferenceImage = pygame.transform.scale_by(self.referenceImage, (self.zoom * self.referenceImageScale))

    def toggleReferenceImageVisibility(self):
        self.referenceImageVisibility = not self.referenceImageVisibility
        if self.referenceImageVisibility:
            self.hideReferenceImageIcon.updateImage(directories["hide"])
        else:
            self.hideReferenceImageIcon.updateImage(directories["show"])

    def clearReferenceImage(self):
        self.mainTrack.referenceImageDir = None

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
    def saveTrack(self, saveNewDirectory = False):
        trackData = self.mainTrack.getSaveState()
        trackData["properties"]["referenceImageScale"] = self.referenceImageScale

        def getFileName():
            root = tk.Tk()
            logo = tk.PhotoImage(file = directories["logo"])
            root.iconphoto(True, logo)

            root.wm_attributes('-topmost', 1)
            root.withdraw()
            fileSelected = asksaveasfilename(title = "Save Track", initialfile = 'Untitled.track', defaultextension = ".track", filetypes = [("Track Files", "*.track")], initialdir =  os.path.normpath(os.path.join(executionDir, 'tracks/')))
            root.destroy()
            return fileSelected

        validFile = True
        if self.saveDirectory is None or saveNewDirectory:
            tempDirectory = getFileName()
            if tempDirectory != '':
                validFile = os.path.isdir(os.path.dirname(tempDirectory))
            else:
                validFile = False
        else:
            tempDirectory = self.saveDirectory

        if validFile:
            try:
                with open(tempDirectory, "w") as outputFile:
                    json.dump(trackData, outputFile, indent=4)
                    pygame.display.set_caption(os.path.splitext(os.path.basename(tempDirectory))[0] + " - " + tempDirectory)
                    self.saveDirectory = tempDirectory
                    self.mainTrack.save()

            except Exception as error:
                Message(self.UILayer, "Can't Save", str(error), "OK", "close", "grey")
                self.saveDirectory = None

        elif not validFile and tempDirectory != '':
            Message(self.UILayer, "Can't Save", "Please select a valid directory", "OK", "close", "grey")
            self.saveDirectory = None

    #Opens track from specific directory specified by user. Track is checked first
    def openTrack(self, tempDirectory = None):
        def validateTrackFile(directory):
            error = None
            try:
                with open(directory) as loadFile:
                    try:
                        trackData = json.load(loadFile)
                        validate(instance = trackData, schema = self.trackFileSchema)
                    except:
                        error = "Invalid"

            except Exception as errorMessage:
                error = errorMessage

            return error

        def loadTrack(directory):
            validFile = validateTrackFile(directory)
            if validFile is None:
                with open(directory) as loadFile:
                    trackData = json.load(loadFile)

                    pointCoords = trackData["points"]
                    self.mainTrack.loadTrackPoints(pointCoords)

                    trackProperties = trackData["properties"]

                    self.trackWidthSlider.updateValue(trackProperties["width"], update = False)
                    self.mainTrack.width = trackProperties["width"]

                    self.trackResSlider.updateValue(trackProperties["trackRes"], update = False)
                    self.mainTrack.perSegRes = trackProperties["trackRes"]

                    self.mainTrack.finishIndex = trackProperties["finishIndex"]
                    self.mainTrack.finishDir = trackProperties["finishDir"]
                    self.mainTrack.updateCloseStatus(trackProperties["closed"], update = False)

                    self.referenceImageScale = trackProperties["referenceImageScale"]

                    self.mainTrack.UUID = trackData["UUID"]

                    if trackProperties["referenceImage"] is not None:
                        referenceImageData = PIL.Image.open(BytesIO(base64.b64decode(trackProperties["referenceImage"])))
                        referenceImageSaveDir = os.path.normpath(os.path.join(executionDir, "temp"))

                        if not os.path.exists(referenceImageSaveDir):
                            os.makedirs(referenceImageSaveDir)

                        referenceImageSaveDir = os.path.normpath(os.path.join(executionDir, "temp/referenceImage.png"))
                        referenceImageData.save(referenceImageSaveDir)
                        self.mainTrack.referenceImageDir = referenceImageSaveDir
                        self.setReferenceImage(referenceImageSaveDir, userPerformed = False)

                    self.mainTrack.computeTrack()
                    self.mainTrack.save()

                    self.saveDirectory = directory
                    self.recentreFrame()

            elif validFile == "Invalid":
                Message(self.UILayer, "Invalid File", "Please select a valid file", "OK", "close", "grey")
            else:
                Message(self.UILayer, "Can't Open", str(validFile), "OK", "close", "grey")

        def getFileName():
            root = tk.Tk()
            logo = tk.PhotoImage(file = directories["logo"])
            root.iconphoto(True, logo)

            root.withdraw()
            root.wm_attributes('-topmost', 1)
            fileSelected = askopenfilename(title = "Open Track", defaultextension = ".track", filetypes = [("Track Files", "*.track")], initialdir =  os.path.normpath(os.path.join(executionDir, 'tracks/')))
            root.destroy()
            return fileSelected

        def saveTrackFirst():
            message.close()
            self.saveTrack()
            loadTrack(tempDirectory)

        def discardTrack():
            message.close()
            if self.saveDirectory is None:
                deleteTrackTimes(self.mainTrack.UUID)
            loadTrack(tempDirectory)

        if tempDirectory is None:
            tempDirectory = getFileName()

        if tempDirectory != '':
            validDir = os.path.isfile(tempDirectory)
            if not validDir:
                message = Message(self.UILayer, "Invalid File", "Please select a valid file", "OK", "close", "grey")

            if tempDirectory != '' and self.mainTrack.isSaved() == False and validDir:
                message = Message(self.UILayer, "Sure?", "You currently have an unsaved track open", "Save", saveTrackFirst,
                        "grey", "Discard", discardTrack, "red")
            else:
                loadTrack(tempDirectory)

    #Clears current track, asks user before clearing
    def newTrack(self):
        def saveTrackFirst():
            message.close()
            self.saveTrack()
            clearTrackSequence()

        def discardTrack():
            message.close()
            if self.saveDirectory is None:
                deleteTrackTimes(self.mainTrack.UUID)
            clearTrackSequence()

        def clearTrackSequence():
            self.mainTrack.clear()
            self.recentreFrame()

            self.trackResSlider.updateValue(self.mainTrack.perSegRes, update = False)
            self.trackWidthSlider.updateValue(self.mainTrack.width, update = False)

            self.viewModeDropdown.index = 0

            self.racingLineSwitch.value = False
            self.antialiasingSwitch.value = False
            self.switchEndsSwitch.value = False

            self.saveDirectory = None

        if not self.mainTrack.isSaved():
            message = Message(self.UILayer, "Sure?", "You currently have an unsaved track open", "Save", saveTrackFirst, "grey",
                    "Discard", discardTrack, "red")

        elif self.saveDirectory is not None:
            self.saveTrack()
            clearTrackSequence()

        else:
            self.recentreFrame()

    def closeTrack(self):
        def closeError():
            unsavedTrackError.close()
            self.closeCount = 0

        def saveTrackFirst():
            global running
            self.saveTrack()
            running = False

        def discardTrack():
            global running
            if self.saveDirectory is None:
                deleteTrackTimes(self.mainTrack.UUID)
            running = False

        if self.closeCount == 0:
            unsavedTrackError = Message(self.UILayer, "Sure?", "You currently have an unsaved track open", "Save",
                                        saveTrackFirst, "grey", "Discard", discardTrack, "red", closeError)
        self.closeCount += 1

    #Undoes previous action
    def undo(self):
        undoActions = self.mainTrack.history.undo()
        for action in undoActions:
            if action.command == "SET REFERENCE IMAGE":
                self.mainTrack.referenceImageDir = action.params[1]
                if self.mainTrack.referenceImageDir is not None:
                    self.setReferenceImage(self.mainTrack.referenceImageDir, userPerformed = False)

        undoActions = self.mainTrack.undo(undoActions)
        for action in undoActions:
            if action.command == "SET SCALE":
                self.scaleReferenceImage(1 / (action.params[0] * (1 / self.mainTrack.scale)))
                self.recentreFrame()

    #Redoes previously undone action
    def redo(self):
        redoActions = self.mainTrack.history.redo()
        for action in redoActions:
            if action.command == "SET REFERENCE IMAGE":
                self.mainTrack.referenceImageDir = action.params[0]
                if self.mainTrack.referenceImageDir is not None:
                    self.setReferenceImage(self.mainTrack.referenceImageDir, userPerformed = False)

        redoActions = self.mainTrack.redo(redoActions)
        for action in redoActions:
            if action.command == "SET SCALE":
                self.scaleReferenceImage(action.params[0] * (1 / self.mainTrack.scale))
                self.recentreFrame()

    #Where all the events are passed to be processed
    def handleEvents(self, events):
        global running

        self.mainTrack.history.checkIfSaved()

        self.events = events
        for event in events:
            if event.type == pygame.QUIT:
                if not self.mainTrack.isSaved():
                    self.closeTrack()

                if self.mainTrack.isSaved() or self.closeCount > 1:
                    running = False

            #Adding control point
            if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed()[0] and (self.mainTrack.mouseHovering is None) and (not self.UILayer.mouseOnLayer((self.mousePosX, self.mousePosY))) and (not programUI.mouseOnLayer((self.mousePosX, self.mousePosY))) and not (self.userSettingScale or self.userSettingFinish) and (not self.UIClick):
                index = -1
                if self.switchEndsSwitch.value:
                    index = 0

                onLine = False
                if len(self.mainTrack.points) >= 2:
                    onLine, nearPointSegment, nearestPoint, nearPointIndex = self.mainTrack.pointOnCurve((self.mousePosX - self.offsetPosition[0]) / self.zoom, (self.mousePosY - self.offsetPosition[1]) / self.zoom, 20)
                    if onLine:
                        index = nearPointSegment

                validPlacement = (not self.mainTrack.closed or onLine)
                if validPlacement:
                    self.mainTrack.add(ControlPoint((self.mousePosX - self.offsetPosition[0]) / self.zoom,
                                                    (self.mousePosY - self.offsetPosition[1]) / self.zoom),
                                       index = index, userPerformed = True)

            #Removing control point
            if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed()[2] and (self.mainTrack.mouseHovering is not None) and (not self.UILayer.mouseOnLayer((self.mousePosX, self.mousePosY))) and (not programUI.mouseOnLayer((self.mousePosX, self.mousePosY))) and not (self.userSettingScale or self.userSettingFinish) and (not self.UIClick):
                index = self.mainTrack.mouseHovering
                if not(self.mainTrack.closed and ((index == 0) or (index == len(self.mainTrack.points) - 1))):
                    self.mainTrack.remove(index = index, userPerformed = True)

            #Set offset pivot
            if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed()[1]:
                self.pivotPos = (self.mousePosX - self.offsetPosition[0], self.mousePosY - self.offsetPosition[1])

            if event.type == pygame.MOUSEBUTTONDOWN and (self.UILayer.mouseOnLayer((self.mousePosX, self.mousePosY))):
                self.UIClick = True

            #Set offset pivot
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    if self.zoom < self.upperZoomLimit:
                        beforeZoom = self.zoom
                        self.zoom *= 1 + self.zoomIncrement

                        if self.zoom > self.upperZoomLimit:
                            self.zoom = self.upperZoomLimit

                        zoomDifference = (self.zoom/beforeZoom) - 1
                        self.offsetPosition = (int(self.offsetPosition[0] - (self.mousePosX - self.offsetPosition[0]) * zoomDifference), int(self.offsetPosition[1] - (self.mousePosY - self.offsetPosition[1]) * zoomDifference))

                        if self.mainTrack.referenceImageDir is not None:
                            self.scaledReferenceImage = pygame.transform.scale_by(self.referenceImage, (self.zoom * self.referenceImageScale))

                elif event.y < 0:
                    if self.zoom > self.lowerZoomLimit:
                        beforeZoom = self.zoom
                        self.zoom *= 1 - self.zoomIncrement

                        if self.zoom < self.lowerZoomLimit:
                            self.zoom = self.lowerZoomLimit

                        zoomDifference = (beforeZoom/self.zoom) - 1
                        self.offsetPosition = (int(self.offsetPosition[0] + (self.mousePosX - self.offsetPosition[0]) * zoomDifference), int(self.offsetPosition[1] + (self.mousePosY - self.offsetPosition[1]) * zoomDifference))

                        if self.mainTrack.referenceImageDir is not None:
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
                        self.userSettingScale = False

            #Logic for setting finish
            if self.userSettingFinish:
                if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed()[0] and (not self.UILayer.mouseOnLayer((self.mousePosX, self.mousePosY))) and (not programUI.mouseOnLayer((self.mousePosX, self.mousePosY))):
                    if self.finishIndex is None:
                        self.finishIndex = ((self.mousePosX - self.offsetPosition[0]) / self.zoom, (self.mousePosY - self.offsetPosition[1]) / self.zoom)
                        onLine, nearPointSegment, nearestPointCoords, nearestPoint = self.mainTrack.pointOnCurve(self.finishIndex[0], self.finishIndex[1], (self.mainTrack.width / 2))
                        if onLine:
                            nearestPoint = max(5, nearestPoint)
                            self.finishIndex = nearestPoint / self.mainTrack.perSegRes
                        else:
                            self.finishIndex = None

                    elif self.finishIndex is not None:
                        self.completeFinish()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.userSettingFinish = False

    def update(self):
        self.mainTrack.updateOffsetValues(self.offsetPosition, self.zoom)

        self.previousScreenWidth = self.screenWidth
        self.previousScreenHeight = self.screenHeight

        self.screenWidth, self.screenHeight = screen.get_size()
        self.mousePosX = pygame.mouse.get_pos()[0]
        self.mousePosY = pygame.mouse.get_pos()[1]

        screen.fill(self.colours["background"])

        if (self.previousScreenWidth != self.screenWidth) or (self.previousScreenHeight != self.screenHeight):
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

        self.mainTrack.showRacingLine = self.racingLineSwitch.value

        self.drawGrid(self.offsetPosition, 50 * self.zoom, 1, self.colours["innerGrid"])

        screenRect = pygame.Rect((0, 0), (self.screenWidth + 15, self.screenHeight + 15))

        #Draws reference image to screen
        if (self.mainTrack.referenceImageDir is not None) and self.referenceImageVisibility:
            self.referenceImageRect = self.scaledReferenceImage.get_rect(center = self.offsetPosition)
            screen.blit(self.scaledReferenceImage, self.referenceImageRect)

        if self.mainTrack.referenceImageDir is None:
            self.hideReferenceImageButton.disabled = True
            self.removeReferenceImageButton.disabled = True
            self.hideReferenceImageIcon.updateImage(directories["hide"])
        else:
            self.hideReferenceImageButton.disabled = False
            self.removeReferenceImageButton.disabled = False

        if not (self.userSettingScale or self.userSettingFinish) and (not self.UIClick):
            self.mainTrack.update((self.mousePosX - self.offsetPosition[0]) / self.zoom, (self.mousePosY - self.offsetPosition[1]) / self.zoom, self.zoom, self.screenWidth, self.screenHeight, self.screenBorder, self.offsetPosition, screenRect, directories)
        self.mainTrack.draw(self.colours, self.switchEndsSwitch.value, self.viewMode, self.antialiasingSwitch.value)

        #Algorithm for setting track scale - draw line between 2 mouse positions
        if self.userSettingScale:
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

                pygame.draw.line(screen, (200, 200, 200), lineStart, lineEnd, 5)
                pygame.draw.line(screen, (200, 200, 200), lineStart_EndStop[0], lineStart_EndStop[1], 5)
                pygame.draw.line(screen, (200, 200, 200), lineEnd_EndStop[0], lineEnd_EndStop[1], 5)

        #Allows user to set whether track is clockwise or anticlockwise
        if self.userSettingFinish:
            transparentSurface = pygame.Surface((self.screenWidth, self.screenHeight), pygame.SRCALPHA)
            pygame.draw.rect(transparentSurface, (50, 50, 50, 100), (0, 0, self.screenWidth, self.screenHeight))
            screen.blit(transparentSurface, (0, 0))

            if self.finishIndex is not None:
                if angle(offsetPoints((self.mousePosX, self.mousePosY), self.offsetPosition, self.zoom, True, True),
                         self.mainTrack.splinePoints[int(self.finishIndex * self.mainTrack.perSegRes)],
                         extendPointsBack(self.mainTrack.splinePoints)[int(self.finishIndex * self.mainTrack.perSegRes) + 1]) < 90:
                    self.finishDir = True
                else:
                    self.finishDir = False

        else:
            self.finishIndex = self.mainTrack.finishIndex
            self.finishDir = self.mainTrack.finishDir

        if self.finishIndex is not None:
            if ((len(self.mainTrack.points) - 1) < self.finishIndex) or (self.finishIndex < 0):
                self.mainTrack.finishIndex = None
                self.mainTrack.finishDir = None

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
            finishPointCoords = (self.mainTrack.splinePoints[int(self.finishIndex * self.mainTrack.perSegRes)])
            finishPointNeighbourCoords = (
            extendPointsBack(self.mainTrack.splinePoints)[int(self.finishIndex * self.mainTrack.perSegRes) + 1])
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

        if self.mainTrack.isSaved():
            saveCharacter = ""
        else:
            saveCharacter = "*"

        if self.saveDirectory is None:
            newCaption = "Untitled Track" + saveCharacter
            self.configAccordion.titleText = "Untitled Track" + saveCharacter
        else:
            newCaption = str(
                os.path.splitext(os.path.basename(self.saveDirectory))[0] + saveCharacter + " - " + self.saveDirectory)
            self.configAccordion.titleText = str(os.path.splitext(os.path.basename(self.saveDirectory))[0] + saveCharacter)

        if self.lastCaption != newCaption:
            pygame.display.set_caption(newCaption)

        self.lastCaption = newCaption
        self.mouseXLabel.text = ("x: " + str(int(((self.mousePosX * 1) - self.offsetPosition[0]) / self.zoom)))
        self.mouseYLabel.text = ("y: " + str(int(((self.mousePosY * 1) - self.offsetPosition[1]) / self.zoom)))
        self.scaleLabel.text = ("view: " + str(int(self.zoom * 100)) + "%")

        #Checks if there are any items left to undo
        if len(self.mainTrack.history.undoStack) == 0:
            self.undoButton.disabled = True
            self.undoIcon.colour = (90, 90, 90)
        else:
            self.undoButton.disabled = False
            self.undoIcon.colour = self.colours["white"]

        #Checks if there are any items left to redo
        if len(self.mainTrack.history.redoStack) == 0:
            self.redoButton.disabled = True
            self.redoIcon.colour = (90, 90, 90)
        else:
            self.redoButton.disabled = False
            self.redoIcon.colour = self.colours["white"]

        #Determines whether track length should be in m or km
        if self.mainTrack.scale is not None:
            trackScaleReduced = int((self.mainTrack.scale * 150) / self.zoom)

            if self.mainTrack.length > 1000:
                lengthText = "length: " + str(int(self.mainTrack.length) / 1000) + "km"
            else:
                lengthText = "length: " + str(int(self.mainTrack.length)) + "m"

            self.trackScaleLabel.text = str(trackScaleReduced) + "m  | " + lengthText

            pygame.draw.line(screen, (200, 200, 200), (20, self.screenHeight - 35), (20, self.screenHeight - 20), 2)
            pygame.draw.line(screen, (200, 200, 200), (20, self.screenHeight - 20), (170, self.screenHeight - 20), 2)
            pygame.draw.line(screen, (200, 200, 200), (170, self.screenHeight - 35), (170, self.screenHeight - 20), 2)
        else:
            self.trackScaleLabel.text = ""

        self.trackLayer.display(self.screenWidth, self.screenHeight, self.events, self.offsetPosition, self.zoom)
        self.UILayer.display(self.screenWidth, self.screenHeight, self.events)

class TrackRacing (Scene):
    def __init__(self, trackEditor):
        super().__init__()
        self.trackEditor = trackEditor
        self.screenBorder = 5
        self.uniquenessToken = None

        self.offsetPosition = (0, 0)
        self.zoom = 2
        self.upperZoomLimit = 3
        self.lowerZoomLimit = 0.5

        self.screenWidth, self.screenHeight = screen.get_size()
        self.mousePosX = 0
        self.mousePosY = 0

        self.events = []

        self.deltaTime = 0

        pygame.joystick.init()
        self.controllers = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]

        self.steeringInput = 0
        self.accelerationInput = 0

        self.colours = {"background": (101, 126, 51),
                        "curve": (128, 128, 128),
                        "controlPoint": (24, 150, 204),
                        "frontControlPoint": (204, 138, 24),
                        "mainGrid": (30, 30, 30),
                        "innerGrid": (25, 25, 25),
                        "white": (200, 200, 200),
                        "mainTrack": (100, 100, 100)}

        self.mainFont = directories["mainFont"]

        self.UILayer = Layer(screen, pygame, mainFont, directories)
        self.speedometer = Label(self.UILayer, 30, (180, 100), "SE", "121mph", self.colours["white"], bold = True)
        self.timer = Label(self.UILayer, 17, (180, 65), "SE", "00:00.00", (200, 200, 200))

        self.viewLeaderboardButton = Button(self.UILayer, (50, 90), "SW", (200, 40), "View Leaderboard", 15, (100, 100, 100), action = self.viewLeaderboard)
        self.leaderboardView = None

        self.viewControlsButton = Button(self.UILayer, (270, 90), "SW", (200, 40), "View Controls", 15, (100, 100, 100), action = self.viewControls)
        self.controlsView = None

        self.deleteRaceTimesButton = Button(self.UILayer, (105, 335), "SE", (30, 30), "", 12, (66, 41, 41), action = self.deleteRaceTimes, show = False)
        self.deleteRaceTimesIcon = Image(self.UILayer, (self.deleteRaceTimesButton.posX - 1, self.deleteRaceTimesButton.posY - 1), "SE", directories["bin"], 0.7, colour = (200, 200, 200), show = False)

        self.zoomAdjustmentSlider = Slider(self.UILayer, 15, (200, 200, 200), self.colours["controlPoint"], (100, 120), "SW", 1, 105, (self.lowerZoomLimit, self.upperZoomLimit), 2.0001, precision = 1, action = self.updateZoom, suffix = 'x')
        self.zoomAdjustmentLabel = Label(self.UILayer, 15, (50, 122), "SW", "Zoom", (200, 200, 200))

        self.car = Car(pygame, screen, directories, self.trackEditor.mainTrack)

        self.timerStart = None
        self.timerEnd = None

        self.pause = False
        self.pauseStart = None
        self.userPaused = False

    def updateZoom(self, value):
        self.zoom = value

    def reset(self):
        self.car.reset()

        self.timerStart = None
        self.timerEnd = None

        self.car.dead = False
        self.timer.text = secondToRaceTimer(0)
        self.timer.colour = (200, 200, 200)

    def deleteRaceTimes(self):
        def delete():
            deleteTrackTimes(self.trackEditor.mainTrack.UUID)
            message.close()
            self.viewLeaderboard()

        def cancel():
            message.close()
            self.viewLeaderboard()

        self.leaderboardView.close()
        self.deleteRaceTimesButton.show = False
        self.deleteRaceTimesIcon.show = False

        message = Message(self.UILayer, "Sure?", ["You are about to delete the race times", "for this track"], "Cancel", cancel,
                        "grey", "Delete", delete, "red")

    def uploadTime(self, raceTime):
        conn = sqlite3.connect(directories["raceTimes"])
        cursor = conn.cursor()
        cursor.execute(f'''INSERT INTO TIMES VALUES ('{self.trackEditor.mainTrack.UUID}', {raceTime}, datetime('now','localtime'))''')
        conn.commit()
        conn.close()

    def deleteSlowTimes(self):
        times = self.getTimes(self.trackEditor.mainTrack.UUID)
        if len(times) > 10:
            slowestAcceptableTime = times[9]

            conn = sqlite3.connect(directories["raceTimes"])
            cursor = conn.cursor()
            cursor.execute(f'''DELETE FROM TIMES WHERE UUID = "{self.trackEditor.mainTrack.UUID}" and (time > {slowestAcceptableTime[0]} or (time = {slowestAcceptableTime[0]} and date > "{slowestAcceptableTime[1]}"))''')
            conn.commit()
            conn.close()

    def getTimes(self, UUID):
        conn = sqlite3.connect(directories["raceTimes"])
        cursor = conn.cursor()
        cursor.execute(f"SELECT time, date FROM TIMES WHERE UUID = '{UUID}' ORDER BY time, date")
        times = cursor.fetchall()
        return times

    def viewLeaderboard(self):
        def closeLeaderboard():
            self.leaderboardView.close()
            self.deleteRaceTimesButton.show = False
            self.deleteRaceTimesIcon.show = False


        if self.leaderboardView in self.UILayer.elements:
            closeLeaderboard()
        else:
            times = self.getTimes(self.trackEditor.mainTrack.UUID)

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
                        lineText = f"{"{:<15}".format(f"{number}.")}-          "
                        leaderboardMessages.append(lineText)

            self.leaderboardView = Message(self.UILayer, "Leaderboard", leaderboardMessages, dimensions = (400, 270), closeAction = closeLeaderboard, layerIndex = 0)
            if len(times) > 0:
                self.deleteRaceTimesButton.show = True
                self.deleteRaceTimesIcon.show = True

    def viewControls(self):
        if self.controlsView in self.UILayer.elements:
            self.controlsView.close()
        else:
            allControls = ["Keyboard:", "Use WASD/arrow keys to move", "'R' to reset", "'P' to pause",
                           "",
                           "Controller:", "R2 to accelerate, L2 to brake", "Left joy to steer", "'X' to reset", "'Menu' to pause"]

            self.controlsView = Message(self.UILayer, "Controls", allControls, dimensions = (400, 270), layerIndex = 0)

    def togglePause(self, userPaused = False):
        self.pause = not self.pause
        if self.pause:
            self.userPaused = userPaused
            self.pauseStart = time.time()
        else:
            if self.timerStart is not None and self.timerEnd is None:
                self.timerStart += (time.time() - self.pauseStart)
                self.pauseStart = None

    #Where all the events are passed to be processed
    def handleEvents(self, events):
        global running

        self.controllers = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]

        self.accelerationInput = 0
        self.steeringInput = 0

        #Get input from connected controller
        if len(self.controllers) > 0:
            self.steeringInput = pygame.joystick.Joystick(0).get_axis(0)
            self.accelerationInput = ((pygame.joystick.Joystick(0).get_axis(5)) / 2) + 0.5
            braking = ((pygame.joystick.Joystick(0).get_axis(4)) / 2) + 0.5
            if braking > 0:
                self.accelerationInput = -braking

        #If arrow/WASD keys pressed, override controller input
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_RIGHT] or keys[pygame.K_LEFT] or keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]:
            self.accelerationInput = 0
            self.steeringInput = 0

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.accelerationInput = 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.accelerationInput = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.steeringInput = 1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.steeringInput = -1

        self.events = events
        for event in events:
            #Reset car position
            if event.type == pygame.JOYBUTTONDOWN:
                if pygame.joystick.Joystick(0).get_button(2): #X
                    self.reset()
                if pygame.joystick.Joystick(0).get_button(6): #Menu
                    self.togglePause(True)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                if event.key == pygame.K_p:
                    self.togglePause(True)
                if event.key == pygame.K_l:
                    self.viewLeaderboard()
                if event.key == pygame.K_c:
                    self.viewControls()

    def update(self):
        self.offsetPosition = ((-self.car.position.x * self.zoom) + (self.screenWidth / 2), (-self.car.position.y * self.zoom) + (self.screenHeight / 2))
        self.trackEditor.mainTrack.updateOffsetValues(self.offsetPosition, self.zoom)

        self.screenWidth, self.screenHeight = screen.get_size()
        self.mousePosX = pygame.mouse.get_pos()[0]
        self.mousePosY = pygame.mouse.get_pos()[1]

        screen.fill(self.colours["background"])

        if self.uniquenessToken != self.trackEditor.mainTrack.getUniquenessToken(): #Track has changed
            self.uniquenessToken = self.trackEditor.mainTrack.getUniquenessToken()

            if len(self.trackEditor.mainTrack.points) >= 2:
                self.reset()
                self.trackEditor.mainTrack.deKink()

        self.trackEditor.mainTrack.draw(self.colours, True, "Display", True)

        if not self.pause:
            self.car.update(self.steeringInput, self.accelerationInput, self.offsetPosition, self.zoom, deltaTime)
        self.car.display()

        if (self.timerStart is None) and (self.car.position != self.trackEditor.mainTrack.getStartPos()[0]):
            self.timerStart = time.time()

        if self.trackEditor.mainTrack.closed:
            startPos, startAngle, startIndex, startDir = self.trackEditor.mainTrack.getStartPos()
            if startDir:
                crossedFinishLine = (self.car.previousSplineIndex == ((startIndex - 1) % len(self.trackEditor.mainTrack.splinePoints))) and (self.car.nearestSplineIndex == startIndex)
                cheated = (self.car.previousSplineIndex == ((startIndex + 1) % len(self.trackEditor.mainTrack.splinePoints))) and (self.car.nearestSplineIndex == startIndex)
            else:
                crossedFinishLine = (self.car.previousSplineIndex == ((startIndex + 1) % len(self.trackEditor.mainTrack.splinePoints))) and (self.car.nearestSplineIndex == startIndex)
                cheated = (self.car.previousSplineIndex == ((startIndex - 1) % len(self.trackEditor.mainTrack.splinePoints))) and (self.car.nearestSplineIndex == startIndex)
        else:
            crossedFinishLine = (self.car.nearestSplineIndex == len(self.trackEditor.mainTrack.splinePoints) - 1)
            cheated = False

        if cheated:
            self.car.dead = True

        def closeMessage():
            message.close()
            self.togglePause()

        if crossedFinishLine:
            if (self.timerEnd is None) and (self.timerStart is not None) and (not self.car.offTrack):
                self.timerEnd = time.time()
                validTime = not self.car.dead
                if validTime:
                    raceTime = float("{:.2f}".format(self.timerEnd - self.timerStart))

                    times = self.getTimes(self.trackEditor.mainTrack.UUID)
                    if len(times) > 0:
                        if times[0][0] > raceTime:
                            timeDifference = float("{:.2f}".format(times[0][0] - raceTime))
                            self.togglePause(True)
                            message = Message(self.UILayer, "New Highscore!", [f"You beat the current highscore ({secondToRaceTimer(times[0][0])})", f"by {timeDifference}s"] , "Continue", closeMessage, (100, 100, 100), closeAction = closeMessage)

                    self.uploadTime(raceTime)
                    self.deleteSlowTimes()

        self.car.previousSplineIndex = self.car.nearestSplineIndex

        self.speedometer.text = f"{pixToMiles(self.car.velocity.x, self.car.scale)} mph"

        if not self.pause or (self.pause and self.timerEnd is not None):
            if self.timerStart is not None:
                timerEnd = time.time()
                if self.timerEnd is not None:
                    timerEnd = self.timerEnd
                timerValue = timerEnd - self.timerStart
                self.timer.text = secondToRaceTimer(timerValue)

            if (self.timerStart is not None) and (self.timerEnd is None):
                if self.car.dead:
                    self.timer.colour = (200, 0, 0)
                else:
                    self.timer.colour = (200, 200, 200)

        if self.pause:
            transparentSurface = pygame.Surface((self.screenWidth, self.screenHeight), pygame.SRCALPHA)
            pygame.draw.rect(transparentSurface, (50, 50, 50, 200), (0, 0, self.screenWidth, self.screenHeight))
            screen.blit(transparentSurface, (0, 0))

        if self.deleteRaceTimesButton.show:
            self.deleteRaceTimesButton.posX = (self.screenWidth / 2) + 180
            self.deleteRaceTimesButton.posY = (self.screenHeight / 2) + 120

            self.deleteRaceTimesIcon.posX = self.deleteRaceTimesButton.posX - 1
            self.deleteRaceTimesIcon.posY = self.deleteRaceTimesButton.posY - 1

        self.UILayer.display(self.screenWidth, self.screenHeight, self.events)

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

    fpsLabel.text = ("fps: " + str(int(clock.get_fps())))

    pygame.display.flip()
    deltaTime = clock.tick(60) / 1000 #Refresh Rate
pygame.quit()
