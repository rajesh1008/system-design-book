#!/usr/bin/env python3
"""Build the EPUB3 (and optionally AZW3) for "System Design for Agentic AI".

    python3 05-build/build_epub.py                       # full book from 05-build/book.yaml
    python3 05-build/build_epub.py 05-build/sample.yaml  # the sample chapter
    options: --azw3  also convert with Calibre ebook-convert
             --embed-fonts  embed Source Sans 3 and JetBrains Mono (adds about 1 MB; KDP charges delivery per MB)
             --strict  fail on any missing manuscript file (the full-book release build)
             --no-figures  skip the render_figures.py step

Pipeline:
  1. render figures (05-build/render_figures.py; unchanged figures are skipped)
  2. each manuscript file -> pandoc JSON (markdown, no automatic ids)
  3. Python assembles the book: Part pages (h1), chapters shifted to h2 and numbered
     "Chapter N. Title", appendices "Appendix X. Title", unique header ids
     (part-NN, chNN, chNN-section-slug, app-X, app-X-slug)
  4. pandoc JSON -> EPUB3 with 05-build/book.lua, kindle.css, highlight.theme, MathML,
     the cover, the metadata and the nav TOC (Parts > Chapters > sections)
  5. epubcheck; the build fails unless it reports 0 errors and 0 fatals
"""
import json, os, re, subprocess, sys, shutil, datetime, unicodedata
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "05-build"
OUT = BUILD / "out"
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return r


def slug(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9\s-]", "", t).strip().lower()
    return re.sub(r"[\s-]+", "-", t)[:48].strip("-") or "s"


def stringify(inlines):
    out = []
    for i in inlines:
        t = i.get("t")
        if t == "Str": out.append(i["c"])
        elif t in ("Space", "SoftBreak", "LineBreak"): out.append(" ")
        elif t == "Code": out.append(i["c"][1])
        elif t in ("Emph", "Strong", "SmallCaps", "Strikeout", "Underline", "Superscript", "Subscript"): out.append(stringify(i["c"]))
        elif t in ("Span", "Link", "Quoted"): out.append(stringify(i["c"][-1] if t == "Span" else i["c"][1] if t == "Link" else i["c"][1]))
    return "".join(out)


def to_json(md_path):
    r = sh(["pandoc", "-f", "markdown-auto_identifiers", "-t", "json", str(md_path)])
    if r.returncode != 0:
        sys.exit(f"pandoc could not read {md_path}:\n{r.stderr}")
    return json.loads(r.stdout)


def text_inlines(s):
    out = []
    for n, w in enumerate(s.split(" ")):
        if n: out.append({"t": "Space"})
        out.append({"t": "Str", "c": w})
    return out


def header(level, ident, inlines, classes=(), kv=()):
    return {"t": "Header", "c": [level, [ident, list(classes), [list(p) for p in kv]], inlines]}


class Assembler:
    def __init__(self):
        self.blocks, self.ids, self.meta = [], set(), None
        self.problems = []

    def uid(self, base):
        i, n = base, 2
        while i in self.ids:
            i = f"{base}-{n}"; n += 1
        self.ids.add(i)
        return i

    def add_file(self, path, shift=0, prefix=None, first_h1=None):
        """first_h1: (level, id, inlines) replaces the file's first H1 (chapter or appendix title)."""
        doc = to_json(path)
        if self.meta is None: self.meta = doc["meta"]
        replaced = False
        for b in doc["blocks"]:
            if b["t"] == "Header":
                lvl, (ident, classes, kv), inl = b["c"]
                if lvl == 1 and first_h1 and not replaced:
                    lvl, ident, inl = first_h1; replaced = True
                    b["c"] = [lvl, [self.uid(ident), classes, kv], inl]
                    self.blocks.append(b)
                    continue
                lvl = min(lvl + shift, 6)
                if not ident:
                    base = f"{prefix}-{slug(stringify(inl))}" if prefix else slug(stringify(inl))
                    ident = base
                b["c"] = [lvl, [self.uid(ident), classes, kv], inl]
            self.blocks.append(b)
        if first_h1 and not replaced:
            self.problems.append(f"{path}: no '# Title' line; the manifest title was used")
            lvl, ident, inl = first_h1
            self.blocks.insert(len(self.blocks) - len(doc["blocks"]), header(lvl, self.uid(ident), inl))


def load_manifest(p):
    m = yaml.safe_load(Path(p).read_text())
    m["_path"] = p
    return m


def write_metadata(m, workdir):
    year = str(m.get("year", datetime.date.today().year))
    meta = {
        "title": [{"type": "main", "text": m["title"]}, {"type": "subtitle", "text": m["subtitle"]}],
        "creator": [{"role": "author", "text": m["author"]}],
        "lang": m.get("language", "en-US"),
        "rights": m.get("rights", f"Copyright © {year} {m['author']}. All rights reserved."),
        "date": m.get("date", datetime.date.today().isoformat()),
        "identifier": [{"scheme": "UUID", "text": m["identifier"]}] if m.get("identifier") else None,
        "subject": m.get("subjects"),
        "description": m.get("description"),
        "belongs-to-collection": m.get("series"),
        "group-position": m.get("series_index"),
        "page-progression-direction": "ltr",
    }
    meta = {k: v for k, v in meta.items() if v is not None}
    (workdir / "metadata.yaml").write_text("---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "...\n")
    # Series: EPUB3 belongs-to-collection + group-position (above), which Calibre 5+ and Apple read.
    # calibre:series <meta name> is OPF2-only and fails epubcheck in EPUB3, so it is not written.
    # KDP takes the series from the KDP dashboard, not from the file.


def assemble(m, strict):
    A = Assembler()
    root = ROOT
    def need(rel):
        p = root / rel
        if not p.exists():
            msg = f"missing manuscript file {rel}"
            if strict: sys.exit(msg)
            print("skip ", msg); return None
        return p
    for rel in m.get("front", []):
        p = need(rel)
        if p: A.add_file(p, shift=0, prefix="front")
    for part in m.get("parts", []):
        pn = int(part["number"])
        pid = f"part-{pn:02d}"
        chapters = [c for c in part.get("chapters", []) if (root / c.get("file", f"02-manuscript/ch{int(c['number']):02d}.md")).exists() or strict]
        if not chapters and not part.get("always", False):
            continue
        title = text_inlines(f"Part {ROMAN[pn] if pn < len(ROMAN) else pn}: {part['title']}") if pn > 0 else text_inlines(part["title"])
        pf = part.get("file")
        if pf and (root / pf).exists():
            A.add_file(root / pf, shift=0, prefix=pid, first_h1=(1, pid, title))
        else:
            A.blocks.append(header(1, A.uid(pid), title, classes=["part"]))
        for ch in part.get("chapters", []):
            n = int(ch["number"])
            rel = ch.get("file", f"02-manuscript/ch{n:02d}.md")
            p = need(rel)
            if not p: continue
            cid = f"ch{n:02d}"
            label = f"Chapter {n}. {ch['title']}" if n > 0 else ch["title"]
            A.add_file(p, shift=1, prefix=cid, first_h1=(2, cid, text_inlines(label)))
    apps = [a for a in m.get("appendices", []) if (root / a.get("file", f"02-manuscript/appendices/app-{a['letter']}.md")).exists() or strict]
    if apps:
        A.blocks.append(header(1, A.uid("appendices"), text_inlines("Appendices"), classes=["part"]))
        for a in m["appendices"]:
            rel = a.get("file", f"02-manuscript/appendices/app-{a['letter']}.md")
            p = need(rel)
            if not p: continue
            aid = f"app-{a['letter']}"
            A.add_file(p, shift=1, prefix=aid, first_h1=(2, aid, text_inlines(f"Appendix {a['letter']}. {a['title']}")))
    for rel in m.get("back", []):
        p = need(rel)
        if p: A.add_file(p, shift=0, prefix="back")
    return A


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    man = Path(args[0]) if args else BUILD / "book.yaml"
    if not man.is_absolute(): man = (Path.cwd() / man).resolve()
    m = load_manifest(man)
    OUT.mkdir(parents=True, exist_ok=True)
    work = OUT / ("_work-" + man.stem); shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    out_epub = ROOT / m.get("output", f"05-build/out/{man.stem}.epub")
    (OUT / "filter-errors.txt").unlink(missing_ok=True)

    if "--no-figures" not in flags:
        chs = m.get("figure_dirs")
        r = subprocess.run([sys.executable, str(BUILD / "render_figures.py")] + (chs or []), cwd=ROOT)
        if r.returncode != 0: sys.exit("figure rendering failed; see 03-figures/out/render-report.md")

    write_metadata(m, work)
    A = assemble(m, "--strict" in flags)
    probe = json.loads(sh(["pandoc", "-f", "markdown", "-t", "json"], input="x").stdout)
    doc = {"pandoc-api-version": probe["pandoc-api-version"], "meta": {}, "blocks": A.blocks}
    (work / "book.json").write_text(json.dumps(doc))

    cover = ROOT / m.get("cover", "05-build/cover.jpg")
    cmd = ["pandoc", "-f", "json", "-t", "epub3", str(work / "book.json"),
           "--metadata-file", str(work / "metadata.yaml"),
           "--lua-filter", str(BUILD / "book.lua"),
           "--css", str(BUILD / "kindle.css"),
           "--syntax-highlighting", str(BUILD / "highlight.theme"),
           "--math-method=mathml", "--split-level=2", "--toc-depth=3",
           "--epub-title-page=true",
           "--resource-path", str(ROOT),
           "-o", str(out_epub)]
    if cover.exists(): cmd += ["--epub-cover-image", str(cover)]
    else: print("warn  no cover at", cover)
    if "--embed-fonts" in flags:
        for f in ["SourceSans3-Regular.otf", "SourceSans3-Bold.otf", "SourceSans3-It.otf", "JetBrainsMonoNL-Regular.ttf"]:
            fp = ROOT / "03-figures/fonts" / f
            if fp.exists(): cmd += ["--epub-embed-font", str(fp)]
    env = dict(os.environ, BOOK_ROOT=str(ROOT), BOOK_FULL="1" if man.stem == "book" else "0")
    r = sh(cmd, env=env, cwd=ROOT)
    sys.stderr.write(r.stderr)
    errfile = OUT / "filter-errors.txt"
    if r.returncode != 0 or errfile.exists():
        sys.exit("build failed" + (f": see {errfile}" if errfile.exists() else ""))
    for p in A.problems: print("warn ", p)
    print("built", out_epub.relative_to(ROOT), f"{out_epub.stat().st_size/1e6:.2f} MB")

    ec = sh(["epubcheck", "--json", str(work / "epubcheck.json"), str(out_epub)])
    rep = json.loads((work / "epubcheck.json").read_text())
    msgs = rep.get("messages", [])
    sev = {}
    for x in msgs: sev[x["severity"]] = sev.get(x["severity"], 0) + 1
    lines = [f"epubcheck {rep.get('checker', {}).get('checkerVersion', '')} on {out_epub.name}: " +
             ", ".join(f"{k.lower()} {v}" for k, v in sorted(sev.items())) if sev else
             f"epubcheck {rep.get('checker', {}).get('checkerVersion', '')} on {out_epub.name}: 0 errors, 0 warnings"]
    for x in msgs:
        loc = x.get("locations", [{}])[0]
        lines.append(f"  {x['severity']} {x['ID']} {loc.get('path','')}:{loc.get('line','')} {x['message']}")
    (OUT / f"epubcheck-{man.stem}.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    if sev.get("ERROR", 0) or sev.get("FATAL", 0):
        sys.exit(1)

    if "--azw3" in flags:
        azw = out_epub.with_suffix(".azw3")
        r = sh(["ebook-convert", str(out_epub), str(azw), "--output-profile", "kindle_pw3"],
               # Calibre must use Debian's lxml, not the pip one in /usr/local (libxml2 mismatch)
               env=dict(os.environ, QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox", PYTHONNOUSERSITE="1",
                        PYTHONPATH="/usr/lib/python3/dist-packages"))
        print(("converted " + str(azw.relative_to(ROOT))) if r.returncode == 0 else ("ebook-convert failed:\n" + r.stderr[-1500:]))


if __name__ == "__main__":
    main()
