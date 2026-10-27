#!/usr/bin/env python3
"""Build a before/after board for a human checkpoint: baseline vs best accepted vs latest round,
the reference screens, and the scoreboard, in one self-contained HTML page.

  gallery.py [--root .design/hill-climb] [--out board.html] [--embed]

--embed inlines the images (base64) so the page stands alone, e.g. to publish or send it.
Without it, images are linked relative to the output file.
"""
import argparse
import base64
import html
import json
import mimetypes
import os
from pathlib import Path

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}

CSS = """
:root { --bg:#f6f6f4; --fg:#16181c; --muted:#5d6470; --line:#dcdcd6; --card:#ffffff;
        --ok:#1f7a4d; --bad:#b4372f; --neutral:#5d6470; }
@media (prefers-color-scheme: dark) { :root { --bg:#111317; --fg:#e7e9ec; --muted:#9aa2ad;
        --line:#2a2e35; --card:#181b20; --ok:#4fbf86; --bad:#e2766c; --neutral:#9aa2ad; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 system-ui, -apple-system, sans-serif; }
main { max-width: 1680px; margin: 0 auto; padding: 32px 16px 64px; }
h1 { font-size: 22px; margin: 0 0 4px; } h2 { font-size: 16px; margin: 40px 0 12px; }
.sub { color: var(--muted); margin: 0 0 24px; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; background: var(--card); }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--muted); font-weight: 500; font-size: 12px; }
.accept { color: var(--ok); font-weight: 600; } .revert { color: var(--bad); font-weight: 600; }
.baseline, .final { color: var(--neutral); font-weight: 600; }
.screen { margin: 0 0 32px; }
.screen h3 { font-size: 13px; font-weight: 600; margin: 0 0 8px; color: var(--muted); }
.row { display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: 12px; }
figure { margin: 0; } figcaption { font-size: 12px; color: var(--muted); margin-bottom: 6px; }
img { width: 100%; height: auto; display: block; border: 1px solid var(--line); border-radius: 4px; background: var(--card); }
.refs { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
@media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
"""


def src(path, out_dir, embed):
    if embed:
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()
    return html.escape(os.path.relpath(path, out_dir))


def images(d):
    d = Path(d)
    return {p.stem: p for p in sorted(d.iterdir()) if p.suffix.lower() in IMG_EXT} if d.is_dir() else {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".design/hill-climb")
    ap.add_argument("--out")
    ap.add_argument("--embed", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    cfg = json.loads((root / "config.json").read_text())
    state = json.loads((root / "state.json").read_text()) if (root / "state.json").exists() else {"rounds": []}
    out = Path(args.out or root / "board.html")
    out_dir = out.parent.resolve()
    rounds_dir = root / "rounds"
    round_dirs = sorted(d for d in rounds_dir.iterdir() if d.is_dir()) if rounds_dir.is_dir() else []
    latest = round_dirs[-1] if round_dirs else None
    best_round = state.get("best_round", 0)
    best_dir = rounds_dir / f"r{best_round:02d}"

    columns = [("Baseline", images(root / "baseline"))]
    if best_round and best_dir.is_dir():
        columns.append((f"Best accepted (r{best_round:02d})", images(best_dir / "current")))
    if latest is not None and latest.name != f"r{best_round:02d}" and latest.name != "r00":
        last = next((r for r in state["rounds"] if f"r{r['round']:02d}" == latest.name), None)
        tag = f" · {last['verdict']}" if last else ""
        columns.append((f"Latest ({latest.name}{tag})", images(latest / "current")))

    stems = sorted(set().union(*[set(c[1]) for c in columns])) if columns else []
    configured = list(cfg.get("screens") or []) + list(cfg.get("holdout") or [])
    if configured:
        stems = [s for s in configured if s in stems]
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
             f"<title>Design hill climb</title><style>{CSS}</style></head><body><main>",
             f"<h1>{html.escape(cfg.get('product', 'Product'))}: design hill climb</h1>",
             f"<p class='sub'>{html.escape(cfg.get('context', ''))}</p>"]

    if state["rounds"]:
        parts.append("<h2>Scoreboard</h2><table><tr><th>Round</th><th>Verdict</th><th>Product</th><th>Δ vs baseline</th>"
                     "<th>Gain vs best</th><th>Worst category Δ</th><th>Gap to best ref</th><th>Changes</th></tr>")
        f = lambda x, s=False: "–" if x is None else (f"{x:+.2f}" if s else f"{x:.2f}")
        for r in state["rounds"]:
            wc = f"{r['worst_category']} {f(r['worst_category_delta'], True)}" if r.get("worst_category") else "–"
            parts.append(f"<tr><td>r{r['round']:02d}</td><td class='{r['verdict']}'>{r['verdict']}"
                         f"{' · ' + html.escape(r['stop']) if r.get('stop') else ''}</td>"
                         f"<td>{f(r['product_overall'])}</td><td>{f(r['rel_overall'], True)}</td>"
                         f"<td>{f(r['gain_vs_best'], True)}</td><td>{html.escape(wc)}</td>"
                         f"<td>{f(r['ref_gap'], True)}</td><td>{html.escape(r.get('changes') or '')}</td></tr>")
        parts.append("</table>")

    parts.append("<h2>Screens</h2>")
    for stem in stems:
        cells = [(label, imgs.get(stem)) for label, imgs in columns]
        parts.append(f"<section class='screen'><h3>{html.escape(stem)}</h3><div class='row' style='--n:{len(cells)}'>")
        for label, p in cells:
            inner = f"<img loading='lazy' alt='{html.escape(label)}: {html.escape(stem)}' src='{src(p, out_dir, args.embed)}'>" if p else "<p class='sub'>not captured</p>"
            parts.append(f"<figure><figcaption>{html.escape(label)}</figcaption>{inner}</figure>")
        parts.append("</div></section>")

    for name, d in (cfg.get("references") or {}).items():
        refs = images(d)
        if refs:
            parts.append(f"<h2>Reference: {html.escape(name)}</h2><div class='refs'>")
            for stem, p in refs.items():
                parts.append(f"<figure><figcaption>{html.escape(stem)}</figcaption>"
                             f"<img loading='lazy' alt='{html.escape(stem)}' src='{src(p, out_dir, args.embed)}'></figure>")
            parts.append("</div>")

    parts.append("</main></body></html>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts))
    size = out.stat().st_size / 1e6
    print(f"wrote {out} ({size:.1f} MB)" + ("  — over 16 MB; drop --embed or use fewer screens before publishing" if size > 16 else ""))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
