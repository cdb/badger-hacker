"""A keyboard-friendly dance floor for the Universe 2026 badge."""

import json
import math
import os
import sys

APP_DIR = "/system/apps/stick_dance"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

with open("assets/dance.json") as source:
    dance = json.load(source)

badge.mode(HIRES | VSYNC)
screen.font = font.nope
MOVES = ("left", "right", "up", "down")
BUTTONS = (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN)
LINKS = ((1, 2), (1, 3), (3, 4), (1, 5), (5, 6),
         (2, 7), (7, 8), (2, 9), (9, 10))
OPPOSITE = {"top_left": "bottom_right", "top_right": "bottom_left",
            "bottom_right": "top_left", "bottom_left": "top_right"}
pose = [list(point) for point in dance["moves"]["idle"]["frames"][0]]
beat = 0.0
automatic = False
palette = 0
move = "idle"


def reset():
    global beat, automatic, palette, move
    beat = 0.0
    automatic = False
    palette = 0
    move = "idle"
    for index, point in enumerate(dance["moves"]["idle"]["frames"][0]):
        pose[index][:] = point


def point(x, y):
    return vec2(x * screen.width / 320, y * screen.height / 240)


def line(x1, y1, x2, y2, thickness=1):
    for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
        if thickness == 1 and (dx or dy):
            continue
        screen.line(point(x1 + dx, y1 + dy), point(x2 + dx, y2 + dy))


def circle(x, y, radius):
    screen.circle(point(x, y), radius * screen.width / 320)


def text(label, x, y):
    screen.text(label, x * screen.width / 320, y * screen.height / 240)


def light_brightness():
    phase = beat % 1
    return dance["lights"]["peak"] * max(0, 1 - phase / dance["lights"]["pulse_beats"])


def light_levels(direction, inverted):
    brightness = light_brightness()
    corners = dance["lights"]["corners"]
    active = dance["lights"]["directions"][direction] if direction else corners
    return tuple(brightness if (OPPOSITE[corner] if inverted else corner)
                 in active else 0 for corner in corners)


def on_exit():
    badge.caselights(0)


def draw():
    accent = dance["palettes"][palette]
    screen.pen = color.rgb(12, 14, 24)
    screen.rectangle(screen.clip)
    screen.pen = color.rgb(31, 37, 55)
    for x in range(-160, 481, 40):
        line(160 + (x - 160) * 0.3, 174, x, 216)
    for y in (174, 184, 198, 216):
        line(0, y, 320, y)

    screen.pen = color.rgb(*accent)
    text("STICK DANCE", 12, 10)
    text("AUTO" if automatic else "YOU LEAD", 240, 10)
    screen.pen = color.rgb(167, 177, 200)
    label = dance["moves"][move]["label"]
    width, _ = screen.measure_text(label)
    screen.text(label, (screen.width - width) / 2, screen.height * 36 / 240)

    screen.pen = color.rgb(27, 38, 48)
    for x in range(-20, 21, 2):
        circle(160 + pose[2][0] + x, 179, 3)

    screen.pen = color.rgb(*accent)
    for start, end in LINKS:
        x1, y1 = pose[start]
        x2, y2 = pose[end]
        line(160 + x1, 132 + y1, 160 + x2, 132 + y2, 3)
    for x, y in pose[1:]:
        circle(160 + x, 132 + y, 2)
    hx, hy = pose[0]
    circle(160 + hx, 132 + hy, 11)
    screen.pen = color.rgb(12, 14, 24)
    circle(160 + hx - 3, 130 + hy, 1)
    circle(160 + hx + 3, 130 + hy, 1)
    line(157 + hx, 136 + hy, 163 + hx, 136 + hy)

    screen.pen = color.rgb(*accent)
    for index in range(8):
        x = 132 + index * 8
        screen.rectangle(x * screen.width / 320, screen.height * 200 / 240,
                         4 * screen.width / 320,
                         (8 if index == int(beat * 2) % 8 else 3) * screen.height / 240)
    screen.pen = color.rgb(167, 177, 200)
    text("D-PAD dance  SELECT auto", 12, 219)


def update():
    global beat, automatic, palette, move
    dt = min(max(badge.ticks_delta, 0), 50)
    if badge.pressed(BUTTON_BACK):
        reset()
    if badge.pressed(BUTTON_SELECT):
        automatic = not automatic
    if badge.pressed(BUTTON_MENU):
        palette = (palette + 1) % len(dance["palettes"])
    beat = (beat + dt * dance["bpm"] / 60000) % 16
    move = MOVES[int(beat / 4)] if automatic else "idle"
    direction = None
    for name, button in zip(MOVES, BUTTONS):
        if badge.held(button):
            move = name
            direction = name
            break
    badge.caselights(*light_levels(direction, badge.upside_down()))
    first, second = dance["moves"][move]["frames"]
    mix = (1 - math.cos(beat * 2 * math.pi)) / 2
    smoothing = 1 - math.exp(-dt / 65)
    for index in range(len(pose)):
        for axis in (0, 1):
            target = first[index][axis] * (1 - mix) + second[index][axis] * mix
            pose[index][axis] += (target - pose[index][axis]) * smoothing
    draw()


run(update)
on_exit()
