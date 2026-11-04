#!/usr/bin/env python3
"""Generates the profile SVG panels and the README repo table. Stdlib only.

  python scripts/generate.py [--config config.json] [--out assets/generated] [--readme README.md]
                             [--snake out/snake-raw.svg] [--koi out/koi/koi.gif] [--demo]

--demo skips the network and renders from sample data (for local previews).
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panels import build_all  # noqa: E402

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


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
            featured.append({"name": r["name"], "desc": r.get("description") or "", "lang": r.get("language")})
        except urllib.error.HTTPError as e:
            print(f"warning: could not read {name}: HTTP {e.code}", file=sys.stderr)
            featured.append({"name": name, "desc": "", "lang": None})
    return {
        "login": login, "user": user, "repos": len(repos),
        "stars": sum(r["stargazers_count"] for r in repos),
        "langs": Counter(r["language"] for r in repos if r["language"]),
        "hours": hours, "days": days, "commits": total, "prs": prs, "featured": featured,
    }


def demo_data(cfg):
    sample = {
        "govmr": ("A blazing-fast, async Go Version Manager written in Rust. Manage toolchains effortlessly", "Rust"),
        "snapdb": ("Snapshot, reset, test. Fast database integration.", "Go"),
        "gossip": ("gossip: decoupled event handling for Go", "Go"),
        "doppel": ("Your data's doppelganger: deep copies without side effects.", "Go"),
        "treeclip.v2": ("A simple CLI Tool to facilitate your AI copy pasting", "Rust"),
        "gosaidno": ("AOP for Go, because I really wanted to use annotations", "Go"),
        "hush": ("Total silence for your videos.", "Rust"),
    }
    return {
        "login": cfg["login"], "user": {"followers": 12}, "repos": 46, "stars": 58,
        "langs": Counter({"Go": 13, "Rust": 12, "Java": 4, "Just": 1}),
        "hours": Counter({9: 1200, 10: 1216, 14: 1800, 16: 1741, 19: 641, 2: 210}),
        "days": Counter({0: 981, 1: 797, 2: 1001, 3: 1388, 4: 657, 5: 893, 6: 1091}),
        "commits": 6808, "prs": 112,
        "featured": [{"name": n, "desc": sample.get(n, ("", None))[0], "lang": sample.get(n, ("", None))[1]} for n in cfg["featured"]],
    }


def repo_table(featured, login):
    rows = ["| repository | what it does | language |", "| :-- | :-- | :-- |"]
    for r in featured:
        desc = " ".join((r.get("desc") or "").split()).replace("|", "\\|")
        lang = f"`{r['lang']}`" if r.get("lang") else ""
        rows.append(f"| [**{r['name']}**](https://github.com/{login}/{r['name']}) | {desc} | {lang} |")
    return "\n".join(rows)


def patch_readme(path, table):
    start, end = "<!-- featured:start -->", "<!-- featured:end -->"
    text = open(path, encoding="utf-8").read()
    a, b = text.index(start) + len(start), text.index(end)
    open(path, "w", encoding="utf-8").write(text[:a] + "\n\n" + table + "\n\n" + text[b:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json"))
    ap.add_argument("--out", default="assets/generated")
    ap.add_argument("--readme")
    ap.add_argument("--snake")
    ap.add_argument("--koi")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    d = demo_data(cfg) if a.demo else collect(cfg)
    os.makedirs(a.out, exist_ok=True)
    for name, svg in build_all(d, a.snake, a.koi).items():
        path = os.path.join(a.out, name)
        open(path, "w", encoding="utf-8").write(svg)
        print(f"wrote {path} ({os.path.getsize(path) // 1024} KB)")
    if a.readme:
        patch_readme(a.readme, repo_table(d["featured"], d["login"]))
        print(f"updated {a.readme}")


if __name__ == "__main__":
    main()
