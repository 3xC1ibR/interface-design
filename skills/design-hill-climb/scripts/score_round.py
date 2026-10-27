#!/usr/bin/env python3
"""Score a hill-climb round from its critic replies and decide: accept, revert, or stop.

  score_round.py --round N [--root .design/hill-climb]

Reads rounds/rNN/critic-*.md. Each file holds one critic's two replies: Step 1 with its
blind scores in a JSON block, then Step 2 with keep/regressions/fixes. The script un-blinds
the letters with that critic's own mapping from labels.json, and takes medians across critics.
Scores always come from the FIRST JSON block that has them; anything after the reveal can't
change them.

The metric is relative, measured inside each critic's reply: product minus baseline, per
category. Absolute scores drift between calls; a delta taken within one call doesn't. A round
is accepted when Overall improves on the best accepted round by at least min_gain AND no
category falls by more than max_category_drop. The rule decides, not the implementer.

Writes rounds/rNN/verdict.json, updates state.json (including a cumulative Keep list), and
regenerates scoreboard.md.
"""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
PRIO = {"MUST": 0, "SHOULD": 1, "COULD": 2}


def parse_critic(path, labels, cats):
    blocks = []
    for b in JSON_BLOCK.findall(path.read_text()):
        try:
            blocks.append(json.loads(b))
        except json.JSONDecodeError:
            continue
    first = next((b for b in blocks if "scores" in b), None)
    if first is None:
        raise ValueError("no ```json block with \"scores\"")
    notes = []
    data = {"scores": first["scores"], "ranking": first.get("ranking")}
    for b in blocks:
        for k, v in b.items():
            if k in ("scores", "ranking"):
                if b is not first and v != first.get(k):
                    notes.append(f"{path.name}: a later block changed '{k}'; using the blind Step 1 values")
                continue
            data[k] = v
    lower = {c.lower(): c for c in cats}
    scores = {}
    for letter, row in (data["scores"] or {}).items():
        letter = letter.strip().upper()
        if letter not in labels:
            raise ValueError(f"unknown candidate letter {letter}")
        clean = {}
        for k, v in (row or {}).items():
            c = lower.get(str(k).strip().lower())
            if c is not None and isinstance(v, (int, float)):
                clean[c] = float(v)
        missing = [c for c in cats if c not in clean]
        if missing:
            raise ValueError(f"candidate {letter} is missing {', '.join(missing)}")
        scores[labels[letter]] = clean
    absent = [i for i in labels.values() if i not in scores]
    if absent:
        raise ValueError(f"no scores for {', '.join(absent)}")
    return scores, data, notes


def med(xs):
    return round(statistics.median(xs), 2) if xs else None


def spread(xs):
    return round(max(xs) - min(xs), 2) if len(xs) > 1 else 0.0


def fmt(x, signed=False):
    if x is None:
        return "–"
    return f"{x:+.2f}" if signed else f"{x:.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".design/hill-climb")
    ap.add_argument("--round", type=int, required=True)
    args = ap.parse_args()

    root = Path(args.root)
    cfg = json.loads((root / "config.json").read_text())
    rdir = root / "rounds" / f"r{args.round:02d}"
    meta = json.loads((rdir / "labels.json").read_text())
    cats = list(meta["categories"]) + ["Overall"]
    min_gain = float(cfg.get("min_gain", 0.15))
    max_drop = float(cfg.get("max_category_drop", 0.3))
    target_gap = float(cfg.get("target_gap", 0.0))
    plateau_n = int(cfg.get("plateau_rounds", 2))
    max_rounds = int(cfg.get("max_rounds", 8))
    final = bool(meta.get("final"))

    warnings, critics = [], []
    for p in sorted(rdir.glob("critic-*.md")):
        mapping = (meta.get("critics", {}).get(p.stem) or {}).get("labels") or meta.get("labels")
        if not mapping:
            print(f"skipping {p.name}: no packet mapping for '{p.stem}' in labels.json", file=sys.stderr)
            continue
        try:
            scores, data, notes = parse_critic(p, mapping, cats)
            critics.append((p.stem, scores, data))
            warnings += notes
        except Exception as e:
            print(f"skipping {p.name}: {e}", file=sys.stderr)
    if not critics:
        sys.exit(f"no usable critic replies in {rdir} (expected critic-K.md files with the brief's JSON blocks)")

    idents = sorted({i for _, s, _ in critics for i in s}, key=lambda i: (i != "product", i != "baseline", i))
    medians = {i: {c: med([s[i][c] for _, s, _ in critics if i in s]) for c in cats} for i in idents}
    refs = [i for i in idents if i.startswith("ref:")]
    ref_gaps = [max(s[r]["Overall"] for r in refs) - s["product"]["Overall"] for _, s, _ in critics if refs]
    ref_gap = med(ref_gaps)
    has_base = "baseline" in idents

    rel, rel_spread = None, None
    if has_base:
        per = {c: [s["product"][c] - s["baseline"][c] for _, s, _ in critics] for c in cats}
        rel = {c: med(v) for c, v in per.items()}
        rel_spread = spread(per["Overall"])
    abs_spread = spread([s["product"]["Overall"] for _, s, _ in critics])

    state_path = root / "state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"rounds": []}
    state["rounds"] = [r for r in state["rounds"] if r["round"] != args.round]
    accepted = {int(k): v for k, v in (state.get("accepted_rel") or {}).items() if int(k) < args.round}
    prev_best = max(accepted) if accepted else 0
    best = accepted.get(prev_best) or {c: 0.0 for c in cats}

    if args.round > 0 and not final and state.get("brief_hash") and state["brief_hash"] != meta["brief_hash"]:
        warnings.append("The brief, screens or references changed since round 0, so scores aren't comparable. "
                        "Start a new climb: new_round.py --round 0 --reset.")

    gain, deltas, worst = None, {}, (None, None)
    if rel and not final:
        gain = round(rel["Overall"] - best.get("Overall", 0.0), 2)
        deltas = {c: round(rel[c] - best.get(c, 0.0), 2) for c in meta["categories"]}
        worst = min(deltas.items(), key=lambda kv: kv[1]) if deltas else (None, None)

    state.setdefault("accepted_rel", {}).pop(str(args.round), None)
    if args.round == 0:
        verdict = "baseline"
        state["brief_hash"] = meta["brief_hash"]
        state["accepted_rel"]["0"] = {c: 0.0 for c in cats}
    elif final:
        verdict = "final"
        climbed = best.get("Overall", 0.0)
        if rel and climbed > 0 and rel["Overall"] < 0.5 * climbed:
            warnings.append(f"On held-out screens the product improved {fmt(rel['Overall'], True)} over baseline, "
                            f"less than half the {fmt(climbed, True)} it gained on the scored screens. The climb "
                            f"likely overfit: apply the system-level fixes across the whole app, then re-check.")
    else:
        ok = gain is not None and gain >= min_gain and (worst[1] is None or worst[1] >= -max_drop)
        verdict = "accept" if ok else "revert"
        if ok:
            state["accepted_rel"][str(args.round)] = rel
    state["best_round"] = max(int(k) for k in state["accepted_rel"])

    if len(critics) < 2:
        warnings.append("Only one critic: no noise estimate, so this verdict is a single opinion. "
                        "Use a panel of 2-3 for decisions you will build on.")
    elif rel_spread is not None and rel_spread > 2 * min_gain:
        warnings.append(f"Critics disagree by {rel_spread:.2f} on the product-vs-baseline delta, more than twice "
                        f"min_gain ({min_gain}). Add critics or raise min_gain, or you are climbing noise.")
    elif args.round == 0 and abs_spread > 1.0:
        warnings.append(f"Critics' Overall scores for the product differ by {abs_spread:.2f}. Expect noisy "
                        f"verdicts; consider 3 critics and a higher min_gain.")

    keep_now = [k for _, _, d in critics for k in d.get("keep") or []]
    if verdict in ("baseline", "accept"):
        protected = state.setdefault("keep", [])
        for k in keep_now:
            if k not in protected:
                protected.append(k)

    changes = ""
    cpath = rdir / "changes.md"
    if cpath.exists():
        lines = [l.strip("- ").strip() for l in cpath.read_text().splitlines()
                 if l.strip() and not l.strip().startswith("<!--")]
        changes = lines[0] if lines else ""

    record = {"round": args.round, "verdict": verdict, "critics": len(critics), "final": final,
              "product_overall": medians["product"]["Overall"],
              "baseline_overall": medians.get("baseline", {}).get("Overall"),
              "rel_overall": rel["Overall"] if rel else None, "gain_vs_best": gain,
              "worst_category": worst[0], "worst_category_delta": worst[1], "ref_gap": ref_gap,
              "spread_overall": rel_spread if rel_spread is not None else abs_spread, "changes": changes}

    climbing = [r for r in state["rounds"] + [record] if 0 < r["round"] <= args.round and not r["final"]]
    climbing.sort(key=lambda r: r["round"])
    stop = None
    if final:
        stop = "final check complete"
    elif verdict == "accept" and ref_gap is not None and ref_gap <= target_gap:
        stop = "target reached: the product matches or beats the best reference"
    elif len(climbing) >= plateau_n and all(r["verdict"] != "accept" for r in climbing[-plateau_n:]):
        stop = f"plateau: no accepted round in the last {plateau_n}"
    elif args.round >= max_rounds:
        stop = f"budget: reached max_rounds ({max_rounds})"
    record["stop"] = stop
    state["rounds"].append(record)
    state["rounds"].sort(key=lambda r: r["round"])
    state_path.write_text(json.dumps(state, indent=2))

    fixes = [{**f, "critic": name} for name, _, d in critics for f in d.get("fixes") or []]
    fixes.sort(key=lambda f: (PRIO.get(str(f.get("priority", "")).upper(), 3), str(f.get("category", ""))))
    regressions = [k for _, _, d in critics for k in d.get("regressions") or []]
    (rdir / "verdict.json").write_text(json.dumps({
        **record, "medians": medians, "rel": rel, "category_deltas_vs_best": deltas, "warnings": warnings,
        "keep": keep_now, "protected_keep": state.get("keep", []), "regressions": regressions,
        "fixes": fixes}, indent=2))

    rows = ["# Design hill climb scoreboard\n",
            "| Round | Product | Baseline | Δ vs baseline | Gain vs best | Worst category Δ | Gap to best ref | "
            "Critic spread | Verdict | Changes |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in state["rounds"]:
        w = f"{r['worst_category']} {fmt(r['worst_category_delta'], True)}" if r.get("worst_category") else "–"
        rows.append(f"| r{r['round']:02d}{' (holdout)' if r.get('final') else ''} | {fmt(r['product_overall'])} | "
                    f"{fmt(r['baseline_overall'])} | {fmt(r['rel_overall'], True)} | {fmt(r['gain_vs_best'], True)} | "
                    f"{w} | {fmt(r['ref_gap'], True)} | {fmt(r['spread_overall'])} | **{r['verdict']}**"
                    f"{' (' + r['stop'] + ')' if r.get('stop') else ''} | {r.get('changes') or ''} |")
    (root / "scoreboard.md").write_text("\n".join(rows) + "\n")

    # ---- report ----
    print(f"round {args.round}: {len(critics)} critic(s)  verdict: {verdict.upper()}" + (f"  STOP: {stop}" if stop else ""))
    for w in warnings:
        print(f"WARNING: {w}")
    print("\nmedian scores")
    print("  " + " | ".join(f"{h[:18]:>18}" for h in ["category"] + idents))
    for c in cats:
        print("  " + " | ".join([f"{c[:18]:>18}"] + [f"{fmt(medians[i][c]):>18}" for i in idents]))
    if rel:
        print("\nproduct vs baseline (median of within-critic deltas): "
              + ", ".join(f"{c} {fmt(v, True)}" for c, v in rel.items()))
        if not final:
            wc = f"{worst[0]} {fmt(worst[1], True)}" if worst[0] else "–"
            print(f"gain vs best accepted round (r{prev_best:02d}): {fmt(gain, True)}  "
                  f"(needs >= {min_gain:+.2f}; worst category {wc}, floor {-max_drop:+.2f})")
    print(f"gap to best reference (Overall): {fmt(ref_gap, True)}   critic spread: {fmt(record['spread_overall'])}")
    if state.get("keep"):
        print("\nPROTECTED (cumulative Keep from round 0 and accepted rounds; fixes must not undo these):")
        for k in state["keep"]:
            print(f"  - {k}")
    if regressions:
        print("\nREGRESSIONS reported this round:")
        for k in regressions:
            print(f"  - {k}")
    print("\nFIXES (all critics; merge duplicates, prefer ones several critics raise):")
    for f in fixes:
        print(f"  [{f.get('priority', '?')}] ({f.get('category', '?')}) {f.get('title', '')}  <{f['critic']}>")
        for k in ("where", "spec", "remove"):
            if f.get(k):
                print(f"        {k}: {f[k]}")
    if verdict == "revert":
        print("\nNext: revert this round's code commit, note why in changes.md, then try a different batch "
              "or split this one to find the change that hurt.")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
