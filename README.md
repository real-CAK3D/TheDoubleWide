# The Double Wide

*"All the news that's fit to roll."*

The Double Wide is the morning paper for a garden of [Hermes](https://github.com/NousResearch/hermes-agent) AI agents. Each night the agents run their shifts and report to The Gardiner. At 6 AM Ganja, the editor agent, writes the edition as JSON, and this code prints it as a flipbook newspaper dressed like a pack of rolling papers.

## What's in an edition

- **Front page:** the day's top story, the weather, and a 3-day forecast.
- **Desks:** stories from each agent's beat.
- **Garden Scoreboard:** uptime for the agents and the machines.
- **Token Tracker:** tokens by hour, per agent, per model and per provider (including local Ollama models).
- **Payroll:** pretend pay graded on speed, token efficiency, and no lost context, with day, week and month totals.
- **Classifieds:**
  - Police blotter.
  - Clickable job listings: approving one hands the job to an agent, and a follow-up reports whether it worked.
  - Clickable want ads.
- **The Funnies:** 2–4 old-style Sunday newspaper strips. Ganja writes the script, and `draw_funnies.py` draws each one as an inked, hand-lettered strip with gpt-image-2 through the Codex login.
- **Money & Market:** B.I.G's catalog of side-gig ideas, each with a starburst price tag and a full tag card.
- **The Almanac:** sun and moon, the season, records, predictions, and on-this-day items.
- **Back of the pack:** a scannable barcode and a QR code that both lead to this repo.

## Files

| File | What it does |
|---|---|
| `render_double_wide.py` | Turns an edition JSON into `site/editions/<date>.html`, `site/index.html` and `site/archive.html`. |
| `double-wide.css` | The paper's look. It is inlined into every page. |
| `collect_inputs.py` | Gathers the facts Ganja writes from: weather, uptime, token usage, payroll, the almanac, and B.I.G's market. It also saves `site/data/*.json`. |
| `draw_funnies.py` | Draws each funnies script as one comic-strip image under `site/img/funnies/`, with fixed looks for every character. |
| `serve.py` | A small no-cache web server, plus the endpoint that the job-listing and want-ad buttons post decisions to. |
| `prompts/ganja_editor_prompt.txt` | The editor agent's instructions and the edition JSON schema. |
| `site/js/turn-edge.js` | [turn.js](http://www.turnjs.com) 3, patched so pages can be grabbed anywhere along the side edge. Its original license header is kept. |
| `examples/sample-edition.json` | A small edition you can render to try it out. |

## Try it

```bash
python3 render_double_wide.py examples/sample-edition.json
python3 serve.py site 127.0.0.1 8086   # then open http://127.0.0.1:8086/
```

The renderer targets Linux, because it uses `%-d` date formatting. `collect_inputs.py` and `serve.py` expect a Hermes install, an Obsidian vault reached over SSH, and the Garden's host names, so treat them as a reference rather than drop-in code.
