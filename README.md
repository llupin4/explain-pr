# explain-pr

explain-pr is a skill for Claude Code. It reads a pull request or a branch and writes one web page that explains the change. The reader does not have to know the code before they read the page.

## What the page shows

The page is a short story in chapters. You step through the chapters one at a time, like slides, with the arrow keys or the Next button. Each chapter is a page that you can scroll. Each chapter answers one question, for example "What happens now when a user submits an order?". The text, diagrams, and code in the chapter all answer that question. The chapter ends with a takeaway and a link to the next chapter.

A sidebar lists the chapters in groups. To read everything as one long page, click One page or press P.

The chapters cover these things, in this order:

- What the change does, the problem that it solves, and a map of the parts of the system that changed.
- One chapter for each path through the system that changed, for example a request or a background job. Each one has before and after diagrams that show the order of calls. These are sequence diagrams. Click a diagram to make it larger. Under the diagrams is the code that made the change, with colored diffs (green for added lines, red for removed lines).
- A closer look at the parts of the code that need more explanation.
- The reason for each design choice. Each reason has a label. `stated` means that the author wrote the reason down, and the page names where. `inferred` means that the agent guessed the reason from the code, and the page shows the evidence.
- Tests, risks, questions for the author, and three points to remember.
- The full diff, at the end.

Before the agent gives you the page, a second agent reads it and compares it to the real code. If you can choose the model, the second agent uses Fable 5.2.

## Install

Run these two commands in Claude Code:

```
/plugin marketplace add llupin4/explain-pr
/plugin install explain-pr@explain-pr
```

If the repository is private, sign in to GitHub on that computer first. Use `gh auth login`.

To install without the plugin system, copy the skill folder into your skills folder:

```bash
git clone https://github.com/llupin4/explain-pr.git
cp -r explain-pr/skills/explain-pr ~/.claude/skills/
```

## Use

Open your repository in Claude Code and ask in plain words. For example:

- "Explain this branch."
- "Explain PR 482 for the team."
- "Explain the changes on feature/retry-queue compared to main."

The agent saves the page in the `.pr-explain` folder of your repository. Git ignores this folder. Open the page in a browser.

## What you need

- Python 3.8 or later.
- Git.
- The GitHub command line tool (`gh`). You need it only to explain a pull request by its number.
- A browser that can reach cdn.jsdelivr.net. The page loads its diagram and diff libraries from that site.

## If your network blocks cdn.jsdelivr.net

The agent can put the libraries inside the page. Then the page works without internet access. It grows to about 5 MB.

Do this setup once, in the folder of this repository:

```bash
python3 skills/explain-pr/scripts/diff_to_json.py --vendor
```

If that download also fails, get the same files from npm:

```bash
npm i mermaid@11 diff2html@3 highlight.js@11
V=skills/explain-pr/templates/vendor
mkdir -p $V
cp node_modules/mermaid/dist/mermaid.min.js $V/
cp node_modules/diff2html/bundles/js/diff2html-ui.min.js $V/
cp node_modules/diff2html/bundles/css/diff2html.min.css $V/
cp node_modules/highlight.js/styles/github.min.css $V/hljs-github.min.css
cp node_modules/highlight.js/styles/github-dark.min.css $V/hljs-github-dark.min.css
```

After the setup, ask the agent for an offline page.

## Files

| File | What it does |
|---|---|
| `skills/explain-pr/SKILL.md` | The instructions that the agent follows. |
| `skills/explain-pr/templates/explainer.html` | The page template. |
| `skills/explain-pr/scripts/diff_to_json.py` | Reads the diff and puts it into the page. |
| `skills/explain-pr/scripts/check_page.py` | Finds errors in a finished page, for example a link to a file that is not in the diff. |

## License

MIT. Mermaid and diff2html use the MIT license. highlight.js uses the BSD-3-Clause license.
