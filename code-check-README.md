# code-check V2

> **Local-first, ultra-fast multi-language static analysis & diagnostic orchestrator for developers, CI pipelines, and AI coding agents.**

`code-check` eliminates the complexity of orchestrating disparate language linters, type checkers, and security scanners. Rather than running 4–5 fragmented CLI tools with conflicting output schemas, `code-check` orchestrates Rust-native analyzers (**Ruff**, **Oxlint**, **ast-grep**) and deep static typing (**Pyright**, **tsc**) in parallel, normalizing all issues into an immutable, structured **Unified Diagnostic IR**.

---

## 1. Architecture

```
                             code-check CLI
                                   │
                           Project Detection
                      (git diff / language router)
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
     Python                     JS / TS                     Other
        │                          │                          │
      Ruff                       Oxlint                    ast-grep
   (lint/bugs)                (lint/hooks)              (structural AST)
        │                          │
    Pyright*                     tsc*
  (deep types)               (deep types)
        └──────────────────────────┬──────────────────────────┘
                                   ▼
                         Unified Diagnostic IR
            (file, line, col, severity, category, rule, fix)
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
  Terminal Cards               Agent JSON                 Fix Engine
  (ANSI layout)          (--agent deterministic)       (--fix verifier)
```

*\*Deep type checking enabled via `--deep` or `--types`.*

---

## 2. Supported Analyzers Matrix

| Language / Domain | Fast Mode (Default) | Deep Mode (`--deep` / `--types`) | Security Mode (`--security`) | Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | **Ruff** (Rust-native) | **Pyright** (Static Types) | **Semgrep** (when installed) | Fast linting, correctness, imports, modern syntax, static typing |
| **JavaScript / TypeScript** | **Oxlint** (Rust-native) | **tsc** (`--noEmit`) | **Semgrep** (when installed) | React hooks, strict syntax, JSX rules, full TypeScript compilation checks |
| **Structural AST** | **ast-grep** (`sg`) | — | — | Custom architectural rules, syntax patterns, dangerous function disallowance |
| **Secrets Detection** | — | — | **Gitleaks** (optional) | Secret and credential scanning in git repositories |
| **Dependency CVEs** | — | — | **OSV-Scanner** (optional) | Open-source vulnerability scanning across package lockfiles |

*Note: ast-grep is an AST structural pattern engine whose rules identify architectural and security violations. Security scanners (Semgrep, Gitleaks, OSV-Scanner) execute strictly in `--security` mode and degrade gracefully when unavailable.*

---

## 3. Installation & Global Workstation Setup

`code-check` is pre-installed globally in `C:\tools\`:

```powershell
# Verify installation from any terminal
code-check --version
code-check doctor
code-check --help
```

### Manual Installation
Requires Python 3.10+:
```powershell
git clone <repo-url> code-check
cd code-check
pip install -e .
```

---

## 4. CLI Commands & Execution Tiers

### A. Core Scans
```powershell
# Fast scan across current project (Ruff + Oxlint + ast-grep in parallel)
code-check

# Target a specific folder or file
code-check ./src/components
code-check ./app/main.py

# Check only Git-modified, staged, and untracked files
code-check --changed

# Deep static type checking (includes Pyright for Python & tsc for TypeScript)
code-check --deep

# Type checking only
code-check --types

# Security analysis (Semgrep + Gitleaks + OSV-Scanner)
code-check --security
```

### B. Automation, Watch & Machine Modes
```powershell
# Safe two-phase auto-fix (scan -> apply fixes -> re-scan -> report remaining)
code-check --fix

# Persistent watch daemon with instant incremental re-check on save
code-check --watch

# Configure custom debounce for slow editors (e.g. 100ms or 500ms)
code-check --watch --debounce 100

# Machine-readable JSON output for AI coding agents & CI pipelines
code-check --agent
# or
code-check --json

# Quiet mode (minimal terminal output)
code-check --quiet

# Strict mode (exit code 1 on warnings)
code-check --strict
```

---

## 5. Tool Discovery & Environment Check (`code-check doctor`)

Inspect system readiness and tool versions:

```powershell
code-check doctor
```

**Output:**
```text
code-check environment

  ✓ Python         3.12.0
  ✓ Ruff           0.16.8
  ✓ Oxlint         1.85.0
  ✓ ast-grep       0.45.3
  ✓ Pyright        1.1.414
  ✓ TypeScript     5.9.3
  ○ Semgrep        unavailable
  ○ Gitleaks       unavailable
  ○ OSV-Scanner    unavailable
```

---

## 6. Unified Diagnostic IR Schema

Every analyzer’s raw output is transformed into this deterministic, immutable JSON schema:

```json
{
  "status": "failed",
  "clean": false,
  "summary": {
    "status": "failed",
    "clean": false,
    "total_issues": 2,
    "errors": 1,
    "warnings": 1,
    "security": 0,
    "security_issues": 0,
    "fixable": 1,
    "fixable_issues": 1,
    "files_checked": 14,
    "tools_run": ["ruff", "oxlint"],
    "tools_executed": ["ruff", "oxlint"],
    "tools_available": ["ruff", "oxlint", "pyright", "tsc", "ast-grep"],
    "duration_ms": 123.4,
    "tool_timings_ms": {
      "ruff": 45.2,
      "oxlint": 78.2
    }
  },
  "issues": [
    {
      "severity": "error",
      "category": "bug",
      "file": "src/auth.py",
      "line": 42,
      "column": 17,
      "end_line": 42,
      "end_column": 29,
      "rule": "F821",
      "message": "Undefined name `user_token`",
      "tool": "ruff",
      "fixable": false
    }
  ]
}
```

### Standardized Diagnostic Categories:
- `syntax`: Parse and compile-time syntax errors (`F9`, `E9`).
- `bug`: Logic errors, React hook rule violations, undefined variables (`F821`, `B006`).
- `style`: Linter formatting, unused imports, deprecated type annotations (`I001`, `UP035`).
- `type`: Static type mismatches from Pyright or `tsc`.
- `security`: Security patterns, secret leaks, vulnerability checks.
- `dependency`: Outdated or vulnerable external package dependencies.
- `architecture`: ast-grep structural rule violations.
- `performance`: Sub-optimal loops, regex aliases, or unbuffered operations.
- `tooling`: Tool failure or misconfiguration.
- `unknown`: Unclassified warnings.

---

## 7. Exit Codes Protocol

`code-check` adheres to predictable exit codes for CI/CD and automation scripts:

| Exit Code | Meaning | Details |
| :--- | :--- | :--- |
| **`0`** | Clean | No errors (and no warnings if `--strict` is unset). |
| **`1`** | Code Issues Detected | One or more errors found, or warnings when `--strict` is enabled. |
| **`2`** | Execution Failure | Tool execution failure, binary timeout, or missing required dependency. |
| **`3`** | Usage Error | Invalid CLI arguments, unrecognized flags, or malformed syntax. |

---

## 8. Git Incremental Mode (`--changed`)

When running `code-check --changed`:
1. Queries `git status --porcelain -uall` to identify modified, staged, and untracked files.
2. Filters out deleted files and unsupported extensions.
3. Dispatches only relevant files to appropriate analyzers.
4. Exits with code `0` immediately (`No modified, staged, or untracked source files found via Git.`) when the working tree is clean.

---

## 9. Safe Two-Phase Auto-Fixing (`--fix`)

The auto-fix engine enforces a safety loop:
```
1. Initial Scan  ──>  Count initial fixable issues
2. Apply Fixes   ──>  Run ruff check --fix / oxlint --fix
3. Verification  ──>  Re-scan project without fix flag
4. Final Report  ──>  Report only truly remaining diagnostics & actual fixed count
```
This guarantees partial or ambiguous fixes do not introduce new regressions unnoticed.

---

## 10. Persistent Watch Mode (`--watch`)

Watch mode runs a continuous daemon:
- Sub-50ms poll loop with configurable debounce (default: **250ms**).
- Caches tracked file lists to prevent repeated directory tree walks.
- Reports: `Changed File -> Analyzers Executed -> Diagnostic Latency -> Summary`.
- **Measured Latency Distribution**:
  - **P50**: **164.5 ms**
  - **P95**: **276.0 ms**
  - **P99**: **276.0 ms**

---

## 11. Configuration (`.code-check.toml`)

Zero-config by default. You can place a `.code-check.toml` in your project root:

```toml
[general]
fail_on = "error"
parallel = true
default_deep = false
debounce_ms = 250
timeout_sec = 30.0

[languages.python]
enabled = true
linters = ["ruff"]
type_checkers = ["pyright"]
rules = ["E", "F", "W", "UP", "B", "S"]

[languages.javascript]
enabled = true
linters = ["oxlint"]
type_checkers = ["tsc"]
react_plugin = true

[ast_grep]
enabled = true
rules_dir = "rules/ast-grep"

[ignore]
paths = [
    "node_modules",
    ".venv",
    "dist",
    "build",
    ".git",
    "coverage"
]
```

---

## 12. Real-World Validation Results

Validated directly against three production codebases on Windows 11:

| Repository | Files | Languages | Analyzers | Issues Detected | Analysis Time |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BEACON** | 1,579 | Python, TS, TSX | Ruff, Oxlint, ast-grep | 100 errors (74 fixable) | **2,297.8 ms** |
| **BEACON Single File** | 1 | Python | Ruff, ast-grep | 1 error | **59.6 ms** |
| **tokensaver** | 400 | Python | Ruff, Oxlint, ast-grep | 100 errors (98 fixable) | **548.7 ms** |
| **code-check** | 27 | Python | Ruff, ast-grep | 25 errors, 75 warnings | **379.0 ms** |

*See benchmark reports for detailed telemetry.*

---

## 13. Limitations & Workstation Boundaries

1. **Optional Security Analyzers**: Semgrep, Gitleaks, and OSV-Scanner are optional plugins. When unavailable, `code-check doctor` and `--security` report them as `○ unavailable` without crashing.
2. **Deep Type Checking (`tsc`)**: `tsc` requires `tsconfig.json` in the target project. In repositories without TypeScript configuration, `tsc` is skipped gracefully.
3. **Windows Console Encoding**: Terminal output automatically handles Windows `cp1252` encoding by reconfiguring stdout to UTF-8 with clean ASCII fallback markers.

---

## 14. Development & Test Suite

Run the full automated test suite:

```powershell
# Run all 31 unit, parser, and integration tests:
py -m pytest

# Run benchmark suite:
py benchmarks/run_benchmarks.py
```
