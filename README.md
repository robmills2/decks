# REM's Commander Decks

Three pages of Commander decks, which GitHub Pages publishes from this repository's main branch:

- **REM's Commander Decks**, the top page at https://robmills2.github.io/decks/, links to the other two.
- **Precon Decks**, at https://robmills2.github.io/decks/precons/, lists the Commander precons Rob lends out. Tap a deck to see what it does.
- **Constructed Decks**, at https://robmills2.github.io/decks/constructed/, lists the decks Rob built himself, grouped by bracket. Tap a deck to see how it plays.

`build.py` makes all three pages, so they share one look. GitHub doesn't run it: after changing a deck list or a description, run it and commit the new page; until then the page stays as it was. If you change `build.py`, rebuild all three pages and check them.

Until November 2026 this repository was called `precons`, and the pages were at https://robmills2.github.io/precons/ and https://robmills2.github.io/precons/decks/. A separate repository, robmills2/precons, now holds only pages that send those old links on to the new addresses, deck links included.

## The top page

- `index.html` is the page.
- `python3 build.py --home index.html` makes it. Its two links and their wording are `HOME_LINKS` in `build.py`. The site's name, REM's Commander Decks, is `SITE` there: it's the top page's title and the name in every page's footer. It reads no deck list, so it needs rebuilding only when `build.py` changes.

## The precon page

- `precons/index.html` is the page.
- `precons/decks.tsv` lists the decks: name, set, commanders, colors, each commander's printing (set and collector number) and its card image addresses.
- `precons/descriptions/` holds one Markdown file for each deck that has a real description, named after the deck in lower case with hyphens between the words, such as `precons/descriptions/federation-fleet.md`. Each file has a `Themes:` line, then the page's three headings (`## What it wants to do`, `## The commander`, `## Standout mechanic`) with text under each: paragraphs, bullets starting with `- `, links written `[words](https://address)`, `**bold**` and `*italics*`. Other Markdown shows on the page as typed. The top of `build.py` describes the format in full.
- `images.py` fills in the card image addresses from Scryfall for any deck that has none yet: `python3 images.py precons/decks.tsv`
- `build.py` makes `precons/index.html` from `precons/decks.tsv` and `precons/descriptions/`: `python3 build.py precons/decks.tsv precons/index.html`. It stops without writing anything, and names the file, if a description file matches no deck or isn't in the format above.
- `.nojekyll`, at the top of the repository, tells GitHub Pages to show the files as they are.

Only the decks with a file in `precons/descriptions/` have real descriptions; the others show placeholder text. The decks listed in `REAL_LINKS` near the top of `build.py` link to their own Archidekt pages; the others go to Archidekt's list of precons.

## Constructed Decks

- `constructed/index.html` is the page.
- `constructed/decks.tsv` lists the decks: name, bracket (1 to 5, or empty if none is set yet), Archidekt number, commanders, colors, each commander's printing (set and collector number), the deck's sideboard (the cards the Cards app marks as sideboard, joined by ` + `) and the commanders' card image addresses. The list comes from the Cards app (the query is below). A deck's bracket is settled when its explanation is written, and Rob sets the same one on Archidekt.
- `constructed/descriptions/` holds one Markdown file for each deck that has a real explanation, named the same way as on the precon page, such as `constructed/descriptions/splinter-group.md`. Each file has a `Themes:` line and a `Difficulty:` line, then six headings with text under each: `## What it wants to do`, `## The commander`, `## Opening hand`, `## Key cards`, `## How it wins` and `## What beats it`. A deck with a sideboard also has `## Sideboard`, saying which cards to swap in and why; it shows last. A deck without a sideboard has no such section, and the build stops if the two don't match. The Markdown is the same as for the precon descriptions. Decks with no file show placeholder text.
- `python3 images.py constructed/decks.tsv` fills in the card image addresses.
- `python3 build.py constructed/decks.tsv constructed/index.html` makes the page. It stops without writing anything, and names the file, on the same mistakes as for the precon page.

On the page, the decks are grouped by bracket, lowest first, with the decks that have no bracket last, and in alphabetical order within each bracket. Each deck links to its list on Archidekt and to Commander Spellbook's Find My Combos, which reads the deck from Archidekt whenever the link is opened, so that link never goes out of date.

A link to the page that ends in a deck's name opens that deck, such as https://robmills2.github.io/decks/constructed/#splinter-group. The name is the deck's name in lower case with hyphens between the words.

### Refreshing the deck list

The list is every deck in the Cards app that isn't a precon, a container or dismantled. In a Brewing chat, run this with run_query and write its rows into `constructed/decks.tsv`, keeping each deck's bracket from the file as it was, and the commander printings listed after the query. Then run `images.py` and `build.py` as above:

```sql
WITH d AS (
  SELECT id, name, archidekt_id FROM collection.decks
  WHERE NOT is_precon AND NOT is_container AND status IN ('assembled', 'building')
),
c AS (
  SELECT s.deck_id, s.id AS slot_id, o.name, o.color_identity, p.set_code, p.collector_number
  FROM collection.deck_slots s
  JOIN scryfall.oracle_cards o ON o.oracle_id = s.oracle_id
  LEFT JOIN scryfall.printings p ON p.id = s.pinned_printing_id
  WHERE s.is_commander AND s.deck_id IN (SELECT id FROM d)
)
SELECT d.name, d.archidekt_id,
  coalesce(string_agg(c.name, ' + ' ORDER BY c.slot_id), 'NO COMMANDER') AS commanders,
  coalesce((SELECT string_agg(x, '' ORDER BY array_position(ARRAY['W','U','B','R','G'], x))
            FROM (SELECT DISTINCT unnest(c2.color_identity) AS x FROM c c2 WHERE c2.deck_id = d.id) y), '') AS identity,
  coalesce(string_agg(coalesce(c.set_code || ' ' || c.collector_number, 'NO PRINTING'), ' + ' ORDER BY c.slot_id), '') AS commander_cards,
  coalesce((SELECT string_agg(o3.name, ' + ' ORDER BY o3.name) FROM collection.deck_slots s3
            JOIN scryfall.oracle_cards o3 ON o3.oracle_id = s3.oracle_id
            WHERE s3.deck_id = d.id AND s3.is_sideboard), '') AS sideboard
FROM d LEFT JOIN c ON c.deck_id = d.id
GROUP BY d.id, d.name, d.archidekt_id
ORDER BY lower(d.name)
```

Keep these commander printings when you refresh. The page shows them in place of the printing the Cards app has, and each deck's explanation links its commander to the same printing:

- PLNH: `dmu 107`, the English Sheoldred, the Apocalypse, so the card on the page is readable. The Cards app has the Phyrexian-language printing, `dmu 369`.
- That Loofa You Use to Clean Between the Cheeks: `sld 1932`, the SpongeBob SquarePants Secret Lair printing of Jodah, the Unifier, which Rob asked for (2026-11-28). The Cards app has `dmu 203`.

Only the decks with a file in `constructed/descriptions/` have real explanations so far; the others show placeholder text.
