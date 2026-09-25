"""UI theme: Inkwell & Ember (dark), lifted from pygame-ui's demo theme packs
(demo/themes/inkwell.py + demo/themes/base.py). This project only ever uses
one theme, so the palette/shape is baked directly into the Theme rules below
instead of going through pygame-ui's build_theme() pack machinery."""

import pygame
from pygame_ui import (
    Accordion, Button, Dropdown, Element, FilePicker, FileSaver, HoverHint,
    ImageButton, KeyIcon, Label, LabelModal, Message, Scrim, ScrollBar,
    Slider, Switch, TextButton, TextInput, Theme,
)

# Palette (Inkwell, dark)
BG = (24, 22, 28)
SURFACE = (38, 36, 44)
RAISED = (56, 53, 63)
TRACK = (74, 70, 82)
TEXT = (235, 230, 224)
MUTED = (140, 134, 148)
ACCENT = (226, 110, 72)
DANGER = (140, 45, 45)
ON = (74, 96, 78)
OFF = (96, 66, 66)

# Shape
RADIUS = 8
PANEL_RADIUS = RADIUS + 5
KEY_RADIUS = max(RADIUS - 2, 0)
SCROLLBAR_RADIUS = 5
HINT_RADIUS = max(RADIUS - 4, 0)
BORDER_WEIGHT = 0
KEY_BORDER_WEIGHT = 2
SWITCH_SCALE = 1
SWITCH_RADIUS = 100
KEY_SIZE = 1
CURSOR = pygame.SYSTEM_CURSOR_HAND
TITLE_SIZE = 26
SCRIM_TINT = (38, 32, 26)
SCRIM_OPACITY = 0.78
FONT_NAME = None
FONT_SIZE = 13

theme = Theme({
    Element:     {"font_name": FONT_NAME},
    Label:       {"color": TEXT},
    Accordion:   {"color": SURFACE + (230,), "border_radius": PANEL_RADIUS,
                  "button_color": RAISED, "icon_color": TEXT, "padding": 20},
    Button:      {"color": RAISED, "border_radius": RADIUS,
                  "border_weight": BORDER_WEIGHT, "border_color": TRACK,
                  "cursor": CURSOR, "padding": 0},
    TextButton:  {"font_color": TEXT, "font_size": FONT_SIZE, "padding": (20, 12)},
    ImageButton: {"image_color": TEXT, "image_scale": 0.7},
    Slider:      {"bar_color": TRACK, "handle_color": ACCENT,
                  "font_size": 15, "font_color": MUTED},
    Switch:      {"on_color": ON, "off_color": OFF,
                  "handle_color": BG, "scale": SWITCH_SCALE,
                  "border_radius": SWITCH_RADIUS},
    TextInput:   {"color": SURFACE, "font_color": TEXT,
                  "placeholder_font_color": MUTED, "border_radius": RADIUS,
                  "button_color": RAISED, "button_border_radius": RADIUS,
                  "button_icon_color": MUTED},
    Dropdown:    {"color": RAISED, "font_color": TEXT,
                  "icon_color": ACCENT, "border_radius": RADIUS,
                  "cursor": CURSOR},
    KeyIcon:     {"color": RAISED, "border_color": ACCENT,
                  "font_color": TEXT, "border_radius": KEY_RADIUS,
                  "border_weight": KEY_BORDER_WEIGHT, "size": KEY_SIZE},
    ScrollBar:   {"track_color": TRACK, "handle_color": RAISED,
                  "border_radius": SCROLLBAR_RADIUS},
    Message:     {"bg_color": SURFACE, "font_color": TEXT,
                  "border_radius": PANEL_RADIUS,
                  "button1_color": RAISED, "button1_font_color": TEXT,
                  "button2_color": DANGER, "button2_font_color": TEXT},
    HoverHint:   {"bg_color": RAISED, "border_color": ACCENT,
                  "font_color": TEXT, "border_radius": HINT_RADIUS,
                  "padding": (12, 8), "margins": (0, 6)},
    FileSaver:   {"bg_color": SURFACE, "font_color": TEXT,
                  "border_radius": PANEL_RADIUS,
                  "button_color": RAISED, "text_input_bg": BG,
                  "text_input_font_color": TEXT},
    LabelModal:  {"color": TEXT},
    Scrim:       {"tint": SCRIM_TINT, "opacity": SCRIM_OPACITY},
    FilePicker:  {"bg_color": SURFACE, "font_color": TEXT,
                  "border_radius": PANEL_RADIUS,
                  "icon_color": TEXT, "action_button_color": RAISED,
                  "delete_button_color": DANGER, "search_bg": BG,
                  "search_font_color": TEXT, "file_selected_bg_color": RAISED,
                  "file_hover_bg_color": BG},
    "icon_subtitle": {"font_size": 10},
    "icon": {"color": (200, 200, 200), "scale": 0.8},
})
