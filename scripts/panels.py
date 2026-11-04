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
CARD_W, CARD_H = 336, 124


def repos_header_svg(n):
    h = 74
    body = prompt(58, "ls ~/repos --featured", f"# {n} repos · click a card to open it", base=0.1)
    return window("~/repos — zsh", "Featured repositories.", h, body)


def repo_card_svg(r):
    lang = r.get("lang")
    col = LANG_COLORS.get(lang, C["overlay0"])
    lines = wrap(r.get("desc") or "no description yet", 40, 2)
    desc = "".join(txt(20, 62 + i * 19, ln, C["subtext0"], 12) for i, ln in enumerate(lines))
    meta = []
    x = 20
    if lang:
        meta.append(f'<circle cx="{x + 5}" cy="{CARD_H - 24}" r="5" fill="{col}"/>{txt(x + 16, CARD_H - 20, lang.lower(), C["text"], 12)}')
        x += 16 + len(lang) * 7.2 + 18
    meta.append(txt(round(x, 1), CARD_H - 20, f"★ {r.get('stars', 0)}", C["yellow"], 12))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARD_W} {CARD_H}" width="{CARD_W}" height="{CARD_H}" role="img" font-family="{FONT}">'
        f"<title>{esc(r['name'])}</title><desc>{esc(r.get('desc') or '')}</desc>"
        f'<rect x=".5" y=".5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="10" fill="{C["base"]}" stroke="{C["surface0"]}"/>'
        f'<rect x="1" y="1" width="4" height="{CARD_H - 2}" rx="2" fill="{col}" opacity=".8"/>'
        f'<text x="20" y="34" font-size="15" font-weight="600" fill="{C["mauve"]}"><tspan fill="{C["overlay0"]}" font-weight="400">~/</tspan>{esc(r["name"])}</text>'
        f'{txt(CARD_W - 20, 33, "↗", C["overlay0"], 14, anchor="end")}'
        f'{desc}{"".join(meta)}</svg>'
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


def bar_row(x, y, label, color, value_px, track, value_text, i):
    return (
        f'<g opacity="0">{fade(0.5 + i * 0.1)}'
        f'{txt(x, y, label, C["subtext0"], 12)}'
        f'<rect x="{x + 76}" y="{y - 11}" width="{track}" height="12" rx="3" fill="{C["surface0"]}"/>'
        f'<rect x="{x + 76}" y="{y - 11}" width="0" height="12" rx="3" fill="{color}">'
        f'<animate attributeName="width" from="0" to="{value_px:.0f}" dur="1.2s" begin="{0.6 + i * 0.12:.2f}s" fill="freeze"/></rect>'
        f'{txt(x + 76 + track + 10, y, value_text, C["text"], 12)}</g>'
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


def koi(y, path, d):
    out = [prompt(y, "git koi", "# a pixel koi that lives off my GitHub activity", base=0.6)]
    top, bh = y + 22, 230
    out.append(inset(PAD, top, IW, bh, C["crust"]))
    if path and os.path.exists(path):
        x0, y0, x1, y1 = gif_bbox(path) or (0, 0, 512, 512)
        bw_, bh_ = x1 - x0, y1 - y0
        s = min((IW - 40) / bw_, (bh - 24) / bh_)
        dw, dh = bw_ * s, bh_ * s
        b64 = base64.b64encode(open(path, "rb").read()).decode()
        out.append(
            f'<svg x="{PAD + (IW - dw) / 2:.1f}" y="{top + (bh - dh) / 2:.1f}" width="{dw:.1f}" height="{dh:.1f}" viewBox="{x0} {y0} {bw_} {bh_}">'
            f'<image href="data:image/gif;base64,{b64}" width="{gif_size(path)[0]}" height="{gif_size(path)[1]}" style="image-rendering:pixelated"/></svg>'
        )
    else:
        out.append(txt(W / 2, top + bh / 2 + 4, "the koi appears after the first workflow run", C["overlay0"], 12, anchor="middle"))

    # legend: what the fish actually encodes
    ly = top + bh + 34
    key = lambda yy, k: txt(PAD, yy, k, C["blue"])  # noqa: E731
    vx = PAD + 10 * CWX
    rows = []
    k = d.get("koi")
    colors = (k or {}).get("colors") or {}
    langs = d["langs"].most_common(5)
    total_l = sum(n for _, n in d["langs"].items()) or 1
    x, sw = vx, []
    for lang, n in langs:
        label = f"{lang.lower()} {pct(n, total_l):.0f}%"
        sw.append(f'<rect x="{x:.1f}" y="{ly - 10}" width="11" height="11" rx="2" fill="{colors.get(lang) or GH_COLORS.get(lang, C["overlay0"])}"/>'
                  + txt(round(x + 17, 1), ly, label, C["text"], 12))
        x += 17 + len(label) * 7.2 + 16
    rows.append(key(ly, "colors") + "".join(sw))
    rows.append(txt(vx, ly + 20, "# its pigments are my languages, by share of repos", C["overlay0"], 12))

    ly2 = ly + 52
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
        rows.append(txt(vx, ly3 + 20, "# weeks with at least one contribution add markings", C["overlay0"], 12))
        ly4 = ly3 + 52
        rows.append(key(ly4, "mood") + txt(vx, ly4, f"{k.get('yesterday', 0)} contributions yesterday · {k['week']} this week", C["text"], 12))
        rows.append(txt(vx, ly4 + 20, "# the day that just ended sets how it swims; redrawn every night", C["overlay0"], 12))
        end = ly4 + 20
    else:
        rows.append(key(ly2, "size") + txt(vx, ly2, "grows with my total contributions", C["text"], 12))
        ly3 = ly2 + 28
        rows.append(key(ly3, "streak") + txt(vx, ly3, "weekly streaks add markings", C["text"], 12))
        ly4 = ly3 + 28
        rows.append(key(ly4, "mood") + txt(vx, ly4, "the last few days set how it swims", C["text"], 12))
        end = ly4
    out.append(f'<g opacity="0">{"".join(rows)}{fade(0.7)}</g>')
    return "".join(out), end


def gif_size(path):
    b = open(path, "rb").read(10)
    return struct.unpack("<HH", b[6:10])


def footer(y):
    s = "$ exit  # bye-bye!"
    line = (f'<text x="{PAD}" y="{y}" font-size="13" fill="{C["text"]}" xml:space="preserve"><tspan fill="{C["green"]}">$</tspan> exit  '
            f'<tspan fill="{C["overlay0"]}"># bye-bye!</tspan></text>')
    return line + blink(PAD + len(s) * CWX + 6, y), y


def activity_svg(d, snake_path=None, koi_path=None):
    parts = []
    y = 70
    for fn in (lambda y: stats(y, d), lambda y: insights(y, d), lambda y: snake(y, snake_path),
               lambda y: koi(y, koi_path, d), footer):
        s, end = fn(y)
        parts.append(s)
        y = end + GAP
    h = round(y - GAP + 40)
    return window("activity — zsh", "GitHub stats, commit rhythm, languages, the contribution snake and a pixel koi with a legend.",
                  h, "".join(parts))


def build_all(d, snake_path=None, koi_path=None):
    files = {"hero.svg": hero_svg(), "repos-header.svg": repos_header_svg(len(d["featured"])),
             "activity.svg": activity_svg(d, snake_path, koi_path)}
    for r in d["featured"]:
        files[f"repos/{r['name']}.svg"] = repo_card_svg(r)
    return files
