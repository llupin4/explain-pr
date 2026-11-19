---
name: explain-pr
description: Writes an HTML page that explains a PR, branch, or diff to a reader who does not know the code. The page has sequence diagrams, a map of changed files, colored diffs, and design reasons labeled stated or inferred. Use for "explain this PR", "explain these changes", "walk me through this branch", or a write-up of a change for teammates.
---

# Explain PR

You write one HTML page about a code change. The page explains what changed, how it fits the system, and why the author chose this design. The reader does not know this part of the code. The reader reads the page alone and cannot ask the author.

The page has three jobs, in this order:

1. Show the structure. Show which parts of the system changed, and how calls and data move through them now.
2. Walk through the code. Show the changes in the order that is easiest to learn, not in file order.
3. Explain the choices. For each design decision, give the reason and say how you know it.

In this file, `<skill-dir>` is the folder that holds this SKILL.md.

Terms used in this file:

- A hunk is one block of changed lines in a diff. Each hunk starts with `@@`.
- A focused diff shows only the hunks that teach one step.
- A flow is one runtime path, for example a request, a job, an event, or a UI action.

## Inputs

If the user does not name a change, explain the current branch against its base branch.

- For a PR number or URL, run `gh pr view <n> --json title,body,baseRefName,headRefName,commits,comments,reviews,files`.
- For review comments on a PR, run `gh api repos/{owner}/{repo}/pulls/<n>/comments`.
- For a branch, find the base with `git merge-base origin/main HEAD`. If the default branch is not `main`, use its name.
- For the commit messages of a branch, run `git log --format='%h %s%n%b' <base>..HEAD`.
- For uncommitted work, use `HEAD` as the base.

If you cannot tell which base to use, ask the user one question. Otherwise, write the base that you used at the top of the page.

## Step 1: Research

Read more than the diff. A page made from the diff alone does not explain why.

1. Run `git diff --stat -M <base>...<head>` to see the size of the change.
2. Read each changed file in full, not only its hunks.
3. Read the callers and callees of each changed function, one level out.
4. Read the PR description, the commit messages, the review comments, and the linked issues.
5. Read each design doc, ADR, or README that the change touches.
6. Read the tests that the change adds or edits. The tests show the intended behavior.
7. Write down what the code did before the change. You need the old path for the "before" diagrams.

Only the sources in items 4 and 5 can give a stated reason.

If the PR has more than about 40 files or 1500 changed lines, you can split the research across subagents by area. Each subagent returns the files it read, the entry points, the call paths before and after, and each stated reason with its source.

## Step 2: Plan the page

Before you write HTML, write these notes for yourself:

- Problem: what was wrong or missing, in two or three sentences.
- Components: each module, service, class, or layer that the change touches. Mark each one as new, changed, removed, or unchanged but relevant.
- Flows: each flow that the change affects. For each flow, list the participants and the messages in order, before and after.
- Order: the order in which the reader sees the changes. A good default is types and data model, then core logic, then wiring, then the UI or API, then tests.
- Mechanical changes: renames, imports, generated files, and formatting. Put these last, or show them only in the full diff.
- Decisions: each place where the author picked one approach over another good approach.

## Step 3: Label every reason

This is the most important rule. Readers repeat what the page says. A guess must never look like a fact.

For each design decision, write these parts:

- Decision: what the author chose, in one sentence.
- Reason: why the author chose it.
- Label: `stated` or `inferred`.
  - If a source gives the reason, use `stated`. Name the source: a commit hash, the PR description, a review comment and its author, or a doc path.
  - If you worked out the reason from the code, use `inferred`. Name the evidence, for example "the old function held a lock during the network call".
- Confidence: for an inferred reason, write high, medium, or low.
- Alternatives: one or two other approaches that the author had, and what each one gains or loses against the chosen one.

Do not write an inferred reason in the voice of the author. Do not write "we did X because". Write "This probably avoids X, because ...".

## Step 4: Make the page file

1. Copy `<skill-dir>/templates/explainer.html` to `.pr-explain/explain-<branch-or-pr>.html` at the repository root.
2. Add `.pr-explain/` to `.git/info/exclude`, so that git ignores the page.
3. If the user names another path for the page, use that path.
4. Put the diff data into the page:

```bash
python3 <skill-dir>/scripts/diff_to_json.py --base <base> --head <head> --inject <page.html>
```

For a PR, use `--pr <n>` in place of `--base` and `--head`. For uncommitted work, use `--working`.

5. To see the hunk numbers of each file, run the same command with `--list` in place of `--inject <page.html>`. You need these numbers for focused diffs.

The script escapes the diff text, so the diff cannot break the page. If you run it again, it replaces the old diff data.

## Step 5: Write the page

Fill in the template. Keep its CSS and its script. The page loads Mermaid, diff2html, and highlight.js from cdn.jsdelivr.net.

The page has these sections, in this order. If a section has nothing true to say, delete it. Do not add filler.

1. Summary. Write three to five sentences: what changed, for whom, and the one idea that the reader must keep. The page script adds the file count and the line counts.
2. Context. Explain the problem and the system background. Define each domain term the first time you use it.
3. Structure map. The page script draws the file tree from the diff data. Below the tree, draw a Mermaid `flowchart` of the components from Step 2. Use the template classes `added`, `changed`, and `removed` to color them.
4. How it flows. For each flow, draw a Mermaid `sequenceDiagram` for before and one for after, side by side. Under each pair, write two to four sentences about what moved.
5. Walkthrough. Show the changes in the order from Step 2. Each step has a short heading, one or two paragraphs, and a focused diff.
6. Design decisions. Write one card for each decision from Step 3.
7. Tests and verification. Say what the tests cover and what they do not cover. Give the commands that run them.
8. Risks and open questions. List behavior changes, rollout or migration concerns, performance, security, and each thing that you did not find out. Put questions for the author here.
9. Full diff. Keep the template block. It shows the whole diff, closed until the reader opens it.
10. Glossary. If the page uses more than about five domain terms, add this section. Otherwise, delete it.

### Diagram rules

- If a flow is new, draw only the "after" diagram and say that the flow is new.
- Keep each sequence diagram to about 15 messages or fewer. Split a larger flow into parts.
- If a flow has more than five participants, use `class="compare stacked"`. Then the two diagrams sit one above the other at full width.
- Use `Note over`, `alt`/`else`, `loop`, and `rect` blocks to point at the part that changed.
- Put each diagram in `<pre class="mermaid">`.
- Inside a diagram, write `<` as `&lt;` and `&` as `&amp;`.
- In a flowchart, put quotes around a label that has spaces or punctuation: `A["Auth service (new)"]`.
- In a sequence diagram, declare each participant first, with a short alias and no quotes: `participant API as Orders API`. Quotes show up on the page.
- Do not put `;` or `#` in message text. Write "number" in place of `#`.
- In messages, use the real function and endpoint names from the code, so that the reader can search for them.

### Focused diff rules

- A focused diff is this element: `<div class="focus-diff" data-file="path/to/file.ts" data-hunks="1,3"></div>`.
- `data-hunks` takes hunk numbers from `--list`, for example `2` or `1,3` or `2-4`. To show the whole file, leave out `data-hunks`.
- Show only the hunks that teach the step.
- The default format is one column. If the reader must compare a rewritten block, add `data-format="side-by-side"`.

### Decision card rules

- Copy the decision card from the template for each decision.
- Each card must have a `stated` badge or an `inferred` badge.
- An inferred card must also have a confidence badge.
- A stated card puts its source in the Evidence row.

### Writing rules

- Write for a skilled engineer who is new to this code.
- Put each reason next to the code that it explains.
- Use the real names from the code. Put each name in `<code>`.
- Keep paragraphs short, with one idea in each.
- Describe the change. Do not praise it.

## Step 6: Test the page

1. Run `python3 <skill-dir>/scripts/check_page.py <page.html>`. Fix each error that it prints.
2. If you have a browser tool, open the page and look at each diagram. A broken diagram shows "Syntax error". Fix each one.
3. If you have no browser tool but `npx` works, test a diagram with `npx -y @mermaid-js/mermaid-cli -i diagram.mmd -o /tmp/out.svg`.
4. Start a review subagent that did not write the page. If you can choose its model, use Fable 5.2 (`model: fable`).
5. Give the subagent the page path, the base, the head, and the task below.
6. Fix each problem that the subagent finds. If you disagree with a finding, keep your text and add the point to Risks and open questions.

The task for the review subagent:

> Compare this PR explainer page with the real diff and the repository. Read the Walkthrough, How it flows, and Design decisions sections. For each claim, answer these questions:
>
> 1. Is the claim true in the code?
> 2. If the reason is labeled `stated`, does the cited source really give that reason?
> 3. If the reason is labeled `inferred`, is it believable, and is its confidence correct?
> 4. Does each sequence diagram match the real order of calls?
>
> For each problem, report the section, the claim, the evidence, and a fix. Do not edit the page.

## Step 7: Deliver

1. If you can, open the page in a browser.
2. Tell the user the path of the page.
3. Tell the user how many flows and decisions the page covers.
4. List the open questions for the author.

## Offline pages

If the page must work without internet access, the libraries must be inside the page.

1. On a computer with internet access, run `python3 <skill-dir>/scripts/diff_to_json.py --vendor` one time. It saves the libraries in `<skill-dir>/templates/vendor/`.
2. In Step 4, add `--inline-vendor` to the `--inject` command.
