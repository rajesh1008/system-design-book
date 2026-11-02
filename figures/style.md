# Figure style: System Design for Agentic AI

One palette, one typeface, one stroke system for every figure in the book, whatever tool draws it.
The single source of truth is `03-figures/palette.json`. After editing it, run
`python3 05-build/gen_theme.py`. That script regenerates `book.mplstyle`, `graphviz/book.gv`,
`graphviz/book.gvpr`, `plantuml-theme.puml`, `mermaid/config.json` and `mermaid/classes.mmd`.
Never hand-edit colours in those generated files or in a figure source; use the tokens below.

## 1. Palette and roles

The hues and roles follow Series Operating Manual section 9 and Book prompt Part C. Teal, amber, green and coral are deepened
from the series hexes so that strokes and labels clear 4.5:1 on white (3:1 for the amber stroke).
`palette-contrast.md` holds the measured ratios.

| Token | Name | Stroke | Fill | Series hex | Means |
|---|---|---|---|---|---|
| `model` | Navy | #1F2A44 | #1F2A44 (white text) | #1F2A44 | Models, inference, the agent loop, the harness |
| `ops` | Teal | #0F766E | #D5ECE9 | #0F9D8A | Lakeshore itineraries, queues, tools, services, operations |
| `policy` | Amber | #B7791F (text #8A5A12) | #FBEBC8 | #E0A100 | Permission, policy, approval tiers, budgets, stop conditions |
| `evidence` | Slate blue | #4F6D9A | #E1E7F0 | #4F6D9A | The chain record, the trail, evidence, traces |
| `org` | Grey | #6B7280 | #FFFFFF | none | People, the organisation, customers, auditors, regulators |
| `knowledge` | Plum (accent) | #7B4B94 | #ECE1F2 | #7B4B94 | Knowledge plane: retrieval, semantic layer, context, memory |
| `verified` | Green (accent) | #2F7A3E | #DCEEDD | #3A9D5D | Verified outcome, a passed gate, a check by something that did not act |
| `fail` | Coral red (accent) | #C0392B | #F8DDD9 | #D64545 | Failure, denial, attack, incident, the duplicate effect |

Neutrals: ink #1A1A1A (all text and the emphasis arrow), grey dark #4B5563 (default borders and
arrows), grey light #D9DCE1 (rules, gridlines), white background.

Rules:
- At most four colour tokens plus neutrals in a figure. The exception is a plane map (HLD or overview), which may show each plane once in its own colour.
- A colour always means the same thing across the book. Do not use navy for "important" or coral for "highlight".
- Colour is never the only carrier of meaning. Every colour distinction is repeated by a label, a
  shape (cylinder for stores, double border for gates), a border style (dashed for external,
  dotted for the trail), a line style or a direct label. The greyscale check enforces a review.

## 2. Encodings beyond colour

| Meaning | Encoding |
|---|---|
| Data store, ledger, record | Cylinder (`store`) |
| Gate, check, approval point | Double border (`gate`) |
| Outside our control (vendor, airline, partner) | Dashed border (`external`) |
| Person or group | Grey border, white fill (`human`) |
| Annotation | No border, italic (`note`) |
| Code or identifier label | JetBrains Mono (`code`) |
| Data flow | 0.75 pt solid |
| Control flow | 1.5 pt solid |
| The one path to notice | 2.5 pt ink (`emphasis`), at most one per figure |
| Asynchronous | Dashed (`async`) |
| Trail or evidence write | Dotted slate blue (`trail`) |
| Failure path | Coral, solid, labelled (`fail`) |

## 3. Typography

- Labels: Source Sans 3, 11 pt at print width (4.5 in); small 9.5 pt; never below 9 pt after scaling.
- Code: JetBrains Mono NL 10 pt. Fallbacks: Noto Sans, Noto Sans Mono. All are vendored in `03-figures/fonts/`.
- Sentence case for every label and in-figure title. No full stops on labels. At most about 40
  label words per figure; explanation belongs in the text.
- Captions and figure numbers are not drawn in the figure; they live in the manuscript.

## 4. Shape and stroke

- Strokes 0.75 / 1.5 / 2.5 pt. One arrowhead style (filled normal, small).
- Square corners or 2 pt radius. Never pills, never fully rounded boxes.
- White background. No shadows, gradients, transparency, 3D, clip art, icons-as-decoration or emoji.
- Left-to-right or top-to-bottom reading order, stated in a comment at the top of the source.

## 5. Reject list

A figure is redrawn if it has: colour as the only distinction;
text under 9 pt at print; more than one emphasis path; more than four colour tokens outside a plane map; a legend where direct labels would fit;
a wider-than-3:2 shape; a drawn caption; title case labels; pills, shadows or gradients;
generated (non-source) artwork.

## 6. Kindle output spec (enforced by `05-build/render_figures.py`)

PNG, 300 ppi metadata, long side 1600 to 4000 px (target 2400), sRGB with ICC, RGB without alpha,
under 5 MB, width:height no wider than 3:2 (fail), taller than 1:2 warns. SVG and PDF are kept
alongside for print.

## 7. Per-tool usage

Sources live in `03-figures/src/chNN/fig-NN-M.<ext>`; files starting with `_` are ignored.

Graphviz (`.dot`), for HLD, infra, deployment and component maps:

    digraph x {
    #include "book.gv"
      a [label="Agent loop", class="model"];
      l [label="Effect\nledger", class="evidence store"];
      subgraph cluster_c { label="Control plane"; class="plane-policy"; ... }
      a -> l [class="trail"];
    }

Node tokens are the colour tokens plus modifiers `store gate external note code human`. Edge tokens are
`data control emphasis async trail fail verified policy`. Cluster tokens are `plane-<colour>`.

PlantUML (`.puml`), for sequence, class, component, state, activity and deployment diagrams:

    @startuml
    !include plantuml-theme.puml
    participant "Policy\nengine" as P <<policy>>
    T -[$FAIL]-> A : timeout
    @enduml

Stereotypes are `<<model>> <<ops>> <<policy>> <<evidence>> <<org>> <<knowledge>> <<verified>> <<fail>>`.
Arrow colours are `$FAIL $POLICY $TRAIL $VERIFIED $EMPH`, and the raw colours are `$C_<TOKEN>`.
Stereotype labels are hidden.

Mermaid (`.mmd`), a fallback for quick state and flow diagrams; prefer PlantUML for the book:

    %% @classes
    stateDiagram-v2
      Permitted:::policy

`%% @classes` pulls in the generated classDefs (the colour tokens plus `gate external`).

Matplotlib (`.py`), for charts:

    import figlib as fl
    fig, ax = fl.figure()
    ax.plot(x, y, color=fl.C["ops"], marker=fl.MARKERS[0], ls=fl.LINESTYLES[0])
    fl.label_line(ax, x[-1], y[-1], "with keys", color=fl.LABEL["ops"])
    fl.save(fig)

Use direct labels rather than legends. Every series also differs by marker, line style or hatch.
Use `fl.LABEL[token]` for coloured text.

Hand-written SVG (`.svg`) is accepted for one-off schematics. Use palette hexes and Source Sans 3 only.

## 8. Alt text

One sentence per figure in `03-figures/alt.md`, formatted `fig-NN-M: sentence.` The sentence says what the figure
shows and the one thing to notice, not the colours.
