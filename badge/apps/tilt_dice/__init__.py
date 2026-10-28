"""A photo-covered die in a tiny gravity-driven tray."""

import os
import sys

APP_DIR = "/system/apps/tilt_dice"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

from physics import DiceTray, gravity_from_imu, texture_spans

badge.mode(HIRES | VSYNC)
screen.font = font.nope
tray = DiceTray(screen.width, screen.height)
textures = []
asset_error = None
for face in range(1, 7):
    path = "assets/%d.png" % face
    try:
        texture = image.load(path)
        if texture.width != 48 or texture.height != 48:
            raise ValueError("Expected a 48x48 face")
        textures.append(texture)
    except (OSError, ValueError, RuntimeError) as error:
        asset_error = "Check assets/%d.png" % face
        print("Tilt Dice: %s: %s" % (path, error))
        break

orientation = badge.upside_down()
BG = color.rgb(13, 18, 30)
TRAY = color.rgb(27, 38, 55)
EDGE = color.rgb(62, 82, 105)
INK = color.rgb(233, 239, 248)
ACCENT = color.rgb(195, 247, 110)


def draw_die():
    for _depth, face, corners, light in tray.faces():
        texture = textures[face]
        for x, y, length, u0, v0, u1, v1 in texture_spans(corners):
            screen.blit_hspan(texture, x, y, length, u0, v0, u1, v1)
        a, b, c, d = corners
        screen.pen = color.rgb(0, 0, 0, int((1 - light) * 150))
        screen.triangle(a[0], a[1], b[0], b[1], c[0], c[1])
        screen.triangle(a[0], a[1], c[0], c[1], d[0], d[1])
        screen.pen = EDGE
        for i in range(4):
            p, q = corners[i], corners[(i + 1) % 4]
            screen.line(int(p[0]), int(p[1]), int(q[0]), int(q[1]))


def update():
    global orientation
    screen.pen = BG
    screen.rectangle(screen.clip)
    screen.pen = ACCENT
    screen.text("TILT DICE", 10, 8)
    screen.text("%d / 6" % len(tray.dice), screen.width - 55, 8)
    screen.pen = EDGE
    screen.rectangle(7, 29, screen.width - 14, screen.height - 40)
    screen.pen = TRAY
    screen.rectangle(8, 30, screen.width - 16, screen.height - 42)

    if asset_error is not None:
        screen.pen = INK
        screen.text(asset_error, 18, 80)
        screen.text("Use 48x48 PNG images.", 18, 100)
        return

    flipped = badge.upside_down()
    if flipped != orientation:
        tray.flip()
        orientation = flipped
    ax, ay, _az, _gx, _gy, _gz = badge.imu()
    gx, gy = gravity_from_imu(ax, ay, orientation)
    if badge.held(BUTTON_LEFT):
        gx = -1
    elif badge.held(BUTTON_RIGHT):
        gx = 1
    if badge.held(BUTTON_UP):
        gy = -1
    elif badge.held(BUTTON_DOWN):
        gy = 1
    if badge.pressed(BUTTON_SELECT):
        tray.roll()
    if badge.pressed(BUTTON_BACK):
        tray.remove()
    if badge.pressed(BUTTON_MENU):
        tray.add()
    tray.step(badge.ticks_delta / 1000, gx, gy)
    draw_die()
    screen.pen = INK
    screen.text("MENU +  BACK -  SELECT toss", 10, screen.height - 10)


run(update)
