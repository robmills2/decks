#!/usr/bin/env python3
"""Build a page of decks from a TSV of decks and their description files.

Three pages are built with this script, and they share its look:

    python3 build.py precons/decks.tsv precons/index.html          the precon page
    python3 build.py constructed/decks.tsv constructed/index.html  the constructed decks
    python3 build.py --home index.html                             the top page, linking both

A TSV with a set_code column makes the precon page; one with a bracket
column makes the constructed decks page. The rest of this note is about
the precon page; the constructed decks page is described above
DECK_SECTIONS below, and the top page above HOME_CSS.

Real: deck names, commanders, colors, each commander's card image (linked
from Scryfall, filled in by images.py), the Archidekt links in REAL_LINKS
below, and the description of every deck that has a file in descriptions/.
Placeholder: every other description, and every other Archidekt link.

A deck's description file is precons/descriptions/<name>.md, where <name>
is the deck's name in lower case with hyphens between the words, such as
precons/descriptions/federation-fleet.md. It has a Themes line, then the page's
three headings, each with its text under it:

    Themes: First theme, Second theme, Third theme

    ## What it wants to do

    A paragraph. A blank line starts a new one.

    ## The commander

    - Bullets go one per line, starting with a dash.

    ## Standout mechanic

    Links are written [the words to show](https://the.address).
    **Two asterisks** make bold, and *one asterisk* makes italics.

Nothing else in Markdown is understood; it shows on the page as typed.
The build stops without writing anything, and names the file, if a file
matches no deck, has a heading it doesn't know, leaves a part out, has
a link it can't read, or has an asterisk that doesn't open and close
bold or italics.

Usage: python3 build.py <decks TSV> <page to write>
       python3 build.py --home <page to write>
"""
import csv
import html
import re
import sys
import unicodedata
from itertools import groupby
from pathlib import Path
from urllib.parse import quote

REAL_LINKS = {
    "Federation Fleet": "https://archidekt.com/decks/27859380/federation_fleet_star_trek_commander",
    "Klingon Fury": "https://archidekt.com/decks/27883780/klingon_fury_star_trek_commander",
    "Landing Party": "https://archidekt.com/decks/28009052/landing_party_star_trek_commander",
    "We Are the Borg": "https://archidekt.com/decks/27814567/we_are_the_borg_star_trek_commander",
}
PLACEHOLDER_LINK = "https://archidekt.com/commander-precons"
SITE = "REM&#8217;s Commander Decks"  # the top page's title, and the name in every footer
SECTIONS = ("What it wants to do", "The commander", "Standout mechanic")
LINK = re.compile(r"\[([^\[\]]+)\]\(([^()\s]+)\)")

COLOR_WORD = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}
GROUP_NAME = {
    "WU": "Azorius", "WB": "Orzhov", "UB": "Dimir", "UR": "Izzet", "BR": "Rakdos",
    "BG": "Golgari", "RG": "Gruul", "WG": "Selesnya", "WR": "Boros", "UG": "Simic",
    "WUB": "Esper", "UBR": "Grixis", "BRG": "Jund", "WRG": "Naya", "WUG": "Bant",
    "WBG": "Abzan", "WUR": "Jeskai", "UBG": "Sultai", "WBR": "Mardu", "URG": "Temur",
}

# The constructed decks page: constructed/decks.tsv makes constructed/index.html.
#
# constructed/decks.tsv has a row for each deck: its name, its bracket (1 to 5, or
# empty if none is set yet), its Archidekt number, its commanders, its colors,
# and each commander's printing and card images (filled in by images.py).
# The page groups the decks by bracket, lowest first, with the decks that have
# no bracket last; within a bracket they go in alphabetical order. Each deck
# links to its list on Archidekt and to its combos on Commander Spellbook.
#
# A deck's explanation is constructed/descriptions/<name>.md, named as on the precon
# page. It has a Themes line and a Difficulty line, then the six headings in
# DECK_SECTIONS, each with its text under it, in the same Markdown as the
# precon page's descriptions:
#
#     Themes: First theme, Second theme, Third theme
#     Difficulty: Medium
#
#     ## What it wants to do
#     ...
#     ## What beats it
#     ...
#
# A deck with a sideboard in the Cards app (the sideboard column of
# constructed/decks.tsv) also has a "## Sideboard" section, last, saying which cards
# to swap in and why; a deck without one has no such section. The build
# checks both ways.
#
# A deck with no file shows placeholder text. The build stops without writing
# anything, and names the file, on the same mistakes as on the precon page.
# A link to the page that ends in a deck's name, such as #splinter-group,
# opens that deck.
DECK_SECTIONS = ("What it wants to do", "The commander", "Opening hand", "Key cards", "How it wins",
                 "What beats it")
DECK_FIELDS = ("Themes", "Difficulty")
SIDEBOARD = "Sideboard"
BRACKET_NAME = {"1": "Exhibition", "2": "Core", "3": "Upgraded", "4": "Optimized", "5": "cEDH"}
NO_BRACKET = "No bracket set yet"
ARCHIDEKT = "https://archidekt.com/decks/"
SPELLBOOK = "https://commanderspellbook.com/find-my-combos/?deckUrl="

e = html.escape


def words(ident):
    w = [COLOR_WORD[c] for c in ident]
    return w[0] if len(w) == 1 else ", ".join(w[:-1]) + " and " + w[-1]


def colors_line(ident):
    if len(ident) == 1:
        return f"Mono-{COLOR_WORD[ident]}"
    if len(ident) == 5:
        return "All five colors"
    if len(ident) == 4:
        return f"Four colors: {words(ident)}"
    return f"{GROUP_NAME[ident]}: {words(ident)}"


def spine(ident):
    n = len(ident)
    stops = [
        f"var(--m-{c.lower()}) {100 * i / n:.3f}% {100 * (i + 1) / n:.3f}%"
        for i, c in enumerate(ident)
    ]
    return f"linear-gradient(to bottom, {', '.join(stops)})"


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


class DescriptionError(Exception):
    pass


def emphasis(s, where):
    """Turn **words** into bold and *words* into italics in already-escaped text."""
    s = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(?=\S)(.+?)(?<=\S)\*", r"<em>\1</em>", s)
    if "*" in s:
        raise DescriptionError(
            f"{where}: an asterisk that doesn't start and end bold (**words**) or italics (*words*)")
    return s


def inline(text, where):
    """Escape a line of text for the page, with its links, bold and italics."""
    links = []

    def set_aside(m):
        label, url = m.group(1).strip(), m.group(2)
        if not url.startswith("https://"):
            raise DescriptionError(f"{where}: a link must start with https://, and {url} doesn't")
        links.append((label, url))
        return f"\x00{len(links) - 1}\x00"

    rest = LINK.sub(set_aside, text)
    if "](" in rest or re.search(r"\]\s+\(", rest):
        raise DescriptionError(f"{where}: a link isn't written as [words](https://address)")

    def put_back(m):
        label, url = links[int(m.group(1))]
        return f'<a href="{e(url)}">{emphasis(e(label), where)}</a>'

    return re.sub(r"\x00(\d+)\x00", put_back, emphasis(e(rest), where))


def blocks_html(lines, where):
    """Turn one section's lines into paragraphs and bulleted lists."""
    out, para, items = [], [], []
    after_blank = False

    def end_para():
        if para:
            out.append(f"<p>{inline(' '.join(para), where)}</p>")
            para.clear()

    def end_list():
        if items:
            lis = "".join(f"\n            <li>{inline(' '.join(item), where)}</li>" for item in items)
            out.append(f"<ul>{lis}\n          </ul>")
            items.clear()

    for line in lines:
        if not line:
            end_para()
            after_blank = True
            continue
        bullet = re.match(r"[-*]\s+(.*)", line)
        if bullet:
            end_para()
            items.append([bullet.group(1)])
        elif items and not after_blank:
            items[-1].append(line)  # a bullet that runs on to the next line
        else:
            end_list()
            para.append(line)
        after_blank = False
    end_para()
    end_list()
    return "\n          ".join(out)


def read_description(path, sections=SECTIONS, fields=("Themes",), optional=()):
    """Read one description file: the lines before its first heading, and each section as HTML.

    fields names the lines allowed before the first heading, Themes first; every one is needed.
    sections are the headings every file needs; optional ones may be left out.
    """
    allowed = tuple(sections) + tuple(optional)
    headings = {s.lower(): s for s in allowed}
    found, lines, current = {}, {}, None
    for n, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        where = f"{path}, line {n}"
        if line.startswith("#"):
            name = headings.get(line[3:].strip().lower()) if line.startswith("## ") else None
            if name is None:
                raise DescriptionError(
                    f'{where}: "{line}" is not one of the headings '
                    + ", ".join(f'"## {s}"' for s in allowed))
            if name in lines:
                raise DescriptionError(f'{where}: "## {name}" is in the file twice')
            current = name
            lines[name] = []
        elif current is not None:
            lines[current].append(line)
        elif line:
            m = re.fullmatch(r"([^:]+):\s*(.*)", line)
            field = m.group(1).strip() if m else None
            if field not in fields or field in found:
                quoted = [f'"{f}: ..."' for f in fields]
                allowed = ("one line, " + quoted[0] if len(quoted) == 1
                           else "the lines " + ", ".join(quoted[:-1]) + " and " + quoted[-1])
                raise DescriptionError(f"{where}: before the first heading, the file can only have {allowed}")
            found[field] = m.group(2).strip()
    themes = [t.strip() for t in found.get("Themes", "").split(",") if t.strip()]
    if not themes:
        raise DescriptionError(f'{path}: no themes. Start the file with a line like "Themes: First, Second, Third"')
    for field in fields[1:]:
        if not found.get(field):
            raise DescriptionError(f'{path}: no "{field}: ..." line before the first heading')
    missing = [s for s in allowed if (s in sections or s in lines) and not any(lines.get(s, []))]
    if missing:
        raise DescriptionError(f"{path}: nothing under " + ", ".join(f'"## {s}"' for s in missing))
    return {"themes": themes, "fields": found,
            "sections": {s: blocks_html(lines[s], f"{path}, {s}") for s in allowed if s in lines}}


def load_descriptions(folder, decks, sections=SECTIONS, fields=("Themes",),
                      tsv="decks.tsv", example="federation-fleet.md", optional=()):
    """Read every description file, by deck name, checking each matches a deck."""
    by_slug = {slug(d["name"]): d["name"] for d in decks}
    found = {}
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        if path.stem not in by_slug:
            raise DescriptionError(
                f"{path}: matches no deck in {tsv}. The file's name must be the deck's name"
                f" in lower case with hyphens between the words, such as {example}")
        found[by_slug[path.stem]] = read_description(path, sections, fields, optional)
    return found


def pips_html(ident):
    """The deck's colors as small mana symbols, with their names for screen readers."""
    label = words(ident)
    pips = "".join(f'<span class="pip pip-{c.lower()}">{c}</span>' for c in ident)
    return f'<span class="pips" role="img" aria-label="{label[0].upper() + label[1:]}">{pips}</span>'


def cards_html(d, cmdrs):
    """The commanders' card images, or nothing if the deck has none yet."""
    grids = [u for u in d.get("commander_grid", "").split(" + ") if u]
    displays = [u for u in d.get("commander_display", "").split(" + ") if u]
    sizes = "(min-width: 40rem) 13rem, " + ("11rem" if len(grids) > 1 else "15rem")
    imgs = "".join(
        f'<img src="{e(g)}" srcset="{e(g)} 488w, {e(big)} 672w" sizes="{sizes}" '
        f'width="488" height="680" alt="{e(c)}" loading="lazy" decoding="async">'
        for g, big, c in zip(grids, displays, cmdrs)
    )
    return f'<div class="cards{" two" if len(grids) > 1 else ""}">{imgs}</div>' if imgs else ""


CHEVRON = ('<svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 7.5l5 5 5-5" fill="none"'
           ' stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def deck_html(d, is_open, desc=None):
    name, ident = d["name"], d["identity"]
    cmdrs = d["commanders"].split(" + ")
    pips = pips_html(ident)
    href = REAL_LINKS.get(name, PLACEHOLDER_LINK)
    cmdr_sentence = (
        f"What {e(cmdrs[0])} does, and how the rest of the deck feeds it."
        if len(cmdrs) == 1
        else f"What {e(' and '.join(cmdrs))} do together, and how the rest of the deck feeds them."
    )
    cards = cards_html(d, cmdrs)
    if desc:
        chips = "".join(f'<span class="chip">{e(t)}</span>' for t in desc["themes"])
        wants, about, mechanic = (desc["sections"][s] for s in SECTIONS)
    else:
        chips = "".join(f'<span class="chip ph">{t}</span>' for t in ("Theme one", "Theme two", "Theme three"))
        wants = ('<p class="ph">Two or three sentences on how this deck wins and what a good turn looks like,'
                 ' written for someone who has never played it.</p>')
        about = f'<p class="ph">{cmdr_sentence}</p>'
        mechanic = ('<p class="ph">The one mechanic that sets this deck apart, what it does,'
                    ' and the card that shows it off best.</p>')
    return f"""
      <details class="deck" id="{slug(name)}" style="--spine: {spine(ident)}"{" open" if is_open else ""}>
        <summary>
          <span class="head">
            <h3>{e(name)}</h3>
            <span class="meta">{pips}<span>{e(" + ".join(cmdrs))}</span></span>
          </span>
          {CHEVRON}
        </summary>
        <div class="panel"><div class="panel-body">
          {cards}
          <div class="text">
          <dl class="facts">
            <div><dt>Colors</dt><dd>{colors_line(ident)}</dd></div>
            <div><dt>Themes</dt><dd><span class="chips">{chips}</span></dd></div>
          </dl>
          <h4>{SECTIONS[0]}</h4>
          {wants}
          <h4>{SECTIONS[1]}</h4>
          {about}
          <h4>{SECTIONS[2]}</h4>
          {mechanic}
          <a class="arch" href="{href}">See the full list on Archidekt<span aria-hidden="true">&nbsp;&#8599;</span></a>
          </div>
        </div></div>
      </details>"""


CSS = """
:root {
  /* Layout: one narrow column of deck boxes under shelf labels, one label per set;
     each deck's colors run down its left edge like the spine of a deck box. */
  --bg: #ECEFEB;
  --surface: #FAFBF9;
  --ink: #16201B;
  --muted: #56645D;
  --line: #D2D9D4;
  --accent: #1C6A51;
  --m-w: #E3D294;
  --m-u: #3D83CA;
  --m-b: #564E4A;
  --m-r: #D3513A;
  --m-g: #3A9257;
  --display: "Bricolage Grotesque", "Avenir Next", "Segoe UI", system-ui, sans-serif;
  --body: "Atkinson Hyperlegible", "Segoe UI", system-ui, -apple-system, sans-serif;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0E1412;
    --surface: #161F1B;
    --ink: #E6ECE8;
    --muted: #98A7A0;
    --line: #27332E;
    --accent: #69C7A0;
    --m-b: #9A8E87;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #0E1412;
  --surface: #161F1B;
  --ink: #E6ECE8;
  --muted: #98A7A0;
  --line: #27332E;
  --accent: #69C7A0;
  --m-b: #9A8E87;
  color-scheme: dark;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 400 1rem/1.55 var(--body); }
.wrap { max-width: 46rem; margin: 0 auto; padding: 2.5rem max(1rem, 4vw) 4rem; }
.top h1 {
  margin: 0; font-family: var(--display); font-weight: 760; font-variation-settings: "opsz" 96;
  font-size: clamp(2.5rem, 1.75rem + 3.5vw, 3.75rem); line-height: .95; letter-spacing: -0.025em; text-wrap: balance;
}
.lede { margin: .75rem 0 0; max-width: 34ch; font-size: 1.125rem; color: var(--muted); text-wrap: pretty; }
.also { margin: .5rem 0 0; color: var(--muted); }
.also a { color: var(--accent); text-underline-offset: .15em; }
.set { margin-top: 2.25rem; }
.set h2 {
  position: sticky; top: 0; z-index: 2; display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
  margin: 0 0 .75rem; padding: .75rem 0 .5rem; background: var(--bg); border-bottom: 1px solid var(--line);
  font-family: var(--display); font-weight: 700; font-variation-settings: "wdth" 75, "opsz" 14;
  font-size: .875rem; line-height: 1.3; letter-spacing: .09em; text-transform: uppercase;
}
.set-count { flex: none; font-family: var(--body); font-weight: 400; font-size: .8125rem; letter-spacing: 0; text-transform: none; color: var(--muted); font-variant-numeric: tabular-nums; }
.decks { display: grid; gap: .625rem; }
.deck { position: relative; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.deck::before { content: ""; position: absolute; top: 0; bottom: 0; left: 0; width: 8px; background: var(--spine); }
.deck summary {
  display: grid; grid-template-columns: 1fr auto; align-items: center; gap: .75rem;
  padding: .875rem 1rem .875rem 1.5rem; cursor: pointer; list-style: none;
}
.deck summary::-webkit-details-marker { display: none; }
.deck summary:hover { background: color-mix(in srgb, var(--accent) 6%, transparent); }
.deck summary:focus-visible { outline: 2px solid var(--accent); outline-offset: -3px; border-radius: 12px; }
.deck h3 { margin: 0; font-family: var(--display); font-weight: 680; font-size: 1.1875rem; line-height: 1.2; letter-spacing: -0.005em; text-wrap: balance; }
.meta { display: flex; flex-wrap: wrap; align-items: center; gap: .25rem .5rem; margin-top: .3rem; font-size: .9375rem; line-height: 1.35; color: var(--muted); }
.pips { display: inline-flex; gap: 3px; }
.pip {
  display: inline-grid; place-items: center; width: 18px; height: 18px; border-radius: 50%;
  font: 700 10px/1 var(--body); color: #1D1A17; box-shadow: inset 0 0 0 1px rgb(0 0 0 / .2);
}
.pip-w { background: #F8F6D8; }
.pip-u { background: #C1D7E9; }
.pip-b { background: #BAB1AB; }
.pip-r { background: #E49977; }
.pip-g { background: #A3C095; }
.chev { width: 20px; height: 20px; color: var(--muted); transition: transform .2s ease; }
.deck[open] .chev { transform: rotate(180deg); }
.panel { padding: 0 1.25rem 1.25rem 1.5rem; }
.panel-body { display: grid; gap: 1rem; margin-top: .25rem; padding-top: 1rem; border-top: 1px solid var(--line); }
.cards { display: flex; gap: .75rem; }
.cards img {
  display: block; width: 15rem; max-width: 100%; height: auto; border-radius: 4.76% / 3.41%;
  background: var(--line); box-shadow: 0 1px 2px rgb(0 0 0 / .18), 0 6px 18px rgb(0 0 0 / .12);
}
.cards.two img { width: calc(50% - .375rem); max-width: 11rem; }
@media (min-width: 40rem) {
  .panel-body { grid-template-columns: 13rem 1fr; gap: 1.5rem; align-items: start; }
  .cards { flex-direction: column; }
  .cards img, .cards.two img { width: 13rem; max-width: 100%; }
}
.facts { display: grid; gap: .5rem; margin: 0; }
.facts > div { display: grid; grid-template-columns: 5.5rem 1fr; gap: .75rem; align-items: baseline; }
.facts dt { font-size: .75rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.facts dd { margin: 0; }
.chips { display: flex; flex-wrap: wrap; gap: .375rem; }
.chip { padding: .1rem .55rem; border: 1px solid var(--line); border-radius: 999px; background: var(--bg); font-size: .8125rem; }
.chip.ph { border: 1px dashed var(--muted); background: none; }
.panel h4 { margin: 1.25rem 0 .25rem; font-family: var(--display); font-weight: 680; font-size: 1rem; }
.panel p, .panel ul { margin: 0; max-width: 62ch; }
.panel p + p, .panel p + ul, .panel ul + p { margin-top: .5rem; }
.panel ul { display: grid; gap: .25rem; padding-left: 1.125rem; }
.panel p a, .panel li a { color: var(--accent); text-underline-offset: .15em; }
.ph { font-style: italic; color: var(--muted); }
.arch {
  display: inline-flex; align-items: center; margin-top: 1.25rem; padding: .55rem .9rem;
  border: 1px solid var(--accent); border-radius: 8px; color: var(--accent); font-weight: 700; text-decoration: none;
}
.arch:hover { background: var(--accent); color: var(--surface); }
.arch:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.foot { max-width: 60ch; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--line); font-size: .8125rem; color: var(--muted); }
.foot p { margin: 0 0 .5rem; }
.foot a { color: var(--accent); }
@media (max-width: 420px) {
  .facts > div { grid-template-columns: 1fr; gap: .1rem; }
}
@media (prefers-reduced-motion: reduce) {
  .chev { transition: none; }
}
"""


def page_html(title, header, parts, css=CSS, script=""):
    """The whole page: its title, what goes under the title, the shelves of decks, and the footer."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&amp;family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,200..800&amp;display=swap">
<style>{css}</style>
</head>
<body>
  <main class="wrap">
    <header class="top">
      <h1>{title}</h1>{header}
    </header>{"".join(parts)}
    <footer class="foot">
      <p>{SITE} is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. &#169;Wizards of the Coast LLC.</p>
      <p>Card images come from <a href="https://scryfall.com">Scryfall</a>.</p>
    </footer>
  </main>{script}
</body>
</html>
"""


def shelf_html(anchor, label, items):
    """One shelf of decks under its label: a set on the precon page, a bracket on the other."""
    n = len(items)
    return f"""
    <section class="set" aria-labelledby="{anchor}">
      <h2 id="{anchor}"><span>{label}</span><span class="set-count">{n} deck{"" if n == 1 else "s"}</span></h2>
      <div class="decks">{"".join(items)}
      </div>
    </section>"""


def precons_page(src, out, decks):
    try:
        descriptions = load_descriptions(Path(src).parent / "descriptions", decks)
    except DescriptionError as err:
        sys.exit(f"Nothing written. {err}")
    sets = [(k, list(g)) for k, g in groupby(decks, key=lambda d: (d["set_code"], d["set_name"]))]
    parts = []
    first = True
    for (code, set_name), group in sets:
        items = []
        for d in group:
            items.append(deck_html(d, first, descriptions.get(d["name"])))
            first = False
        parts.append(shelf_html(f"set-{code}", e(set_name), items))
    header = ('\n      <p class="lede">Preconstructed Commander decks you can borrow, grouped by set.'
              " Tap one to see what it does.</p>"
              '\n      <p class="also">Looking for a constructed deck? <a href="../constructed/">Click Here</a></p>')
    page = page_html("Precon Decks", header, parts)
    Path(out).write_text(page, encoding="utf-8")
    print(f"{len(decks)} decks in {len(sets)} sets, {len(descriptions)} with a real description"
          f" -> {out} ({len(page):,} characters)")


# ---- The constructed decks page ----

DECKS_CSS = """
.deck { scroll-margin-top: 3.5rem; }
.links { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1.25rem; }
.links .arch { margin-top: 0; }
.nw { white-space: nowrap; }
"""

# Browsers will break a line after the hyphen in -1/-1, leaving "-1/-" at the end of a line, so the
# explanations keep counters like -1/-1 and +1/+1 together.
SIGNED_PT = re.compile(r"[+-]\d+/[+-]\d+")


def keep_together(section_html):
    parts = re.split(r"(<[^>]+>)", section_html)
    return "".join(p if p.startswith("<") else SIGNED_PT.sub(r'<span class="nw">\g<0></span>', p)
                   for p in parts)

OPEN_FROM_ADDRESS = """
  <script>
    // A link to this page that ends in a deck's name, such as #splinter-group, opens that deck.
    function openFromAddress() {
      var id;
      try { id = decodeURIComponent(location.hash.slice(1)); } catch (err) { return; }
      var deck = id && document.getElementById(id);
      if (deck && deck.tagName === "DETAILS") { deck.open = true; deck.scrollIntoView(); }
    }
    addEventListener("hashchange", openFromAddress);
    openFromAddress();
  </script>"""


def placeholder_list(*items):
    lis = "".join(f"\n            <li>{item}</li>" for item in items)
    return f'<ul class="ph">{lis}\n          </ul>'


def deck_placeholders(cmdrs):
    """Placeholder text for each of the six sections, for a deck with no explanation yet."""
    them = (f"What {e(cmdrs[0])} does, when to cast it, and how the rest of the deck uses it."
            if len(cmdrs) == 1 else
            f"What {e(' and '.join(cmdrs))} do together, when to cast them, and how the rest of the deck uses them.")
    return {
        "What it wants to do": '<p class="ph">Two or three sentences on the plan, and what a good game looks like.</p>',
        "The commander": f'<p class="ph">{them}</p>',
        "Opening hand": placeholder_list("What a hand worth keeping has.", "When to send a hand back."),
        "Key cards": placeholder_list("A card worth knowing, and what to do with it.",
                                      "Another card worth knowing, and when to play it.",
                                      "Four to six cards in all, each linked to its card."),
        "How it wins": '<p class="ph">The usual ways this deck ends a game, and about how long that takes.</p>',
        "What beats it": placeholder_list("A card or situation that gives this deck trouble.",
                                          "How to play around it."),
    }


def own_deck_html(d, is_open, desc=None):
    name, ident = d["name"], d["identity"]
    cmdrs = d["commanders"].split(" + ")
    archidekt = ARCHIDEKT + d["archidekt_id"].strip()
    spellbook = SPELLBOOK + quote(archidekt, safe="")
    bracket = d["bracket"].strip()
    bracket_text = f"{bracket} ({BRACKET_NAME[bracket]})" if bracket else '<span class="ph">Not set yet</span>'
    if desc:
        chips = "".join(f'<span class="chip">{e(t)}</span>' for t in desc["themes"])
        difficulty = e(desc["fields"]["Difficulty"])
        sections = {s: keep_together(h) for s, h in desc["sections"].items()}
    else:
        chips = "".join(f'<span class="chip ph">{t}</span>' for t in ("Theme one", "Theme two", "Theme three"))
        difficulty = '<span class="ph">Easy, medium or hard</span>'
        sections = deck_placeholders(cmdrs)
    if d.get("sideboard", "").strip():
        sections = dict(sections)
        sections.setdefault(SIDEBOARD, '<p class="ph">Which sideboard cards to swap in, and what changes'
                                       ' when you do.</p>')
    body = "".join(f"\n          <h4>{s}</h4>\n          {sections[s]}"
                   for s in DECK_SECTIONS + (SIDEBOARD,) if s in sections)
    arrow = '<span aria-hidden="true">&nbsp;&#8599;</span>'
    return f"""
      <details class="deck" id="{slug(name)}" style="--spine: {spine(ident)}"{" open" if is_open else ""}>
        <summary>
          <span class="head">
            <h3>{e(name)}</h3>
            <span class="meta">{pips_html(ident)}<span>{e(" + ".join(cmdrs))}</span></span>
          </span>
          {CHEVRON}
        </summary>
        <div class="panel"><div class="panel-body">
          {cards_html(d, cmdrs)}
          <div class="text">
          <dl class="facts">
            <div><dt>Colors</dt><dd>{colors_line(ident)}</dd></div>
            <div><dt>Themes</dt><dd><span class="chips">{chips}</span></dd></div>
            <div><dt>Bracket</dt><dd>{bracket_text}</dd></div>
            <div><dt>Difficulty</dt><dd>{difficulty}</dd></div>
          </dl>{body}
          <div class="links"><a class="arch" href="{e(archidekt)}">See the full list on Archidekt{arrow}</a><a class="arch" href="{e(spellbook)}">Combos on Commander Spellbook{arrow}</a></div>
          </div>
        </div></div>
      </details>"""


def own_decks_page(src, out, decks):
    try:
        descriptions = load_descriptions(Path(src).parent / "descriptions", decks, DECK_SECTIONS, DECK_FIELDS,
                                         tsv=src, example="splinter-group.md", optional=(SIDEBOARD,))
    except DescriptionError as err:
        sys.exit(f"Nothing written. {err}")
    for d in decks:
        desc = descriptions.get(d["name"])
        if not desc:
            continue
        where = Path(src).parent / "descriptions" / f"{slug(d['name'])}.md"
        cards = d.get("sideboard", "").strip()
        if SIDEBOARD in desc["sections"] and not cards:
            sys.exit(f'Nothing written. {where} has a "## Sideboard" section, but {src} lists no sideboard'
                     f" for {d['name']}. Only a deck with a sideboard has that section.")
        if cards and SIDEBOARD not in desc["sections"]:
            sys.exit(f"Nothing written. {d['name']} has a sideboard ({cards}), so {where} needs a"
                     ' "## Sideboard" section, last.')
    groups, slugs = {}, {}
    for d in decks:
        bracket = d["bracket"].strip()
        if bracket and bracket not in BRACKET_NAME:
            sys.exit(f"Nothing written. {src}: {d['name']} has bracket {bracket}."
                     " A bracket is 1 to 5, or empty if none is set yet.")
        if not d["archidekt_id"].strip().isdigit():
            sys.exit(f"Nothing written. {src}: {d['name']} has no Archidekt number.")
        if slug(d["name"]) in slugs:
            sys.exit(f"Nothing written. {src}: {d['name']} and {slugs[slug(d['name'])]} would have the same link.")
        slugs[slug(d["name"])] = d["name"]
        groups.setdefault(bracket, []).append(d)
    order = sorted((b for b in groups if b), key=int) + ([""] if "" in groups else [])
    parts = []
    first = True
    for bracket in order:
        items = []
        for d in sorted(groups[bracket], key=lambda d: d["name"].lower()):
            items.append(own_deck_html(d, first, descriptions.get(d["name"])))
            first = False
        label = f"Bracket {bracket}: {BRACKET_NAME[bracket]}" if bracket else NO_BRACKET
        parts.append(shelf_html(f"bracket-{bracket or 'none'}", label, items))
    header = ('\n      <p class="lede">Custom-built Commander decks, grouped by bracket from most casual to most'
              " powerful. Tap one to see how it plays.</p>"
              '\n      <p class="also">Looking for a precon? <a href="../precons/">Click Here</a></p>')
    page = page_html("Constructed Decks", header, parts, CSS + DECKS_CSS, OPEN_FROM_ADDRESS)
    Path(out).write_text(page, encoding="utf-8")
    print(f"{len(decks)} decks in {len(order)} brackets, {len(descriptions)} with a real explanation"
          f" -> {out} ({len(page):,} characters)")


# ---- The top page, linking both ----
#
# python3 build.py --home index.html makes the page at the top of the site,
# robmills2.github.io/decks/, with one link to each of the other two pages.
# It reads no deck list, so it changes only when this script does.

HOME_CSS = """
.sites { display: grid; gap: .625rem; margin-top: 2.25rem; }
.site {
  position: relative; display: grid; grid-template-columns: 1fr auto; align-items: center; gap: .75rem;
  padding: 1rem 1rem 1rem 1.5rem; background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
  color: var(--ink); text-decoration: none; overflow: hidden;
}
.site::before {
  content: ""; position: absolute; top: 0; bottom: 0; left: 0; width: 8px;
  background: linear-gradient(to bottom, var(--m-w) 0% 20%, var(--m-u) 20% 40%, var(--m-b) 40% 60%,
                                         var(--m-r) 60% 80%, var(--m-g) 80% 100%);
}
.site:hover { background: color-mix(in srgb, var(--accent) 6%, var(--surface)); }
.site:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.site-name { font-family: var(--display); font-weight: 680; font-size: 1.1875rem; line-height: 1.2; }
.site .chev { transform: rotate(-90deg); }
"""

HOME_LINKS = (
    ("precons/", "Precons"),
    ("constructed/", "Constructed Decks"),
)


def home_page(out):
    items = "".join(
        f'\n      <a class="site" href="{href}"><span class="site-name">{name}</span>{CHEVRON}</a>'
        for href, name in HOME_LINKS)
    header = '\n      <p class="lede">Commander decks you can borrow at game night.</p>'
    parts = [f'\n    <nav class="sites" aria-label="The two lists of decks">{items}\n    </nav>']
    page = page_html(SITE, header, parts, CSS + HOME_CSS)
    Path(out).write_text(page, encoding="utf-8")
    print(f"top page linking {len(HOME_LINKS)} pages -> {out} ({len(page):,} characters)")


def main(src, out):
    with open(src, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        decks = list(reader)
        columns = reader.fieldnames or []
    if "set_code" in columns:
        precons_page(src, out, decks)
    elif "bracket" in columns:
        own_decks_page(src, out, decks)
    else:
        sys.exit(f"Nothing written. {src} has neither a set_code column (the precon page)"
                 " nor a bracket column (the constructed decks).")


if __name__ == "__main__":
    if sys.argv[1] == "--home":
        home_page(sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2])
