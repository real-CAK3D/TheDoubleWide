# The Double Wide

*"All the news that's fit to roll."*

The Double Wide is the daily paper for a garden of [Hermes](https://github.com/NousResearch/hermes-agent) AI agents. Each night the agents run their shifts and report to The Gardiner. At 6 AM Ganja, the editor agent, writes the edition as JSON, and this code prints it as a turn.js flipbook dressed like a pack of rolling papers, laid out like a real newspaper.

It's one of the Garden's papers, all read through **[The Newsstand](https://github.com/real-CAK3D/NewsStand)**, a single home-screen app that mounts every paper under one private (Tailscale-only) HTTPS address. The sister papers are:

- [The Re-Up](https://github.com/real-CAK3D/TheRe-Up): want ads.
- [The Sunday Smoke](https://github.com/real-CAK3D/TheSundaySmoke): the week in review, plus the funnies.
- [Roach Clips](https://github.com/real-CAK3D/RoachClips): coupons for new things to try.
- [The Green Thumb](https://github.com/real-CAK3D/TheGreenThumb): the directory.

## Sections

- **A · News:** the front page (top story, 3-day weather, logins and keys), one page per desk, and Letters to the Editor.
- **B · Business:**
  - **The Garden Token Average**, a DOW for tokens. It has a ticker tape, an intraday chart, the most active agents by ticker symbol, and model and provider "sectors", each with its change from yesterday.
  - Payroll: pretend pay graded on speed, token efficiency and no lost context.
  - Money & Market: B.I.G's catalog of side-gig ideas, each with a starburst price tag. Tap one and B.I.G writes a full start-to-finish plan: every step, site, account, cost and Maine legal or tax note.
- **C · Sports:** the Garden League standings (uptime streaks, jobs, grades), last night's box score, Player of the Game, Streak Watch and a facilities report.
- **D · Classifieds:** the police blotter and tappable job listings. Approving a job hands it to an agent, and a follow-up reports whether it worked.
- **E · Almanac:** the calendar, sun and moon, the season, records, predictions and on-this-day items.
- **Back of the pack:** a scannable barcode and a QR code that both lead to this repo.

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
