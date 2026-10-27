#!/usr/bin/env python3
"""Build blinded critic packets for one hill-climb round.

  new_round.py --round N --current SHOTS_DIR [--root .design/hill-climb] [--critics 3]
               [--final] [--reset] [--one-pass] [--seed S] [--packet-dir DIR]

Round 0 is the audit. If baseline/ is empty, the current captures become the baseline, and
the product is compared with the references only. --reset (round 0 only) archives a previous
climb first, so you can start over with a new brief or new screens.

Rounds 1+ show the product's current version, its baseline and the references, on the scored
screens. --final scores only the held-out screens, to check that the gains transferred to
screens the climb never optimized.

Each critic gets its OWN packet with its own shuffled letters, written to a fresh temp
directory outside the workspace, with file timestamps normalized, so nothing in the packet
reveals which candidate is yours. The letter mappings stay in rounds/rNN/labels.json.

Critiques run in two turns so that blind scoring is enforced. The first prompt gets the
scores. A follow-up message then reveals which candidate is which and asks for Keep,
Regressions and fixes. Both are printed for each critic. Save each critic's two replies, in
order, as rounds/rNN/critic-K.md. --one-pass puts REVEAL.md in the packet instead, for
harnesses that can't send a follow-up to a running subagent; blinding then relies on the
critic's honor.
"""
import argparse
import hashlib
import json
import os
import random
import re
import shutil
import string
import sys
import tempfile
import time
from pathlib import Path

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
DERIVED = re.compile(r"\.(squint|sbs|diff)$")
TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "brief-template.md"
FIXED_MTIME = 946684800  # 2000-01-01: every packet file gets the same timestamp
DEFAULT_CATEGORIES = ["Typography", "Hierarchy", "Spacing & density", "Color & contrast",
                      "Iconography", "Consistency & polish", "Clarity"]


def images(d):
    d = Path(d)
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if p.suffix.lower() in IMG_EXT and not DERIVED.search(p.stem))


def select(paths, wanted):
    by_stem = {p.stem: p for p in paths}
    missing = [w for w in wanted if w not in by_stem]
    if missing:
        print(f"warning: no capture found for: {', '.join(missing)}", file=sys.stderr)
    return [by_stem[w] for w in wanted if w in by_stem]


def clean_copy(src, dst):
    """Copy content only (no metadata) and stamp a fixed mtime, so timestamps can't identify a candidate."""
    shutil.copyfile(src, dst)
    os.utime(dst, (FIXED_MTIME, FIXED_MTIME))


def vocabulary_excerpt(text):
    """DESIGN.md minus its history: drop sections about decisions, logs or changes."""
    out, skip = [], False
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            skip = bool(re.search(r"\b(decision log|decisions|history|change ?log|changes|migrations?)\b",
                                  m.group(2), re.I))
        if not skip:
            out.append(line)
    return "\n".join(out).strip() + "\n"


def brief_hash(cfg, template_text, screens, refs):
    """Fingerprint of what must stay fixed during a climb (not paths, letters or round number)."""
    keyed = json.dumps({"context": cfg.get("context"), "platform": cfg.get("platform"),
                        "categories": cfg.get("categories"), "screens": sorted(screens),
                        "references": {name: sorted(p.name for p in files) for name, files in refs}},
                       sort_keys=True)
    return hashlib.sha256((template_text + keyed).encode()).hexdigest()[:12]


def reset(root):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    arch = root / "archive" / stamp
    moved = []
    for name in ("baseline", "rounds", "state.json", "scoreboard.md", "board.html"):
        p = root / name
        if p.exists():
            arch.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(arch / name))
            moved.append(name)
    print(f"archived previous climb to {arch}: {', '.join(moved)}" if moved else "nothing to archive")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".design/hill-climb")
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--current", required=True, help="directory of fresh captures of the product")
    ap.add_argument("--critics", type=int, default=3, help="number of critics (one packet each)")
    ap.add_argument("--final", action="store_true", help="score the held-out screens only")
    ap.add_argument("--reset", action="store_true", help="round 0 only: archive the previous climb and start over")
    ap.add_argument("--one-pass", action="store_true", help="put REVEAL.md in the packet (no follow-up turn)")
    ap.add_argument("--seed", type=int, help="shuffle seed (default: derived from the round number)")
    ap.add_argument("--packet-dir", help="where to create packets (default: the system temp directory)")
    args = ap.parse_args()

    root = Path(args.root)
    cfg = json.loads((root / "config.json").read_text())
    template = TEMPLATE.read_text()
    categories = cfg.get("categories") or DEFAULT_CATEGORIES
    holdout = list(cfg.get("holdout") or [])

    if args.reset:
        if args.round != 0:
            sys.exit("--reset only applies to round 0")
        reset(root)

    current_all = images(args.current)
    if not current_all:
        sys.exit(f"no images in {args.current}")
    main_screens = list(cfg.get("screens") or []) or [p.stem for p in current_all if p.stem not in set(holdout)]
    if args.final:
        if args.round == 0:
            sys.exit("--final needs a completed climb; use the next round number after your last round")
        if not holdout:
            sys.exit("--final needs 'holdout' screens in config.json")
        scored = holdout
    else:
        scored = main_screens

    baseline_dir = root / "baseline"
    if args.round == 0 and not images(baseline_dir):
        baseline_dir.mkdir(parents=True, exist_ok=True)
        for p in current_all:
            shutil.copyfile(p, baseline_dir / p.name)
        print(f"baseline saved from {args.current} ({len(current_all)} images)")
    if args.round > 0 and not images(baseline_dir):
        sys.exit("no baseline/ yet: run round 0 first")

    rdir = root / "rounds" / f"r{args.round:02d}"
    if rdir.exists() and any(rdir.glob("critic-*.md")):
        hint = "use --reset to start a new climb" if args.round == 0 else f"use --round {args.round + 1}"
        sys.exit(f"{rdir} already has critic results; {hint}")
    rdir.mkdir(parents=True, exist_ok=True)

    current_sel = select(current_all, scored)
    if not current_sel:
        sys.exit("none of the screens to score were found in the captures")
    keep_dir = rdir / "current"
    if keep_dir.exists():
        shutil.rmtree(keep_dir)
    keep_dir.mkdir()
    for p in current_sel:
        shutil.copyfile(p, keep_dir / p.name)

    identities = [("product", current_sel)]
    if args.round > 0:
        base_sel = select(images(baseline_dir), scored)
        if base_sel:
            identities.append(("baseline", base_sel))
    refs = []
    for name, d in (cfg.get("references") or {}).items():
        files = images(d)
        if not files:
            print(f"warning: reference '{name}' has no images in {d}", file=sys.stderr)
            continue
        refs.append((name, files))
        identities.append((f"ref:{name}", files))

    vocab_text = None
    vocab = cfg.get("vocabulary")
    if vocab and Path(vocab).is_file():
        vocab_text = vocabulary_excerpt(Path(vocab).read_text())
    vocab_note = ("Where it fits, express specs with the token and component names in VOCABULARY.md "
                  "(the product's design system). If the system itself is the problem, say so.") if vocab_text else ""
    context = cfg.get("context", "").strip() or "An application interface."
    if cfg.get("platform"):
        context += f"\n\nPlatform: {cfg['platform']}."
    product_name = cfg.get("product", "the product")

    base_seed = args.seed if args.seed is not None else 1000 + args.round * 97
    packet_root = Path(args.packet_dir) if args.packet_dir else Path(tempfile.gettempdir())
    packet_root.mkdir(parents=True, exist_ok=True)
    critics = {}
    for k in range(1, args.critics + 1):
        packet = Path(tempfile.mkdtemp(prefix="design-review-", dir=packet_root))
        rng = random.Random(base_seed + k)
        letters = list(string.ascii_uppercase[:len(identities)])
        rng.shuffle(letters)
        labels, lines = {}, []
        for (ident, files), letter in sorted(zip(identities, letters), key=lambda t: t[1]):
            labels[letter] = ident
            cdir = packet / "candidates" / letter
            cdir.mkdir(parents=True)
            for p in files:
                clean_copy(p, cdir / p.name)
            lines.append(f"- **{letter}**: `candidates/{letter}/` ({', '.join(p.name for p in files)})")
        if vocab_text:
            (packet / "VOCABULARY.md").write_text(vocab_text)
        brief = (template.replace("{{ROUND}}", str(args.round))
                 .replace("{{CONTEXT}}", context)
                 .replace("{{CANDIDATES}}", "\n".join(lines))
                 .replace("{{CATEGORIES}}", "\n".join(f"- {c}" for c in categories))
                 .replace("{{VOCAB}}", vocab_note))
        (packet / "BRIEF.md").write_text(brief)

        product_letter = next(l for l, v in labels.items() if v == "product")
        reveal = [f"- **{product_letter}** is the product under review ({product_name})"
                  + (", current version." if args.round > 0 else ".")]
        for l, v in sorted(labels.items()):
            if v == "baseline":
                reveal.append(f"- **{l}** is the same product's earlier version (the baseline).")
            elif v.startswith("ref:"):
                reveal.append(f"- **{l}** is a reference product ({v[4:]}) that sets the quality bar.")
        if args.round == 0:
            reveal.append("\nThis is round 0: there is no earlier version. List as Keep the product's strengths "
                          "worth protecting, and leave Regressions empty.")
        reveal_text = "\n".join(reveal) + "\n"
        if args.one_pass:
            (packet / "REVEAL.md").write_text("# Reveal\n\n" + reveal_text)
        for p in packet.rglob("*"):
            os.utime(p, (FIXED_MTIME, FIXED_MTIME))
        critics[f"critic-{k}"] = {"packet": str(packet.resolve()), "labels": labels, "reveal": reveal_text}

    (rdir / "labels.json").write_text(json.dumps({
        "round": args.round, "final": args.final, "screens": [p.stem for p in current_sel],
        "categories": categories,
        "brief_hash": brief_hash(cfg, template, [s for s in main_screens], refs),
        "critics": critics}, indent=2))

    print(f"round {args.round}: {len(identities)} candidates, {len(current_sel)} product screens, "
          f"{args.critics} critic packet(s)")
    print(f"Save each critic's replies, in order, as {rdir}/critic-K.md, then run score_round.py --round {args.round}")
    for name, c in critics.items():
        pdir = c["packet"]
        prompt = (f"Act as the review sub-agent for this task.\n\n"
                  f"Read the brief at {pdir}/BRIEF.md and follow it exactly. This is round {args.round}. "
                  f"Open every screenshot listed there (they are image files; view them as images). "
                  f"Do not modify the packet or open anything outside {pdir}; scratch files for measuring "
                  f"are fine in a separate temp directory. "
                  + ("Do Step 1, then Step 2; open REVEAL.md only after Step 1 is written. "
                     if args.one_pass else "Do Step 1 only, then stop and wait for the reveal message. ")
                  + "Reply in the output format the brief asks for.")
        print(f"\n===== {name}: prompt (fresh context) =====\n{prompt}")
        if not args.one_pass:
            print(f"\n----- {name}: follow-up message (send to the same critic after its Step 1 reply) -----\n"
                  f"Reveal:\n{c['reveal']}\nNow do Step 2 of the brief for the product. Do not change your "
                  f"Step 1 scores. End with the Step 2 JSON block.")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
