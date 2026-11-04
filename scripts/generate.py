#!/usr/bin/env python3
"""Generates the data-driven profile SVGs from public GitHub data. Stdlib only.

  python scripts/generate.py [--config config.json] [--out out] [--demo]
  python scripts/generate.py frame-snake  IN.svg OUT.svg
  python scripts/generate.py frame-koi    IN.gif OUT.svg

Writes to --out: stats.svg, insights.svg, featured-header.svg, card-<repo>.svg.
--demo skips the network and renders from sample data (for local previews).
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import C, CW, esc, svg_open, panel_open, panel_close, prompt_line, text  # noqa: E402

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
LANG_COLORS = {
    "Go": C["sapphire"], "Rust": C["peach"], "Java": C["red"], "TypeScript": C["blue"],
    "JavaScript": C["yellow"], "Python": C["green"], "Shell": C["teal"], "CSS": C["mauve"],
    "HTML": C["peach"], "Just": C["overlay0"],
}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ----------------------------------------------------------------------------
# data
# ----------------------------------------------------------------------------
def get_json(path, params=None):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return json.load(r)


def paginate(path, params=None, per_page=100, max_pages=200):
    out, page = [], 1
    while page <= max_pages:
        chunk = get_json(path, {**(params or {}), "per_page": per_page, "page": page})
        out += chunk
        if len(chunk) < per_page:
            break
        page += 1
    return out


def collect(cfg):
    login = cfg["login"]
    tz = ZoneInfo(os.environ.get("PROFILE_TZ") or cfg.get("timezone", "America/Toronto"))
    user = get_json(f"/users/{login}")
    repos = [r for r in paginate(f"/users/{login}/repos", {"type": "owner"}) if not r["fork"]]
    hours, days, total = Counter(), Counter(), 0
    for r in repos:
        try:
            commits = paginate(f"/repos/{r['full_name']}/commits", {"author": login})
        except urllib.error.HTTPError as e:
            if e.code == 409:  # empty repository
                continue
            raise
        for c in commits:
            when = dt.datetime.fromisoformat(c["commit"]["author"]["date"].replace("Z", "+00:00")).astimezone(tz)
            hours[when.hour] += 1
            days[when.weekday()] += 1
            total += 1
    try:
        prs = get_json("/search/issues", {"q": f"author:{login} type:pr is:public", "per_page": 1})["total_count"]
    except urllib.error.HTTPError:
        prs = None
    featured = []
    for name in cfg["featured"]:
        try:
            r = get_json(f"/repos/{login}/{name}")
            featured.append({"name": r["name"], "desc": r.get("description") or "", "lang": r.get("language"), "url": r["html_url"]})
        except urllib.error.HTTPError as e:
            # keep a placeholder card so the README never shows a broken image
            print(f"warning: could not read {name}: HTTP {e.code}", file=sys.stderr)
            featured.append({"name": name, "desc": "", "lang": None, "url": f"https://github.com/{login}/{name}"})
    return {
        "login": login, "user": user, "repos": len(repos),
        "stars": sum(r["stargazers_count"] for r in repos),
        "langs": Counter(r["language"] for r in repos if r["language"]),
        "hours": hours, "days": days, "commits": total, "prs": prs, "featured": featured,
    }


def demo_data(cfg):
    return {
        "login": cfg["login"], "user": {"followers": 12}, "repos": 46, "stars": 58,
        "langs": Counter({"Go": 13, "Rust": 12, "Java": 4, "Just": 1}),
        "hours": Counter({9: 1200, 10: 1216, 14: 1800, 16: 1741, 19: 641, 2: 210, 7: 800, 20: 0}),
        "days": Counter({0: 981, 1: 797, 2: 1001, 3: 1388, 4: 657, 5: 893, 6: 1091}),
        "commits": 6808, "prs": 112,
        "featured": [
            {"name": n, "desc": d, "lang": l, "url": f"https://github.com/{cfg['login']}/{n}"}
            for n, d, l in [
                ("govmr", "A blazing-fast, async Go Version Manager written in Rust. Manage toolchains effortlessly", "Rust"),
                ("gossip", "gossip: decoupled event handling for Go", "Go"),
                ("doppel", "Your data's doppelganger: deep copies without side effects.", "Go"),
                ("gosaidno", "AOP for Go, because I really wanted to use annotations", "Go"),
                ("treeclip.v2", "A simple CLI Tool to facilitate your AI copy pasting", "Rust"),
                ("hush", "Total silence for your videos.", "Rust"),
            ]
        ],
    }


# ----------------------------------------------------------------------------
# rendering
# ----------------------------------------------------------------------------
def pct(n, total):
    return 0 if not total else n / total * 100


def fade(i, step=0.18, base=0.2):
    return f'<animate attributeName="opacity" from="0" to="1" dur="0.4s" begin="{base + i * step:.2f}s" fill="freeze"/>'


def render_stats(d):
    W, H = 680, 132
    tiles = [("repos", d["repos"], C["mauve"]), ("stars", d["stars"], C["yellow"]),
             ("followers", d["user"].get("followers", 0), C["blue"]),
             ("commits", d["commits"], C["peach"]), ("pull requests", d["prs"], C["green"])]
    tw, gap = 120, 14
    x0 = (W - (5 * tw + 4 * gap)) / 2
    out = [svg_open(W, H, "stats.sh", "GitHub stats: " + ", ".join(f"{k} {v}" for k, v, _ in tiles)), panel_open(W, H, "stats.sh")]
    out.append(prompt_line(24, 58, f"gh api users/{d['login']} --summary"))
    for i, (label, val, col) in enumerate(tiles):
        x = round(x0 + i * (tw + gap), 1)
        v = "n/a" if val is None else f"{val:,}"
        out.append(
            f'<g opacity="0"><rect x="{x}" y="72" width="{tw}" height="46" rx="6" fill="{C["mantle"]}" stroke="{C["surface0"]}"/>'
            f'<text x="{x + tw / 2}" y="94" text-anchor="middle" font-size="20" font-weight="500" fill="{col}">{v}</text>'
            f'<text x="{x + tw / 2}" y="110" text-anchor="middle" font-size="12" fill="{C["subtext0"]}">{esc(label)}</text>{fade(i)}</g>'
        )
    out += [panel_close(), "</svg>"]
    return "".join(out)


def bar_row(y, label, color, value_px, track_px, value_text, i):
    return (
        f'<g opacity="0">{fade(i, 0.12, 0.1)}'
        f'<text x="20" y="{y}" font-size="12" fill="{C["subtext0"]}">{esc(label)}</text>'
        f'<rect x="96" y="{y - 11}" width="{track_px}" height="12" rx="3" fill="{C["surface0"]}"/>'
        f'<rect x="96" y="{y - 11}" width="0" height="12" rx="3" fill="{color}">'
        f'<animate attributeName="width" from="0" to="{value_px:.0f}" dur="1.2s" begin="{0.2 + i * 0.12:.2f}s" fill="freeze"/></rect>'
        f'<text x="{96 + track_px + 10}" y="{y}" font-size="12" fill="{C["text"]}">{esc(value_text)}</text></g>'
    )


def render_insights(d):
    W, H, PW = 680, 204, 336
    total = d["commits"]
    buckets = [
        ("morning", C["yellow"], sum(d["hours"][h] for h in range(6, 12))),
        ("daytime", C["peach"], sum(d["hours"][h] for h in range(12, 18))),
        ("evening", C["mauve"], sum(d["hours"][h] for h in range(18, 24))),
        ("night", C["blue"], sum(d["hours"][h] for h in range(0, 6))),
    ]
    track = 150
    top = max((b[2] for b in buckets), default=1) or 1
    out = [svg_open(W, H, "insights", "Commit rhythm by time of day and repositories by language")]
    out.append(panel_open(PW, H, "rhythm.log"))
    out.append(prompt_line(20, 58, "commits --by-hour"))
    for i, (label, col, n) in enumerate(buckets):
        out.append(bar_row(88 + i * 26, label, col, track * n / top, track, f"{pct(n, total):.1f}%", i))
    peak = max(range(7), key=lambda k: d["days"][k]) if d["days"] else 0
    out.append(f'<text x="20" y="192" font-size="12" fill="{C["overlay0"]}"># peak day: {DAYS[peak].lower()}</text>')
    out.append(panel_close())
    out.append(panel_open(PW, H, "languages.log", x=344))
    out.append(prompt_line(20, 58, "repos --by-lang"))
    langs = d["langs"].most_common(4)
    ltop = max((n for _, n in langs), default=1)
    for i, (lang, n) in enumerate(langs):
        out.append(bar_row(88 + i * 26, lang.lower(), LANG_COLORS.get(lang, C["overlay0"]), track * n / ltop, track, f"{n} repos" if n != 1 else "1 repo", i))
    out.append(f'<text x="20" y="192" font-size="12" fill="{C["overlay0"]}"># across {d["repos"]} repositories</text>')
    out.append(panel_close())
    out.append("</svg>")
    return "".join(out)


def render_featured_header(n):
    W, H = 680, 62
    return "".join([
        svg_open(W, H, "featured.sh", "Featured repositories"), panel_open(W, H, "featured.sh"),
        prompt_line(24, 52, "gh repo list --pinned", f"# {n} repos"), panel_close(), "</svg>",
    ])


def truncate(s, n):
    s = " ".join(s.split())
    if len(s) <= n:
        return s
    cut = s[: n - 1].rsplit(" ", 1)[0] if " " in s[: n - 1] else s[: n - 1]
    return cut.rstrip(" ,.:;-") + "…"


def render_card(r):
    W, H = 340, 64
    lang = r.get("lang")
    parts = [svg_open(W, H, r["name"], f"{r['name']}: {r['desc']}"),
             f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="6" fill="{C["mantle"]}" stroke="{C["surface0"]}"/>',
             text(14, 26, r["name"], C["mauve"], 14, 500),
             text(14, 48, truncate(r["desc"], 44) or "no description yet", C["subtext0"], 12)]
    if lang:
        tw = len(lang) * 12 * CW
        parts.append(text(W - 14, 26, lang, C["subtext0"], 12, anchor="end"))
        parts.append(f'<circle cx="{W - 14 - tw - 10:.1f}" cy="22" r="4" fill="{LANG_COLORS.get(lang, C["overlay0"])}"/>')
    parts.append("</svg>")
    return "".join(parts)


# ----------------------------------------------------------------------------
# framing the third-party outputs (snake svg, koi gif) in terminal panels
# ----------------------------------------------------------------------------
PW, PH = 336, 190


def frame_snake(src, dst):
    raw = open(src, encoding="utf-8").read()
    raw = re.sub(r"^\s*<\?xml[^>]*\?>", "", raw)
    m = re.search(r"<svg\b[^>]*>", raw)
    vb = re.search(r'viewBox="([\d.\s-]+)"', m.group(0))
    minx, miny, vw, vh = [float(v) for v in vb.group(1).split()]
    inner = raw[m.end(): raw.rindex("</svg>")]
    aw = PW - 36
    ah = aw * vh / vw
    ay = 28 + (PH - 28 - 36 - ah) / 2 + 8
    body = (
        svg_open(PW, PH, "snake.svg", "Contribution snake") + panel_open(PW, PH, "snake.svg")
        + f'<svg x="18" y="{ay:.1f}" width="{aw}" height="{ah:.1f}" viewBox="{minx} {miny} {vw} {vh}">{inner}</svg>'
        + text(18, PH - 14, "# eats your contributions", C["overlay0"], 12) + panel_close() + "</svg>"
    )
    open(dst, "w", encoding="utf-8").write(body)


def frame_koi(src, dst):
    b64 = base64.b64encode(open(src, "rb").read()).decode()
    body = (
        svg_open(PW, PH, "koi.gif", "Pixel-art koi drawn from public GitHub activity") + panel_open(PW, PH, "koi.gif")
        + f'<image href="data:image/gif;base64,{b64}" x="18" y="38" width="{PW - 36}" height="{PH - 38 - 36}" '
        'preserveAspectRatio="xMidYMid meet" style="image-rendering:pixelated"/>'
        + text(18, PH - 14, "# redrawn nightly from your activity", C["overlay0"], 12) + panel_close() + "</svg>"
    )
    open(dst, "w", encoding="utf-8").write(body)


# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    for name in ("frame-snake", "frame-koi"):
        p = sub.add_parser(name)
        p.add_argument("src")
        p.add_argument("dst")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json"))
    ap.add_argument("--out", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.cmd == "frame-snake":
        return frame_snake(a.src, a.dst)
    if a.cmd == "frame-koi":
        return frame_koi(a.src, a.dst)

    cfg = json.load(open(a.config, encoding="utf-8"))
    d = demo_data(cfg) if a.demo else collect(cfg)
    os.makedirs(a.out, exist_ok=True)
    files = {"stats.svg": render_stats(d), "insights.svg": render_insights(d),
             "featured-header.svg": render_featured_header(len(d["featured"]))}
    for r in d["featured"]:
        files[f"card-{r['name']}.svg"] = render_card(r)
    for name, body in files.items():
        open(os.path.join(a.out, name), "w", encoding="utf-8").write(body)
    # the README is built from this list, so a missing repo never leaves a broken image
    json.dump([{"name": r["name"], "url": r["url"]} for r in d["featured"]],
              open(os.path.join(a.out, "featured.json"), "w"), indent=2)
    print(f"wrote {len(files)} files to {a.out}")


if __name__ == "__main__":
    main()
