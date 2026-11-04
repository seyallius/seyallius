"""Shared Catppuccin Mocha helpers for the profile SVGs (stdlib only)."""
import html

C = {
    "base": "#1e1e2e", "mantle": "#181825", "crust": "#11111b",
    "surface0": "#313244", "surface1": "#45475a", "surface2": "#585b70",
    "overlay0": "#6c7086", "subtext0": "#a6adc8", "text": "#cdd6f4",
    "lavender": "#b4befe", "blue": "#89b4fa", "sapphire": "#74c7ec",
    "teal": "#94e2d5", "green": "#a6e3a1", "yellow": "#f9e2af",
    "peach": "#fab387", "red": "#f38ba8", "mauve": "#cba6f7", "pink": "#f5c2e7",
}
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
CW = 0.6  # monospace glyph width as a fraction of font size


def esc(s):
    return html.escape(str(s), quote=True)


def svg_open(w, h, title, desc=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" font-family="{FONT}">'
        f"<title>{esc(title)}</title><desc>{esc(desc or title)}</desc>"
    )


def panel_open(w, h, title, x=0, y=0, bar=True):
    """Opens a <g> with a terminal window background. Close with panel_close()."""
    s = (
        f'<g transform="translate({x},{y})">'
        f'<rect width="{w}" height="{h}" rx="8" fill="{C["base"]}"/>'
    )
    if bar:
        s += (
            f'<rect width="{w}" height="28" rx="8" fill="{C["mantle"]}"/>'
            f'<rect y="14" width="{w}" height="14" fill="{C["mantle"]}"/>'
            f'<circle cx="18" cy="14" r="5" fill="{C["red"]}"/>'
            f'<circle cx="36" cy="14" r="5" fill="{C["yellow"]}"/>'
            f'<circle cx="54" cy="14" r="5" fill="{C["green"]}"/>'
            f'<text x="{w / 2:g}" y="18" text-anchor="middle" font-size="12" '
            f'fill="{C["overlay0"]}">{esc(title)}</text>'
        )
    return s


def panel_close():
    return "</g>"


def text(x, y, s, fill, size=13, weight=400, anchor=None, extra=""):
    a = f' text-anchor="{anchor}"' if anchor else ""
    w = f' font-weight="{weight}"' if weight != 400 else ""
    return f'<text x="{x}" y="{y}" font-size="{size}"{w}{a} fill="{fill}" {extra}>{esc(s)}</text>'


def prompt_line(x, y, cmd, comment=""):
    s = (
        f'<text x="{x}" y="{y}" font-size="13" fill="{C["text"]}">'
        f'<tspan fill="{C["green"]}">$</tspan> {esc(cmd)}'
    )
    if comment:
        s += f' <tspan fill="{C["overlay0"]}">{esc(comment)}</tspan>'
    return s + "</text>"


def blink_cursor(x, y, w, h, fill=None):
    fill = fill or C["mauve"]
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}">'
        '<animate attributeName="opacity" values="1;0" keyTimes="0;.5" '
        'calcMode="discrete" dur="1.1s" repeatCount="indefinite"/></rect>'
    )


def kt(values):
    """Format a keyTimes list."""
    return ";".join(f"{v:.4f}".rstrip("0").rstrip(".") if v not in (0, 1) else str(int(v)) for v in values)
