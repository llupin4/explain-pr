# explain-pr

A Claude Code skill that turns a PR, branch, or diff into one HTML page. The page teaches the change to a reader who did not write it.

The page has these parts:

- A summary and the problem context.
- A structure map: a file tree of changed files with status badges and line counts, and a Mermaid component diagram that marks new, changed, and removed parts.
- Before and after Mermaid sequence diagrams for each runtime flow that the change affects. Click a diagram to enlarge it.
- A walkthrough in teaching order, with focused diffs rendered by diff2html (syntax highlighting, word-level changes, unified or side-by-side).
- Design decisions. Each reason has a label: `stated` (the author said so, with a source) or `inferred` (deduced from the code, with evidence and a confidence level).
- Tests, risks, and open questions for the author.
- The full diff, collapsed, with a unified or side-by-side toggle.

The skill also tells the agent to run an independent review of the page with a second subagent. If the agent tool lets you pick the model, that subagent runs on Fable 5.2.

## Install

### As a plugin (Claude Code)

```
/plugin marketplace add llupin4/explain-pr
/plugin install explain-pr@explain-pr
```

If the repository is private, the machine needs git access to it (for example, `gh auth login`).

### As a plain skill

Copy the skill folder into your personal or project skills folder:

```bash
git clone https://github.com/llupin4/explain-pr.git
cp -r explain-pr/skills/explain-pr ~/.claude/skills/        # personal
# or
cp -r explain-pr/skills/explain-pr <repo>/.claude/skills/   # one project
```

## Use

Ask the agent in plain words:

- "Explain this branch."
- "Explain PR 482 for the team."
- "Write an explain-these-changes page for feature/retry-queue against main."

The page goes to `.pr-explain/explain-<name>.html` in the repository. The skill adds that folder to `.git/info/exclude`, so git does not track it.

## Requirements

- Python 3.8 or later and git.
- The GitHub CLI (`gh`), only for PR numbers.
- A browser with internet access to cdn.jsdelivr.net to view the page. This loads Mermaid 11, diff2html 3, and highlight.js 11.

## Offline pages

If the network blocks jsDelivr, embed the libraries in the page. Do this setup step once:

```bash
python3 skills/explain-pr/scripts/diff_to_json.py --vendor
```

If that download is also blocked, get the same files from npm:

```bash
npm i mermaid@11 diff2html@3 highlight.js@11
V=skills/explain-pr/templates/vendor; mkdir -p $V
cp node_modules/mermaid/dist/mermaid.min.js $V/
cp node_modules/diff2html/bundles/js/diff2html-ui.min.js $V/
cp node_modules/diff2html/bundles/css/diff2html.min.css $V/
cp node_modules/highlight.js/styles/github.min.css $V/hljs-github.min.css
cp node_modules/highlight.js/styles/github-dark.min.css $V/hljs-github-dark.min.css
```

Then ask the agent for an offline page. It passes `--inline-vendor`, and the page grows to about 5 MB.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/diff_to_json.py` | Splits the diff per file, counts lines, lists hunks (`--list`), and injects the data into the page (`--inject`). Takes `--base`, `--pr`, or `--working`. |
| `scripts/check_page.py` | Finds broken diff references, bad hunk numbers, raw `<` or `&` in diagrams, leftover template examples, and decisions without a `stated` or `inferred` label. |

## License

MIT. Mermaid and diff2html are MIT. highlight.js is BSD-3-Clause.
