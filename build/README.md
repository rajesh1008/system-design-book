# Production: System Design for Agentic AI

How the manuscript becomes a Kindle-ready EPUB3. Tool versions and known gaps are in `TOOLCHAIN.md`.
The figure style is in `03-figures/style.md`.

## Commands (run from /workspace/book)

| Command | Does |
|---|---|
| `make theme` | Regenerate every theme file from `03-figures/palette.json` |
| `make figures` | Render changed figures (`python3 05-build/render_figures.py [chNN ...] [--force] [--only fig-NN-M]`) |
| `make sample` | Build `05-build/out/sample.epub` (and `.azw3`) from `sample.yaml` |
| `make book` | Build `05-build/out/book.epub` from `book.yaml` (no embedded fonts: the series design uses the reader's fonts) |
| `make azw3` | The same plus a Calibre AZW3 proof copy |
| `make wordcount` | Per-chapter body and interview words, with a running total, into `05-build/out/wordcount.md` |

`build_epub.py [manifest] [--azw3] [--embed-fonts] [--strict] [--no-figures]` renders figures, assembles
the book and runs pandoc and EPUBCheck. It exits 1 on any filter error, any EPUBCheck ERROR or FATAL,
or, with `--strict`, any missing manuscript file. The EPUBCheck report goes to
`05-build/out/epubcheck-<stem>.txt` and the figure report to `03-figures/out/render-report.md`.
`wordcount.py [--sample] [--write] [--floor N]` counts words.

## Series styling

The book uses the series house style of the FDE Handbook (same series): navy, teal and amber with light
tints, a teal chapter-opener block with a large numeral, cream Part pages, tinted boxes with a coloured
label strip and a round icon, a navy-tinted interview question line, label bars on code ("Python",
"Shell", ... or "Output" for ```text blocks) and zebra tables. Dark text on light tints throughout, so
it reads on e-ink greyscale. The pieces:

- `kindle.css`: every colour and rule (palette in its header comment). `strong` keeps the body font and size.
- `highlight.theme`: syntax colours (keywords plum, strings rust, comments green italic).
- `book.lua`: box label strips and icons, `div.q` question lines, code label bars, the Scoreboard box,
  decision-record boxes (`> **DR-...**`, `> Decision. ...`, `::: note` "Decision record ..."), pull quotes
  (a one-sentence block quote). Add `{.nolabel}` to a code fence to drop its label bar. Hooks with no use
  yet: `::: key-takeaways`, `::: epigraph`, `::: warning`.
- `build_epub.py`: chapter, appendix and Part headings as label / numeral / title spans (the nav still reads
  "Chapter N. Title"); runs `make_icons.py`, which draws the icons into `out/_icons/` (needs cairosvg).

## File layout

    02-manuscript/front/      copyright.md, dedication.md, preface.md, how-to-read.md
    02-manuscript/parts/      part-NN.md   (Part opener text; its '# ' line is replaced by the manifest title)
    02-manuscript/chNN.md     one file per chapter, NN = 01..48
    02-manuscript/appendices/ app-X.md     (A..O)
    02-manuscript/back/       about-the-author.md
    02-manuscript/_sample/    the production sample (ch00, part-00)
    03-figures/src/chNN/      figure sources fig-NN-M.{dot,puml,mmd,py,svg}
    03-figures/out/chNN/      rendered fig-NN-M.{png,svg,pdf} (never edit)
    03-figures/alt.md         alt text, one line per figure
    05-build/book.yaml        the manifest: metadata, Parts, chapter titles and order

## Headings

- `# Title` once, at the top of the file. The build replaces it with the manifest title, so
  chapters become `Chapter N. Title` and appendices `Appendix X. Title`, in title case.
- `## Section` for sections, in sentence case. They appear in the TOC and get ids `chNN-slug`.
- `### Subsection`, in sentence case, appears in the body only.
- The last two sections of every chapter are `## Scoreboard` and `## Interview Questions and Answers {.interview}`.
- Front-matter files that should stay out of the TOC use `{.unnumbered .unlisted}`.

## Boxes (fenced divs; the label is added by the build, never typed)

| Write | Renders as |
|---|---|
| `::: from-the-field` (alias `field`) | From the Field |
| `::: decision-maker` (alias `decision`) | For the Decision-Maker |
| `::: recent-research` (alias `research`) | Recent Research |
| `::: {.experts-disagree title="The question"}` (alias `disagree`) | Where Experts Disagree, plus the question |
| `::: try-it-yourself` (alias `try`) | Try It Yourself |
| `::: {.sidebar title="Keys, tokens and nonces"}` | A named sidebar (title required) |
| `::: warning` | Warning |

Close each box with `:::`. A box inside a `.qa` needs fewer colons than its parent (`::::` outside, `:::` inside).

## Interview Questions and Answers

    ## Interview Questions and Answers {.interview}

    :::: {.qa type="design" round="system-design" level="staff" tags="idempotency"}
    **3. The question, in one sentence?**

    The model answer, in prose.

    ::: weak
    A weak answer says ... and why that fails.
    :::
    ::::

The `.qa` attributes stay in the source for the interview bank and are not rendered. The build adds the
"A weak answer" label only if the text does not already start with it. Use 12 to 20 questions per chapter;
`wordcount.py` checks the count.

## Figures

- Source `03-figures/src/chNN/fig-NN-M.<ext>`. Figures are drawn from source, never generated or pasted.
- In the text, reference the figure first and place it after:

      @fig-02-3 shows the chain from proposal to verified outcome.

      ![The evidence chain for one rebooking](fig-02-3){#fig-02-3}

  The build resolves the PNG, prepends "Figure 2.3." to the caption and takes the alt text from `alt.md`.
  Captions use sentence case, have no period and are not drawn in the figure.
- Add `fig-02-3: One sentence.` to `03-figures/alt.md`. The build fails if it is missing.
- Re-render and read `03-figures/out/render-report.md`. A fail must be fixed. A grayscale "review"
  means you open `03-figures/out/_greyscale/fig-NN-M.png` and confirm that shape, border or label
  carries the distinction as well as color.

## Tables, code, math, cross-references

- Tables are pipe tables with a caption line after them: `: Caption in sentence case {#tbl-NN-M}`.
  The build prepends "Table N.M.". Keep to five columns at most; they wrap on a 6-inch screen.
- Code uses fenced blocks with a language (` ```python `). Lines wrap; keep them under about 70 characters.
- Math uses `$...$` or `$$...$$`, output as MathML. Simple relations can stay as plain text.
- Cross-references: `@fig-NN-M`, `@tbl-NN-M`, `@chNN` and `@app-X` become links with the correct label.

## House rules the build does not check

American spelling (en-US). No em dashes, exclamation marks or emoji. Use sentence case everywhere
except the titles of Chapters, Parts and appendices. Lakeshore and every named person are fictional.

## Metadata

`book.yaml` holds the title, subtitle, author (Rajesh Ranjan Mahapatra), language en-US, the series
"AI at Work (Practitioner Playbooks)" with `series_index` 3, the identifier and the cover. The cover
`05-build/cover.jpg` (1600x2560) is a typographic placeholder made by `make_cover.py`; replace it with
the final artwork at the same size. Do not run `sync_public.sh` as part of a build; it pushes to a
public repository.
