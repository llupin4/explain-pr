---
name: explain-pr
description: Builds an HTML explainer page for a PR, branch, or diff. The page has Mermaid sequence diagrams, a structure map, rendered diffs, and design decisions labeled stated or inferred. Use for "explain this PR", "explain these changes", "walk me through this branch", or a change write-up for teammates.
---

# Explain PR

You write one HTML page about a code change. It teaches what the change does, how it fits the system, and why it has this design. Assume that the reader does not know this part of the codebase. The page must work for a teammate who reads it alone, without the author in the room.

The page has three jobs, in this order:

1. Show the structure. Which parts of the system changed, and how do calls and data move through them now?
2. Walk through the code. Show focused diffs in the order that builds understanding, not in file order.
3. Explain the choices. For each design decision, say why, and say how you know.

## Inputs

Find out what to explain. If the user does not say, use the current branch against its base.

- A PR number or URL: run `gh pr view <n> --json title,body,baseRefName,headRefName,commits,comments,reviews,files` and `gh pr diff <n>`. Use `gh api repos/{owner}/{repo}/pulls/<n>/comments` for review comments.
- A branch: find the base with `git merge-base origin/main HEAD` (or the default branch). Use `git log --format='%h %s%n%b' <base>..HEAD` for commit messages.
- Uncommitted work: diff against `HEAD`.

If the base is truly unclear, ask one question. Otherwise, state the base you picked at the top of the page.

## Step 1: Research

Read more than the diff. A diff without context produces a shallow page.

1. Run `git diff --stat -M <base>...<head>` to size the change.
2. Read every changed file in full, not only the hunks. Read the callers and callees of changed functions, one level out.
3. Read the PR body, commit messages, review comments, linked issues, and any ADR, design doc, or README the change touches. These are your only sources for stated reasons.
4. Read the tests that changed or were added. Tests show the intended behavior.
5. Note what the code did before. You need the old path to draw the "before" diagram.

For a large PR (more than about 40 files or 1500 changed lines), you can split research across subagents by area. Each one returns: files read, entry points, call paths before and after, and any stated reasons with their source.

## Step 2: Build the model

Before you write HTML, write these notes for yourself:

- Problem: what was wrong or missing, in two or three sentences.
- Components: each module, service, class, or layer that the change touches. Mark each one new, changed, removed, or unchanged-but-relevant.
- Flows: each runtime path the change affects (a request, a job, an event, a UI action). For each flow, list the participants and the messages in order, before and after.
- Explanation order: the order in which the reader meets the changes. Usually: data model or types, then the core logic, then the wiring, then the UI or API surface, then tests. Mechanical changes (renames, imports, generated files, formatting) go last or into the full diff only.
- Decisions: each place where the author chose one approach over a reasonable other one.

## Step 3: Label every reason

This is the most important rule. Readers will repeat what the page says, so the page must not present a guess as a fact.

For each design decision, write:

- Decision: what was chosen, in one sentence.
- Reason, with a label:
  - `stated`: the author said so. Cite the source (commit `abc123`, PR description, review comment by a named person, a doc path).
  - `inferred`: you deduced it from the code. Name the evidence ("the old function held a lock across the network call", "the new test covers concurrent writes").
- Alternatives: one or two other approaches that the author had available, and the tradeoff of each against the chosen one.
- Confidence for inferred reasons: high, medium, or low.

Never write an inferred reason in the voice of the author ("we did X because"). Write "This likely avoids X, because ...".

## Step 4: Generate the diff data

Run the helper to turn the diff into a JSON block the page can render:

```bash
python3 <skill-dir>/scripts/diff_to_json.py --base <base> --head <head> --out /tmp/explain-pr-diffs.html
```

It writes a `<script type="application/json" id="pr-diffs">` element with one patch per file, the file status list, and the line counts. It escapes the content so that it cannot break out of the script tag. Paste that element into the page where the template marks `<!-- PR-DIFFS -->`, or let the script inject it with `--inject <page.html>`.

To print the hunk numbers of each file, run the same command with `--list`. You need the hunk numbers for focused diffs. For a PR, use `--pr <n>` in place of `--base`. For uncommitted work, use `--working`.

## Step 5: Write the page

In this file, `<skill-dir>` is the folder that holds this SKILL.md. Copy `<skill-dir>/templates/explainer.html` and fill it in. Keep its CSS and script. It loads Mermaid, diff2html, and highlight.js from jsDelivr.

The page has these sections, in this order. If a section has nothing true to say, skip it. Do not pad.

1. Summary. Three to five sentences: what changed, for whom, and the one idea the reader must keep. Add the base, head, file count, and line counts.
2. Context. The problem and the relevant system background. Define each domain term at first use.
3. Structure map.
   - A file tree of changed files, grouped by directory, with a badge for new, modified, deleted, or renamed, and the +/- counts. Put mechanical files in a collapsed group.
   - A Mermaid `flowchart` of the components from Step 2. Style new components and changed edges so they stand out (the template has `classDef` lines for `added`, `changed`, and `removed`).
4. How it flows. For each affected flow, a Mermaid `sequenceDiagram` for before and one for after, side by side (`.compare` grid). If a flow is new, draw only "after" and say so. Under each pair, write two to four sentences on what moved. Use `Note over`, `alt`/`else`, `loop`, and `rect` blocks to show the important part. Keep each diagram under about 15 messages. Split larger flows. If a flow has more than five participants, use `class="compare stacked"` so the two diagrams sit one above the other at full width.
5. Walkthrough. The changes in the order from Step 2. Each step has a short heading, one or two paragraphs, and a focused diff: `<div class="focus-diff" data-file="path/to/file.ts" data-hunks="1,3"></div>`. Show only the hunks that teach. Default to `data-format="line-by-line"`. If the reader must compare a rewritten block, use `data-format="side-by-side"`.
6. Design decisions. One card per decision from Step 3, with its `stated` or `inferred` badge, source or evidence, alternatives, and tradeoff.
7. Tests and verification. What the tests cover, what they do not cover, and the commands to run them.
8. Risks and open questions. Behavior changes, migration or rollout concerns, performance, security, and anything you did not find out. Questions for the author go here.
9. Full diff. The whole change rendered by diff2html in a collapsed `<details>` element, with the file list.
10. Glossary. If the page uses more than about five domain terms, add this section.

### Mermaid rules

- Put each diagram in `<pre class="mermaid">`. Escape `<` as `&lt;` and `&` as `&amp;` inside it.
- Quote labels that have spaces, parentheses, or punctuation: `A["Auth service (new)"]`.
- In sequence diagrams, declare participants first with short aliases and no quotes: `participant API as Orders API`. Quotes show up as literal text.
- Do not put `;` or `#` in message text. Write "number" for `#`.
- Use the real function and endpoint names from the code in messages, so the reader can search for them.

### Writing rules

- Write for a smart engineer who is new to this code.
- Explain the why next to the code, not in a separate essay.
- Use real names from the code. Wrap identifiers in `<code>`.
- Keep paragraphs short. One idea per paragraph.
- Do not praise the change. Describe it.

## Step 6: Check the page

1. Run `python3 <skill-dir>/scripts/check_page.py <page.html>`. It checks that every `data-file` exists in the diff data, every hunk index is valid, every Mermaid block is not empty and has no raw `<`, and every decision card has a `stated` or `inferred` badge. Fix all errors.
2. If you have a browser tool, open the page and look at it. Mermaid shows "Syntax error" in place of a broken diagram. Fix any you see. If `npx` is available and you cannot open a browser, you can parse each diagram with `npx -y @mermaid-js/mermaid-cli -i diagram.mmd -o /tmp/out.svg`.
3. Run the independent review. Start a subagent that did not write the page. If you can pick its model, use Fable 5.2 (`model: fable`). Give it the page path, the base and head, and this task:

   > Check this PR explainer against the actual diff and repository. For each claim in the Design decisions, How it flows, and Walkthrough sections: (a) is it true in the code, (b) is a reason labeled `stated` really stated in the cited source, (c) is an `inferred` reason plausible, and is its confidence right, (d) does each sequence diagram match the real call order. Report each problem with the section, the claim, the evidence, and a fix. Do not rewrite the page.

   Fix what it finds. If you disagree with a finding, keep your version and add the point to Risks and open questions.

## Step 7: Deliver

Save the page as `explain-<branch-or-pr>.html`. Default location: `.pr-explain/` at the repo root (add it to `.git/info/exclude` so it is not committed), unless the user names another path. Open it if you can. Tell the user the path, the number of flows and decisions covered, and any open questions for the author.

If the page must work without internet access, run `python3 <skill-dir>/scripts/diff_to_json.py --vendor` once on a machine with access. It downloads the libraries into `templates/vendor/`. Then pass `--inline-vendor` with `--inject` to embed them in the page.
