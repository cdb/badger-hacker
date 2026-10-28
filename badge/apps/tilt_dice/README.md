# Tilt Dice

Tilt Dice lets you toss up to six photo-covered 3D dice that tumble toward the lowest edge of your badge.

## Controls

Tilt the badge to change gravity. The die rolls toward the bottom, left, right,
or top of the display as that edge becomes physically lower. Laying the badge
screen-up removes in-screen gravity so motion gradually slows.

- SELECT: toss all dice with fresh spins.
- MENU: add one die, up to six.
- BACK: remove the most recently added die, down to zero.
- Direction buttons: override tilt along that axis.
- HOME: return to the launcher.

Start with one die. Zero leaves an empty tray; MENU adds a die again. All four
arrows remain gravity overrides, not count controls. Back no longer resets the
position, and Menu no longer toggles the hint. The count resets on app launch.
The exact physical Menu touch pad still needs identifying on the badge.

This is playful, lightweight physics: screen-plane motion with bouncing walls,
friction, contact torque that tips the cube onto a face, and three-dimensional
rotation. It is not a fair random-number
generator or a full rigid-body simulator. Images stay attached to their faces.
The cubes use orthographic projection and face shading. Dice-to-dice collisions
use projected bounding boxes rather than exact cube geometry to keep the
simulation lightweight; small gaps between angled faces are possible.

## Local preview and photos

From the project root:

```sh
python3 badge/apps/tilt_dice/preview/server.py
```

Open `http://127.0.0.1:8765`. Drag the gravity pad or hold the arrow keys to
simulate tilt. Enter or Space tosses all dice, M adds a die, and B removes one.
The + and - buttons do the same, with a visible 0 to 6 count. Choose **Lay flat**
for zero screen-plane gravity.

The web page and Python server live together in `preview/`. Unlike Stick
Dance's static preview, this preview needs its Python server to run the badge's
shared physics and save photo faces. The old command
`python3 tools/preview_tilt_dice.py` remains a compatible launcher.

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
check tilt-axis directions, slow settling, wall and dice collisions, a sideways badge,
the launcher's inverted orientation, photo readability and frame rate, all
controls, HOME and reopen, and the custom icon on the real menu. The vertical
accelerometer sign was corrected from on-badge feedback; the corrected direction,
inverted orientation, rendering speed with six dice, and Menu/Back count controls
still need confirmation. Multi-dice controls are local only until redeployment.
