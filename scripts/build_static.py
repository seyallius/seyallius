#!/usr/bin/env python3
"""Builds the hand-authored SVGs in assets/: hero (typing), about, skills, footer.

Edit the CONTENT section below, run `python scripts/build_static.py`, commit the
result to main. These files never change on their own, so no workflow needs them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import C, CW, esc, svg_open, panel_open, panel_close, prompt_line, blink_cursor, kt  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

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


def write(name, body):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print("wrote", os.path.relpath(path), f"({len(body) // 1024 or 1} KB)")


# ----------------------------------------------------------------------------
def hero():
    W, H, X0 = 680, 180, 24
    t = 0.6
    plan = []
    for segs, size, y, weight, dtc in HERO_LINES:
        n = sum(len(s) for s, _ in segs)
        plan.append(dict(segs=segs, size=size, y=y, weight=weight, dt=dtc, n=n, start=t))
        t += n * dtc + 0.5
    D = round(t + 5.0, 2)

    clips, texts, cur = [], [], []
    for i, L in enumerate(plan):
        cw = CW * L["size"]
        times = [0.0] + [(L["start"] + k * L["dt"]) / D for k in range(L["n"])] + [1.0]
        widths = [0.0] + [round((k + 1) * cw, 1) for k in range(L["n"])] + [round(L["n"] * cw, 1)]
        clips.append(
            f'<clipPath id="c{i}"><rect x="{X0}" y="{L["y"] - L["size"]}" width="0" height="{round(L["size"] * 1.5)}">'
            f'<animate attributeName="width" calcMode="discrete" dur="{D}s" repeatCount="indefinite" '
            f'keyTimes="{kt(times)}" values="{";".join(str(w) for w in widths)}"/></rect></clipPath>'
        )
        tsp = "".join(f'<tspan fill="{col}">{esc(s)}</tspan>' for s, col in L["segs"])
        wt = f' font-weight="{L["weight"]}"' if L["weight"] != 400 else ""
        texts.append(
            f'<text x="{X0}" y="{L["y"]}" font-size="{L["size"]}"{wt} xml:space="preserve" '
            f'textLength="{round(L["n"] * cw, 1)}" lengthAdjust="spacing" clip-path="url(#c{i})">{tsp}</text>'
        )

    # one cursor that follows the typing across lines
    ev = []
    first = plan[0]
    ev.append((0.0, X0, first["y"] - round(first["size"] * 0.8), round(first["size"] * 0.95), round(CW * first["size"], 1)))
    for L in plan:
        cw = CW * L["size"]
        top, h, w = L["y"] - round(L["size"] * 0.8), round(L["size"] * 0.95), round(cw, 1)
        for k in range(L["n"]):
            ev.append(((L["start"] + k * L["dt"]) / D, round(X0 + (k + 1) * cw, 1), top, h, w))
    keys = kt([e[0] for e in ev] + [1.0])
    def vals(idx):
        return ";".join(str(e[idx]) for e in ev) + ";" + str(ev[-1][idx])
    cursor = (
        f'<rect x="{X0}" y="{ev[0][2]}" width="{ev[0][4]}" height="{ev[0][3]}" fill="{C["mauve"]}">'
        + "".join(
            f'<animate attributeName="{a}" calcMode="discrete" dur="{D}s" repeatCount="indefinite" keyTimes="{keys}" values="{vals(i)}"/>'
            for a, i in (("x", 1), ("y", 2), ("height", 3), ("width", 4))
        )
        + '<animate attributeName="opacity" values="1;0" keyTimes="0;.5" calcMode="discrete" dur="1.1s" repeatCount="indefinite"/></rect>'
    )

    body = (
        svg_open(W, H, "seyallius - Helleo~", "Terminal window typing: Helleo~, systems and backend engineer, Go and Rust.")
        + f"<defs>{''.join(clips)}</defs>"
        + panel_open(W, H, "seyallius — zsh")
        + "".join(texts)
        + cursor
        + panel_close()
        + "</svg>"
    )
    write("hero.svg", body)


def about():
    W = 680
    rows = len(ABOUT)
    H = 28 + 30 + rows * 22 + 22
    parts = [svg_open(W, H, "about.md", "About: " + " ".join(f"{k}: {v}" for k, v in ABOUT)), panel_open(W, H, "about.md")]
    parts.append(prompt_line(24, 58, "cat about.md"))
    col = 24 + 10 * 7.8 + 8
    for i, (k, v) in enumerate(ABOUT):
        y = 88 + i * 22
        parts.append(
            f'<g opacity="0"><text x="24" y="{y}" font-size="13" fill="{C["blue"]}">{esc(k)}</text>'
            f'<text x="{col:g}" y="{y}" font-size="13" fill="{C["text"]}">{esc(v)}</text>'
            f'<animate attributeName="opacity" from="0" to="1" dur="0.4s" begin="{0.3 + i * 0.25:g}s" fill="freeze"/></g>'
        )
    parts += [panel_close(), "</svg>"]
    write("about.svg", "".join(parts))


def skills():
    W, CWX = 680, 13 * CW
    H = 28 + 30 + len(SKILLS) * 24 + 30
    # timeline
    toks = []  # (x, y, string, color, appear_time)
    t = 0.5
    for r, (key, items) in enumerate(SKILLS):
        y = 88 + r * 24
        toks.append((24, y, key, C["blue"], t))
        x = 24 + 12 * CWX
        toks.append((x, y, "= [", C["overlay0"], t + 0.1))
        x += 3 * CWX
        for j, it in enumerate(items):
            t += 0.18
            s = f'"{it}"'
            toks.append((x, y, s, C["green"], t))
            x += len(s) * CWX
            if j < len(items) - 1:
                toks.append((x, y, ", ", C["overlay0"], t))
                x += 2 * CWX
        toks.append((x, y, "]", C["overlay0"], t))
        t += 0.3
    D = round(t + 6.0, 2)
    parts = [svg_open(W, H, "stack.toml", "Tech stack: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in SKILLS)), panel_open(W, H, "stack.toml")]
    parts.append(prompt_line(24, 58, "cat stack.toml"))
    for x, y, s, col, ta in toks:
        parts.append(
            f'<text x="{round(x, 1)}" y="{y}" font-size="13" fill="{col}" opacity="0" xml:space="preserve" '
            f'textLength="{round(len(s) * CWX, 1)}" lengthAdjust="spacing">{esc(s)}'
            f'<animate attributeName="opacity" calcMode="discrete" dur="{D}s" repeatCount="indefinite" '
            f'keyTimes="0;{ta / D:.4f};1" values="0;1;1"/></text>'
        )
    end_y = 88 + len(SKILLS) * 24 - 4
    parts.append(f'<text x="24" y="{end_y}" font-size="13" fill="{C["green"]}">$</text>')
    parts.append(blink_cursor(38, end_y - 12, 8, 15, C["mauve"]))
    parts += [panel_close(), "</svg>"]
    write("skills.svg", "".join(parts))


def footer():
    W, H = 680, 56
    s = "$ exit # bye-bye!"
    x_cur = round(24 + len(s) * 7.8 + 6, 1)
    parts = [
        svg_open(W, H, "bye-bye!", "Closing terminal line: exit, bye-bye!"),
        panel_open(W, H, "", bar=False),
        f'<text x="24" y="34" font-size="13" fill="{C["text"]}"><tspan fill="{C["green"]}">$</tspan> exit <tspan fill="{C["overlay0"]}"># bye-bye!</tspan></text>',
        blink_cursor(x_cur, 22, 9, 16),
        panel_close(),
        "</svg>",
    ]
    write("footer.svg", "".join(parts))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    hero()
    about()
    skills()
    footer()
