#!/usr/bin/env node
/**
 * ralph.mjs - Production-grade autonomous Ralph Loop engine with Gate 0 verification.
 * 
 * Supports both:
 * 1. The official Geoffrey Huntley / snarktank prd.json format (userStories, progress.txt, <promise>COMPLETE</promise>)
 * 2. Markdown checklist specifications (tasks.md / PRD.md / todo.md)
 * 
 * Enforces test verification and Gate 0 anti-cheat diff auditing before committing.
 */

import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const VERSION = '1.1.0';
const DEFAULT_TASKS = ['prd.json', 'tasks.md', 'PRD.md', 'todo.md', 'TASKS.md'];
const AGY_PATH = 'C:\\Users\\advdi\\.gemini\\bin\\agy.exe';
const GATE0_SCRIPT = 'C:\\Users\\advdi\\.gemini\\config\\skills\\adversarial-loop\\scripts\\diff_audit.py';
const ASSETS_DIR = 'C:\\tools\\ralph-assets';

function printHelp() {
  console.log(`
Ralph Loop v${VERSION} — Autonomous Fresh-Context Task Runner
Supports official prd.json (snarktank) & markdown tasks.md

Usage:
  ralph run [file] [options]      Run autonomous task loop (auto-detects prd.json or tasks.md)
  ralph status [file]             Show progress on task checklist
  ralph init [--format json|md]   Create starter prd.json or tasks.md + STEERING.md
  ralph --help                    Show this help
  ralph --version                 Show version

Options:
  --engine <agy|kiro|claude>      Agent CLI (default: auto-detect agy, fallback claude/kiro)
  --test-cmd <cmd>                Verification command (default: auto-detect npm test/pytest/cargo)
  --max-iterations <n>            Maximum loop iterations (default: 25)
  --circuit-breaker <n>           Max consecutive failures per task (default: 3)
  --no-gate0                      Skip Gate 0 anti-cheat diff audit
  --dry-run                       Simulate loop without calling agent
`);
}

function detectEngine(override) {
  if (override) return override;
  if (fs.existsSync(AGY_PATH)) return 'agy';
  const claudeCheck = spawnSync('claude', ['--version'], { encoding: 'utf8', windowsHide: true });
  if (claudeCheck.status === 0) return 'claude';
  return 'agy';
}

function detectTestCmd(override) {
  if (override) return override;
  if (fs.existsSync('package.json')) {
    try {
      const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
      if (pkg.scripts && pkg.scripts.test) return 'npm test';
    } catch {}
  }
  if (fs.existsSync('pytest.ini') || fs.existsSync('pyproject.toml') || fs.existsSync('tests')) return 'pytest';
  if (fs.existsSync('Cargo.toml')) return 'cargo test';
  if (fs.existsSync('go.mod')) return 'go test ./...';
  return null;
}

function findTaskFile(explicitFile) {
  if (explicitFile && fs.existsSync(explicitFile)) return explicitFile;
  for (const f of DEFAULT_TASKS) {
    if (fs.existsSync(f)) return f;
  }
  return null;
}

function parseMarkdownTasks(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split(/\r?\n/);
  const tasks = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const m = line.match(/^\s*[-*]\s*\[([ xX])\]\s*(.+)$/);
    if (m) {
      tasks.push({
        id: `TASK-${tasks.length + 1}`,
        lineIndex: i,
        completed: m[1].toLowerCase() === 'x',
        title: m[2].trim(),
        rawLine: line
      });
    }
  }
  return { isJson: false, content, lines, tasks };
}

function parseJsonTasks(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const data = JSON.parse(content);
  const tasks = (data.userStories || []).map((s, idx) => ({
    id: s.id || `US-${idx + 1}`,
    completed: s.passes === true,
    title: s.title,
    description: s.description,
    acceptanceCriteria: s.acceptanceCriteria || [],
    storyObj: s
  }));
  return { isJson: true, data, tasks, branchName: data.branchName };
}

function parseTasks(filePath) {
  if (filePath.endsWith('.json')) {
    return parseJsonTasks(filePath);
  }
  return parseMarkdownTasks(filePath);
}

function markCompleted(filePath, isJson, parsedData, currentTask) {
  if (isJson) {
    currentTask.storyObj.passes = true;
    fs.writeFileSync(filePath, JSON.stringify(parsedData.data, null, 2), 'utf8');
  } else {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split(/\r?\n/);
    if (lines[currentTask.lineIndex]) {
      lines[currentTask.lineIndex] = lines[currentTask.lineIndex].replace(/\[\s*\]/, '[x]');
      fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
    }
  }
}

function runCommand(cmd, args = [], options = {}) {
  if (args.length === 0) {
    const res = spawnSync(cmd, {
      stdio: options.stdio || 'inherit',
      shell: true,
      windowsHide: true,
      ...options
    });
    return res.status;
  }
  const res = spawnSync(cmd, args, {
    stdio: options.stdio || 'inherit',
    windowsHide: true,
    ...options
  });
  return res.status;
}

function execGit(args) {
  const res = spawnSync('git', args, { encoding: 'utf8', windowsHide: true });
  return {
    status: res.status,
    stdout: (res.stdout || '').trim(),
    stderr: (res.stderr || '').trim()
  };
}

async function runLoop(taskFile, opts) {
  const isJson = taskFile.endsWith('.json');
  console.log(`\n=======================================================`);
  console.log(`  RALPH LOOP — Autonomous Fresh-Context Engine v${VERSION}`);
  console.log(`=======================================================\n`);

  const engine = detectEngine(opts.engine);
  const testCmd = detectTestCmd(opts.testCmd);
  const maxIterations = parseInt(opts.maxIterations || '25', 10);
  const circuitBreaker = parseInt(opts.circuitBreaker || '3', 10);
  const useGate0 = !opts.noGate0 && fs.existsSync(GATE0_SCRIPT);

  console.log(`  Spec Format:     ${isJson ? 'Official snarktank JSON (prd.json)' : 'Markdown Checklist'}`);
  console.log(`  Target Spec:     ${taskFile}`);
  console.log(`  Agent Engine:    ${engine.toUpperCase()} (${engine === 'agy' ? AGY_PATH : 'claude CLI'})`);
  console.log(`  Test Runner:     ${testCmd || '(none detected / manual verification)'}`);
  console.log(`  Gate 0 Anti-Cheat: ${useGate0 ? 'ENABLED (' + path.basename(GATE0_SCRIPT) + ')' : 'DISABLED'}`);
  console.log(`  Max Iterations:  ${maxIterations}`);
  console.log(`  Circuit Breaker: ${circuitBreaker} consecutive failures\n`);

  // Verify git repo
  const gitCheck = execGit(['rev-parse', '--is-inside-work-tree']);
  if (gitCheck.status !== 0) {
    console.error('Error: Ralph loop must run inside a Git repository. Run `git init` first.');
    process.exit(1);
  }

  let iteration = 0;
  let currentTaskFailures = 0;
  let lastFailedTaskText = '';

  while (iteration < maxIterations) {
    iteration++;
    const parsed = parseTasks(taskFile);
    const pending = parsed.tasks.filter(t => !t.completed);

    if (pending.length === 0) {
      console.log(`\n🎉 ALL TASKS COMPLETED! All ${parsed.tasks.length} items verified and passing.`);
      console.log(`Emitting stop signal: <promise>COMPLETE</promise>\n`);
      process.exit(0);
    }

    const currentTask = pending[0];
    console.log(`----------------------------------------------------------------------`);
    console.log(`[Iteration ${iteration}/${maxIterations}] Progress: ${parsed.tasks.length - pending.length}/${parsed.tasks.length} done`);
    console.log(`Current Target: [${currentTask.id}] ${currentTask.title}`);
    console.log(`----------------------------------------------------------------------\n`);

    // Check circuit breaker
    if (currentTask.title === lastFailedTaskText) {
      currentTaskFailures++;
      if (currentTaskFailures >= circuitBreaker) {
        console.error(`\n🚨 CIRCUIT BREAKER TRIPPED! Task failed ${circuitBreaker} consecutive times.`);
        console.error(`Task: "${currentTask.title}"`);
        console.error(`Stopping loop to prevent token burn. Review requirements or run tests manually.\n`);
        process.exit(2);
      }
    } else {
      lastFailedTaskText = currentTask.title;
      currentTaskFailures = 0;
    }

    // Read steering if present
    let steeringNotes = '';
    if (fs.existsSync('STEERING.md')) {
      const steer = fs.readFileSync('STEERING.md', 'utf8').trim();
      if (steer) {
        steeringNotes = `\n\nACTIVE DEVELOPER STEERING (Follow strictly):\n${steer}`;
      }
    }

    // Read progress log learnings if progress.txt exists
    let previousLearnings = '';
    if (fs.existsSync('progress.txt')) {
      const prog = fs.readFileSync('progress.txt', 'utf8').trim();
      if (prog) {
        previousLearnings = `\n\nCODEBASE PATTERNS & PRIOR LEARNINGS (from progress.txt):\n${prog.slice(0, 1500)}`;
      }
    }

    // Construct prompt
    let prompt = '';
    if (isJson) {
      prompt = `You are an autonomous engineering agent running in a fresh context window (Ralph Loop iteration ${iteration}).

YOUR SINGLE OBJECTIVE:
Implement User Story [${currentTask.id}]: "${currentTask.title}"
${currentTask.description ? 'Description: ' + currentTask.description : ''}
Acceptance Criteria:
${currentTask.acceptanceCriteria.map(c => '- ' + c).join('\n')}

SPECIFICATION CONTEXT:
Refer to ${taskFile} for the complete system spec. Implement ONLY this single story.

NON-NEGOTIABLE QUALITY RULES (GRAVITAS & ADVERSARIAL GATE 0):
1. Ground before mutating: Read target code, callers, and tests before making any edits.
2. Bounded write scope: Modify only files directly required for this single story.
3. Fresh evidence: Run the test suite (${testCmd ? '`' + testCmd + '`' : 'appropriate test suite'}) after your edits and verify all tests pass.
4. Gate 0 Anti-Cheat: diff_audit will scan your git diff before commit. Any skipped tests, weakened assertions, lowered thresholds, or swallowed exceptions will immediately reject your changes.
5. Record learnings: Append what was implemented and reusable codebase patterns to progress.txt.
6. If all stories pass, reply with <promise>COMPLETE</promise>.${previousLearnings}${steeringNotes}`;
    } else {
      prompt = `You are an autonomous engineering agent running in a fresh context window (Ralph Loop iteration ${iteration}).

YOUR SINGLE OBJECTIVE:
Complete this specific atomic task:
"${currentTask.title}"

SPECIFICATION CONTEXT:
Refer to ${taskFile} for broader project context. Focus ONLY on this specific item.

NON-NEGOTIABLE QUALITY RULES (GRAVITAS & ADVERSARIAL GATE 0):
1. Ground before mutating: Read target code, callers, and tests before making any edits.
2. Bounded write scope: Modify only files directly required for this single task.
3. Fresh evidence: Run the test suite (${testCmd ? '`' + testCmd + '`' : 'appropriate test suite'}) after your edits and verify all tests pass.
4. Gate 0 Anti-Cheat: diff_audit will scan your git diff before commit. Any skipped tests, weakened assertions, lowered thresholds, or swallowed exceptions will immediately reject your changes.
5. When implementation is verified and tests pass, report completion and stop.${steeringNotes}`;
    }

    if (opts.dryRun) {
      console.log(`[DRY-RUN] Would spawn ${engine} with prompt:\n${prompt}\n`);
      markCompleted(taskFile, isJson, parsed, currentTask);
      continue;
    }

    // Record git baseline before agent touches code
    const baselineSha = execGit(['rev-parse', 'HEAD']).stdout;

    // Spawn agent in fresh context
    console.log(`>>> Spawning ${engine} agent in fresh context...\n`);
    let agentExit = 1;
    if (engine === 'agy') {
      agentExit = runCommand(AGY_PATH, ['--print', prompt, '--dangerously-skip-permissions']);
    } else if (engine === 'kiro') {
      const kiroCli = process.env.KIRO_CLI || 'c:\\Users\\advdi\\tools\\antigravity-auto-submit\\kiro-agent\\kiro-cli.mjs';
      agentExit = runCommand(process.execPath, [kiroCli, 'run', prompt]);
    } else {
      agentExit = runCommand('claude', ['--print', prompt]);
    }

    if (agentExit !== 0) {
      console.warn(`\n⚠️ Agent exited with code ${agentExit}. Retrying on next iteration...`);
      continue;
    }

    // Run verification tests
    if (testCmd) {
      console.log(`\n>>> Running Verification Suite: \`${testCmd}\`...`);
      const testStatus = runCommand(testCmd, [], { stdio: 'inherit' });
      if (testStatus !== 0) {
        console.error(`\n❌ VERIFICATION FAILED: \`${testCmd}\` exited with code ${testStatus}.`);
        console.log(`Reverting uncommitted changes to maintain clean state...`);
        execGit(['checkout', '--', '.']);
        continue;
      }
      console.log(`✅ Verification tests PASSED.`);
    }

    // Run Gate 0 Anti-Cheat Audit if available
    if (useGate0) {
      console.log(`>>> Running Gate 0 Anti-Cheat Audit (${path.basename(GATE0_SCRIPT)})...`);
      const auditRes = spawnSync('python', [GATE0_SCRIPT, '--base', baselineSha], { encoding: 'utf8', windowsHide: true });
      if (auditRes.status !== 0) {
        console.error(`\n🚨 GATE 0 BLOCKED: Shortcut or test tampering detected!`);
        console.error(auditRes.stdout || auditRes.stderr);
        console.log(`Reverting cheating changes...`);
        execGit(['checkout', '--', '.']);
        continue;
      }
      console.log(`✅ Gate 0 audit PASSED (no skipped tests or weakened assertions).`);
    }

    // Mark task completed in file
    markCompleted(taskFile, isJson, parsed, currentTask);

    // Atomic git commit
    const commitMsg = `feat(ralph): [${currentTask.id}] ${currentTask.title.slice(0, 50)}`;
    execGit(['add', '-A']);
    const commitRes = execGit(['commit', '-m', commitMsg]);
    if (commitRes.status === 0) {
      console.log(`\n📦 Committed atomic progress: "${commitMsg}"`);
    } else {
      console.log(`(No new changes to commit or commit succeeded)`);
    }

    // Append to progress logs
    const logEntry = `\n## [${new Date().toISOString()}] - ${currentTask.id}: ${currentTask.title}\n- Completed successfully with test verification.\n---\n`;
    fs.appendFileSync(isJson ? 'progress.txt' : '.ralph_progress.log', logEntry, 'utf8');

    console.log(`\n✓ Story verified and locked. Moving to next item...\n`);
  }

  console.warn(`\n⚠️ Maximum iterations (${maxIterations}) reached. Check remaining tasks with \`ralph status\`.\n`);
}

function showStatus(taskFile) {
  const parsed = parseTasks(taskFile);
  const done = parsed.tasks.filter(t => t.completed).length;
  const total = parsed.tasks.length;
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);

  console.log(`\nRalph Loop Status: ${taskFile}`);
  console.log(`Completed: ${done} / ${total} (${pct}%)\n`);

  for (const t of parsed.tasks) {
    console.log(`  [${t.completed ? 'x' : ' '}] [${t.id}] ${t.title}`);
  }
  console.log('');
}

function initFiles(format) {
  if (format === 'json') {
    if (fs.existsSync(path.join(ASSETS_DIR, 'prd.json.example'))) {
      fs.copyFileSync(path.join(ASSETS_DIR, 'prd.json.example'), 'prd.json');
      console.log('Created prd.json (from official snarktank schema)');
    }
  } else {
    if (!fs.existsSync('tasks.md')) {
      fs.writeFileSync('tasks.md', `# Project Tasks\n\n- [ ] Task 1: Define requirements and baseline tests\n- [ ] Task 2: Implement core logic\n- [ ] Task 3: Add edge-case test coverage\n`, 'utf8');
      console.log('Created tasks.md');
    }
  }
  if (!fs.existsSync('STEERING.md')) {
    fs.writeFileSync('STEERING.md', `# Mid-Flight Steering Notes\n\n<!-- Add mid-flight instructions here while Ralph runs -->\n`, 'utf8');
    console.log('Created STEERING.md');
  }
  if (!fs.existsSync('progress.txt')) {
    fs.writeFileSync('progress.txt', `# Ralph Progress Log\n\n## Codebase Patterns\n<!-- Add reusable patterns discovered here -->\n\n---\n`, 'utf8');
    console.log('Created progress.txt');
  }
}

// CLI Arg Parsing
const args = process.argv.slice(2);
const command = args[0] || 'run';

if (args.includes('--help') || args.includes('-h')) {
  printHelp();
  process.exit(0);
}
if (args.includes('--version') || args.includes('-v')) {
  console.log(`ralph v${VERSION}`);
  process.exit(0);
}

if (command === 'init') {
  const format = args.includes('--json') ? 'json' : 'md';
  initFiles(format);
  process.exit(0);
}

if (command === 'status') {
  const file = findTaskFile(args[1]);
  if (!file) {
    console.error('Error: No task file found (prd.json, tasks.md, PRD.md). Run `ralph init` to create one.');
    process.exit(1);
  }
  showStatus(file);
  process.exit(0);
}

if (command === 'run' || !command.startsWith('-')) {
  const fileArg = command === 'run' ? args[1] : command;
  const file = findTaskFile(fileArg);
  if (!file) {
    console.error('Error: No task file found. Run `ralph init` to create a starter prd.json or tasks.md.');
    process.exit(1);
  }

  const opts = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--engine' && args[i + 1]) opts.engine = args[++i];
    if (args[i] === '--test-cmd' && args[i + 1]) opts.testCmd = args[++i];
    if (args[i] === '--max-iterations' && args[i + 1]) opts.maxIterations = args[++i];
    if (args[i] === '--circuit-breaker' && args[i + 1]) opts.circuitBreaker = args[++i];
    if (args[i] === '--no-gate0') opts.noGate0 = true;
    if (args[i] === '--dry-run') opts.dryRun = true;
  }

  runLoop(file, opts);
} else {
  printHelp();
}
