"""Builds the profile SVGs (stdlib only).

hero.svg            terminal 1: typing intro, desk scene, about, stack
repos-header.svg    terminal title strip above the repo cards
repos/<name>.svg    one card per featured repo (the README wraps each in a link)
activity.svg        terminal 2: stats, commit rhythm, languages, snake, koi + legend
"""
import base64
import math
import os
import re
import struct
from collections import Counter
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import C, CW, FONT, esc, kt  # noqa: E402

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
W, PAD = 680, 32
IW = W - 2 * PAD          # inner width
CWX = 13 * CW             # glyph width at 13px
GAP = 64                  # space between sections

# ----------------------------------------------------------------------------
# CONTENT
# ----------------------------------------------------------------------------
HERO_LINES = [
    # (segments, font size, baseline y, weight, seconds per char)
    ([("seyallius@github", C["green"]), (":", C["overlay0"]), ("~", C["blue"]), (" $ whoami", C["text"])], 13, 76, 400, 0.07),
    ([("Helleo~", C["mauve"])], 32, 124, 500, 0.14),
    ([("Systems and backend engineer · Go and Rust", C["text"])], 14, 158, 400, 0.05),
    ([("Building tools that make other developers' lives easier", C["subtext0"])], 13, 184, 400, 0.04),
    ([("# Benkyou wa tanoshii!", C["overlay0"])], 12, 210, 400, 0.06),
]
ABOUT = [
    ("role", "Go backend engineer. Scalable systems that don't fall over."),
    ("obsessed", "Rust: systems, CLI tools, memory safety and speed."),
    ("origin", "3+ years of Java and Spring Boot microservices."),
    ("creed", "Simplicity, concurrency and performance are not trade-offs."),
    ("routine", "4 AM to 7 AM is project time. Most days."),
]
SKILLS = [
    ("languages", ["go", "rust", "java"]),
    ("frameworks", ["gin", "beego", "fiber", "actix", "spring"]),
    ("infra", ["docker", "git", "actions", "linux"]),
    ("data", ["postgres", "redis", "kafka", "mongodb"]),
]
LANG_COLORS = {
    "Go": C["sapphire"], "Rust": C["peach"], "Java": C["red"], "TypeScript": C["blue"],
    "JavaScript": C["yellow"], "Python": C["green"], "Shell": C["teal"], "CSS": C["mauve"],
    "HTML": C["pink"], "Just": C["overlay0"],
}
GH_COLORS = {  # GitHub's own language colors: the koi is painted with these
    "Go": "#00ADD8", "Rust": "#dea584", "Java": "#b07219", "Python": "#3572A5", "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a", "Shell": "#89e051", "HTML": "#e34c26", "CSS": "#663399", "Just": "#384d54",
}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
KOI_STAGES = [(0, "hatchling"), (500, "young"), (1500, "growing"), (12750, "adult")]


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def fade(base):
    return f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{base:.2f}s" fill="freeze"/>'


def txt(x, y, s, fill, size=13, weight=400, anchor=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    w = f' font-weight="{weight}"' if weight != 400 else ""
    return f'<text x="{x}" y="{y}" font-size="{size}"{w}{a} fill="{fill}" xml:space="preserve">{esc(s)}</text>'


def prompt(y, cmd, comment="", x=PAD, base=0.3):
    s = (f'<text x="{x}" y="{y}" font-size="13" fill="{C["text"]}" opacity="0" xml:space="preserve">'
         f'<tspan fill="{C["green"]}">$</tspan> {esc(cmd)}')
    if comment:
        s += f'  <tspan fill="{C["overlay0"]}">{esc(comment)}</tspan>'
    return s + fade(base) + "</text>"


def pct(n, total):
    return 0 if not total else n / total * 100


def wrap(s, width, lines):
    words, out, cur = " ".join((s or "").split()).split(" "), [], ""
    for w in words:
        if not w:
            continue
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = f"{cur} {w}" if cur else w
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    if len(out) > lines:
        last = out[lines - 1]
        while len(last) > width - 1:
            last = last.rsplit(" ", 1)[0]
        out = out[: lines - 1] + [last.rstrip(" ,.:;-") + "…"]
    return out


def chrome(title, h):
    return (
        f'<rect width="{W}" height="{h}" fill="{C["base"]}"/>'
        f'<rect width="{W}" height="30" fill="{C["mantle"]}"/>'
        f'<rect y="30" width="{W}" height="1" fill="{C["surface0"]}"/>'
        f'<circle cx="20" cy="15" r="5.5" fill="{C["red"]}"/><circle cx="39" cy="15" r="5.5" fill="{C["yellow"]}"/>'
        f'<circle cx="58" cy="15" r="5.5" fill="{C["green"]}"/>'
        f'<text x="{W / 2:g}" y="19.5" text-anchor="middle" font-size="12" fill="{C["overlay0"]}">{esc(title)}</text>'
    )


def window(title, desc, h, body, defs=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" role="img" font-family="{FONT}">'
        f"<title>{esc(title)}</title><desc>{esc(desc)}</desc>"
        f'<defs><clipPath id="win"><rect width="{W}" height="{h}" rx="10"/></clipPath>{defs}</defs>'
        f'<g clip-path="url(#win)">{chrome(title, h)}{body}</g>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="10" fill="none" stroke="{C["surface0"]}"/></svg>'
    )


def inset(x, y, w, h, fill=None):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill or C["mantle"]}" stroke="{C["surface0"]}"/>'


def blink(x, y):
    return (f'<rect x="{x:.1f}" y="{y - 12}" width="8" height="16" fill="{C["mauve"]}">'
            '<animate attributeName="opacity" values="1;0" keyTimes="0;.5" calcMode="discrete" dur="1.1s" repeatCount="indefinite"/></rect>')


# ----------------------------------------------------------------------------
# terminal 1
# ----------------------------------------------------------------------------
def typing():
    t, plan = 0.6, []
    for segs, size, y, weight, dtc in HERO_LINES:
        n = sum(len(s) for s, _ in segs)
        plan.append(dict(segs=segs, size=size, y=y, weight=weight, dt=dtc, n=n, start=t))
        t += n * dtc + 0.5
    D = round(t + 5.0, 2)
    clips, texts, ev = [], [], []
    f = plan[0]
    ev.append((0.0, PAD, f["y"] - round(f["size"] * 0.8), round(f["size"] * 0.95), round(CW * f["size"], 1)))
    for i, L in enumerate(plan):
        cw = CW * L["size"]
        times = [0.0] + [(L["start"] + k * L["dt"]) / D for k in range(L["n"])] + [1.0]
        widths = [0.0] + [round((k + 1) * cw, 1) for k in range(L["n"])] + [round(L["n"] * cw, 1)]
        clips.append(
            f'<clipPath id="h{i}"><rect x="{PAD}" y="{L["y"] - L["size"]}" width="0" height="{round(L["size"] * 1.5)}">'
            f'<animate attributeName="width" calcMode="discrete" dur="{D}s" repeatCount="indefinite" '
            f'keyTimes="{kt(times)}" values="{";".join(str(w) for w in widths)}"/></rect></clipPath>'
        )
        tsp = "".join(f'<tspan fill="{col}">{esc(s)}</tspan>' for s, col in L["segs"])
        wt = f' font-weight="{L["weight"]}"' if L["weight"] != 400 else ""
        texts.append(
            f'<text x="{PAD}" y="{L["y"]}" font-size="{L["size"]}"{wt} xml:space="preserve" '
            f'textLength="{round(L["n"] * cw, 1)}" lengthAdjust="spacing" clip-path="url(#h{i})">{tsp}</text>'
        )
        top, h, w = L["y"] - round(L["size"] * 0.8), round(L["size"] * 0.95), round(cw, 1)
        for k in range(L["n"]):
            ev.append(((L["start"] + k * L["dt"]) / D, round(PAD + (k + 1) * cw, 1), top, h, w))
    keys = kt([e[0] for e in ev] + [1.0])

    def vals(idx):
        return ";".join(str(e[idx]) for e in ev) + ";" + str(ev[-1][idx])

    cursor = (
        f'<rect x="{PAD}" y="{ev[0][2]}" width="{ev[0][4]}" height="{ev[0][3]}" fill="{C["mauve"]}">'
        + "".join(
            f'<animate attributeName="{a}" calcMode="discrete" dur="{D}s" repeatCount="indefinite" keyTimes="{keys}" values="{vals(i)}"/>'
            for a, i in (("x", 1), ("y", 2), ("height", 3), ("width", 4))
        )
        + '<animate attributeName="opacity" values="1;0" keyTimes="0;.5" calcMode="discrete" dur="1.1s" repeatCount="indefinite"/></rect>'
    )
    return "".join(texts) + cursor, "".join(clips), HERO_LINES[-1][2]


def desk(y):
    src = open(os.path.join(ASSETS, "desk-scene.svg"), encoding="utf-8").read()
    inner = src[src.index("<defs>"): src.rindex("</svg>")]
    inner = re.sub(r'<rect width="680" height="28" fill="#181825"/>\n?', "", inner)
    inner = re.sub(r'<circle cx="18" cy="14"[^\n]*\n', "", inner)
    inner = re.sub(r'<text x="340" y="18"[^\n]*desk\.svg</text>\n?', "", inner)
    inner = inner.replace('<rect width="680" height="320" rx="8"/>', '<rect width="680" height="320"/>')
    for i in ("pc", "wc", "sc", "wp", "fl", "kp", "rp", "code"):
        inner = (inner.replace(f'id="{i}"', f'id="d-{i}"').replace(f"url(#{i})", f"url(#d-{i})")
                 .replace(f'href="#{i}"', f'href="#d-{i}"'))
    sy = y + 22
    sh = round(IW * 292 / 680, 1)
    clip = f'<clipPath id="scene"><rect x="{PAD}" y="{sy}" width="{IW}" height="{sh}" rx="8"/></clipPath>'
    body = (prompt(y, "./sunrise.sh", "# 04:00 → 07:00, every day")
            + f'<g clip-path="url(#scene)"><svg x="{PAD}" y="{sy}" width="{IW}" height="{sh}" viewBox="0 28 680 292">{inner}</svg></g>'
            + f'<rect x="{PAD}" y="{sy}" width="{IW}" height="{sh}" rx="8" fill="none" stroke="{C["surface0"]}"/>')
    return body, clip, sy + sh


def about(y):
    out = [prompt(y, "cat about.md", base=0.5)]
    col = PAD + 11 * CWX
    for i, (k, v) in enumerate(ABOUT):
        yy = y + 36 + i * 28
        out.append(f'<g opacity="0">{txt(PAD, yy, k, C["blue"])}{txt(round(col, 1), yy, v, C["text"])}{fade(0.6 + i * 0.1)}</g>')
    return "".join(out), "", y + 36 + (len(ABOUT) - 1) * 28


def stack(y):
    out = [prompt(y, "cat stack.toml", base=0.6)]
    toks, t = [], 0.6
    for r, (key, items) in enumerate(SKILLS):
        yy = y + 36 + r * 30
        toks.append((PAD, yy, key, C["blue"], t))
        x = PAD + 12 * CWX
        toks.append((x, yy, "= [", C["overlay0"], t + 0.1))
        x += 3 * CWX
        for j, it in enumerate(items):
            t += 0.18
            s = f'"{it}"'
            toks.append((x, yy, s, C["green"], t))
            x += len(s) * CWX
            if j < len(items) - 1:
                toks.append((x, yy, ", ", C["overlay0"], t))
                x += 2 * CWX
        toks.append((x, yy, "]", C["overlay0"], t))
        t += 0.3
    D = round(t + 6.0, 2)
    for x, yy, s, col, ta in toks:
        out.append(
            f'<text x="{round(x, 1)}" y="{yy}" font-size="13" fill="{col}" opacity="0" xml:space="preserve" '
            f'textLength="{round(len(s) * CWX, 1)}" lengthAdjust="spacing">{esc(s)}'
            f'<animate attributeName="opacity" calcMode="discrete" dur="{D}s" repeatCount="indefinite" '
            f'keyTimes="0;{ta / D:.4f};1" values="0;1;1"/></text>'
        )
    return "".join(out), "", y + 36 + (len(SKILLS) - 1) * 30


def hero_svg():
    parts, defs = [], []
    s, df, y = typing()
    parts.append(s)
    defs.append(df)
    for fn in (desk, about, stack):
        s, df, y = fn(y + GAP)
        parts.append(s)
        defs.append(df)
    h = round(y + 44)
    return window("seyallius — zsh", "Typing intro, a pixel-art animation of a developer coding from 4 AM until sunrise, about me and my tech stack.",
                  h, "".join(parts), "".join(defs))


# ----------------------------------------------------------------------------
# repo cards
# ----------------------------------------------------------------------------
CARD_W, CARD_H = 222, 148


def repos_header_svg(n):
    h = 74
    body = prompt(58, "ls ~/repos --featured", f"# {n} repos · click a card to open it", base=0.1)
    return window("~/repos — zsh", "Featured repositories.", h, body)


def repo_card_svg(r):
    lang = r.get("lang")
    col = LANG_COLORS.get(lang, C["overlay0"])
    lines = wrap(r.get("desc") or "no description yet", 25, 3)
    desc = "".join(txt(18, 58 + i * 18, ln, C["subtext0"], 12) for i, ln in enumerate(lines))
    meta, x = [], 18
    if lang:
        meta.append(f'<circle cx="{x + 4}" cy="{CARD_H - 23}" r="4.5" fill="{col}"/>{txt(x + 14, CARD_H - 19, lang.lower(), C["text"], 12)}')
        x += 14 + len(lang) * 7.2 + 14
    meta.append(txt(round(x, 1), CARD_H - 19, f"★ {r.get('stars', 0)}", C["yellow"], 12))
    name = r["name"] if len(r["name"]) <= 17 else r["name"][:16] + "…"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARD_W} {CARD_H}" width="{CARD_W}" height="{CARD_H}" role="img" font-family="{FONT}">'
        f"<title>{esc(r['name'])}</title><desc>{esc(r.get('desc') or '')}</desc>"
        f'<defs><clipPath id="c"><rect width="{CARD_W}" height="{CARD_H}" rx="10"/></clipPath></defs>'
        f'<g clip-path="url(#c)"><rect width="{CARD_W}" height="{CARD_H}" fill="{C["base"]}"/>'
        f'<rect width="{CARD_W}" height="3" fill="{col}"/></g>'
        f'<rect x=".5" y=".5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="10" fill="none" stroke="{C["surface0"]}"/>'
        f'<text x="18" y="32" font-size="14" font-weight="600" fill="{C["mauve"]}"><tspan fill="{C["overlay0"]}" font-weight="400">~/</tspan>{esc(name)}</text>'
        f'{desc}<rect x="18" y="{CARD_H - 40}" width="{CARD_W - 36}" height="1" fill="{C["surface0"]}"/>{"".join(meta)}'
        f'{txt(CARD_W - 18, CARD_H - 19, "open ↗", C["overlay0"], 11, anchor="end")}</svg>'
    )


# ----------------------------------------------------------------------------
# terminal 2
# ----------------------------------------------------------------------------
def stats(y, d):
    tiles = [("repos", d["repos"], C["mauve"]), ("stars", d["stars"], C["yellow"]),
             ("followers", d["user"].get("followers", 0), C["blue"]),
             ("commits", d["commits"], C["peach"]), ("pull requests", d["prs"], C["green"])]
    gap, top, th = 12, y + 22, 78
    tw = (IW - 4 * gap) / 5
    out = [prompt(y, f"gh api users/{d['login']} --summary", base=0.2)]
    for i, (label, val, col) in enumerate(tiles):
        x = PAD + i * (tw + gap)
        v = "n/a" if val is None else f"{val:,}"
        out.append(
            f'<g opacity="0">{inset(round(x, 1), top, round(tw, 1), th)}'
            f'<text x="{x + tw / 2:.1f}" y="{top + 40}" text-anchor="middle" font-size="24" font-weight="600" fill="{col}">{v}</text>'
            f'<text x="{x + tw / 2:.1f}" y="{top + 61}" text-anchor="middle" font-size="12" fill="{C["subtext0"]}">{esc(label)}</text>{fade(0.3 + i * 0.12)}</g>'
        )
    return "".join(out), top + th


def bar_row(x, y, label, color, value_px, track, value_text, i, lw=76):
    return (
        f'<g opacity="0">{fade(0.5 + i * 0.1)}'
        f'{txt(x, y, label, C["subtext0"], 12)}'
        f'<rect x="{x + lw}" y="{y - 11}" width="{track}" height="12" rx="3" fill="{C["surface0"]}"/>'
        f'<rect x="{x + lw}" y="{y - 11}" width="0" height="12" rx="3" fill="{color}">'
        f'<animate attributeName="width" from="0" to="{value_px:.0f}" dur="1.2s" begin="{0.6 + i * 0.12:.2f}s" fill="freeze"/></rect>'
        f'{txt(x + lw + track + 10, y, value_text, C["text"], 12)}</g>'
    )


def insights(y, d):
    total, track = d["commits"], 128
    buckets = [
        ("morning", C["yellow"], sum(d["hours"][h] for h in range(6, 12))),
        ("daytime", C["peach"], sum(d["hours"][h] for h in range(12, 18))),
        ("evening", C["mauve"], sum(d["hours"][h] for h in range(18, 24))),
        ("night", C["blue"], sum(d["hours"][h] for h in range(0, 6))),
    ]
    top = max((b[2] for b in buckets), default=1) or 1
    xl, xr, step = PAD, 362, 32
    out = [prompt(y, "commits --by-hour", x=xl, base=0.4), prompt(y, "repos --by-lang", x=xr, base=0.4)]
    for i, (label, col, n) in enumerate(buckets):
        out.append(bar_row(xl, y + 40 + i * step, label, col, track * n / top, track, f"{pct(n, total):.1f}%", i))
    langs = d["langs"].most_common(4)
    ltop = max((n for _, n in langs), default=1)
    for i, (lang, n) in enumerate(langs):
        out.append(bar_row(xr, y + 40 + i * step, lang.lower(), LANG_COLORS.get(lang, C["overlay0"]),
                           track * n / ltop, track, f"{n} repos" if n != 1 else "1 repo", i))
    peak = max(range(7), key=lambda k: d["days"][k]) if d["days"] else 0
    fy = y + 40 + 4 * step + 4
    out.append(txt(xl, fy, f"# peak day: {DAYS[peak].lower()}", C["overlay0"], 12))
    out.append(txt(xr, fy, f"# across {d['repos']} repositories", C["overlay0"], 12))
    out.append(f'<rect x="340" y="{y + 20}" width="1" height="{fy - y - 26}" fill="{C["surface0"]}"/>')
    return "".join(out), fy


def tiles(y, cmd, comment, items, base=0.3):
    gap, top, th = 12, y + 22, 78
    tw = (IW - (len(items) - 1) * gap) / len(items)
    out = [prompt(y, cmd, comment, base=base)]
    for i, (label, val, col) in enumerate(items):
        x = PAD + i * (tw + gap)
        out.append(
            f'<g opacity="0">{inset(round(x, 1), top, round(tw, 1), th)}'
            f'<text x="{x + tw / 2:.1f}" y="{top + 40}" text-anchor="middle" font-size="22" font-weight="600" fill="{col}">{esc(val)}</text>'
            f'<text x="{x + tw / 2:.1f}" y="{top + 61}" text-anchor="middle" font-size="12" fill="{C["subtext0"]}">{esc(label)}</text>{fade(base + 0.1 + i * 0.12)}</g>'
        )
    return "".join(out), top + th


def year(y, d):
    k = d.get("koi")
    if not k or "year_total" not in k:
        return "", y - GAP
    date, n = k["best_day"]
    best = dt_label(date)
    return tiles(y, "git log --since='1 year'", "# the last 365 days", [
        ("contributions", f"{k['year_total']:,}", C["peach"]),
        ("active days", f"{k['active_days']}", C["green"]),
        ("current streak", f"{k['day_streak']}d", C["mauve"]),
        ("longest streak", f"{k['longest_day_streak']}d", C["blue"]),
        (f"best · {best}", f"{n}", C["yellow"]),
    ], base=0.4)


def dt_label(iso):
    m = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    y_, mo, da = iso.split("-")
    return f"{m[int(mo) - 1]} {int(da)}"


def punchcard(y, d):
    punch = d.get("punch") or {}
    out = [prompt(y, "git log --punchcard", "# when my commits land, by weekday and hour", base=0.5)]
    top = y + 22
    h = 7 * 24 + 44
    out.append(inset(PAD, top, IW, h))
    x0, step = PAD + 56, (IW - 76) / 24
    mx = max(punch.values(), default=0) or 1
    for di, name in enumerate(["mon", "tue", "wed", "thu", "fri", "sat", "sun"]):
        cy = top + 26 + di * 24
        out.append(txt(PAD + 18, cy + 4, name, C["subtext0"], 11))
        for hr in range(24):
            v = punch.get((di, hr), 0)
            cx = x0 + hr * step + step / 2
            if v:
                f = (v / mx) ** 0.5
                r = 2 + 6.5 * f
                out.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="0" fill="{C["mauve"]}" opacity="{0.35 + 0.65 * f:.2f}">'
                           f'<animate attributeName="r" from="0" to="{r:.1f}" dur="0.6s" begin="{0.6 + (di * 24 + hr) * 0.006:.2f}s" fill="freeze"/></circle>')
            else:
                out.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="1.2" fill="{C["surface1"]}"/>')
    for hr in range(0, 24, 3):
        out.append(txt(round(x0 + hr * step + step / 2, 1), top + h - 12, f"{hr:02d}", C["overlay0"], 11, anchor="middle"))
    return "".join(out), top + h


TYPE_COLORS = {"feat": C["green"], "fix": C["red"], "refactor": C["mauve"], "docs": C["blue"], "chore": C["overlay0"],
               "test": C["yellow"], "perf": C["peach"], "ci": C["teal"], "build": C["sapphire"], "style": C["pink"], "other": C["surface2"]}


def repos_and_types(y, d):
    per_repo = (d.get("per_repo") or Counter()).most_common(5)
    types = (d.get("types") or Counter())
    if not per_repo:
        return "", y - GAP
    xl, xr, step, track, lw = PAD, 362, 32, 104, 96
    out = [prompt(y, "top --repos", "# by my commits", x=xl, base=0.5), prompt(y, "git log --types", x=xr, base=0.5)]
    rmax = per_repo[0][1] or 1
    pal = [C["mauve"], C["blue"], C["teal"], C["green"], C["yellow"]]
    for i, (name, n) in enumerate(per_repo):
        label = name if len(name) <= 12 else name[:11] + "…"
        out.append(bar_row(xl, y + 40 + i * step, label, pal[i], track * n / rmax, track, f"{n:,}", i, lw))
    tot = sum(types.values()) or 1
    top_t = [t for t in types.most_common() if t[0] != "other"][:4] + ([("other", types["other"])] if types.get("other") else [])
    tmax = max((n for _, n in top_t), default=1) or 1
    for i, (t, n) in enumerate(top_t):
        out.append(bar_row(xr, y + 40 + i * step, t, TYPE_COLORS.get(t, C["overlay0"]), track * n / tmax, track, f"{pct(n, tot):.0f}%", i, lw - 20))
    rows = max(len(per_repo), len(top_t))
    fy = y + 40 + rows * step + 4
    out.append(txt(xl, fy, f"# {sum(n for _, n in per_repo) * 100 // max(d['commits'], 1)}% of my commits live here", C["overlay0"], 12))
    out.append(txt(xr, fy, "# conventional-commit prefixes", C["overlay0"], 12))
    out.append(f'<rect x="340" y="{y + 20}" width="1" height="{fy - y - 26}" fill="{C["surface0"]}"/>')
    return "".join(out), fy


def snake(y, path):
    out = [prompt(y, "./snake.sh", "# eats my contribution graph, square by square", base=0.5)]
    top = y + 22
    if path and os.path.exists(path):
        raw = re.sub(r"^\s*<\?xml[^>]*\?>", "", open(path, encoding="utf-8").read())
        m = re.search(r"<svg\b[^>]*>", raw)
        minx, miny, vw, vh = [float(v) for v in re.search(r'viewBox="([\d.\s-]+)"', m.group(0)).group(1).split()]
        inner = raw[m.end(): raw.rindex("</svg>")]
        aw = IW - 32
        ah = aw * vh / vw
        out.append(inset(PAD, top, IW, round(ah + 32, 1)))
        out.append(f'<svg x="{PAD + 16}" y="{top + 16}" width="{aw}" height="{ah:.1f}" viewBox="{minx} {miny} {vw} {vh}">{inner}</svg>')
        return "".join(out), top + ah + 32
    out.append(inset(PAD, top, IW, 100))
    out.append(txt(W / 2, top + 54, "the snake appears after the first workflow run", C["overlay0"], 12, anchor="middle"))
    return "".join(out), top + 100


def gif_bbox(path):
    """Union of all frame rectangles in a GIF (stdlib only), or None."""
    b = open(path, "rb").read()
    if b[:3] != b"GIF":
        return None
    cw, ch, packed = struct.unpack("<HHB", b[6:11])
    i = 13 + (3 * 2 ** ((packed & 7) + 1) if packed & 0x80 else 0)
    box = None

    def skip_blocks(i):
        while b[i]:
            i += b[i] + 1
        return i + 1

    while i < len(b):
        tag = b[i]
        if tag == 0x21:
            i = skip_blocks(i + 2)
        elif tag == 0x2C:
            l, t, w, h, p = struct.unpack("<HHHHB", b[i + 1:i + 10])
            box = (l, t, l + w, t + h) if box is None else (min(box[0], l), min(box[1], t), max(box[2], l + w), max(box[3], t + h))
            i += 10 + (3 * 2 ** ((p & 7) + 1) if p & 0x80 else 0)
            i = skip_blocks(i + 1)
        else:
            break
    if box is None:
        return 0, 0, cw, ch
    if box == (0, 0, cw, ch):
        return box
    m = 10
    return max(0, box[0] - m), max(0, box[1] - m), min(cw, box[2] + m), min(ch, box[3] + m)


def koi_stage(total):
    return [name for lim, name in KOI_STAGES if total >= lim][-1]


KOI_BODY = "white"  # keep in sync with the git-koi "body" input in the workflow
PIGMENTS = {  # git-koi snaps every language color to the nearest of these by hue
    "red": ("#d9412b", "beni"), "orange": ("#f08a24", "orenji"), "yellow": ("#f2c94c", "ki"),
    "blue": ("#3d7fd1", "ai"), "black": ("#2a2a2e", "sumi"),
}


def pigment(hex_color):
    """Mirror of git-koi's select_pigment: hue bands, grays become black."""
    if not hex_color:
        return "black"
    r, g, b = (int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn < 0.12:
        return "black"
    if mx == r:
        h = (60 * ((g - b) / (mx - mn))) % 360
    elif mx == g:
        h = 60 * ((b - r) / (mx - mn)) + 120
    else:
        h = 60 * ((r - g) / (mx - mn)) + 240
    if h >= 330 or h < 18:
        return "red"
    if h < 45:
        return "orange"
    if h < 160:
        return "yellow"
    return "blue"


def pond_decor(bx, by, bw, bh):
    out = []
    for i, (px, py, r, dl) in enumerate([(0.18, 0.3, 26, 0), (0.7, 0.72, 34, 2.3), (0.45, 0.2, 20, 4.1), (0.86, 0.3, 22, 5.6)]):
        cx, cy = bx + px * bw, by + py * bh
        out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="2" fill="none" stroke="{C["surface1"]}" stroke-width="1.5" opacity="0">'
                   f'<animate attributeName="r" values="2;{r}" dur="4s" begin="{dl}s" repeatCount="indefinite"/>'
                   f'<animate attributeName="opacity" values=".8;0" dur="4s" begin="{dl}s" repeatCount="indefinite"/></circle>')
    for px, py, r in [(0.08, 0.15, 3), (0.93, 0.85, 4), (0.55, 0.9, 2.5), (0.3, 0.82, 3.5), (0.62, 0.1, 2.5)]:
        out.append(f'<circle cx="{bx + px * bw:.0f}" cy="{by + py * bh:.0f}" r="{r}" fill="{C["surface0"]}"/>')
    return "".join(out)


def lily(cx, cy, r, rot):
    a0, a1 = math.radians(rot - 9), math.radians(rot + 9)
    p0 = (cx + r * math.cos(a0), cy + r * math.sin(a0))
    p1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
    return (f'<path d="M{cx},{cy} L{p0[0]:.1f},{p0[1]:.1f} A{r},{r} 0 1 0 {p1[0]:.1f},{p1[1]:.1f} Z" fill="#3b5a4a" opacity=".9"/>'
            f'<path d="M{cx},{cy} L{p0[0]:.1f},{p0[1]:.1f} A{r},{r} 0 1 0 {p1[0]:.1f},{p1[1]:.1f} Z" fill="none" stroke="#5d9a6e" stroke-opacity=".7"/>'
            f'<path d="M{cx},{cy} L{cx - r * .7 * math.cos(math.radians(rot)):.1f},{cy - r * .7 * math.sin(math.radians(rot)):.1f}" stroke="#5d9a6e" stroke-opacity=".5"/>')


def koi(y, path, d):
    out = [prompt(y, "git koi", "# a pixel koi that lives off my GitHub activity", base=0.6)]
    top, bh = y + 22, 300
    bx = PAD
    defs = f'<clipPath id="pond"><rect x="{bx}" y="{top}" width="{IW}" height="{bh}" rx="8"/></clipPath>'
    out.append(inset(bx, top, IW, bh, C["crust"]))
    out.append(f'<g clip-path="url(#pond)">{pond_decor(bx, top, IW, bh)}')
    if path and os.path.exists(path):
        x0, y0, x1, y1 = gif_bbox(path) or (0, 0, 512, 512)
        cw_, ch_ = x1 - x0, y1 - y0
        s = 230 / cw_
        dw, dh = cw_ * s, ch_ * s
        gw, gh = gif_size(path)
        b64 = base64.b64encode(open(path, "rb").read()).decode()
        X0, Y0 = bx, top
        route = (f"M{X0 + 130},{Y0 + 150} C{X0 + 200},{Y0 + 40} {X0 + 420},{Y0 + 30} {X0 + 500},{Y0 + 110} "
                 f"C{X0 + 570},{Y0 + 180} {X0 + 520},{Y0 + 270} {X0 + 410},{Y0 + 240} "
                 f"C{X0 + 320},{Y0 + 215} {X0 + 290},{Y0 + 120} {X0 + 190},{Y0 + 210} "
                 f"C{X0 + 110},{Y0 + 280} {X0 + 50},{Y0 + 200} {X0 + 130},{Y0 + 150} Z")
        out.append(
            f'<g><animateMotion dur="34s" repeatCount="indefinite" rotate="auto" path="{route}" calcMode="linear" '
            f'keyPoints="0;0.22;0.3;0.55;0.62;0.86;1" keyTimes="0;0.2;0.36;0.58;0.7;0.9;1"/>'
            f'<svg x="{-dw / 2:.1f}" y="{-dh / 2:.1f}" width="{dw:.1f}" height="{dh:.1f}" viewBox="{x0} {y0} {cw_} {ch_}">'
            f'<image href="data:image/gif;base64,{b64}" width="{gw}" height="{gh}" style="image-rendering:pixelated"/></svg></g>'
        )
    else:
        out.append(txt(W / 2, top + bh / 2 + 4, "the koi appears after the first workflow run", C["overlay0"], 12, anchor="middle"))
    out.append(lily(bx + 70, top + 52, 30, 30) + lily(bx + IW - 60, top + bh - 50, 36, 200) + lily(bx + IW - 120, top + 40, 18, 120))
    out.append("</g>")

    # legend: what the fish actually encodes
    ly = top + bh + 34
    key = lambda yy, k: txt(PAD, yy, k, C["blue"])  # noqa: E731
    vx = PAD + 10 * CWX
    rows = []
    k = d.get("koi")
    colors = (k or {}).get("colors") or {}
    total_l = sum(d["langs"].values()) or 1
    groups = {}
    for lang, n in d["langs"].items():
        pg = pigment(colors.get(lang) or GH_COLORS.get(lang))
        groups.setdefault(pg, []).append((lang, n))
    ranked = sorted(groups.items(), key=lambda kv: -sum(n for _, n in kv[1]))
    yy = ly
    for i, (pg, items) in enumerate(ranked[:4]):
        share = sum(n for _, n in items) / total_l * 100
        names = ", ".join(l.lower() for l, _ in sorted(items, key=lambda t: -t[1])[:3])
        hexc, jp = PIGMENTS[pg]
        rows.append((key(yy, "colors") if i == 0 else "")
                    + f'<rect x="{vx}" y="{yy - 10}" width="11" height="11" rx="2" fill="{hexc}" stroke="{C["surface2"]}" stroke-width=".5"/>'
                    + txt(round(vx + 18, 1), yy, f"{pg} ({jp}) {share:.0f}%", C["text"], 12)
                    + txt(round(vx + 18 + 22 * 7.2, 1), yy, f"← {names}", C["subtext0"], 12))
        yy += 20
    rows.append(f'<rect x="{vx}" y="{yy - 10}" width="11" height="11" rx="2" fill="#dfe3ea"/>'
                + txt(round(vx + 18, 1), yy, f"{KOI_BODY} ground", C["text"], 12)
                + txt(round(vx + 18 + 22 * 7.2, 1), yy, "← the body type, the base under the patches", C["subtext0"], 12))
    rows.append(txt(vx, yy + 20, "# git-koi snaps each language to one of 5 koi pigments by hue", C["overlay0"], 11))
    ly2 = yy + 52
    if k:
        total = k["total"]
        frac = lambda t: math.log2(1 + min(t, 100000) / 50) / math.log2(1 + 100000 / 50)  # noqa: E731  git-koi's growth curve
        tw = 230
        bar = (f'<rect x="{vx}" y="{ly2 - 10}" width="{tw}" height="10" rx="3" fill="{C["surface0"]}"/>'
               f'<rect x="{vx}" y="{ly2 - 10}" width="0" height="10" rx="3" fill="{C["peach"]}">'
               f'<animate attributeName="width" from="0" to="{tw * frac(total):.1f}" dur="1.4s" begin="0.8s" fill="freeze"/></rect>')
        for lim, _ in KOI_STAGES[1:]:
            bar += f'<rect x="{vx + tw * frac(lim):.1f}" y="{ly2 - 13}" width="1.5" height="16" fill="{C["overlay0"]}"/>'
        bar += txt(round(vx + tw + 14, 1), ly2, f"{total:,} contributions · {koi_stage(total)}", C["text"], 12)
        rows.append(key(ly2, "size") + bar)
        rows.append(txt(vx, ly2 + 20, "# it grows with every contribution; ticks = 500 / 1.5k / 12.75k", C["overlay0"], 12))
        ly3 = ly2 + 52
        rows.append(key(ly3, "streak") + txt(vx, ly3, f"{k['streak']} weeks running · longest {k['longest']}", C["text"], 12))
        rows.append(txt(vx, ly3 + 20, "# streaks brighten the colors and paint the fin tips", C["overlay0"], 12))
        ly4 = ly3 + 52
        rows.append(key(ly4, "mood") + txt(vx, ly4, f"{k.get('yesterday', 0)} contributions yesterday · {k['week']} this week", C["text"], 12))
        rows.append(txt(vx, ly4 + 20, "# the day that just ended sets how it swims; redrawn every night", C["overlay0"], 12))
        end = ly4 + 20
    else:
        rows.append(key(ly2, "size") + txt(vx, ly2, "grows with my total contributions", C["text"], 12))
        end = ly2
    out.append(f'<g opacity="0">{"".join(rows)}{fade(0.7)}</g>')
    return "".join(out), end, defs


def gif_size(path):
    b = open(path, "rb").read(10)
    return struct.unpack("<HH", b[6:10])


def footer(y):
    s = "$ exit  # bye-bye!"
    line = (f'<text x="{PAD}" y="{y}" font-size="13" fill="{C["text"]}" xml:space="preserve"><tspan fill="{C["green"]}">$</tspan> exit  '
            f'<tspan fill="{C["overlay0"]}"># bye-bye!</tspan></text>')
    return line + blink(PAD + len(s) * CWX + 6, y), y


def activity_svg(d, snake_path=None, koi_path=None):
    parts, defs = [], []
    y = 70
    for fn in (lambda y: stats(y, d), lambda y: year(y, d), lambda y: insights(y, d), lambda y: punchcard(y, d),
               lambda y: repos_and_types(y, d), lambda y: snake(y, snake_path),
               lambda y: koi(y, koi_path, d), footer):
        res = fn(y)
        parts.append(res[0])
        if len(res) > 2:
            defs.append(res[2])
        y = res[1] + GAP
    h = round(y - GAP + 40)
    return window("activity — zsh", "GitHub stats, the last year, commit rhythm, a punch card, top repos, commit types, "
                  "the contribution snake and a swimming pixel koi with a legend.", h, "".join(parts), "".join(defs))


def build_all(d, snake_path=None, koi_path=None):
    files = {"hero.svg": hero_svg(), "repos-header.svg": repos_header_svg(len(d["featured"])),
             "activity.svg": activity_svg(d, snake_path, koi_path)}
    for r in d["featured"]:
        files[f"repos/{r['name']}.svg"] = repo_card_svg(r)
    return files
