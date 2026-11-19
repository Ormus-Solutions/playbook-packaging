# {{title}}

<FILL: one line: what this playbook gives the reader.>

## What it is

<FILL: one paragraph. What it does, in plain words. Name the pattern it uses and say why the pattern works.>

## What it saved me

<FILL: your own words. What changed in how you work, and what it saves you. Say what you measured ("I stopped checking X by hand"); never invent numbers.>

## Who it is for

<FILL: who gets value from it, and who should skip it.>

## Requirements

| Tool | Version | Check |
|---|---|---|
| Python | 3.11 or newer | `python3 --version` |
| git | any recent version | `git --version` |
| Herdr | <FILL: the version you tested with, or delete this row> | `<FILL: the command that prints it>` |
| <FILL: another tool, or delete this row> | <FILL: version> | `<FILL: check command>` |

## Quick start

### Hand it to your agent

Clone this repo, open your coding agent (Claude Code, Codex, Grok) inside the
clone, and paste this:

```text
Read PLAYBOOK.md in this repo and follow it step by step. After each step,
run its "Verify:" command and compare the result with "Expected:". If they
differ, stop and tell me what you saw. Ask me before any step that changes
something outside this repo. When you finish, run the "Done when" checks and
show me their output.
```

### Do it by hand

1. <FILL: the same steps as PLAYBOOK.md, short, for a person.>

## Preview

The output of `bash examples/run.sh` on the synthetic data in `examples/`:

```text
<FILL: paste the output of bash examples/run.sh here.>
```

## Files

| Path | What it is |
|---|---|
| `PLAYBOOK.md` | the steps, for an agent or a person |
| `src/tool.py` | the reference implementation |
| `examples/` | synthetic input, an example config and the expected output |
| `tests/` | offline tests that pin the behaviour on the synthetic data |
| `check.sh` | the one gate: tests, placeholders, scrub |
| `scripts/scrub.sh` | the scrub check, copied from playbook-packaging |
| `CHANGELOG.md` | what changed, newest first |

## Credits

Made by <FILL: your name>. Packaged with playbook-packaging by Ormus (Ormus Solutions). MIT license.
