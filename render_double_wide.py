#!/usr/bin/env python3
"""Render an edition of THE DOUBLE WIDE (CAK3D's morning paper) as a turn.js flipbook.

Usage: render_double_wide.py <edition.json>
Writes site/editions/<date>.html, refreshes site/index.html (latest) and site/archive.html.
Edition JSON is written each morning by Ganja; weather comes from site/data/weather-<date>.json.
Pages turn with turn.js (personal-use license, loaded from cdnjs) — desktop shows two-page spreads,
phones one page; drag a corner, swipe, or use the arrow buttons. Job Listings are clickable
(approve / mark done / not now) via serve.py's /api/jobs.
"""
import datetime as dt, glob, html, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
CSS_FILE = "double-wide.css"   # sister papers that reuse this flipbook point this at their own stylesheet
AGENTS = {
    "Ganja": "ganja", "The Gardiner": "gardener", "Gardiner": "gardener", "CHRONIC": "chronic", "Chronic": "chronic",
    "Maple": "maple", "Herbie": "herbie", "Homie": "homie", "Ibby": "ibby", "Disco Stu": "discostu", "BAK3R": "bak3r",
    "CYPH3R": "cyph3r", "Clydius": "clydius", "tinyZ": "tinyz", "tiny-Z": "tinyz", "Fat Man": "fatman", "Little Boy": "littleboy", "B.I.G": "big",
}
COMIC_BG = ["#ffd84d", "#7fd3f7", "#ff9fb2", "#b7e36b", "#ffb347", "#c9a7ff"]
e = lambda s: html.escape(str(s or ""))


def para(text):
    out = []
    for p in re.split(r"\n\s*\n", str(text or "").strip()):
        if p:
            p = e(p).replace("\n", "<br>")
            out.append("<p>" + re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p) + "</p>")
    return "".join(out)


def mug(agent, cls="mug"):
    slug = AGENTS.get(str(agent or "").strip())
    if slug and os.path.exists(os.path.join(SITE, "img", slug + ".png")):
        return '<img class="%s" src="../img/%s.png" alt="%s">' % (cls, slug, e(agent))
    if agent:
        return '<span class="%s mono" aria-hidden="true">%s</span>' % (cls, e(str(agent)[:1]))
    return ""


def story(s, lead=False):
    if not isinstance(s, dict):
        return ""
    tag = '<div class="kicker">%s</div>' % e(s.get("tag")) if s.get("tag") else ""
    by = '<div class="byline">%s<span>By %s</span></div>' % (mug(s.get("agent")), e(s.get("agent"))) if s.get("agent") else ""
    dek = '<p class="dek">%s</p>' % e(s.get("dek")) if s.get("dek") else ""
    return '<article class="%s">%s<h3>%s</h3>%s%s%s</article>' % (
        "story lead" if lead else "story", tag, e(s.get("title")), dek, by, para(s.get("body")))


WX_ICONS = [("thunder", "⛈"), ("snow", "❄"), ("sleet", "🌨"), ("rain", "🌧"), ("shower", "🌦"), ("drizzle", "🌦"),
            ("fog", "🌫"), ("partly", "⛅"), ("mostly cloudy", "☁"), ("cloudy", "☁"), ("overcast", "☁"),
            ("mostly sunny", "🌤"), ("sunny", "☀"), ("clear", "☀"), ("wind", "💨")]


def wx_icon(text):
    t = str(text or "").lower()
    return next((i for k, i in WX_ICONS if k in t), "🌤")


def weather_block(date):
    try:
        w = json.load(open(os.path.join(SITE, "data", "weather-%s.json" % date)))
    except Exception:
        return '<div class="box weather"><h2>Weather</h2><p>The weather desk overslept.</p></div>'
    now = w.get("now") or {}
    days = w.get("days") or []
    if not days:  # older weather files: build day cards from the forecast periods
        ps = w.get("periods") or []
        days = [{"name": p.get("name"), "high": p.get("temp"), "low": None, "short": p.get("short")}
                for p in ps if "night" not in str(p.get("name", "")).lower()][:3]
    cards = "".join(
        '<div class="wx-day"><div class="wx-dname">%s</div><div class="wx-icon">%s</div>'
        '<div class="wx-hl"><b>%s°</b>%s</div><div class="wx-short">%s</div>%s</div>'
        % (e(str(d.get("name", ""))[:3].upper() if d.get("name") not in ("Today", "Tonight", "This Afternoon") else "TODAY"),
           wx_icon(d.get("short")), e(d.get("high")), (" / %s°" % e(d.get("low"))) if d.get("low") is not None else "",
           e(d.get("short")), ('<div class="wx-pop">💧 %s%%</div>' % e(d.get("pop"))) if d.get("pop") else "")
        for d in days[:3])
    return ('<div class="box weather"><h2>Weather</h2><div class="wx-now"><span class="wx-bigicon">%s</span>'
            '<span class="wx-temp">%s°</span><span>%s<br><small>%s · humidity %s%%</small></span></div>'
            '<div class="wx-3day"><div class="wx-label">3-Day Forecast</div><div class="wx-days">%s</div></div>'
            '<p class="small">%s</p></div>'
            % (wx_icon(now.get("text")), e(now.get("temp_f")), e(now.get("text")), e(w.get("place")), e(now.get("humidity")),
               cards, e((w.get("today") or {}).get("detail"))))


def jobs_block(items):
    rows = []
    for i, it in enumerate(items or []):
        if not isinstance(it, dict):
            continue
        rows.append(
            '<button type="button" class="ad job" data-idx="%d">%s<div class="job-txt"><b>%s</b>%s'
            '<div>%s</div>%s<div class="job-status" data-status="open">Tap to approve or handle ›</div></div></button>'
            % (i, mug(it.get("agent"), "mug sm"), e(it.get("title")),
               (' <span class="tag">%s</span>' % e(it.get("agent"))) if it.get("agent") else "",
               e(it.get("details") or it.get("text")),
               ('<div class="ask">➜ %s</div>' % e(it.get("ask"))) if it.get("ask") else ""))
    return "".join(rows) or '<p class="small">No job listings today. Everybody\'s employed.</p>'


def ads_block(items):
    rows = []
    for it in items or []:
        if isinstance(it, dict):
            rows.append('<div class="ad">%s<div><b>%s</b>%s<div>%s</div></div></div>'
                        % (mug(it.get("agent"), "mug sm"), e(it.get("title")),
                           (' <span class="tag">%s</span>' % e(it.get("agent"))) if it.get("agent") else "",
                           e(it.get("details") or it.get("text"))))
    return "".join(rows) or '<p class="small">No want ads today.</p>'


def comic(fun):
    panels = []
    for i, p in enumerate(fun.get("panels") or []):
        if not isinstance(p, dict):
            p = {"caption": p}
        cast = p.get("cast") or ([{"agent": p.get("agent"), "says": p.get("says") or p.get("caption")}] if p.get("agent") else [])
        narr = p.get("caption") if p.get("cast") or p.get("says") else (p.get("narration") or "")
        people = "".join(
            '<div class="actor">%s%s</div>' % (
                ('<div class="bubble">%s</div>' % e(c.get("says"))) if c.get("says") else "", mug(c.get("agent"), "mug toon"))
            for c in cast if isinstance(c, dict))
        panels.append(
            '<div class="cpanel" style="--bg:%s">%s%s<div class="stage">%s</div></div>'
            % (COMIC_BG[i % len(COMIC_BG)], ('<div class="narr">%s</div>' % e(narr)) if narr else "",
               ('<div class="sfx">%s</div>' % e(p.get("sfx"))) if p.get("sfx") else "", people))
    return ('<div class="sunday"><div class="sunday-head"><span>THE</span> SUNDAY FUNNIES</div>'
            '<div class="comic-title">%s</div><div class="cpanels">%s</div>%s</div>'
            % (e(fun.get("title")), "".join(panels), ('<p class="joke">%s</p>' % e(fun.get("joke"))) if fun.get("joke") else ""))



def _streak(h):
    if not h:
        return ""
    d, hh = int(h // 24), int(h % 24)
    return ("%dd %dh" % (d, hh)) if d else ("%dh" % hh)


def scoreboard_block(date):
    try:
        u = json.load(open(os.path.join(SITE, "data", "uptime-%s.json" % date)))
    except Exception:
        return '<div class="box scoreboard"><h2>Uptime Scoreboard</h2><p class="small">No scoreboard today.</p></div>'
    def row(x, is_machine=False):
        st = str(x.get("status", ""))
        cls = "up" if st in ("up", "shift ok") else ("warn" if st.startswith("shift") and "error" not in st else "down")
        who = ('<span class="mug sm mono">%s</span>' % ("🖥" if is_machine else e(x["name"][:1]))) if is_machine else mug(x["name"], "mug sm")
        return ('<li class="sb-row"><span class="light %s"></span>%s<span class="sb-name">%s<small>%s</small></span><span class="sb-streak">%s</span></li>'
                % (cls, who, e(x["name"]), e(x.get("kind") or st), e(_streak(x.get("streak_h")) or st)))
    best = u.get("longest") or {}
    top = ('<p class="sb-best">🏆 Longest streak: <b>%s</b> — %s</p>' % (e(best.get("name")), e(_streak(best.get("streak_h"))))) if best else ""
    return ('<div class="box scoreboard"><h2>Uptime Scoreboard</h2>%s<div class="sb-cols"><div><h4>Agents</h4><ul>%s</ul></div>'
            '<div><h4>Machines</h4><ul>%s</ul></div></div></div>'
            % (top, "".join(row(x) for x in u.get("agents") or []), "".join(row(x, True) for x in u.get("machines") or [])))


def coming_block(items):
    rows = "".join('<li><span class="cu-when">%s</span>%s<span>%s</span></li>' % (e(x.get("when")), mug(x.get("agent"), "mug xs"), e(x.get("what")))
                   for x in items or [] if isinstance(x, dict))
    return '<div class="box coming"><h2>Coming Up</h2><ul class="cu">%s</ul></div>' % (rows or "<li>Nothing on the calendar. Enjoy it.</li>")


def market_block(m):
    items = [x for x in (m or []) if isinstance(x, dict)]
    if not items:
        return ('<div class="market-teaser"><div class="kicker">Coming soon</div><h3>B.I.G opens for business</h3>'
                '<p>The Budding Investment Garden is setting up shop. Once B.I.G is online, this page carries fresh ways to make quick cash '
                'and resale finds every morning — each one with what it takes and what it might pay.</p>'
                '<p class="small">Until then, this shelf stays empty on purpose: no made-up money tips.</p></div>')
    return "".join('<div class="ad">%s<div><b>%s</b>%s<div>%s</div>%s</div></div>'
                   % (mug(x.get("agent") or "B.I.G", "mug sm"), e(x.get("title")),
                      (' <span class="tag">%s</span>' % e(x.get("tag"))) if x.get("tag") else "", e(x.get("text")),
                      ('<div class="ask">➜ %s</div>' % e(x.get("payoff"))) if x.get("payoff") else "") for x in items)



def _k(n):
    n = float(n or 0)
    return ("%.1fM" % (n / 1e6)) if n >= 1e6 else ("%.0fk" % (n / 1e3)) if n >= 1e3 else "%d" % n


def tokens_block(date):
    try:
        u = json.load(open(os.path.join(SITE, "data", "usage-%s.json" % date)))
    except Exception:
        return '<div class="box tokens"><h2>Token Tracker</h2><p class="small">No usage figures today.</p></div>'
    hrs = u.get("hours") or [0] * 24
    top = max(hrs) or 1
    peak = max(range(24), key=lambda h: hrs[h])
    bars = "".join('<div class="tk-bar%s" title="%s:00 — %s tokens"><span style="height:%d%%"></span><i>%s</i></div>'
                   % (" peak" if h == peak and hrs[h] else "", h, _k(hrs[h]), max(2, round(hrs[h] / top * 100)) if hrs[h] else 0,
                      (str(h % 12 or 12) + ("a" if h < 12 else "p")) if h % 3 == 0 else "") for h in range(24))
    def table(title, d, is_agent=False):
        d = d or {}
        mx = max(d.values()) if d else 1
        rows = "".join('<li>%s<span class="tk-name">%s</span><span class="tk-meter"><span style="width:%d%%"></span></span><b>%s</b></li>'
                       % (mug(k, "mug xs") if is_agent else "", e(k), max(3, round(v / mx * 100)), _k(v)) for k, v in list(d.items())[:10])
        return '<div class="tk-list"><h4>%s</h4><ul>%s</ul></div>' % (title, rows or "<li>—</li>")
    return ('<div class="box tokens"><h2>Token Tracker</h2>'
            '<div class="tk-sum"><div><b>%s</b><small>tokens</small></div><div><b>%s</b><small>cached reads</small></div>'
            '<div><b>~%s</b><small>Hermes API calls</small></div><div><b>%s:00</b><small>busiest hour</small></div></div>'
            '<div class="tk-chart">%s</div>'
            '<div class="tk-grid">%s%s%s</div><p class="small">%s%s</p></div>'
            % (_k(u.get("total")), _k(u.get("cache_read")), e(u.get("calls")), peak, bars,
               table("By agent", u.get("by_agent"), True), table("By model", u.get("by_model")), table("By provider", u.get("by_provider")),
               e(u.get("note")), "" if u.get("pc_included") else " PC usage (Claude Code / Codex) not included today."))




# ---------------------------------------------------------------- newspaper sections
def sec(letter, name, num, kicker=""):
    return ('<div class="sec-banner"><span class="sec-letter">%s</span><span class="sec-name">%s</span>%s<span class="sec-pg">%s%d</span></div>'
            % (letter, e(name), ('<span class="sec-kick">%s</span>' % e(kicker)) if kicker else "", letter, num))


# ---------------------------------------------------------------- Section B: the Garden Token Average (a DOW for tokens)
SYMBOLS = {"Ganja": "GNJA", "The Gardiner": "GRDN", "CHRONIC": "CHRN", "Maple": "MAPL", "Herbie": "HRBE", "Homie": "HOMY", "Ibby": "IBBY",
           "Disco Stu": "STU", "BAK3R": "BAKR", "CYPH3R": "CYPH", "Clydius": "CLYD", "tinyZ": "TNYZ", "Fat Man": "FATM", "Little Boy": "LTLB",
           "B.I.G": "BIG"}


def sym(name):
    return SYMBOLS.get(name) or (re.sub(r"[^A-Za-z]", "", str(name)).upper()[:4] or "?")


def _chg(now, before):
    if not before:
        return "new", "flat", "—"
    pct = (now - before) / before * 100
    cls = "up" if pct > 0.5 else "down" if pct < -0.5 else "flat"
    return "%s%.1f%%" % ("▲" if pct > 0 else "▼" if pct < 0 else "", abs(pct)), cls, ("%+.0fk" % ((now - before) / 1000))


def tokens_dow(date):
    try:
        u = json.load(open(os.path.join(SITE, "data", "usage-%s.json" % date)))
    except Exception:
        return '<div class="box dow"><h2>The Garden Token Average</h2><p class="small">The market was closed — no usage figures today.</p></div>'
    prev_day = (dt.date.fromisoformat(date) - dt.timedelta(days=1)).isoformat()
    try:
        pu = json.load(open(os.path.join(SITE, "data", "usage-%s.json" % prev_day)))
    except Exception:
        pu = {}
    total, ptotal = u.get("total") or 0, pu.get("total") or 0
    pct, cls, delta = _chg(total, ptotal)
    hrs = u.get("hours") or [0] * 24
    cum, run = [], 0
    for h in hrs:
        run += h
        cum.append(run)
    W, H, top = 600, 170, max(cum[-1], 1)
    vol_top = max(hrs) or 1
    line = " ".join("%.1f,%.1f" % (i * W / 23, H - 12 - cum[i] / top * (H - 40)) for i in range(24))
    bars = "".join('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>' % (i * W / 24 + 2, H - hrs[i] / vol_top * 34, W / 24 - 4, hrs[i] / vol_top * 34)
                   for i in range(24) if hrs[i])
    ticks = "".join('<text x="%.1f" y="%d">%s</text>' % (i * W / 23, H + 14, (str(i % 12 or 12) + ("a" if i < 12 else "p"))) for i in range(0, 24, 3))
    chart = ('<svg class="dow-chart" viewBox="0 -6 %d %d" preserveAspectRatio="none" role="img" aria-label="tokens through the day">'
             '<g class="vol">%s</g><polygon class="area" points="0,%d %s %d,%d"/><polyline class="ln" points="%s"/><g class="tk">%s</g></svg>'
             % (W, H + 22, bars, H - 12, line, W, H - 12, line, ticks))

    def movers(cur, old, is_agent):
        rows = []
        for k, v in sorted((cur or {}).items(), key=lambda kv: -kv[1])[:12]:
            pc, c, d = _chg(v, (old or {}).get(k, 0))
            rows.append('<tr class="%s"><td class="sym">%s</td><td class="nm">%s%s</td><td class="num">%s</td><td class="num chg">%s</td><td class="num">%s</td></tr>'
                        % (c, e(sym(k)) if is_agent else "", mug(k, "mug xs") if is_agent else "", e(k), _k(v), pc, d))
        return "".join(rows) or '<tr><td colspan="5">—</td></tr>'
    tape = " ".join('<span class="%s">%s %s %s</span>' % (_chg(v, (pu.get("by_agent") or {}).get(k, 0))[1], e(sym(k)), _k(v),
                                                          _chg(v, (pu.get("by_agent") or {}).get(k, 0))[0])
                    for k, v in sorted((u.get("by_agent") or {}).items(), key=lambda kv: -kv[1]))
    peak = max(range(24), key=lambda h: hrs[h])
    return ('<div class="dow"><div class="ticker"><div class="tape">%s &nbsp;·&nbsp; %s</div></div>'
            '<div class="dow-head"><div><div class="dow-name">The Garden Token Average</div><div class="small">GTA · tokens burned across the Garden · %s</div></div>'
            '<div class="dow-quote %s"><b>%s</b><span>%s</span><small>%s vs. yesterday</small></div></div>'
            '<div class="dow-stats"><div><small>Volume (API calls)</small><b>~%s</b></div><div><small>Cached reads</small><b>%s</b></div>'
            '<div><small>Busiest hour</small><b>%d:00</b></div><div><small>Yesterday\'s close</small><b>%s</b></div></div>'
            '%s<p class="small dow-note">Line: running total through the day · bars: tokens each hour. ▲ red = burned more than yesterday, ▼ green = leaner.</p>'
            '<div class="dow-tables"><div><h4>Most Active — by agent</h4><table class="quotes"><thead><tr><th>Sym</th><th>Agent</th><th>Tokens</th><th>Chg</th><th>Net</th></tr></thead><tbody>%s</tbody></table></div>'
            '<div><h4>Sectors — by model</h4><table class="quotes"><thead><tr><th></th><th>Model</th><th>Tokens</th><th>Chg</th><th>Net</th></tr></thead><tbody>%s</tbody></table>'
            '<h4>Exchanges — by provider</h4><table class="quotes"><thead><tr><th></th><th>Provider</th><th>Tokens</th><th>Chg</th><th>Net</th></tr></thead><tbody>%s</tbody></table></div></div>'
            '<p class="small">%s%s</p></div>'
            % (tape, tape, e(u.get("day") or prev_day), cls, _k(total), pct, delta, e(u.get("calls")), _k(u.get("cache_read")), peak, _k(ptotal) if ptotal else "—",
               chart, movers(u.get("by_agent"), pu.get("by_agent"), True), movers(u.get("by_model"), pu.get("by_model"), False),
               movers(u.get("by_provider"), pu.get("by_provider"), False),
               e(u.get("note")), "" if u.get("pc_included") else " PC usage (Claude Code / Codex) not included today."))


# ---------------------------------------------------------------- Section C: the Sports Section
def sports_block(date):
    try:
        up = json.load(open(os.path.join(SITE, "data", "uptime-%s.json" % date)))
    except Exception:
        up = {}
    try:
        pay = json.load(open(os.path.join(SITE, "data", "payroll-%s.json" % date)))
    except Exception:
        pay = {}
    prow = {r.get("agent"): r for r in pay.get("rows") or []}
    teams = []
    for a in up.get("agents") or []:
        st = str(a.get("status", ""))
        light = "up" if st in ("up", "shift ok") else ("warn" if st.startswith("shift") and "error" not in st else "down")
        r = prow.get(a["name"], {})
        teams.append((a.get("streak_h") or 0, '<tr><td class="team">%s<span>%s</span></td><td><span class="light %s"></span></td><td class="num">%s</td>'
                      '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td></tr>'
                      % (mug(a["name"], "mug xs"), e(a["name"]), light, e(_streak(a.get("streak_h")) or st), e(r.get("jobs", "—")),
                         e(r.get("grade", "—")), ("$%.2f" % r["week"]) if "week" in r else "—")))
    teams.sort(key=lambda t: -t[0])
    box = "".join('<tr><td class="team">%s<span>%s</span></td><td class="num">%s</td><td class="num">%s</td><td class="num">%s</td><td class="num">$%.2f</td></tr>'
                  % (mug(r["agent"], "mug xs"), e(r["agent"]), e(r.get("jobs")), e(r.get("per_job")), e(r.get("grade")), r.get("today", 0))
                  for r in pay.get("rows") or [] if r.get("jobs"))
    fac = "".join('<tr><td class="team">🖥 <span>%s</span></td><td><span class="light %s"></span></td><td class="num">%s</td><td>%s</td></tr>'
                  % (e(m["name"]), "up" if m.get("status") == "up" else "down", e(_streak(m.get("streak_h")) or m.get("status")), e(m.get("kind") or ""))
                  for m in up.get("machines") or [])
    eotd, best = pay.get("employee_of_the_day") or {}, up.get("longest") or {}
    head = ("%s takes Player of the Game" % eotd["agent"]) if eotd.get("agent") else ("Streak watch: %s" % best.get("name")) if best else "Quiet night in the Garden League"
    return ('<div class="sports"><h2 class="sp-head">%s</h2>'
            '<div class="sp-top">%s%s</div>'
            '<div class="sp-cols"><div><h4>Garden League Standings</h4><table class="agate"><thead><tr><th>Team</th><th></th><th>Streak</th><th>Jobs</th><th>Grade</th><th>Pay wk</th></tr></thead>'
            '<tbody>%s</tbody></table></div>'
            '<div><h4>Last Night\'s Box Score</h4><table class="agate"><thead><tr><th>Player</th><th>Jobs</th><th>Tok/job</th><th>Grade</th><th>Pay</th></tr></thead>'
            '<tbody>%s</tbody></table><h4>Facilities Report</h4><table class="agate"><thead><tr><th>Machine</th><th></th><th>Up</th><th></th></tr></thead><tbody>%s</tbody></table></div></div></div>'
            % (e(head),
               ('<div class="sp-mvp">%s<div><span class="kicker">Player of the Game</span><b>%s</b><div>%s</div></div></div>' % (mug(eotd["agent"], "mug"), e(eotd["agent"]), e(eotd.get("why")))) if eotd.get("agent") else "",
               ('<div class="sp-streak"><span class="kicker">Streak Watch</span><b>%s</b><div>%s straight without a stumble</div></div>' % (e(best.get("name")), e(_streak(best.get("streak_h"))))) if best else "",
               "".join(t[1] for t in teams) or '<tr><td colspan="6">No standings today.</td></tr>',
               box or '<tr><td colspan="5">No games last night.</td></tr>', fac or '<tr><td colspan="4">—</td></tr>'))


# ---------------------------------------------------------------- listings (jobs + want ads), clickable
def listing_block(items, kind):
    """Job Listings (kind='job') and Want Ads (kind='want') are both tappable: approve / handle / not now (+ link)."""
    rows = []
    for i, it in enumerate(items or []):
        if not isinstance(it, dict):
            continue
        rows.append(
            '<button type="button" class="ad job" data-kind="%s" data-idx="%d">%s<div class="job-txt"><b>%s</b>%s'
            '<div>%s</div>%s<div class="job-status" data-status="open">%s</div></div></button>'
            % (kind, i, mug(it.get("agent"), "mug sm"), e(it.get("title")),
               (' <span class="tag">%s</span>' % e(it.get("agent"))) if it.get("agent") else "",
               e(it.get("details") or it.get("text")),
               ('<div class="ask">➜ %s</div>' % e(it.get("ask"))) if it.get("ask") else "",
               "Tap to approve or handle ›" if kind == "job" else "Tap to answer this ad ›"))
    empty = "No job listings today. Everybody's employed." if kind == "job" else "No want ads today."
    return "".join(rows) or '<p class="small">%s</p>' % e(empty)


def followups_block(date):
    """Results of listings CAK3D approved in the last few editions (filled in by serve.py when the agent finishes)."""
    rows = []
    jd = os.path.join(ROOT, "jobs")
    for f in sorted(glob.glob(os.path.join(jd, "*.json")))[-4:]:
        try:
            st = json.load(open(f))
        except Exception:
            continue
        for k, v in st.items():
            if v.get("status") != "approved":
                continue
            res = v.get("result_status")
            icon = {"ok": "✅", "failed": "❌", "needs": "👉"}.get(res, "⏳")
            rows.append('<li><span class="fu-icon">%s</span><div><b>%s</b> <span class="small">(approved %s)</span><div class="small">%s</div></div></li>'
                        % (icon, e(v.get("title")), e(str(v.get("at", ""))[:10]),
                           e(v.get("result") or "Still working on it — the report posts in Ganja's channel when it's done.")))
    if not rows:
        return ""
    return '<div class="box followups"><h2>Follow-ups</h2><p class="small">What happened to the jobs you approved</p><ul class="fu">%s</ul></div>' % "".join(rows[-8:])


# ---------------------------------------------------------------- B.I.G's catalog
def catalog_block(items):
    items = [x for x in (items or []) if isinstance(x, dict)]
    if not items:
        return ('<div class="market-teaser"><div class="kicker">Coming soon</div><h3>B.I.G opens for business</h3>'
                '<p>The Budding Investment Garden is setting up shop. Once B.I.G files his first catalog, this page lists quick-cash ideas '
                'and side gigs — each with its price tag, what it takes, what it might pay, and the risk.</p>'
                '<p class="small">Until then, this shelf stays empty on purpose: no made-up money tips.</p></div>')
    cards = []
    for i, x in enumerate(items):
        cards.append(
            '<button type="button" class="cat-item" data-idx="%d"><span class="burst"><span>%s</span></span>'
            '<span class="cat-no">ITEM No. %s</span><b class="cat-title">%s</b>%s<span class="cat-desc">%s</span>'
            '<span class="cat-meta"><span>⏱ %s</span><span>⚠ %s risk</span></span><span class="cat-more">See details ›</span></button>'
            % (i, e(x.get("price") or x.get("income_week") or "?"), e(x.get("item_no") or "%03d-%02d" % (27 + i, i + 1)),
               e(x.get("title")), ('<span class="cat-tag">%s</span>' % e(x.get("tag"))) if x.get("tag") else "",
               e(x.get("desc") or x.get("text")), e(x.get("tend") or "?"), e((x.get("risk") or "?").split(" ")[0])))
    return ('<div class="catalog-head"><span>B.I.G\'s</span> Wish-Book of Quick Cash<small>All prices are weekly estimates · tap any item for the full tag</small></div>'
            '<div class="catalog">%s</div>' % "".join(cards))


# ---------------------------------------------------------------- newspaper comic strips
def strips_block(fun):
    strips = fun.get("strips") or []
    if not strips and fun.get("panels"):   # older single-strip editions
        strips = [{"title": fun.get("title"), "panels": fun.get("panels")}]
    out = []
    for s in strips[:4]:
        if not isinstance(s, dict):
            continue
        if s.get("image"):   # drawn by draw_funnies.py: one inked strip, lettering included
            said = " / ".join("%s: %s" % (c.get("agent"), c.get("says")) for p in (s.get("panels") or []) if isinstance(p, dict)
                              for c in (p.get("cast") or []) if isinstance(c, dict) and c.get("says"))
            out.append('<figure class="strip-art"><a href="%s" target="_blank" rel="noopener"><img src="%s" loading="lazy" alt="%s"></a></figure>'
                       % (e(s["image"]), e(s["image"]), e("%s %s. %s" % (s.get("title") or "", s.get("byline") or "", said))))
            continue
        panels = []
        for p in (s.get("panels") or [])[:4]:
            if not isinstance(p, dict):
                p = {"caption": p}
            cast = p.get("cast") or ([{"agent": p.get("agent"), "says": p.get("says") or p.get("caption")}] if p.get("agent") else [])
            narr = p.get("caption") if (p.get("cast") or p.get("says")) else (p.get("narration") or "")
            people = "".join('<div class="ink-actor">%s%s</div>' % (('<div class="balloon">%s</div>' % e(c.get("says"))) if c.get("says") else "",
                                                                       mug(c.get("agent"), "mug ink"))
                             for c in cast if isinstance(c, dict))
            panels.append('<div class="ink-panel">%s%s<div class="ink-stage">%s</div></div>'
                          % (('<div class="ink-narr">%s</div>' % e(narr)) if narr else "",
                             ('<div class="ink-sfx">%s</div>' % e(p.get("sfx"))) if p.get("sfx") else "", people))
        out.append('<div class="strip-row"><div class="strip-name">%s<span>%s</span></div><div class="ink-panels">%s</div></div>'
                   % (e(s.get("title")), e(s.get("byline") or "by the Garden Gang"), "".join(panels)))
    joke = ('<p class="joke">%s</p>' % e(fun.get("joke"))) if fun.get("joke") else ""
    return '<div class="funnies-news"><div class="fn-head">The Funnies</div>%s%s</div>' % ("".join(out), joke)


# ---------------------------------------------------------------- the almanac
def almanac_block(date, notes, numbers):
    try:
        a = json.load(open(os.path.join(SITE, "data", "almanac-%s.json" % date)))
    except Exception:
        a = {}
    notes = notes if isinstance(notes, dict) else {}
    sky = a.get("sky") or {}
    season = a.get("season") or {}
    records = a.get("records") or {}
    def lis(xs):
        return "".join("<li>%s</li>" % e(x) for x in xs if x)
    sky_html = lis([
        sky.get("sunrise") and "Sunrise %s · Sunset %s" % (sky.get("sunrise"), sky.get("sunset")),
        sky.get("daylength") and "Daylight %s (%s since yesterday)" % (sky.get("daylength"), sky.get("daydelta")),
        sky.get("moon") and "Moon: %s, %s%% lit" % (sky.get("moon"), sky.get("illum")),
        sky.get("next_full") and "Next full moon %s · next new moon %s" % (sky.get("next_full"), sky.get("next_new")),
    ])
    season_html = lis(season.get("lines") or [])
    records_html = lis(records.get("lines") or [])
    nums = "".join("<li><b>%s</b> %s</li>" % (e(k), e(v)) for k, v in (numbers or {}).items())
    col = lambda title, body: ('<div class="alm-sec"><h4>%s</h4><ul>%s</ul></div>' % (title, body)) if body else ""
    return ('<div class="almanac-page"><div class="alm-head">The Garden Almanac<small>for the year 2026 · calculated for Lewiston, Maine</small></div>'
            '<div class="alm-cols">%s%s%s%s%s%s%s</div>%s</div>'
            % (col("The Sky", sky_html), col("The Season", season_html), col("Garden Records", records_html),
               col("Predictions &amp; Outlook", lis(notes.get("predictions") or [])),
               col("On This Day", lis(notes.get("on_this_day") or [])),
               col("Planting &amp; Tending", lis(notes.get("tending") or [])),
               col("By the Numbers", nums),
               ('<div class="alm-foot">%s%s</div>' % (('<p class="alm-saying">“%s”</p>' % e(notes.get("saying"))) if notes.get("saying") else "",
                                                     ('<p class="small">Oddity of the day: %s</p>' % e(notes.get("oddity"))) if notes.get("oddity") else ""))))


# ---------------------------------------------------------------- payroll
def payroll_block(date):
    try:
        p = json.load(open(os.path.join(SITE, "data", "payroll-%s.json" % date)))
    except Exception:
        return '<div class="box payroll"><h2>Payroll</h2><p class="small">Payroll office closed today.</p></div>'
    rows = "".join(
        '<tr><td>%s<span>%s</span></td><td>%s</td><td>%s</td><td>%s</td><td class="pay">$%s</td><td>$%s</td><td>$%s</td></tr>'
        % (mug(r["agent"], "mug xs"), e(r["agent"]), e(r.get("jobs")), e(r.get("grade")), e(r.get("per_job")),
           e("%.2f" % r.get("today", 0)), e("%.2f" % r.get("week", 0)), e("%.2f" % r.get("month", 0)))
        for r in p.get("rows") or [])
    eotd = p.get("employee_of_the_day")
    return ('<div class="box payroll"><h2>Payroll</h2><p class="small">Pretend pay, real scorekeeping: base pay per job, bonuses for finishing fast and '
            'lean on tokens, docked for errors, reruns or lost context. %s</p>%s'
            '<table class="paytab"><thead><tr><th>Agent</th><th>Jobs</th><th>Grade</th><th>Tokens/job</th><th>Today</th><th>Week</th><th>Month</th></tr></thead>'
            '<tbody>%s</tbody></table></div>'
            % (e(p.get("period")), ('<p class="eotd">🏅 Employee of the Day: <b>%s</b> — %s</p>' % (e(eotd.get("agent")), e(eotd.get("why")))) if eotd else "", rows))


# ---------------------------------------------------------------- a real, scannable barcode (Code 128-B)
_C128 = ["212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213", "221312", "231212", "112232",
         "122132", "122231", "113222", "123122", "123221", "223211", "221132", "221231", "213212", "223112", "312131", "311222", "321122",
         "321221", "312212", "322112", "322211", "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311",
         "211313", "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331", "231131", "213113",
         "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111", "314111", "221411", "431111", "111224", "111422",
         "121124", "121421", "141122", "141221", "112214", "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111",
         "241112", "134111", "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141", "214121",
         "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141", "114131", "311141", "411131", "211412",
         "211214", "211232", "2331112"]


def code128_svg(text):
    codes = [104] + [ord(ch) - 32 for ch in text]
    check = (codes[0] + sum(i * c for i, c in enumerate(codes[1:], 1))) % 103
    pattern = "".join(_C128[c] for c in codes + [check]) + _C128[106]
    x, bars = 10, []
    for i, w in enumerate(pattern):
        w = int(w)
        if i % 2 == 0:
            bars.append('<rect x="%d" y="0" width="%d" height="60"/>' % (x, w))
        x += w
    return ('<svg class="barcode-svg" viewBox="0 0 %d 60" preserveAspectRatio="none" role="img" aria-label="barcode: %s">%s</svg>'
            % (x + 10, e(text), "".join(bars)))


def page(title, inner, extra=""):
    return '<div class="pg" data-title="%s"><div class="page-in%s">%s</div></div>' % (e(title), extra, inner)


def render(ed):
    date = ed.get("date") or dt.date.today().isoformat()
    d = dt.date.fromisoformat(date)
    no = ed.get("edition_no") or (d - dt.date(2026, 9, 26)).days + 1
    head = ed.get("headline") or {}
    fun = ed.get("funnies") or {}
    market = ed.get("market") or []
    try:   # B.I.G's catalog is copied in by the collector; never retyped by the editor
        market = market or json.load(open(os.path.join(SITE, "data", "market-%s.json" % date))).get("items") or []
    except Exception:
        pass
    keys = para(ed.get("logins_and_keys")) or "<p>No report.</p>"
    blotter = "".join('<li>%s<span><b>%s</b> %s</span></li>' % (mug(b.get("agent"), "mug xs"), e(b.get("time")), e(b.get("text")))
                      for b in ed.get("police_blotter") or [] if isinstance(b, dict))
    almanac = "".join("<li><b>%s</b> %s</li>" % (e(k), e(v)) for k, v in (ed.get("almanac") or {}).items())
    # a real paper: A News · B Business · C Sports · D Classifieds · E Almanac
    pages = [page("A1 · Front Page", sec("A", "News", 1, "Today's top story") + '<div class="front"><div class="front-lead">%s</div><aside class="front-side">%s'
                  '<div class="box keys"><h2>Logins &amp; Keys</h2>%s</div></aside></div>' % (story(head, lead=True), weather_block(date), keys))]
    n = 2
    for s_ in ed.get("sections") or []:
        if isinstance(s_, dict) and s_.get("stories"):
            pages.append(page("A%d · %s" % (n, s_.get("name")), sec("A", "News", n, s_.get("name")) + '<div class="desk"><h2 class="desk-name">%s</h2><div class="cols">%s</div></div>'
                              % (e(s_.get("name")), "".join(story(x) for x in s_["stories"]))))
            n += 1
    sug = [x for x in (ed.get("suggestions") or []) if isinstance(x, dict)]
    if sug:   # ideas for new sections/improvements; CAK3D decides what sticks
        pages.append(page("A%d · Letters to the Editor" % n, sec("A", "Opinion", n, "Letters to the Editor") +
                          '<div class="box letters"><h2>Letters to the Editor</h2><p class="small">Ideas for the paper — tell Ganja which ones to keep</p>%s</div>'
                          % "".join('<div class="ad">%s<div><b>%s</b>%s<div>%s</div></div></div>'
                                    % (mug(x.get("agent"), "mug sm"), e(x.get("title")), (' <span class="tag">%s</span>' % e(x.get("agent"))) if x.get("agent") else "", e(x.get("text")))
                                    for x in sug)))
    pages.append(page("B1 · The Garden Token Average", sec("B", "Business", 1, "Markets") + tokens_dow(date), " biz"))
    pages.append(page("B2 · Payroll", sec("B", "Business", 2, "Payroll") + payroll_block(date), " biz"))
    pages.append(page("B3 · Money & Market", sec("B", "Business", 3, "B.I.G's Wish-Book") + '<div class="box market">%s</div>' % catalog_block(market), " biz"))
    pages.append(page("C1 · Sports", sec("C", "Sports", 1, "The Garden League") + sports_block(date), " sports-page"))
    pages.append(page("D1 · Classifieds", sec("D", "Classifieds", 1) + '<div class="lower two"><div class="box blotter"><h2>Police Blotter</h2><ul>%s</ul></div>'
                      '<div class="box jobs"><h2>Job Listings</h2><p class="small">Help wanted — tap one to approve it or handle it yourself</p>%s</div></div>%s'
                      '<a class="reup-plug" href="/re-up/"><b>Want ads have moved!</b> Everything the agents need is in <i>The Re-Up</i> ›</a>'
                      % (blotter or "<li>A quiet night. Nobody got arrested, not even the cron jobs.</li>",
                         listing_block(ed.get("job_listings"), "job"), followups_block(date))))
    if (fun.get("strips") or fun.get("panels")):   # older editions only; the funnies live in The Sunday Smoke now
        pages.append(page("The Funnies", strips_block(fun), " comic-page"))
    pages.append(page("E1 · Almanac & Calendar", sec("E", "Almanac", 1, "Calendar · Sky · Season") + coming_block(ed.get("coming_up"))
                      + almanac_block(date, ed.get("almanac_notes"), ed.get("almanac"))
                      + '<p class="small center">That\'s the whole pack. <a href="../archive.html">Back issues →</a> · <a href="../catalog.html">B.I.G\'s catalog archive →</a></p>'))
    # hard covers = the outside of the rolling-paper pack
    front_cover = page("The Pack", (
        '<div class="gum"><span>GUMMED · DOUBLE WIDE · 1¼ · SLOW BURNING</span></div>'
        '<div class="pc-top"><div class="seal">%s</div><div class="ear">No. %s<br>%s<br><b>%s</b><br>%s</div></div>'
        '<div class="flag"><div class="est">EST. 2026 · THE GARDEN · LEWISTON, ME</div><h1>The Double<br>Wide</h1>'
        '<div class="motto">“All the news that\'s fit to roll”</div></div>'
        '<div class="pc-band"><span>1¼ SIZE</span><span>32 LEAVES</span><span>SLOW BURNING</span></div>'
        '<div class="pc-teaser"><div class="kicker">Today\'s headline</div><b>%s</b></div>'
        '<div class="pc-open">Open the pack ›</div>')
        % (SEAL, e(no), d.strftime("%a"), d.strftime("%b %-d"), d.strftime("%Y"), e(head.get("title"))), " hardcover")
    back_cover = page("Back of the Pack", (
        '<div class="gum"><span>MADE IN THE GARDEN · ROLLED BY GANJA</span></div>'
        '<div class="pb-body"><div class="seal">%s</div><h2 class="pb-title">The Double Wide</h2>'
        '<p>Printed at dawn on The Garden.<br>Compiled by The Gardiner · Rolled by Ganja.</p>'
        '<p class="pb-warn">CAUTION: contents may contain cron jobs, read-only filesystems and strong opinions.</p>'
        '<div class="codes"><a class="bc-wrap" href="%s" title="TheDoubleWide on GitHub">%s</a><div id="qr" class="qr" data-url="%s"></div></div>'
        '<p class="pb-code">%s · No. %s · scan me</p>'
        '<p><a href="../archive.html">Back issues ›</a></p></div>') % (SEAL, REPO, code128_svg(REPO), REPO, date, e(no)), " hardcover back")
    pages = [front_cover] + pages + [back_cover]
    pick = lambda xs, keys: [{k: x.get(k) for k in keys} for x in (xs or []) if isinstance(x, dict)]
    lists = {"job": pick(ed.get("job_listings"), ("title", "agent", "details", "text", "ask", "url")),
             "market": pick(market, MARKET_KEYS)}
    return book(pages, date=date, no=no, lists=lists)


MARKET_KEYS = ("title", "tag", "price", "desc", "text", "how", "income_week", "tend", "upfront", "weekly_cost", "risk", "links", "item_no")


def book(pages, date, no, lists, paper="The Double Wide", motto="“All the news that's fit to roll”",
         gum="GUMMED · DOUBLE WIDE · 1¼ · SLOW BURNING · 32 LEAVES · MADE IN THE GARDEN", price="PRICE: ONE PINCH",
         delivered="DELIVERED BY GANJA", flap="Printed at dawn on The Garden · Compiled by The Gardiner · Rolled by Ganja",
         body_class="pub-dw", est="EST. 2026 · THE GARDEN · LEWISTON, ME"):
    """Wrap finished pages in the flipbook page (masthead, pager, tap-to-open cards, app hookups)."""
    d = dt.date.fromisoformat(date)
    css = open(os.path.join(ROOT, CSS_FILE)).read()
    list_json = json.dumps(lists, ensure_ascii=False).replace("</", "<\\/")
    out = TEMPLATE
    for k, v in (("@@CSS@@", css), ("@@PAPER@@", e(paper)), ("@@MOTTO@@", e(motto)), ("@@GUM@@", e(gum)), ("@@PRICE@@", e(price)),
                 ("@@DELIVERED@@", e(delivered)), ("@@FLAP@@", e(flap)), ("@@BODYCLASS@@", e(body_class)), ("@@EST@@", e(est)),
                 ("@@DATE_LONG@@", d.strftime("%A, %B %-d, %Y")), ("@@NO@@", e(no)), ("@@DOW@@", d.strftime("%a")),
                 ("@@MD@@", d.strftime("%b %-d")), ("@@YEAR@@", d.strftime("%Y")), ("@@SEAL@@", SEAL),
                 ("@@PAGES@@", "\n".join(pages)), ("@@DATE@@", date), ("@@JOBS@@", list_json)):
        out = out.replace(k, v)
    return out


REPO = "https://github.com/real-CAK3D/TheDoubleWide"

SEAL = ('<svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" stroke-width="4"/>'
        '<path d="M24 78h72v-22l-36-18-36 18z" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round"/>'
        '<rect x="36" y="60" width="14" height="18" fill="currentColor"/><rect x="62" y="60" width="20" height="10" fill="currentColor"/>'
        '<path d="M74 38c4-8 12-8 10-16M82 36c6-6 12-4 12-12" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/></svg>')

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>@@PAPER@@ — @@DATE_LONG@@</title>
<link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#2a1a10">
<link rel="icon" href="/icons/icon-192.png"><link rel="apple-touch-icon" href="/icons/icon-192.png">
<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><script src="/app.js" defer></script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Abril+Fatface&family=UnifrakturMaguntia&family=Bangers&family=Patrick+Hand+SC&family=Oswald:wght@400;600;700&family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>@@CSS@@</style></head><body class="@@BODYCLASS@@">
<div class="pack">
  <div class="gum"><span>@@GUM@@</span></div>
  <header class="cover">
    <div class="seal">@@SEAL@@</div>
    <div class="flag"><div class="est">@@EST@@</div><h1>@@PAPER@@</h1>
      <div class="motto">@@MOTTO@@</div></div>
    <div class="ear">No. @@NO@@<br>@@DOW@@<br><b>@@MD@@</b><br>@@YEAR@@</div>
  </header>
  <div class="strip"><span>@@DATE_LONG@@</span><span>@@PRICE@@</span><span>@@DELIVERED@@</span></div>
  <div class="book-wrap" id="bookwrap"><div id="flipbook">
@@PAGES@@
  </div></div>
  <nav class="pager" aria-label="Turn the pages">
    <button type="button" id="prev" aria-label="Previous page">‹</button>
    <div class="where"><span id="leafname">The Pack</span><span class="dots" id="dots"></span><span class="swipe-hint">⟵ swipe, or grab the page edge to turn ⟶</span></div>
    <button type="button" id="next" aria-label="Next page">›</button>
  </nav>
  <footer class="flap"><span>@@FLAP@@</span><a href="../archive.html">Back issues</a></footer>
</div>
<div class="modal" id="jobmodal" hidden><div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="jm-title">
  <button type="button" class="modal-x" id="jm-close" aria-label="Close">×</button>
  <div class="jm-head"><span id="jm-mug"></span><div><div class="kicker" id="jm-kind">Job Listing</div><h3 id="jm-title"></h3></div></div>
  <div id="jm-body"></div><div id="jm-links" class="jm-links"></div>
  <div class="jm-actions">
    <button type="button" class="btn go" data-d="approve" id="jm-go">✅ Approve</button>
    <button type="button" class="btn" data-d="done" id="jm-self">🛠 I'll do it myself — mark done</button>
    <button type="button" class="btn ghost" data-d="dismiss">Not now</button>
  </div><p class="small" id="jm-msg"></p></div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
<script src="../js/turn-edge.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcode-generator/1.4.4/qrcode.min.js"></script>
<script>
(function () {
  var DATE = "@@DATE@@", LIST = @@JOBS@@;
  var BASE = location.pathname.replace(/\/(editions|issues|guides)\/[^\/]*$/, '/').replace(/[^\/]*$/, '');
  var book = document.getElementById('flipbook'), wrap = document.getElementById('bookwrap');
  var pages = Array.prototype.slice.call(book.querySelectorAll('.pg'));
  var nameEl = document.getElementById('leafname'), dotsEl = document.getElementById('dots');
  var turning = false, hasTurn = !!(window.jQuery && jQuery.fn.turn);
  function dims() {   // one full-width page at a time, so the classic newspaper layout fits
    var w = wrap.clientWidth;
    var h = Math.round(Math.max(560, Math.min(innerHeight - 40, 1100)));
    return { w: w, h: h };
  }
  pages.forEach(function (pg, i) {
    var b = document.createElement('button'); b.type = 'button'; b.setAttribute('aria-label', pg.dataset.title);
    b.onclick = function () { if (hasTurn && !turning) jQuery(book).turn('page', i + 1); };
    dotsEl.appendChild(b);
  });
  function label(p) {
    document.body.classList.toggle('on-cover', p === 1 || p === pages.length);   // closed book: the cover is the pack
    nameEl.textContent = (pages[p - 1] ? pages[p - 1].dataset.title : '') + '  ·  ' + p + ' of ' + pages.length;
    Array.prototype.forEach.call(dotsEl.children, function (d, i) { d.classList.toggle('on', i === p - 1); });
  }
  if (hasTurn) {
    var d = dims();
    jQuery(book).turn({ width: d.w, height: d.h, display: 'single', acceleration: true, gradients: true, duration: 950,
      when: { turning: function () { turning = true; }, turned: function (ev, p) { turning = false; label(p); } } });
    var start = parseInt((location.hash.match(/page-(\d+)/) || [])[1] || '1', 10);
    if (start > 1) jQuery(book).turn('page', start);
    label(jQuery(book).turn('page'));
    var go = function (dir) { if (!turning) jQuery(book).turn(dir > 0 ? 'next' : 'previous'); };
    document.getElementById('prev').onclick = function () { go(-1); };
    document.getElementById('next').onclick = function () { go(1); };
    addEventListener('keydown', function (e) { if (e.key === 'ArrowRight') go(1); if (e.key === 'ArrowLeft') go(-1); });
    var x0 = null, y0 = null;   // phones: swipe anywhere on the page (dragging a corner also works)
    book.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
    book.addEventListener('touchend', function (e) {
      if (x0 === null) return; var dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0; x0 = null;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.4) setTimeout(function () { go(dx < 0 ? 1 : -1); }, 30);
    });
    var t; addEventListener('resize', function () { clearTimeout(t); t = setTimeout(function () {
      var n = dims(); jQuery(book).turn('size', n.w, n.h); label(jQuery(book).turn('page')); }, 200); });
  } else { document.body.classList.add('noturn'); nameEl.textContent = 'All pages'; }

  // ---- Job Listings, Want Ads and B.I.G's catalog: tap → details → approve / handle / not now ----
  var modal = document.getElementById('jobmodal'), cur = null;
  function paintStatus(st) {
    Array.prototype.forEach.call(document.querySelectorAll('.job, .cat-item, .coupon'), function (b) {
      var kind = b.dataset.kind || 'market', key = (kind === 'job' ? '' : kind + ':') + b.dataset.idx, s = st[key];
      var el = b.querySelector('.job-status') || b.querySelector('.cat-more');
      if (!s || !el) return; b.classList.add('st-' + s.status);
      el.textContent = s.status === 'approved' ? (s.result_status === 'ok' ? '✅ Done — ' + (s.result || 'it worked') :
                                                   s.result_status === 'failed' ? '❌ Didn\'t work — ' + (s.result || 'see Discord') :
                                                   s.result_status === 'needs' ? '👉 Needs you — ' + (s.result || 'see Discord') :
                                                   '⏳ Approved — ' + (s.agent || 'Ganja') + ' is on it') :
                       s.status === 'done' ? '🛠 Done (by you)' : s.status === 'clipped' ? '✂ Clipped — saved for later' : s.status === 'dismissed' ? 'Not now' : el.textContent;
    });
  }
  var PLANS = {};
  function paintPlans() {
    Array.prototype.forEach.call(document.querySelectorAll('.cat-item'), function (b) {
      var j = (LIST.market || [])[+b.dataset.idx] || {}, p = PLANS[j.item_no], el = b.querySelector('.cat-more');
      if (!p || !el) return;
      el.textContent = p.status === 'ready' ? '📋 Full plan ready ›' : p.status === 'writing' ? '✍️ B.I.G is writing the plan…' : el.textContent;
    });
  }
  function load() {
    fetch(BASE + 'api/jobs?date=' + DATE, { cache: 'no-store' }).then(function (r) { return r.json(); }).then(paintStatus).catch(function () {});
    if (LIST.market && LIST.market.length) fetch(BASE + 'api/plans', { cache: 'no-store' }).then(function (r) { return r.json(); })
      .then(function (p) { PLANS = p || {}; paintPlans(); }).catch(function () {});
  }
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  function row(label, val) { return val ? '<div class="tag-row"><span>' + esc(label) + '</span><b>' + esc(val) + '</b></div>' : ''; }
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.job, .cat-item, .coupon'); if (!b) return;
    ev.stopPropagation();
    var kind = b.dataset.kind || 'market', j = (LIST[kind] || [])[+b.dataset.idx] || {};
    cur = { kind: kind, idx: +b.dataset.idx };
    document.getElementById('jm-kind').textContent = kind === 'job' ? 'Job Listing' : kind === 'want' ? 'Want Ad' : kind === 'coupon' ? 'The Couponer · ' + (j.category || 'coupon') : 'B.I.G\'s Catalog · Item No. ' + (j.item_no || '');
    document.getElementById('jm-title').textContent = j.title || '';
    var body = '';
    if (kind === 'market') {
      body = '<div class="burst big"><span>' + esc(j.price || j.income_week || '?') + '</span></div><p>' + esc(j.desc || j.text) + '</p>' +
             (j.how ? '<p><b>How it pays:</b> ' + esc(j.how) + '</p>' : '') +
             '<div class="tag-card">' + row('Potential income / week', j.income_week) + row('Time to keep it going', j.tend) +
             row('Up-front cost', j.upfront) + row('Weekly cost', j.weekly_cost) + row('Risk of loss', j.risk) + '</div>';
    } else if (kind === 'coupon') {
      body = '<div class="burst big coupon-price"><span>' + esc(j.price || 'FREE') + '</span></div><p>' + esc(j.what) + '</p>' +
             (j.why ? '<p><b>Why it fits your setup:</b> ' + esc(j.why) + '</p>' : '') +
             '<div class="tag-card">' + row('Works with', j.fits) + row('Deal', j.deal) + row('Good through', j.expires) +
             row('Time to try it', j.time) + row('Difficulty', j.difficulty) + '</div>';
    } else {
      body = '<p>' + esc(j.details || j.text) + '</p>' + (j.ask ? '<p class="ask">➜ ' + esc(j.ask) + '</p>' : '');
    }
    document.getElementById('jm-body').innerHTML = body;
    var links = (j.links || []).slice(); if (j.url) links.unshift({ label: 'Open', url: j.url });
    document.getElementById('jm-links').innerHTML = links.filter(function (l) { return /^https?:\/\//.test(l.url || ''); })
      .map(function (l) { return '<a class="btn link" target="_blank" rel="noopener" href="' + esc(l.url) + '">🔗 ' + esc(l.label || l.url) + '</a>'; }).join('');
    var go = document.getElementById('jm-go'), self = document.getElementById('jm-self');
    go.dataset.d = 'approve'; self.dataset.d = 'done'; self.style.display = '';
    if (kind === 'market') {
      var p = PLANS[j.item_no] || {};
      go.dataset.d = p.status === 'ready' ? 'read' : 'plan'; go.dataset.url = p.url || '';
      go.innerHTML = p.status === 'ready' ? '📖 Read B.I.G\'s full start-to-finish plan' : p.status === 'writing' ? '✍️ B.I.G is writing the plan — check back soon'
                   : '📋 Have B.I.G write the full plan: every step, site, account &amp; legal need';
      self.style.display = 'none';
    } else if (kind === 'coupon') {
      go.innerHTML = '🛠 Have the Garden set it up'; self.innerHTML = '✂ Clip it — save for later'; self.dataset.d = 'clip';
    } else {
      go.innerHTML = (kind === 'want' ? '✅ Yes — have ' : '✅ Approve — have ') + esc(j.agent || 'the agent') + ' handle it';
      self.innerHTML = '🛠 I\'ll do it myself — mark done';
    }
    var m = b.querySelector('.mug'); document.getElementById('jm-mug').innerHTML = m ? m.outerHTML : '';
    document.getElementById('jm-msg').textContent = ''; modal.hidden = false;
  }, true);
  function close() { modal.hidden = true; }
  document.getElementById('jm-close').onclick = close;
  modal.addEventListener('click', function (e) { if (e.target === modal) close(); });
  ['touchstart', 'touchmove', 'wheel', 'mousedown', 'mousemove'].forEach(function (t) { modal.addEventListener(t, function (e) { e.stopPropagation(); }, { passive: true }); });
  Array.prototype.forEach.call(modal.querySelectorAll('.btn[data-d]'), function (btn) {
    btn.onclick = function () {
      var msg = document.getElementById('jm-msg');
      if (btn.dataset.d === 'read') { location.href = BASE + btn.dataset.url; return; }
      msg.textContent = 'Sending…';
      if (btn.dataset.d === 'plan') {
        fetch(BASE + 'api/plan', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Double-Wide': '1' },
          body: JSON.stringify({ date: DATE, idx: cur.idx }) })
          .then(function (r) { return r.json(); })
          .then(function (res) { msg.textContent = res.message || 'Sent.'; if (res.status === 'ready' && res.url) location.href = BASE + res.url; load(); })
          .catch(function () { msg.textContent = 'Could not reach the Garden — try again in a minute.'; });
        return;
      }
      fetch(BASE + 'api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Double-Wide': '1' },
        body: JSON.stringify({ date: DATE, kind: cur.kind, idx: cur.idx, decision: btn.dataset.d }) })
        .then(function (r) { return r.json(); })
        .then(function (res) { msg.textContent = res.message || 'Saved.'; load(); if (res.ok) setTimeout(close, 1600); })
        .catch(function () { msg.textContent = 'Could not reach the Garden — try again in a minute.'; });
    };
  });
  // ---- back cover QR code (the barcode beside it encodes the same link) ----
  var qrEl = document.getElementById('qr');
  if (qrEl && window.qrcode) { var q = qrcode(0, 'M'); q.addData(qrEl.dataset.url); q.make(); qrEl.innerHTML = q.createSvgTag({ cellSize: 3, margin: 2, scalable: true }); }
  load();
})();
</script></body></html>"""


def main():
    ed = json.load(open(sys.argv[1]))
    date = ed.get("date") or dt.date.today().isoformat()
    os.makedirs(os.path.join(SITE, "editions"), exist_ok=True)
    pg = render(ed)
    open(os.path.join(SITE, "editions", date + ".html"), "w").write(pg)
    print("rendered %s: editions/%s.html" % (date, date))
    if "--no-build" not in sys.argv:   # home page (latest issue), back issues, B.I.G's catalog + plans
        import subprocess
        subprocess.run([sys.executable, os.path.join(ROOT, "build_extras.py")], check=False)


if __name__ == "__main__":
    main()
