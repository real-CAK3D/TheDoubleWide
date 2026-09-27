#!/usr/bin/env python3
"""The Double Wide web server (Tailscale-only).

Static files from site/ with no-cache headers, plus the Job Listings API:
  GET  /api/jobs?date=YYYY-MM-DD      -> {"<idx>": {"status": ..., "at": ..., "agent": ...}}
  POST /api/jobs {date, idx, decision} -> decision: approve | done | dismiss
On "approve" the listing (read from the edition draft on disk, never from the browser) is handed to
Ganja as a one-off Hermes job; his report is posted in his Discord channel.
Usage: serve.py <site_dir> <host> <port>
"""
import datetime as dt, functools, glob, http.server, json, os, re, subprocess, sys, threading

ROOT = os.path.dirname(os.path.abspath(__file__))
JOBS_DIR = os.path.join(ROOT, "jobs")
DRAFTS = os.path.join(ROOT, "drafts")
HERMES = os.path.expanduser("~/.hermes")
LOCK = threading.Lock()
HOST_ORIGIN, PORT = None, 8086


def load_state(date):
    try:
        return json.load(open(os.path.join(JOBS_DIR, date + ".json")))
    except Exception:
        return {}


def save_state(date, st):
    os.makedirs(JOBS_DIR, exist_ok=True)
    tmp = os.path.join(JOBS_DIR, date + ".json.tmp")
    json.dump(st, open(tmp, "w"), indent=1)
    os.replace(tmp, os.path.join(JOBS_DIR, date + ".json"))


RESULT_RULE = ("START your final reply with exactly one line: 'RESULT: OK — <what worked>', 'RESULT: FAILED — <what went wrong>' or "
               "'RESULT: NEEDS CAK3D — <the step he must do>'. The paper shows that line as the follow-up, so keep it under 120 characters.")


def hand_to_ganja(date, idx, job, kind="job"):
    if kind == "market":
        prompt = (
            "CAK3D tapped 'Interested' on this idea in B.I.G's catalog (The Double Wide, edition %s):\n- Idea: %s\n- Details: %s\n- How it pays: %s\n"
            "- Income/week: %s · Time: %s · Up-front: %s · Weekly cost: %s · Risk: %s\n\n"
            "As B.I.G (resale / quick-cash scout; ask B.I.G via his notes in the Garden Wiki at 10_Constellations/B.I.G if needed), write a "
            "short STARTER PLAN: first 3 concrete steps, accounts/services needed (say which CAK3D already has), a tiny first test, and what "
            "would tell us to stop. Do NOT buy anything, create accounts, list items or spend money — those need CAK3D. Save the plan to the "
            "vault at 10_Constellations/B.I.G/Plans/<idea>.md via ssh cak3d. " + RESULT_RULE
        ) % (date, job.get("title"), job.get("desc") or job.get("text") or "", job.get("how") or "", job.get("income_week") or "?",
             job.get("tend") or "?", job.get("upfront") or "?", job.get("weekly_cost") or "?", job.get("risk") or "?")
    else:
        prompt = (
            "CAK3D just APPROVED this %s from The Double Wide (edition %s, #%d) by tapping it in the paper:\n"
            "- Title: %s\n- Owner agent: %s\n- Details: %s\n- Request: %s\n\n"
            "Carry it out now if the Garden agents can do it (use your ssh aliases and tools as your SOUL describes; inspect first, "
            "back up before changes, keep a rollback path, never print or store secrets). If it genuinely needs CAK3D's own hands — buying "
            "hardware, clicking in a web console, physical access, an interactive login — don't pretend: give short, exact steps. "
            "Your final reply is posted to Discord: say what you did and how you verified it, or the steps CAK3D needs, in a few lines. "
            + RESULT_RULE
        ) % ("job listing" if kind == "job" else "want ad", date, idx + 1, job.get("title"), job.get("agent") or "unassigned",
             job.get("details") or job.get("text") or "", job.get("ask") or "")
    code = ("import sys, json; from cron.jobs import create_job\n"
            "j = create_job(sys.argv[1], '1m', name=sys.argv[2], repeat=1, deliver='discord')\n"
            "print(j.get('id') if isinstance(j, dict) else j)")
    try:
        r = subprocess.run([os.path.join(HERMES, "hermes-agent/venv/bin/python"), "-c", code, prompt,
                            "Double Wide approval: " + str(job.get("title"))[:60]],
                           cwd=os.path.join(HERMES, "hermes-agent"), env={**os.environ, "HERMES_HOME": HERMES},
                           capture_output=True, text=True, timeout=180)
        return r.returncode == 0, (r.stdout.strip() or r.stderr.strip()[-200:])
    except Exception as e:
        return False, str(e)


def followup(date):
    """Fill in results for approved listings: read the one-off job's report (its first line is 'RESULT: …')."""
    st = load_state(date)
    changed = False
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
            failed = "script failed" in txt or "Status:** error" in txt
            v["result_status"] = "failed" if failed else "ok"
            v["result"] = (resp.replace("## Response", "").strip().splitlines() or ["finished — see Discord"])[0][:160]
        v["finished_at"] = dt.datetime.fromtimestamp(os.path.getmtime(outs[-1])).isoformat(timespec="minutes")
        changed = True
    if changed:
        with LOCK:
            save_state(date, st)
    return st


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/jobs"):
            m = re.search(r"date=(\d{4}-\d{2}-\d{2})", self.path)
            return self._json(200, followup(m.group(1)) if m else {})
        return super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/api/jobs"):
            return self._json(404, {"ok": False})
        origin = self.headers.get("Origin")
        ok_origin = not origin or origin == HOST_ORIGIN or re.fullmatch(r"http://terminal-vnic(\.[\w.-]+)?:%d" % PORT, origin)
        if self.headers.get("X-Double-Wide") != "1" or not ok_origin:
            return self._json(403, {"ok": False, "message": "Not from the paper."})
        try:
            req = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 4096)) or b"{}")
            date, idx, decision = str(req.get("date")), int(req.get("idx")), str(req.get("decision"))
            kind = str(req.get("kind") or "job")
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) and decision in ("approve", "done", "dismiss") and kind in ("job", "want", "market")
            if kind == "market":   # B.I.G's catalog, as copied into the site by the collector
                items = json.load(open(os.path.join(os.path.abspath(sys.argv[1]), "data", "market-%s.json" % date))).get("items") or []
            else:
                items = json.load(open(os.path.join(DRAFTS, date + ".json"))).get("job_listings" if kind == "job" else "want_ads") or []
            job = items[idx]
        except Exception:
            return self._json(400, {"ok": False, "message": "That listing couldn't be found."})
        key = str(idx) if kind == "job" else "%s:%d" % (kind, idx)
        with LOCK:
            st = load_state(date)
            prev = st.get(key, {})
            if decision == "approve" and prev.get("status") == "approved":
                return self._json(200, {"ok": True, "message": "Already approved — Ganja is on it."})
            entry = {"status": {"approve": "approved", "done": "done", "dismiss": "dismissed"}[decision], "kind": kind,
                     "at": dt.datetime.now().isoformat(timespec="seconds"), "title": job.get("title"), "agent": "Ganja"}
            if decision == "approve":
                ok, info = hand_to_ganja(date, idx, job, kind)
                if not ok:
                    return self._json(500, {"ok": False, "message": "Couldn't hand it to Ganja: " + info})
                entry["hermes_job"] = info
            st[key] = entry
            save_state(date, st)
        msg = {"approve": "Approved! Ganja picks it up within a minute; the result shows here and in Discord.",
               "done": "Marked done — nice work.", "dismiss": "Okay, parked for now."}[decision]
        if kind == "market" and decision == "approve":
            msg = "Noted! B.I.G drafts a starter plan (no spending) — it shows up here and in Discord."
        return self._json(200, {"ok": True, "message": msg})


if __name__ == "__main__":
    site, host, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
    HOST_ORIGIN, PORT = "http://%s:%d" % (host, port), port
    http.server.ThreadingHTTPServer((host, port), functools.partial(Handler, directory=site)).serve_forever()
