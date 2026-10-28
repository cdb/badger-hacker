export const moves = ["left", "right", "up", "down"];
export const links = [[1, 2], [1, 3], [3, 4], [1, 5], [5, 6],
  [2, 7], [7, 8], [2, 9], [9, 10]];

export function lightBrightness(beat, data) {
  return data.lights.peak * Math.max(0, 1 - (beat % 1) / data.lights.pulse_beats);
}

export function lightLevels(state, data) {
  const brightness = lightBrightness(state.beat, data);
  const active = state.direction ? data.lights.directions[state.direction] : data.lights.corners;
  return data.lights.corners.map(corner => active.includes(corner) ? brightness : 0);
}

export function createState(data) {
  return {
    beat: 0, automatic: false, palette: 0, move: "idle", direction: null,
    pose: data.moves.idle.frames[0].map(point => [...point]),
  };
}

export function step(state, data, elapsed, held) {
  const dt = Math.min(Math.max(elapsed, 0), 50);
  state.beat = (state.beat + dt * data.bpm / 60000) % 16;
  state.direction = moves.find(move => held.has(move)) ?? null;
  state.move = state.direction
    ?? (state.automatic ? moves[Math.floor(state.beat / 4)] : "idle");
  const [first, second] = data.moves[state.move].frames;
  const mix = (1 - Math.cos(state.beat * 2 * Math.PI)) / 2;
  const smoothing = 1 - Math.exp(-dt / 65);
  state.pose.forEach((point, index) => {
    for (let axis = 0; axis < 2; axis++) {
      const target = first[index][axis] * (1 - mix) + second[index][axis] * mix;
      point[axis] += (target - point[axis]) * smoothing;
    }
  });
}
