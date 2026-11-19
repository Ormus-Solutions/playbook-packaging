# Lane counts: the playbook

This file is written for a coding agent (Claude Code, Codex, Grok) and is
readable by a person. Do the steps in order. Each step is one action, a
"Verify:" command and the result to expect. Stop at the first result that
does not match and report what you saw.

## Goal

The reader can run `python3 src/tool.py tasks.json` and get a count of tasks
per lane and state, with their own lanes in their own config file.

## Before you start

| Need | Check | Expected | If it fails |
|---|---|---|---|
| Python 3.11 or newer | `python3 -c 'import sys; print(sys.version_info >= (3, 11))'` | `True` | install a newer Python from python.org or your package manager |
| git | `git --version` | a version line | install git |

## Steps

### 1. Run the demo on the synthetic data

This shows what the tool does before anything on your machine changes.

```bash
bash examples/run.sh
```

Verify: `bash examples/run.sh | diff - examples/expected-output.txt && echo same`
Expected: `same`

### 2. Make your config file

```bash
mkdir -p ~/.config/playbook-lane-counts
cp -n examples/config.example.toml ~/.config/playbook-lane-counts/config.toml
```

Verify: `python3 -c 'import tomllib, pathlib; print(sorted(tomllib.loads(pathlib.Path("~/.config/playbook-lane-counts/config.toml").expanduser().read_text())))'`
Expected: `['lanes', 'states', 'title']`

### 3. Put your own lanes in it

Open `~/.config/playbook-lane-counts/config.toml` and change `lanes` and
`states` to the names your project uses.

Verify: `python3 src/tool.py examples/tasks.json | head -n 2`
Expected: your title, then a header line that starts with `lane` and lists your states.

## Adapt it

| Setting | Where | Example |
|---|---|---|
| Title | `~/.config/playbook-lane-counts/config.toml`, key `title` | `title = "demo-api board"` |
| Lanes | the same file, key `lanes` | `lanes = ["api", "web", "docs"]` |
| States | the same file, key `states` | `states = ["open", "review", "done"]` |
| Config path | the `--config` option | `python3 src/tool.py tasks.json --config ./my.toml` |

## Done when

- `./check.sh` prints `check: ok`.
- `python3 src/tool.py examples/tasks.json` prints a table with your lanes.

## Undo

Delete the config folder: `rm -r ~/.config/playbook-lane-counts`. The tool
writes nothing else.

## Safety

- Reads: the tasks file you give it and its config file.
- Writes: nothing. It prints to the terminal.
- Never: sends anything over the network, reads other files, or changes your tasks.
