# 9Router keep-alive stack

Everything here keeps 9Router (the local AI gateway + dashboard) running with as
little overhead as possible.

- Gateway / dashboard / API : `http://localhost:20127` (native, what the app binds)
- Bridge for the legacy port: `http://localhost:20128` → `127.0.0.1:20127`
  (Cline, Continue and older configs point at 20128; it is proxied in-process,
  no extra program)
- Data (accounts, connections, usage): `%APPDATA%\9router\`
- Logs: `C:\tools\9router\logs\supervisor.log`, `server.log` (rotated at 5 MB)

## What runs

| Process | Role | Typical cost |
|---|---|---|
| `wscript.exe` | invisible launcher started by the scheduled task; waits on node | ~3 MB, 0% CPU |
| `node supervisor.cjs` | spawns the server, restarts it on crash/hang, serves the 20128 bridge | ~40 MB, ~0% CPU |
| `node custom-server.js` | the actual 9Router Next server | ~110-160 MB, ~0.2% CPU idle |

No PowerShell polling loops, no WMI queries, no `curl` health pings every few
seconds. Health is checked once a minute with a single HTTP request, and only
restarts after 3 consecutive failures (a hang, not a hiccup).

## How it starts

Registered as the scheduled task **9Router** (`C:\tools\9router\install-task.ps1`).

- **Now (not elevated):** hidden at logon, plus a 1-minute repetition watchdog
  that restarts the supervisor if it ever dies. Windows refuses
  "run whether logged on or not" tasks for non-admin users, so it does **not**
  start before you log in yet.
- **After one elevated run:** the task gains an `AtStartup` trigger with an S4U
  principal, so it is up at boot, before anyone logs in, with no stored password.

Upgrade to boot-start (one UAC prompt):

```
Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\tools\9router\install-task.ps1'
```

or run `C:\tools\bin\start-9router-admin.cmd`.

## Commands

```
9r status      task state, PIDs, RAM, health of both ports
9r start       enable the task and start now (never duplicates an instance)
9r stop        disable the task, then stop everything (stays stopped)
9r restart     stop + start
9r update      npm i -g 9router@latest, then restart through the task
```

`9r stop` **disables** the task on purpose: the repetition watchdog would
otherwise bring the stack back within a minute.

## Files

- `config.json` — profile, app dir, node path, ports, heap cap, health settings.
  Edit and re-run `9r restart` after changing ports.
- `supervisor.cjs` — the supervisor. Sets `PORT`, `HOSTNAME`, `DATA_DIR`,
  `APPDATA`, `USERPROFILE`, `TMP` and `NODE_PATH` explicitly, because the task
  can run without a fully loaded shell profile; if those were inherited wrong,
  the app would create an empty database and look like all accounts vanished.
- `install-task.ps1` — idempotent task registration (elevation-aware).
- `9r-ctl.ps1` — start/stop/status logic behind the `9r` commands.
- `launch-supervisor.vbs` — generated; hides the console window and forwards the
  exit code. Must keep CRLF line endings (Windows Script Host requirement).
- `register-boot-task.cmd` — elevated wrapper for `install-task.ps1`.
- `legacy/` — the previous PowerShell supervisor + watchdog and the old Startup
  shortcut, kept for reference. Nothing runs from here.

## Troubleshooting

- **Nothing listening:** `9r status`, then read `logs\supervisor.log`. Check
  `logs\server.log` for a Next start-up error.
- **"another supervisor is already running":** delete `supervisor.lock` if no
  `node supervisor.cjs` process exists.
- **Port already in use:** if something else owns 20127 (for example `9r dev`,
  which runs the repo dev server), the supervisor adopts it instead of spawning a
  second server and leaves it alone. Run `9r stop` before `9r dev`.
- **Boot without logging in:** see "Upgrade to boot-start" above.

## Rollback to the old setup

The old files are in `legacy/`. To go back completely:

```
schtasks /Delete /TN 9Router /F
Copy-Item C:\tools\9router\legacy\startup-9router.vbs "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\9router.vbs"
Copy-Item C:\tools\9router\legacy\* C:\tools\scripts\ -Exclude startup-9router.vbs
```

That restores the previous logon shortcut and the PowerShell supervisor/watchdog.
