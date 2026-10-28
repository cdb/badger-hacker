"""Compatibility launcher for the app-local Tilt Dice preview."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parents[1] /
            "badge" / "apps" / "tilt_dice" / "preview" / "server.py"),
        run_name="__main__",
    )
