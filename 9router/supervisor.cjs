#!/usr/bin/env node
/**
 * 9Router supervisor
 * ------------------
 * Starts the 9Router dashboard/gateway at Windows boot, keeps it alive, and
 * serves the legacy `20128 -> 20127` bridge in this same process.
 *
 * Why this exists: the previous stack used two PowerShell loops (a "supervisor"
 * and a "watchdog") that queried WMI every 3-15s. They cost ~170 MB of RAM and
 * constant CPU, only ran at *logon* (not boot), and died on logoff. This file is
 * one small Node process with no polling hot loop:
 *
 *   - child spawn / exit events drive restarts (no busy waiting)
 *   - one 60s health timer detects hang/deadlock
 *   - the 20128 bridge is event-driven HTTP, no extra process
 *
 * Total steady state: 2 processes (this + the Next server), ~0% idle CPU.
 *
 * Runs under a Scheduled Task registered with LogonType S4U (no stored password,
 * starts at startup before logon). Because S4U does not load the user's shell
 * profile, every user-scoped path the app needs (APPDATA, USERPROFILE, DATA_DIR,
 * TMP, NODE_PATH) is set explicitly below rather than inherited.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const http = require("http");
const net = require("net");
const { spawn } = require("child_process");

const ROOT = __dirname;
const LOG_DIR = path.join(ROOT, "logs");
const SUP_LOG = path.join(LOG_DIR, "supervisor.log");
const SERVER_LOG = path.join(LOG_DIR, "server.log");
// Overridable for isolated testing (a second instance must not fight the live
// one for the config or the single-instance lock).
const CONFIG_PATH = process.env.NINEROUTER_CONFIG
  ? path.resolve(process.env.NINEROUTER_CONFIG)
  : path.join(ROOT, "config.json");
const LOCK_FILE = process.env.NINEROUTER_LOCK
  ? path.resolve(process.env.NINEROUTER_LOCK)
  : path.join(ROOT, "supervisor.lock");
// A stop flag the user's `9r stop` writes. Because the S4U task cannot be
// disabled by a non-elevated shell ("Access is denied"), the supervisor itself
// honors this flag and exits immediately, so the minute-by-minute watchdog
// respawns a no-op instead of reviving the stack. `9r start` removes it.
const STOP_FLAG = process.env.NINEROUTER_STOP_FLAG
  ? path.resolve(process.env.NINEROUTER_STOP_FLAG)
  : path.join(ROOT, "stopped.flag");

// ---------------------------------------------------------------- config ----

function readConfig() {
  const profile = process.env.USERPROFILE || path.join("C:\\Users", process.env.USERNAME || "advdi");
  const defaults = {
    profile,
    appDir: path.join(process.env.APPDATA || path.join(profile, "AppData", "Roaming"), "npm", "node_modules", "9router", "app"),
    nodePath: process.execPath,
    port: 20127,
    bridgePort: 20128,
    host: "0.0.0.0",
    maxOldSpaceMb: 1024,
    healthIntervalMs: 60000,
    healthTimeoutMs: 5000,
    maxHealthFailures: 3,
    logMaxBytes: 5 * 1024 * 1024
  };
  try {
    return { ...defaults, ...JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8")) };
  } catch {
    return defaults;
  }
}

const cfg = readConfig();

function dataDir() {
  // Windows default for the app is %APPDATA%\9router (src/lib/dataDir.js).
  return path.join(cfg.profile, "AppData", "Roaming", "9router");
}

// ------------------------------------------------------------------ logs ----

try {
  fs.mkdirSync(LOG_DIR, { recursive: true });
} catch {
  /* ignore */
}

function rotateIfNeeded(file) {
  try {
    if (fs.statSync(file).size > cfg.logMaxBytes) fs.renameSync(file, `${file}.1`);
  } catch {
    /* no file yet */
  }
}

let supStream = null;
function log(message) {
  const line = `${new Date().toISOString()} ${message}\n`;
  try {
    if (!supStream) {
      rotateIfNeeded(SUP_LOG);
      supStream = fs.createWriteStream(SUP_LOG, { flags: "a" });
      supStream.on("error", () => {});
    }
    supStream.write(line);
  } catch {
    /* never die because logging failed */
  }
  try {
    process.stdout.write(line);
  } catch {
    /* detached task may have no usable stdout */
  }
}

let serverStream = null;
function serverLog() {
  if (!serverStream) {
    rotateIfNeeded(SERVER_LOG);
    serverStream = fs.createWriteStream(SERVER_LOG, { flags: "a" });
    serverStream.on("error", () => {});
  }
  return serverStream;
}

// ------------------------------------------------------------------ util ----

function isAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return err.code === "EPERM";
  }
}

/** Single-instance guard: a stale lock from a crashed process is taken over. */
function acquireLock() {
  try {
    const pid = parseInt(fs.readFileSync(LOCK_FILE, "utf8").trim(), 10);
    if (Number.isFinite(pid) && pid > 0 && pid !== process.pid && isAlive(pid)) {
      log(`another supervisor is already running (pid ${pid}) — exiting`);
      return false;
    }
  } catch {
    /* no lock file */
  }
  try {
    fs.writeFileSync(LOCK_FILE, String(process.pid));
  } catch {
    /* ignore */
  }
  return true;
}

function releaseLock() {
  try {
    const pid = parseInt(fs.readFileSync(LOCK_FILE, "utf8").trim(), 10);
    if (pid === process.pid) fs.unlinkSync(LOCK_FILE);
  } catch {
    /* ignore */
  }
}

function portInUse(port) {
  return new Promise((resolve) => {
    const socket = net.connect({ port, host: "127.0.0.1" });
    let settled = false;
    const done = (value) => {
      if (settled) return;
      settled = true;
      try {
        socket.destroy();
      } catch {
        /* ignore */
      }
      resolve(value);
    };
    socket.setTimeout(1500);
    socket.once("connect", () => done(true));
    socket.once("timeout", () => done(false));
    socket.once("error", () => done(false));
  });
}

function probeHealth() {
  return new Promise((resolve) => {
    let settled = false;
    const done = (value) => {
      if (!settled) {
        settled = true;
        resolve(value);
      }
    };
    const req = http.get(
      { host: "127.0.0.1", port: cfg.port, path: "/api/health", timeout: cfg.healthTimeoutMs },
      (res) => {
        let body = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => {
          if (body.length < 4096) body += chunk;
        });
        res.on("end", () => done(res.statusCode === 200 && /"ok"\s*:\s*true/.test(body)));
        res.on("error", () => done(false));
      }
    );
    req.on("timeout", () => {
      req.destroy();
      done(false);
    });
    req.on("error", () => done(false));
  });
}

// --------------------------------------------------------------- process ----

let child = null;
let childStartedAt = 0;
let attempts = 0;
let healthFails = 0;
let restartTimer = null;
let stopping = false;
let adopted = false;

function childEnv() {
  const profile = cfg.profile;
  const appdata = path.join(profile, "AppData", "Roaming");
  const localappdata = path.join(profile, "AppData", "Local");
  const home = dataDir();
  const drive = path.parse(profile).root.replace(/[\\/]+$/, "");
  const env = {
    ...process.env,
    PORT: String(cfg.port),
    HOSTNAME: cfg.host,
    NODE_ENV: "production",
    NEXT_TELEMETRY_DISABLED: "1",
    DATA_DIR: home,
    USERPROFILE: profile,
    HOMEDRIVE: drive,
    HOMEPATH: profile.slice(drive.length) || "\\",
    APPDATA: appdata,
    LOCALAPPDATA: localappdata,
    TEMP: path.join(localappdata, "Temp"),
    TMP: path.join(localappdata, "Temp"),
    NODE_PATH: [path.join(home, "runtime", "node_modules"), path.join(cfg.appDir, "node_modules"), process.env.NODE_PATH]
      .filter(Boolean)
      .join(path.delimiter)
  };
  return env;
}

function serverScript() {
  const custom = path.join(cfg.appDir, "custom-server.js");
  if (fs.existsSync(custom)) return custom;
  return path.join(cfg.appDir, "server.js");
}

function startChild() {
  const script = serverScript();
  if (!fs.existsSync(script)) {
    log(`FATAL: server entry not found: ${script} — is 9router installed? (npm i -g 9router)`);
    return;
  }
  if (!fs.existsSync(cfg.nodePath)) {
    log(`FATAL: node not found at ${cfg.nodePath}`);
    return;
  }

  const args = ["--dns-result-order=ipv4first", `--max-old-space-size=${cfg.maxOldSpaceMb}`, script];
  log(`starting server (port ${cfg.port}, pid will follow): ${cfg.nodePath} ${args.join(" ")}`);

  let proc;
  try {
    proc = spawn(cfg.nodePath, args, {
      cwd: cfg.appDir,
      env: childEnv(),
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"]
    });
  } catch (err) {
    log(`spawn failed: ${err.message}`);
    return;
  }

  child = proc;
  childStartedAt = Date.now();
  healthFails = 0;
  adopted = false;
  log(`server pid ${proc.pid}`);

  const out = serverLog();
  proc.stdout.on("data", (chunk) => {
    try {
      out.write(chunk);
    } catch {
      /* ignore */
    }
  });
  proc.stderr.on("data", (chunk) => {
    try {
      out.write(chunk);
    } catch {
      /* ignore */
    }
  });

  proc.on("error", (err) => log(`server error: ${err.message}`));

  proc.on("exit", (code, signal) => {
    const uptime = Date.now() - childStartedAt;
    log(`server exited (code=${code} signal=${signal}) after ${Math.round(uptime / 1000)}s`);
    if (child === proc) child = null;
    if (stopping) return;

    // A server that stayed up for 2+ minutes counts as healthy: reset backoff.
    attempts = uptime > 120000 ? 0 : attempts + 1;
    const delay = Math.min(30000, 1000 * Math.pow(2, Math.min(attempts, 5)));
    log(`restarting in ${delay}ms (attempt ${attempts})`);

    if (restartTimer) clearTimeout(restartTimer);
    restartTimer = setTimeout(() => {
      restartTimer = null;
      ensureRunning();
    }, delay);
  });
}

async function ensureRunning() {
  if (stopping) return;
  if (child && child.exitCode === null) return;

  if (await portInUse(cfg.port)) {
    if (!adopted) {
      log(`port ${cfg.port} is already served by another process — monitoring it instead of spawning a second server`);
      adopted = true;
    }
    return;
  }
  startChild();
}

async function healthTick() {
  if (stopping) return;

  if (!child || child.exitCode !== null) {
    // Nothing of ours is running: adopt or (re)start.
    if (!(await portInUse(cfg.port))) {
      healthFails = 0;
      await ensureRunning();
    }
  }

  const ok = await probeHealth();
  if (ok) {
    if (healthFails > 0) log("health probe recovered");
    healthFails = 0;
    return;
  }

  healthFails += 1;
  log(`health probe failed (${healthFails}/${cfg.maxHealthFailures})`);

  if (healthFails < cfg.maxHealthFailures) return;
  healthFails = 0;

  if (child && child.exitCode === null) {
    log("server unresponsive — recycling it");
    try {
      child.kill("SIGKILL");
    } catch (err) {
      log(`kill failed: ${err.message}`);
    }
  } else {
    log("external 9router instance is unresponsive — leaving it alone (not our child)");
  }
}

// ---------------------------------------------------------------- bridge ----

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "host"
]);
// Client-supplied forwarding headers are dropped: custom-server.js trusts
// forwarding headers only from a loopback peer, so passing them through would
// let a local client spoof its own source IP (rate-limit / logging bypass).
const SPOOFABLE = new Set(["x-forwarded-for", "x-real-ip"]);

const proxyAgent = new http.Agent({ keepAlive: true, maxSockets: 256 });

function forwardedHeaders(req) {
  const headers = {};
  for (const [name, value] of Object.entries(req.headers)) {
    const key = name.toLowerCase();
    if (HOP_BY_HOP.has(key)) continue;
    if (SPOOFABLE.has(key)) continue;
    if (key === "x-9r-real-ip" || key === "x-9r-via-proxy" || key === "x-9r-peer-token") continue;
    headers[key] = value;
  }
  headers.host = `localhost:${cfg.port}`;
  return headers;
}

function bridgeRequest(req, res) {
  const proxyReq = http.request(
    {
      host: "127.0.0.1",
      port: cfg.port,
      method: req.method,
      path: req.url,
      headers: forwardedHeaders(req),
      agent: proxyAgent
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
      proxyRes.on("error", () => {
        try {
          res.destroy();
        } catch {
          /* ignore */
        }
      });
    }
  );

  proxyReq.on("error", () => {
    if (res.headersSent) {
      try {
        res.destroy();
      } catch {
        /* ignore */
      }
      return;
    }
    res.writeHead(502, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(`502 Bad Gateway: 9Router is not answering on port ${cfg.port}\n`);
  });

  req.on("aborted", () => {
    try {
      proxyReq.destroy();
    } catch {
      /* ignore */
    }
  });
  req.pipe(proxyReq);
}

function bridgeUpgrade(req, socket, head) {
  const upstream = net.connect(cfg.port, "127.0.0.1", () => {
    let raw = `${req.method} ${req.url} HTTP/1.1\r\n`;
    for (const [name, value] of Object.entries(forwardedHeaders(req))) raw += `${name}: ${value}\r\n`;
    raw += "\r\n";
    upstream.write(raw);
    if (head && head.length) upstream.write(head);
    upstream.pipe(socket);
    socket.pipe(upstream);
  });
  upstream.on("error", () => {
    try {
      socket.destroy();
    } catch {
      /* ignore */
    }
  });
  socket.on("error", () => {
    try {
      upstream.destroy();
    } catch {
      /* ignore */
    }
  });
  socket.on("close", () => {
    try {
      upstream.destroy();
    } catch {
      /* ignore */
    }
  });
}

function startBridge() {
  const bridge = http.createServer(bridgeRequest);
  bridge.on("upgrade", bridgeUpgrade);
  bridge.on("clientError", (err, socket) => {
    try {
      socket.destroy();
    } catch {
      /* ignore */
    }
  });
  bridge.on("error", (err) => {
    log(`bridge cannot listen on ${cfg.host}:${cfg.bridgePort} (${err.code || err.message}) — 20128 will not be proxied`);
  });
  bridge.listen(cfg.bridgePort, cfg.host, () => {
    log(`bridge listening on ${cfg.host}:${cfg.bridgePort} -> 127.0.0.1:${cfg.port}`);
  });
  return bridge;
}

// --------------------------------------------------------------- control ----
// A loopback-only control channel. Stopping the stack cannot rely on killing
// processes: when the task runs as S4U the processes live in session 0, and a
// normal shell gets "Access is denied" from Stop-Process while `schtasks /End`
// reports success without tearing down the job tree. So the supervisor is asked
// to shut itself down over 127.0.0.1 instead — same user, no elevation needed.
const CONTROL_PORT = 20129;

function startControl() {
  const control = http.createServer((req, res) => {
    const url = new URL(req.url, "http://127.0.0.1");
    if (req.method === "GET" && url.pathname === "/ping") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          pid: process.pid,
          child: child && child.exitCode === null ? child.pid : null,
          uptimeSec: childStartedAt ? Math.round((Date.now() - childStartedAt) / 1000) : 0,
          healthFails,
          port: cfg.port
        })
      );
      return;
    }
    if (req.method === "POST" && url.pathname === "/stop") {
      const code = Number.parseInt(url.searchParams.get("code") || "0", 10);
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: true, stopping: true }));
      // Answer first, then stop, so the caller sees a clean response.
      setTimeout(() => shutdown(`control stop (exit ${code})`, Number.isFinite(code) ? code : 0), 50);
      return;
    }
    res.writeHead(404, { "Content-Type": "text/plain" });
    res.end("not found\n");
  });
  control.on("error", (err) => log(`control channel unavailable on 127.0.0.1:${CONTROL_PORT} (${err.code || err.message})`));
  control.listen(CONTROL_PORT, "127.0.0.1", () => log(`control channel on 127.0.0.1:${CONTROL_PORT}`));
  return control;
}

// --------------------------------------------------------------- startup ----

function shutdown(reason, exitCode) {
  if (stopping) return;
  stopping = true;
  log(`shutting down (${reason})`);
  if (restartTimer) clearTimeout(restartTimer);
  releaseLock();

  const finish = () => process.exit(Number.isFinite(exitCode) ? exitCode : 0);
  if (child && child.exitCode === null) {
    try {
      child.kill();
    } catch {
      /* ignore */
    }
    setTimeout(() => {
      try {
        if (child && child.exitCode === null) child.kill("SIGKILL");
      } catch {
        /* ignore */
      }
      finish();
    }, 1500);
  } else {
    finish();
  }
}

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
process.on("uncaughtException", (err) => log(`uncaughtException: ${(err && err.stack) || err}`));
process.on("unhandledRejection", (err) => log(`unhandledRejection: ${(err && err.stack) || err}`));
process.on("exit", releaseLock);

if (fs.existsSync(STOP_FLAG)) {
  log(`stop flag present (${STOP_FLAG}) — staying stopped; run '9r start' to clear it`);
  process.exit(0);
}

if (!acquireLock()) process.exit(0);

log(`supervisor pid ${process.pid} starting (node ${process.version})`);
log(`profile=${cfg.profile} appDir=${cfg.appDir} dataDir=${dataDir()}`);

startBridge();
startControl();
ensureRunning();
setInterval(() => {
  healthTick().catch((err) => log(`health tick error: ${err && err.message ? err.message : err}`));
}, cfg.healthIntervalMs);
