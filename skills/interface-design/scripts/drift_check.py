#!/usr/bin/env python3
"""Catch design drift: literal style values that bypass the design tokens.

  drift_check.py diff [--base REF] [--staged] [--tailwind-palette] [--json] [--warn-only]
      Scan only the lines this change ADDS (git diff vs REF, default HEAD, plus untracked
      files). Every finding is a value that should come from a token, or a new token that
      should live in the token files. Exit 1 if anything is found, so it works as a hook.
      --base origin/main compares against the merge-base, for reviewing a whole branch.

  drift_check.py inventory [PATH] [--grid 4] [--json]
      Measure the values actually in use across the codebase: distinct colors (with
      near-duplicate clusters), font sizes, radii, spacing values off the grid. Use it to
      bootstrap DESIGN.md and to see how far an app has already drifted.

Token files (where literals belong) are skipped. Defaults cover common names; add your own
in .design/drift.json:  {"token_files": ["src/styles/tokens.css"], "ignore": ["src/legacy/**"]}
Silence a deliberate exception by putting  drift-ok: <reason>  in a comment on that line.

Covers CSS/SCSS/Less, Tailwind classes, JS/TS/JSX/TSX style objects, Vue/Svelte/Astro/HTML,
SwiftUI/UIKit, Jetpack Compose and Flutter. It is a heuristic linter: expect a few false
positives (an anchor like href="#abc"), and treat every hit as a question, not a verdict.
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

WEB = {".css", ".scss", ".sass", ".less", ".styl", ".pcss", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
       ".vue", ".svelte", ".astro", ".html", ".htm", ".mdx"}
CSSY = {".css", ".scss", ".sass", ".less", ".styl", ".pcss", ".vue", ".svelte", ".astro", ".html", ".htm"}
JSX = {".tsx", ".jsx", ".js", ".ts", ".mdx"}
SWIFT = {".swift"}
KOTLIN = {".kt", ".kts"}
DART = {".dart"}
ALL = WEB | SWIFT | KOTLIN | DART

DEFAULT_TOKEN_GLOBS = [
    "**/tokens.*", "**/*.tokens.*", "**/*-tokens.*", "**/design-tokens/**", "**/tokens/**",
    "**/theme.*", "**/themes/**", "**/theme/**", "tailwind.config.*", "**/tailwind.config.*",
    "**/Theme*.swift", "**/DesignSystem/**", "**/design-system/**", "**/ui/theme/**",
    "**/globals.css", "**/global.css", "**/*variables.*", "DESIGN.md", "**/*.stories.*",
]
DEFAULT_IGNORE = [
    "**/node_modules/**", "**/dist/**", "**/build/**", "**/.next/**", "**/out/**", "**/coverage/**",
    "**/vendor/**", "**/Pods/**", "**/DerivedData/**", "**/*.min.*", "**/*.map", "**/*.lock",
    "**/__tests__/**", "**/*.test.*", "**/*.spec.*", "**/__snapshots__/**", "**/.design/**",
]

HEX = re.compile(r"(?<![\w.&/])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b")
COLOR_FN = re.compile(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(\s*[\d.]")
TW_ARB = re.compile(r"(?<![\w-])(?:[a-z][\w-]*:)*!?-?[a-z][a-z0-9-]*-\[(?!var\(|--)[^\]\s'\"`]+\](?!:)")
TW_PALETTE = re.compile(
    r"(?<![\w-])(?:[a-z-]+:)*(?:bg|text|border|ring|fill|stroke|from|via|to|outline|shadow|decoration|divide|"
    r"placeholder|accent|caret)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|"
    r"teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b")
CSS_DECL = re.compile(
    r"(?<![\w-])(margin|padding|gap|row-gap|column-gap|top|right|bottom|left|inset|width|height|min-width|"
    r"max-width|min-height|max-height|font-size|line-height|letter-spacing|border-radius|border-width|"
    r"outline-offset)(?:-[a-z-]+)?\s*:\s*([^;{}]+)")
LENGTH = re.compile(r"(?<![\w.#-])(\d*\.?\d+)(px|rem|em)\b")
CSS_VAR_DEF = re.compile(r"^\s*--[\w-]+\s*:")
Z_INDEX = re.compile(r"z-index\s*:\s*-?\d{2,}|\bzIndex\s*:\s*-?\d{2,}")
SHADOW = re.compile(r"box-shadow\s*:\s*(?![^;]*var\()(?!none|inherit|initial|unset)[^;]*\d")
MOTION = re.compile(r"(?:transition|animation)(?:-duration|-timing-function|-delay)?\s*:\s*[^;]*(?:\d+m?s\b|cubic-bezier\()"
                    r"|cubic-bezier\(")
IMPORTANT = re.compile(r"!important")
HTML_STYLE = re.compile(r"\bstyle=\"[^\"]*\d")
JS_STYLE_KEYS = re.compile(r"\b(?:fontSize|lineHeight|letterSpacing|borderRadius|fontWeight)\s*:\s*['\"]?\d+(?:\.\d+)?[a-z%]*")
JS_LAYOUT_KEYS = re.compile(r"\b(?:margin|padding|gap|top|left|right|bottom|width|height)(?:[A-Z]\w*)?\s*:\s*['\"]?\d+(?:\.\d+)?[a-z%]*")

SWIFT_RULES = [
    ("swift-color", re.compile(r"\b(?:UI|NS)?Color\(\s*(?:red|hue|white|hex|displayP3|#)[^)]*\)?|Color\(\s*\.sRGB[^)]*\)?")),
    ("swift-font-size", re.compile(r"\.system\(\s*size:\s*\d+(?:\.\d+)?|\.custom\([^)]*size:\s*\d+(?:\.\d+)?")),
    ("swift-spacing", re.compile(r"\.padding\(\s*(?:\.\w+\s*,\s*)?\d+(?:\.\d+)?|\b(?:Lazy)?[VH]Stack\([^)]*spacing:\s*\d+(?:\.\d+)?"
                                 r"|\.cornerRadius\(\s*\d+(?:\.\d+)?|RoundedRectangle\(\s*cornerRadius:\s*\d+(?:\.\d+)?")),
    ("swift-shadow", re.compile(r"\.shadow\([^)]*radius:\s*\d+(?:\.\d+)?")),
    ("swift-motion", re.compile(r"\.(?:easeIn|easeOut|easeInOut|linear|spring)\([^)]*\d")),
    ("swift-opacity", re.compile(r"\.opacity\(\s*0?\.\d")),
]
KOTLIN_RULES = [
    ("compose-dimension", re.compile(r"(?<![\w.])(?:[2-9]|\d{2,})(?:\.\d+)?\.(?:dp|sp)\b")),
    ("compose-color", re.compile(r"\bColor\(\s*0x[0-9A-Fa-f]{6,8}")),
]
DART_RULES = [
    ("flutter-color", re.compile(r"\bColor\(\s*0x[0-9A-Fa-f]{6,8}|Color\.fromRGBO\(")),
    ("flutter-spacing", re.compile(r"EdgeInsets\.\w+\([^)]*\d|BorderRadius\.circular\(\s*\d|SizedBox\(\s*(?:width|height):\s*\d")),
    ("flutter-font-size", re.compile(r"fontSize:\s*\d")),
]


def load_cfg(root):
    p = root / ".design" / "drift.json"
    cfg = json.loads(p.read_text()) if p.exists() else {}
    return DEFAULT_TOKEN_GLOBS + cfg.get("token_files", []), DEFAULT_IGNORE + cfg.get("ignore", [])


def matches(path, globs):
    s = path.replace("\\", "/")
    for g in globs:
        if fnmatch.fnmatch(s, g) or (g.startswith("**/") and fnmatch.fnmatch(s, g[3:])):
            return True
    return False


def css_lengths(value):
    """Literal lengths in a CSS declaration value that should be tokens (0 and 1px hairlines are fine)."""
    if "var(" in value and not LENGTH.search(re.sub(r"var\([^)]*\)", "", value)):
        return []
    hits = []
    for num, unit in LENGTH.findall(re.sub(r"var\([^)]*\)", "", value)):
        n = float(num)
        if n == 0 or (unit == "px" and n <= 1):
            continue
        hits.append(f"{num}{unit}")
    return hits


COMMENT_LINE = re.compile(r"^\s*(?://|/\*|\*|<!--|#\s)")
INLINE_COMMENT = re.compile(r"/\*.*?\*/|(?<![:\w])//.*$|<!--.*?-->")
AT_RULE = re.compile(r"^\s*@(?:media|container|supports|custom-media)\b")


def scan_line(path, text, tw_palette=False):
    """Return [(kind, snippet)] for one line of source."""
    if "drift-ok" in text or COMMENT_LINE.match(text) or AT_RULE.match(text):
        return []
    text = INLINE_COMMENT.sub("", text)
    ext = Path(path).suffix.lower()
    out = []
    if ext in WEB:
        if CSS_VAR_DEF.match(text) and (HEX.search(text) or COLOR_FN.search(text) or LENGTH.search(text)):
            return [("token-defined-outside-token-files", text.strip()[:120])]
        for m in HEX.finditer(text):
            out.append(("color-literal", m.group(0)))
        for m in COLOR_FN.finditer(text):
            out.append(("color-literal", text[m.start():m.start() + 28].split(")")[0] + ")"))
        for m in TW_ARB.finditer(text):
            out.append(("tailwind-arbitrary-value", m.group(0)))
        if tw_palette:
            for m in TW_PALETTE.finditer(text):
                out.append(("tailwind-raw-palette", m.group(0)))
        if ext in CSSY or "css`" in text or "styled." in text:
            for prop, value in CSS_DECL.findall(text):
                for lit in css_lengths(value):
                    out.append(("length-literal", f"{prop}: {lit}"))
        for rx, kind in ((Z_INDEX, "z-index-literal"), (SHADOW, "shadow-literal"), (MOTION, "motion-literal"),
                         (IMPORTANT, "important")):
            m = rx.search(text)
            if m:
                out.append((kind, m.group(0)[:80]))
        if ext in JSX:
            for m in JS_STYLE_KEYS.finditer(text):
                out.append(("style-object-literal", m.group(0)))
            if "style" in text:
                for m in JS_LAYOUT_KEYS.finditer(text):
                    out.append(("style-object-literal", m.group(0)))
        elif HTML_STYLE.search(text):
            out.append(("inline-style", HTML_STYLE.search(text).group(0)[:80]))
    rules = SWIFT_RULES if ext in SWIFT else KOTLIN_RULES if ext in KOTLIN else DART_RULES if ext in DART else []
    for kind, rx in rules:
        for m in rx.finditer(text):
            out.append((kind, m.group(0)[:80]))
    return out


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


def added_lines(root, base, staged):
    if staged:
        diff = git(root, "diff", "--cached", "--no-color", "-U0")
    else:
        ref = base
        if base != "HEAD":
            ref = git(root, "merge-base", base, "HEAD").strip()
        diff = git(root, "diff", ref, "--no-color", "-U0")
    path, lineno = None, 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = None if line[4:] == "/dev/null" else line[6:] if line[4:].startswith("b/") else line[4:]
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
        elif line.startswith("+") and path:
            yield path, lineno, line[1:]
            lineno += 1
    if not staged:
        for path in git(root, "ls-files", "--others", "--exclude-standard").splitlines():
            p = root / path
            if p.suffix.lower() in ALL and p.is_file():
                for i, text in enumerate(p.read_text(errors="replace").splitlines(), 1):
                    yield path, i, text


def cmd_diff(args):
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    tokens, ignore = load_cfg(root)
    findings = []
    for path, n, text in added_lines(root, args.base, args.staged):
        if Path(path).suffix.lower() not in ALL or matches(path, ignore) or matches(path, tokens):
            continue
        for kind, snip in scan_line(path, text, args.tailwind_palette):
            findings.append({"file": path, "line": n, "kind": kind, "value": snip})
    if args.json:
        print(json.dumps({"findings": findings}, indent=2))
    elif not findings:
        print("drift check: clean (no literal style values in added lines)")
    else:
        by_kind = Counter(f["kind"] for f in findings)
        print(f"drift check: {len(findings)} finding(s) in added lines — "
              + ", ".join(f"{k} x{v}" for k, v in by_kind.most_common()))
        for f in findings:
            print(f"  {f['file']}:{f['line']}  {f['kind']}  {f['value']}")
        print("\nFor each: use the existing token, add a token to the token files (and DESIGN.md) if the system "
              "genuinely lacks one, or mark a deliberate exception with 'drift-ok: <reason>'.")
    sys.exit(0 if args.warn_only or not findings else 1)


# ---------- inventory ----------

def norm_hex(h):
    h = h.lstrip("#").lower()
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    return "#" + h[:6] + (f" a{h[6:8]}" if len(h) == 8 and h[6:8] != "ff" else "")


def rgb_of(h):
    h = h.lstrip("#")[:6]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def parse_rgb_fn(s):
    m = re.match(r"rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)", s)
    return "#%02x%02x%02x" % tuple(min(255, int(x)) for x in m.groups()) if m else None


def cluster_colors(counter, dist=12):
    cols = [c for c, _ in counter.most_common() if c.startswith("#") and " a" not in c]
    clusters, used = [], set()
    for c in cols:
        if c in used:
            continue
        group = [c]
        used.add(c)
        rc = rgb_of(c)
        for o in cols:
            if o not in used and sum((a - b) ** 2 for a, b in zip(rc, rgb_of(o))) ** 0.5 < dist:
                group.append(o)
                used.add(o)
        if len(group) > 1:
            clusters.append(group)
    return clusters


def cmd_inventory(args):
    start = Path(args.path or ".").resolve()
    try:
        root = Path(git(start, "rev-parse", "--show-toplevel").strip())
        files = [root / f for f in git(root, "ls-files", "--cached", "--others", "--exclude-standard").splitlines()]
        files = [f for f in files if str(f).startswith(str(start))]
    except Exception:
        root, files = start, [p for p in start.rglob("*") if p.is_file()]
    tokens, ignore = load_cfg(root)
    colors, sizes, radii, spacing, other = Counter(), Counter(), Counter(), Counter(), Counter()
    where = defaultdict(set)
    for f in files:
        rel = str(f.relative_to(root))
        if f.suffix.lower() not in ALL or matches(rel, ignore) or not f.is_file():
            continue
        in_tokens = matches(rel, tokens)
        for text in f.read_text(errors="replace").splitlines():
            if COMMENT_LINE.match(text):
                continue
            text = INLINE_COMMENT.sub("", text)
            for m in HEX.finditer(text):
                c = norm_hex(m.group(0))
                colors[c] += 1
                where[c].add("tokens" if in_tokens else rel)
            for m in COLOR_FN.finditer(text):
                raw = text[m.start():m.start() + 60].split(")")[0] + ")"
                c = parse_rgb_fn(raw) or re.sub(r"\s+", " ", raw.lower())
                colors[c] += 1
                where[c].add("tokens" if in_tokens else rel)
            for prop, value in CSS_DECL.findall(text):
                for num, unit in LENGTH.findall(value):
                    v = f"{float(num):g}{unit}"
                    if prop == "font-size":
                        sizes[v] += 1
                    elif prop == "border-radius":
                        radii[v] += 1
                    elif prop in ("line-height", "letter-spacing", "border-width", "outline-offset"):
                        continue
                    else:
                        spacing[v] += 1
            for m in re.finditer(r"text-\[(\d*\.?\d+(?:px|rem))\]", text):
                sizes[m.group(1)] += 1
            for m in re.finditer(r"rounded(?:-[a-z]+)?-\[(\d*\.?\d+(?:px|rem))\]", text):
                radii[m.group(1)] += 1
            for m in re.finditer(r"(?<![\w-])-?(?:p|m|gap|space-[xy]|[pm][xytrbl]|top|left|right|bottom|inset|w|h)-\[(\d*\.?\d+px)\]", text):
                spacing[m.group(1)] += 1
            for m in re.finditer(r"\bfontSize\s*:\s*['\"]?(\d+(?:\.\d+)?)", text):
                sizes[m.group(1) + "px"] += 1
            for m in re.finditer(r"\.system\(\s*size:\s*(\d+(?:\.\d+)?)", text):
                sizes[m.group(1) + "pt"] += 1
            for m in re.finditer(r"(?<![\w.])(\d+(?:\.\d+)?)\.sp\b", text):
                sizes[m.group(1) + "sp"] += 1
            for kind, _ in scan_line(rel, text) if not in_tokens else []:
                other[kind] += 1

    grid = args.grid
    off_grid = {v: n for v, n in spacing.items() if v.endswith("px") and float(v[:-2]) % grid != 0}
    clusters = cluster_colors(colors)
    report = {
        "distinct_colors": len(colors), "colors": colors.most_common(40),
        "near_duplicate_color_clusters": clusters,
        "colors_outside_token_files": sorted(c for c, w in where.items() if w - {"tokens"}),
        "distinct_font_sizes": len(sizes), "font_sizes": sorted(sizes.items(), key=lambda kv: -kv[1]),
        "distinct_radii": len(radii), "radii": sorted(radii.items(), key=lambda kv: -kv[1]),
        "distinct_spacing_values": len(spacing), "spacing": sorted(spacing.items(), key=lambda kv: -kv[1])[:40],
        f"spacing_off_{grid}px_grid": off_grid,
        "literal_findings_outside_token_files": dict(other.most_common()),
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print(f"# Design value inventory ({root.name})\n")
    print(f"Colors: {len(colors)} distinct; {len(report['colors_outside_token_files'])} appear outside token files.")
    for c, n in colors.most_common(24):
        print(f"  {c:<14} x{n}")
    if clusters:
        print(f"\nNear-duplicate colors (probably meant to be the same token): {len(clusters)} cluster(s)")
        for g in clusters[:15]:
            print("  " + "  ".join(g))
    print(f"\nFont sizes: {len(sizes)} distinct")
    print("  " + ", ".join(f"{v} x{n}" for v, n in report["font_sizes"][:20]))
    print(f"\nRadii: {len(radii)} distinct")
    print("  " + ", ".join(f"{v} x{n}" for v, n in report["radii"][:20]))
    print(f"\nSpacing/size literals: {len(spacing)} distinct; {len(off_grid)} off the {grid}px grid")
    print("  " + ", ".join(f"{v} x{n}" for v, n in report["spacing"][:24]))
    if off_grid:
        print("  off-grid: " + ", ".join(f"{v} x{n}" for v, n in sorted(off_grid.items(), key=lambda kv: -kv[1])[:20]))
    if other:
        print("\nLiteral style values outside token files, by kind:")
        for k, n in other.most_common():
            print(f"  {k:<36} {n}")
    print("\nA healthy product UI usually has a handful of grays, one accent with a few tints, semantic status "
          "colors, 5-8 font sizes, 2-4 radii and spacing on one grid. Large counts and near-duplicate clusters "
          "are drift; consolidate them through the token files, not ad hoc.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("diff")
    d.add_argument("--base", default="HEAD")
    d.add_argument("--staged", action="store_true")
    d.add_argument("--tailwind-palette", action="store_true",
                   help="also flag raw Tailwind palette classes (bg-blue-500) for projects with semantic color tokens")
    d.add_argument("--json", action="store_true")
    d.add_argument("--warn-only", action="store_true")
    i = sub.add_parser("inventory")
    i.add_argument("path", nargs="?")
    i.add_argument("--grid", type=int, default=4)
    i.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        cmd_diff(args) if args.cmd == "diff" else cmd_inventory(args)
    except subprocess.CalledProcessError as e:
        sys.exit(f"git failed: {e.stderr.strip() or e}")


if __name__ == "__main__":
    main()
