# Stick Dance

Make a neon stick figure dance with directional controls on your keyboard or badge.

## Play locally

From the repository root, run:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory badge/apps/stick_dance
```

Open http://127.0.0.1:8765/preview/ in your browser. No packages, internet
connection, or badge are required. Use the local server rather than opening
the HTML file directly, because browsers restrict loading JSON from file URLs.

| Keyboard | Badge | Action |
|----------|-------|--------|
| Hold Left / A | LEFT | Slide left |
| Hold Right / D | RIGHT | Slide right |
| Hold Up / W | UP | Raise arms and jump |
| Hold Down / S | DOWN | Squat and bounce |
| Space | SELECT | Toggle automatic dancing |
| C | MENU | Cycle lime, pink, and cyan |
| R / Escape | BACK | Reset to manual mode and lime |
| Not mapped | HOME | Return to launcher |

You can also hold the on-screen dance buttons with a mouse or touch.
Directions temporarily override automatic dancing; releasing returns to the
routine. In manual mode, releasing returns to a gentle idle bounce.
Simultaneous directions use Left, Right, Up, Down priority. Switching away
from the browser clears held controls so the dancer never gets stuck.

## Badge app

The deployable app is `__init__.py`, `icon.png`, and `assets/dance.json`.
Open **Stick Dance** from the badge menu. The launcher owns HOME.
The app needs no Wi-Fi, credentials, extra hardware, or saved data.
Reopening starts fresh.

The white case LEDs pulse on each beat at 112 BPM. With no direction held,
all four pulse together, even during auto groove. Holding a direction selects
just that side: left pair, right pair, top pair for Up, or bottom pair for Down.
Releasing immediately restores all four without restarting the beat.
Simultaneous directions follow the same priority as the dancer.
Each pulse fades from
35% brightness to off over roughly 118 ms, then stays off until the next beat.
The lights turn off when the app exits normally or returns HOME.
Four white dots at the edges of the browser stage preview the same pulses.
These lights are white hardware LEDs; changing the dancer color does not
change their color.

The LEDs are on the back of the badge and are not readily visible from the
front. On-badge feedback confirmed Up/Down worked but Left/Right were reversed
with the initial mapping. `lights.corners` in `assets/dance.json` now mirrors
that mapping horizontally: CL0..CL3 are top right, top left, bottom left,
bottom right. The corrected mapping still needs an on-badge recheck.
Upside-down handling swaps opposite corners by name; verify both orientations.

Both versions load the same poses, tempo, and colors from `assets/dance.json`.
The HTML playground is a Canvas 2D preview, not a MicroPython emulator.
It does not prove badge graphics API compatibility, performance, or inputs.

## Checks

```sh
python3 /path/to/hyb26-skill/scripts/validate_app.py badge/apps/stick_dance
python3 -m unittest discover -s tests
node --test tests/stick_dance.test.mjs
```

Physical verification is still required: install through BADGER USB Disk Mode,
confirm menu icon support and the visible dance icon, exercise every direction,
SELECT, MENU, and BACK, then HOME/reopen. Repeat with the badge inverted.
Confirm all four case lights pulse once per beat when no direction is held,
only the matching pair pulses while holding each direction, all four return
on release (including auto mode), and lights stay synchronized after reset
and turn off after HOME. Browser checks cannot verify LEDs or their mapping.
