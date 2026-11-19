#!/usr/bin/env python3
"""Turn a git diff into a JSON <script> block for the explain-pr page.

Usage:
  diff_to_json.py --base origin/main [--head HEAD] [--repo .] [--out FILE]
  diff_to_json.py --base origin/main --inject page.html [--inline-vendor]
  diff_to_json.py --base origin/main --list        # print hunk numbers per file
  diff_to_json.py --vendor                        # download JS/CSS for offline use
  diff_to_json.py --pr 123 ...                    # use `gh pr diff 123` as the source
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import urllib.request

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
VENDOR_DIR = SKILL_DIR / "templates" / "vendor"
VENDOR = {
    "mermaid.min.js": "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js",
    "diff2html-ui.min.js": "https://cdn.jsdelivr.net/npm/diff2html@3/bundles/js/diff2html-ui.min.js",
    "diff2html.min.css": "https://cdn.jsdelivr.net/npm/diff2html@3/bundles/css/diff2html.min.css",
    "hljs-github.min.css": "https://cdn.jsdelivr.net/npm/highlight.js@11/styles/github.min.css",
    "hljs-github-dark.min.css": "https://cdn.jsdelivr.net/npm/highlight.js@11/styles/github-dark.min.css",
}
MARKER = "<!-- PR-DIFFS -->"
VENDOR_MARKER_RE = re.compile(r"<!-- VENDOR-START -->.*?<!-- VENDOR-END -->", re.S)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True,
                          capture_output=True, text=True).stdout


def split_files(diff_text):
    """Split a unified diff into {path: patch}. Path is the new path (old path for deletes)."""
    files = {}
    chunks = re.split(r"(?m)^(?=diff --git )", diff_text)
    for chunk in chunks:
        if not chunk.startswith("diff --git "):
            continue
        path = None
        m = re.search(r"(?m)^\+\+\+ b/(.+)$", chunk)
        if m:
            path = m.group(1)
        else:
            m = re.search(r"(?m)^--- a/(.+)$", chunk) or re.search(r"(?m)^rename to (.+)$", chunk)
            if m:
                path = m.group(1)
            else:
                m = re.match(r"diff --git a/(.+?) b/(.+)$", chunk.splitlines()[0])
                path = m.group(2) if m else chunk.splitlines()[0]
        files[path.strip()] = chunk if chunk.endswith("\n") else chunk + "\n"
    return files


def file_meta(path, patch):
    status = "modified"
    old = None
    if re.search(r"(?m)^new file mode", patch):
        status = "added"
    elif re.search(r"(?m)^deleted file mode", patch):
        status = "deleted"
    m = re.search(r"(?m)^rename from (.+)$", patch)
    if m:
        status, old = "renamed", m.group(1)
    adds = dels = 0
    hunks = []
    for line in patch.splitlines():
        if line.startswith("@@"):
            hunks.append(line)
        elif line.startswith("+") and not line.startswith("+++"):
            adds += 1
        elif line.startswith("-") and not line.startswith("---"):
            dels += 1
    binary = "Binary files" in patch and not hunks
    return {"path": path, "status": status, "oldPath": old, "additions": adds,
            "deletions": dels, "hunks": hunks, "binary": binary}


def build(diff_text, base, head):
    files = split_files(diff_text)
    meta = [file_meta(p, d) for p, d in files.items()]
    return {
        "base": base, "head": head,
        "totals": {"files": len(meta),
                   "additions": sum(m["additions"] for m in meta),
                   "deletions": sum(m["deletions"] for m in meta)},
        "files": meta,
        "patches": files,
    }


def script_tag(data):
    # Escape characters that could end the <script> element or confuse HTML parsers.
    body = json.dumps(data, ensure_ascii=False)
    body = body.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    body = body.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return f'<script type="application/json" id="pr-diffs">{body}</script>'


def vendor_block():
    missing = [n for n in VENDOR if not (VENDOR_DIR / n).exists()]
    if missing:
        sys.exit(f"Missing vendor files {missing}. Run with --vendor first.")
    css = (VENDOR_DIR / "diff2html.min.css").read_text()
    light = (VENDOR_DIR / "hljs-github.min.css").read_text()
    dark = (VENDOR_DIR / "hljs-github-dark.min.css").read_text()
    js = "\n".join((VENDOR_DIR / n).read_text().replace("</script", "<\\/script")
                   for n in ["mermaid.min.js", "diff2html-ui.min.js"])
    return ("<!-- VENDOR-START -->\n<style>" + css + "</style>\n"
            "<style id=\"hljs-light\">" + light + "</style>\n"
            "<style id=\"hljs-dark\" media=\"not all\">" + dark + "</style>\n"
            "<script>" + js + "</script>\n<!-- VENDOR-END -->")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="base ref; the diff is base...head (merge-base)")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--pr", help="PR number; uses `gh pr diff` instead of git")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--working", action="store_true", help="diff uncommitted work against HEAD")
    ap.add_argument("--context", type=int, default=5, help="context lines per hunk")
    ap.add_argument("--out", help="write the <script> tag to this file")
    ap.add_argument("--inject", help="replace the PR-DIFFS marker (or old block) in this HTML page")
    ap.add_argument("--inline-vendor", action="store_true", help="with --inject: embed JS/CSS for offline use")
    ap.add_argument("--list", action="store_true", help="print hunk numbers per file and exit")
    ap.add_argument("--vendor", action="store_true", help="download JS/CSS into templates/vendor and exit")
    a = ap.parse_args()

    if a.vendor:
        VENDOR_DIR.mkdir(parents=True, exist_ok=True)
        for name, url in VENDOR.items():
            print("downloading", url)
            urllib.request.urlretrieve(url, VENDOR_DIR / name)
        print("saved to", VENDOR_DIR)
        return

    if a.pr:
        diff_text = subprocess.run(["gh", "pr", "diff", a.pr], cwd=a.repo, check=True,
                                   capture_output=True, text=True).stdout
        base, head = f"PR {a.pr} base", f"PR {a.pr} head"
    elif a.working:
        diff_text = git(a.repo, "diff", "-M", f"-U{a.context}", "--no-color", "HEAD")
        base, head = "HEAD", "working tree"
    else:
        if not a.base:
            ap.error("--base, --pr, or --working is required")
        diff_text = git(a.repo, "diff", "-M", f"-U{a.context}", "--no-color", f"{a.base}...{a.head}")
        base, head = a.base, a.head

    data = build(diff_text, base, head)

    if a.list:
        t = data["totals"]
        print(f"{t['files']} files, +{t['additions']} -{t['deletions']}")
        for f in data["files"]:
            print(f"\n{f['status']:8} {f['path']}  +{f['additions']} -{f['deletions']}")
            for i, h in enumerate(f["hunks"], 1):
                print(f"   hunk {i}: {h[:110]}")
        return

    tag = script_tag(data)
    if a.inject:
        page = pathlib.Path(a.inject)
        html = page.read_text()
        old = re.compile(r'<script type="application/json" id="pr-diffs">.*?</script>', re.S)
        if old.search(html):
            html = old.sub(lambda _: tag, html)
        elif MARKER in html:
            html = html.replace(MARKER, tag)
        else:
            sys.exit(f"No {MARKER} marker or pr-diffs block in {page}")
        if a.inline_vendor:
            html = VENDOR_MARKER_RE.sub(lambda _: vendor_block(), html)
        page.write_text(html)
        print(f"injected {data['totals']['files']} file patches into {page}")
    elif a.out:
        pathlib.Path(a.out).write_text(tag)
        print(f"wrote {a.out}")
    else:
        print(tag)


if __name__ == "__main__":
    main()
