import builtins
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


APP = Path(__file__).resolve().parents[1] / "badge/apps/stick_dance"
MOVES = ("left", "right", "up", "down")


class DanceTests(unittest.TestCase):
    def setUp(self):
        self.held = set()
        self.pressed = set()
        self.badge = Mock(ticks_delta=16)
        self.badge.upside_down.return_value = False
        self.badge.held.side_effect = lambda button: button in self.held
        self.badge.pressed.side_effect = lambda button: button in self.pressed
        screen = Mock(width=320, height=240)
        screen.measure_text.return_value = (90, 8)
        self.env = {
            "badge": self.badge, "screen": screen, "font": Mock(),
            "color": Mock(rgb=lambda *values: values),
            "vec2": lambda x, y: (x, y), "run": Mock(),
            "HIRES": 1, "VSYNC": 2,
        }
        for action in (*MOVES, "select", "back", "menu"):
            self.env["BUTTON_" + action.upper()] = action
        real_open = builtins.open

        def app_open(path, *args, **kwargs):
            return real_open(APP / path, *args, **kwargs)

        source = (APP / "__init__.py").read_text()
        with patch("os.chdir"), patch.object(sys, "path", sys.path[:]), \
                patch("builtins.open", side_effect=app_open):
            exec(compile(source, str(APP / "__init__.py"), "exec"), self.env)

    def test_module_starts_frame_loop(self):
        self.env["run"].assert_called_once_with(self.env["update"])

    def test_directions_release_and_auto_override(self):
        for move in MOVES:
            self.held.clear()
            self.held.add(move)
            self.env["update"]()
            self.assertEqual(self.env["move"], move)
        self.held.clear()
        self.env["update"]()
        self.assertEqual(self.env["move"], "idle")
        self.pressed.add("select")
        self.env["update"]()
        self.pressed.clear()
        self.assertTrue(self.env["automatic"])
        for index, move in enumerate(MOVES):
            self.env["beat"] = index * 4 + 0.1
            self.env["update"]()
            self.assertEqual(self.env["move"], move)
        self.held.add("up")
        self.env["update"]()
        self.assertEqual(self.env["move"], "up")
        self.held.clear()
        self.env["update"]()
        self.assertEqual(self.env["move"], "down")

    def test_color_cycle_and_reset(self):
        for expected in (1, 2, 0):
            self.pressed.add("menu")
            self.env["update"]()
            self.assertEqual(self.env["palette"], expected)
        self.pressed = {"select"}
        self.env["update"]()
        self.pressed = {"back"}
        self.env["update"]()
        self.assertFalse(self.env["automatic"])
        self.assertEqual(self.env["palette"], 0)
        self.assertEqual(self.env["move"], "idle")

    def test_priority_and_large_frame_delta(self):
        self.held = {"left", "up"}
        self.badge.ticks_delta = 100000
        self.env["update"]()
        self.assertEqual(self.env["move"], "left")
        self.assertAlmostEqual(self.env["beat"], 50 * 112 / 60000)

    def test_pose_matches_shared_interpolation(self):
        data = json.loads((APP / "assets/dance.json").read_text())
        self.held.add("up")
        self.env["update"]()
        mix = (1 - math.cos(self.env["beat"] * 2 * math.pi)) / 2
        smoothing = 1 - math.exp(-16 / 65)
        first, second = data["moves"]["up"]["frames"]
        idle = data["moves"]["idle"]["frames"][0]
        for index, point in enumerate(self.env["pose"]):
            for axis, value in enumerate(point):
                target = first[index][axis] * (1 - mix) + second[index][axis] * mix
                expected = idle[index][axis] + (target - idle[index][axis]) * smoothing
                self.assertAlmostEqual(value, expected)

    def test_light_pulse_peak_fade_off_and_beat_wrap(self):
        for beat, expected in ((0, 0.35), (0.11, 0.175), (0.22, 0),
                               (0.75, 0), (1, 0.35), (15.11, 0.175)):
            self.env["beat"] = beat
            self.assertAlmostEqual(self.env["light_brightness"](), expected)

    def test_light_output_tracks_same_clock_in_manual_and_auto(self):
        for automatic in (False, True):
            self.env["automatic"] = automatic
            self.env["beat"] = 15.99
            self.env["update"]()
            self.assertLess(self.env["beat"], 1)
            self.badge.caselights.assert_called_with(*([self.env["light_brightness"]()] * 4))
            self.assertGreater(self.env["light_brightness"](), 0)

    def test_directional_lights_and_inversion(self):
        self.env["beat"] = 0
        expected = {
            "left": (0, 0.35, 0.35, 0),
            "right": (0.35, 0, 0, 0.35),
            "up": (0.35, 0.35, 0, 0),
            "down": (0, 0, 0.35, 0.35),
        }
        for direction, levels in expected.items():
            self.assertEqual(self.env["light_levels"](direction, False), levels)
            self.assertEqual(self.env["light_levels"](direction, True),
                             levels[2:] + levels[:2])

    def test_release_restores_all_lights_even_during_auto(self):
        self.badge.ticks_delta = 0
        for automatic in (False, True):
            self.env["automatic"] = automatic
            self.held = {"left", "up"}
            self.env["update"]()
            self.badge.caselights.assert_called_with(0, 0.35, 0.35, 0)
            self.held.clear()
            self.env["update"]()
            self.badge.caselights.assert_called_with(0.35, 0.35, 0.35, 0.35)

    def test_lights_off_on_exit(self):
        self.env["on_exit"]()
        self.badge.caselights.assert_called_with(0)

    def test_run_cleanup_on_return(self):
        source = (APP / "__init__.py").read_text()
        wrapper = source[source.rindex("\nrun(update)"):]
        self.badge.caselights.reset_mock()
        exec(wrapper, self.env)
        self.badge.caselights.assert_called_with(0)


if __name__ == "__main__":
    unittest.main()
