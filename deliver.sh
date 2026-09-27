#!/usr/bin/env bash
# After Ganja files the paper: rebuild the front page/back issues, hand the day's comic strips to The Sunday Smoke
# (drawn now, printed Sunday) and ring The Corner Chronicle's bell.
set -u
D="$HOME/.hermes/garden/doublewide"; PY="$HOME/.hermes/hermes-agent/venv/bin/python"; T=$(TZ=America/New_York date +%F)
[ -f "$D/site/editions/$T.html" ] || { echo "no Double Wide for $T"; exit 0; }
"$PY" "$D/build_extras.py"
HEAD=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["headline"]["title"])' "$D/drafts/$T.json" 2>/dev/null)
"$PY" "$HOME/.hermes/garden/newsstand/notify.py" "🗞️ The Double Wide is here" "${HEAD:-Today's paper is rolled.}" "/double-wide/"
"$PY" "$HOME/.hermes/garden/sunday-smoke/take_strips.py" "$D/drafts/$T.json" || true
