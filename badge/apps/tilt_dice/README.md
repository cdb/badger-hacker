# Tilt Dice

Tilt Dice is a photo-covered 3D die that tumbles, bounces, and settles toward the lowest edge of your badge.

## Controls

Tilt the badge to change gravity. The die rolls toward the bottom, left, right,
or top of the display as that edge becomes physically lower. Laying the badge
screen-up removes in-screen gravity so motion gradually slows.

- SELECT: toss the die with a fresh spin.
- BACK: return the die to the center.
- MENU: show or hide the control hint.
- Direction buttons: override tilt along that axis.
- HOME: return to the launcher.

This is playful, lightweight physics: screen-plane motion with bouncing walls,
friction, and three-dimensional rotation. It is not a fair random-number
generator or a full rigid-body simulator. Images stay attached to their faces.
The cube uses orthographic projection and face shading.

## Local preview and photos

From the project root:

```sh
python3 tools/preview_tilt_dice.py
```

Open `http://127.0.0.1:8765`. Drag the gravity pad or hold the arrow keys to
simulate tilt. Space tosses the die and R resets it. Choose **Lay flat** for
zero screen-plane gravity.

**Choose photos** accepts one to six PNG, JPEG, or WebP images. They are
center-cropped into 48x48 PNG files and replace `assets/1.png` through
`assets/6.png`. Fewer than six images repeat around the cube. This updates
the app's real local assets, not just the preview. Keep originals elsewhere.
No external service receives the pictures.

You can also replace those six PNGs directly with 48x48 images. Paletted
PNGs are recommended for lower memory use. All images load once on launch;
reopen the badge app after changing them.

The preview uses this app's `physics.py` on the local Python server, but Canvas
drawing is not the badge firmware. It never accesses USB or the mounted badge.
Python 3.10+ is the only computer dependency. The app needs no Wi-Fi,
credentials, or expansion hardware.

## Local checks

```sh
python3 -m unittest discover -s tests -v
python3 /path/to/hyb26-skill/scripts/validate_app.py badge/apps/tilt_dice
```

Physical verification is deliberately outstanding. When deployment is wanted,
check tilt-axis directions, slow settling, wall collisions, a sideways badge,
the launcher's inverted orientation, photo readability and frame rate, all
controls, HOME and reopen, and the custom icon on the real menu. Accelerometer
axis mapping and rendering speed have not been confirmed on this badge.
