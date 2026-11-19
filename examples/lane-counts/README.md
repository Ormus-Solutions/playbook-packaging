# Lane counts

Print how many tasks each lane of a project has open and done, from one JSON file.

## What it is

A small command that reads a list of tasks (each with a lane and a state) and
prints a table: one row per lane, one column per state. It uses the pattern
"config in a file, logic in a pure function": the lanes and states live in a
TOML file, and the counting is a function with no side effects, so the tests
can pin it with a few lines of synthetic data.

## What it saved me

This is a synthetic example made for playbook-packaging. In a real playbook,
this section is the author's own words about what changed in how they work.

## Who it is for

Anyone who splits a project into lanes (for example "api", "web", "docs") and
wants a quick count without opening a board. Skip it if your tracker already
shows this.

## Requirements

| Tool | Version | Check |
|---|---|---|
| Python | 3.11 or newer | `python3 --version` |
| git | any recent version | `git --version` |

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

1. Run `bash examples/run.sh` and compare it with the preview below.
2. Copy `examples/config.example.toml` to `~/.config/playbook-lane-counts/config.toml`.
3. Put your own lanes and states in it.
4. Run `python3 src/tool.py your-tasks.json`.

## Preview

The output of `bash examples/run.sh` on the synthetic data in `examples/`:

```text
acme-web board
lane   open  done
api       2     1
web       1     2
docs      0     1
other     1     0
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

Made by Ormus (Ormus Solutions) as the worked example of playbook-packaging. MIT license.
