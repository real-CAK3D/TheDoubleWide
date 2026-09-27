#!/usr/bin/env python3
"""Copy this paper's prompt file(s) into the writer agent's Hermes job (jobs keep their own copy of the prompt),
creating the job (paused; its relay timer triggers it) the first time. Run after editing a prompt:
  ~/.hermes/hermes-agent/venv/bin/python sync_prompt.py
"""
import json, os, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
H = os.path.expanduser("~/.hermes")
CODE = r"""
import sys
from cron.jobs import load_jobs, update_job, create_job, pause_job
name, prompt, script = sys.argv[1], open(sys.argv[2]).read(), sys.argv[3] or None
j = next((j for j in load_jobs() if j.get("name") == name), None)
if j is None:
    j = create_job(prompt, "0 0 1 1 *", name=name, deliver="discord", script=script)
    pause_job(j["id"]); print("created", j["id"], name)
elif j.get("prompt") != prompt or (script and j.get("script") != script):
    update_job(j["id"], {"prompt": prompt, **({"script": script} if script else {})}); print("updated", j["id"], name)
else:
    print("in sync", j["id"], name)
"""
for job in json.load(open(os.path.join(ROOT, "jobs.json"))):
    home = H if job["profile"] == "main" else os.path.join(H, "profiles", job["profile"])
    r = subprocess.run([os.path.join(H, "hermes-agent/venv/bin/python"), "-c", CODE, job["name"], os.path.join(ROOT, job["prompt"]), job.get("script", "")],
                       cwd=os.path.join(H, "hermes-agent"), env={**os.environ, "HERMES_HOME": home}, capture_output=True, text=True, timeout=120)
    print(((r.stdout or r.stderr).strip().splitlines() or ["?"])[-1])
