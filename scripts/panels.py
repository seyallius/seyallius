"""Builds the profile's separate SVG panels (stdlib only).

hero.svg      terminal window: typing intro + the pixel-art desk scene
skills.svg    animated stack.toml
stats.svg     five number tiles
insights.svg  commit rhythm and languages
snake.svg     contribution snake in a card
koi.svg       git-koi in a card

The README (Markdown, so links work) holds everything else.
"""
import base64
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import C, CW, FONT, esc, kt  # noqa: E402

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
W, PAD = 680, 32
CWX = 13 * CW

HERO_LINES = [
    # (segments, font size, baseline y, weight, seconds per char)
    ([("seyallius@github", C["green"]), (":", C["overlay0"]), ("~", C["blue"]), (" $ whoami", C["text"])], 13, 76, 400, 0.07),
    ([("Helleo~", C["mauve"])], 32, 124, 500, 0.14),
    ([("Systems and backend engineer · Go and Rust", C["text"])], 14, 158, 400, 0.05),
    ([("Building tools that make other developers' lives easier", C["subtext0"])], 13, 184, 400, 0.04),
    ([("# Benkyou wa tanoshii!", C["overlay0"])], 12, 210, 400, 0.06),
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


def fade(base):
    return f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{base:.2f}s" fill="freeze"/>'


def txt(x, y, s, fill, size=13, weight=400, anchor=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    w = f' font-weight="{weight}"' if weight != 400 else ""
    return f'<text x="{x}" y="{y}" font-size="{size}"{w}{a} fill="{fill}">{esc(s)}</text>'


def pct(n, total):
    return 0 if not total else n / total * 100


def card(h, title, desc, body, defs=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" role="img" font-family="{FONT}">'
        f"<title>{esc(title)}</title><desc>{esc(desc)}</desc><defs>{defs}</defs>"
        f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="10" fill="{C["base"]}" stroke="{C["surface0"]}"/>'
        f"{body}</svg>"
    )


# ----------------------------------------------------------------------------
def hero_svg():
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

    # desk scene (nested, title bar stripped, ids prefixed)
    src = open(os.path.join(ASSETS, "desk-scene.svg"), encoding="utf-8").read()
    inner = src[src.index("<defs>"): src.rindex("</svg>")]
    inner = re.sub(r'<rect width="680" height="28" fill="#181825"/>\n?', "", inner)
    inner = re.sub(r'<circle cx="18" cy="14"[^\n]*\n', "", inner)
    inner = re.sub(r'<text x="340" y="18"[^\n]*desk\.svg</text>\n?', "", inner)
    inner = inner.replace('<rect width="680" height="320" rx="8"/>', '<rect width="680" height="320"/>')
    for i in ("pc", "wc", "sc", "wp", "fl", "kp", "rp", "code"):
        inner = (inner.replace(f'id="{i}"', f'id="d-{i}"').replace(f"url(#{i})", f"url(#d-{i})")
                 .replace(f'href="#{i}"', f'href="#d-{i}"'))
    py = HERO_LINES[-1][2] + 44          # prompt baseline
    sy, sh = py + 18, 292                # scene top / height
    total = sy + sh
    prompt = (f'<text x="{PAD}" y="{py}" font-size="13" fill="{C["text"]}" opacity="0" xml:space="preserve">'
              f'<tspan fill="{C["green"]}">$</tspan> ./sunrise.sh <tspan fill="{C["overlay0"]}"># 04:00 to 07:00</tspan>{fade(0.4)}</text>')
    scene = f'<svg x="0" y="{sy}" width="{W}" height="{sh}" viewBox="0 28 {W} {sh}">{inner}</svg>'
    chrome = (
        f'<rect width="{W}" height="28" fill="{C["mantle"]}"/>'
        f'<circle cx="18" cy="14" r="5" fill="{C["red"]}"/><circle cx="36" cy="14" r="5" fill="{C["yellow"]}"/>'
        f'<circle cx="54" cy="14" r="5" fill="{C["green"]}"/>'
        f'<text x="{W / 2:g}" y="18" text-anchor="middle" font-size="12" fill="{C["overlay0"]}">seyallius — zsh</text>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {total}" width="{W}" height="{total}" role="img" font-family="{FONT}">'
        f"<title>seyallius</title><desc>Terminal window: typing intro, then a pixel-art animation of a developer coding from 4 AM until sunrise and leaving for the day.</desc>"
        f'<defs><clipPath id="win"><rect width="{W}" height="{total}" rx="10"/></clipPath>{"".join(clips)}</defs>'
        f'<g clip-path="url(#win)"><rect width="{W}" height="{total}" fill="{C["base"]}"/>{chrome}'
        f'{"".join(texts)}{cursor}{prompt}{scene}</g>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{total - 1}" rx="10" fill="none" stroke="{C["surface0"]}"/></svg>'
    )


def skills_svg():
    toks, t = [], 0.5
    for r, (key, items) in enumerate(SKILLS):
        yy = 52 + r * 30
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
    body = []
    for x, yy, s, col, ta in toks:
        body.append(
            f'<text x="{round(x, 1)}" y="{yy}" font-size="13" fill="{col}" opacity="0" xml:space="preserve" '
            f'textLength="{round(len(s) * CWX, 1)}" lengthAdjust="spacing">{esc(s)}'
            f'<animate attributeName="opacity" calcMode="discrete" dur="{D}s" repeatCount="indefinite" '
            f'keyTimes="0;{ta / D:.4f};1" values="0;1;1"/></text>'
        )
    h = 52 + (len(SKILLS) - 1) * 30 + 36
    return card(h, "Tech stack", "Languages, frameworks, infrastructure and data stores.", "".join(body))


def stats_svg(d):
    tiles = [("repos", d["repos"], C["mauve"]), ("stars", d["stars"], C["yellow"]),
             ("followers", d["user"].get("followers", 0), C["blue"]),
             ("commits", d["commits"], C["peach"]), ("pull requests", d["prs"], C["green"])]
    tw, gap, top, th = 116, 13, 28, 76
    body = []
    for i, (label, val, col) in enumerate(tiles):
        x = 24 + i * (tw + gap)
        v = "n/a" if val is None else f"{val:,}"
        body.append(
            f'<g opacity="0"><rect x="{x}" y="{top}" width="{tw}" height="{th}" rx="8" fill="{C["mantle"]}" stroke="{C["surface0"]}"/>'
            f'<text x="{x + tw / 2}" y="{top + 38}" text-anchor="middle" font-size="24" font-weight="500" fill="{col}">{v}</text>'
            f'<text x="{x + tw / 2}" y="{top + 59}" text-anchor="middle" font-size="12" fill="{C["subtext0"]}">{esc(label)}</text>{fade(0.2 + i * 0.12)}</g>'
        )
    return card(top * 2 + th, "GitHub stats", "Repositories, stars, followers, commits and pull requests.", "".join(body))


def bar_row(x, y, label, color, value_px, track, value_text, i):
    return (
        f'<g opacity="0">{fade(0.2 + i * 0.1)}'
        f'{txt(x, y, label, C["subtext0"], 12)}'
        f'<rect x="{x + 78}" y="{y - 11}" width="{track}" height="12" rx="3" fill="{C["surface0"]}"/>'
        f'<rect x="{x + 78}" y="{y - 11}" width="0" height="12" rx="3" fill="{color}">'
        f'<animate attributeName="width" from="0" to="{value_px:.0f}" dur="1.2s" begin="{0.4 + i * 0.12:.2f}s" fill="freeze"/></rect>'
        f'{txt(x + 78 + track + 10, y, value_text, C["text"], 12)}</g>'
    )


def insights_svg(d):
    total, track = d["commits"], 128
    buckets = [
        ("morning", C["yellow"], sum(d["hours"][h] for h in range(6, 12))),
        ("daytime", C["peach"], sum(d["hours"][h] for h in range(12, 18))),
        ("evening", C["mauve"], sum(d["hours"][h] for h in range(18, 24))),
        ("night", C["blue"], sum(d["hours"][h] for h in range(0, 6))),
    ]
    top = max((b[2] for b in buckets), default=1) or 1
    xl, xr, y0, step = 32, 372, 76, 32
    body = [
        txt(xl, 44, "WHEN I COMMIT", C["overlay0"], 11, 500), txt(xr, 44, "WHAT I BUILD IN", C["overlay0"], 11, 500),
        f'<rect x="338" y="28" width="1" height="{20 + 4 * step + 36}" fill="{C["surface0"]}"/>',
    ]
    for i, (label, col, n) in enumerate(buckets):
        body.append(bar_row(xl, y0 + i * step, label, col, track * n / top, track, f"{pct(n, total):.1f}%", i))
    langs = d["langs"].most_common(4)
    ltop = max((n for _, n in langs), default=1)
    for i, (lang, n) in enumerate(langs):
        body.append(bar_row(xr, y0 + i * step, lang.lower(), LANG_COLORS.get(lang, C["overlay0"]),
                            track * n / ltop, track, f"{n} repos" if n != 1 else "1 repo", i))
    peak = max(range(7), key=lambda k: d["days"][k]) if d["days"] else 0
    fy = y0 + 4 * step + 8
    body.append(txt(xl, fy, f"# peak day: {DAYS[peak].lower()}", C["overlay0"], 12))
    body.append(txt(xr, fy, f"# across {d['repos']} repositories", C["overlay0"], 12))
    return card(fy + 32, "Productivity insights", "Commit rhythm by time of day and repositories by language.", "".join(body))


# ----------------------------------------------------------------------------
def snake_svg(path):
    if not (path and os.path.exists(path)):
        return placeholder("The snake appears after the first workflow run.")
    raw = open(path, encoding="utf-8").read()
    raw = re.sub(r"^\s*<\?xml[^>]*\?>", "", raw)
    m = re.search(r"<svg\b[^>]*>", raw)
    minx, miny, vw, vh = [float(v) for v in re.search(r'viewBox="([\d.\s-]+)"', m.group(0)).group(1).split()]
    inner = raw[m.end(): raw.rindex("</svg>")]
    aw = W - 48
    ah = aw * vh / vw
    h = round(ah + 48)
    body = f'<svg x="24" y="24" width="{aw}" height="{ah:.1f}" viewBox="{minx} {miny} {vw} {vh}">{inner}</svg>'
    return card(h, "Contribution snake", "A snake eating my contribution graph.", body)


def koi_svg(path):
    if not (path and os.path.exists(path)):
        return placeholder("The koi appears after the first workflow run.")
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    body = (f'<image href="data:image/gif;base64,{b64}" x="24" y="16" width="{W - 48}" height="168" '
            'preserveAspectRatio="xMidYMid meet" style="image-rendering:pixelated"/>')
    return card(200, "Pixel koi", "A koi fish that grows with my commits.", body)


def placeholder(msg):
    return card(120, "Placeholder", msg, txt(W / 2, 64, msg, C["overlay0"], 12, anchor="middle"))


def build_all(d, snake=None, koi=None):
    return {
        "hero.svg": hero_svg(), "skills.svg": skills_svg(), "stats.svg": stats_svg(d),
        "insights.svg": insights_svg(d), "snake.svg": snake_svg(snake), "koi.svg": koi_svg(koi),
    }
