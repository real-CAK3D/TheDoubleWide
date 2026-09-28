#!/usr/bin/env python3
"""THE DOUBLE WIDE — morning inputs for Ganja (stdout is injected into Ganja's 6 am job).

1. Weather for Lewiston, ME from the NWS (same grid/station as Homie) -> site/data/weather-<today>.json
2. Agent portraits: each agent's Discord bot avatar -> site/img/<agent>.png (refreshed weekly)
3. Prints: report day, weather summary, logins & keys status, The Gardiner's recap, every agent manifest.
Usage: collect_inputs.py [REPORT_DAY]
"""
import datetime as dt, glob, json, os, subprocess, sys, time, urllib.request
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
H = os.path.expanduser("~/.hermes")
VAULT = "/home/ubuntu/CAK3D_Garden_Wiki/10_Constellations"
UA = {"User-Agent": "TheDoubleWide morning paper (CAK3D Garden)"}
PROFILES = {"main": "ganja", "chronic": "chronic", "maple": "maple", "herbie": "herbie", "homie": "homie",
            "ibby": "ibby", "discostu": "discostu", "bak3r": "bak3r", "cyph3r": "cyph3r", "clydius": "clydius", "tinyz": "tinyz"}


GARDEN_NS = os.path.expanduser('~/.hermes/garden/newsstand')


def get_json(url, headers=None, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **(headers or {})}), timeout=timeout) as r:
        return json.load(r)


def env(path):
    d = {}
    try:
        for line in open(path, errors="ignore"):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.strip().split("=", 1)
                d.setdefault(k.strip(), v.strip().strip("'\""))
    except FileNotFoundError:
        pass
    return d


def weather(today):
    cfg = json.load(open(f"{H}/garden/homie/lewiston_weather_ac_config.json"))["location"]
    obs = get_json(f"https://api.weather.gov/stations/{cfg['nws_station']}/observations/latest")["properties"]
    fc = get_json(f"https://api.weather.gov/gridpoints/{cfg['nws_grid']}/forecast")["properties"]["periods"]
    c = (obs.get("temperature") or {}).get("value")
    days = []  # 3-day forecast: each daytime period with the following night's low and chance of rain
    for i, p in enumerate(fc):
        if p.get("isDaytime") or (i == 0 and not days):
            nxt = fc[i + 1] if i + 1 < len(fc) and not fc[i + 1].get("isDaytime") else None
            pop = (p.get("probabilityOfPrecipitation") or {}).get("value")
            days.append({"name": p["name"], "high": p["temperature"], "low": nxt["temperature"] if nxt else None,
                         "short": p["shortForecast"], "pop": pop or None})
        if len(days) == 3:
            break
    w = {"place": "Lewiston, ME", "days": days,
         "now": {"temp_f": round(c * 9 / 5 + 32) if c is not None else "?", "text": obs.get("textDescription"),
                 "humidity": round((obs.get("relativeHumidity") or {}).get("value") or 0)},
         "periods": [{"name": p["name"], "temp": p["temperature"], "short": p["shortForecast"]} for p in fc[:6]],
         "today": {"detail": fc[0]["detailedForecast"] if fc else ""}}
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    json.dump(w, open(os.path.join(SITE, "data", f"weather-{today}.json"), "w"))
    return w


def portraits():
    os.makedirs(os.path.join(SITE, "img"), exist_ok=True)
    got = []
    for prof, slug in PROFILES.items():
        dest = os.path.join(SITE, "img", f"{slug}.png")
        if os.path.exists(dest) and time.time() - os.path.getmtime(dest) < 7 * 86400:
            got.append(slug); continue
        tok = env(f"{H}/.env" if prof == "main" else f"{H}/profiles/{prof}/.env").get("DISCORD_BOT_TOKEN")
        if not tok:
            continue
        try:
            me = get_json("https://discord.com/api/v10/users/@me", {"Authorization": f"Bot {tok}"})
            if me.get("avatar"):
                url = f"https://cdn.discordapp.com/avatars/{me['id']}/{me['avatar']}.png?size=256"
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                    open(dest, "wb").write(r.read())
                got.append(slug)
        except Exception:
            pass
    return got


def _since(ts):
    """ISO/epoch -> (since_iso, streak_hours)."""
    t = dt.datetime.fromisoformat(ts) if isinstance(ts, str) else dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.isoformat(), round((dt.datetime.now(dt.timezone.utc) - t).total_seconds() / 3600, 1)


def uptime(today):
    """Uptime Scoreboard: always-on agents (gateway up since), shift agents (last shift result), machines (booted since)."""
    env_ = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}
    agents = []
    for name, unit in (("Ganja", "hermes-gateway"), ("Maple", "hermes-gateway-maple"), ("Herbie", "hermes-gateway-herbie"),
                       ("Homie", "hermes-gateway-homie"), ("Ibby", "hermes-gateway-ibby"), ("tinyZ", "hermes-gateway-tinyz")):
        out = subprocess.run(["systemctl", "--user", "show", "-p", "ActiveState", "-p", "ActiveEnterTimestamp", unit + ".service"],
                             capture_output=True, text=True, env=env_, timeout=20).stdout
        kv = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
        up = kv.get("ActiveState") == "active"
        row = {"name": name, "kind": "always on", "status": "up" if up else "down"}
        if up and kv.get("ActiveEnterTimestamp"):   # e.g. "Sat 2026-09-26 12:14:06 UTC" (systemd 249)
            try:
                row["since"], row["streak_h"] = _since(dt.datetime.strptime(kv["ActiveEnterTimestamp"].rsplit(" ", 1)[0], "%a %Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc).isoformat())
            except ValueError:
                pass
        agents.append(row)
    try:
        log = open(f"{H}/logs/relay.log").read().splitlines()
    except Exception:
        log = []
    for name, prof in (("CHRONIC", "chronic"), ("Disco Stu", "discostu"), ("The Gardiner", "gardener"), ("BAK3R", "bak3r"), ("CYPH3R", "cyph3r"), ("B.I.G", "big")):
        last = next((l for l in reversed(log) if f"[{prof}] finished" in l), "")
        st = "ok" if "status=ok" in last else ("error" if "status=error" in last else ("no run yet" if not last else "no result"))
        agents.append({"name": name, "kind": "night shift", "status": "shift " + st, "last": last[:20]})
    machines = []
    for name, host in (("The Garden", None), ("X (cak3d)", "cak3d"), ("theBAK3RY", "thebak3ry"), ("Hack-Safe", "hack-safe")):
        cmd = ["uptime", "-s"] if host is None else ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", host, "uptime -s"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            boot = r.stdout.strip()
            if r.returncode == 0 and boot:
                since, h = _since(dt.datetime.strptime(boot, "%Y-%m-%d %H:%M:%S").astimezone().isoformat())
                machines.append({"name": name, "status": "up", "since": since, "streak_h": h})
            else:
                machines.append({"name": name, "status": "unreachable"})
        except Exception:
            machines.append({"name": name, "status": "unreachable"})
    try:
        import base64
        ps = "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss')"
        r = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", "nukebox",
                            "powershell -NoProfile -EncodedCommand " + base64.b64encode(ps.encode("utf-16-le")).decode()],
                           capture_output=True, text=True, errors="replace", timeout=40)
        since, h = _since(r.stdout.strip()[:19] + "+00:00")
        machines.append({"name": "NukeBox PC", "status": "up", "since": since, "streak_h": h})
    except Exception:
        machines.append({"name": "NukeBox PC", "status": "unreachable"})
    ranked = [x for x in agents + machines if x.get("streak_h")]
    best = max(ranked, key=lambda x: x["streak_h"]) if ranked else None
    data = {"agents": agents, "machines": machines, "longest": best}
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    json.dump(data, open(os.path.join(SITE, "data", f"uptime-{today}.json"), "w"))
    return data


def coming_up_facts():
    """Dated facts for the 'Coming Up' calendar: Tailscale keys expiring within 60 days + job listings still waiting on CAK3D."""
    out = []
    try:
        st = json.loads(subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=20).stdout)
        for n in [st.get("Self") or {}] + list((st.get("Peer") or {}).values()):
            if n.get("KeyExpiry") and (n.get("Online") or n is st.get("Self")):
                exp = dt.datetime.fromisoformat(n["KeyExpiry"].replace("Z", "+00:00"))
                days = (exp - dt.datetime.now(dt.timezone.utc)).days
                if days <= 60:
                    out.append(f"{exp:%b %-d}: Tailscale key for {n.get('HostName')} expires ({days} days)")
    except Exception:
        pass
    for f in sorted(glob.glob(os.path.join(ROOT, "drafts", "*.json")))[-3:]:
        date = os.path.basename(f)[:-5]
        try:
            jobs = json.load(open(f)).get("job_listings") or []
            jf = os.path.join(ROOT, "jobs", date + ".json")
            done = json.load(open(jf)) if os.path.exists(jf) else {}
        except Exception:
            continue
        for i, j in enumerate(jobs):
            s = (done.get(str(i)) or {}).get("status")
            if s not in ("done", "dismissed", "approved"):
                out.append(f"waiting on CAK3D since {date}: {j.get('title')} ({s or 'not answered'})")
    return out


AGENT_NAMES = {"main": "Ganja", "maple": "Maple", "herbie": "Herbie", "homie": "Homie", "ibby": "Ibby", "tinyz": "tinyZ",
               "chronic": "CHRONIC", "discostu": "Disco Stu", "gardener": "The Gardiner", "bak3r": "BAK3R", "cyph3r": "CYPH3R",
               "clydius": "Clydius", "big": "B.I.G", "fatman": "Fat Man", "littleboy": "Little Boy"}


def usage(day, today):
    """Token Tracker for the report day (America/New_York): tokens by hour, per agent, per model, per provider.
    Hermes stores usage per session, so each session's tokens are spread over the hours its messages fall in
    (sessions that span days only count the share of messages sent that day). Adds the PC's Claude Code / Codex
    usage when the nightly PC exporter left a file in the vault."""
    import collections, sqlite3
    d0 = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(), TZ)
    s0, s1 = d0.timestamp(), (d0 + dt.timedelta(days=1)).timestamp()
    hours = [0.0] * 24
    agent_hours = collections.defaultdict(lambda: [0.0] * 24)   # who burned tokens when (for the market chart)
    agent, model, prov = collections.Counter(), collections.Counter(), collections.Counter()
    cache = 0.0
    calls = 0
    homes = [("main", H)] + [(os.path.basename(p), p) for p in sorted(glob.glob(f"{H}/profiles/*")) if os.path.isdir(p)]
    for prof, home in homes:
        db = os.path.join(home, "state.db")
        if not os.path.exists(db):
            continue
        try:
            c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=20)
            rows = c.execute("select id, model, billing_provider, coalesce(input_tokens,0), coalesce(output_tokens,0), "
                             "coalesce(cache_read_tokens,0), coalesce(api_call_count,0), started_at from sessions "
                             "where started_at < ? and (ended_at is null or ended_at >= ?)", (s1, s0)).fetchall()
            for sid, mdl, bp, tin, tout, tcache, ncalls, started in rows:
                ts = [r[0] for r in c.execute("select timestamp from messages where session_id = ? and timestamp is not null", (sid,))]
                inday = [t for t in ts if s0 <= t < s1] or ([started] if not ts and started and s0 <= started < s1 else [])
                if not inday:
                    continue
                frac = len(inday) / max(len(ts), 1) if ts else 1.0
                tok = (tin + tout) * frac
                if tok <= 0:
                    continue
                name = AGENT_NAMES.get(prof, prof)
                for t in inday:
                    h = dt.datetime.fromtimestamp(t, TZ).hour
                    hours[h] += tok / len(inday)
                    agent_hours[name][h] += tok / len(inday)
                bp_label = "Ollama (NukeBox)" if "ollama" in str(bp or "").lower() else (bp or "unknown")
                agent[name] += tok; model[mdl or "unknown"] += tok; prov[bp_label] += tok
                cache += tcache * frac; calls += round(ncalls * frac)
            c.close()
        except Exception:
            continue
    try:  # PC side (Claude Code / Codex), written by the nightly PC exporter
        r = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "cak3d",
                            f"cat '/home/ubuntu/CAK3D_Garden_Wiki/60_Sources/AI Chat Intake/_usage/{day}.json'"],
                           capture_output=True, text=True, timeout=30)
        pc = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        pc = None
    if pc:
        pc_tot = sum((pc.get("by_agent") or {}).values()) or 1
        for i, v in enumerate(pc.get("hours") or []):
            hours[i] += v
            for k, kv in (pc.get("by_agent") or {}).items():   # PC hours split across the PC's tools by their share
                agent_hours[k][i] += v * kv / pc_tot
        for src, dst in (("by_agent", agent), ("by_model", model), ("by_provider", prov)):
            for k, v in (pc.get(src) or {}).items():
                dst[k] += v
        cache += pc.get("cache_read", 0)
    try:  # Ollama on NukeBox (qwen3, gemma …): read from its server log, since Hermes doesn't count the side calls it sends there
        import ollama_usage
        ol = ollama_usage.usage(day)
    except Exception:
        ol = None
    if ol and ol.get("total"):
        for i, v in enumerate(ol["hours"]):
            hours[i] += v
            agent_hours["NukeBox (Ollama)"][i] += v
        agent["NukeBox (Ollama)"] += ol["total"]
        prov["Ollama (NukeBox)"] += ol["total"]
        for k, v in ol["by_model"].items():
            model[k] += v
        calls += ol.get("requests", 0)
    data = {"day": day, "total": round(sum(agent.values())), "cache_read": round(cache), "calls": calls,
            "hours": [round(h) for h in hours], "by_agent": dict(agent.most_common()), "by_model": dict(model.most_common()),
            "by_provider": dict(prov.most_common()), "pc_included": bool(pc),
            "agent_hours": {k: [round(x) for x in v] for k, v in agent_hours.items() if sum(v) > 0},
            "note": "Tokens = input + output. Hermes logs usage per session, so hourly figures are spread by message times (estimate)."}
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    json.dump(data, open(os.path.join(SITE, "data", f"usage-{today}.json"), "w"))
    return data



# ---------------------------------------------------------------- almanac (sky + season + Garden records)
LAT, LON = 44.1004, -70.2148   # Lewiston, Maine


def _sun(day):
    """NOAA approximation: sunrise/sunset (local) and day length for Lewiston."""
    import math
    n = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    de = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
          - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    la = math.radians(LAT)
    ha = math.degrees(math.acos(math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(de)) - math.tan(la) * math.tan(de)))
    mid = dt.datetime.combine(day, dt.time(), dt.timezone.utc)
    rise = mid + dt.timedelta(minutes=720 - 4 * (LON + ha) - eq)
    sset = mid + dt.timedelta(minutes=720 - 4 * (LON - ha) - eq)
    return rise.astimezone(TZ), sset.astimezone(TZ), (sset - rise).total_seconds() / 60


def _moon(when):
    import math
    syn = 29.530588853
    ref = dt.datetime(2000, 1, 6, 18, 14, tzinfo=dt.timezone.utc)
    age = ((when - ref).total_seconds() / 86400) % syn
    illum = (1 - math.cos(2 * math.pi * age / syn)) / 2
    names = [(1.85, "New Moon"), (5.54, "Waxing Crescent"), (9.23, "First Quarter"), (12.92, "Waxing Gibbous"), (16.61, "Full Moon"),
             (20.30, "Waning Gibbous"), (23.99, "Last Quarter"), (27.68, "Waning Crescent"), (99, "New Moon")]
    name = next(nm for lim, nm in names if age < lim)
    nxt_full = when + dt.timedelta(days=(14.765 - age) % syn)
    nxt_new = when + dt.timedelta(days=(syn - age) % syn)
    return name, round(illum * 100), nxt_full.astimezone(TZ), nxt_new.astimezone(TZ)


def almanac(today, day):
    t = dt.date.fromisoformat(today)
    rise, sset, mins = _sun(t)
    _, _, mins_y = _sun(t - dt.timedelta(days=1))
    moon, illum, nf, nn = _moon(dt.datetime.now(dt.timezone.utc))
    fmt = lambda x: x.strftime("%-I:%M %p")
    delta = mins - mins_y
    sky = {"sunrise": fmt(rise), "sunset": fmt(sset), "daylength": "%dh %02dm" % (mins // 60, mins % 60),
           "daydelta": ("%+.1f min" % delta), "moon": moon, "illum": illum,
           "next_full": nf.strftime("%b %-d"), "next_new": nn.strftime("%b %-d")}
    y = t.year
    def until(m, d, label):
        target = dt.date(y if dt.date(y, m, d) >= t else y + 1, m, d)
        return "%s in %d days (%s)" % (label, (target - t).days, target.strftime("%b %-d"))
    season = {"lines": [
        until(12, 21, "Winter solstice"), until(10, 31, "Halloween"),
        "Average first frost around Lewiston: late Sept to early Oct — cover tender plants on clear, still nights",
        "Fall foliage in central Maine usually peaks early to mid October",
        "Daylight is %s a day right now" % ("shrinking by about %.0f minutes" % -delta if delta < 0 else "growing by about %.0f minutes" % delta),
    ]}
    lines = []
    try:
        log = open(f"{H}/logs/relay.log").read().splitlines()
        nights = {l[:10] for l in log if "[gardener] finished" in l and "status=ok" in l}
        lines.append("Nightly relays completed: %d" % len(nights))
    except Exception:
        pass
    lines.append("Days since the Garden Wiki became the Garden's memory (Sep 26): %d" % (t - dt.date(2026, 9, 26)).days)
    try:
        u = json.load(open(os.path.join(SITE, "data", f"uptime-{today}.json")))
        if u.get("longest"):
            lines.append("Longest uptime streak: %s, %.1f days" % (u["longest"]["name"], u["longest"]["streak_h"] / 24))
    except Exception:
        pass
    month_tok = 0
    for f in glob.glob(os.path.join(SITE, "data", "usage-%s-*.json" % today[:7])):
        try:
            month_tok += json.load(open(f)).get("total", 0)
        except Exception:
            pass
    if month_tok:
        lines.append("Tokens used so far this month: %.1fM" % (month_tok / 1e6))
    try:
        r = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "cak3d", "tail -n 1 '/home/ubuntu/CAK3D_Garden_Wiki/99_Meta/Chronic Intake Log.md'"],
                           capture_output=True, text=True, timeout=30)
        if r.stdout.strip():
            lines.append("Chronic's last sort: " + r.stdout.strip().lstrip("- ")[:160])
    except Exception:
        pass
    data = {"sky": sky, "season": season, "records": {"lines": lines}}
    json.dump(data, open(os.path.join(SITE, "data", f"almanac-{today}.json"), "w"))
    return data


# ---------------------------------------------------------------- payroll (pretend pay, real efficiency scoring)
PAY = {  # profile: (display name, base pay per job, token budget per job, target minutes)
    "chronic": ("CHRONIC", 40, 400_000, 30), "gardener": ("The Gardiner", 35, 250_000, 20), "main": ("Ganja", 45, 300_000, 15),
    "discostu": ("Disco Stu", 25, 150_000, 10), "maple": ("Maple", 20, 120_000, 10), "ibby": ("Ibby", 25, 150_000, 10),
    "homie": ("Homie", 20, 120_000, 10), "herbie": ("Herbie", 20, 120_000, 10), "bak3r": ("BAK3R", 25, 120_000, 10),
    "cyph3r": ("CYPH3R", 25, 120_000, 10), "big": ("B.I.G", 30, 200_000, 20)}


def payroll(today):
    """Score every relay job that finished in the last 24 hours: base pay × (token efficiency, speed); errors earn
    nothing and reruns of the same job (lost context / catch-ups) are docked. Keeps a running ledger."""
    import re, sqlite3
    now = dt.datetime.now(dt.timezone.utc)
    since = now - dt.timedelta(hours=24)
    try:
        log = open(f"{H}/logs/relay.log").read().splitlines()
    except Exception:
        log = []
    trig, runs = {}, []
    for l in log:
        m = re.match(r"(\S+Z) \[(\w+)\] (trigger|finished) '([^']+)'.*?(?:status=(\w*))?(?: last_run|$)", l)
        if not m:
            continue
        ts = dt.datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
        prof, what, job = m.group(2), m.group(3), m.group(4)
        if what == "trigger":
            trig[(prof, job)] = ts
        elif ts >= since and prof in PAY:
            st = m.group(5) or ""
            start = trig.get((prof, job), ts)
            runs.append({"prof": prof, "job": job, "ok": st == "ok", "minutes": max((ts - start).total_seconds() / 60, 0.1), "start": start, "end": ts})
    for r in runs:   # tokens for the run: the job's cron session(s) in that profile's state.db
        home = H if r["prof"] == "main" else f"{H}/profiles/{r['prof']}"
        tok = 0
        try:
            jobs = json.load(open(f"{home}/cron/jobs.json"))["jobs"]
            jid = next((j["id"] for j in jobs if j.get("name") == r["job"]), None)
            if jid:
                c = sqlite3.connect(f"file:{home}/state.db?mode=ro", uri=True, timeout=20)
                row = c.execute("select sum(coalesce(input_tokens,0)+coalesce(output_tokens,0)) from sessions where id like ? and started_at between ? and ?",
                                (f"cron_{jid}_%", r["start"].timestamp() - 120, r["end"].timestamp() + 120)).fetchone()
                tok = row[0] or 0
                c.close()
        except Exception:
            pass
        r["tokens"] = tok
    per = {}
    for r in runs:
        name, base, budget, target = PAY[r["prof"]]
        reruns = sum(1 for x in runs if x["prof"] == r["prof"] and x["job"] == r["job"]) - 1
        if r["ok"]:
            eff = max(-1, min(1, (budget - r["tokens"]) / budget)) if r["tokens"] else 0
            spd = max(-1, min(1, (target - r["minutes"]) / target))
            score = max(0.2, 1 + 0.25 * eff + 0.15 * spd - 0.1 * reruns)
            pay = base * score
        else:
            score, pay = 0, 0
        a = per.setdefault(name, {"agent": name, "jobs": 0, "pay": 0.0, "tokens": 0, "scores": []})
        a["jobs"] += 1; a["pay"] += pay; a["tokens"] += r["tokens"]; a["scores"].append(score)
    ledger_f = os.path.join(SITE, "data", "payroll-ledger.json")
    try:
        ledger = json.load(open(ledger_f))
    except Exception:
        ledger = {}
    ledger[today] = {k: round(v["pay"], 2) for k, v in per.items()}
    json.dump(ledger, open(ledger_f, "w"), indent=1)
    t = dt.date.fromisoformat(today)
    week0 = t - dt.timedelta(days=t.weekday())
    rows = []
    names = sorted({n for d in ledger.values() for n in d})
    for n in names:
        wk = sum(v.get(n, 0) for d, v in ledger.items() if week0 <= dt.date.fromisoformat(d) <= t)
        mo = sum(v.get(n, 0) for d, v in ledger.items() if d[:7] == today[:7])
        p = per.get(n, {})
        avg = sum(p.get("scores", [])) / len(p["scores"]) if p.get("scores") else None
        grade = "—" if avg is None else "A" if avg >= 1.25 else "B" if avg >= 1.05 else "C" if avg >= 0.9 else "D" if avg > 0 else "F"
        rows.append({"agent": n, "jobs": p.get("jobs", 0), "grade": grade, "today": round(p.get("pay", 0), 2), "week": round(wk, 2), "month": round(mo, 2),
                     "per_job": ("%.0fk" % (p["tokens"] / p["jobs"] / 1000)) if p.get("jobs") and p.get("tokens") else "—", "_avg": avg or 0})
    rows.sort(key=lambda x: -x["today"])
    best = max((r for r in rows if r["_avg"]), key=lambda r: r["_avg"], default=None)
    for r in rows:
        r.pop("_avg", None)
    data = {"period": "Shift: last 24 hours to %s." % dt.datetime.now(TZ).strftime("%-I:%M %p %b %-d"), "rows": rows,
            "employee_of_the_day": {"agent": best["agent"], "why": "best efficiency score on the night shift"} if best else None}
    json.dump(data, open(os.path.join(SITE, "data", f"payroll-{today}.json"), "w"))
    return data


def market_copy(today, day):
    """B.I.G files his catalog as JSON in the vault; copy it in so the editor never retypes money figures."""
    for d in (today, day):
        r = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "cak3d", f"cat '/home/ubuntu/CAK3D_Garden_Wiki/10_Constellations/B.I.G/Market/{d}.json'"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            try:
                data = json.loads(r.stdout)
                json.dump(data, open(os.path.join(SITE, "data", f"market-{today}.json"), "w"))
                return data
            except ValueError:
                pass
    return None


def directory_changes(today):
    """Births and passings: listings that appeared in / disappeared from The Green Thumb since the last snapshot."""
    gt = os.path.join(H, "garden", "green-thumb")
    try:
        ents = json.load(open(os.path.join(gt, "site", "data", "green-thumb.json"))).get("entries") or []
    except Exception:
        ents = []
    try:
        ents += json.load(open(os.path.join(gt, "private", "entries.json"))).get("entries") or []
    except Exception:
        pass
    snap = {x["id"]: {"name": x.get("name"), "device": x.get("device"), "category": x.get("category")} for x in ents if x.get("id")}
    d = os.path.join(SITE, "data")
    prev = sorted(f for f in os.listdir(d) if f.startswith("directory-") and f < "directory-%s.json" % today)
    json.dump(snap, open(os.path.join(d, "directory-%s.json" % today), "w"))
    if not prev:
        out = {"born": [], "passed": [], "first_snapshot": True}
    else:
        old = json.load(open(os.path.join(d, prev[-1])))
        out = {"born": [dict(snap[k], id=k) for k in snap if k not in old], "passed": [dict(old[k], id=k) for k in old if k not in snap], "since": prev[-1][10:20]}
    json.dump(out, open(os.path.join(d, "obits-%s.json" % today), "w"))
    return out


def main():
    now = dt.datetime.now(TZ)
    today = now.date().isoformat()
    day = sys.argv[1] if len(sys.argv) > 1 else (now - dt.timedelta(days=1)).date().isoformat()
    print(f"THE DOUBLE WIDE — edition date {today} (reporting on {day})\n")
    try:
        w = weather(today)
        print(f"WEATHER (saved for the page): now {w['now']['temp_f']}°F {w['now']['text']}; " +
              "; ".join(f"{p['name']}: {p['temp']}° {p['short']}" for p in w["periods"][:3]))
    except Exception as e:
        print(f"WEATHER: unavailable ({type(e).__name__})")
    print(f"PORTRAITS available (use these agent names for 'agent' fields): {', '.join(portraits()) or 'none'}")
    try:
        keys = subprocess.run([f"{H}/hermes-agent/venv/bin/python", f"{H}/scripts/hermes_agent_token_watchdog.py", "--summary"],
                              capture_output=True, text=True, timeout=120).stdout.strip()
    except Exception as e:
        keys = f"watchdog unavailable ({type(e).__name__})"
    print(f"\nLOGINS & KEYS:\n{keys}\n")
    try:
        u = uptime(today)
        fmt = lambda x: f"{x['name']}: {x['status']}" + (f" for {x['streak_h']/24:.1f} days" if x.get("streak_h") else "")
        print("UPTIME SCOREBOARD (printed in the paper automatically): " + "; ".join(fmt(x) for x in u["agents"] + u["machines"]))
        if u.get("longest"):
            print(f"  longest streak: {u['longest']['name']} ({u['longest']['streak_h']/24:.1f} days)")
    except Exception as e:
        print(f"UPTIME: unavailable ({type(e).__name__})")
    try:
        us = usage(day, today)
        top = lambda d: ", ".join(f"{k} {v/1000:.0f}k" for k, v in list(d.items())[:5])
        print(f"\nTOKEN TRACKER for {day} (printed in the paper automatically): {us['total']/1000:.0f}k tokens "
              f"(+{us['cache_read']/1000:.0f}k cached) over ~{us['calls']} calls. Busiest hour: "
              f"{max(range(24), key=lambda h: us['hours'][h])}:00. By agent: {top(us['by_agent'])}. By model: {top(us['by_model'])}. "
              f"By provider: {top(us['by_provider'])}.")
    except Exception as e:
        print(f"TOKEN TRACKER: unavailable ({type(e).__name__})")
    for label, fn in (("ALMANAC", lambda: almanac(today, day)), ("PAYROLL", lambda: payroll(today)), ("MARKET", lambda: market_copy(today, day))):
        try:
            r = fn()
            if label == "ALMANAC":
                sk = r["sky"]
                print(f"\nALMANAC (sky + season + records print automatically): sunrise {sk['sunrise']}, sunset {sk['sunset']}, "
                      f"{sk['moon']} {sk['illum']}% lit; " + "; ".join(r["records"]["lines"]))
            elif label == "PAYROLL":
                print("PAYROLL (prints automatically): " + "; ".join(f"{x['agent']} ${x['today']:.2f} ({x['grade']})" for x in r["rows"])
                      + (f". Employee of the day: {r['employee_of_the_day']['agent']}" if r.get("employee_of_the_day") else ""))
            elif label == "MARKET":
                print("B.I.G CATALOG: " + (f"{len(r.get('items') or [])} items filed — they print in ROACH CLIPS (B.I.G's paper), not in The Double Wide; you may mention the best one in a story" if r else "none filed yet (the page shows the coming-soon teaser)"))
        except Exception as e:
            print(f"{label}: unavailable ({type(e).__name__}: {e})")
    try:
        ob = directory_changes(today)
        print("\nDIRECTORY CHANGES (Obituaries & Announcements print automatically): born: %s; passed: %s"
              % (", ".join("%s (%s)" % (x["name"], x.get("device")) for x in ob["born"]) or "none",
                 ", ".join("%s (%s)" % (x["name"], x.get("device")) for x in ob["passed"]) or "none"))
    except Exception as ex:
        print("DIRECTORY CHANGES: unavailable (%s)" % type(ex).__name__)
    try:   # the kiosk's mail slot, tip line and 👍/👎 buttons (The Corner Chronicle's server keeps them)
        priv = os.path.join(GARDEN_NS, "private")
        def jl(n, d):
            try:
                return json.load(open(os.path.join(priv, n + ".json")))
            except Exception:
                return d
        letters, tips, ratings = jl("letters", []), jl("tips", []), jl("ratings", [])
        new_l = [x for x in letters if x.get("status") == "new"]
        new_t = [x for x in tips if x.get("status") == "new"]
        print("\nREADER MAIL & TIPS (print every one — see READERS in your instructions):")
        for x in new_l:
            print("  LETTER to %s (%s): %s" % (x.get("to"), x.get("at", "")[:16], x.get("text")))
        for x in new_t:
            print("  TIP for %s (%s): %s" % (x.get("agent"), x.get("at", "")[:16], x.get("text")))
        if not (new_l or new_t):
            print("  none today — leave reader_letters and tip_line empty")
        week = (dt.datetime.now(TZ) - dt.timedelta(days=7)).isoformat()[:10]
        score = {}
        for r in ratings:
            if r.get("at", "")[:10] >= week:
                k = "%s / %s" % (r.get("paper"), r.get("section"))
                score[k] = score.get(k, 0) + int(r.get("vote") or 0)
        if score:
            print("READER RATINGS (last 7 days, 👍 minus 👎): " + "; ".join("%s %+d" % kv for kv in sorted(score.items(), key=lambda kv: -abs(kv[1]))[:14]))
        for rows, name in ((letters, "letters"), (tips, "tips")):
            changed = False
            for x in rows:
                if x.get("status") == "new":
                    x["status"], x["to_paper"] = "with the editor", today
                    changed = True
            if changed:
                tmp = os.path.join(priv, name + ".json.tmp")
                json.dump(rows, open(tmp, "w"), indent=1, ensure_ascii=False)
                os.chmod(tmp, 0o600)
                os.replace(tmp, os.path.join(priv, name + ".json"))
    except Exception as ex:
        print("READER MAIL: unavailable (%s)" % type(ex).__name__)
    facts = coming_up_facts()
    print("\nCOMING UP FACTS (use these + the recap for the 'coming_up' calendar):\n" + ("\n".join("- " + f for f in facts) or "- none found"))

    def vault_cat(path):
        r = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "cak3d", f"cat {json.dumps(path)} 2>/dev/null"],
                           capture_output=True, text=True, timeout=60)
        return r.stdout
    recap = vault_cat(f"{VAULT}/The Gardiner/Handoffs/Daily Recaps/{day}.md")
    print("=== THE GARDINER'S DAILY RECAP ===\n" + (recap.strip()[:9000] or f"(no recap written for {day})"))
    r = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "cak3d",
                        f"for f in {json.dumps(VAULT + '/The Gardiner/Handoffs/Inbox/' + day)}/*.md {json.dumps(VAULT + '/The Gardiner/Handoffs/Inbox/' + today)}/*.md; "
                        "do [ -f \"$f\" ] && { echo \"=== MANIFEST: $f\"; head -c 3500 \"$f\"; echo; }; done"],
                       capture_output=True, text=True, timeout=90)
    print("\n" + (r.stdout.strip()[:24000] or "(no manifests found)"))


if __name__ == "__main__":
    main()
