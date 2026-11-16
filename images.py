#!/usr/bin/env python3
"""Fill in each commander's card image addresses in decks.tsv from Scryfall.

For every deck whose commander_grid is empty, this asks Scryfall for the
printings named in commander_cards ("set number", several joined by " + ")
and writes their WebP image addresses: grid (488 x 680) into commander_grid
and display (672 x 936) into commander_display. It checks that each
printing's name matches the commanders column, and writes nothing if any
does not.

Usage: python3 images.py decks.tsv
"""
import csv
import json
import sys
import time
import urllib.request

API = "https://api.scryfall.com/cards/collection"
HEADERS = {
    "User-Agent": "RobsPrecons/0.1",
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def main(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fields = list(reader.fieldnames)
        rows = list(reader)
    for col in ("commander_grid", "commander_display"):
        if col not in fields:
            fields.append(col)

    todo = [r for r in rows if not r.get("commander_grid")]
    wanted = []
    for r in todo:
        for card in r["commander_cards"].split(" + "):
            set_code, number = card.split()
            wanted.append({"set": set_code, "collector_number": number})

    found = {}
    for i in range(0, len(wanted), 75):  # Scryfall takes 75 cards a request
        body = json.dumps({"identifiers": wanted[i:i + 75]}).encode()
        req = urllib.request.Request(API, data=body, headers=HEADERS, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        if data.get("not_found"):
            sys.exit(f"Scryfall does not know: {data['not_found']}")
        for card in data["data"]:
            found[(card["set"], card["collector_number"])] = card
        time.sleep(0.2)

    problems = []
    for r in todo:
        grids, displays = [], []
        for card_id, name in zip(r["commander_cards"].split(" + "), r["commanders"].split(" + ")):
            set_code, number = card_id.split()
            card = found[(set_code, number)]
            face = card if "image_uris" in card else card["card_faces"][0]
            if name not in (card["name"], face["name"]):
                problems.append(f"{r['name']}: {card_id} is {card['name']}, not {name}")
                continue
            grids.append(face["image_uris"]["grid"])
            displays.append(face["image_uris"]["display"])
        r["commander_grid"] = " + ".join(grids)
        r["commander_display"] = " + ".join(displays)
    if problems:
        sys.exit("Nothing written:\n" + "\n".join(problems))

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"filled {len(todo)} decks, {len(wanted)} commander cards")


if __name__ == "__main__":
    main(sys.argv[1])
