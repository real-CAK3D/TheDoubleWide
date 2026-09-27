#!/usr/bin/env python3
"""Draw The Double Wide's funnies as real newspaper comic strips.

Ganja writes each strip's script into the edition draft (title, byline, 3-4 panels with a scene and lines).
This turns every strip into one inked, hand-lettered strip image with the Codex image model (gpt-image-2,
same ChatGPT login the agents use), saves it under site/img/funnies/ and records the path in the draft.
Run after Ganja's job:  draw_funnies.py drafts/<date>.json   (then re-render). Safe to re-run: drawn strips are skipped.
"""
import base64, concurrent.futures as cf, importlib.util, io, json, os, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "site", "img", "funnies")
HERMES = os.path.expanduser("~/.hermes/hermes-agent")
SIZE, QUALITY = "2048x768", "medium"

# How each agent is drawn, taken from their portraits so they look the same every day.
LOOKS = {
    "Ganja": "GANJA, a friendly woman in her 30s with shoulder-length wavy auburn-brown hair and a dark green sweater",
    "The Gardiner": "THE GARDINER, a weathered, kindly old woman with long gray hair under a wide straw hat decorated with dried herbs and buttons",
    "CHRONIC": "CHRONIC, a laid-back man with long wavy light-brown hair, a scruffy beard and a striped knitted poncho-style sweater",
    "Maple": "MAPLE, a Black woman with voluminous curly deep-red hair, cat-eye glasses, hoop earrings and a green cardigan over a patterned blouse",
    "CYPH3R": "CYPH3R, a young Black woman with long box braids, round glasses and a green plaid flannel shirt",
    "Homie": "HOMIE, a middle-aged man with curly salt-and-pepper hair, a short gray beard, round dark glasses and a tweed blazer",
    "Ibby": "IBBY, a young Black man with short twists and a denim button-up shirt",
    "Disco Stu": "DISCO STU, a balding man with a bushy mustache, large glasses, a very red flushed face, brown suit and striped tie",
    "BAK3R": "BAK3R, a smiling Asian man in his 50s with graying swept-back hair, a short gray goatee and a denim shirt",
    "B.I.G": "B.I.G, a big heavyset Black man with a short beard, a dark paisley velvet blazer and a gold chain",
    "Clydius": "CLYDIUS, a stocky, muscular short-haired American pit bull terrier (NOT a retriever) with a copper-brown coat, red nose, cropped-looking pointed ears, white chest and a gray collar (a dog: he barks, he doesn't talk)",
    "tinyZ": "TINYZ, a teenage boy with shaggy light-brown hair and an olive hoodie",
    "Herbie": "HERBIE, a small round green robot companion with a cannabis-leaf cap like a little mushroom hat, big glowing green eyes and a peace-sign pendant",
    "Fat Man": "FAT MAN, a round, olive-drab metal barrel-shaped machine with a boxy tail fin and a cartoon face (he is the Windows mini-PC)",
    "Little Boy": "LITTLE BOY, a long, slim olive-drab metal cylinder machine with a boxy tail fin and a cartoon face (he is the laptop)",
}
ALIASES = {"Gardiner": "The Gardiner", "Gardener": "The Gardiner", "Chronic": "CHRONIC", "Cyph3r": "CYPH3R", "Bak3r": "BAK3R",
           "BIG": "B.I.G", "tiny-Z": "tinyZ", "TinyZ": "tinyZ", "FatMan": "Fat Man", "LittleBoy": "Little Boy", "DiscoStu": "Disco Stu"}

STYLE = ("A classic 1940s American Sunday-newspaper comic strip: ONE horizontal row of {n} equal panels with black ink borders and white gutters, "
         "hand-drawn pen-and-ink cartoon art with flat, slightly faded newsprint colors and Ben-Day dots, expressive faces, simple backgrounds. "
         "Hand-lettered speech balloons in all caps, easy to read, spelled EXACTLY as given; no other words except small signs if natural. "
         "Title lettered in bold at the top left: '{title}', and a small byline beside it: '{byline}'. Clean, good-natured, family-friendly.")


def canon(name):
    name = (name or "").strip()
    return ALIASES.get(name, name)


def strip_prompt(s):
    panels = [p if isinstance(p, dict) else {"scene": str(p)} for p in (s.get("panels") or [])[:4]]
    who = []
    for p in panels:
        for c in p.get("cast") or []:
            a = canon((c or {}).get("agent"))
            if a in LOOKS and a not in who:
                who.append(a)
    lines = [STYLE.format(n=len(panels), title=(s.get("title") or "The Funnies").upper(), byline=s.get("byline") or "by the Garden Gang")]
    if who:
        lines.append("Characters (draw them the same in every panel): " + "; ".join(LOOKS[a] for a in who) + ".")
    for i, p in enumerate(panels, 1):
        bits = ["Panel %d:" % i]
        if p.get("caption"):
            bits.append("caption box in the corner reading '%s'." % p["caption"])
        if p.get("scene"):
            bits.append(p["scene"].rstrip(".") + ".")
        for c in p.get("cast") or []:
            if isinstance(c, dict) and c.get("says"):
                bits.append("%s says in a balloon: '%s'." % (canon(c.get("agent")).upper(), c["says"].upper()))
        if p.get("sfx"):
            bits.append("small sound-effect lettering '%s'." % p["sfx"])
        lines.append(" ".join(bits))
    return "\n".join(lines)


def load_codex():
    sys.path.insert(0, HERMES)
    spec = importlib.util.spec_from_file_location("codex_img", os.path.join(HERMES, "plugins/image_gen/openai-codex/__init__.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def draw(cx, token, prompt, dest):
    from PIL import Image
    last = None
    for attempt in range(2):
        try:
            b64 = cx._collect_image_b64(token, prompt=prompt, size=SIZE, quality=QUALITY)
            if b64:
                im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
                im.thumbnail((1800, 1800))
                im.save(dest, "JPEG", quality=84, optimize=True, progressive=True)
                return True
            last = "no image returned"
        except Exception as ex:
            last = "%s: %s" % (type(ex).__name__, str(ex)[:160])
        time.sleep(10)
    print("  failed:", last)
    return False


def main():
    path = sys.argv[1]
    ed = json.load(open(path))
    date = ed.get("date") or os.path.basename(path)[:10]
    fun = ed.get("funnies") or {}
    strips = [s for s in (fun.get("strips") or []) if isinstance(s, dict)][:4]
    todo = [(i, s) for i, s in enumerate(strips) if not (s.get("image") and os.path.exists(os.path.join(ROOT, "site", s["image"].replace("../", ""))))]
    if not todo:
        print("funnies: nothing to draw")
        return
    os.makedirs(OUT, exist_ok=True)
    cx = load_codex()
    token = cx._read_codex_access_token()
    if not token:
        print("funnies: no Codex login available; strips stay as text")
        return
    jobs = {}
    with cf.ThreadPoolExecutor(max_workers=2) as pool:   # 2 at a time: kind to the 1 GB VM and the rate limit
        for i, s in todo:
            name = "%s-%d.jpg" % (date, i + 1)
            jobs[pool.submit(draw, cx, token, strip_prompt(s), os.path.join(OUT, name))] = (i, name)
        for f in cf.as_completed(jobs):
            i, name = jobs[f]
            if f.result():
                strips[i]["image"] = "../img/funnies/" + name
                print("funnies: drew", name)
    ed = json.load(open(path))   # re-read in case the draft changed while drawing
    ed.setdefault("funnies", {})["strips"] = strips
    json.dump(ed, open(path, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
