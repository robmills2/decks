#!/usr/bin/env python3
"""Build the precon page mockup from a TSV of decks.

Real: deck names, commanders, colors, and Federation Fleet's Archidekt link.
Placeholder: every description, and every other Archidekt link.

Usage: python3 build.py decks.tsv index.html
"""
import csv
import html
import re
import sys
import unicodedata
from itertools import groupby
from pathlib import Path

REAL_LINKS = {
    "Federation Fleet": "https://archidekt.com/decks/27859380/federation_fleet_star_trek_commander",
}
PLACEHOLDER_LINK = "https://archidekt.com/commander-precons"

COLOR_WORD = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}
GROUP_NAME = {
    "WU": "Azorius", "WB": "Orzhov", "UB": "Dimir", "UR": "Izzet", "BR": "Rakdos",
    "BG": "Golgari", "RG": "Gruul", "WG": "Selesnya", "WR": "Boros", "UG": "Simic",
    "WUB": "Esper", "UBR": "Grixis", "BRG": "Jund", "WRG": "Naya", "WUG": "Bant",
    "WBG": "Abzan", "WUR": "Jeskai", "UBG": "Sultai", "WBR": "Mardu", "URG": "Temur",
}

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


def deck_html(d, is_open):
    name, ident = d["name"], d["identity"]
    cmdrs = d["commanders"].split(" + ")
    label = words(ident)
    pips = "".join(f'<span class="pip pip-{c.lower()}">{c}</span>' for c in ident)
    href = REAL_LINKS.get(name, PLACEHOLDER_LINK)
    cmdr_sentence = (
        f"What {e(cmdrs[0])} does, and how the rest of the deck feeds it."
        if len(cmdrs) == 1
        else f"What {e(' and '.join(cmdrs))} do together, and how the rest of the deck feeds them."
    )
    return f"""
      <details class="deck" id="{slug(name)}" style="--spine: {spine(ident)}"{" open" if is_open else ""}>
        <summary>
          <span class="head">
            <h3>{e(name)}</h3>
            <span class="meta"><span class="pips" role="img" aria-label="{label[0].upper() + label[1:]}">{pips}</span><span>{e(" + ".join(cmdrs))}</span></span>
          </span>
          <svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 7.5l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </summary>
        <div class="panel">
          <dl class="facts">
            <div><dt>Colors</dt><dd>{colors_line(ident)}</dd></div>
            <div><dt>Themes</dt><dd><span class="chips"><span class="chip">Theme one</span><span class="chip">Theme two</span><span class="chip">Theme three</span></span></dd></div>
          </dl>
          <h4>What it wants to do</h4>
          <p class="ph">Two or three sentences on how this deck wins and what a good turn looks like, written for someone who has never played it.</p>
          <h4>The commander</h4>
          <p class="ph">{cmdr_sentence}</p>
          <h4>Combos and synergies</h4>
          <ul class="ph">
            <li>A combo worth knowing, the cards it takes, and what happens when they come together.</li>
            <li>Two cards that work better together than apart.</li>
          </ul>
          <a class="arch" href="{href}">See the full list on Archidekt<span aria-hidden="true">&nbsp;&#8599;</span></a>
        </div>
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
.note { margin: 1.5rem 0 0; max-width: 60ch; padding: .75rem 1rem; border: 1px dashed var(--muted); border-radius: 10px; font-size: .875rem; color: var(--muted); }
.note strong { color: var(--ink); }
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
.facts { display: grid; gap: .5rem; margin: .25rem 0 0; padding-top: 1rem; border-top: 1px solid var(--line); }
.facts > div { display: grid; grid-template-columns: 5.5rem 1fr; gap: .75rem; align-items: baseline; }
.facts dt { font-size: .75rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.facts dd { margin: 0; }
.chips { display: flex; flex-wrap: wrap; gap: .375rem; }
.chip { padding: .1rem .55rem; border: 1px dashed var(--muted); border-radius: 999px; font-size: .8125rem; font-style: italic; color: var(--muted); }
.panel h4 { margin: 1.25rem 0 .25rem; font-family: var(--display); font-weight: 680; font-size: 1rem; }
.panel p, .panel ul { margin: 0; max-width: 62ch; }
.panel ul { display: grid; gap: .25rem; padding-left: 1.125rem; }
.ph { font-style: italic; color: var(--muted); }
.arch {
  display: inline-flex; align-items: center; margin-top: 1.25rem; padding: .55rem .9rem;
  border: 1px solid var(--accent); border-radius: 8px; color: var(--accent); font-weight: 700; text-decoration: none;
}
.arch:hover { background: var(--accent); color: var(--surface); }
.arch:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media (max-width: 420px) {
  .facts > div { grid-template-columns: 1fr; gap: .1rem; }
}
@media (prefers-reduced-motion: reduce) {
  .chev { transition: none; }
}
"""


def main(src, out):
    with open(src, newline="", encoding="utf-8") as f:
        decks = list(csv.DictReader(f, delimiter="\t"))
    sets = [(k, list(g)) for k, g in groupby(decks, key=lambda d: (d["set_code"], d["set_name"]))]
    parts = []
    first = True
    for (code, set_name), group in sets:
        n = len(group)
        items = []
        for d in group:
            items.append(deck_html(d, first))
            first = False
        parts.append(f"""
    <section class="set" aria-labelledby="set-{code}">
      <h2 id="set-{code}"><span>{e(set_name)}</span><span class="set-count">{n} deck{"" if n == 1 else "s"}</span></h2>
      <div class="decks">{"".join(items)}
      </div>
    </section>""")
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rob&#8217;s Precons</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&amp;family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,200..800&amp;display=swap">
<style>{CSS}</style>
</head>
<body>
  <main class="wrap">
    <header class="top">
      <h1>Rob&#8217;s Precons</h1>
      <p class="lede">{len(decks)} Commander decks you can borrow. Tap one to see what it does.</p>
      <p class="note"><strong>Mockup.</strong> Deck names, commanders and colors are real. The descriptions are placeholder text, and only Federation Fleet links to its own Archidekt page; the others go to Archidekt&#8217;s list of precons.</p>
    </header>{"".join(parts)}
  </main>
</body>
</html>
"""
    Path(out).write_text(page, encoding="utf-8")
    print(f"{len(decks)} decks in {len(sets)} sets -> {out} ({len(page):,} characters)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
