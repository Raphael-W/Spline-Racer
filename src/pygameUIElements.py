import os
import time
from utils import *

import pygame

class UIElement:
    def __init__(self, layer, pos, stick, show = True, layerIndex = -1):
        self.contextualPosX = pos[0]
        self.contextualPosY = pos[1]

        self.posX = pos[0]
        self.posY = pos[1]
        self.stick = stick.lower()

        self.boundingBox = layer.pygame.Rect(0, 0, 0, 0)

        self.layer = layer
        self.layerIndex = layerIndex

        self.show = show

        layer.add(self)

    def update(self):
        pass

    def alwaysUpdate(self):
        pass

    def display(self):
        pass

    def returnBoundingBox(self):
        return self.boundingBox.topleft, self.boundingBox.topright, self.boundingBox.bottomleft, self.boundingBox.bottomright

    def updateContextualPos(self):
        contextualPosX = self.posX
        contextualPosY = self.posY

        #Offset position
        offsetX, offsetY = self.layer.offset

        contextualPosX = (((contextualPosX + (self.boundingBox.size[0] / 2)) * self.layer.zoom) - (self.boundingBox.size[0] / 2) + offsetX)
        contextualPosY = (((contextualPosY + (self.boundingBox.size[1] / 2)) * self.layer.zoom) - (self.boundingBox.size[1] / 2) + offsetY)

        #Apply stickiness to position
        vertValid = not (("n" in self.stick) and ("s" in self.stick))
        horValid = not (("e" in self.stick) and ("w" in self.stick))
        charValid = all([True for char in self.stick if char in ["n", "e", "s", "w", "v", "h"]])

        horStick = None
        vertStick = None
        for char in self.stick:
            if char in ["n", "s", "v"]:
                vertStick = char
            if char in ["e", "w", "h"]:
                horStick = char


        if vertValid and horValid and charValid and (len(self.stick) > 0):
            if horStick == "e":
                contextualPosX = self.layer.screenWidth - self.posX
            elif horStick == "h":
                contextualPosX = (self.layer.screenWidth / 2) - self.posX

            if vertStick == "s":
                contextualPosY = self.layer.screenHeight - self.posY
            elif vertStick == "v":
                contextualPosY = (self.layer.screenHeight / 2) - self.posY

        self.contextualPosX, self.contextualPosY = contextualPosX, contextualPosY

    def close(self):
        if self in self.layer.elements:
            self.layer.elements.remove(self)

class Button (UIElement):
    def __init__(self, layer, pos, stick, dimensions, text, fontSize, colour, textOffset = (0, 0), roundedCorners = 10, surface = None, action = None, show = True, disabled = False, layerIndex = -1):
        super().__init__(layer, pos, stick, show, layerIndex)
        self.width = dimensions[0]
        self.height = dimensions[1]
        self.boundingBox = layer.pygame.Rect(self.posX, self.posY, self.width, self.height)
        self.roundedCorners = roundedCorners

        self.surface = surface
        if surface is None:
            self.surface = self.layer.screen

        self.text = text
        self.lastText = None
        self.textOffset = textOffset
        self.font = layer.pygame.freetype.Font(layer.fontName, fontSize)
        self.textRect = self.font.get_rect(self.text)
        self.textSurface = pygame.Surface(self.textRect.size, self.layer.pygame.SRCALPHA)

        self.action = action

        self.stepBeforeClick = False
        self.mouseHovering = False
        self.actionRun = False
        self.pointSelected = False

        self.colour = colour
        self.baseColour = colour
        self.hoverColour = (colour[0] - (colour[0] * 0.2),
                            colour[1] - (colour[1] * 0.2),
                            colour[2] - (colour[2] * 0.2))

        self.pressedColour = (colour[0] - (colour[0] * 0.4),
                              colour[1] - (colour[1] * 0.4),
                              colour[2] - (colour[2] * 0.4))

        self.disabled = disabled
        self.lastDisabled = None

    def update(self):
        self.updateContextualPos()

        if (self.lastText != self.text) or (self.lastDisabled != self.disabled):
            self.boundingBox = self.layer.pygame.Rect(self.contextualPosX, self.contextualPosY, self.width, self.height)
            self.textRect = self.font.get_rect(self.text)
            self.textSurface = pygame.Surface(self.textRect.size, self.layer.pygame.SRCALPHA)

            if self.disabled:
                self.font.render_to(self.textSurface, (0, 0, self.textRect.width, self.textRect.height), self.text, (160, 160, 160))
            else:
                self.font.render_to(self.textSurface, (0, 0, self.textRect.width, self.textRect.height), self.text, (250, 250, 250))

            self.lastText = self.text
            self.lastDisabled = self.disabled

        self.textRect.center = (self.boundingBox.center[0] - self.textOffset[0], self.boundingBox.center[1] - self.textOffset[1])

        if not self.disabled:
            mousePos = self.layer.pygame.mouse.get_pos()
            self.mouseHovering = (((self.contextualPosX + self.width / 2) + ((self.width / 2) + 2) > mousePos[0] > (self.contextualPosX + self.width / 2) - ((self.width / 2) + 2)) and
                                  ((self.contextualPosY + self.height / 2) + ((self.height / 2) + 2) > mousePos[1] > (self.contextualPosY + self.height / 2) - ((self.height / 2) + 2)))

            if self.mouseHovering:
                self.colour = self.hoverColour
            else:
                self.colour = self.baseColour

            self.pointSelected = self.mouseHovering and self.layer.pygame.mouse.get_pressed()[0]
            if self.pointSelected:
                self.colour = self.pressedColour

            if self.pointSelected and self.stepBeforeClick:
                if self.action is not None and not self.actionRun:
                    self.action()
                    self.actionRun = True
            else:
                self.actionRun = False

            self.stepBeforeClick = self.mouseHovering and not(self.layer.pygame.mouse.get_pressed()[0])

        else:
            self.colour = self.pressedColour

    def display(self):
        self.boundingBox = self.layer.pygame.Rect(self.contextualPosX, self.contextualPosY, self.width, self.height)
        self.layer.pygame.draw.rect(self.surface, self.colour, self.boundingBox, 0, self.roundedCorners)
        self.surface.blit(self.textSurface, self.textRect)

class Label (UIElement):
    def __init__(self, layer, fontSize, pos, stick, text, colour, bold = False, show = True, layerIndex = -1):
        super().__init__(layer, pos, stick, show, layerIndex)
        self.text = text
        self.lastText = None

        self.font = layer.pygame.freetype.Font(layer.fontName, fontSize)
        self.bold = bold
        self.font.strong = bold

        self.textSize = self.font.get_rect(self.text).size
        self.textSurface = pygame.Surface(self.textSize, self.layer.pygame.SRCALPHA)
        self.colour = colour

    def update(self):
        self.updateContextualPos()
        if self.text != self.lastText:
            self.updateTextSize()
        self.boundingBox = self.layer.pygame.Rect((self.contextualPosX - 10, self.contextualPosY - 10), (self.textSize[0] + 20, self.textSize[1] + 20))

    def updateFontSize(self, newFontSize):
         self.font = self.layer.pygame.freetype.Font(self.layer.fontName, newFontSize)
         self.font.strong = self.bold

    def updateTextSize(self):
        self.textSize = self.font.get_rect(self.text).size
        self.textSurface = pygame.Surface(self.textSize, self.layer.pygame.SRCALPHA)
        self.font.render_to(self.textSurface, (0, 0), self.text, self.colour)
        self.lastText = self.text

    def display(self):
        self.layer.screen.blit(self.textSurface, (self.contextualPosX, self.contextualPosY))

class Slider (UIElement):
    def __init__(self, layer, fontSize, barColour, handleColour, pos, stick, size, length, valueRange, value = 0, action = None, increment = None, precision = None, suffix = None, finishedUpdatingAction = None, show = True, disabled = False, hideLabel = False, layerIndex = -1):
        super().__init__(layer, pos, stick, show, layerIndex)

        self.barColour = barColour
        self.displayBarColour = self.barColour

        self.handleColour = handleColour
        self.selectedHandleColour = (handleColour[0] - (handleColour[0] * 0.4),
                                     handleColour[1] - (handleColour[1] * 0.4),
                                     handleColour[2] - (handleColour[2] * 0.4))
        self.displayColour = handleColour

        self.font = layer.pygame.freetype.Font(layer.fontName, fontSize)
        self.previousValue = None
        self.valueLabelSurface = pygame.Surface((0, 0), pygame.SRCALPHA)

        self.size = size
        self.length = length
        self.valueRange = valueRange
        self.value = value
        self.increment = increment
        self.precision = precision
        self.suffix = suffix
        if not (valueRange[0] <= value <= valueRange[1]): self.value = valueRange[0]

        self.mouseHovering = False
        self.handleX = (self.length / (self.valueRange[1] - self.valueRange[0])) * (self.value - self.valueRange[0])
        self.handleSelected = False
        self.handleSelectedLast = False
        self.mouseDownLast = False
        self.handleSize = int(10 * self.size)

        self.initialValue = value
        self.action = action
        self.finishedUpdatingAction = finishedUpdatingAction

        self.show = show
        self.disabled = disabled
        self.hideLabel = hideLabel

    def update(self):
        self.updateContextualPos()

        if not self.disabled:
            mouseX, mouseY = self.layer.pygame.mouse.get_pos()
            self.handleSize = int(10 * self.size)
            self.boundingBox = self.layer.pygame.Rect(self.contextualPosX + self.handleX - self.handleSize, self.contextualPosY - (self.handleSize * 0.75), self.handleSize * 2, self.handleSize * 2)
            self.mouseHovering = (((self.contextualPosX + self.handleX) + (self.handleSize + 2) > mouseX > (self.contextualPosX + self.handleX) - (self.handleSize + 2)) and
                                  (self.contextualPosY + (self.handleSize + 2) > mouseY > self.contextualPosY - (self.handleSize + 2)))

            self.displayBarColour = self.barColour
            if self.mouseHovering or self.handleSelected:
                self.displayColour = self.selectedHandleColour
            else:
                self.displayColour = self.handleColour

            if not self.layer.pygame.mouse.get_pressed()[0]:
                self.handleSelected = False

            if self.handleSelected:
                if self.action is not None:
                    self.action(self.value)

                if self.contextualPosX < mouseX < (self.contextualPosX + self.length):
                    if self.increment is None:
                        self.handleX = mouseX - self.contextualPosX
                    else:
                        gap = (self.length / (self.valueRange[1] - self.valueRange[0])) * self.increment
                        handleX = int((mouseX - self.contextualPosX) / gap)
                        self.handleX = handleX * gap

                elif self.contextualPosX >= mouseX:
                    self.handleX = 0
                else:
                    self.handleX = self.length

                self.value = (self.handleX / (self.length / (self.valueRange[1] - self.valueRange[0]))) + (self.valueRange[0])

            if not self.handleSelected:
                self.handleSelected = self.mouseHovering and self.layer.pygame.mouse.get_pressed()[0] and not self.mouseDownLast

            if self.handleSelected and not self.handleSelectedLast:
                self.initialValue = self.value

            if not self.handleSelected and self.handleSelectedLast:
                if self.finishedUpdatingAction is not None:
                    self.finishedUpdatingAction(self.initialValue, self)

            self.mouseDownLast = self.layer.pygame.mouse.get_pressed()[0]
            self.handleSelectedLast = self.handleSelected
        else:
            self.displayBarColour = (120, 120, 120)
            self.displayColour = (46, 80, 94)

    def display(self):
        bar = self.layer.pygame.Rect(self.contextualPosX, self.contextualPosY, self.length, int(7 * self.size))
        self.layer.pygame.draw.rect(self.layer.screen, self.displayBarColour, bar, 0, 100)
        if not self.hideLabel:
            displayValue = str(int(self.value))
            if self.precision is not None:
                displayValue = str(round(self.value, self.precision))
            if self.suffix is not None:
                displayValue += self.suffix

            if self.value != self.previousValue:
                textSize = self.font.get_rect(displayValue).size
                self.valueLabelSurface = pygame.Surface(textSize, pygame.SRCALPHA)
                self.font.render_to(self.valueLabelSurface, (0, 0), displayValue, (200, 200, 200))
                self.previousValue = self.value

            self.layer.screen.blit(self.valueLabelSurface, (self.contextualPosX + self.length + 17, self.contextualPosY - 3))

        self.layer.pygame.gfxdraw.aacircle(self.layer.screen, int(self.contextualPosX + self.handleX), int(self.contextualPosY + (int(7 * self.size)) / 2), self.handleSize, self.displayColour)
        self.layer.pygame.gfxdraw.filled_circle(self.layer.screen, int(self.contextualPosX + self.handleX), int(self.contextualPosY + (int(7 * self.size)) / 2), self.handleSize, self.displayColour)

    def updateValue(self, value, update = True, runFinalAction = False):
        if self.valueRange[0] <= value <= self.valueRange[1]:
            self.value = value
            self.handleX = (self.length / (self.valueRange[1] - self.valueRange[0])) * (value - self.valueRange[0])

            if self.action is not None and update:
                self.action(self.value)
            if self.finishedUpdatingAction is not None and runFinalAction:
                self.finishedUpdatingAction(self.value)

class Switch (UIElement):
    def __init__(self, layer, pos, stick, size, value = True, action = None, show = True, disabled = False, layerIndex = -1):
        super().__init__(layer, pos, stick, show, layerIndex)

        self.size = size
        self.value = value
        self.action = action
        self.disabled = disabled

        self.barWidth = 0
        self.barHeight = 0

        self.trueColour = (41, 66, 43)
        self.falseColour = (66, 41, 41)
        self.colour = (0, 0, 0)

        self.handleColour = (20, 20, 20)
        self.handleDisplayColour = (20, 20, 20)

        self.mouseHovering = False
        self.pointSelected = False
        self.mouseDownLast = False

    def updateValue(self, value):
        self.value = value
        if self.action is not None:
            self.action(value)

    def update(self):
        self.updateContextualPos()

        self.barWidth = 55 * self.size
        self.barHeight = 25 * self.size
        mouseX, mouseY = self.layer.pygame.mouse.get_pos()

        self.mouseHovering = ((self.contextualPosX + self.barWidth > mouseX > self.contextualPosX) and (self.contextualPosY + self.barHeight > mouseY > self.contextualPosY)) and not self.disabled

        if self.mouseHovering:
            self.pointSelected = self.mouseHovering and self.layer.pygame.mouse.get_pressed()[0] and not self.mouseDownLast

        if self.pointSelected:
            self.value = not self.value
            self.pointSelected = False

            if self.action is not None:
                self.action(self.value)

        if self.value:
            self.colour = self.trueColour
            if self.mouseHovering:
                self.colour = (self.trueColour[0] - (self.trueColour[0] * 0.2), self.trueColour[1] - (self.trueColour[1] * 0.2), self.trueColour[1] - (self.trueColour[1] * 0.2))

            if self.disabled:
                self.handleDisplayColour = (32, 38, 32)
                self.colour = (42, 51, 43)
            else:
                self.handleDisplayColour = self.handleColour
                self.colour = self.trueColour
        else:
            self.colour = self.falseColour
            if self.mouseHovering:
                self.colour = (self.falseColour[0] - (self.falseColour[0] * 0.2), self.falseColour[1] - (self.falseColour[1] * 0.2), self.falseColour[1] - (self.falseColour[1] * 0.2))

            if self.disabled:
                self.handleDisplayColour = (43, 33, 33)
                self.colour = (54, 40, 40)
            else:
                self.handleDisplayColour = self.handleColour
                self.colour = self.falseColour

        self.mouseDownLast = self.layer.pygame.mouse.get_pressed()[0]

    def display(self):
        self.boundingBox = self.layer.pygame.Rect(self.contextualPosX, self.contextualPosY, self.barWidth, self.barHeight)
        self.layer.pygame.draw.rect(self.layer.screen, self.colour, self.boundingBox, 0, 100)

        if self.value:
            circleOffset = (self.barWidth / 2)
        else:
            circleOffset = 0

        self.layer.pygame.gfxdraw.aacircle(self.layer.screen, int(self.contextualPosX + (self.barWidth / 4) + circleOffset), int(self.contextualPosY + (self.barHeight / 2)), int(9 * self.size), self.handleDisplayColour)
        self.layer.pygame.gfxdraw.filled_circle(self.layer.screen, int(self.contextualPosX + (self.barWidth / 4) + circleOffset), int(self.contextualPosY + (self.barHeight / 2)), int(9 * self.size), self.handleDisplayColour)

class Image(UIElement):
    def __init__(self, layer, pos, stick, imageDir, size, colour = None, show = True, layerIndex = -1):
        super().__init__(layer, pos, stick, show, layerIndex)

        self.imageDir = imageDir
        self.size = size
        self.colour = colour

        self.angle = 0
        self.transformedImage = None
        self.transformedRect = None

        self.image = self.layer.pygame.image.load(self.imageDir).convert_alpha()
        self.boundingBox = self.image.get_rect()

    def update(self):
        self.updateContextualPos()
        self.transformedImage = self.image
        self.transformedImage = self.layer.pygame.transform.scale_by(self.transformedImage, self.size)
        self.transformedImage = self.layer.pygame.transform.rotate(self.transformedImage, (self.angle % 360))

        if self.colour is not None:
            self.transformedImage.fill(self.colour, special_flags = self.layer.pygame.BLEND_RGB_MAX)

        imageSize = self.getSize()
        self.transformedRect = self.transformedImage.get_rect(center = (self.contextualPosX + (imageSize[0] / 2), self.contextualPosY + (imageSize[1] / 2)))

    def display(self):
        if self.show:
            self.layer.screen.blit(self.transformedImage, self.transformedRect)

    def getSize(self):
        return self.boundingBox.size

    def updateImage(self, newDir):
        self.imageDir = newDir
        self.image = self.layer.pygame.image.load(self.imageDir).convert_alpha()
        self.boundingBox = self.image.get_rect()

class TextInput(UIElement):
    def __init__(self, layer, pos, stick, dimensions, fontSize, placeholder = "", text = "", suffix = "", characterWhitelist = (), characterBlackList = (), enterAction = None, show = True, bgColour = (100, 100, 100, 100), layerIndex = -1):
        super().__init__(layer, pos, stick, show, layerIndex)

        self.width, self.height = dimensions
        self.fontSize = fontSize
        self.placeholder = placeholder
        self.text = text
        self.suffix = suffix

        self.characterWhitelist = characterWhitelist
        self.characterBlackList = characterBlackList
        self.font = layer.pygame.freetype.Font(layer.fontName, self.fontSize)
        self.enterAction = enterAction

        self.showTypingBar = True
        self.timeAtFlash = time.time()

        self.bgColour = bgColour

        self.hovering = False
        self.selected = True

        self.cursorIndex = 0
        self.backSpaceInitialRemove = False
        self.backSpacePressed = None

        self.show = show

        self.maxLength = ((self.width - 10) // (self.font.get_rect('a').width + 2)) - len(self.suffix)

    def update(self):
        self.updateContextualPos()
        if pygame.key.get_pressed()[pygame.K_BACKSPACE] and self.backSpacePressed is None:
            self.backSpacePressed = time.time()
        elif not pygame.key.get_pressed()[pygame.K_BACKSPACE]:
            self.backSpacePressed = None
            self.backSpaceInitialRemove = False

        if self.backSpacePressed is not None:
            if not self.backSpaceInitialRemove or ((time.time() - self.backSpacePressed) > 0.5):
                self.backSpaceInitialRemove = True
                if self.cursorIndex > 0:
                    self.text = self.text[:self.cursorIndex - 1] + self.text[self.cursorIndex:]
                    self.cursorIndex = max(self.cursorIndex - 1, 0)

        if self.selected:
            if (time.time() - self.timeAtFlash) >= 0.5:
                self.showTypingBar = not self.showTypingBar
                self.timeAtFlash = time.time()

        for letter in self.layer.events:
            if letter.type == 768: #int version of 'pygame.KEYDOWN'
                if letter.key == self.layer.pygame.K_RIGHT:
                    self.cursorIndex += 1

                if letter.key == self.layer.pygame.K_LEFT:
                    self.cursorIndex -= 1

                if letter.key == self.layer.pygame.K_RETURN:
                    if self.enterAction is not None:
                        self.enterAction(self.text)

            if letter.type == 771: #int version of 'pygame.TEXTINPUT'
                letterUni = letter.text
                if ((letterUni.lower() in self.characterWhitelist) or len(self.characterWhitelist) == 0) and (letterUni.lower() not in self.characterBlackList) and len(self.text) < self.maxLength:
                    self.timeAtFlash = time.time()
                    self.showTypingBar = True
                    self.text = self.text[:self.cursorIndex] + letterUni + self.text[self.cursorIndex:]
                    self.cursorIndex += 1

    def display(self):
        transparentSurface = self.layer.pygame.Surface((self.width, self.height), self.layer.pygame.SRCALPHA)
        self.layer.pygame.draw.rect(transparentSurface, self.bgColour, (0, 0, self.width, self.height), border_radius = 15)
        self.layer.screen.blit(transparentSurface, (self.contextualPosX, self.contextualPosY))
        self.font.origin = True

        if self.text == "":
            self.font.render_to(self.layer.screen, (self.contextualPosX + 10, self.contextualPosY + (self.height / 2) + ((self.fontSize - 5) / 2)), self.placeholder, (150, 150, 150))
        else:
            self.font.render_to(self.layer.screen, (self.contextualPosX + 10, self.contextualPosY + (self.height / 2) + ((self.fontSize - 5) / 2)), self.text + self.suffix, (200, 200, 200))

        if self.showTypingBar:
            if self.cursorIndex > (len(self.text)):
                self.cursorIndex = len(self.text)

            elif self.cursorIndex <= 0:
                self.cursorIndex = 0

            textWidth = self.font.get_rect(self.text[:self.cursorIndex]).width
            self.layer.pygame.draw.line(self.layer.screen, (200, 200, 200), (self.contextualPosX + 10 + textWidth, self.contextualPosY + 7), (self.contextualPosX + 10 + textWidth, self.contextualPosY - 7 + self.height), 2)

class Accordion(UIElement):
    def __init__(self, layer, pos, stick, dimensions, title, elements, openDir = "l", collapse = False, show = True, layerIndex = 0):
        super().__init__(layer, pos, stick, show, layerIndex)

        self.width, self.height = dimensions
        self.displayWidth, self.displayHeight = dimensions
        self.collapsedSize = 50
        self.openDir = openDir

        self.titleText = title
        self.fontSize = 20
        self.titleLabel = Label(layer, self.fontSize, (0, 0), stick, self.titleText, (200, 200, 200))

        self.elements = elements + [self.titleLabel]
        self.collapse = collapse

        self.collapseButton = Button(layer, (0, 0), stick, (30, 30), "", 15, (100, 100, 100), roundedCorners = 30, action = self.toggleCollapse)
        self.collapseImage = Image(layer, (0, 0), stick, self.layer.directories["minus"], 1, colour = (200, 200, 200))
        self.expandImage = Image(layer, (0, 0), stick, self.layer.directories["plus"], 1, colour = (200, 200, 200))

    def update(self):
        self.updateContextualPos()

        if self.collapse:
            self.displayHeight = self.collapsedSize
            self.displayWidth = self.collapsedSize

            self.collapseImage.show = False
            self.expandImage.show = True

        else:
            self.displayHeight = self.height
            self.displayWidth = self.width

            self.collapseImage.show = True
            self.expandImage.show = False

        if self.openDir == "l":
            self.collapseImage.posX, self.collapseImage.posY = (self.posX + 38, (self.posY + self.displayHeight) - 12)
            self.expandImage.posX, self.expandImage.posY = (self.posX + 38, (self.posY + self.displayHeight) - 12)
            self.collapseButton.posX, self.collapseButton.posY = (self.posX + 40, (self.posY + self.displayHeight) - 10)
        else:
            self.collapseImage.posX, self.collapseImage.posY = (self.posX + self.displayWidth - 38, (self.posY + self.displayHeight) - 12)
            self.expandImage.posX, self.expandImage.posY = (self.posX + self.displayWidth - 38, (self.posY + self.displayHeight) - 12)
            self.collapseButton.posX, self.collapseButton.posY = (self.posX + self.displayWidth - 40, (self.posY + self.displayHeight) - 10)

        fontSize = {19: 19,
                    20: 17, 21: 17, 22: 17,
                    23: 15, 24: 15,
                    25: 14, 26: 14, 27: 14}

        titleLength = len(self.titleText)
        if 19 <= titleLength <= 27:
            newFontSize = fontSize[titleLength]
        else:
            if titleLength > 27:
                newFontSize = 14
            else:
                newFontSize = 20

        if self.fontSize != newFontSize:
            self.titleLabel.updateFontSize(newFontSize)
            self.fontSize = newFontSize

        self.titleLabel.text = self.titleText[:27]
        if self.titleText[:27] != self.titleText:
            self.titleLabel.text = self.titleText[:24] + "..."
            if self.titleText[-1] == "*":
                self.titleLabel.text += "*"

        if self.openDir == "l":
            self.titleLabel.posX, self.titleLabel.posY = ((self.displayWidth / 2) + (self.titleLabel.textSize[0] / 2) + self.posX, self.displayHeight - 25 + self.posY)
        else:
            self.titleLabel.posX, self.titleLabel.posY = ((self.displayWidth / 2) - (self.titleLabel.textSize[0] / 2) + self.posX, self.displayHeight - 25 + self.posY)


        self.boundingBox = self.layer.pygame.Rect((self.contextualPosX - self.displayWidth, self.contextualPosY - self.displayHeight), (self.displayWidth, self.displayHeight))

    def display(self):
        transparentSurface = self.layer.pygame.Surface(self.boundingBox.size, self.layer.pygame.SRCALPHA)
        self.layer.pygame.draw.rect(transparentSurface, (50, 50, 50, 200), (0, 0, self.displayWidth, self.displayHeight), border_radius = 15)
        if self.openDir == "l":
            self.layer.screen.blit(transparentSurface, (self.contextualPosX - self.displayWidth, self.contextualPosY - self.displayHeight))
        else:
            self.layer.screen.blit(transparentSurface, (self.contextualPosX, self.contextualPosY - self.displayHeight))

    def setCollapseStatus(self, value):
        self.collapse = value
        for element in self.elements:
            element.show = not self.collapse

    def toggleCollapse(self):
        self.setCollapseStatus(not self.collapse)

class Message(UIElement):
    def __init__(self, layer, title, message, button1Text = None, button1Action = None, button1Colour = None, button2Text = None, button2Action = None, button2Colour = None, closeAction = None, dimensions = (400, 150), linePadding = 25, lineSpacing = 20, messageFontSize = 15, align = "centre", show = True, layerIndex = -1):
        super().__init__(layer, (0, 0), "", show, layerIndex)

        self.message = message
        self.lastMessage = None

        self.title = title
        self.lastTitle = None

        self.button1Text = button1Text
        self.button1Action = button1Action
        self.button1Colour = button1Colour

        if self.button1Action == "close":
            self.button1Action = self.close

        self.button2Text = button2Text
        self.button2Action = button2Action
        self.button2Colour = button2Colour

        if self.button2Action == "close":
            self.button2Action = self.close

        self.xAction = closeAction

        self.greyColour = (120, 120, 120)
        self.redColour = (95, 25, 25)

        self.width, self.height = dimensions
        self.linePadding = linePadding
        self.lineSpacing = lineSpacing
        self.align = align

        self.posX = (self.layer.screenWidth / 2) - (self.width / 2)
        self.posY = (self.layer.screenHeight / 2) - (self.height / 2)

        self.boundingBox = self.layer.pygame.Rect(self.posX, self.posY, self.width, self.height)

        self.messageFont = layer.pygame.freetype.Font(layer.fontName, messageFontSize)
        self.titleFont = layer.pygame.freetype.Font(layer.fontName, 25)

        self.messagesBoundingBox = []
        self.messagesSize = []

        self.titleSize = self.titleFont.get_rect(self.title).size
        self.titleBoundingBox = self.layer.pygame.Rect((self.posX, self.posY), (self.titleSize[0], self.titleSize[1]))
        self.titleBoundingBox.center = self.boundingBox.center

        self.titleSurface = pygame.Surface(self.titleBoundingBox.size, self.layer.pygame.SRCALPHA)
        self.messageSurfaces = []

        self.closeButton = Button(layer, (self.posX + self.width - 40, self.posY + 10), "", (30, 30), "", 10,
                                  self.greyColour, action = self.closeButton)
        self.closeImage = Image(layer, (self.posX + self.width - 38, self.posY + 12), "", self.layer.directories["cross"], 1, colour = (200, 200, 200))

        if button1Text is not None:
            if button2Text is None:
                centreButtonColour = self.greyColour
                if self.button1Colour == "red":
                    centreButtonColour = self.redColour

                self.centreButton = Button(layer, (self.posX + 10, (self.posY + self.height) - 40), "",
                                           (self.width - 20, 30), button1Text, 15, centreButtonColour,
                                           action = lambda: self.buttonAction(self.button1Action))

            else:
                leftButtonColour = self.greyColour
                if self.button1Colour == "red":
                    leftButtonColour = self.redColour

                rightButtonColour = self.greyColour
                if self.button2Colour == "red":
                    rightButtonColour = self.redColour

                self.leftButton = Button(layer, (self.posX + 10, (self.posY + self.height) - 40), "",
                                         ((self.width / 2) - 20, 30), button1Text, 15, leftButtonColour,
                                         action = lambda: self.buttonAction(self.button1Action))
                self.rightButton = Button(layer, (self.posX + 10 + (self.width / 2), (self.posY + self.height) - 40), "",
                                          ((self.width / 2) - 20, 30), button2Text, 15, rightButtonColour,
                                          action = lambda: self.buttonAction(self.button2Action))

    def wrapText(self, text, padding):
        if isinstance(text, str):
            textLength = self.messageFont.get_rect(text).size[0]
            acceptedLength = (self.width - (2 * padding))
            if textLength <= acceptedLength:
                return [text]
            else:
                message = []
                currentLine = []
                lineLength = 0
                splitText = text.split()
                for word in splitText:
                    wordLength = self.messageFont.get_rect(word + " ").size[0]
                    if (lineLength + wordLength) <= acceptedLength:
                        currentLine.append(word)
                        lineLength += wordLength
                    else:
                        message.append(" ".join(currentLine))
                        lineLength = wordLength
                        currentLine = [word]
                message.append(" ".join(currentLine))

                return message
        else:
            return text

    def update(self):
        oldX = self.posX
        oldY = self.posY
        self.posX = (self.layer.screenWidth / 2) - (self.width / 2)
        self.posY = (self.layer.screenHeight / 2) - (self.height / 2)
        self.boundingBox = self.layer.pygame.Rect(self.posX, self.posY, self.width, self.height)
        posChanged = (oldX != self.posX) or (oldY != self.posY)

        for event in self.layer.events:
            if event.type == pygame.KEYDOWN:
                if (event.key == pygame.K_RETURN) and (self.button2Action is None) and (self.button1Action is not None):
                    self.buttonAction(self.button1Action)

        if (self.lastMessage != self.message) or posChanged:
            if isinstance(self.message, str):
                self.message = self.wrapText(self.message, self.linePadding)

            for lineIndex in range(len(self.message)):
                self.messagesSize.append(self.messageFont.get_rect(self.message[lineIndex]).size)
                self.messagesBoundingBox.append(self.layer.pygame.Rect((self.posX, self.posY), (self.messagesSize[lineIndex][0], self.messagesSize[lineIndex][1])))
                self.messagesBoundingBox[lineIndex].center = self.boundingBox.center

                if self.lastMessage != self.message:
                    self.messageSurfaces.append(pygame.Surface(self.messagesBoundingBox[lineIndex].size, self.layer.pygame.SRCALPHA))
                    self.messageFont.render_to(self.messageSurfaces[lineIndex], (0, 0), self.message[lineIndex], (200, 200, 200))

            self.lastMessage = self.message

        if (self.lastTitle != self.title) or posChanged:
            self.titleBoundingBox = self.layer.pygame.Rect((self.posX, self.posY), (self.titleSize[0], self.titleSize[1]))
            self.titleSurface = pygame.Surface(self.titleBoundingBox.size, self.layer.pygame.SRCALPHA)
            self.titleFont.render_to(self.titleSurface, (0, 0), self.title, (200, 200, 200))
            self.titleBoundingBox.center = self.boundingBox.center

        self.closeButton.posX, self.closeButton.posY = (self.posX + self.width - 40, self.posY + 10)
        self.closeImage.posX, self.closeImage.posY = (self.posX + self.width - 38, self.posY + 12)

        if self.button1Text is not None:
            if self.button2Text is None:
                self.centreButton.posX, self.centreButton.posY = (self.posX + 10, (self.posY + self.height) - 40)
            else:
                self.leftButton.posX, self.leftButton.posY = (self.posX + 10, (self.posY + self.height) - 40)
                self.rightButton.posX, self.rightButton.posY = (self.posX + 10 + (self.width / 2), (self.posY + self.height) - 40)

    def display(self):
        transparentSurface = self.layer.pygame.Surface((self.layer.screenWidth, self.layer.screenHeight), self.layer.pygame.SRCALPHA)
        self.layer.pygame.draw.rect(transparentSurface, (50, 50, 50, 200), (0, 0, self.layer.screenWidth, self.layer.screenHeight))
        self.layer.screen.blit(transparentSurface, (0, 0))

        self.layer.pygame.draw.rect(self.layer.screen, (70, 70, 70), (self.posX, self.posY, self.width, self.height), border_radius = 15)
        self.layer.screen.blit(self.titleSurface, (self.titleBoundingBox.centerx - (self.titleSize[0] / 2), self.posY + 20))

        for lineIndex in range(len(self.message)):
            if self.align == "left":
                position = (self.posX + 25, self.posY + 60 + (lineIndex * self.lineSpacing))
            else:
                position = (self.messagesBoundingBox[lineIndex].centerx - (self.messagesSize[lineIndex][0] / 2), self.posY + 60 + (lineIndex * self.lineSpacing))

            self.layer.screen.blit(self.messageSurfaces[lineIndex], position)

    def close(self):
        try:
            if self.button1Text is not None:
                if self.button2Text is None:
                    self.layer.elements.remove(self.centreButton)
                else:
                    self.layer.elements.remove(self.leftButton)
                    self.layer.elements.remove(self.rightButton)

            self.layer.elements.remove(self.closeButton)
            self.layer.elements.remove(self.closeImage)
            self.layer.elements.remove(self)

        except:
            pass

    def closeButton(self):
        if self.xAction is not None:
            self.xAction()
        self.close()

    def buttonAction(self, mainAction):
        self.close()
        mainAction()

class Dropdown(UIElement):
    def __init__(self, layer, pos, stick, dimensions, values, itemIndex, disabledIndexes = [], colour = (100, 100, 100), action = None, show = True, layerIndex = -1):
        super().__init__(layer, pos, stick, show, layerIndex)
        self.values = values
        self.index = itemIndex
        self.disabledIndexes = disabledIndexes

        self.action = action

        self.font = layer.pygame.freetype.Font(layer.fontName, 15)
        self.colour = colour
        self.currentColour = self.colour

        self.width, self.height = dimensions
        self.boundingBox = self.layer.pygame.Rect(pos, dimensions)

        self.dropdownIcon = Image(layer, (0, 0), "", self.layer.directories["down"], 1, (30, 30, 30), show)
        self.displayMenu = False

        self.currentlySelectedSurface = pygame.Surface(self.boundingBox.size, self.layer.pygame.SRCALPHA)
        self.lastSelectedValue = None

        self.mouseHovering = False
        self.hoveringItemIndex = None
        self.pointSelected = False
        self.stepBeforeClick = False
        self.noClickBefore = False

    def update(self):
        self.updateContextualPos()

        self.dropdownIcon.posX, self.dropdownIcon.posY = (self.contextualPosX + (self.width - 30), self.contextualPosY + (self.height / 2) - 13)

        mousePos = self.layer.pygame.mouse.get_pos()
        self.mouseHovering = (((self.contextualPosX + self.width / 2) + ((self.width / 2) + 2) > mousePos[0] >= (self.contextualPosX + self.width / 2) - ((self.width / 2) + 2)) and
                              ((self.contextualPosY + self.height / 2) + ((self.height / 2) + 0) > mousePos[1] >= (self.contextualPosY + self.height / 2) - ((self.height / 2) + 2)))

        if self.displayMenu: totalHeight = len(self.values) * 22 + self.height + 5
        else: totalHeight = self.height
        self.boundingBox = self.layer.pygame.Rect((self.contextualPosX, self.contextualPosY), (self.width, totalHeight))

        if self.mouseHovering:
            self.currentColour = (self.colour[0] - 25, self.colour[1] - 25, self.colour[2] - 25)
        else:
            self.currentColour = self.colour

        self.pointSelected = self.mouseHovering and self.layer.pygame.mouse.get_pressed()[0]
        if self.pointSelected and self.stepBeforeClick:
            self.displayMenu = not self.displayMenu
        elif self.displayMenu and self.layer.pygame.mouse.get_pressed()[0] and self.noClickBefore and not self.boundingBox.collidepoint(mousePos):
            self.displayMenu = False

        if self.displayMenu:
            self.dropdownIcon.angle = 180
            self.layer.overrideUpdateElements = [self]
        else:
            self.dropdownIcon.angle = 0
            self.layer.overrideUpdateElements = None


        if self.displayMenu:
            self.hoveringItemIndex = None
            currentIndex = 0
            for i in range(len(self.values) - 1):
                if i == self.index:
                    currentIndex += 1

                mouseOverItem = (((self.contextualPosX + self.width) > mousePos[0] >= self.contextualPosX) and
                                 (self.contextualPosY + ((i + 1) * 22) + self.height > mousePos[1] >= self.contextualPosY + (i * 22) + self.height))
                if mouseOverItem and (currentIndex not in self.disabledIndexes):
                    self.hoveringItemIndex = i
                    if self.layer.pygame.mouse.get_pressed()[0]:
                        self.index = currentIndex
                        self.displayMenu = False
                        if self.action is not None:
                            self.action(self.values[currentIndex])
                currentIndex += 1

        self.stepBeforeClick = self.mouseHovering and not(self.layer.pygame.mouse.get_pressed()[0])
        self.noClickBefore = not(self.layer.pygame.mouse.get_pressed()[0])

    def alwaysUpdate(self):
        self.dropdownIcon.show = self.show

    def display(self):
        if self.displayMenu:
            self.layer.pygame.draw.rect(self.layer.screen, (100, 100, 100), (self.contextualPosX, self.contextualPosY, self.width, (len(self.values) - 1) * 22 + self.height + 5), border_radius = 10)
            currentIndex = 0
            for i in range(len(self.values) - 1):
                if i == self.index:
                    currentIndex += 1

                if (i == self.hoveringItemIndex) and (currentIndex not in self.disabledIndexes):
                    self.layer.pygame.draw.rect(self.layer.screen, (75, 75, 75), (self.contextualPosX, self.contextualPosY + (i * 22) + self.height, self.width, 22), border_radius = 10)

                if currentIndex in self.disabledIndexes:
                    colour = (150, 150, 150)
                else:
                    colour = (200, 200, 200)
                self.font.render_to(self.layer.screen, (self.contextualPosX + 10, self.contextualPosY + self.height + (22 * i) + 5), str(self.values[currentIndex]), colour)
                currentIndex += 1

        if self.lastSelectedValue != str(self.values[self.index]):
            self.currentlySelectedSurface = pygame.Surface(self.boundingBox.size, self.layer.pygame.SRCALPHA)
            self.font.render_to(self.currentlySelectedSurface, (0, 0), str(self.values[self.index]), (200, 200, 200))
            self.lastSelectedValue = str(self.values[self.index])

        self.layer.pygame.draw.rect(self.layer.screen, self.currentColour, (self.contextualPosX, self.contextualPosY, self.width, self.height), border_radius = 10)
        self.layer.screen.blit(self.currentlySelectedSurface, (self.contextualPosX + 10, self.contextualPosY + (self.height / 2) - 6))

    def getCurrent(self):
        return self.values[self.index]

class FilePicker(UIElement):
    def __init__(self, layer, title, directory, extensions, openAction, validateFile, deleteTrackAction = None, renameTrackAction = None):
        super().__init__(layer, (0, 0), "", True, -1)
        self.directory = directory
        self.extensions = extensions
        self.title = title
        self.fileList = None
        self.limitedList = None
        self.lastLimitedList = None
        self.openAction = openAction
        self.validateFile = validateFile

        self.deleteTrackAction = deleteTrackAction
        self.renameTrackAction = renameTrackAction

        self.width = 350
        self.height = 400

        self.boxCornerX = 0
        self.boxCornerY = 0

        self.scrollHeight = 0
        self.viewProportion = 0
        self.scrollExaggeration = 0
        self.totalTextHeight = 0
        self.scrollColour = (0, 0, 0)

        self.scrollBarHovering = False
        self.stepBeforeScroll = True
        self.stepBeforeSelect = True
        self.scrollSelected = False
        self.selectedYOffset = 0

        self.itemHovering = False
        self.itemIndexHovering = 0
        self.itemIndexSelected = None
        self.selectedItem = None

        self.framesTillOpen = None

        self.messageFont = layer.pygame.freetype.Font(layer.fontName, 18)
        self.titleFont = layer.pygame.freetype.Font(layer.fontName, 25)
        self.titleFont.strong = True

        self.trackListSurface = self.layer.pygame.Surface((self.width, self.height - 155), self.layer.pygame.SRCALPHA)
        self.trackListTextSurface = self.layer.pygame.Surface((self.width, self.height - 155), self.layer.pygame.SRCALPHA)
        self.titleCenterX = 0
        self.titleRect = self.titleFont.get_rect(self.title)
        self.titleSurface = pygame.Surface(self.titleRect.size, pygame.SRCALPHA)
        self.titleFont.render_to(self.titleSurface, (0, 0), self.title, (200, 200, 200))

        self.openButton = Button(layer, (0, 0), "", (self.width - 145, 40), "Open", 18, (150, 150, 150), disabled = True, action = self.openTrack)
        self.closeButton = Button(layer, (0, 0), "", (30, 30), "", 10, (122, 43, 43), action = self.closeWindow)
        self.closeImage = Image(layer, (0, 0), "", self.layer.directories["cross"], 1, colour = (200, 200, 200))
        self.searchBar = TextInput(layer, (0, 0), "", (self.width - 90, 30), 18, "Search", bgColour = (70, 70, 70, 255), characterBlackList = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"])

        self.deleteTrackButton = Button(layer, (0, 0), "", (40, 40), "", 18, (122, 43, 43), disabled = True, action = self.deleteTrack)
        self.deleteTrackIcon = Image(layer, (0, 0), "", self.layer.directories["bin"], 1, colour = (200, 200, 200))
        self.renameTrackButton = Button(layer, (0, 0), "", (40, 40), "", 18, (150, 150, 150), disabled = True, action = self.renameTrack)
        self.renameTrackIcon = Image(layer, (0, 0), "", self.layer.directories["rename"], 1, colour = (200, 200, 200))

    def closeWindow(self):
        self.close()
        self.openButton.close()
        self.closeButton.close()
        self.closeImage.close()
        self.searchBar.close()
        self.deleteTrackButton.close()
        self.deleteTrackIcon.close()
        self.renameTrackButton.close()
        self.renameTrackIcon.close()

    def setView(self, view):
        self.show = view
        self.openButton.show = view
        self.closeButton.show = view
        self.closeImage.show = view
        self.searchBar.show = view
        self.deleteTrackButton.show = view
        self.deleteTrackIcon.show = view
        self.renameTrackButton.show = view
        self.renameTrackIcon.show = view

    def openTrack(self):
        self.setView(False)
        self.framesTillOpen = 2

    def deleteTrack(self):
        def removeFile():
            if self.deleteTrackAction is not None:
                self.deleteTrackAction(fileDirectory)
                self.setView(True)
                self.fileList = None
        def cancel():
            self.setView(True)

        fileDirectory = os.path.join(self.directory, self.selectedItem)
        self.setView(False)
        Message(self.layer, "Delete Track", f'Are you sure you want to delete "{getTrackName(self.selectedItem)}"', "Cancel", cancel, "grey", "Delete", removeFile, "red")


    def renameTrack(self):
        def rename(newFileDir):
            if self.renameTrackAction is not None:
                self.renameTrackAction(fileDirectory, newFileDir)
                self.setView(True)
                self.fileList = None

        fileDirectory = os.path.join(self.directory, self.selectedItem)
        self.setView(False)
        FileSaver(self.layer, self.directory, rename, actionText = "Rename")

    def update(self):
        self.trackListSurface = self.layer.pygame.Surface((self.width, self.height - 155), self.layer.pygame.SRCALPHA)

        if self.fileList is None:
            self.fileList = []

            for item in os.listdir(self.directory):
                fullDir = os.path.join(self.directory, item)
                isFile = os.path.isfile(fullDir)
                isCorrectExtension = os.path.splitext(fullDir)[1] in self.extensions
                isValid = self.validateFile(fullDir)
                if isFile and isCorrectExtension and isValid:
                    self.fileList.append(item)

            self.limitedList = self.fileList
        self.limitedList = []
        for item in self.fileList:
            if (item[:len(self.searchBar.text)].lower() == self.searchBar.text.lower()) or self.searchBar.text == '':
                self.limitedList.append(item)

        self.totalTextHeight = (18 * len(self.limitedList)) + (12 * (len(self.limitedList) - 1))
        self.viewProportion = 228 / self.totalTextHeight
        self.scrollExaggeration = (self.totalTextHeight - 228)/ (235 - (235 * self.viewProportion))

        self.boxCornerX = (self.layer.screenWidth / 2) - (self.width / 2)
        self.boxCornerY = (self.layer.screenHeight / 2) - (self.height / 2)

        self.openButton.posX = self.boxCornerX + 20
        self.openButton.posY = (self.boxCornerY + self.height) - 60

        self.deleteTrackButton.posX = self.boxCornerX + 275
        self.deleteTrackButton.posY = (self.boxCornerY + self.height) - 60
        self.deleteTrackIcon.posX = self.deleteTrackButton.posX + 7
        self.deleteTrackIcon.posY = self.deleteTrackButton.posY + 6

        self.renameTrackButton.posX = self.boxCornerX + 230
        self.renameTrackButton.posY = (self.boxCornerY + self.height) - 60
        self.renameTrackIcon.posX = self.renameTrackButton.posX + 7
        self.renameTrackIcon.posY = self.renameTrackButton.posY + 6

        self.closeButton.posX = self.boxCornerX + self.width - 45
        self.closeButton.posY = self.boxCornerY + 15
        self.closeImage.posX = self.closeButton.posX + 2
        self.closeImage.posY = self.closeButton.posY + 3

        self.searchBar.posX = self.boxCornerX + 20
        self.searchBar.posY = self.boxCornerY + 60

        mousePos = self.layer.pygame.mouse.get_pos()
        scrollHeight = 235 * self.viewProportion
        self.scrollBarHovering = (((self.boxCornerX + self.width) - 50 <= mousePos[0] <= ((self.boxCornerX + self.width) - 50) + 15) and
                                  (self.boxCornerY + 90 + self.scrollHeight <= mousePos[1] <= (self.boxCornerY + 90 + self.scrollHeight + scrollHeight)))

        self.scrollSelected = self.layer.pygame.mouse.get_pressed()[0] and (self.scrollSelected or self.stepBeforeScroll)
        if self.scrollSelected and self.stepBeforeScroll:
            self.selectedYOffset = mousePos[1] - (self.boxCornerY + 60 + self.scrollHeight)

        self.stepBeforeScroll = self.scrollBarHovering and not (self.layer.pygame.mouse.get_pressed()[0]) and (not self.scrollSelected)

        if not self.scrollBarHovering and not self.scrollSelected:
            self.scrollColour = (70, 70, 70)
        elif self.scrollBarHovering and not self.scrollSelected:
            self.scrollColour = (60, 60, 60)
        else:
            self.scrollColour = (50, 50, 50)

        if self.scrollSelected:
            self.scrollHeight = mousePos[1] - (self.boxCornerY + 60) - self.selectedYOffset

        for event in self.layer.events:
            if event.type == self.layer.pygame.MOUSEWHEEL:
                self.scrollHeight += (event.y * -1) * (10 / self.scrollExaggeration)

            if event.type == pygame.KEYDOWN:
                if (event.key == pygame.K_RETURN) and (self.selectedItem is not None):
                    self.openTrack()
                if (event.key == pygame.K_RETURN) and (len(self.limitedList) == 1):
                    self.selectedItem = self.limitedList[0]
                    self.itemIndexSelected = 0
                    self.openTrack()

        self.scrollHeight = max(0, min(self.scrollHeight, 235 - 235 * self.viewProportion))

        self.itemHovering = ((self.boxCornerX + 10 <= mousePos[0] <= self.boxCornerX + self.width - 70) and
                             (self.boxCornerY + 95 <= mousePos[1] <= self.boxCornerY + 69 + self.height - 140))

        if self.itemHovering:
            unOffsetMouseY = (mousePos[1] + (self.scrollHeight * self.scrollExaggeration)) - self.boxCornerY - 95
            self.itemIndexHovering = int((unOffsetMouseY // 30))
            if self.layer.pygame.mouse.get_pressed()[0] and self.itemIndexHovering < len(self.limitedList) and self.stepBeforeSelect and self.itemIndexHovering >= 0:
                self.itemIndexSelected = self.itemIndexHovering
                if self.selectedItem == self.limitedList[self.itemIndexSelected]:
                    self.openTrack()

                self.selectedItem = self.limitedList[self.itemIndexSelected]

        self.stepBeforeSelect = self.itemHovering and not (self.layer.pygame.mouse.get_pressed()[0])

        if self.selectedItem is not None:
            self.openButton.disabled = False
            self.deleteTrackButton.disabled = False
            self.renameTrackButton.disabled = False
        else:
            self.openButton.disabled = True
            self.deleteTrackButton.disabled = True
            self.renameTrackButton.disabled = True

    def alwaysUpdate(self):
        if self.framesTillOpen is not None:
            waitSurface = self.layer.pygame.Surface((self.layer.screenWidth, self.layer.screenHeight), self.layer.pygame.SRCALPHA)
            self.layer.pygame.draw.rect(waitSurface, (50, 50, 50, 200), (0, 0, self.layer.screenWidth, self.layer.screenHeight))

            trackName = getTrackName(self.selectedItem)
            waitMessage = f"Opening {trackName}..."
            messageSize = self.messageFont.get_rect(waitMessage).size
            self.messageFont.render_to(waitSurface, ((self.layer.screenWidth / 2) - (messageSize[0] / 2), (self.layer.screenHeight / 2) - (messageSize[1] / 2)), waitMessage, (200, 200, 200, 255))

            self.layer.screen.blit(waitSurface, (0, 0))

            self.framesTillOpen -= 1
            if self.framesTillOpen <= 0:
                fileDirectory = os.path.join(self.directory, self.selectedItem)
                self.openAction(fileDirectory)
                self.closeWindow()

    def display(self):
        transparentSurface = self.layer.pygame.Surface((self.layer.screenWidth, self.layer.screenHeight), self.layer.pygame.SRCALPHA)
        self.layer.pygame.draw.rect(transparentSurface, (50, 50, 50, 200), (0, 0, self.layer.screenWidth, self.layer.screenHeight))
        self.layer.screen.blit(transparentSurface, (0, 0))

        self.boundingBox = self.layer.pygame.Rect((self.boxCornerX, self.boxCornerY), (self.width, self.height))
        self.layer.pygame.draw.rect(self.layer.screen, (100, 100, 100), self.boundingBox, border_radius = 15)

        self.titleCenterX = self.boxCornerX + (self.width / 2) - (self.titleRect.size[0] / 2)
        self.layer.screen.blit(self.titleSurface, (self.titleCenterX, self.boxCornerY + 25))

        if self.itemHovering and 0 <= self.itemIndexHovering < len(self.limitedList):
            self.layer.pygame.draw.rect(self.trackListSurface, (80, 80, 80), (20, (30 * self.itemIndexHovering) - (self.scrollHeight * self.scrollExaggeration) + 3, self.width - 90, 30), border_radius = 20)

        if self.selectedItem is not None and self.selectedItem in self.limitedList:
            self.layer.pygame.draw.rect(self.trackListSurface, (60, 60, 60), (20, (30 * self.itemIndexSelected) - (self.scrollHeight * self.scrollExaggeration) + 3, self.width - 90, 30), border_radius = 20)

        if self.lastLimitedList != self.limitedList:
            self.trackListTextSurface = self.layer.pygame.Surface((self.width, max((30 * (len(self.limitedList))) + 10, 10)), self.layer.pygame.SRCALPHA)
            for itemIndex in range(len(self.limitedList)):
                trackName = os.path.splitext(self.limitedList[itemIndex])[0]
                if trackName[:22] != trackName:
                    trackName = trackName[:19] + "..."
                self.messageFont.render_to(self.trackListTextSurface, (30, (30 * itemIndex) + 10), trackName, (200, 200, 200, 255))
            self.lastLimitedList = self.limitedList

        self.trackListSurface.blit(self.trackListTextSurface, (0, -(self.scrollHeight * self.scrollExaggeration)))
        self.layer.screen.blit(self.trackListSurface, (self.boxCornerX, self.boxCornerY + 90))

        if abs(self.viewProportion) < 1:
            self.layer.pygame.draw.rect(self.layer.screen, self.scrollColour, ((self.boxCornerX + self.width) - 50, self.boxCornerY + 90 + self.scrollHeight, 15, 235 * self.viewProportion), border_radius = 5)

class FileSaver(UIElement):
    def __init__(self, layer, directory, saveAction, actionText = None):
        super().__init__(layer, (0, 0), "", True, -1)

        self.directory = directory
        self.saveAction = saveAction
        self.titleFont = layer.pygame.freetype.Font(layer.fontName, 25)
        self.titleFont.strong = True

        self.actionText = actionText
        if actionText is None:
            self.actionText = "Save"

        self.fileDirectory = None
        self.fileList = [name.lower() for name in os.listdir(self.directory)]

        self.width = 350
        self.height = 180

        self.boxCornerX = 0
        self.boxCornerY = 0

        self.saveButton = Button(layer, (0, 0), "", (self.width - 40, 40), self.actionText, 18, (150, 150, 150), disabled = True, action = self.saveTrack)
        self.fileNameInput = TextInput(layer, (0, 0), "", (self.width - 40, 50), 18, "Track name", bgColour = (70, 70, 70, 255), characterBlackList = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"])
        self.closeButton = Button(layer, (0, 0), "", (30, 30), "", 10, (122, 43, 43), action = self.closeWindow)
        self.closeImage = Image(layer, (0, 0), "", self.layer.directories["cross"], 1, colour = (200, 200, 200))

    def closeWindow(self):
        self.saveButton.close()
        self.fileNameInput.close()
        self.closeButton.close()
        self.closeImage.close()
        self.close()

    def saveTrack(self):
        self.closeWindow()
        self.fileDirectory = os.path.join(self.directory, (self.fileNameInput.text + ".track"))
        self.saveAction(self.fileDirectory)

    def update(self):
        self.boxCornerX = (self.layer.screenWidth / 2) - (self.width / 2)
        self.boxCornerY = (self.layer.screenHeight / 2) - (self.height / 2)

        self.saveButton.posX = self.boxCornerX + 20
        self.saveButton.posY = self.boxCornerY + self.height - 60

        self.fileNameInput.posX = self.boxCornerX + 20
        self.fileNameInput.posY = self.boxCornerY + 60

        self.closeButton.posX = self.boxCornerX + self.width - 40
        self.closeButton.posY = self.boxCornerY + 15
        self.closeImage.posX = self.closeButton.posX + 2
        self.closeImage.posY = self.closeButton.posY + 3

        if (self.fileNameInput.text != '') and not((self.fileNameInput.text.lower() + ".track") in self.fileList):
            self.saveButton.disabled = False
        else:
            self.saveButton.disabled = True

        for event in self.layer.events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and not self.saveButton.disabled:
                    self.saveTrack()

    def display(self):
        transparentSurface = self.layer.pygame.Surface((self.layer.screenWidth, self.layer.screenHeight), self.layer.pygame.SRCALPHA)
        self.layer.pygame.draw.rect(transparentSurface, (50, 50, 50, 200), (0, 0, self.layer.screenWidth, self.layer.screenHeight))
        self.layer.screen.blit(transparentSurface, (0, 0))

        self.boundingBox = self.layer.pygame.Rect((self.boxCornerX, self.boxCornerY), (self.width, self.height))
        self.layer.pygame.draw.rect(self.layer.screen, (100, 100, 100), self.boundingBox, border_radius = 15)

        titleCenterX = self.boxCornerX + (self.width / 2) - (self.titleFont.get_rect(self.actionText).size[0] / 2)
        self.titleFont.render_to(self.layer.screen, (titleCenterX, self.boxCornerY + 25), self.actionText, (200, 200, 200))

class KeyboardKeyIcon(UIElement):
    def __init__(self, layer, pos, stick, character, show = True):
        super().__init__(layer, pos, stick, show, -1)

        self.character = character
        self.font = layer.pygame.freetype.Font(layer.fontName, 20)
        self.surface = self.createKey()

    def createKey(self):
        surface = self.layer.pygame.Surface((30, 30), self.layer.pygame.SRCALPHA)
        self.layer.pygame.draw.rect(surface, (120, 120, 120), (0, 0, 30, 30), border_radius = 8)

        textSize = self.font.get_rect(self.character)
        self.font.render_to(surface, (15 - (textSize.width / 2), 15 - (textSize.height / 2)), self.character, (200, 200, 200))

        return surface

    def display(self):
        self.updateContextualPos()
        self.layer.screen.blit(self.surface, (self.contextualPosX, self.contextualPosY))

class Layer:
    def __init__(self, screen, pygame, fontName, directories):
        self.elements = []
        self.overrideUpdateElements = None

        self.directories = directories

        self.screen = screen
        self.pygame = pygame
        self.fontName = fontName

        self.offset = (0, 0)
        self.zoom = 1

        self.screenWidth = 0
        self.screenHeight = 0

        self.events = []

    def add(self, element):
        insertIndex = element.layerIndex
        if insertIndex < 0:
            insertIndex = len(self.elements)

        self.elements.insert(insertIndex, element)

    def display(self, screenWidth, screenHeight, events, offset = (0, 0), zoom = 1):
        self.screenWidth = screenWidth
        self.screenHeight = screenHeight
        self.offset = offset
        self.zoom = zoom
        self.events = events

        for element in self.elements:
            element.alwaysUpdate()
            if element.show:
                if (self.overrideUpdateElements is not None and element in self.overrideUpdateElements) or (self.overrideUpdateElements is None):
                    element.update()
                element.display()

    def mouseOnLayer(self, mousePos):
        boundingBoxes = [element.returnBoundingBox() for element in self.elements if element.show]
        hovering = False
        mouseX, mouseY = mousePos

        for box in boundingBoxes:
            hovering = hovering or ((box[0][0] < mouseX < box[1][0]) and (box[0][1] < mouseY < box[2][1]))

        return hovering

    def clear(self):
        self.elements = []
