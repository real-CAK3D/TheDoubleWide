#!/usr/bin/env python3
"""The Double Wide web server (Tailscale-only; mounted at /double-wide/ under The Corner Chronicle's HTTPS address).

  GET  /api/jobs?date=YYYY-MM-DD       -> {"<key>": {"status": ..., "result": ...}}
  POST /api/jobs {date, kind, idx, decision}   kind: job | want | market;  decision: approve | done | dismiss
        "approve" hands the listing (read from disk, never from the browser) to Ganja as a one-off Hermes job.
  GET  /api/plans                      -> {"<item_no>": {"status": writing|ready|failed, "url": ...}}
  POST /api/plan {date, idx}           -> B.I.G writes a full start-to-finish plan for that catalog item
Usage: serve.py <site_dir> <host> <port>
"""
import datetime as dt, glob, json, os, re, subprocess, sys

import gardenweb as gw
from gardenweb import jload, jsave, LOCK

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
HERMES = os.path.expanduser("~/.hermes")
PY = os.path.join(HERMES, "hermes-agent/venv/bin/python")
NEWSSTAND = os.path.join(HERMES, "garden", "newsstand")   # notices go out through The Corner Chronicle app
RESULT_RULE = ("START your final reply with exactly one line: 'RESULT: OK — <what worked>', 'RESULT: FAILED — <what went wrong>' or "
               "'RESULT: NEEDS CAK3D — <the step he must do>'. The paper shows that line as the follow-up, so keep it under 120 characters.")


def create_job(profile_home, prompt, name, schedule="1m", pause=False):
    code = ("import sys; from cron.jobs import create_job, pause_job\n"
            "j = create_job(sys.argv[1], sys.argv[3], name=sys.argv[2], repeat=1, deliver='discord')\n"
            "jid = j.get('id') if isinstance(j, dict) else j\n"
            "if sys.argv[4] == '1': pause_job(jid)\n"
            "print(jid)")
    r = subprocess.run([PY, "-c", code, prompt, name, schedule, "1" if pause else "0"], cwd=os.path.join(HERMES, "hermes-agent"),
                       env={**os.environ, "HERMES_HOME": profile_home}, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        return False, r.stderr.strip()[-200:]
    return True, (r.stdout.strip().splitlines() or [""])[-1]


def hand_to_ganja(date, idx, job, kind):
    prompt = (
        "CAK3D just APPROVED this %s from The Double Wide (edition %s, #%d) by tapping it in the paper:\n"
        "- Title: %s\n- Owner agent: %s\n- Details: %s\n- Request: %s\n\n"
        "Carry it out now if the Garden agents can do it (use your ssh aliases and tools as your SOUL describes; inspect first, "
        "back up before changes, keep a rollback path, never print or store secrets). If it genuinely needs CAK3D's own hands — buying "
        "hardware, clicking in a web console, physical access, an interactive login — don't pretend: give short, exact steps. "
        "Your final reply is posted to Discord: say what you did and how you verified it, or the steps CAK3D needs, in a few lines. " + RESULT_RULE
    ) % ("job listing" if kind == "job" else "want ad", date, idx + 1, job.get("title"), job.get("agent") or "unassigned",
         job.get("details") or job.get("text") or "", job.get("ask") or "")
    try:
        return create_job(HERMES, prompt, "Double Wide approval: " + str(job.get("title"))[:60])
    except Exception as e:
        return False, str(e)


def sh(s):
    return "'" + str(s).replace("'", "'\\''") + "'"


def start_plan(date, idx, item, item_no):
    """B.I.G's gateway is only up for shifts, so his one-off plan job runs through relay-step (start, run, stop);
    then the guide page is built and CAK3D gets a notice."""
    facts = json.dumps({k: item.get(k) for k in ("item_no", "title", "tag", "price", "desc", "how", "income_week", "tend", "upfront",
                                                  "weekly_cost", "risk", "links")}, ensure_ascii=False, indent=1)
    prompt = open(os.path.join(ROOT, "prompts", "big_plan_prompt.txt")).read() \
        .replace("@@ITEM@@", facts).replace("@@ITEM_NO@@", item_no).replace("@@DATE@@", date)
    name = "B.I.G plan: %s" % item_no
    ok, jid = create_job(os.path.join(HERMES, "profiles", "big"), prompt, name, schedule="0 0 1 1 *", pause=True)
    if not ok:
        return False, jid
    cmd = ("%s/bin/relay-step.sh big %s; %s %s/build_extras.py; [ -f %s/guides/%s.html ] && %s %s/notify.py %s %s %s") % (
        HERMES, sh(name), PY, ROOT, SITE, item_no, PY, NEWSSTAND, sh("📋 B.I.G's plan is ready"), sh(str(item.get("title") or item_no)[:80]),
        sh("/double-wide/guides/%s.html" % item_no))
    subprocess.Popen(["systemd-run", "--user", "--collect", "--unit=big-plan-%s-%s" % (item_no.lower(), dt.datetime.now().strftime("%H%M%S")),
                      "/bin/bash", "-c", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True, jid


def plans_state():
    st = jload(os.path.join(ROOT, "plans", "state.json"), {})
    for no, v in st.items():   # a guide page on disk means it's done
        if os.path.exists(os.path.join(SITE, "guides", no + ".html")):
            v["status"], v["url"] = "ready", "guides/%s.html" % no
        elif v.get("status") == "writing" and v.get("at", "") < (dt.datetime.now() - dt.timedelta(hours=3)).isoformat():
            v["status"] = "failed"
    return st


def followup(date):
    """Fill in results for approved listings from the one-off job's report (first line 'RESULT: …')."""
    f = os.path.join(ROOT, "jobs", date + ".json")
    st, changed = jload(f, {}), False
    for key, v in st.items():
        jid = v.get("hermes_job")
        if v.get("status") != "approved" or v.get("result_status") or not jid or not re.fullmatch(r"[0-9a-f]{6,32}", str(jid)):
            continue
        outs = sorted(glob.glob(os.path.join(HERMES, "cron", "output", jid, "*.md")))
        if not outs:
            continue
        txt = open(outs[-1], errors="ignore").read()
        resp = txt[txt.rfind("## Response"):] if "## Response" in txt else txt
        m = re.search(r"RESULT:\s*(OK|FAILED|NEEDS CAK3D)\s*[—\-:]*\s*(.*)", resp)
        if m:
            v["result_status"] = {"OK": "ok", "FAILED": "failed", "NEEDS CAK3D": "needs"}[m.group(1)]
            v["result"] = m.group(2).strip()[:160]
        else:
            v["result_status"] = "failed" if ("script failed" in txt or "Status:** error" in txt) else "ok"
            v["result"] = (resp.replace("## Response", "").strip().splitlines() or ["finished — see Discord"])[0][:160]
        v["finished_at"] = dt.datetime.fromtimestamp(os.path.getmtime(outs[-1])).isoformat(timespec="minutes")
        changed = True
    if changed:
        with LOCK:
            jsave(f, st)
    return st


def items_for(kind, date):
    if kind == "market":   # B.I.G's catalog, as copied into the site
        return jload(os.path.join(SITE, "data", "market-%s.json" % date), {}).get("items") or []
    return jload(os.path.join(ROOT, "drafts", date + ".json"), {}).get("job_listings" if kind == "job" else "want_ads") or []


class Handler(gw.Handler):
    ROOT = ROOT

    def get_api(self, p):
        if p == "/api/jobs":
            m = re.search(r"date=(\d{4}-\d{2}-\d{2})", self.path)
            self.json(200, followup(m.group(1)) if m else {})
            return True
        if p == "/api/plans":
            self.json(200, plans_state())
            return True

    def post_api(self, p):
        if p == "/api/plan":
            req = self.body()
            date, idx = str(req.get("date")), int(req.get("idx"))
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)
            item = items_for("market", date)[idx]
            no = re.sub(r"[^A-Za-z0-9-]", "", str(item.get("item_no") or "%s-%d" % (date, idx + 1)))
            with LOCK:
                st = plans_state()
                if st.get(no, {}).get("status") in ("writing", "ready"):
                    s = st[no]["status"]
                    self.json(200, {"ok": True, "status": s, "url": st[no].get("url"),
                                    "message": "B.I.G is already writing this one." if s == "writing" else "The plan is ready."})
                    return True
                ok, info = start_plan(date, idx, item, no)
                if not ok:
                    self.json(500, {"ok": False, "message": "Couldn't reach B.I.G: " + info})
                    return True
                st[no] = {"status": "writing", "title": item.get("title"), "date": date, "idx": idx, "job": info,
                          "at": dt.datetime.now().isoformat(timespec="seconds")}
                jsave(os.path.join(ROOT, "plans", "state.json"), st)
            self.json(200, {"ok": True, "status": "writing",
                            "message": "B.I.G is on it — he researches and writes the full plan (about 15–30 min). You'll get a notice when it's ready."})
            return True
        if p == "/api/jobs":
            req = self.body()
            try:
                date, idx, decision = str(req.get("date")), int(req.get("idx")), str(req.get("decision"))
                kind = str(req.get("kind") or "job")
                assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) and decision in ("approve", "done", "dismiss")
                assert kind in ("job", "want", "market") and not (kind == "market" and decision == "approve")
                job = items_for(kind, date)[idx]
            except Exception:
                self.json(400, {"ok": False, "message": "That listing couldn't be found."})
                return True
            key = str(idx) if kind == "job" else "%s:%d" % (kind, idx)
            f = os.path.join(ROOT, "jobs", date + ".json")
            with LOCK:
                st = jload(f, {})
                if decision == "approve" and st.get(key, {}).get("status") == "approved":
                    self.json(200, {"ok": True, "message": "Already approved — Ganja is on it."})
                    return True
                entry = {"status": {"approve": "approved", "done": "done", "dismiss": "dismissed"}[decision], "kind": kind,
                         "at": dt.datetime.now().isoformat(timespec="seconds"), "title": job.get("title"), "agent": "Ganja"}
                if decision == "approve":
                    ok, info = hand_to_ganja(date, idx, job, kind)
                    if not ok:
                        self.json(500, {"ok": False, "message": "Couldn't hand it to Ganja: " + info})
                        return True
                    entry["hermes_job"] = info
                st[key] = entry
                jsave(f, st)
            self.json(200, {"ok": True, "message": {"approve": "Approved! Ganja picks it up within a minute; the result shows here and in Discord.",
                                                    "done": "Marked done — nice work.", "dismiss": "Okay, parked for now."}[decision]})
            return True


if __name__ == "__main__":
    gw.run(Handler, sys.argv[1], sys.argv[2], int(sys.argv[3]))
