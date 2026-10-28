import { createState, step, links, lightLevels } from "./dance.mjs";

const canvas = document.querySelector("#dance");
const ctx = canvas.getContext("2d");
const error = document.querySelector("#error");
const auto = document.querySelector("#auto");
const directionButtons = [...document.querySelectorAll("[data-move]")];
const keyMoves = {
  ArrowLeft: "left", KeyA: "left", ArrowRight: "right", KeyD: "right",
  ArrowUp: "up", KeyW: "up", ArrowDown: "down", KeyS: "down",
};
const keys = new Set();
const pointers = new Map();
let data;
let state;
let previousTime;

function syncControls() {
  const accent = data.palettes[state.palette];
  document.documentElement.style.setProperty("--accent", `rgb(${accent.join(",")})`);
  auto.setAttribute("aria-pressed", String(state.automatic));
}

function reset() {
  state = createState(data);
  keys.clear();
  pointers.clear();
  syncControls();
}

function clearInput() {
  keys.clear();
  pointers.clear();
  directionButtons.forEach(button => button.classList.remove("active"));
}

function draw() {
  const accent = `rgb(${data.palettes[state.palette].join(",")})`;
  ctx.setTransform(2, 0, 0, 2, 0, 0);
  ctx.fillStyle = "#0c0e18";
  ctx.fillRect(0, 0, 320, 240);
  const glow = ctx.createRadialGradient(160, 115, 5, 160, 115, 115);
  glow.addColorStop(0, "#1c2930");
  glow.addColorStop(1, "#0c0e18");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, 320, 240);

  const levels = lightLevels(state, data);
  const positions = {
    top_left: [10, 65], top_right: [310, 65],
    bottom_right: [310, 155], bottom_left: [10, 155],
  };
  ctx.save();
  ctx.shadowColor = "white";
  data.lights.corners.forEach((corner, index) => {
    const [x, y] = positions[corner];
    ctx.fillStyle = `rgba(255,255,255,${0.08 + levels[index]})`;
    ctx.shadowBlur = levels[index] * 30;
    ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
  });
  ctx.restore();

  ctx.lineWidth = 0.5;
  ctx.strokeStyle = "#242e40";
  ctx.beginPath();
  for (let x = -160; x <= 480; x += 40) {
    ctx.moveTo(160 + (x - 160) * 0.3, 174);
    ctx.lineTo(x, 216);
  }
  for (const y of [174, 184, 198, 216]) {
    ctx.moveTo(0, y); ctx.lineTo(320, y);
  }
  ctx.stroke();
  ctx.fillStyle = "#0a1018";
  ctx.beginPath();
  ctx.ellipse(160 + state.pose[2][0], 179, 30, 4, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.save();
  ctx.translate(160, 132);
  ctx.strokeStyle = accent;
  ctx.lineWidth = 3;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.shadowColor = accent;
  ctx.shadowBlur = 12;
  ctx.beginPath();
  for (const [start, end] of links) {
    ctx.moveTo(...state.pose[start]);
    ctx.lineTo(...state.pose[end]);
  }
  ctx.stroke();
  const [hx, hy] = state.pose[0];
  ctx.fillStyle = accent;
  ctx.beginPath(); ctx.arc(hx, hy, 11, 0, Math.PI * 2); ctx.fill();
  ctx.shadowBlur = 0;
  ctx.fillStyle = "#0c0e18";
  for (const x of [-3, 3]) {
    ctx.beginPath(); ctx.arc(hx + x, hy - 2, 1, 0, Math.PI * 2); ctx.fill();
  }
  ctx.strokeStyle = "#0c0e18";
  ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.arc(hx, hy + 2, 4, 0.2, Math.PI - 0.2); ctx.stroke();
  ctx.restore();

  for (let i = 0; i < 8; i++) {
    ctx.fillStyle = i === Math.floor(state.beat * 2) % 8 ? accent : "#303b47";
    ctx.fillRect(132 + i * 8, 201, 4, i === Math.floor(state.beat * 2) % 8 ? 8 : 3);
  }
  document.querySelector("#move").textContent = data.moves[state.move].label;
  document.querySelector("#mode").textContent = state.automatic ? "AUTO GROOVE" : "YOU LEAD";
}

function frame(time) {
  if (document.hidden) {
    previousTime = undefined;
  } else {
    const held = new Set([...keys].map(code => keyMoves[code]).concat([...pointers.values()]));
    step(state, data, previousTime === undefined ? 0 : time - previousTime, held);
    previousTime = time;
    directionButtons.forEach(button => {
      button.classList.toggle("active", held.has(button.dataset.move));
    });
    draw();
  }
  requestAnimationFrame(frame);
}

try {
  const response = await fetch("../assets/dance.json");
  if (!response.ok) throw new Error(`Could not load poses (HTTP ${response.status}).`);
  data = await response.json();
  state = createState(data);
  syncControls();

  auto.addEventListener("click", () => {
    state.automatic = !state.automatic;
    syncControls();
  });
  document.querySelector("#color").addEventListener("click", () => {
    state.palette = (state.palette + 1) % data.palettes.length;
    syncControls();
  });
  document.querySelector("#reset").addEventListener("click", reset);
  window.addEventListener("keydown", event => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (keyMoves[event.code]) {
      event.preventDefault();
      keys.add(event.code);
    } else if (["Space", "KeyC", "KeyR", "Escape"].includes(event.code)) {
      event.preventDefault();
      if (event.repeat) return;
      if (event.code === "Space") auto.click();
      else if (event.code === "KeyC") document.querySelector("#color").click();
      else reset();
    }
  });
  window.addEventListener("keyup", event => keys.delete(event.code));
  window.addEventListener("blur", clearInput);
  document.addEventListener("visibilitychange", clearInput);
  canvas.addEventListener("pointerdown", () => canvas.focus());
  for (const button of directionButtons) {
    button.addEventListener("pointerdown", event => {
      if (event.button !== 0) return;
      event.preventDefault();
      button.setPointerCapture(event.pointerId);
      pointers.set(event.pointerId, button.dataset.move);
    });
    const release = event => pointers.delete(event.pointerId);
    button.addEventListener("pointerup", release);
    button.addEventListener("pointercancel", release);
    button.addEventListener("lostpointercapture", release);
    button.addEventListener("keydown", event => {
      if (event.code === "Enter") {
        event.preventDefault();
        keys.add(`button:${button.dataset.move}`);
        keyMoves[`button:${button.dataset.move}`] = button.dataset.move;
      }
    });
    button.addEventListener("keyup", event => {
      if (event.code === "Enter") keys.delete(`button:${button.dataset.move}`);
    });
    button.addEventListener("blur", () => keys.delete(`button:${button.dataset.move}`));
  }
  requestAnimationFrame(frame);
} catch (failure) {
  error.textContent = `The dance floor could not start: ${failure.message} Serve this folder with the Python command in README.md, then reload.`;
  error.hidden = false;
  document.querySelectorAll("button").forEach(button => { button.disabled = true; });
  console.error(failure);
}
