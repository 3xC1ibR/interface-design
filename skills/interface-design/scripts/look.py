#!/usr/bin/env python3
"""Look at UI screenshots the way a designer would.

  look.py sbs BEFORE AFTER [--out PATH] [--labels Before After]
      Side-by-side composite. BEFORE/AFTER are two image files, or two directories
      (pairs files with the same name; --out is then a directory).

  look.py diff BEFORE AFTER [--out DIR] [--threshold 24] [--cell 12]
      What changed, where, and how much. Reports percent of pixels changed and the
      changed regions as boxes; writes a highlighted diff image per pair.
      Use it on screens that should NOT have changed to catch collateral damage.

  look.py squint IMAGE_OR_DIR [--out DIR] [--radius 6]
      Blurred grayscale render (the designer's squint test). With detail gone, the
      most prominent thing on screen should be the most important thing. Output goes to a
      separate folder (default: <input>-squint/) so it never mixes with captures.

  look.py blind BEFORE_IMG AFTER_IMG [--out DIR]
      Prepare a blind A/B comparison for a critic: copies the two images as A.png and B.png
      in random order plus an unlabeled side-by-side AB.png. The key (which is new) is printed
      here and NOT written into DIR, so the critic can't see it.

Requires Pillow.
"""
import argparse
import sys
from collections import deque
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
except ImportError:
    sys.exit("Pillow is required: pip install pillow")

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
DERIVED = (".squint", ".sbs", ".diff")


def images_in(d):
    return {p.name: p for p in sorted(Path(d).iterdir())
            if p.suffix.lower() in IMG_EXT and not p.stem.endswith(DERIVED)}


def pairs(a, b):
    a, b = Path(a), Path(b)
    if a.is_dir() and b.is_dir():
        ia, ib = images_in(a), images_in(b)
        only_a = sorted(set(ia) - set(ib))
        only_b = sorted(set(ib) - set(ia))
        for n in only_a:
            print(f"only in {a}: {n}")
        for n in only_b:
            print(f"only in {b}: {n}")
        return [(n, ia[n], ib[n]) for n in sorted(set(ia) & set(ib))], True
    if a.is_file() and b.is_file():
        return [(b.name, a, b)], False
    sys.exit("BEFORE and AFTER must both be files or both be directories")


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def sbs_one(pa, pb, labels, out):
    a = Image.open(pa).convert("RGB")
    b = Image.open(pb).convert("RGB")
    h = min(a.height, b.height)
    a = a.resize((round(a.width * h / a.height), h)) if a.height != h else a
    b = b.resize((round(b.width * h / b.height), h)) if b.height != h else b
    gap, bar = 24, 44
    canvas = Image.new("RGB", (a.width + b.width + gap * 3, h + bar + gap), (128, 128, 128))
    canvas.paste(a, (gap, bar))
    canvas.paste(b, (gap * 2 + a.width, bar))
    d = ImageDraw.Draw(canvas)
    f = font(22)
    d.text((gap, 10), labels[0], fill=(255, 255, 255), font=f)
    d.text((gap * 2 + a.width, 10), labels[1], fill=(255, 255, 255), font=f)
    canvas.save(out)
    return out


def changed_regions(mask, cell):
    """Group changed pixels into boxes on a coarse grid. Returns [(x0,y0,x1,y1,area)]."""
    gw, gh = max(1, mask.width // cell), max(1, mask.height // cell)
    grid = mask.resize((gw, gh), Image.BOX)
    data = list(grid.get_flattened_data() if hasattr(grid, "get_flattened_data") else grid.getdata())
    seen = [False] * len(data)
    boxes = []
    for i, v in enumerate(data):
        if v == 0 or seen[i]:
            continue
        q = deque([i])
        seen[i] = True
        xs, ys, n = [], [], 0
        while q:
            j = q.popleft()
            x, y = j % gw, j // gw
            xs.append(x)
            ys.append(y)
            n += 1
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < gw and 0 <= ny < gh:
                    k = ny * gw + nx
                    if not seen[k] and data[k] > 0:
                        seen[k] = True
                        q.append(k)
        sx, sy = mask.width / gw, mask.height / gh
        boxes.append((int(min(xs) * sx), int(min(ys) * sy), int((max(xs) + 1) * sx), int((max(ys) + 1) * sy), n))
    boxes.sort(key=lambda b: -b[4])
    return boxes


def diff_one(pa, pb, threshold, cell, out):
    a = Image.open(pa).convert("RGB")
    b = Image.open(pb).convert("RGB")
    note = ""
    if a.size != b.size:
        note = f" (size changed {a.width}x{a.height} -> {b.width}x{b.height}; compared on a padded canvas)"
        w, h = max(a.width, b.width), max(a.height, b.height)
        pa_, pb_ = Image.new("RGB", (w, h)), Image.new("RGB", (w, h))
        pa_.paste(a)
        pb_.paste(b)
        a, b = pa_, pb_
    r, g, bl = ImageChops.difference(a, b).split()
    mx = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    mask = mx.point(lambda v: 255 if v > threshold else 0)
    changed = mask.histogram()[255]
    pct = 100.0 * changed / (mask.width * mask.height)
    boxes = changed_regions(mask, cell) if changed else []
    if out:
        base = ImageOps.grayscale(b).convert("RGB").point(lambda v: 90 + v // 3)
        red = Image.new("RGB", b.size, (235, 40, 40))
        base.paste(red, mask=mask)
        d = ImageDraw.Draw(base)
        for x0, y0, x1, y1, _ in boxes[:20]:
            d.rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], outline=(255, 200, 0), width=3)
        base.save(out)
    return pct, boxes, note


def squint_one(p, radius, out):
    im = Image.open(p).convert("L")
    # scale blur with image size so results are comparable across densities
    r = radius * max(1.0, im.width / 1440)
    im.filter(ImageFilter.GaussianBlur(r)).save(out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sbs")
    s.add_argument("before")
    s.add_argument("after")
    s.add_argument("--out")
    s.add_argument("--labels", nargs=2, default=["Before", "After"])
    d = sub.add_parser("diff")
    d.add_argument("before")
    d.add_argument("after")
    d.add_argument("--out", help="directory for highlighted diff images")
    d.add_argument("--threshold", type=int, default=24, help="per-channel difference that counts as changed (0-255)")
    d.add_argument("--cell", type=int, default=12, help="grid size in px used to group changes into regions")
    bl = sub.add_parser("blind")
    bl.add_argument("before")
    bl.add_argument("after")
    bl.add_argument("--out", help="directory for A.png, B.png and AB.png (default: a new temp directory)")
    q = sub.add_parser("squint")
    q.add_argument("path")
    q.add_argument("--out")
    q.add_argument("--radius", type=float, default=6)
    args = ap.parse_args()

    if args.cmd == "sbs":
        ps, is_dir = pairs(args.before, args.after)
        if is_dir:
            out = Path(args.out or "sbs")
            out.mkdir(parents=True, exist_ok=True)
            for n, pa, pb in ps:
                print(sbs_one(pa, pb, args.labels, out / f"{Path(n).stem}.sbs.png"))
        else:
            n, pa, pb = ps[0]
            print(sbs_one(pa, pb, args.labels, args.out or f"{Path(n).stem}.sbs.png"))

    elif args.cmd == "diff":
        ps, _ = pairs(args.before, args.after)
        out = Path(args.out) if args.out else None
        if out:
            out.mkdir(parents=True, exist_ok=True)
        any_change = False
        for n, pa, pb in ps:
            pct, boxes, note = diff_one(pa, pb, args.threshold, args.cell,
                                        out / f"{Path(n).stem}.diff.png" if out else None)
            status = "unchanged" if pct == 0 else f"{pct:.2f}% changed in {len(boxes)} region(s)"
            print(f"{n}: {status}{note}")
            for x0, y0, x1, y1, _ in boxes[:8]:
                print(f"    region x={x0}-{x1} y={y0}-{y1} ({x1 - x0}x{y1 - y0})")
            any_change |= pct > 0
        if out:
            print(f"diff images -> {out}")
        sys.exit(1 if any_change else 0)

    elif args.cmd == "blind":
        import random
        import shutil
        import tempfile
        out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="blind-ab-"))
        out.mkdir(parents=True, exist_ok=True)
        pair = [("before", Path(args.before)), ("after", Path(args.after))]
        random.SystemRandom().shuffle(pair)
        for letter, (_, src) in zip("AB", pair):
            Image.open(src).convert("RGB").save(out / f"{letter}.png")  # re-encode: drops metadata
        sbs_one(out / "A.png", out / "B.png", ["A", "B"], out / "AB.png")
        print(f"blind pair -> {out}  (A.png, B.png, AB.png)")
        print(f"KEY (keep this out of the critic's view): A = {pair[0][0]}, B = {pair[1][0]}")

    elif args.cmd == "squint":
        p = Path(args.path)
        files = list(images_in(p).values()) if p.is_dir() else [p]
        if args.out:
            out = Path(args.out)
        else:
            base = p if p.is_dir() else p.parent
            out = base.parent / f"{base.name}-squint"
        out.mkdir(parents=True, exist_ok=True)
        for f in files:
            print(squint_one(f, args.radius, out / f"{f.stem}.squint.png"))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
