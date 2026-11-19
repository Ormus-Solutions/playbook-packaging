# Playbook packaging: the playbook

This file is written for a coding agent (Claude Code, Codex, Grok) and is
readable by a person. Do the steps in order. Each step is one action, a
"Verify:" command and the result to expect. Stop at the first result that
does not match and report what you saw.

In the commands, replace SLUG with the playbook's slug and PROJECT with the
folder of the thing being packaged. Run each command from the root of this
repo unless the command starts with `cd`.

## Goal

A new repo, `playbook-SLUG`, next to this one. It follows
[STANDARD.md](STANDARD.md), passes its own `./check.sh`, holds no private
data, and was published private first, tested by a fresh agent, then made
public and shared in the chat.

## Before you start

| Need | Check | Expected | If it fails |
|---|---|---|---|
| Python 3.11 or newer | `python3 -c 'import sys; print(sys.version_info >= (3, 11))'` | `True` | install a newer Python from python.org or your package manager |
| git | `git --version` | a version line | install git |
| bash | `bash --version \| head -n 1` | a version line | install bash |
| gitleaks (recommended) | `gitleaks version` | a version | install it from its releases page; without it the scrub still runs and says it skipped gitleaks |
| GitHub CLI (to publish) | `gh auth status` | logged in to github.com | run `gh auth login`, or publish on the website |
| this repo | `test -x scripts/new.sh && echo ok` | `ok` | `cd` to the root of your clone of playbook-packaging |
| the thing to package | `ls PROJECT` | its files | ask the person where it lives |

## Steps

### 1. Run the demo on synthetic data

This shows the whole process before anything on the machine changes.

```bash
bash examples/run.sh
```

Verify: `bash examples/run.sh | diff - examples/expected-output.txt && echo same`
Expected: `same`

### 2. Write the deny-list

The scrub finds a key by its shape, but it cannot know the names of your
clients. You list them. The list lives outside every repo, because it holds
exactly the words that must not be published.

```bash
mkdir -p ~/.config/playbooks
touch ~/.config/playbooks/denylist.txt
chmod 600 ~/.config/playbooks/denylist.txt
```

Then add one name per line: clients, companies, products, machine names,
project code names, and people's full names. An agent proposes names (from
the folder names in the person's projects, for example) and the person
confirms each one. Lines that start with `#` are comments.

Verify: `ls -l ~/.config/playbooks/denylist.txt | cut -c1-10; grep -cvE '^[[:space:]]*(#|$)' ~/.config/playbooks/denylist.txt`
Expected: `-rw-------`, then a number above 0.

### 3. Pick the slug

One or two words for what the playbook does, joined by a dash: `lane-counts`,
`session-notes`. Not your name, not a client's name.

Verify: `echo SLUG | grep -E '^[a-z0-9]+(-[a-z0-9]+)*$'`
Expected: the slug, printed back.

### 4. Make the repo from the template

```bash
bash scripts/new.sh SLUG ../playbook-SLUG
```

Verify: `git -C ../playbook-SLUG symbolic-ref --short HEAD`
Expected: `main`

### 5. Scrub the project you are packaging

Find the private parts before they reach the new repo. The list tells you what
to leave out or replace while you copy. Do not fix them in the private
project; it is allowed to hold them.

```bash
bash scripts/scrub.sh PROJECT > /tmp/scrub-SLUG.txt
```

Verify: `tail -n 2 /tmp/scrub-SLUG.txt`
Expected: a line that starts with `scrub:` (`clean`, or `FAILED` with the count of findings listed above it).

### 6. Copy the core, not the history

Copy only the files that do the work into `src/`, by hand or with `cp`. Do not
copy the `.git` folder: a public repo publishes every commit, and old commit
messages and diffs often name clients. The fresh repo starts a clean history.
While you copy, turn every host, path and name into a setting read from a
config file, and leave out what only your own setup needs.

Verify: `bash scripts/scrub.sh ../playbook-SLUG | tail -n 1`
Expected: a line that starts with `scrub: clean`.

### 7. Make synthetic examples

A reader must see it work before they trust it, and real data cannot be
published. Write made-up input in `examples/` (names like `acme-web` and
`demo-api`, lanes like `api`, `web`, `docs`), an example config, and
`examples/run.sh`, which runs the tool on them. Check the output by eye, then
save it as `examples/expected-output.txt`.

Verify: `cd ../playbook-SLUG && bash examples/run.sh | diff - examples/expected-output.txt && echo same`
Expected: `same`

### 8. Pin the behaviour with tests

Replace `tests/test_tool.py` with tests for your tool, on the synthetic data,
offline. Keep the demo test. To see that a test can fail, change one number in
`src/`, run the tests, watch one fail, and undo the change.

Verify: `cd ../playbook-SLUG && python3 -m unittest discover -s tests 2>&1 | tail -n 1`
Expected: `OK`

### 9. Write PLAYBOOK.md for an agent

Fill every section of `../playbook-SLUG/PLAYBOOK.md`. Each step is one
action with the exact command, a `Verify:` line and an `Expected:` line. A
step that changes something outside the repo says so, so the agent asks first.

Verify: `python3 src/playbook_lint.py ../playbook-SLUG | grep -c PLAYBOOK.md`
Expected: `0`

### 10. Write README.md

Fill every section of `../playbook-SLUG/README.md`. "What it saved me" is in
your own words. The Preview is the output of `bash examples/run.sh`, pasted in
a code block. Put your name in `LICENSE` and in Credits.

Verify: `python3 src/playbook_lint.py ../playbook-SLUG | tail -n 1`
Expected: `lint: ok`

### 11. Set a noreply e-mail for the commits

A public repo shows the e-mail of every commit. GitHub gives you a private
address under Settings, Emails; it looks like
`12345+you@users.noreply.github.com`.

```bash
git -C ../playbook-SLUG config user.email 12345+you@users.noreply.github.com
```

Verify: `git -C ../playbook-SLUG config user.email`
Expected: an address that ends in `users.noreply.github.com`.

### 12. Run the gate and make the first commit

```bash
cd ../playbook-SLUG && ./check.sh && git add -A && git commit -m "feat: first version"
```

Verify: `cd ../playbook-SLUG && ./check.sh | tail -n 1`
Expected: `check: ok` (now the scrub reads the commit too).

### 13. Publish it private

Ask the person first: this creates a repo on GitHub.

```bash
cd ../playbook-SLUG && gh repo create playbook-SLUG --private --source . --push
```

Verify: `gh repo view playbook-SLUG --json visibility -q .visibility`
Expected: `PRIVATE`

### 14. Run the fresh-agent test

Clone the private repo into a temp folder. Open a new agent session there,
one that has never seen your setup, and paste only the README's Quick start
prompt. Write down every question it asks you and every step where it gets
stuck. Fix `PLAYBOOK.md` for each one, commit, push, and run the test again
until the agent reaches "Done when" without your help.

Verify: `rm -rf /tmp/fresh-SLUG && gh repo clone playbook-SLUG /tmp/fresh-SLUG && /tmp/fresh-SLUG/check.sh | tail -n 1`
Expected: `check: ok`, and the fresh agent's last message shows every "Done when" check passing.

### 15. Make it public

Ask the person first: from here on, anyone can read and copy it.

```bash
gh repo edit playbook-SLUG --visibility public --accept-visibility-change-consequences
```

Verify: `gh repo view playbook-SLUG --json visibility,licenseInfo,defaultBranchRef -q '[.visibility, .licenseInfo.spdxId, .defaultBranchRef.name] | join(" ")'`
Expected: `PUBLIC MIT main`

### 16. Share it in the chat

Ask the person first: the post goes to other people. Use the three parts of
the README's "Sharing it in the chat" section. The person posts it.

Verify: `gh repo view playbook-SLUG --json url -q .url`
Expected: the link that the post's third line carries.

## Adapt it

| Setting | Where | Example |
|---|---|---|
| Deny-list file | environment variable `PLAYBOOK_DENYLIST` | `PLAYBOOK_DENYLIST=~/work/denylist.txt bash scripts/scrub.sh .` |
| Deny-list entries | the deny-list file, one per line | `globex corp` also matches `globex-corp`, `globex_corp` and `globexcorp` |
| A line the scrub must accept | add the marker `scrub:allow` to that line | a test fixture with a fake address; the summary counts it |
| What new repos start with | `template/` | add a `docs/` folder for an SVG made from the synthetic data |
| The sections the lint asks for | `README_SECTIONS` and `PLAYBOOK_SECTIONS` in `src/playbook_lint.py` | add a "Troubleshooting" section |
| The author in new repos | `LICENSE` and Credits in each new repo | your name, or your company's |
| gitleaks | installed or not | the scrub uses it when `gitleaks version` works |

## Done when

- `cd ../playbook-SLUG && ./check.sh | tail -n 1` prints `check: ok`.
- `python3 src/playbook_lint.py ../playbook-SLUG | tail -n 1` prints `lint: ok`.
- A fresh agent reached "Done when" of the new playbook from the Quick start prompt alone.
- The visibility check of step 15 prints `PUBLIC MIT main`.
- The post with its three parts is in the chat.

## Undo

- Before publishing: `rm -rf ../playbook-SLUG`. Nothing else was written.
- After step 13: `gh repo delete playbook-SLUG` (it asks you to confirm).
- After step 15: make it private again (`gh repo edit playbook-SLUG --visibility private --accept-visibility-change-consequences`) or delete it. Anything that was public may already be cloned. A key that was ever public must be rotated where it was issued; deleting the repo is not enough.
- The deny-list: `rm ~/.config/playbooks/denylist.txt`. It is yours alone; nothing else reads it.

## Safety

- Reads: the folders you pass to `scripts/scrub.sh` and `src/playbook_lint.py`, their git history, and the deny-list file.
- Writes: `scripts/new.sh` writes only the folder you give it, and refuses one that is not empty. `scripts/scrub.sh` and the lint write nothing; the scrub makes a temp copy of the files for gitleaks and deletes it.
- Never: the scripts never push, create a repo, change a repo's visibility or post a message. Those are steps 13, 15 and 16, and the person says yes to each one.
- The output is safe to paste: a finding names the file, line, column and rule, never the matched text; a deny-list hit names the entry number, never the word; a path with a deny-listed word is shown with `***`.
- The scrub is a net, not a wall. It catches the common shapes of private data. Read the diff yourself before a repo goes public, and look at every picture, because the scrub cannot read them.
