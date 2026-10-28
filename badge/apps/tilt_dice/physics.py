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
    return clamp(sign * ax / 16384, -1, 1), clamp(sign * ay / 16384, -1, 1)


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

    def _support(self, axis, direction, acceleration, dt):
        matrix = rotation(self.q)
        row = matrix[axis]
        # Average the support near an edge/face instead of alternating vertices.
        corner = [direction * clamp(value / 0.04, -1, 1) * self.radius for value in row]
        rx, ry, rz = transform(matrix, corner)
        force = -direction * acceleration
        scale = 1.5 * dt / (self.radius * self.radius)
        if axis == 0:
            self.wy += rz * force * scale
            self.wz -= ry * force * scale
        else:
            self.wx -= rz * force * scale
            self.wz += rx * force * scale

    def _settle(self, axis):
        matrix = rotation(self.q)
        index = max(range(3), key=lambda i: abs(matrix[axis][i]))
        normal = tuple(matrix[i][index] for i in range(3))
        target = [0, 0, 0]
        target[axis] = 1 if normal[axis] > 0 else -1
        alignment = abs(normal[axis])
        if alignment < 0.99999 or max(abs(self.wx), abs(self.wy), abs(self.wz)) > 0.08:
            return
        # Remove sub-pixel contact jitter only once a face is already at rest.
        correction = (1 + alignment,
                      normal[1] * target[2] - normal[2] * target[1],
                      normal[2] * target[0] - normal[0] * target[2],
                      normal[0] * target[1] - normal[1] * target[0])
        length = math.sqrt(sum(v * v for v in correction))
        self.q = multiply(tuple(v / length for v in correction), self.q)
        self._normalize()
        if axis == 0:
            self.wy, self.wz = 0.0, 0.0
        else:
            self.wx, self.wz = 0.0, 0.0

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
            contact_x = self.x <= left + ex + 0.05 or self.x >= right - ex - 0.05
            contact_y = self.y <= top + ey + 0.05 or self.y >= bottom - ey - 0.05
            support_x = 0
            support_y = 0
            if contact_x:
                direction = -1 if self.x < (left + right) / 2 else 1
                self.x = clamp(self.x, left + ex, right - ex)
                outward = (self.x <= left + ex and self.vx < 0 or
                           self.x >= right - ex and self.vx > 0)
                if outward:
                    self.vx = -self.vx * 0.42 if abs(self.vx) > 12 else 0
                self.vy *= math.exp(-dt * 9)
                support_x = max(0, direction * ax)
                self._support(0, direction, support_x, dt)
            if contact_y:
                direction = -1 if self.y < (top + bottom) / 2 else 1
                self.y = clamp(self.y, top + ey, bottom - ey)
                outward = (self.y <= top + ey and self.vy < 0 or
                           self.y >= bottom - ey and self.vy > 0)
                if outward:
                    self.vy = -self.vy * 0.42 if abs(self.vy) > 12 else 0
                self.vx *= math.exp(-dt * 9)
                support_y = max(0, direction * ay)
                self._support(1, direction, support_y, dt)

            # Use collision-resolved velocity so gravity cannot spin a resting die.
            blend = 1 - math.exp(-dt * 3)
            self.wx += (-self.vy / self.radius - self.wx) * blend
            self.wy += (self.vx / self.radius - self.wy) * blend
            self.wz *= math.exp(-dt * 2.5)
            if support_x or support_y:
                damping = math.exp(-dt * 4)
                self.wx *= damping
                self.wy *= damping
                self.wz *= damping
                if self.vx * self.vx + self.vy * self.vy < 16:
                    if support_x:
                        self._settle(0)
                    if support_y:
                        self._settle(1)
                    ex, ey = self.extents()
                    self.x = clamp(self.x, left + ex, right - ex)
                    self.y = clamp(self.y, top + ey, bottom - ey)

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


class DiceTray:
    MAX_DICE = 6

    def __init__(self, width=320, height=240):
        self.width, self.height = width, height
        self.dice = []
        self.add()

    def add(self):
        if len(self.dice) >= self.MAX_DICE:
            return
        die = Dice(self.width, self.height)
        die.radius = min(self.width, self.height) / 12
        left, top, right, bottom = die.bounds
        # Six well-spaced entry positions; prefer the one furthest from other dice.
        positions = [(left + (right - left) * (column + 0.5) / 3,
                      top + (bottom - top) * (row + 0.5) / 2)
                     for row in range(2) for column in range(3)]
        die.x, die.y = max(positions, key=lambda p: min(
            (p[0] - other.x) ** 2 + (p[1] - other.y) ** 2 for other in self.dice
        ) if self.dice else self.width * self.width)
        self.dice.append(die)

    def remove(self):
        if self.dice:
            self.dice.pop()

    def roll(self):
        for die in self.dice:
            die.roll()

    def flip(self):
        for die in self.dice:
            die.flip()

    def _constrain(self, die):
        ex, ey = die.extents()
        left, top, right, bottom = die.bounds
        die.x = clamp(die.x, left + ex, right - ex)
        die.y = clamp(die.y, top + ey, bottom - ey)

    def _collide(self, a, b, dt):
        ax, ay = a.extents()
        bx, by = b.extents()
        dx, dy = b.x - a.x, b.y - a.y
        ox, oy = ax + bx - abs(dx), ay + by - abs(dy)
        if ox <= 0 or oy <= 0:
            return
        # Projected bounding boxes keep pair collisions cheap on MicroPython.
        axis = 0 if ox < oy else 1
        direction = 1 if (dx if axis == 0 else dy) >= 0 else -1
        overlap = ox if axis == 0 else oy
        position = "x" if axis == 0 else "y"
        velocity = "vx" if axis == 0 else "vy"
        setattr(a, position, getattr(a, position) - direction * overlap / 2)
        setattr(b, position, getattr(b, position) + direction * overlap / 2)
        relative = (getattr(b, velocity) - getattr(a, velocity)) * direction
        if relative < 0:
            impulse = -relative * 0.65
            setattr(a, velocity, getattr(a, velocity) - direction * impulse)
            setattr(b, velocity, getattr(b, velocity) + direction * impulse)
        for die, sign in ((a, direction), (b, -direction)):
            gravity = die.gx if axis == 0 else die.gy
            support = max(0, gravity * sign * 580)
            if support:
                die._support(axis, sign, support, dt)
                damping = math.exp(-dt * 4)
                die.wx *= damping
                die.wy *= damping
                die.wz *= damping
                if die.vx * die.vx + die.vy * die.vy < 16:
                    die._settle(axis)

    def step(self, elapsed, gx, gy):
        remaining = clamp(elapsed, 0, 0.1)
        while remaining > 0.000001:
            dt = min(remaining, 1 / 120)
            remaining -= dt
            for die in self.dice:
                die.step(dt, gx, gy)
            for iteration in range(4):
                for i, die in enumerate(self.dice):
                    for other in self.dice[i + 1:]:
                        self._collide(die, other, dt if iteration == 0 else 0)
                for die in self.dice:
                    self._constrain(die)

    def faces(self):
        return [face for die in self.dice for face in die.faces()]


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
