import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createState, step, moves, lightBrightness, lightLevels } from "../badge/apps/stick_dance/preview/dance.mjs";

const data = JSON.parse(readFileSync(new URL("../badge/apps/stick_dance/assets/dance.json", import.meta.url)));

test("held directions select matching lights and release restores all, even in auto", () => {
  const expected = {
    left: [0, 0.35, 0.35, 0], right: [0.35, 0, 0, 0.35],
    up: [0.35, 0.35, 0, 0], down: [0, 0, 0.35, 0.35],
  };
  for (const automatic of [false, true]) {
    const state = createState(data);
    state.automatic = automatic;
    for (const move of moves) {
      step(state, data, 0, new Set([move]));
      assert.deepEqual(lightLevels(state, data), expected[move]);
    }
    step(state, data, 0, new Set(["up", "left"]));
    assert.deepEqual(lightLevels(state, data), expected.left);
    step(state, data, 0, new Set());
    assert.deepEqual(lightLevels(state, data), [0.35, 0.35, 0.35, 0.35]);
  }
});

test("case lights pulse once per beat with bounded brightness and an off interval", () => {
  for (const [beat, expected] of [[0, 0.35], [0.11, 0.175], [0.22, 0],
    [0.75, 0], [1, 0.35], [15.11, 0.175], [16, 0.35]]) {
    assert(Math.abs(lightBrightness(beat, data) - expected) < 1e-10);
  }
  for (let beat = 0; beat < 16; beat += 0.01) {
    assert(lightBrightness(beat, data) >= 0);
    assert(lightBrightness(beat, data) <= 0.35);
  }
});

test("manual controls select every move and release to idle", () => {
  const state = createState(data);
  for (const move of moves) {
    step(state, data, 16, new Set([move]));
    assert.equal(state.move, move);
    assert(state.pose.flat().every(Number.isFinite));
  }
  step(state, data, 16, new Set());
  assert.equal(state.move, "idle");
});

test("auto cycles all moves, with temporary manual override", () => {
  const state = createState(data);
  state.automatic = true;
  for (let index = 0; index < 4; index++) {
    state.beat = index * 4 + 0.1;
    step(state, data, 0, new Set());
    assert.equal(state.move, moves[index]);
  }
  step(state, data, 16, new Set(["up"]));
  assert.equal(state.move, "up");
  step(state, data, 16, new Set());
  assert.equal(state.move, "down");
  assert(state.automatic);
});

test("simultaneous directions have deterministic badge-compatible priority", () => {
  const state = createState(data);
  step(state, data, 16, new Set(["down", "left", "up"]));
  assert.equal(state.move, "left");
});

test("timing is frame-rate independent and long pauses are bounded", () => {
  const fast = createState(data);
  const slow = createState(data);
  for (let frame = 0; frame < 120; frame++) step(fast, data, 1000 / 120, new Set());
  for (let frame = 0; frame < 30; frame++) step(slow, data, 1000 / 30, new Set());
  assert(Math.abs(fast.beat - slow.beat) < 1e-10);
  assert(Math.abs(fast.beat - 112 / 60) < 1e-10);
  const before = fast.beat;
  step(fast, data, 100000, new Set());
  assert(Math.abs(fast.beat - before - 50 * 112 / 60000) < 1e-10);
});

test("reset state does not share mutable pose arrays with assets", () => {
  const state = createState(data);
  state.pose[0][0] = 100;
  assert.equal(createState(data).pose[0][0], 0);
  assert.equal(data.moves.idle.frames[0][0][0], 0);
});

test("all poses and the head stay inside the badge stage", () => {
  for (const move of Object.values(data.moves)) {
    assert.equal(move.frames.length, 2);
    for (const frame of move.frames) {
      assert.equal(frame.length, 11);
      for (const [x, y] of frame) {
        assert(x + 160 >= 0 && x + 160 <= 320);
        assert(y + 132 >= 26 && y + 132 <= 174);
      }
      assert(frame[0][1] + 132 - 11 >= 26);
    }
  }
});
