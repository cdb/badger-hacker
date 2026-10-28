import importlib.util
import math
from pathlib import Path
import random
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "badge" / "apps" / "tilt_dice"
sys.path.insert(0, str(APP))
from physics import Dice, DiceTray, gravity_from_imu, rotation, texture_spans

spec = importlib.util.spec_from_file_location("preview", APP / "preview" / "server.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        random.seed(41)
        self.die = Dice()

    def advance(self, gx, gy, seconds=10, hz=60):
        for _ in range(int(seconds * hz)):
            self.die.step(1 / hz, gx, gy)

    def assert_contained(self):
        ex, ey = self.die.extents()
        left, top, right, bottom = self.die.bounds
        self.assertGreaterEqual(self.die.x - ex, left - 0.00001)
        self.assertLessEqual(self.die.x + ex, right + 0.00001)
        self.assertGreaterEqual(self.die.y - ey, top - 0.00001)
        self.assertLessEqual(self.die.y + ey, bottom + 0.00001)

    def test_settles_at_each_lowest_edge(self):
        for gx, gy in ((0, 1), (-1, 0), (1, 0), (0, -1)):
            with self.subTest(gravity=(gx, gy)):
                self.die.reset()
                self.advance(gx, gy, 20)
                self.assert_contained()
                ex, ey = self.die.extents()
                left, top, right, bottom = self.die.bounds
                gap = {(-1, 0): self.die.x - ex - left,
                       (1, 0): right - self.die.x - ex,
                       (0, -1): self.die.y - ey - top,
                       (0, 1): bottom - self.die.y - ey}[(gx, gy)]
                self.assertLess(gap, 0.1)
                self.assertLess(math.hypot(self.die.vx, self.die.vy), 0.5)
                self.assertLess(max(abs(self.die.wx), abs(self.die.wy), abs(self.die.wz)), 0.05)
                axis = 0 if gx else 1
                self.assertGreater(max(abs(v) for v in rotation(self.die.q)[axis]), 0.99999)
                self.assertAlmostEqual((ex, ey)[axis], self.die.radius, places=3)

    def test_tosses_land_on_faces_not_corners(self):
        for seed in range(12):
            for gx, gy in ((0, 1), (-1, 0), (1, 0), (0, -1), (1, 1)):
                with self.subTest(seed=seed, gravity=(gx, gy)):
                    random.seed(seed)
                    self.die.reset()
                    self.die.roll()
                    self.advance(gx, gy, 15)
                    self.assert_contained()
                    matrix = rotation(self.die.q)
                    for axis, gravity in enumerate((gx, gy)):
                        if gravity:
                            self.assertGreater(max(abs(v) for v in matrix[axis]), 0.99999)
                    self.assertLess(max(abs(self.die.wx), abs(self.die.wy), abs(self.die.wz)), 0.05)

    def test_near_corner_tips_over_instead_of_freezing(self):
        for degrees in (20, 43, 47, 70):
            with self.subTest(angle=degrees):
                angle = math.radians(degrees) / 2
                self.die.reset()
                self.die.q = (math.cos(angle), 0, 0, math.sin(angle))
                self.advance(0, 1, 12)
                self.assertGreater(max(abs(v) for v in rotation(self.die.q)[1]), 0.99999)

    def test_settled_die_can_tumble_to_a_different_wall(self):
        self.advance(0, 1, 12)
        self.advance(-1, 0, 12)
        ex, _ey = self.die.extents()
        self.assertAlmostEqual(self.die.x - ex, self.die.bounds[0], places=3)
        self.assertGreater(max(abs(v) for v in rotation(self.die.q)[0]), 0.99999)

    def test_no_drift_after_settling(self):
        self.advance(0, 1, 25)
        before = self.die.q
        self.advance(0, 1, 10)
        self.assertLess(max(abs(a - b) for a, b in zip(before, self.die.q)), 0.001)

    def test_toss_and_changing_gravity_never_clip(self):
        for i in range(1600):
            if i % 120 == 0:
                self.die.roll()
            self.die.step(1 / 30, math.sin(i / 90), math.cos(i / 90))
            self.assert_contained()
            self.assertAlmostEqual(sum(v * v for v in self.die.q), 1, places=10)

    def test_flat_badge_slows_down(self):
        self.die.roll()
        self.advance(0, 0, 20)
        self.assertLess(math.hypot(self.die.vx, self.die.vy), 0.1)
        self.assert_contained()

    def test_frame_rate_independence(self):
        results = []
        for hz in (30, 60, 120):
            self.die.reset()
            self.advance(0.3, 0.8, seconds=0.3, hz=hz)
            results.append((self.die.x, self.die.y, *self.die.q))
        for state in results[1:]:
            for a, b in zip(results[0], state):
                self.assertAlmostEqual(a, b, places=7)

    def test_pause_catch_up_is_bounded(self):
        other = Dice()
        self.die.step(1000, 1, 1)
        other.step(0.1, 1, 1)
        self.assertEqual(self.die.q, other.q)
        self.assertEqual(self.die.x, other.x)

    def test_flip_preserves_involution_and_bounds(self):
        self.advance(0, 1)
        before = (self.die.x, self.die.y, self.die.vx, self.die.vy)
        self.die.flip()
        self.assert_contained()
        self.die.flip()
        for a, b in zip(before, (self.die.x, self.die.y, self.die.vx, self.die.vy)):
            self.assertAlmostEqual(a, b)

    def test_imu_scaling_and_orientation(self):
        self.assertEqual(gravity_from_imu(0, 16384), (0, 1))
        self.assertEqual(gravity_from_imu(0, -16384), (0, -1))
        self.assertEqual(gravity_from_imu(0, -16384, True), (0, 1))
        self.assertEqual(gravity_from_imu(0, 16384, True), (0, -1))
        self.assertEqual(gravity_from_imu(16384, 0), (1, 0))
        self.assertEqual(gravity_from_imu(100000, -100000), (1, -1))

    def test_projection_is_affine_and_face_ids_are_stable(self):
        for _ in range(120):
            self.die.step(1 / 60, 0.4, 0.7)
            for _depth, face, (a, b, c, d), light in self.die.faces():
                self.assertIn(face, range(6))
                self.assertTrue(0.3 <= light <= 1)
                for axis in (0, 1):
                    self.assertAlmostEqual(a[axis] + c[axis], b[axis] + d[axis])

    def test_texture_spans_map_to_face(self):
        corners = ((10, 10), (58, 10), (58, 58), (10, 58))
        rows = list(texture_spans(corners))
        self.assertEqual(len(rows), 48)
        for x, y, length, u0, v0, u1, v1 in rows:
            self.assertEqual((x, length), (10, 48))
            self.assertAlmostEqual(u0, 0.5 / 48)
            self.assertAlmostEqual(u1, 47.5 / 48)
            self.assertAlmostEqual(v0, (y - 10 + 0.5) / 48)
            self.assertAlmostEqual(v0, v1)

    def test_rotated_spans_stay_inside_uv_range(self):
        self.die.roll()
        for _ in range(100):
            self.die.step(1 / 30, 0.7, 0.3)
            for _depth, _face, corners, _light in self.die.faces():
                for x, y, length, *uvs in texture_spans(corners):
                    self.assertGreater(length, 0)
                    for value in uvs:
                        self.assertTrue(-0.00001 <= value <= 1.00001, value)


class TrayTests(unittest.TestCase):
    def setUp(self):
        random.seed(41)
        self.tray = DiceTray()

    def test_count_is_bounded_and_empty_tray_is_usable(self):
        self.assertEqual(len(self.tray.dice), 1)
        for _ in range(10):
            self.tray.remove()
        self.tray.roll()
        self.tray.flip()
        self.tray.step(0.1, 1, 1)
        self.assertEqual(self.tray.faces(), [])
        for _ in range(10):
            self.tray.add()
        self.assertEqual(len(self.tray.dice), 6)
        self.assertEqual(len({(die.x, die.y) for die in self.tray.dice}), 6)

    def test_remove_preserves_remaining_dice_and_add_does_not_reset(self):
        original = self.tray.dice[0]
        original.x = 100
        self.tray.add()
        self.tray.remove()
        self.assertIs(self.tray.dice[0], original)
        self.assertEqual(original.x, 100)

    def test_toss_applies_to_every_die(self):
        for _ in range(5):
            self.tray.add()
        self.tray.roll()
        for die in self.tray.dice:
            self.assertLess(die.vy, -169)
            self.assertGreater(abs(die.wx) + abs(die.wy) + abs(die.wz), 0)

    def test_pair_collision_separates_and_bounces(self):
        self.tray.add()
        a, b = self.tray.dice
        a.q = b.q = (1, 0, 0, 0)
        a.x, b.x, a.y, b.y = 140, 175, 120, 120
        a.vx, b.vx = 50, -50
        self.tray.step(1 / 120, 0, 0)
        self.assertGreaterEqual(b.x - a.x, a.extents()[0] + b.extents()[0] - 0.001)
        self.assertLess(a.vx, 0)
        self.assertGreater(b.vx, 0)

    def test_six_dice_remain_contained_with_changing_gravity(self):
        for _ in range(5):
            self.tray.add()
        for frame in range(600):
            if frame % 120 == 0:
                self.tray.roll()
            self.tray.step(1 / 30, math.sin(frame / 70), math.cos(frame / 70))
            for die in self.tray.dice:
                ex, ey = die.extents()
                left, top, right, bottom = die.bounds
                self.assertGreaterEqual(die.x - ex, left - 0.00001)
                self.assertLessEqual(die.x + ex, right + 0.00001)
                self.assertGreaterEqual(die.y - ey, top - 0.00001)
                self.assertLessEqual(die.y + ey, bottom + 0.00001)

    def test_six_dice_piles_do_not_overlap_visibly(self):
        for gx, gy in ((0, 1), (1, 0), (1, 1)):
            with self.subTest(gravity=(gx, gy)):
                random.seed(41)
                self.tray = DiceTray()
                for _ in range(5):
                    self.tray.add()
                self.tray.roll()
                for _ in range(900):
                    self.tray.step(1 / 60, gx, gy)
                for i, a in enumerate(self.tray.dice):
                    for b in self.tray.dice[i + 1:]:
                        ax, ay = a.extents()
                        bx, by = b.extents()
                        overlap = min(ax + bx - abs(a.x - b.x),
                                      ay + by - abs(a.y - b.y))
                        self.assertLess(overlap, 0.5)


class AssetTests(unittest.TestCase):
    def test_all_faces_and_custom_icon_are_square_pngs(self):
        import base64
        for path in [APP / "assets" / ("%d.png" % i) for i in range(1, 7)] + [APP / "icon.png"]:
            value = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()
            self.assertEqual(preview.decode_face(value), path.read_bytes())

    def test_rejects_bad_assets_and_numeric_inputs(self):
        for value in ("not a png", "data:image/png;base64,%%", "data:image/png;base64,AAAA"):
            with self.assertRaises((ValueError, preview.binascii.Error)):
                preview.decode_face(value)
        for value in (True, "1", float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                preview.number({"dt": value}, "dt", 0)

    def test_preview_http_and_photo_upload_in_isolated_folder(self):
        import base64
        import json

        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            (app / "assets").mkdir()
            original = (APP / "assets" / "1.png").read_bytes()
            for i in range(1, 7):
                (app / "assets" / ("%d.png" % i)).write_bytes(original)
            server = preview.HTTPServer(("127.0.0.1", 0), preview.Handler)
            server.tray = DiceTray()
            url = "http://127.0.0.1:%d" % server.server_port
            thread = threading.Thread(target=server.serve_forever)
            thread.start()

            def post(path, value, origin=url):
                request = Request(url + path, json.dumps(value).encode(), {
                    "Content-Type": "application/json", "Origin": origin})
                with urlopen(request, timeout=3) as response:
                    return json.load(response)

            try:
                with patch.object(preview, "APP", app):
                    with urlopen(url, timeout=3) as response:
                        self.assertIn(b"Choose photos", response.read())
                    request = Request(url, headers={"Host": "example.com"})
                    with self.assertRaises(HTTPError) as raised:
                        urlopen(request, timeout=3)
                    self.assertEqual(raised.exception.code, 403)
                    raised.exception.close()
                    state = post("/step", {"dt": 0.1, "gx": -1, "gy": 0, "action": "roll"})
                    self.assertTrue(state["faces"])
                    self.assertEqual(state["count"], 1)
                    for _ in range(8):
                        state = post("/step", {"action": "add", "dt": 0})
                    self.assertEqual(state["count"], 6)
                    for _ in range(8):
                        state = post("/step", {"action": "remove", "dt": 0})
                    self.assertEqual(state, {"faces": [], "count": 0})
                    state = post("/step", {"action": "add", "dt": 0})
                    self.assertEqual(state["count"], 1)
                    png = "data:image/png;base64," + base64.b64encode(original).decode()
                    self.assertEqual(post("/faces", {"faces": [png]}), {"saved": 6})
                    for i in range(1, 7):
                        with urlopen(url + "/assets/%d.png" % i, timeout=3) as response:
                            self.assertEqual(response.read(), original)
                    for path, data, origin, code in (
                        ("/faces", {"faces": [png]}, "https://example.com", 403),
                        ("/faces", {"faces": [png] * 7}, url, 400),
                        ("/step", {"dt": "not a number"}, url, 400),
                        ("/step", {"action": "unknown"}, url, 400),
                    ):
                        with self.subTest(path=path, code=code):
                            with self.assertRaises(HTTPError) as raised:
                                post(path, data, origin)
                            self.assertEqual(raised.exception.code, code)
                            raised.exception.close()
            finally:
                server.shutdown()
                thread.join()
                server.server_close()

    def test_badge_entrypoint_and_controls_with_runtime_stubs(self):
        class Screen:
            width, height, clip = 320, 240, (0, 0, 320, 240)
            spans = 0
            text_log = []

            def rectangle(self, *args):
                pass

            def triangle(self, *args):
                pass

            def line(self, *args):
                pass

            def text(self, value, *args):
                self.text_log.append(value)

            def blit_hspan(self, texture, x, y, length, *uvs):
                self.spans += 1
                if length <= 0:
                    raise AssertionError("Invalid span")

        class Badge:
            ticks_delta = 16
            down = False
            pressed_buttons = set()

            def mode(self, flags):
                pass

            def upside_down(self):
                return self.down

            def imu(self):
                return (0, -16384 if self.down else 16384, 0, 0, 0, 0)

            def held(self, button):
                return button in self.pressed_buttons

            def pressed(self, button):
                return button in self.pressed_buttons

        class Image:
            width = height = 48

            @staticmethod
            def load(path):
                if not (APP / path).exists():
                    raise OSError("Missing face")
                return Image()

        class Color:
            @staticmethod
            def rgb(*values):
                return values

        screen, badge = Screen(), Badge()
        namespace = {"screen": screen, "badge": badge, "image": Image,
                     "color": Color, "font": type("Font", (), {"nope": "nope"}),
                     "HIRES": 1, "VSYNC": 2}
        for button in ("SELECT", "BACK", "MENU", "UP", "DOWN", "LEFT", "RIGHT"):
            namespace["BUTTON_" + button] = button

        def run(update):
            for button, count in (("SELECT", 1), ("BACK", 0), ("BACK", 0),
                                  ("MENU", 1), ("MENU", 2), ("SELECT", 2),
                                  ("UP", 2), ("DOWN", 2), ("LEFT", 2), ("RIGHT", 2)):
                badge.pressed_buttons = {button}
                with patch.object(namespace["tray"], "step", wraps=namespace["tray"].step) as step:
                    update()
                    if button in ("UP", "DOWN", "LEFT", "RIGHT"):
                        gx, gy = step.call_args.args[1:]
                        expected = {"UP": (0, -1), "DOWN": (0, 1),
                                    "LEFT": (-1, 1), "RIGHT": (1, 1)}[button]
                        self.assertEqual((gx, gy), expected)
                self.assertEqual(len(namespace["tray"].dice), count)
            badge.down = True
            update()

        namespace["run"] = run
        original_path = sys.path[:]
        try:
            with patch("os.chdir") as chdir:
                exec(compile((APP / "__init__.py").read_text(), "__init__.py", "exec"), namespace)
                chdir.assert_called_once_with("/system/apps/tilt_dice")
        finally:
            sys.path[:] = original_path
        self.assertGreater(screen.spans, 0)
        self.assertIsNone(namespace["asset_error"])
        self.assertTrue(namespace["orientation"])
        self.assertNotIn("BUTTON_HOME", namespace)
        namespace["asset_error"] = "Check assets/1.png"
        spans = screen.spans
        namespace["update"]()
        self.assertEqual(screen.spans, spans)
        self.assertIn("Check assets/1.png", screen.text_log)


if __name__ == "__main__":
    unittest.main()
