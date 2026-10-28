# Badge playground

Small, independent apps for the GitHub Universe 2026 badge live under
`badge/apps/`. Development is local only until deployment is explicitly wanted.

## Apps

- [Tilt Dice](badge/apps/tilt_dice/README.md): up to six photo-covered 3D dice
  with tilt-driven gravity, collisions, and a local interactive preview.
- [Stick Dance](badge/apps/stick_dance/README.md): a controllable stick figure
  with directional dancing, auto groove, and beat-synced white case lights.

Run the Tilt Dice preview from this folder:

```sh
python3 badge/apps/tilt_dice/preview/server.py
```

Open `http://127.0.0.1:8765`. No packages, badge connection, or network account
are required. The preview listens only on this computer.
Its web page and server are committed in `badge/apps/tilt_dice/preview/`.
The previous `python3 tools/preview_tilt_dice.py` command still works.

For Stick Dance, use a separate port if Tilt Dice is already running:

```sh
python3 -m http.server 8766 --bind 127.0.0.1 --directory badge/apps/stick_dance
```

Open `http://127.0.0.1:8766/preview/` and use arrow keys or WASD to dance.
