# The playbook standard

Every playbook repo follows these rules. The reason is simple: a reader, or
their agent, learns the shape once and can then use any playbook. The parts a
program can check are checked by `src/playbook_lint.py` (marked "lint" below)
and by `scripts/scrub.sh` (marked "scrub"). The rest is for the person who
reviews the repo before it goes public.

## Name, license, branch

- One public repo per playbook, named `playbook-<slug>`. The slug is lowercase
  words joined by dashes and says what the playbook does: `lane-counts`, not
  `my-tool`.
- The MIT license, in `LICENSE` (lint).
- The default branch is `main`.

## Files

| Path | What it holds | Checked |
|---|---|---|
| `README.md` | the front door, for a person | lint |
| `PLAYBOOK.md` | the steps, for an agent, readable by a person | lint |
| `src/` | a small reference implementation | lint (not empty) |
| `examples/` | synthetic input, an example config, the expected output | lint (not empty) |
| `tests/` | offline tests that pin the behaviour on the synthetic data | lint (not empty) |
| `check.sh` | one command: the tests and the scrub; non-zero on any failure | lint (executable) |
| `scripts/scrub.sh` | copied from playbook-packaging, unchanged | lint |
| `CHANGELOG.md` | what changed, newest first, with a first entry | lint |
| `LICENSE` | the MIT license | lint |
| `.gitignore` | caches, local settings, `.env` files | lint |

## README.md

The sections, in this order:

1. **Title**: a `# ` line with the playbook's name.
2. **What it is**: one paragraph. Name the pattern and say why it works.
3. **What it saved me**: the author's own words about what changed in how
   they work. Say what you measured; never invent numbers.
4. **Who it is for**: who gets value from it, and who should skip it.
5. **Requirements**: a table of tool, version and a check command: the Herdr
   version when the playbook uses Herdr, Python 3.11 or newer, and every
   other tool.
6. **Quick start**, with two paths:
   - **Hand it to your agent**: one copy-paste prompt, in a code block, that
     tells a coding agent to read `PLAYBOOK.md` and follow it.
   - **Do it by hand**: the same steps, short, for a person.
7. **Preview**: made from the synthetic example, as text in a code block or
   a generated SVG. Never a real screenshot.
8. **Files**: what each path holds.
9. **Credits**: the author, and the license.

The lint checks that each section is there, that the agent prompt names
`PLAYBOOK.md`, and that the preview has a code block or an SVG.

## PLAYBOOK.md

Written for a coding agent (Claude Code, Codex, Grok) and readable by a
person. The sections:

| Section | What it holds |
|---|---|
| Goal | the state the reader's machine is in when this is done |
| Before you start | each prerequisite with a check command, the expected result, and what to do if it fails |
| Steps | numbered `### 1. Do this` headings; one action each; each with a `Verify:` line (a command) and an `Expected:` line (its result) |
| Adapt it | a table of Setting, Where and Example: what to change for your own projects |
| Done when | the acceptance checks |
| Undo | how to remove it cleanly |
| Safety | what it reads and writes, and what it never does |

Why `Verify:` and `Expected:` on every step: an agent that runs a command and
compares the result knows when it went wrong, and stops there, instead of
building ten more steps on a broken one. The pattern is called a
verification loop.

## Code

- `src/` holds a small reference implementation: Python 3.11 or newer with the
  standard library is preferred, with type hints.
- No hard-coded hosts or user paths. Settings come from a config file or from
  environment variables, with an example config in `examples/`.
- `examples/` lets anyone see it work with no setup: a `--demo` flag or
  `examples/run.sh`, and the output it must print.
- `tests/` runs offline (unittest or pytest) and pins the behaviour on the
  synthetic data.
- `check.sh` runs the tests and the scrub, and exits non-zero on any failure.

## Writing

- Plain, short sentences. No marketing words, no emojis.
- Name the pattern and say why it works, because readers are learning.
- Made-up, generic examples only: `acme-web`, `demo-api`, lanes `api`, `web`,
  `docs`.
- When an example needs an address, use the ones reserved for documentation:
  e-mails at `example.com`, IP addresses in `192.0.2.0/24`. The scrub lets
  them through, because they can never belong to anyone.

## What never goes in

- Secrets: keys, tokens, passwords, private keys, `.env` files (scrub).
- E-mail addresses and phone numbers (scrub).
- A commit whose author or committer e-mail is not a noreply address: a
  public repo shows it on every commit (scrub).
- Host names, IP addresses, Tailscale names and internal URLs (scrub).
- Home paths that show a user name (scrub).
- Client and company names, and people's names other than the author credit
  (scrub, with your deny-list).
- Real screenshots, client logos, and paths that reveal a client project
  (the scrub cannot read pictures: look at each one yourself).
