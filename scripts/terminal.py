"""Assembles the whole profile as ONE terminal-window SVG (stdlib only).

Static content (hero lines, about, skills) lives in the CONTENT block below.
Data-driven sections (featured repos, stats, insights) come from generate.py.
The snake svg and the koi gif are optional inputs produced by other actions.
"""
import base64
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import C, CW, FONT, esc, kt  # noqa: E402

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
W, X = 680, 24
CWX = 13 * CW  # glyph width at 13px

# ----------------------------------------------------------------------------
# CONTENT
# ----------------------------------------------------------------------------
HERO_LINES = [
    # (segments [(text, color)], font size, baseline y, weight, seconds per char)
    ([("seyallius@github", C["green"]), (":", C["overlay0"]), ("~", C["blue"]), (" $ whoami", C["text"])], 13, 58, 400, 0.07),
    ([("Helleo~", C["mauve"])], 30, 96, 500, 0.14),
    ([("Systems and backend engineer · Go and Rust", C["text"])], 14, 124, 400, 0.05),
    ([("Building tools that make other developers' lives easier", C["subtext0"])], 13, 146, 400, 0.04),
    ([("# Benkyou wa tanoshii!", C["overlay0"])], 12, 168, 400, 0.06),
]
HERO_END = 184

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
    "HTML": C["peach"], "Just": C["overlay0"],
}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
def fade(base):
    return f'<animate attributeName="opacity" from="0" to="1" dur="0.4s" begin="{base:.2f}s" fill="freeze"/>'


def prompt(y, cmd, comment="", x=X, base=0.2):
    s = (f'<text x="{x}" y="{y}" font-size="13" fill="{C["text"]}" opacity="0" xml:space="preserve">'
         f'<tspan fill="{C["green"]}">$</tspan> {esc(cmd)}')
    if comment:
        s += f' <tspan fill="{C["overlay0"]}">{esc(comment)}</tspan>'
    return s + fade(base) + "</text>"


def txt(x, y, s, fill, size=13, weight=400, anchor=None, extra=""):
    a = f' text-anchor="{anchor}"' if anchor else ""
    w = f' font-weight="{weight}"' if weight != 400 else ""
    return f'<text x="{x}" y="{y}" font-size="{size}"{w}{a} fill="{fill}" {extra}>{esc(s)}</text>'


def truncate(s, n):
    s = " ".join(s.split())
    if len(s) <= n:
        return s
    head = s[: n - 1]
    cut = head.rsplit(" ", 1)[0] if " " in head else head
    return cut.rstrip(" ,.:;-") + "…"


def pct(n, total):
    return 0 if not total else n / total * 100


# ----------------------------------------------------------------------------
# sections: each returns (svg, defs, next_y)
# ----------------------------------------------------------------------------
def hero():
    t, plan = 0.6, []
    for segs, size, y, weight, dtc in HERO_LINES:
        n = sum(len(s) for s, _ in segs)
        plan.append(dict(segs=segs, size=size, y=y, weight=weight, dt=dtc, n=n, start=t))
        t += n * dtc + 0.5
    D = round(t + 5.0, 2)
    clips, texts, ev = [], [], []
    first = plan[0]
    ev.append((0.0, X, first["y"] - round(first["size"] * 0.8), round(first["size"] * 0.95), round(CW * first["size"], 1)))
    for i, L in enumerate(plan):
        cw = CW * L["size"]
        times = [0.0] + [(L["start"] + k * L["dt"]) / D for k in range(L["n"])] + [1.0]
        widths = [0.0] + [round((k + 1) * cw, 1) for k in range(L["n"])] + [round(L["n"] * cw, 1)]
        clips.append(
            f'<clipPath id="h{i}"><rect x="{X}" y="{L["y"] - L["size"]}" width="0" height="{round(L["size"] * 1.5)}">'
            f'<animate attributeName="width" calcMode="discrete" dur="{D}s" repeatCount="indefinite" '
            f'keyTimes="{kt(times)}" values="{";".join(str(w) for w in widths)}"/></rect></clipPath>'
        )
        tsp = "".join(f'<tspan fill="{col}">{esc(s)}</tspan>' for s, col in L["segs"])
        wt = f' font-weight="{L["weight"]}"' if L["weight"] != 400 else ""
        texts.append(
            f'<text x="{X}" y="{L["y"]}" font-size="{L["size"]}"{wt} xml:space="preserve" '
            f'textLength="{round(L["n"] * cw, 1)}" lengthAdjust="spacing" clip-path="url(#h{i})">{tsp}</text>'
        )
        top, h, w = L["y"] - round(L["size"] * 0.8), round(L["size"] * 0.95), round(cw, 1)
        for k in range(L["n"]):
            ev.append(((L["start"] + k * L["dt"]) / D, round(X + (k + 1) * cw, 1), top, h, w))
    keys = kt([e[0] for e in ev] + [1.0])

    def vals(idx):
        return ";".join(str(e[idx]) for e in ev) + ";" + str(ev[-1][idx])

    cursor = (
        f'<rect x="{X}" y="{ev[0][2]}" width="{ev[0][4]}" height="{ev[0][3]}" fill="{C["mauve"]}">'
        + "".join(
            f'<animate attributeName="{a}" calcMode="discrete" dur="{D}s" repeatCount="indefinite" keyTimes="{keys}" values="{vals(i)}"/>'
            for a, i in (("x", 1), ("y", 2), ("height", 3), ("width", 4))
        )
        + '<animate attributeName="opacity" values="1;0" keyTimes="0;.5" calcMode="discrete" dur="1.1s" repeatCount="indefinite"/></rect>'
    )
    return "".join(texts) + cursor, "".join(clips), HERO_END


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
    h = 292
    svg = (prompt(y, "./sunrise.sh", "# 04:00 to 07:00", base=0.3)
           + f'<svg x="0" y="{y + 12}" width="{W}" height="{h}" viewBox="0 28 {W} {h}">{inner}</svg>')
    return svg, "", y + 12 + h


def about(y):
    out = [prompt(y, "cat about.md", base=0.4)]
    col = X + 10 * CWX + 8
    for i, (k, v) in enumerate(ABOUT):
        yy = y + 28 + i * 22
        out.append(
            f'<g opacity="0">{txt(X, yy, k, C["blue"])}{txt(round(col, 1), yy, v, C["text"])}{fade(0.5 + i * 0.1)}</g>'
        )
    return "".join(out), "", y + 28 + len(ABOUT) * 22 - 10


def featured(y, repos):
    out = [prompt(y, "gh repo list --pinned", f"# {len(repos)} repos", base=0.5)]
    name_w = max([len(r["name"]) for r in repos] + [8])
    dx = X + 16 + (name_w + 2) * CWX
    for i, r in enumerate(repos):
        yy = y + 28 + i * 22
        col = LANG_COLORS.get(r.get("lang"), C["overlay0"])
        desc = truncate(r.get("desc") or "", int((W - X - 70 - dx) / (12 * CW)))
        out.append(
            f'<g opacity="0"><circle cx="{X + 4}" cy="{yy - 4}" r="4" fill="{col}"/>'
            f'{txt(X + 16, yy, r["name"], C["mauve"], 13, 500)}{txt(round(dx, 1), yy, desc, C["subtext0"], 12)}'
            f'{txt(W - X, yy, (r.get("lang") or "").lower(), C["overlay0"], 12, anchor="end")}{fade(0.6 + i * 0.05)}</g>'
        )
    return "".join(out), "", y + 28 + len(repos) * 22 - 10


def stack(y):
    out = [prompt(y, "cat stack.toml", base=0.5)]
    toks, t = [], 0.5
    for r, (key, items) in enumerate(SKILLS):
        yy = y + 28 + r * 24
        toks.append((X, yy, key, C["blue"], t))
        x = X + 12 * CWX
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
    return "".join(out), "", y + 28 + len(SKILLS) * 24 - 14


def stats(y, d):
    tiles = [("repos", d["repos"], C["mauve"]), ("stars", d["stars"], C["yellow"]),
             ("followers", d["user"].get("followers", 0), C["blue"]),
             ("commits", d["commits"], C["peach"]), ("pull requests", d["prs"], C["green"])]
    out = [prompt(y, f"gh api users/{d['login']} --summary", base=0.5)]
    tw, gap = 116, 13
    for i, (label, val, col) in enumerate(tiles):
        x = X + i * (tw + gap)
        v = "n/a" if val is None else f"{val:,}"
        out.append(
            f'<g opacity="0"><rect x="{x}" y="{y + 14}" width="{tw}" height="46" rx="6" fill="{C["mantle"]}" stroke="{C["surface0"]}"/>'
            f'<text x="{x + tw / 2}" y="{y + 36}" text-anchor="middle" font-size="20" font-weight="500" fill="{col}">{v}</text>'
            f'<text x="{x + tw / 2}" y="{y + 52}" text-anchor="middle" font-size="12" fill="{C["subtext0"]}">{esc(label)}</text>{fade(0.6 + i * 0.1)}</g>'
        )
    return "".join(out), "", y + 14 + 46


def bar_row(x, y, label, color, value_px, track, value_text, i):
    return (
        f'<g opacity="0">{fade(0.6 + i * 0.1)}'
        f'{txt(x, y, label, C["subtext0"], 12)}'
        f'<rect x="{x + 76}" y="{y - 11}" width="{track}" height="12" rx="3" fill="{C["surface0"]}"/>'
        f'<rect x="{x + 76}" y="{y - 11}" width="0" height="12" rx="3" fill="{color}">'
        f'<animate attributeName="width" from="0" to="{value_px:.0f}" dur="1.2s" begin="{0.7 + i * 0.12:.2f}s" fill="freeze"/></rect>'
        f'{txt(x + 76 + track + 10, y, value_text, C["text"], 12)}</g>'
    )


def insights(y, d):
    total, track = d["commits"], 150
    buckets = [
        ("morning", C["yellow"], sum(d["hours"][h] for h in range(6, 12))),
        ("daytime", C["peach"], sum(d["hours"][h] for h in range(12, 18))),
        ("evening", C["mauve"], sum(d["hours"][h] for h in range(18, 24))),
        ("night", C["blue"], sum(d["hours"][h] for h in range(0, 6))),
    ]
    top = max((b[2] for b in buckets), default=1) or 1
    xl, xr = X, 352
    out = [prompt(y, "commits --by-hour", x=xl, base=0.5), prompt(y, "repos --by-lang", x=xr, base=0.5)]
    out.append(f'<rect x="338" y="{y - 12}" width="1" height="{28 + 4 * 26 + 8}" fill="{C["surface0"]}"/>')
    for i, (label, col, n) in enumerate(buckets):
        out.append(bar_row(xl, y + 28 + i * 26, label, col, track * n / top, track, f"{pct(n, total):.1f}%", i))
    langs = d["langs"].most_common(4)
    ltop = max((n for _, n in langs), default=1)
    for i, (lang, n) in enumerate(langs):
        out.append(bar_row(xr, y + 28 + i * 26, lang.lower(), LANG_COLORS.get(lang, C["overlay0"]),
                           track * n / ltop, track, f"{n} repos" if n != 1 else "1 repo", i))
    peak = max(range(7), key=lambda k: d["days"][k]) if d["days"] else 0
    out.append(txt(xl, y + 28 + 4 * 26 + 6, f"# peak day: {DAYS[peak].lower()}", C["overlay0"], 12))
    out.append(txt(xr, y + 28 + 4 * 26 + 6, f"# across {d['repos']} repositories", C["overlay0"], 12))
    return "".join(out), "", y + 28 + 4 * 26 + 6


def snake_inner(path):
    raw = open(path, encoding="utf-8").read()
    raw = re.sub(r"^\s*<\?xml[^>]*\?>", "", raw)
    m = re.search(r"<svg\b[^>]*>", raw)
    vb = re.search(r'viewBox="([\d.\s-]+)"', m.group(0))
    minx, miny, vw, vh = [float(v) for v in vb.group(1).split()]
    return raw[m.end(): raw.rindex("</svg>")], (minx, miny, vw, vh)


def pair(y, snake=None, koi=None):
    bw, bh = 310, 124
    lx, rx_ = X, X + bw + 12
    out = [prompt(y, "./snake & git-koi", base=0.6)]
    top = y + 14
    for x in (lx, rx_):
        out.append(f'<rect x="{x}" y="{top}" width="{bw}" height="{bh}" rx="6" fill="{C["mantle"]}" stroke="{C["surface0"]}"/>')
    if snake and os.path.exists(snake):
        inner, (minx, miny, vw, vh) = snake_inner(snake)
        aw = bw - 24
        ah = aw * vh / vw
        out.append(f'<svg x="{lx + 12}" y="{top + (bh - ah) / 2:.1f}" width="{aw}" height="{ah:.1f}" viewBox="{minx} {miny} {vw} {vh}">{inner}</svg>')
    else:
        out.append(txt(lx + bw / 2, top + bh / 2 + 4, "snake appears after the first workflow run", C["overlay0"], 12, anchor="middle"))
    if koi and os.path.exists(koi):
        b64 = base64.b64encode(open(koi, "rb").read()).decode()
        out.append(f'<image href="data:image/gif;base64,{b64}" x="{rx_ + 12}" y="{top + 8}" width="{bw - 24}" height="{bh - 16}" '
                   'preserveAspectRatio="xMidYMid meet" style="image-rendering:pixelated"/>')
    else:
        out.append(txt(rx_ + bw / 2, top + bh / 2 + 4, "koi appears after the first workflow run", C["overlay0"], 12, anchor="middle"))
    cy = top + bh + 16
    out.append(txt(lx, cy, "# eats your contributions", C["overlay0"], 12))
    out.append(txt(rx_, cy, "# redrawn nightly from your activity", C["overlay0"], 12))
    return "".join(out), "", cy


def footer(y):
    s = "$ exit # bye-bye!"
    cur = (
        f'<rect x="{round(X + len(s) * CWX + 6, 1)}" y="{y - 12}" width="9" height="16" fill="{C["mauve"]}">'
        '<animate attributeName="opacity" values="1;0" keyTimes="0;.5" calcMode="discrete" dur="1.1s" repeatCount="indefinite"/></rect>'
    )
    line = (f'<text x="{X}" y="{y}" font-size="13" fill="{C["text"]}"><tspan fill="{C["green"]}">$</tspan> exit '
            f'<tspan fill="{C["overlay0"]}"># bye-bye!</tspan></text>')
    return line + cur, "", y


# ----------------------------------------------------------------------------
def assemble(d, snake=None, koi=None):
    body, defs = [], []
    s, df, y = hero()
    body.append(s)
    defs.append(df)
    y += 22
    for fn in (
        lambda y: desk(y),
        lambda y: about(y),
        lambda y: featured(y, d["featured"]),
        lambda y: stack(y),
        lambda y: stats(y, d),
        lambda y: insights(y, d),
        lambda y: pair(y, snake, koi),
    ):
        s, df, y_end = fn(y)
        body.append(s)
        defs.append(df)
        y = y_end + 34
    s, _, y_end = footer(y)
    body.append(s)
    total = y_end + 26
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {total}" width="{W}" height="{total}" role="img" font-family="{FONT}">'
        f"<title>seyallius</title><desc>A single terminal window: typing intro, pixel-art animation of a developer's morning, about, "
        f"featured repositories, tech stack, GitHub stats, commit rhythm, contribution snake and a pixel koi.</desc>"
        f"<defs>{''.join(defs)}</defs>"
        f'<rect width="{W}" height="{total}" rx="8" fill="{C["base"]}"/>'
        f'<rect width="{W}" height="28" rx="8" fill="{C["mantle"]}"/><rect y="14" width="{W}" height="14" fill="{C["mantle"]}"/>'
        f'<circle cx="18" cy="14" r="5" fill="{C["red"]}"/><circle cx="36" cy="14" r="5" fill="{C["yellow"]}"/><circle cx="54" cy="14" r="5" fill="{C["green"]}"/>'
        f'<text x="{W / 2:g}" y="18" text-anchor="middle" font-size="12" fill="{C["overlay0"]}">seyallius — zsh</text>'
    )
    return head + "".join(body) + "</svg>"
