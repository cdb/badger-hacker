"""Small, dependency-free dice simulation shared by the badge and local preview."""

import math
import random


VERTICES = (
    (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
    (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
)
FACES = (
    (0, 1, 2, 3), (1, 5, 6, 2), (4, 0, 3, 7),
    (4, 5, 1, 0), (3, 2, 6, 7), (5, 4, 7, 6),
)
NORMALS = ((0, 0, 1), (1, 0, 0), (-1, 0, 0),
           (0, -1, 0), (0, 1, 0), (0, 0, -1))


def clamp(value, low, high):
    return max(low, min(high, value))


def gravity_from_imu(ax, ay, upside_down=False):
    """Map sensor Gs to display coordinates, including the launcher's 180 flip."""
    sign = -1 if upside_down else 1
    return clamp(sign * ax / 16384, -1, 1), clamp(-sign * ay / 16384, -1, 1)


def multiply(a, b):
    w, x, y, z = a
    bw, bx, by, bz = b
    return (w * bw - x * bx - y * by - z * bz,
            w * bx + x * bw + y * bz - z * by,
            w * by - x * bz + y * bw + z * bx,
            w * bz + x * by - y * bx + z * bw)


def rotation(q):
    w, x, y, z = q
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
        (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
        (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)),
    )


def transform(matrix, point):
    x, y, z = point
    return tuple(row[0] * x + row[1] * y + row[2] * z for row in matrix)


class Dice:
    def __init__(self, width=320, height=240):
        self.width = width
        self.height = height
        self.radius = min(width, height) / 8
        self.bounds = (8, 30, width - 8, height - 12)
        self.reset()

    def reset(self):
        self.x = self.width / 2
        self.y = self.height / 2
        self.vx, self.vy = 0.0, 0.0
        self.wx, self.wy, self.wz = 0.0, 0.0, 0.0
        self.q = (0.91, 0.23, -0.31, 0.12)
        self._normalize()
        self.gx, self.gy = 0.0, 0.0

    def roll(self):
        self.vx = random.uniform(-230, 230)
        self.vy = random.uniform(-280, -170)
        self.wx = random.uniform(-12, 12)
        self.wy = random.uniform(-12, 12)
        self.wz = random.uniform(-8, 8)

    def flip(self):
        left, top, right, bottom = self.bounds
        self.x, self.y = left + right - self.x, top + bottom - self.y
        self.vx, self.vy = -self.vx, -self.vy
        self.wx, self.wy = -self.wx, -self.wy
        self.gx, self.gy = -self.gx, -self.gy
        self.q = multiply((0, 0, 0, 1), self.q)

    def _normalize(self):
        length = math.sqrt(sum(value * value for value in self.q))
        self.q = tuple(value / length for value in self.q)

    def extents(self):
        matrix = rotation(self.q)
        return (self.radius * sum(abs(value) for value in matrix[0]),
                self.radius * sum(abs(value) for value in matrix[1]))

    def step(self, elapsed, gx, gy):
        # Bound catch-up work after a pause and resolve fast motion in short steps.
        remaining = clamp(elapsed, 0, 0.1)
        gx, gy = clamp(gx, -1, 1), clamp(gy, -1, 1)
        while remaining > 0.000001:
            dt = min(remaining, 1 / 120)
            remaining -= dt
            smoothing = 1 - math.exp(-dt * 14)
            self.gx += (gx - self.gx) * smoothing
            self.gy += (gy - self.gy) * smoothing
            ax = 0 if abs(self.gx) < 0.025 else self.gx * 580
            ay = 0 if abs(self.gy) < 0.025 else self.gy * 580
            self.vx = (self.vx + ax * dt) * math.exp(-0.9 * dt)
            self.vy = (self.vy + ay * dt) * math.exp(-0.9 * dt)
            self.x += self.vx * dt
            self.y += self.vy * dt

            derivative = multiply((0, self.wx, self.wy, self.wz), self.q)
            self.q = tuple(self.q[i] + derivative[i] * dt / 2 for i in range(4))
            self._normalize()

            ex, ey = self.extents()
            left, top, right, bottom = self.bounds
            contact_x = self.x < left + ex or self.x > right - ex
            contact_y = self.y < top + ey or self.y > bottom - ey
            if contact_x:
                self.x = clamp(self.x, left + ex, right - ex)
                outward = (self.x <= left + ex and self.vx < 0 or
                           self.x >= right - ex and self.vx > 0)
                if outward:
                    self.vx = -self.vx * 0.42 if abs(self.vx) > 12 else 0
                self.vy *= math.exp(-dt * 9)
            if contact_y:
                self.y = clamp(self.y, top + ey, bottom - ey)
                outward = (self.y <= top + ey and self.vy < 0 or
                           self.y >= bottom - ey and self.vy > 0)
                if outward:
                    self.vy = -self.vy * 0.42 if abs(self.vy) > 12 else 0
                self.vx *= math.exp(-dt * 9)

            # Use collision-resolved velocity so gravity cannot spin a resting die.
            blend = 1 - math.exp(-dt * 3)
            self.wx += (-self.vy / self.radius - self.wx) * blend
            self.wy += (self.vx / self.radius - self.wy) * blend
            self.wz *= math.exp(-dt * 2.5)
            if (contact_x or contact_y) and self.vx * self.vx + self.vy * self.vy < 16:
                damping = math.exp(-dt * 16)
                self.wx *= damping
                self.wy *= damping
                self.wz *= damping
                if max(abs(self.wx), abs(self.wy), abs(self.wz)) < 0.02:
                    self.wx, self.wy, self.wz = 0.0, 0.0, 0.0

    def faces(self):
        matrix = rotation(self.q)
        points = [transform(matrix, point) for point in VERTICES]
        visible = []
        for index, face in enumerate(FACES):
            normal = transform(matrix, NORMALS[index])
            if normal[2] <= 0.015:
                continue
            corners = [(self.x + points[v][0] * self.radius,
                        self.y + points[v][1] * self.radius) for v in face]
            depth = sum(points[v][2] for v in face) / 4
            light = clamp(0.55 + 0.45 * (
                -0.3 * normal[0] - 0.4 * normal[1] + 0.85 * normal[2]), 0.3, 1)
            visible.append((depth, index, corners, light))
        visible.sort()
        return visible


def texture_spans(corners):
    """Affine scanlines for an orthographic cube face, using normalized UVs."""
    a, b, c, d = corners
    vertices = ((a[0], a[1], 0, 0), (b[0], b[1], 1, 0),
                (c[0], c[1], 1, 1), (d[0], d[1], 0, 1))
    for y in range(math.ceil(min(p[1] for p in corners)),
                   math.ceil(max(p[1] for p in corners))):
        sample_y = y + 0.5
        hits = []
        for i in range(4):
            start, end = vertices[i], vertices[(i + 1) % 4]
            if min(start[1], end[1]) <= sample_y < max(start[1], end[1]):
                t = (sample_y - start[1]) / (end[1] - start[1])
                hits.append(tuple(start[k] + t * (end[k] - start[k]) for k in (0, 2, 3)))
        if len(hits) != 2:
            continue
        hits.sort()
        left, right = hits
        x0 = math.ceil(left[0] - 0.5)
        x1 = math.ceil(right[0] - 0.5)
        if x1 <= x0:
            continue
        scale = 1 / (right[0] - left[0])
        t0 = (x0 + 0.5 - left[0]) * scale
        t1 = (x1 - 0.5 - left[0]) * scale
        u0, v0 = (left[k] + (right[k] - left[k]) * t0 for k in (1, 2))
        u1, v1 = (left[k] + (right[k] - left[k]) * t1 for k in (1, 2))
        yield x0, y, x1 - x0, u0, v0, u1, v1
