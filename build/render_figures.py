#!/usr/bin/env python3
"""Render every figure source to Kindle-ready PNG plus SVG and PDF, validate, and report.

    python3 05-build/render_figures.py              # all chapters, only what changed
    python3 05-build/render_figures.py ch02 ch03    # some chapters
    python3 05-build/render_figures.py --force      # re-render everything
    python3 05-build/render_figures.py --only fig-02-3

Sources: 03-figures/src/chNN/fig-NN-M.{dot,puml,mmd,py,svg}   (files starting with '_' are ignored)
Outputs: 03-figures/out/chNN/fig-NN-M.{png,svg,pdf}
Report:  03-figures/out/render-report.md and render-report.json; greyscale previews in out/_greyscale/

PNG spec enforced (from palette.json 'kindle'): long side 1600-4000 px (target 2400), 300 ppi
metadata, sRGB with embedded ICC profile, RGB with no alpha (flattened onto white), < 5 MB,
width:height no wider than 3:2 (fail), taller than 1:2 warns. Effective smallest text at the
4.5 in print width must be >= 9 pt; more than 40 words of labels warns. Exit code 1 on any fail.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageCms

sys.path.insert(0, str(Path(__file__).resolve().parent))
import greyscale_check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "03-figures"
SRC, OUT = FIG / "src", FIG / "out"
PAL = json.loads((FIG / "palette.json").read_text())
K = PAL["kindle"]
PLANTUML_JAR = os.environ.get("PLANTUML_JAR", "/opt/plantuml/plantuml.jar")
THEME_FILES = [FIG / "palette.json", FIG / "graphviz" / "book.gv", FIG / "graphviz" / "book.gvpr",
               FIG / "plantuml-theme.puml", FIG / "mermaid" / "config.json", FIG / "mermaid" / "classes.mmd",
               FIG / "book.mplstyle", FIG / "figlib.py", Path(__file__)]
EXTS = (".dot", ".gv", ".puml", ".mmd", ".py", ".svg")
ENV = dict(os.environ, FONTCONFIG_FILE=str(FIG / "fonts.conf"), PYTHONPATH=str(FIG))
SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
PRINT_W_PT = PAL["print_text_width_in"] * 72
PRINT_H_PT = PAL["print_text_height_in"] * 72   # a tall figure is limited by page height instead
NAME_RE = re.compile(r"^fig-\d{2}-\d+[a-z]?$|^fig-[A-O]-\d+[a-z]?$")


class RenderError(Exception):
    pass


def run(cmd, stdin=None, cwd=None, timeout=180):
    p = subprocess.run(cmd, input=stdin, cwd=cwd, env=ENV, capture_output=True, timeout=timeout)
    if p.returncode != 0:
        raise RenderError(f"{cmd[0]} failed ({p.returncode}): {p.stderr.decode(errors='replace')[-1500:]}")
    return p.stdout


def svg_box(svg_text):
    """(width, height) in the SVG's own user units."""
    m = re.search(r'viewBox="\s*([-\d.]+)[ ,]+([-\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)', svg_text)
    if m:
        return float(m.group(3)), float(m.group(4))
    w = re.search(r'<svg[^>]*\bwidth="([\d.]+)', svg_text)
    h = re.search(r'<svg[^>]*\bheight="([\d.]+)', svg_text)
    if w and h:
        return float(w.group(1)), float(h.group(1))
    raise RenderError("cannot read SVG size")


def svg_fonts_and_words(svg_text):
    # Inline sizes always count. Rules in <style> count only when some selector's classes are all used,
    # because mermaid ships legacy CSS (e.g. g.stateGroup text 10px) that styles nothing in the drawing.
    styles = re.findall(r"<style[^>]*>(.*?)</style>", svg_text, flags=re.S)
    body = re.sub(r"<style[^>]*>.*?</style>", "", svg_text, flags=re.S)
    used = set()
    for c in re.findall(r'class="([^"]*)"', body):
        used.update(c.split())
    sizes = [float(x) for x in re.findall(r'font-size="([\d.]+)', body)]
    sizes += [float(x) for x in re.findall(r'font-size:\s*([\d.]+)px', body)]
    for css in styles:
        for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            m = re.search(r"font-size:\s*([\d.]+)px", decl)
            if not m:
                continue
            for part in sel.split(","):
                classes = re.findall(r"\.([\w-]+)", part)
                if all(c in used for c in classes):
                    sizes.append(float(m.group(1))); break
    texts = re.findall(r"<text[^>]*>(.*?)</text>", svg_text, flags=re.S)
    words = sum(len(re.sub(r"<[^>]+>", " ", t).split()) for t in texts)
    return (min(sizes) if sizes else None), words


def print_scale(w, h):
    """How much the figure is shrunk to sit in the 4.5 in x 6.5 in print/text area (never enlarged)."""
    return min(1.0, PRINT_W_PT / w, PRINT_H_PT / h)


def rasterise_svg(svg_path, png_path):
    svg_text = svg_path.read_text()
    w, h = svg_box(svg_text)
    if w >= h:
        run(["rsvg-convert", "-w", str(K["target_long_px"]), "-b", "white", str(svg_path), "-o", str(png_path)])
    else:
        run(["rsvg-convert", "-h", str(K["target_long_px"]), "-b", "white", str(svg_path), "-o", str(png_path)])


def svg_to_pdf(svg_path, pdf_path):
    run(["rsvg-convert", "-f", "pdf", "-b", "white", str(svg_path), "-o", str(pdf_path)])


# ---------------------------------------------------------------- per-tool renderers
def expand_includes(text, base):
    def rep(m):
        name = m.group(1)
        for d in (base, FIG / "graphviz"):
            if (d / name).exists():
                return expand_includes((d / name).read_text(), d)
        raise RenderError(f"#include {name} not found")
    return re.sub(r'^\s*#include\s+"([^"]+)"\s*$', rep, text, flags=re.M)


def render_dot(src, base):
    text = expand_includes(src.read_text(), src.parent)
    if "book.gv" not in src.read_text():
        raise RenderError('missing #include "book.gv" (house style)')
    styled = run(["gvpr", "-c", "-f", str(FIG / "graphviz" / "book.gvpr")], stdin=text.encode())
    tool = "neato" if re.search(r"^\s*//\s*layout\s*=\s*neato", text, re.M) else "dot"
    Path(base + ".svg").write_bytes(run([tool, "-Tsvg"], stdin=styled))
    rasterise_svg(Path(base + ".svg"), Path(base + ".raw.png"))
    svg_to_pdf(Path(base + ".svg"), Path(base + ".pdf"))


def render_puml(src, base):
    if "plantuml-theme.puml" not in src.read_text():
        raise RenderError("missing !include plantuml-theme.puml (house style)")
    svg = run(["java", "-Djava.awt.headless=true", f"-Dplantuml.include.path={FIG}", "-jar", PLANTUML_JAR,
               "-tsvg", "-pipe", "-charset", "UTF-8"], stdin=src.read_bytes())
    s = svg.decode("utf-8", errors="replace")
    for bad in ("Syntax Error", "is deprecated", "Cannot include", "cannot include", "Dot executable"):
        if bad in s:
            raise RenderError(f"PlantUML reported '{bad}' inside the diagram; fix the source")
    Path(base + ".svg").write_text(s)
    rasterise_svg(Path(base + ".svg"), Path(base + ".raw.png"))
    svg_to_pdf(Path(base + ".svg"), Path(base + ".pdf"))


def render_mmd(src, base):
    text = src.read_text()
    if "%% @classes" in text:
        text += "\n" + (FIG / "mermaid" / "classes.mmd").read_text()
    tmp = Path(base + ".src.mmd")
    tmp.write_text(text)
    common = ["mmdc", "-p", str(FIG / "mermaid" / "puppeteer.json"), "-c", str(FIG / "mermaid" / "config.json"),
              "-b", "white", "-q", "-i", str(tmp)]
    try:
        run(common + ["-o", base + ".svg"])
        w, h = svg_box(Path(base + ".svg").read_text())
        scale = max(1.0, K["target_long_px"] / max(w, h))
        # Chromium rasterises mermaid text correctly (rsvg drops inter-word spaces in mermaid tspans)
        run(common + ["-o", base + ".raw.png", "-s", f"{scale:.3f}"])
        run(common + ["-o", base + ".pdf"])   # mmdc 12 fits the PDF to the diagram by default
    finally:
        tmp.unlink(missing_ok=True)


def render_py(src, base):
    env = dict(ENV, FIG_OUT=base, MPLCONFIGDIR=str(Path.home() / ".cache" / "mpl-book"))
    p = subprocess.run([sys.executable, str(src)], cwd=src.parent, env=env, capture_output=True, timeout=300)
    if p.returncode != 0:
        raise RenderError(f"python failed: {p.stderr.decode(errors='replace')[-1500:]}")
    for ext in (".svg", ".pdf", ".raw.png"):
        if not Path(base + ext).exists():
            raise RenderError(f"script did not write {ext}; call figlib.save(fig)")


def render_svg(src, base):
    shutil.copyfile(src, base + ".svg")
    rasterise_svg(Path(base + ".svg"), Path(base + ".raw.png"))
    svg_to_pdf(Path(base + ".svg"), Path(base + ".pdf"))


RENDERERS = {".dot": render_dot, ".gv": render_dot, ".puml": render_puml, ".mmd": render_mmd,
             ".py": render_py, ".svg": render_svg}


# ---------------------------------------------------------------- Kindle finishing + checks
def finish_png(raw, final):
    im = Image.open(raw)
    im.load()
    if im.mode in ("RGBA", "LA", "P", "PA") or "transparency" in im.info:
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    im = im.convert("RGB")
    long_side = max(im.size)
    if long_side > K["max_long_px"]:
        f = K["max_long_px"] / long_side
        im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
    elif long_side < K["min_long_px"]:
        f = K["target_long_px"] / long_side
        im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True, dpi=(K["ppi"], K["ppi"]), icc_profile=SRGB)
    if buf.tell() > K["max_bytes"]:   # palette-quantise flat-colour art; still RGB on decode
        im.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(buf := io.BytesIO(), "PNG", optimize=True,
                                                                       dpi=(K["ppi"], K["ppi"]), icc_profile=SRGB)
    Path(final).write_bytes(buf.getvalue())
    Path(raw).unlink(missing_ok=True)


def validate(name, base, kind):
    fails, warns = [], []
    png = Path(base + ".png")
    im = Image.open(png)
    w, h = im.size
    size = png.stat().st_size
    if im.mode != "RGB":
        fails.append(f"mode {im.mode}, not RGB")
    if not (K["min_long_px"] <= max(w, h) <= K["max_long_px"]):
        fails.append(f"long side {max(w, h)} px outside {K['min_long_px']}-{K['max_long_px']}")
    if w / h > K["max_aspect_w_over_h"] + 0.01:
        fails.append(f"aspect {w / h:.2f}:1 is wider than 3:2; stack the layout vertically or split it")
    if h / w > 2.0:
        warns.append(f"very tall ({h / w:.2f}:1); on a 6 in screen text will shrink")
    if size > K["max_bytes"]:
        fails.append(f"{size / 1e6:.1f} MB > 5 MB")
    dpi = im.info.get("dpi", (0, 0))
    if round(dpi[0]) != K["ppi"]:
        fails.append(f"dpi metadata {dpi}")
    if "icc_profile" not in im.info:
        fails.append("no sRGB ICC profile")
    svg_text = Path(base + ".svg").read_text(errors="replace")
    sw, sh = svg_box(svg_text)
    min_font, words = svg_fonts_and_words(svg_text)
    if kind == ".py":
        meta = json.loads(Path(base + ".meta.json").read_text())
        min_font, words = meta["min_font_pt"], meta["label_words"]
    eff = None
    if min_font:
        eff = min_font * print_scale(sw, sh)
        if eff < K["min_font_pt_at_print"] - 0.05:
            fails.append(f"smallest text is {eff:.1f} pt at print width (needs >= 9 pt): "
                         f"fewer nodes, shorter labels, or a taller layout")
    if words > 40:
        warns.append(f"{words} words of labels (budget about 40); move explanation into the text")
    grey = greyscale_check.check(png)
    if grey["verdict"] != "ok":
        warns.append("greyscale: %d colour pairs are close in grey; confirm shape, border, label or line style also differs"
                     % len(grey["close_pairs"]))
    return {"figure": name, "tool": kind.lstrip("."), "png": str(png.relative_to(ROOT)), "px": [w, h],
            "aspect": round(w / h, 3), "bytes": size, "min_font_pt_at_print": round(eff, 1) if eff else None,
            "label_words": words, "greyscale": grey["verdict"], "greyscale_preview": grey["preview"],
            "fails": fails, "warns": warns, "status": "fail" if fails else ("warn" if warns else "ok")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapters", nargs="*", help="e.g. ch00 ch02 (default: all)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", help="a single figure name, e.g. fig-02-3")
    args = ap.parse_args()
    theme_mtime = max(p.stat().st_mtime for p in THEME_FILES if p.exists())
    chapters = args.chapters or sorted(d.name for d in SRC.iterdir() if d.is_dir())
    results, t0 = [], time.time()
    for ch in chapters:
        for src in sorted((SRC / ch).glob("*")):
            if src.suffix not in EXTS or src.name.startswith("_") or src.name.startswith("."):
                continue
            name = src.stem
            if args.only and name != args.only:
                continue
            outdir = OUT / ch
            outdir.mkdir(parents=True, exist_ok=True)
            base = str(outdir / name)
            entry = {"figure": name, "chapter": ch, "source": str(src.relative_to(ROOT))}
            if not NAME_RE.match(name):
                entry.update(status="fail", fails=[f"name '{name}' must be fig-NN-M (chapter, sequence)"], warns=[])
                results.append(entry)
                continue
            png = Path(base + ".png")
            if (not args.force and png.exists()
                    and png.stat().st_mtime > max(src.stat().st_mtime, theme_mtime)):
                try:
                    entry.update(validate(name, base, src.suffix))
                    entry["rendered"] = "cached"
                except Exception as e:  # noqa: BLE001
                    entry.update(status="fail", fails=[str(e)], warns=[])
                results.append(entry)
                continue
            try:
                RENDERERS[src.suffix](src, base)
                finish_png(base + ".raw.png", base + ".png")
                entry.update(validate(name, base, src.suffix))
                entry["rendered"] = "now"
            except (RenderError, subprocess.TimeoutExpired, OSError) as e:
                entry.update(status="fail", fails=[str(e)], warns=[])
            results.append(entry)
            print(f"{entry['status']:5s} {ch}/{name}  " + "; ".join(entry.get("fails", []) + entry.get("warns", [])))
    write_report(results, time.time() - t0)
    nfail = sum(r["status"] == "fail" for r in results)
    print(f"{len(results)} figures, {nfail} failed. Report: 03-figures/out/render-report.md")
    sys.exit(1 if nfail else 0)


def write_report(results, secs):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "render-report.json").write_text(json.dumps(results, indent=2))
    alt = FIG / "alt.md"
    alts = set(re.findall(r"^(fig-[\w-]+):", alt.read_text(), re.M)) if alt.exists() else set()
    lines = ["# Figure render report", "",
             f"Generated {__import__('datetime').datetime.now(__import__('zoneinfo').ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M')} IST in {secs:.1f} s. "
             f"{len(results)} figures; {sum(r['status'] == 'fail' for r in results)} fail, "
             f"{sum(r['status'] == 'warn' for r in results)} warn.", "",
             "| Figure | Tool | Status | Pixels | Aspect | KB | Min text at print (pt) | Label words | Greyscale | Alt text | Notes |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        px = "x".join(map(str, r.get("px", []))) or "-"
        notes = "; ".join(r.get("fails", []) + r.get("warns", [])).replace("|", "/").replace("\n", " ")
        lines.append(f"| {r['figure']} | {r.get('tool', '-')} | {r['status']} | {px} | {r.get('aspect', '-')} | "
                     f"{round(r.get('bytes', 0) / 1024)} | {r.get('min_font_pt_at_print', '-')} | {r.get('label_words', '-')} | "
                     f"{r.get('greyscale', '-')} | {'yes' if r['figure'] in alts else 'MISSING'} | {notes} |")
    (OUT / "render-report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
