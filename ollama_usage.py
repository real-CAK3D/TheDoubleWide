#!/usr/bin/env python3
"""Ollama usage on NukeBox (the GMKTec NucBox) for the Token Tracker.

Ollama keeps no usage history, but its server log on NukeBox records every request: llama-server writes
"slot release: ... n_tokens = N" when a request finishes (N = prompt + generated tokens), followed by the
"[GIN] yyyy/mm/dd - hh:mm:ss | status | time | client | POST /v1/chat/completions" line. The model that
answered is the last one the log says it loaded (its Ollama tag, e.g. qwen3:4b).

  ollama_usage.py YYYY-MM-DD   -> prints {"total", "hours"[24], "by_model", "by_client", "requests"} for that day
Called by collect_inputs.usage(); read-only on NukeBox (it only reads the log over SSH).
"""
import base64, collections, datetime as dt, json, re, subprocess, sys

HOST = "nukebox"
LOGS = ["server-2.log", "server-1.log", "server.log"]   # oldest first; Ollama rotates server.log -> server-1.log ...


def ps(cmd, timeout=60):
    enc = base64.b64encode(cmd.encode("utf-16-le")).decode()
    r = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", HOST, "powershell -NoProfile -EncodedCommand " + enc],
                       capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def read_logs():
    out = []
    for f in LOGS:
        out.append(ps("$p = Join-Path $env:LOCALAPPDATA 'Ollama\\%s'; if (Test-Path $p) { Get-Content -Raw -Encoding UTF8 $p }" % f))
    return "\n".join(out)


GIN = re.compile(r"\[GIN\] (\d{4})/(\d\d)/(\d\d) - (\d\d):(\d\d):(\d\d) \| (\d{3}) \|\s*([^|]+)\|\s*([^|]+)\|\s*(\w+)\s+\"([^\"]+)\"")
REL = re.compile(r"stop processing: n_tokens = (\d+)")
NAME = re.compile(r"general\.name\s+str\s+=\s+(.+)$")
TAG = re.compile(r"model=registry\.ollama\.ai/(?:library/)?(\S+)")
REQ_MODEL = re.compile(r"\"model\"\s*:\s*\"([^\"]+)\"")


def usage(day):
    text = read_logs()
    if not text.strip():
        return None
    hours, by_model, by_client = [0] * 24, collections.Counter(), collections.Counter()
    requests, pending, model = 0, 0, "ollama"
    alias, last = {}, None   # the loader's long name ("Qwen3 4B Thinking 2507") -> the tag printed a moment later (qwen3:4b)
    for line in text.splitlines():
        m = NAME.search(line)
        if m:
            last = m.group(1).strip()
        m = TAG.search(line)
        if m and last:
            alias[last], last = m.group(1), None
    for line in text.splitlines():
        m = TAG.search(line)   # "template selection ... model=registry.ollama.ai/library/qwen3:4b" once a model is loaded
        if m:
            model = m.group(1)
            continue
        m = NAME.search(line)
        if m and m.group(1).strip() not in ("n/a", ""):
            model = alias.get(m.group(1).strip(), m.group(1).strip())
            continue
        m = REL.search(line)
        if m:
            pending += int(m.group(1))
            continue
        m = GIN.search(line)
        if not m or m.group(10) != "POST":
            continue
        path = m.group(11)
        if not any(k in path for k in ("chat", "generate", "completions", "embed")):
            continue
        tok, pending = pending, 0
        when = dt.datetime(*map(int, m.group(1, 2, 3, 4, 5, 6)))
        if when.date().isoformat() != day or not tok:
            continue
        requests += 1
        hours[when.hour] += tok
        by_model[model] += tok
        by_client[m.group(9).strip()] += tok
    return {"day": day, "total": sum(hours), "hours": hours, "by_model": dict(by_model), "by_client": dict(by_client), "requests": requests}


if __name__ == "__main__":
    print(json.dumps(usage(sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()), indent=1))
