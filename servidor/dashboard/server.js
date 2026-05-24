// dashboard/server.js
// Express API que recibe eventos de los agentes y sirve el frontend.

const express = require("express");
const http    = require("http");
const { Server } = require("socket.io");
const cors    = require("cors");
const fs      = require("fs");
const path    = require("path");

const app    = express();
const server = http.createServer(app);
const io     = new Server(server, { cors: { origin: "*" } });

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

// ── Almacén en memoria ────────────────────────────────────────
const store = {
  events:   [],   // todos los eventos
  backups:  [],   // solo backups
  failovers:[],   // solo failovers
  currentDb: "primary",
  containers: {},
};

const LOG_PATH = "/app/logs/dashboard.log";
fs.mkdirSync("/app/logs", { recursive: true });

function appendLog(msg) {
  const line = `${new Date().toISOString()} ${msg}\n`;
  fs.appendFileSync(LOG_PATH, line);
}

// ── Recibir eventos de agentes ────────────────────────────────
app.post("/api/event", (req, res) => {
  const event = { ...req.body, receivedAt: new Date().toISOString() };
  store.events.unshift(event);
  if (store.events.length > 500) store.events.pop();

  // Clasificar
  switch (event.type) {
    case "backup_done":
    case "backup_start":
    case "backup_error":
      store.backups.unshift(event);
      if (store.backups.length > 200) store.backups.pop();
      appendLog(`[BACKUP] ${JSON.stringify(event)}`);
      break;

    case "failover":
      store.failovers.unshift(event);
      if (event.direction === "primary→mirror") {
        store.currentDb = "mirror";
      } else {
        store.currentDb = "primary";
      }
      appendLog(`[FAILOVER] ${JSON.stringify(event)}`);
      break;

    case "container_status":
      store.containers[event.name] = event;
      appendLog(`[CONTAINER] ${JSON.stringify(event)}`);
      break;

    case "agent_start":
      appendLog(`[AGENT] failover-agent iniciado`);
      break;
  }

  // Emitir a todos los clientes WebSocket
  io.emit("event", event);
  io.emit("state", getState());

  res.json({ ok: true });
});

// ── Estado actual ─────────────────────────────────────────────
function getState() {
  return {
    currentDb:  store.currentDb,
    containers: store.containers,
    lastBackups: store.backups.slice(0, 20),
    lastFailovers: store.failovers.slice(0, 20),
    lastEvents:  store.events.slice(0, 50),
  };
}

app.get("/api/state", (req, res) => res.json(getState()));

// ── WebSocket ────────────────────────────────────────────────
io.on("connection", (socket) => {
  socket.emit("state", getState());
});

// ── Arrancar ─────────────────────────────────────────────────
const API_PORT = process.env.API_PORT || 3001;
server.listen(API_PORT, () =>
  console.log(`Dashboard API + WS corriendo en :${API_PORT}`)
);
