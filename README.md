# Sunday 22 November 2026 — The World in One Day

[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/rfky18/news-image-20261122/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/rfky18/news-image-20261122/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A one-image summary of the world's news on **Sunday 22 November 2026**,
drawn as a classic newspaper front page — for the
[make.fun bounty `news-image-20261122`](https://make.fun/bounty/news-image-20261122)
("Sum up 22 November's world news in one image", $100, free entry).

## What is on the page

- **39 dated stories** across **7 regions** (Europe 9 · Asia-Pacific 10 ·
  Middle East 4 · Americas 5 · Africa 5 · Oceania 2 · World 4), every one
  from Sunday 22 November 2026, each with its source.
- **Masthead = the date**, stat strip (~200 nations at COP31 · 03:00 GMT ·
  186 drones · 161 downed · 2 radars · 856 candidates), region bar, and a
  **"THE DAY IN UTC"** timeline strip.
- **3 hero stories**: COP31's final text at dawn (Antalya), Iran's claimed
  strikes on US bases in Bahrain, Russia's 186-drone barrage on Ukraine.
- **10 illustrated secondary stories** (Hong Kong election, Verstappen's Las
  Vegas win, India's 720/9 in Wellington, Sparta II still ablaze, and more),
  a flat schematic **map with 13 numbered pins**, and **26 more stories** in
  the "ALSO ON SUNDAY 22 NOVEMBER" list.
- A red **DATE CHECK** box listing the near-miss stories deliberately left
  out (Russia's 400-drone barrage of 19–20 Nov, the Peru quake, and others),
  including why Sparta II still counts: it was still burning at anchor on
  Sunday.

## How it is made

`main.py` is **Python stdlib only** — no network, no third-party packages at
runtime. It renders a deterministic 1024×1024 PNG (two runs produce
byte-identical output).

- **Text** is blitted from bitmap atlases (`atlas/`) rendered at build time
  from real Google Fonts TTFs: Bodoni Moda (masthead), Libre Baskerville Bold
  (headlines), Gelasio (body), Liberation Sans (strips/labels), Roboto
  (captions). No geometric stroke fonts.
- **All pictures** — hero scenes, secondary icons, the flat world map — are
  flat vector shapes drawn in code. No external or generated images.

## Run it

```sh
python3 main.py            # writes /output/entry.png
MAKEFUN_OUTPUT_DIR=out python3 main.py   # writes out/entry.png
```

Output: `entry.png`, 1024×1024, under 1 MiB.
