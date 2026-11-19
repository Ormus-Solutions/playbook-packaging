# Playbook packaging

How to turn something you built for yourself into a public playbook repo that
anyone in the chat, and their coding agent, can follow.

## What it is

A standard, a template and two checks. [STANDARD.md](STANDARD.md) says what
every playbook repo holds. `scripts/new.sh` copies the template into a new
repo. `src/playbook_lint.py` checks that a repo follows the standard.
`scripts/scrub.sh` checks that it holds nothing private before it goes
public. The pattern is called a "golden path": one well-marked way to do a
common job, with the checks built in, so each author spends their effort on
what the playbook teaches and not on its shape. And because every playbook
has the same shape, a reader learns it once.

## What it saved me

I asked for it in these words: "we need a playbook for how to package
playbooks that everyone in the chat can use". The chat shares how its members
work with coding agents. Without one shape, each share is a different kind of
repo, and each reader has to work out how to run it. What this saves: the
shape is decided once, and the scrub catches a client name or a key before a
repo goes public, not after.

## Who it is for

Anyone who built something for themselves (a script, a setup, a way of
working with an agent) and wants other people to be able to use it. Also
anyone who wants a checklist for publishing a small repo without leaking
private data. Skip it if you publish packages to a registry (PyPI, npm):
those have their own standards.

## Requirements

| Tool | Version | Check |
|---|---|---|
| Python | 3.11 or newer | `python3 --version` |
| git | any recent version | `git --version` |
| bash | 3.2 or newer | `bash --version` |
| gitleaks | optional, recommended | `gitleaks version` |
| GitHub CLI | optional, to publish from the terminal | `gh --version` |
| Herdr | not needed for this playbook | none |

## Quick start

### Hand it to your agent

Clone this repo, open your coding agent (Claude Code, Codex, Grok) inside the
clone, and paste this. Change PROJECT to the folder of what you built and SLUG
to a short name for it:

```text
Read PLAYBOOK.md in this repo and follow it step by step to package my
project in the folder PROJECT as a public playbook repo named playbook-SLUG.
After each step, run its "Verify:" command and compare the result with
"Expected:". If they differ, stop and tell me what you saw. Never push,
create a repo or make one public without my yes. When you finish, run the
"Done when" checks and show me their output.
```

### Do it by hand

1. Write your deny-list: `~/.config/playbooks/denylist.txt`, one private name
   per line (clients, companies, machines, people's full names), mode 600.
2. Run `bash examples/run.sh` to see the whole process on synthetic data.
3. Make the repo: `bash scripts/new.sh SLUG ../playbook-SLUG`.
4. Move the core of your tool into `src/`, with its settings in a config file.
5. Add synthetic examples in `examples/` and tests in `tests/`.
6. Fill `README.md`, `PLAYBOOK.md` and `LICENSE` until `./check.sh` prints
   `check: ok` and `python3 src/playbook_lint.py ../playbook-SLUG` prints
   `lint: ok`.
7. Before the first commit, set a noreply e-mail in the new repo (GitHub:
   Settings, Emails): `git config user.email 12345+you@users.noreply.github.com`.
   The scrub stops on a commit with any other address.
8. Follow the publishing checklist below, then share it with the post format.

## Preview

The output of `bash examples/run.sh`. It makes a playbook repo from the
template in a temp folder, lints it, fills it with the finished example in
`examples/lane-counts/`, lints it again and runs its gate:

```text
== 1. scripts/new.sh lane-counts playbook-lane-counts
created: .git .gitignore CHANGELOG.md LICENSE PLAYBOOK.md README.md check.sh examples scripts src tests
== 2. lint the fresh copy (it fails: placeholders are left)
lint: playbook-lane-counts
  README.md: 9 lines with a placeholder to fill (first: line 3)
  PLAYBOOK.md: 12 lines with a placeholder to fill (first: line 10)
  LICENSE: 1 line with a placeholder to fill (first: line 3)
lint: 3 problems
== 3. copy in the finished docs from examples/lane-counts/
== 4. lint again
lint: playbook-lane-counts
lint: ok
== 5. the new repo's own gate
check: ok
```

## Publishing checklist

1. **Private first.** Push the new repo as a private repo and read it on the
   website, as a stranger would. Mistakes are cheap while nobody else can see
   it.
2. **Scrub.** `./check.sh` must print `check: ok`. It runs the scrub on the
   files, the file names, every commit and every commit's e-mail. Then look at every picture
   yourself: the scrub cannot read them.
3. **A fresh-agent test.** Open a new agent session that has never seen your
   setup, in a fresh clone in a temp folder, and give it only the Quick start
   prompt. Every question it asks you, and every step where it gets stuck, is
   a gap in `PLAYBOOK.md`. Fix it and run the test again until the agent
   reaches "Done when" alone.
4. **Then public.** Make the repo public, and check that the link opens
   without signing in.

## Sharing it in the chat

Post three numbered parts, in this order:

```text
1. What I changed in how I work: <one or two sentences>
2. What it saved me: <your words; what you measured, if you can>
3. The link: https://github.com/<you>/playbook-<slug>
```

The order matters: people decide from the first two lines whether the link is
worth their time.

## Files

| Path | What it is |
|---|---|
| `STANDARD.md` | the rules every playbook repo follows |
| `PLAYBOOK.md` | the steps to package and publish a playbook, for an agent or a person |
| `template/` | the skeleton of a playbook repo, with placeholders to fill |
| `scripts/new.sh` | copies the template into a new repo and fills the slug |
| `scripts/scrub.sh` | the check that a folder holds nothing private; copy it into every playbook |
| `src/playbook_lint.py` | checks that a repo follows the standard |
| `examples/run.sh` | the whole process on synthetic data, with no setup |
| `examples/lane-counts/` | the finished docs of the synthetic example playbook |
| `examples/denylist.example.txt` | what a deny-list looks like (made-up names) |
| `examples/expected-output.txt` | what `examples/run.sh` must print |
| `tests/` | offline tests for the scrub, the lint, `new.sh` and the demo |
| `check.sh` | the one gate: tests, shellcheck when installed, lint and scrub |
| `CHANGELOG.md` | what changed, newest first |

## Credits

Made by Ormus (Ormus Solutions). MIT license. The scrub runs
[gitleaks](https://github.com/gitleaks/gitleaks), a separate project, when it
is installed.
