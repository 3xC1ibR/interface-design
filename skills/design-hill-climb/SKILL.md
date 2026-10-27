---
name: design-hill-climb
description: Audit and iteratively improve an existing interface by hill-climbing against blind, screenshot-only critics and reference apps the user admires. Use when the user wants a design audit or score for a UI, a comparison with apps like Linear, Claude, Codex or Things, a request to "polish until it's great" or "make it as good as X", an agent-driven design improvement loop, or UI quality turned into a measurable target, on web, desktop/Electron, iOS or Android. Also use for a one-shot audit report with prioritized fixes. Every fix follows the interface-design skill's change rules.
---

# Design Hill Climb

This skill turns "make it look better" into an optimization loop with an outside judge:

> capture → blind critique → score → fix a small batch → recapture → accept or revert

It combines three things:
- a review council: a frozen brief, scores per category against reference apps, and prioritized fixes with concrete values;
- a critic loop: fresh-context critics that see screenshots only, never the code;
- the hygiene you'd apply to any eval you plan to optimize against.

## Why each piece exists

- **Agents can't grade their own UI.** They see their intent, not the pixels. Critics get images only, never code, diffs, rationale, earlier critiques or the score history.
- **Critics are noisy and biased.** So the candidates are blinded behind letters shuffled separately for each critic, in packets that carry no timestamps or history. Scoring happens before the reveal, in a separate turn, and those blind scores can't be changed afterwards. The brief stays fixed for the whole climb. The baseline and the references are scored *in the same call* as the current version, and the metric is the delta within that call. A panel of critics is aggregated by median.
- **Hill climbs overfit (Goodhart's law).** So each round is a small batch of fixes whose effect can be attributed. A per-category regression gate catches trade-offs that the overall score hides. A protected Keep list stops fixes from undoing past wins. Held-out screens are checked at the end. A human checkpoint with pictures overrides any score.
- **Verdicts are made by rule.** `score_round.py` decides accept or revert, so the implementer never decides whether its own change worked.

## Setup

Gather these first. Ask the user only for what you cannot find or decide yourself.

1. **Screens to optimize.** Pick 4 to 10 captures that represent the product, including at least one dense state and one empty or edge state. Set aside 1 to 3 more as a **holdout**: they are never shown to critics during the climb.
2. **References.** Get 2 to 4 products the user admires, in the same category and posture, with screenshots of comparable screens. Ask the user for these, because they carry taste. Capture public ones yourself where you can. Without references, critics drift toward generic taste. References from the wrong category push toward the wrong density, as when a marketing site is the bar for a dense tool.
3. **Deterministic capture.** Use `scripts/capture_web.py`, starting from `assets/capture-example.json` (see interface-design's `references/seeing-your-work.md` for Electron, iOS and Android). Hold data, time, fonts, window size and animation constant, or the critics will be scoring noise.
4. **Critics.** Use a panel of 2 or 3 fresh subagents on the strongest model available. Mix model families if you can, because they catch different problems. The implementer can be a cheaper model.
5. **Budget.** Defaults: at most 8 rounds and at most 3 fixes per round.
6. **Version control.** Work on a branch with one commit per round containing only product code, so that a revert is one command. Keep `.design/hill-climb/` out of those commits (gitignore it, or commit it separately), or reverting a round would delete its own record.

Create `.design/hill-climb/config.json` from `assets/config-example.json`; `references/config.md` explains every field. Write `context` as a neutral description of the product and its users. Never put the target or the scores in it. If the repo has a DESIGN.md, set `vocabulary` to its path so critics write their specs in the product's own token names.

## Round 0: audit

1. Capture the product to a directory, for example `.design/shots/current`.
2. Build the packets: `python3 scripts/new_round.py --round 0 --current .design/shots/current --critics 3`. This saves the baseline and writes one packet per critic to a temp directory. For each critic it prints a prompt and a follow-up reveal message.
3. Spawn critic K in a **fresh context** with critic K's prompt; it replies with blind scores and stops. Then send critic K's follow-up message to that *same* critic (in Claude Code, continue the subagent with SendMessage); it replies with Keep, Regressions and fixes. Save both replies, in order, as `.design/hill-climb/rounds/r00/critic-K.md`. The file name must match the packet, because each critic's letters are shuffled differently. Splitting the work into two turns is what makes the blind scoring real. If your harness can't continue a subagent, pass `--one-pass`, which puts the reveal in the packet behind an honor-system instruction.
4. Score it: `python3 scripts/score_round.py --round 0`. This prints median scores, the gap to the best reference, the protected Keep list and every fix.
5. **Watch the noise.** From round 1 on, the script measures how much the critics disagree about the product-vs-baseline delta. If that spread exceeds about twice `min_gain`, it warns you; add a critic or raise `min_gain`, or you are optimizing noise. In round 0, a large spread in absolute scores is an early hint.

**If the user only wants an audit, stop here.** Build the board with `python3 scripts/gallery.py --embed`, then give the user:
- the scores against the references;
- the Keep list;
- the merged, prioritized fixes, each with its concrete spec;
- any fixes that are really concept-level decisions.

## Rounds 1 to N

1. **Choose the batch.** Merge duplicate fixes across critics. Take the MUST fixes that several critics agree on first, up to `fixes_per_round`. Skip any fix that would undo an item on the protected Keep list (cumulative across round 0 and accepted rounds, kept in `state.json`). Prefer fixes that remove, merge or quiet something over fixes that add. A fix that implies a new concept or surface (for example "make this modal inline") is a design decision, so take it to the user.
2. **Implement under interface-design's change rules.** Use tokens only. Update the contract when a fix is system-level, and get `drift_check.py diff` clean. Critics describe pixels, so you translate their specs into the real source. Apply a system-level fix everywhere it belongs, not only on the scored screens; that is what lets the holdout check pass.
3. **Record and commit.** Write one line per change in `.design/hill-climb/rounds/rNN/changes.md` (create the folder; `new_round.py` won't overwrite the file), then commit.
4. **Score the round.** Recapture with the same config, then run `new_round.py --round N --current ...`. Spawn **new** critics (never reuse a critic from an earlier round), run both turns as in round 0, save the replies as `critic-K.md`, and run `score_round.py --round N`.
5. **Act on the verdict.**
   - **accept**: keep the commit and start the next round.
   - **revert**: revert the round's code commit and note why in `changes.md`. Then try a different batch, or split this one to find the change that hurt.
   - **stop** (target reached, plateau or budget): go to Final.

Rules for the whole climb:
- Don't tell critics the target, the history or what changed.
- Don't edit the brief, the scored screens or the references mid-climb. The script warns when they have changed. If you must change them, start over with `new_round.py --round 0 --reset`, which archives the old climb.
- **Checkpoint with the human** every 3 rounds, and after any large visual change. Show them `gallery.py --embed`. Their taste overrides the score.

## Final

Recapture, including the holdout screens, and run `python3 scripts/new_round.py --round <next number> --current ... --final`. This scores **only the held-out screens**, product against baseline, so you can see whether the gains transferred to screens the climb never optimized. Run fresh critics, then `score_round.py --round <same number>`. If the holdout gain is less than half the climbed gain, the script warns that the climb overfit. Spread the system-level fixes across the app and check again.

Deliver:
- the gallery (publish it if the environment supports artifacts);
- `scoreboard.md`;
- the DESIGN.md changes;
- the fixes you didn't take, and why;
- concept-level suggestions for the user to decide.

## Reading the numbers

- **Trust deltas over absolutes.** "Product minus baseline, measured in the same call" is the metric; absolute scores wander between calls.
- **A reference gap closing is progress.** "Beating" a reference on score is not necessarily real, so check it with the user's eyes.
- **One category staying low with no fix aimed at it** usually means the critics see a problem but can't express it in pixels. Run a focused critic on just that category, or look for a concept-level cause.
- **Repeated reverts on similar fixes** mean the fixes are fighting the product's signature or posture. Re-read the contract before trying again.
- **Fixes that flip-flop** between rounds (one critic says lighten the titles, the next says restore the weight) mark a taste call the critics can't settle. Show the user both renders, record their decision in DESIGN.md, and stop relitigating it.
- **Check what actually rendered.** Critics measure pixels, so they catch cases where the code says one thing and the screen shows another, such as a font weight with no matching font file that falls back to regular. Take those reports seriously, because a code review would miss them.

## Files in this skill

- `assets/brief-template.md`: the critic brief. It sets the role, blind scoring with anchors, the reveal step, Keep, Regressions and fixes with concrete specs, and the JSON output format. `new_round.py` fills it in for each round. Edit it before round 0 if the categories or bar need changing, never during a climb.
- `assets/config-example.json`: starting configuration.
- `references/config.md`: config fields, workspace layout and tips on choosing screens and references.
- `scripts/new_round.py`: builds one blinded packet per critic (own shuffle, normalized timestamps, written outside the workspace) and prints each critic's prompt and follow-up reveal. Also handles `--final` (holdout only) and `--reset`.
- `scripts/score_round.py`: un-blinds the replies, keeps the blind Step 1 scores even if a later reply restates them, skips malformed replies, takes medians, computes deltas, gates accept or revert, keeps the cumulative Keep list, and regenerates `scoreboard.md`.
- `scripts/gallery.py`: an HTML board showing baseline, best and latest for each screen, the references and the scoreboard.
- `scripts/capture_web.py`, `scripts/look.py`: capture and comparison tools, identical to the copies in interface-design.

Scripts need Python 3 and Pillow, and capture needs Playwright. Run them from the repo root with the skill directory as the path prefix.

Background: the council format follows Theo Browne's T3 Code UI hill climb. The screenshot-only critic loop follows Anshu Chimala's "How to turn your AI into a world-class designer" (Lenny's Newsletter, 2026).
