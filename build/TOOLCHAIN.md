# Toolchain

Verified on November 2, 2026 (IST) on the shared box: Debian 13.7 (trixie), x86_64. All tools run
headless. Re-check with `make versions`.

| Tool | Version | Path | Used for |
|---|---|---|---|
| Pandoc | 3.13 | /usr/bin/pandoc | Markdown to EPUB3 |
| Graphviz | 2.42.4 | /usr/bin/dot, gvpr | HLD, infra, deployment figures |
| OpenJDK | 21.0.13 | /usr/bin/java | PlantUML runtime |
| PlantUML | 1.2026.9 | /opt/plantuml/plantuml.jar (env PLANTUML_JAR overrides) | Sequence and UML figures |
| Mermaid CLI (mmdc) | 12.0.0 | /usr/local/bin/mmdc | Fallback state and flow figures |
| Chromium | 156.0.8078.73 | /usr/bin/chromium | Mermaid rendering (puppeteer) and XHTML previews |
| Node.js | 24.22.1 | | mmdc runtime |
| EPUBCheck | 5.4.0 | /usr/local/bin/epubcheck (/opt/epubcheck) | Validation inside every build |
| Calibre ebook-convert | 8.5.0 | /usr/bin/ebook-convert | Optional AZW3 proof copy |
| rsvg-convert | 2.60.0 | /usr/bin/rsvg-convert | SVG to PNG and PDF |
| ImageMagick | 7.1.1-43 | magick | Ad hoc inspection only |
| Python | 3.13.5 | /usr/bin/python3 | Build scripts |
| matplotlib | 3.11.2 | pip | Charts |
| Pillow | 13.0.0 | pip | PNG normalization, ICC, checks |
| cairosvg | 2.9.1 | pip | SVG fallback renderer |
| numpy | 2.5.4 | pip | Charts, grayscale check |
| PyYAML | 6.0.3 | pip | Build manifests |

Fonts are installed in fontconfig and vendored, with their licenses, in `03-figures/fonts/`:
Source Sans 3 (labels and body), JetBrains Mono NL (code), Noto Sans and Noto Sans Mono (fallbacks).
All are SIL OFL, so embedding them in the EPUB is allowed (`--embed-fonts`).

## Known gaps and workarounds

- **Kindle Previewer has no Linux build.** Substitutes: EPUBCheck with 0 errors, the grayscale
  previews in `03-figures/out/_greyscale/`, Chromium screenshots of the XHTML at 600 px width, and the
  Calibre AZW3 (`kindle_pw3` profile). Run Kindle Previewer 3 on Windows or macOS on the final
  EPUB before KDP upload.
- **Calibre and pip lxml clash.** The user-site lxml / html5-parser are built against a different
  libxml2 than Debian's calibre. build_epub.py runs ebook-convert with `PYTHONNOUSERSITE=1` and
  `PYTHONPATH=/usr/lib/python3/dist-packages`. Do the same when calling it by hand.
- **mmdc 12 dropped `--pdfFit`.** PDFs already fit the diagram, so the flag was removed.
- **Mermaid styling is approximate.** Corners are forced to 2 px and borders to gray dark through
  themeCSS, but label alignment and edge-label backgrounds follow Mermaid's own layout. Use PlantUML for book
  figures and keep Mermaid for drafts.
- **Mermaid legacy CSS.** Mermaid ships unused rules such as `g.stateGroup text{font-size:10px}`. The
  font-size check ignores rules whose selectors match no element.
- **calibre:series metadata fails EPUBCheck in EPUB3.** The series is carried as
  `belongs-to-collection` with `group-position`. KDP takes the series from its dashboard.
- **Pandoc `--mathml` is deprecated.** Use `--math-method=mathml`.
- **Chromium wrapper warning.** `/usr/bin/chromium` prints `[: ... unexpected operator`. This is harmless.
- **apt.** Early installs needed the box's proxy settings and some package version adjustments. Pandoc
  and EPUBCheck are upstream releases rather than Debian's older packages.

## Restore of November 9, 2026 (IST)

A box image refresh removed every apt-installed tool (make, rsync, Graphviz, OpenJDK, librsvg2-bin,
ImageMagick, Chromium, Calibre) along with the Debian package lists and `/opt/plantuml`. Pandoc,
EPUBCheck (`/opt/epubcheck`), Node, mmdc, the pip packages, and the fonts survived.

- **Why apt failed.** Direct HTTP and HTTPS to deb.debian.org through the transparent egress gateway
  (198.18.0.1) returned `500 Internal Server Error` and TLS EOFs to apt, so `apt-get update` fetched no
  Debian lists and every install said "Unable to locate package". The box's egress proxy at
  `127.0.0.1:8791` (`SAND_EGRESS_TUNNEL_PROXY_ADDR`) works. The fix is
  `/etc/apt/apt.conf.d/80box-egress-proxy`:
  `Acquire::http::Proxy "http://127.0.0.1:8791";` and the same for `Acquire::https::Proxy`.
  If the image refresh wipes that file again, recreate it, then `sudo apt-get update`.
- **apt packages.** `sudo apt-get install -y --no-install-recommends make rsync graphviz librsvg2-bin
  openjdk-21-jre-headless imagemagick chromium fontconfig`, then `sudo apt-get install -y calibre`.
  The versions match the table above.
- **PlantUML.** The official release jar, from
  `https://github.com/plantuml/plantuml/releases/download/v1.2026.9/plantuml-1.2026.9.jar`, is installed
  as `/opt/plantuml/plantuml.jar`. A wrapper at `/usr/local/bin/plantuml` runs
  `java -Djava.awt.headless=true -jar ${PLANTUML_JAR:-/opt/plantuml/plantuml.jar}`.
- **Check.** Run `which make rsync dot gvpr plantuml java rsvg-convert ebook-convert` and `make versions`,
  then build one chapter with `make chapter CH=NN`. It should report 0 failed figures and 0 epubcheck errors.
