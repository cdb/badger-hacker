# Badge playground

Small, independent apps for the GitHub Universe 2026 badge live under
`badge/apps/`. Development is local only until deployment is explicitly wanted.

## Apps

- [Tilt Dice](badge/apps/tilt_dice/README.md): a photo-covered 3D die with
  tilt-driven gravity, bouncing walls, and a local interactive preview.

Run the preview from this folder:

```sh
python3 tools/preview_tilt_dice.py
```

Open `http://127.0.0.1:8765`. No packages, badge connection, or network account
are required. The preview listens only on this computer.
