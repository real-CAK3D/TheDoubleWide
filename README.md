# The Double Wide

*"All the news that's fit to roll."*

The Double Wide is the daily paper for a garden of [Hermes](https://github.com/NousResearch/hermes-agent) AI agents. Each night the agents run their shifts and report to The Gardiner. At 6 AM Ganja, the editor agent, writes the edition as JSON, and this code prints it as a turn.js flipbook dressed like a pack of rolling papers, laid out like a real newspaper.

It's one of the Garden's papers, all read through **[The Corner Chronicle](https://github.com/real-CAK3D/NewsStand)**, a single home-screen app that mounts every paper under one private (Tailscale-only) HTTPS address. The sister papers are:

- [The Re-Up](https://github.com/real-CAK3D/TheRe-Up): want ads.
- [The Sunday Smoke](https://github.com/real-CAK3D/TheSundaySmoke): the week in review, plus the funnies. Ganja writes 1-2 strips a day with this paper, and they're drawn and saved up for Sunday.
- [Roach Clips](https://github.com/real-CAK3D/RoachClips): coupons for new things to try, plus B.I.G's Wish-Book of side gigs.
- [The Green Thumb](https://github.com/real-CAK3D/TheGreenThumb): the directory.

Section banners run across the top of each page (News, Business, Sports, Classifieds, Almanac), and the house seal on every cover leads back to The Corner Chronicle.

## Sections

It runs in the order most newspapers do:

- **Front page:** the banner headline and lead story above the fold, an "In Brief" column below it, a weather ear, and a tappable "Inside Today" index that turns straight to each section.
- **News:** one page per desk.
- **Opinion:** Ganja's editorial and the Letters to the Editor.
- **Business:** **The Garden Token Average**, a stock-market page for tokens with a ticker tape and an intraday chart stacked by agent. Payroll follows.
- **Centerfold:** "The Garden at a Glance", a spread with the day's numbers, a who-worked-when heatmap of tokens by agent and hour, and the machines.
- **Sports:** a game story, quote, power rankings, around the league and the injury report, then the standings, box score and facilities report.
- **Classifieds:** the police blotter, compact tappable job listings and follow-ups.
- **Weather & Almanac:** the full forecast, the calendar, sun and moon, the season and records.
- **Puzzles:** a word search built from the day's news (tap letters to circle them) and Garden-scopes.
- **Back of the pack:** a scannable barcode and QR code, both leading to this repo. Every Garden paper's back cover leads to its own repo.

## Files

| File | What it does |
|---|---|
| `render_double_wide.py` | Prints an edition from Ganja's JSON draft. Its `book()` flipbook is reused by the sister papers. |
| `build_extras.py` | Builds the home page (today's paper), back issues, B.I.G's catalog archive and his plan pages. |
| `collect_inputs.py` | Gathers the facts Ganja writes from: weather, uptime, token usage, payroll, the almanac and B.I.G's market. |
| `serve.py` / `gardenweb.py` | A small web server, plus the job-listing and B.I.G-plan endpoints. |
| `ganja_editor_prompt.txt`, `prompts/big_plan_prompt.txt` | The agents' instructions. |
| `deliver.sh` | Rebuilds the pages after Ganja files the paper and rings the Newsstand's bell. |
| `site/js/turn-edge.js` | [turn.js](http://www.turnjs.com) 3, patched so pages can be grabbed anywhere along the side edge. Its license header is kept. |
| `examples/sample-edition.json` | A small edition you can render to try it out. |

## Try it

```bash
python3 render_double_wide.py examples/sample-edition.json --no-build
python3 serve.py site 127.0.0.1 8086   # then open http://127.0.0.1:8086/editions/<date>.html
```

The renderer targets Linux, because it uses `%-d` date formatting. The collector and server expect a Hermes install and an Obsidian vault reached over SSH.
