#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execSync, spawn } from 'node:child_process';
import readline from 'node:readline';

const HOME = process.env.USERPROFILE || os.homedir();
const CODEX_DIR = path.join(HOME, '.codex');
const AUTH_FILE = path.join(CODEX_DIR, 'auth.json');
const SWITCHER_DIR = path.join(HOME, '.codex-switcher');
const ACCOUNTS_FILE = path.join(SWITCHER_DIR, 'accounts.json');
const BACKUPS_DIR = path.join(SWITCHER_DIR, 'backups');
const PROFILES_DIR = path.join(HOME, '.codex-switch', 'profiles');
const CURRENT_FILE = path.join(HOME, '.codex-switch', 'current');
const APPX_PACKAGE = 'OpenAI.Codex_2p2nqsd0c76g0!App';

// ANSI styling
const c = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  green: '\x1b[32m',
  cyan: '\x1b[36m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  magenta: '\x1b[35m',
  blue: '\x1b[34m',
  bgCyan: '\x1b[46m\x1b[30m',
  bgGreen: '\x1b[42m\x1b[30m',
  gray: '\x1b[90m',
};

function parseJwt(token) {
  if (!token || typeof token !== 'string') return {};
  try {
    const parts = token.split('.');
    if (parts.length < 2) return {};
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
    const jsonStr = Buffer.from(padded, 'base64').toString('utf8');
    return JSON.parse(jsonStr);
  } catch {
    return {};
  }
}

function ensureDirs() {
  if (!fs.existsSync(CODEX_DIR)) fs.mkdirSync(CODEX_DIR, { recursive: true });
  if (!fs.existsSync(SWITCHER_DIR)) fs.mkdirSync(SWITCHER_DIR, { recursive: true });
  if (!fs.existsSync(BACKUPS_DIR)) fs.mkdirSync(BACKUPS_DIR, { recursive: true });
  if (!fs.existsSync(PROFILES_DIR)) fs.mkdirSync(PROFILES_DIR, { recursive: true });
}

function getActiveAuth() {
  if (!fs.existsSync(AUTH_FILE)) return null;
  try {
    const content = fs.readFileSync(AUTH_FILE, 'utf8');
    const auth = JSON.parse(content);
    const jwt = parseJwt(auth?.tokens?.id_token);
    return {
      auth,
      accountId: auth?.tokens?.account_id || jwt['https://api.openai.com/auth']?.chatgpt_account_id,
      email: jwt?.email || null,
      name: jwt?.name || null,
      planType: jwt['https://api.openai.com/auth']?.chatgpt_plan_type || 'free',
      exp: jwt?.exp ? new Date(jwt.exp * 1000) : null,
    };
  } catch {
    return null;
  }
}

function loadAccounts() {
  ensureDirs();
  let accountsData = { version: 1, accounts: [] };

  if (fs.existsSync(ACCOUNTS_FILE)) {
    try {
      accountsData = JSON.parse(fs.readFileSync(ACCOUNTS_FILE, 'utf8'));
      if (!Array.isArray(accountsData.accounts)) accountsData.accounts = [];
    } catch {}
  }

  // Also check profiles directory in ~/.codex-switch/profiles for any missing accounts
  if (fs.existsSync(PROFILES_DIR)) {
    try {
      const profileFolders = fs.readdirSync(PROFILES_DIR, { withFileTypes: true });
      for (const dirent of profileFolders) {
        if (!dirent.isDirectory()) continue;
        const profileName = dirent.name;
        const profileAuthPath = path.join(PROFILES_DIR, profileName, 'auth.json');
        if (!fs.existsSync(profileAuthPath)) continue;

        try {
          const profileAuth = JSON.parse(fs.readFileSync(profileAuthPath, 'utf8'));
          const jwt = parseJwt(profileAuth?.tokens?.id_token);
          const email = jwt?.email || `${profileName}@account`;
          const accountId = profileAuth?.tokens?.account_id || jwt['https://api.openai.com/auth']?.chatgpt_account_id;

          // Check if already in accountsData
          const exists = accountsData.accounts.some(
            (a) => (accountId && a.auth_data?.account_id === accountId) || (a.email && a.email.toLowerCase() === email.toLowerCase())
          );

          if (!exists && profileAuth?.tokens) {
            accountsData.accounts.push({
              id: crypto.randomUUID(),
              name: profileName,
              email: email,
              plan_type: jwt['https://api.openai.com/auth']?.chatgpt_plan_type || 'free',
              subscription_expires_at: null,
              auth_mode: 'chat_g_p_t',
              auth_data: {
                type: 'chat_g_p_t',
                id_token: profileAuth.tokens.id_token,
                access_token: profileAuth.tokens.access_token,
                refresh_token: profileAuth.tokens.refresh_token,
                account_id: accountId,
              },
              created_at: new Date().toISOString(),
              last_used_at: new Date().toISOString(),
            });
          }
        } catch {}
      }
    } catch {}
  }

  // Save updated accounts back
  try {
    fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(accountsData, null, 2), 'utf8');
  } catch {}

  return accountsData.accounts;
}

function saveAccounts(accounts) {
  ensureDirs();
  const data = { version: 1, accounts };
  fs.writeFileSync(ACCOUNTS_FILE, JSON.stringify(data, null, 2), 'utf8');
}

function backupActiveAuth() {
  if (!fs.existsSync(AUTH_FILE)) return;
  try {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupFile = path.join(BACKUPS_DIR, `auth_${timestamp}.json`);
    fs.copyFileSync(AUTH_FILE, backupFile);

    // Keep only last 20 backups
    const files = fs.readdirSync(BACKUPS_DIR).filter(f => f.startsWith('auth_')).sort();
    if (files.length > 20) {
      for (const f of files.slice(0, files.length - 20)) {
        try { fs.unlinkSync(path.join(BACKUPS_DIR, f)); } catch {}
      }
    }
  } catch {}
}

function syncActiveTokensBackToStorage() {
  const active = getActiveAuth();
  if (!active || !active.auth || !active.auth.tokens) return;

  const accounts = loadAccounts();
  let updated = false;

  for (const acc of accounts) {
    const matchId = active.accountId && acc.auth_data?.account_id === active.accountId;
    const matchEmail = active.email && acc.email && acc.email.toLowerCase() === active.email.toLowerCase();

    if (matchId || matchEmail) {
      acc.auth_data = {
        type: 'chat_g_p_t',
        id_token: active.auth.tokens.id_token,
        access_token: active.auth.tokens.access_token,
        refresh_token: active.auth.tokens.refresh_token,
        account_id: active.auth.tokens.account_id || acc.auth_data?.account_id,
      };
      acc.last_used_at = new Date().toISOString();
      if (active.planType) acc.plan_type = active.planType;
      updated = true;

      // Also sync to ~/.codex-switch/profiles/<name>/auth.json
      const profileFolder = path.join(PROFILES_DIR, acc.name || acc.email.split('@')[0]);
      if (fs.existsSync(profileFolder)) {
        try {
          fs.writeFileSync(path.join(profileFolder, 'auth.json'), JSON.stringify(active.auth, null, 2), 'utf8');
        } catch {}
      }
      break;
    }
  }

  if (updated) {
    saveAccounts(accounts);
  }
}

function isAppRunning() {
  try {
    const out = execSync('powershell -NoProfile -Command "Get-Process -Name ChatGPT, codex -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName -Unique"', {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
    return out.length > 0;
  } catch {
    return false;
  }
}

function restartApp() {
  console.log(`${c.yellow}↻ Restarting ChatGPT Codex app & background daemon...${c.reset}`);
  try {
    execSync('powershell -NoProfile -Command "Stop-Process -Name ChatGPT, codex -Force -ErrorAction SilentlyContinue"', {
      stdio: ['ignore', 'ignore', 'ignore'],
    });
  } catch {}

  // Wait a moment for processes to exit cleanly
  try {
    execSync('powershell -NoProfile -Command "Start-Sleep -Milliseconds 600"', {
      stdio: ['ignore', 'ignore', 'ignore'],
    });
  } catch {}

  // Launch ChatGPT app again
  try {
    spawn('powershell', ['-NoProfile', '-Command', `Start-Process "shell:AppsFolder\\${APPX_PACKAGE}"`], {
      detached: true,
      stdio: 'ignore',
    }).unref();
    console.log(`${c.green}✔ ChatGPT Codex app launched successfully.${c.reset}`);
  } catch (err) {
    console.log(`${c.yellow}⚠️ Could not automatically launch app: ${err.message}${c.reset}`);
  }
}

function switchAccount(targetAccount, options = {}) {
  ensureDirs();
  backupActiveAuth();
  syncActiveTokensBackToStorage();

  const authPayload = {
    auth_mode: 'chatgpt',
    OPENAI_API_KEY: null,
    tokens: {
      access_token: targetAccount.auth_data.access_token,
      account_id: targetAccount.auth_data.account_id,
      id_token: targetAccount.auth_data.id_token,
      refresh_token: targetAccount.auth_data.refresh_token,
    },
  };

  fs.writeFileSync(AUTH_FILE, JSON.stringify(authPayload, null, 2), 'utf8');

  // Update last_used_at in accounts.json
  const accounts = loadAccounts();
  const found = accounts.find((a) => a.id === targetAccount.id || a.email === targetAccount.email);
  if (found) {
    found.last_used_at = new Date().toISOString();
    saveAccounts(accounts);
  }

  // Update ~/.codex-switch/current
  try {
    const profileName = targetAccount.name || targetAccount.email.split('@')[0];
    fs.writeFileSync(CURRENT_FILE, profileName, 'utf8');
  } catch {}

  console.log(`\n${c.green}${c.bold}✔ Successfully switched account!${c.reset}`);
  console.log(`${c.cyan}  Account :${c.reset} ${c.bold}${targetAccount.name || 'Unnamed'}${c.reset}`);
  console.log(`${c.cyan}  Email   :${c.reset} ${targetAccount.email}`);
  console.log(`${c.cyan}  Plan    :${c.reset} ${(targetAccount.plan_type || 'free').toUpperCase()}`);

  const running = isAppRunning();
  if (running) {
    if (options.restart === true) {
      restartApp();
    } else if (options.restart === false) {
      console.log(`\n${c.yellow}ℹ ChatGPT Codex app is currently running. Please restart it to apply changes.${c.reset}`);
    } else {
      promptRestart();
    }
  } else {
    console.log(`\n${c.dim}Next time you launch ChatGPT Codex app or run 'codex', it will use this account.${c.reset}`);
  }
}

function promptRestart() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  rl.question(`\n${c.yellow}? ChatGPT Codex app is currently running. Restart it now? [Y/n]: ${c.reset}`, (answer) => {
    rl.close();
    const clean = answer.trim().toLowerCase();
    if (clean === '' || clean === 'y' || clean === 'yes') {
      restartApp();
    } else {
      console.log(`${c.gray}Restart skipped. Relaunch ChatGPT Codex app whenever you are ready.${c.reset}`);
    }
  });
}

function printStatus() {
  const active = getActiveAuth();
  console.log(`\n${c.bold}=== ChatGPT Codex App: Active Account ===${c.reset}`);
  if (!active) {
    console.log(`${c.yellow}No active session found in ${AUTH_FILE}.${c.reset}`);
    return;
  }

  console.log(`${c.cyan}Name      :${c.reset} ${active.name || 'N/A'}`);
  console.log(`${c.cyan}Email     :${c.reset} ${c.bold}${active.email || 'N/A'}${c.reset}`);
  console.log(`${c.cyan}Plan      :${c.reset} ${c.green}${active.planType.toUpperCase()}${c.reset}`);
  console.log(`${c.cyan}Account ID:${c.reset} ${active.accountId || 'N/A'}`);
  if (active.exp) {
    console.log(`${c.cyan}Token Exp :${c.reset} ${active.exp.toLocaleString()}`);
  }
  const running = isAppRunning();
  console.log(`${c.cyan}App State :${c.reset} ${running ? `${c.green}● Running${c.reset}` : `${c.gray}○ Closed${c.reset}`}`);
}

function printList() {
  const accounts = loadAccounts();
  const active = getActiveAuth();

  console.log(`\n${c.bold}Available Codex Accounts (${accounts.length}):${c.reset}\n`);
  if (accounts.length === 0) {
    console.log(`${c.yellow}No saved accounts found.${c.reset}`);
    console.log(`Run ${c.cyan}codex-switch save <name>${c.reset} to save the current session.\n`);
    return;
  }

  accounts.forEach((acc, i) => {
    const isActive =
      (active?.accountId && acc.auth_data?.account_id === active.accountId) ||
      (active?.email && acc.email && acc.email.toLowerCase() === active.email.toLowerCase());

    const num = `${c.bold}[${i + 1}]${c.reset}`;
    const status = isActive ? `${c.green}${c.bold}✔ ACTIVE${c.reset}` : `        `;
    const plan = `[${(acc.plan_type || 'free').toUpperCase()}]`.padEnd(8);
    const planColor = acc.plan_type === 'go' || acc.plan_type === 'pro' ? c.magenta : c.dim;

    console.log(`  ${num} ${status} ${c.bold}${acc.name || 'Unnamed'}${c.reset.padEnd(20 - (acc.name?.length || 0))} ${c.cyan}${acc.email.padEnd(28)}${c.reset} ${planColor}${plan}${c.reset}`);
  });
  console.log('');
}

function runInteractive() {
  const accounts = loadAccounts();
  const active = getActiveAuth();

  if (accounts.length === 0) {
    console.log(`\n${c.yellow}No accounts available in storage.${c.reset}`);
    console.log(`To save the currently logged-in account, run:`);
    console.log(`  ${c.cyan}codex-switch save <your-account-name>${c.reset}\n`);
    process.exit(0);
  }

  // Find initial selection (active account or index 0)
  let selectedIndex = 0;
  accounts.forEach((acc, i) => {
    const isActive =
      (active?.accountId && acc.auth_data?.account_id === active.accountId) ||
      (active?.email && acc.email && acc.email.toLowerCase() === active.email.toLowerCase());
    if (isActive) selectedIndex = i;
  });

  const stdin = process.stdin;
  if (!stdin.isTTY) {
    // Fallback to table print and exit if non-TTY
    printList();
    return;
  }

  readline.emitKeypressEvents(stdin);
  stdin.setRawMode(true);
  stdin.resume();

  // Hide cursor
  process.stdout.write('\x1b[?25l');

  function render(initial = false) {
    if (!initial) {
      readline.cursorTo(process.stdout, 0, 0);
      readline.clearScreenDown(process.stdout);
    }

    console.log(`\n${c.cyan}${c.bold}╭─────────────────────────────────────────────────────────────╮${c.reset}`);
    console.log(`${c.cyan}${c.bold}│                 ChatGPT Codex Account Switcher              │${c.reset}`);
    console.log(`${c.cyan}${c.bold}╰─────────────────────────────────────────────────────────────╯${c.reset}`);
    console.log(`${c.gray}Use ↑/↓ or j/k to navigate, [Enter] to switch, [1-${accounts.length}] quick-select, [q] to exit.${c.reset}\n`);

    accounts.forEach((acc, i) => {
      const isSelected = i === selectedIndex;
      const isActive =
        (active?.accountId && acc.auth_data?.account_id === active.accountId) ||
        (active?.email && acc.email && acc.email.toLowerCase() === active.email.toLowerCase());

      const pointer = isSelected ? `${c.cyan}${c.bold}❯${c.reset}` : ' ';
      const num = `${c.bold}[${i + 1}]${c.reset}`;
      const activeTag = isActive ? `${c.green}${c.bold}✔ ACTIVE${c.reset}` : '        ';
      const name = isSelected ? `${c.bgCyan} ${acc.name || 'Unnamed'} ${c.reset}` : `${c.bold}${acc.name || 'Unnamed'}${c.reset}`;
      const email = `${c.cyan}${acc.email}${c.reset}`;
      const plan = `[${(acc.plan_type || 'free').toUpperCase()}]`;
      const planColored = acc.plan_type === 'go' || acc.plan_type === 'pro' ? `${c.magenta}${plan}${c.reset}` : `${c.dim}${plan}${c.reset}`;

      console.log(` ${pointer} ${num} ${activeTag} ${name.padEnd(isSelected ? 30 : 20)} ${email.padEnd(30)} ${planColored}`);
    });

    console.log(`\n${c.dim}───────────────────────────────────────────────────────────────${c.reset}`);
    console.log(`${c.gray}Active Session:${c.reset} ${active?.email ? `${active.email} (${active.planType})` : 'None'}  |  ${c.gray}App:${c.reset} ${isAppRunning() ? `${c.green}Running${c.reset}` : `${c.gray}Closed${c.reset}`}\n`);
  }

  function cleanup() {
    process.stdout.write('\x1b[?25h'); // Restore cursor
    if (stdin.isTTY) stdin.setRawMode(false);
    stdin.pause();
  }

  render(true);

  stdin.on('keypress', (str, key) => {
    if (!key) return;

    if (key.ctrl && key.name === 'c') {
      cleanup();
      process.exit(0);
    }

    if (key.name === 'q' || key.name === 'escape') {
      cleanup();
      console.log(`${c.gray}Cancelled.${c.reset}`);
      process.exit(0);
    }

    if (key.name === 'up' || key.name === 'k') {
      selectedIndex = (selectedIndex - 1 + accounts.length) % accounts.length;
      render();
    } else if (key.name === 'down' || key.name === 'j') {
      selectedIndex = (selectedIndex + 1) % accounts.length;
      render();
    } else if (key.name === 'return' || key.name === 'enter') {
      cleanup();
      switchAccount(accounts[selectedIndex]);
    } else if (str >= '1' && str <= String(accounts.length)) {
      const idx = parseInt(str, 10) - 1;
      cleanup();
      switchAccount(accounts[idx]);
    }
  });
}

function saveCurrent(name) {
  const active = getActiveAuth();
  if (!active || !active.auth || !active.auth.tokens) {
    console.log(`${c.red}Error: No active login found in ${AUTH_FILE}.${c.reset}`);
    process.exit(1);
  }

  const accounts = loadAccounts();
  const profileName = name || active.name || (active.email ? active.email.split('@')[0] : 'account');

  // Check if exists
  const existingIndex = accounts.findIndex(
    (a) => (active.accountId && a.auth_data?.account_id === active.accountId) || a.name.toLowerCase() === profileName.toLowerCase()
  );

  const newAcc = {
    id: existingIndex >= 0 ? accounts[existingIndex].id : crypto.randomUUID(),
    name: profileName,
    email: active.email || `${profileName}@unknown`,
    plan_type: active.planType || 'free',
    subscription_expires_at: null,
    auth_mode: 'chat_g_p_t',
    auth_data: {
      type: 'chat_g_p_t',
      id_token: active.auth.tokens.id_token,
      access_token: active.auth.tokens.access_token,
      refresh_token: active.auth.tokens.refresh_token,
      account_id: active.accountId,
    },
    created_at: existingIndex >= 0 ? accounts[existingIndex].created_at : new Date().toISOString(),
    last_used_at: new Date().toISOString(),
  };

  if (existingIndex >= 0) {
    accounts[existingIndex] = newAcc;
    console.log(`${c.green}✔ Updated existing account profile: ${c.bold}${profileName}${c.reset} (${newAcc.email})`);
  } else {
    accounts.push(newAcc);
    console.log(`${c.green}✔ Saved new account profile: ${c.bold}${profileName}${c.reset} (${newAcc.email})`);
  }

  saveAccounts(accounts);

  // Also create folder in ~/.codex-switch/profiles/
  const profileFolder = path.join(PROFILES_DIR, profileName);
  if (!fs.existsSync(profileFolder)) fs.mkdirSync(profileFolder, { recursive: true });
  fs.writeFileSync(path.join(profileFolder, 'auth.json'), JSON.stringify(active.auth, null, 2), 'utf8');
}

function removeAccount(query) {
  const accounts = loadAccounts();
  const idx = parseInt(query, 10);
  let targetIdx = -1;

  if (!isNaN(idx) && idx >= 1 && idx <= accounts.length) {
    targetIdx = idx - 1;
  } else {
    targetIdx = accounts.findIndex(
      (a) => a.name.toLowerCase() === query.toLowerCase() || a.email.toLowerCase() === query.toLowerCase()
    );
  }

  if (targetIdx === -1) {
    console.log(`${c.red}Account '${query}' not found.${c.reset}`);
    process.exit(1);
  }

  const removed = accounts.splice(targetIdx, 1)[0];
  saveAccounts(accounts);
  console.log(`${c.green}✔ Removed account profile:${c.reset} ${removed.name} (${removed.email})`);
}

function printHelp() {
  console.log(`
${c.cyan}${c.bold}ChatGPT Codex Account Switcher (CLI)${c.reset}
Fast terminal-based multi-account manager for OpenAI ChatGPT Codex app & CLI.

${c.bold}USAGE:${c.reset}
  ${c.cyan}codex-switch${c.reset}                  Interactive account switcher with arrow keys
  ${c.cyan}cs${c.reset}                            Short alias for codex-switch

${c.bold}COMMANDS:${c.reset}
  ${c.cyan}codex-switch <1|2|...>${c.reset}        Switch directly by account index
  ${c.cyan}codex-switch <name|email>${c.reset}     Switch directly by account name or email
  ${c.cyan}codex-switch list${c.reset} (or ${c.cyan}ls${c.reset})      List all saved accounts
  ${c.cyan}codex-switch current${c.reset} (or ${c.cyan}whoami${c.reset}) Show currently active account details
  ${c.cyan}codex-switch save [name]${c.reset}      Save current login session as a profile
  ${c.cyan}codex-switch rm <name|#>${c.reset}       Remove an account profile
  ${c.cyan}codex-switch restart${c.reset}          Restart ChatGPT Codex app & daemon
  ${c.cyan}codex-switch help${c.reset}             Show this help screen

${c.bold}FLAGS:${c.reset}
  ${c.cyan}-r, --restart${c.reset}                 Auto-restart ChatGPT Codex app after switching
  ${c.cyan}-n, --no-restart${c.reset}              Do not restart app after switching
`);
}

// Main CLI router
async function main() {
  const args = process.argv.slice(2);
  const restartFlag = args.includes('-r') || args.includes('--restart');
  const noRestartFlag = args.includes('-n') || args.includes('--no-restart');
  const filteredArgs = args.filter((a) => !['-r', '--restart', '-n', '--no-restart'].includes(a));

  const restartOption = restartFlag ? true : noRestartFlag ? false : null;

  if (filteredArgs.length === 0) {
    runInteractive();
    return;
  }

  const cmd = filteredArgs[0].toLowerCase();

  switch (cmd) {
    case 'list':
    case 'ls':
      printList();
      break;

    case 'current':
    case 'whoami':
    case 'status':
      printStatus();
      break;

    case 'save':
      saveCurrent(filteredArgs[1]);
      break;

    case 'rm':
    case 'remove':
    case 'delete':
      if (!filteredArgs[1]) {
        console.log(`${c.red}Specify account index or name to remove.${c.reset}`);
        process.exit(1);
      }
      removeAccount(filteredArgs[1]);
      break;

    case 'restart':
      restartApp();
      break;

    case 'help':
    case '-h':
    case '--help':
      printHelp();
      break;

    default: {
      // Treat argument as index, name, or email to switch directly
      const accounts = loadAccounts();
      const num = parseInt(cmd, 10);
      let target = null;

      if (!isNaN(num) && num >= 1 && num <= accounts.length) {
        target = accounts[num - 1];
      } else {
        target = accounts.find(
          (a) =>
            a.name.toLowerCase().includes(cmd) ||
            a.email.toLowerCase().includes(cmd) ||
            (a.auth_data?.account_id && a.auth_data.account_id.toLowerCase().startsWith(cmd))
        );
      }

      if (!target) {
        console.log(`${c.red}Account matching '${cmd}' not found.${c.reset}`);
        console.log(`Run ${c.cyan}codex-switch list${c.reset} to see available accounts.`);
        process.exit(1);
      }

      switchAccount(target, { restart: restartOption });
      break;
    }
  }
}

main().catch((err) => {
  console.error(`${c.red}Error: ${err.message}${c.reset}`);
  process.exit(1);
});
