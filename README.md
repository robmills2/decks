# Rob's Precons

One page listing the Commander precons Rob lends out. Tap a deck to see what it does.

- `index.html` is the page GitHub Pages shows.
- `decks.tsv` lists the decks: name, set, commanders, colors, each commander's printing (set and collector number) and its card image addresses.
- `descriptions/` holds one Markdown file for each deck that has a real description, named after the deck in lower case with hyphens between the words, such as `descriptions/federation-fleet.md`. Each file has a `Themes:` line, then the page's three headings (`## What it wants to do`, `## The commander`, `## Standout mechanic`) with text under each: paragraphs, bullets starting with `- `, links written `[words](https://address)`, `**bold**` and `*italics*`. Other Markdown shows on the page as typed. The top of `build.py` describes the format in full.
- `images.py` fills in the card image addresses from Scryfall for any deck that has none yet: `python3 images.py decks.tsv`
- `build.py` makes `index.html` from `decks.tsv` and `descriptions/`: `python3 build.py decks.tsv index.html`. It stops without writing anything, and names the file, if a description file matches no deck or isn't in the format above.
- `.nojekyll` tells GitHub Pages to show the files as they are.

GitHub doesn't run `build.py`. After changing `decks.tsv` or a description, run it and commit the new `index.html`; until then the page stays as it was.

This is still a mockup: only the decks with a file in `descriptions/` have real descriptions, and the others show placeholder text. Only Federation Fleet links to its own Archidekt page.
