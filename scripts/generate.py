#!/usr/bin/env python3
"""Generates the profile SVGs and the README repo cards. Stdlib only.

  python scripts/generate.py [--config config.json] [--out assets/generated] [--readme README.md]
                             [--snake out/snake-raw.svg] [--koi out/koi/koi.gif] [--demo]

--demo skips the network and renders from sample data (for local previews).
"""
import argparse
import hashlib
import html
import re
import shutil
import datetime as dt
import json
import math
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


def graphql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(API + "/graphql", data=body, headers={
        "Authorization": f"Bearer {TOKEN}", "User-Agent": "profile-readme-generator", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    if out.get("errors"):
        raise RuntimeError(out["errors"])
    return out["data"]


CAL_Q = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
  contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions
  weeks{contributionDays{date contributionCount}}}}}}"""
COL_Q = """query($login:String!){user(login:$login){repositories(ownerAffiliations:OWNER,isFork:false,first:100){
  nodes{primaryLanguage{name color}}}}}"""


def streaks(daily, today):
    """Weeks (Mon-Sun) with at least one active day; the current week can't end a streak."""
    weeks = Counter()
    for day, n in daily.items():
        if n:
            weeks[day - dt.timedelta(days=day.weekday())] += 1
    this_week = today - dt.timedelta(days=today.weekday())
    if not daily:
        return 0, 0
    first = min(daily) - dt.timedelta(days=min(daily).weekday())
    run, longest, w = 0, 0, first
    while w <= this_week:
        if weeks[w]:
            run += 1
        elif w != this_week:
            run = 0
        longest = max(longest, run)
        w += dt.timedelta(weeks=1)
    return run, longest


def koi_facts(login, created_at):
    """Total contributions, streaks, last 7 days and language colors: the inputs git-koi draws from."""
    today = dt.date.today()
    total, daily = 0, {}
    for year in range(int(created_at[:4]), today.year + 1):
        d = graphql(CAL_Q, {"login": login, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"})
        cal = d["user"]["contributionsCollection"]["contributionCalendar"]
        total += cal["totalContributions"]
        for wk in cal["weeks"]:
            for day in wk["contributionDays"]:
                daily[dt.date.fromisoformat(day["date"])] = day["contributionCount"]
    daily = {k: v for k, v in daily.items() if k <= today}
    current, longest = streaks(daily, today)
    week = sum(v for k, v in daily.items() if (today - k).days < 7)
    yesterday = daily.get(today - dt.timedelta(days=1), 0)
    year = {k: v for k, v in daily.items() if (today - k).days < 365}
    best = max(year.items(), key=lambda kv: kv[1], default=(today, 0))
    run, longest_days, d0 = 0, 0, min(daily) if daily else today
    while d0 <= today:
        run = run + 1 if daily.get(d0) else 0
        longest_days = max(longest_days, run)
        d0 += dt.timedelta(days=1)
    cur_days, d0 = 0, today if daily.get(today) else today - dt.timedelta(days=1)
    while daily.get(d0):
        cur_days += 1
        d0 -= dt.timedelta(days=1)
    colors = {}
    for n in graphql(COL_Q, {"login": login})["user"]["repositories"]["nodes"]:
        if n["primaryLanguage"]:
            colors[n["primaryLanguage"]["name"]] = n["primaryLanguage"]["color"]
    return {"total": total, "streak": current, "longest": longest, "week": week, "yesterday": yesterday, "colors": colors,
            "year_total": sum(year.values()), "active_days": sum(1 for v in year.values() if v),
            "best_day": (best[0].isoformat(), best[1]), "day_streak": cur_days, "longest_day_streak": longest_days}


TYPE_RE = re.compile(r"^\s*([a-zA-Z]+)(\([^)]*\))?!?:")
KNOWN_TYPES = {"feat", "fix", "refactor", "docs", "chore", "test", "perf", "ci", "build", "style"}


def commit_type(message):
    m = TYPE_RE.match(message or "")
    t = m.group(1).lower() if m else ""
    return t if t in KNOWN_TYPES else "other"


def collect(cfg):
    login = cfg["login"]
    tz = ZoneInfo(os.environ.get("PROFILE_TZ") or cfg.get("timezone", "America/Toronto"))
    user = get_json(f"/users/{login}")
    repos = [r for r in paginate(f"/users/{login}/repos", {"type": "owner"}) if not r["fork"]]
    hours, days, total = Counter(), Counter(), 0
    punch, per_repo, types = Counter(), Counter(), Counter()
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
            punch[(when.weekday(), when.hour)] += 1
            per_repo[r["name"]] += 1
            types[commit_type(c["commit"]["message"])] += 1
            total += 1
    try:
        prs = get_json("/search/issues", {"q": f"author:{login} type:pr is:public", "per_page": 1})["total_count"]
    except urllib.error.HTTPError:
        prs = None
    by_name = {r["name"]: r for r in repos}
    featured = []
    for name in cfg["featured"]:
        r = by_name.get(name)
        if r is None:
            try:
                r = get_json(f"/repos/{login}/{name}")
            except urllib.error.HTTPError as e:
                print(f"warning: could not read {name}: HTTP {e.code}", file=sys.stderr)
                r = {"name": name}
        featured.append({"name": r["name"], "desc": r.get("description") or "", "lang": r.get("language"),
                         "stars": r.get("stargazers_count", 0), "forks": r.get("forks_count", 0)})
    try:
        koi = koi_facts(login, user["created_at"])
    except Exception as e:  # GraphQL needs a token; the legend falls back gracefully
        print(f"warning: koi facts unavailable: {e}", file=sys.stderr)
        koi = None
    return {
        "login": login, "user": user, "repos": len(repos),
        "stars": sum(r["stargazers_count"] for r in repos),
        "langs": Counter(r["language"] for r in repos if r["language"]),
        "hours": hours, "days": days, "commits": total, "prs": prs, "featured": featured, "koi": koi,
        "punch": punch, "per_repo": per_repo, "types": types,
    }


def demo_data(cfg):
    sample = {
        "govmr": ("A blazing-fast, async Go Version Manager written in Rust. Manage toolchains effortlessly", "Rust", 21),
        "snapdb": ("Snapshot, reset, test. Fast database integration.", "Go", 4),
        "gossip": ("gossip: decoupled event handling for Go", "Go", 3),
        "doppel": ("Your data's doppelganger: deep copies without side effects.", "Go", 2),
        "treeclip.v2": ("A simple CLI Tool to facilitate your AI copy pasting", "Rust", 5),
        "gosaidno": ("AOP for Go, because I really wanted to use annotations", "Go", 1),
        "hush": ("Total silence for your videos. Encrypts the title, thumbnail, audio, and pixels into an unplayable blob. Stream-decrypt on the fly with Rust.", "Rust", 2),
        "goxide": ("Rust oxidization in Go?", "HTML", 0),
        "war": ("war - Offline dependency cache for Go projects. Fight network outages, code anywhere.", "Rust", 1),
    }
    return {
        "login": cfg["login"], "user": {"followers": 12}, "repos": 43, "stars": 58,
        "langs": Counter({"Rust": 16, "Go": 14, "Java": 4, "HTML": 3}),
        "hours": Counter({9: 120, 10: 116, 14: 180, 16: 171, 19: 64, 2: 21, 5: 80}),
        "days": Counter({0: 98, 1: 79, 2: 100, 3: 138, 4: 65, 5: 89, 6: 109}),
        "commits": 953, "prs": 144,
        "punch": Counter({(d, h): max(0, int(12 * abs(math.sin(d * 1.3 + h * .4)) - (6 if 1 < h < 4 else 0)))
                          for d in range(7) for h in range(24)}),
        "per_repo": Counter({"govmr": 212, "treeclip.v2": 140, "hush": 96, "snapdb": 88, "gossip": 61, "war": 40}),
        "types": Counter({"feat": 310, "fix": 160, "refactor": 120, "docs": 70, "chore": 90, "test": 40, "other": 163}),
        "featured": [{"name": n, "desc": sample.get(n, ("", None, 0))[0], "lang": sample.get(n, ("", None, 0))[1],
                      "stars": sample.get(n, ("", None, 0))[2], "forks": 0} for n in cfg["featured"]],
        "koi": {"total": 2140, "streak": 9, "longest": 14, "week": 23, "yesterday": 4, "year_total": 1180, "active_days": 214,
                "best_day": ("2026-03-14", 41), "day_streak": 6, "longest_day_streak": 23,
                "colors": {"Rust": "#dea584", "Go": "#00ADD8", "Java": "#b07219", "HTML": "#e34c26"}},
    }


def card_block(featured, login):
    """Clickable cards, two per row. Each card is its own SVG wrapped in a link."""
    out = []
    for r in featured:
        out.append(f'<a href="https://github.com/{login}/{r["name"]}"><img src="assets/generated/repos/{r["name"]}.svg" '
                   f'alt="{r["name"]}: {html.escape(r.get("desc") or "", quote=True)}" width="222"></a>')
    return "\n".join(out)


def patch_readme(path, block):
    start, end = "<!-- featured:start -->", "<!-- featured:end -->"
    text = open(path, encoding="utf-8").read()
    a, b = text.index(start) + len(start), text.index(end)
    text = text[:a] + "\n" + block + "\n" + text[b:]
    open(path, "w", encoding="utf-8").write(bust_cache(text, os.path.dirname(os.path.abspath(path))))


def bust_cache(text, root):
    """Append ?v=<content hash> to every generated image, so browsers and GitHub's
    image cache fetch a new copy exactly when the file changes."""
    def repl(m):
        f = os.path.join(root, m.group(1))
        if not os.path.exists(f):
            return m.group(1)
        return m.group(1) + "?v=" + hashlib.sha1(open(f, "rb").read()).hexdigest()[:10]
    return re.sub(r"(assets/generated/[\w.\-/]+?\.svg)(\?v=[0-9a-f]+)?", repl, text)


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
    if os.path.isdir(a.out):  # drop panels from older layouts and repos no longer featured
        shutil.rmtree(a.out)
    for name, svg in build_all(d, a.snake, a.koi).items():
        path = os.path.join(a.out, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(svg)
    print(f"wrote {len(os.listdir(a.out))} entries to {a.out}")
    if a.readme:
        patch_readme(a.readme, card_block(d["featured"], d["login"]))
        print(f"updated {a.readme}")


if __name__ == "__main__":
    main()
