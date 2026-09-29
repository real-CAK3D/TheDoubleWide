#!/usr/bin/env python3
"""Build The Double Wide's pages around the editions: the home page (today's paper) and back issues.
Runs after every edition is printed (render_double_wide calls it). Safe to run any time.
(B.I.G's catalog archive and plans moved to Roach Clips on 2026-09-27.)
"""
import datetime as dt, glob, html, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
VAULT = "/home/ubuntu/CAK3D_Garden_Wiki"
VENV_PY = os.path.expanduser("~/.hermes/hermes-agent/venv/bin/python")
try:
    import markdown
except ImportError:   # system python: rerun with the Hermes venv, which has the markdown package
    if os.path.exists(VENV_PY) and sys.executable != VENV_PY:
        os.execv(VENV_PY, [VENV_PY] + sys.argv)
    markdown = None
sys.path.insert(0, ROOT)
import render_double_wide as rd   # noqa: E402
from render_double_wide import e, mug   # noqa: E402

from zoneinfo import ZoneInfo
TZ_NOW = dt.datetime.now(ZoneInfo("America/New_York"))


def load(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return default if default is not None else {}


def nice(day, fmt="%A, %B %-d, %Y"):
    try:
        return dt.date.fromisoformat(day).strftime(fmt)
    except Exception:
        return day


def shell(title, body, cls="stand", extra_head="", scripts=""):
    """A plain (non-flipbook) newsstand page with the paper's fonts, colors and app hookups."""
    css = open(os.path.join(ROOT, "double-wide.css")).read()
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s</title><link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#2a1a10">'
            '<link rel="icon" href="/icons/icon-192.png"><link rel="apple-touch-icon" href="/icons/icon-192.png">'
            '<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes">'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link href="https://fonts.googleapis.com/css2?family=Abril+Fatface&family=UnifrakturMaguntia&family=Bangers&family=Patrick+Hand+SC'
            '&family=Oswald:wght@400;600;700&family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">'
            '<style>%s</style>%s<script src="/app.js" defer></script></head><body class="%s">%s%s</body></html>'
            % (e(title), css, extra_head, cls, body, scripts))


def topbar(title, sub="", up=""):
    return ('<header class="stand-top"><a class="stand-home ns-home" href="/" aria-label="The Corner Chronicle" title="The Corner Chronicle"><svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" stroke-width="5"/><path d="M24 78h72v-22l-36-18-36 18z" fill="none" stroke="currentColor" stroke-width="6" stroke-linejoin="round"/><rect x="36" y="60" width="14" height="18" fill="currentColor"/><rect x="62" y="60" width="20" height="10" fill="currentColor"/><path d="M74 38c4-8 12-8 10-16M82 36c6-6 12-4 12-12" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/></svg></a><a class="stand-home" href="%s" aria-label="Today&#39;s paper">🗞</a>'
            '<div><h1>%s</h1>%s</div><a class="stand-home" href="%sarchive.html" aria-label="Back issues">🗂</a></header>'
            % (up or "./", e(title), ('<div class="stand-sub">%s</div>' % e(sub)) if sub else "", up))


def listing(folder):
    return sorted((f[:-5] for f in os.listdir(os.path.join(SITE, folder)) if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", f)), reverse=True) \
        if os.path.isdir(os.path.join(SITE, folder)) else []


# ------------------------------------------------------------------ back issues + home
SISTERS = [("🗞 The Corner Chronicle", "/", "every paper in one place"),
           ("💨 The Sunday Smoke", "/sunday-smoke/", "Sundays · the week rolled up + the funnies"),
           ("📌 The Re-Up", "/re-up/", "want ads · what the agents need"),
           ("✂ Roach Clips", "/roach-clips/", "Tuesdays · new things to try, found by B.I.G"),
           ("🌱 The Green Thumb", "/green-thumb/", "every device, app &amp; login")]


def build_archive():
    eds = listing("editions")
    items = "".join('<li><a href="editions/%s.html">%s</a></li>' % (x, nice(x)) for x in eds)
    sis = "".join('<li><a href="%s">%s</a> <span class="small">%s</span></li>' % (u, e(n), d) for n, u, d in SISTERS)
    body = ('%s<main class="paper"><div class="box arch"><h2>The Double Wide</h2><ul class="archive">%s</ul></div>'
            '<div class="box arch"><h2>More from the Garden</h2><ul class="archive"><li><a href="/roach-clips/catalog.html">💰 B.I.G&#39;s Wish-Book &amp; plans</a> <span class="small">(in Roach Clips)</span></li>%s</ul>'
            '<p class="small">Every paper is on The Corner Chronicle — the one app on your home screen.</p></div></main>'
            % (topbar("Back Issues", "every Double Wide ever rolled"), items or "<li>None yet.</li>", sis))
    open(os.path.join(SITE, "archive.html"), "w").write(shell("The Double Wide — Back Issues", body, "stand"))


def build_index():
    """The app opens on today's paper: index.html is a copy of the newest edition."""
    eds = listing("editions")
    if eds:
        pg = open(os.path.join(SITE, "editions", eds[0] + ".html")).read()
        open(os.path.join(SITE, "index.html"), "w").write(pg.replace('href="../', 'href="').replace('src="../', 'src="'))
        ed = load(os.path.join(ROOT, "drafts", eds[0] + ".json"))
        json.dump({"paper": "The Double Wide", "date": eds[0], "title": (ed.get("headline") or {}).get("title") or "",
                   "url": "editions/%s.html" % eds[0], "issues": eds[:10]}, open(os.path.join(SITE, "latest.json"), "w"), ensure_ascii=False)


def main():
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    for step in (build_archive, build_index):
        try:
            step()
        except Exception as ex:
            print("extras: %s failed: %s: %s" % (step.__name__, type(ex).__name__, ex))
    print("extras built")


if __name__ == "__main__":
    main()
