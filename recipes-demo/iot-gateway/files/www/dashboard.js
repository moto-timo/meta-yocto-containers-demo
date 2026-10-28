// IoT gateway dashboard. Not inline, so the CSP can forbid inline scripts.
"use strict";

/* --- State ------------------------------------------------------------ */
const HISTORY_LEN = 30;
const sensorState = {};          // sensor_id -> {raw, processed, history[], canvas, ctx}
const logEl  = document.getElementById("log");
const gridEl = document.getElementById("sensors");

/* --- MQTT ------------------------------------------------------------- */
const wsHost = location.hostname || "localhost";
const wsPort = 9001;
// Over HTTPS (mqtt-auth), use the web server's /mqtt proxy.
const url    = location.protocol === "https:"
  ? `wss://${location.host}/mqtt`
  : `ws://${wsHost}:${wsPort}/mqtt`;

log("Connecting to MQTT broker at " + url);

const client = mqtt.connect(url, {
  reconnectPeriod: 2000,
  connectTimeout: 5000,
});

client.on("connect", () => {
  setStatus("ok", "Connected");
  log("MQTT connected");
  client.subscribe(["sensors/raw/#", "sensors/processed/#", "sensors/status"]);
});
client.on("reconnect", () => setStatus("wait", "Reconnecting"));
client.on("offline",   () => setStatus("err",  "Offline"));
client.on("error", (e) => { setStatus("err", "Error"); log("Error: " + e.message); });

client.on("message", (topic, payload) => {
  try {
    const data = JSON.parse(payload.toString());
    const parts = topic.split("/");

    if (parts[1] === "raw" && parts[2]) {
      handleRaw(parts[2], data);
    } else if (parts[1] === "processed" && parts[2]) {
      handleProcessed(parts[2], data);
    } else if (parts[1] === "status") {
      log(`Heartbeat: uptime=${data.uptime_ticks} sensors=[${data.sensors}]`);
    }
  } catch (_) { /* ignore malformed */ }
});

/* --- Handlers --------------------------------------------------------- */
function ensureSensor(id, data) {
  if (sensorState[id]) return sensorState[id];

  const card = document.createElement("div");
  card.className = "card";
  card.id = "card-" + id;
  card.innerHTML = `
    <h2>${data.type || id} <span style="color:var(--accent)">${id}</span></h2>
    <div><span class="value" id="val-${id}">--</span><span class="unit">${data.unit || ""}</span></div>
    <div class="stats">
      <span><span class="label">Mean</span><span class="num" id="mean-${id}">--</span></span>
      <span><span class="label">Min</span><span class="num" id="min-${id}">--</span></span>
      <span><span class="label">Max</span><span class="num" id="max-${id}">--</span></span>
      <span><span class="label">Samples</span><span class="num" id="cnt-${id}">0</span></span>
    </div>
    <canvas id="chart-${id}" height="100"></canvas>`;
  gridEl.appendChild(card);

  const canvas = card.querySelector("canvas");
  const ctx = canvas.getContext("2d");
  sensorState[id] = { history: [], canvas, ctx, type: data.type, unit: data.unit };
  return sensorState[id];
}

function handleRaw(id, data) {
  const s = ensureSensor(id, data);
  document.getElementById("val-" + id).textContent = data.value;
  s.history.push(data.value);
  if (s.history.length > HISTORY_LEN) s.history.shift();
  drawChart(s);
}

function handleProcessed(id, data) {
  ensureSensor(id, data);
  const st = data.stats || {};
  const el = (x) => document.getElementById(x + "-" + id);
  if (el("mean")) el("mean").textContent = st.mean ?? "--";
  if (el("min"))  el("min").textContent  = st.min  ?? "--";
  if (el("max"))  el("max").textContent  = st.max  ?? "--";
  if (el("cnt"))  el("cnt").textContent  = st.count ?? 0;
}

/* --- Sparkline chart -------------------------------------------------- */
function drawChart(s) {
  const { canvas, ctx, history } = s;
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr; canvas.height = h * dpr;
  ctx.scale(dpr, dpr);

  if (history.length < 2) return;
  const min = Math.min(...history), max = Math.max(...history);
  const range = max - min || 1;
  const step = w / (HISTORY_LEN - 1);

  ctx.clearRect(0, 0, w, h);

  // Gradient fill
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "rgba(56,189,248,0.25)");
  grad.addColorStop(1, "rgba(56,189,248,0)");
  ctx.beginPath();
  ctx.moveTo(0, h);
  history.forEach((v, i) => {
    const x = i * step, y = h - ((v - min) / range) * (h - 4) - 2;
    i === 0 ? ctx.lineTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.lineTo((history.length - 1) * step, h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  history.forEach((v, i) => {
    const x = i * step, y = h - ((v - min) / range) * (h - 4) - 2;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "var(--accent)";
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

/* --- Helpers ---------------------------------------------------------- */
function setStatus(state, label) {
  const el = document.getElementById("conn-status");
  el.innerHTML = `<span class="dot ${state}"></span><span>${label}</span>`;
}

function log(msg) {
  const now = new Date().toLocaleTimeString();
  const line = document.createElement("div");
  line.innerHTML = `<span class="ts">${now}</span> ${msg}`;
  logEl.appendChild(line);
  if (logEl.children.length > 100) logEl.removeChild(logEl.firstChild);
  logEl.scrollTop = logEl.scrollHeight;
}
