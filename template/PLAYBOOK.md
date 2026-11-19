# {{title}}: the playbook

This file is written for a coding agent (Claude Code, Codex, Grok) and is
readable by a person. Do the steps in order. Each step is one action, a
"Verify:" command and the result to expect. Stop at the first result that
does not match and report what you saw.

## Goal

<FILL: one or two sentences: the state the reader's machine is in when this is done.>

## Before you start

| Need | Check | Expected | If it fails |
|---|---|---|---|
| Python 3.11 or newer | `python3 -c 'import sys; print(sys.version_info >= (3, 11))'` | `True` | install a newer Python from python.org or your package manager |
| git | `git --version` | a version line | install git |
| <FILL: another need, or delete this row> | `<FILL: check command>` | <FILL: expected> | <FILL: what to do> |

## Steps

### 1. Run the demo on the synthetic data

This shows what the tool does before anything on your machine changes.

```bash
bash examples/run.sh
```

Verify: `bash examples/run.sh | diff - examples/expected-output.txt && echo same`
Expected: `same`

### 2. <FILL: the next action>

<FILL: what to do, as one action, with the exact command.>

Verify: `<FILL: a command that proves it worked>`
Expected: <FILL: what that command prints>

## Adapt it

| Setting | Where | Example |
|---|---|---|
| Lanes | `~/.config/playbook-{{slug}}/config.toml`, key `lanes` | `lanes = ["api", "web", "docs"]` |
| <FILL: setting> | <FILL: file or env variable> | <FILL: example value> |

## Done when

- `./check.sh` prints `check: ok`.
- <FILL: the checks that prove the reader has it working.>

## Undo

<FILL: how to remove it cleanly: every file it wrote and every setting it changed.>

## Safety

- Reads: <FILL: what it reads>
- Writes: <FILL: what it writes, and where>
- Never: <FILL: what it never does, for example send messages, delete data, read secrets>
