#!/usr/bin/env python3
"""Check an explain-pr page for broken references and missing labels.

Usage: check_page.py page.html
Exit code 1 if any error is found.
"""
import html as htmllib
import json
import re
import sys


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    page = open(sys.argv[1], encoding="utf-8").read()
    errors, warnings = [], []

    m = re.search(r'<script type="application/json" id="pr-diffs">(.*?)</script>', page, re.S)
    if not m:
        errors.append("No pr-diffs data block. Run diff_to_json.py --inject.")
        data = {"patches": {}}
    else:
        data = json.loads(m.group(1))

    # Focused diffs point at real files and hunks
    for tag in re.findall(r'<div class="focus-diff"[^>]*>', page):
        f = re.search(r'data-file="([^"]*)"', tag)
        h = re.search(r'data-hunks="([^"]*)"', tag)
        path = htmllib.unescape(f.group(1)) if f else None
        if not path or "{{" in path:
            errors.append(f"focus-diff without a real data-file: {tag}")
            continue
        patch = data["patches"].get(path)
        if patch is None:
            errors.append(f"focus-diff file not in diff: {path}")
            continue
        n = len(re.findall(r"(?m)^@@ ", patch))
        if h and h.group(1).strip():
            for part in h.group(1).split(","):
                part = part.strip()
                rng = re.fullmatch(r"(\d+)-(\d+)", part)
                nums = range(int(rng.group(1)), int(rng.group(2)) + 1) if rng else [int(part)] if part.isdigit() else []
                if not nums:
                    errors.append(f"{path}: bad hunk spec '{part}'")
                for k in nums:
                    if k < 1 or k > n:
                        errors.append(f"{path}: hunk {k} does not exist (file has {n})")

    # Mermaid blocks
    blocks = re.findall(r'<pre class="mermaid">(.*?)</pre>', page, re.S)
    if not blocks:
        warnings.append("No Mermaid diagrams.")
    seq = 0
    for i, b in enumerate(blocks, 1):
        body = b.strip()
        first = body.splitlines()[0].strip() if body else ""
        if not body:
            errors.append(f"Mermaid block {i} is empty.")
            continue
        if first.startswith("sequenceDiagram"):
            seq += 1
            msgs = len(re.findall(r"(?m)^\s*\S+\s*-[-x)]?>>?[+-]?\s*\S+\s*:", body))
            if msgs > 20:
                warnings.append(f"Mermaid block {i}: {msgs} messages. Consider splitting.")
        if re.search(r"<(?!br\s*/?>)", body):
            errors.append(f"Mermaid block {i} has a raw '<'. Use &lt;.")
        if re.search(r"&(?![a-zA-Z]+;|#\d+;)", body):
            errors.append(f"Mermaid block {i} has a raw '&'. Use &amp;.")
        if "OrderService" in body or "RetryQueue" in body:
            errors.append(f"Mermaid block {i} still has the template example.")
    if blocks and seq == 0:
        warnings.append("No sequence diagrams.")

    # Decision labels
    decisions = re.findall(r'<div class="decision"[^>]*>(.*?)</dl>', page, re.S)
    for i, d in enumerate(decisions, 1):
        if not re.search(r'class="badge (stated|inferred)"', d):
            errors.append(f"Decision {i} has no stated or inferred badge.")
        if 'badge inferred' in d and 'confidence:' not in d:
            errors.append(f"Decision {i} is inferred but has no confidence badge.")
        if 'badge stated' in d and not re.search(r"<dt>(Evidence|Source)</dt>\s*<dd>\s*[^<\s{]", d):
            warnings.append(f"Decision {i} is stated: make sure that it cites a source.")
    if not decisions:
        warnings.append("No design decisions.")

    # Chapters
    nocomment = re.sub(r"<!--.*?-->", "", page, flags=re.S)
    parts = re.split(r'(?=<section class="chapter)', nocomment)
    chapters = [c for c in parts if c.startswith('<section class="chapter')]
    if not chapters:
        errors.append("No chapters. Each topic must be a <section class=\"chapter\">.")
    main_count = 0
    for i, c in enumerate(chapters, 1):
        c = c.split("</section>")[0]
        part = re.search(r'data-part="([^"]*)"', c)
        h2 = re.search(r"<h2>(.*?)</h2>", c, re.S)
        name = re.sub(r"<[^>]+>", "", h2.group(1)).strip() if h2 else f"chapter {i}"
        if not part:
            errors.append(f"Chapter {i} ({name}) has no data-part.")
        if not h2:
            errors.append(f"Chapter {i} has no <h2> title.")
        if part and part.group(1) == "Appendix":
            continue
        main_count += 1
        cover = 'class="chapter cover"' in c
        recap = 'class="recap"' in c
        if not cover and not recap:
            if 'class="asks"' not in c:
                warnings.append(f"Chapter {i} ({name}) has no <p class=\"asks\"> question.")
            if 'class="takeaway"' not in c:
                warnings.append(f"Chapter {i} ({name}) has no takeaway.")
        prose = re.sub(r"<(pre|script|style)\b.*?</\1>", " ", c, flags=re.S)
        prose = re.sub(r'<div class="focus-diff"[^>]*></div>', " ", prose)
        prose = re.sub(r"<[^>]+>", " ", prose)
        words = len(re.findall(r"[A-Za-z0-9][\w'-]*", htmllib.unescape(prose)))
        if words > 450:
            warnings.append(f"Chapter {i} ({name}) has {words} words of prose. Split it, or cut it to about 400.")
    if main_count > 25:
        warnings.append(f"{main_count} chapters outside the Appendix. Merge chapters that answer the same question.")
    if 0 < main_count < 4:
        warnings.append(f"Only {main_count} chapters outside the Appendix.")

    # Leftover placeholders
    visible = re.sub(r"<(script|style)\b.*?</\1>", "", page, flags=re.S)
    left = re.findall(r"\{\{[^}]{0,60}\}\}", visible)
    if left:
        errors.append(f"{len(left)} template placeholders remain, for example {left[0]}")

    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("error:", e)
    print(f"{len(errors)} errors, {len(warnings)} warnings, {len(chapters)} chapters, {len(blocks)} diagrams, {len(decisions)} decisions")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
