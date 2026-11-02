#!/usr/bin/env python3
"""Word counts per chapter: body words vs Interview Questions and Answers words, with a running total.

    python3 05-build/wordcount.py                 # all 02-manuscript/chNN.md, table to stdout
    python3 05-build/wordcount.py --sample        # include 02-manuscript/_sample/ch00.md
    python3 05-build/wordcount.py --write         # also write 05-build/out/wordcount.md and .json
    python3 05-build/wordcount.py --floor 1000000 # the floor the running total is compared with (default 1,000,000)

Counting rules (the book prompt's floor counts chapter body plus its interview section; front matter,
Part pages and appendices are excluded):
  - The text is parsed by pandoc, so markup, attributes, link targets and fenced-div syntax are not words.
  - Body = everything before the "Interview Questions and Answers" heading; Interview = that section to the
    end of the chapter. Box text, captions and table cells count as words.
  - Code blocks are not prose: counted separately as "code lines" and excluded from both word counts.
  - A word is a whitespace-separated token containing a letter or a digit ("p95", "$3,280", "re-read" = 1).
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MS = ROOT / "02-manuscript"
WORD = re.compile(r"[A-Za-z0-9]")
IQA = "interview questions and answers"


def words_in(node, acc):
    if isinstance(node, dict):
        t = node.get("t")
        if t == "CodeBlock":
            acc["code"] += node["c"][1].count("\n") + 1
            return
        if t == "Str":
            acc["text"].append(node["c"]); return
        if t in ("Space", "SoftBreak", "LineBreak"):
            acc["text"].append(" "); return
        if t == "Code":
            acc["text"].append(node["c"][1]); return
        if t == "Math":
            acc["text"].append(" [math] "); return
        if t in ("Link", "Image"):
            words_in(node["c"][1], acc); return   # link text only, never the target
        if t in ("Header", "Div", "Span", "CodeBlock", "Figure", "Table"):
            words_in(node.get("c"), acc); return
        words_in(node.get("c"), acc)
    elif isinstance(node, list):
        for x in node:
            if isinstance(x, (dict, list)): words_in(x, acc)


def count_tokens(text):
    return sum(1 for w in "".join(text).split() if WORD.search(w))


def chapter_counts(md):
    doc = json.loads(subprocess.run(["pandoc", "-f", "markdown", "-t", "json", str(md)],
                                    capture_output=True, text=True, check=True).stdout)
    body = {"text": [], "code": 0}; iqa = {"text": [], "code": 0}
    cur = body; n_q = 0; title = ""
    for b in doc["blocks"]:
        if b["t"] == "Header":
            acc = {"text": [], "code": 0}; words_in(b["c"][2], acc)
            h = "".join(acc["text"]).strip()
            if b["c"][0] == 1 and not title: title = h
            if h.lower() == IQA: cur = iqa
        if cur is iqa and b["t"] == "Div" and "qa" in b["c"][0][1]: n_q += 1
        words_in(b, cur)
    return {"title": title, "body": count_tokens(body["text"]), "interview": count_tokens(iqa["text"]),
            "questions": n_q, "code_lines": body["code"] + iqa["code"]}


def main():
    floor = 1_000_000
    if "--floor" in sys.argv: floor = int(sys.argv[sys.argv.index("--floor") + 1])
    files = sorted(MS.glob("ch[0-9][0-9].md"))
    if "--sample" in sys.argv: files = sorted((MS / "_sample").glob("ch*.md")) + files
    rows, run = [], 0
    for f in files:
        c = chapter_counts(f)
        c["chapter"] = f.stem; c["total"] = c["body"] + c["interview"]; run += c["total"]; c["running"] = run
        c["iqa_ok"] = 12 <= c["questions"] <= 20
        rows.append(c)
    out = ["| Chapter | Body words | Interview words | Questions | Chapter total | Running total | Code lines |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for c in rows:
        q = f"{c['questions']}" + ("" if c["iqa_ok"] else " (needs 12-20)")
        out.append(f"| {c['chapter']} {c['title'][:60]} | {c['body']:,} | {c['interview']:,} | {q} | {c['total']:,} | {c['running']:,} | {c['code_lines']:,} |")
    tb = sum(c["body"] for c in rows); ti = sum(c["interview"] for c in rows)
    out.append(f"| **Total** | **{tb:,}** | **{ti:,}** | | **{tb + ti:,}** | | |")
    out.append("")
    out.append(f"Floor {floor:,}: {'met' if tb + ti >= floor else f'{floor - tb - ti:,} words short'} "
               f"({(tb + ti) / floor:.1%}). Front matter, Part pages and appendices are not counted.")
    text = "\n".join(out)
    print(text)
    if "--write" in sys.argv:
        o = ROOT / "05-build/out"; o.mkdir(parents=True, exist_ok=True)
        (o / "wordcount.md").write_text(text + "\n")
        (o / "wordcount.json").write_text(json.dumps({"floor": floor, "chapters": rows, "body": tb, "interview": ti}, indent=1))


if __name__ == "__main__":
    main()
