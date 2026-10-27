# interface-design

Two companion agent skills for building, changing, and auditing user interfaces across web, desktop/Electron, iOS, and Android without visual or conceptual drift:

- **[`interface-design`](skills/interface-design/SKILL.md)**: everyday UI creation and change discipline built around a persistent `DESIGN.md` contract, conceptual-model grammar checks, token enforcement, deterministic screenshot capture, subtraction passes, and blind A/B critique.
- **[`design-hill-climb`](skills/design-hill-climb/SKILL.md)**: a multi-round optimization loop that audits and iteratively improves an interface against reference apps and a panel of blind, screenshot-only critics with anti-Goodhart gates and held-out screens.

## Why This Exists

Agents fail at interface work in two opposite ways:

1. **On a blank canvas, they converge on the generic.** Every layout, palette, and component choice defaults to the highest-probability token sequence unless grounded in an explicit conceptual model, posture, and signature detail.
2. **On an existing application, they diverge.** One extra label, a fourth button style, a new gray 3% off the existing token, or a modal where an inline action belongs. Each diff looks locally reasonable in code review; twenty edits later, the interface feels incoherent.

Code diffs cannot verify visual hierarchy, and agents that know their own intent cannot objectively grade their own pixels. These skills replace blind code edits with a persistent design contract, deterministic rendering across states, automated token-drift checks, and fresh-context visual critics.

## Included Skills

### 1. `interface-design`

Covers both **Create mode** (diverging on directions, modeling objects and actions before pixels, spending novelty in one place, and writing `DESIGN.md`) and **Change mode** (converging on the existing contract):

- **[`skills/interface-design/SKILL.md`](skills/interface-design/SKILL.md)**: the core 10-step change workflow and mode selector.
- **[`skills/interface-design/references/conceptual-model.md`](skills/interface-design/references/conceptual-model.md)**: object-action grammar, application posture (sovereign, transient, ambient), layer stack, direct manipulation, signifiers, and motion checks.
- **[`skills/interface-design/references/design-contract.md`](skills/interface-design/references/design-contract.md)**: the `DESIGN.md` contract template (compatible with Google's open `DESIGN.md` token front matter) and how to bootstrap a contract from an existing codebase.
- **[`skills/interface-design/references/create-mode.md`](skills/interface-design/references/create-mode.md)**: end-to-end process for new surfaces and redesigns (discover, define, diverge, converge, deliver).
- **[`skills/interface-design/references/seeing-your-work.md`](skills/interface-design/references/seeing-your-work.md)**: deterministic capture recipes for web, Electron, iOS Simulator, and Android, plus the full state matrix (empty, loading, error, long content, narrow/wide, light/dark, interactive states).
- **[`skills/interface-design/references/tells.md`](skills/interface-design/references/tells.md)**: common drift smells and machine-generated UI tells to eliminate during the subtraction pass.
- **Scripts**:
  - [`scripts/capture_web.py`](skills/interface-design/scripts/capture_web.py): deterministic Playwright screenshot capture across screens, viewports, and color schemes.
  - [`scripts/look.py`](skills/interface-design/scripts/look.py): side-by-side (`sbs`), pixel-region diff (`diff`), blurred hierarchy test (`squint`), and randomized blind A/B packet generator (`blind`).
  - [`scripts/drift_check.py`](skills/interface-design/scripts/drift_check.py): flags literal style values in diffs (`diff`) and inventories distinct colors, font sizes, spacings, radii, shadows, and z-indexes across a codebase (`inventory`).

### 2. `design-hill-climb`

Turns *"polish this UI until it's as good as X"* into a controlled evaluation and optimization loop:

> capture → blind critique → score → fix a small batch → recapture → accept or revert

- **[`skills/design-hill-climb/SKILL.md`](skills/design-hill-climb/SKILL.md)**: Round 0 audit, Rounds 1..N hill-climbing, human checkpoints, and final holdout verification.
- **[`skills/design-hill-climb/references/config.md`](skills/design-hill-climb/references/config.md)**: `.design/hill-climb/config.json` schema, workspace layout, and screen/reference selection rules.
- **[`skills/design-hill-climb/assets/brief-template.md`](skills/design-hill-climb/assets/brief-template.md)**: two-turn critic protocol (Step 1 blind scoring across shuffled candidates, Step 2 identity reveal with protected Keep list, Regressions, and concrete fixes).
- **Scripts**:
  - [`scripts/new_round.py`](skills/design-hill-climb/scripts/new_round.py): generates per-critic shuffled, timestamp-normalized blind packets outside the workspace (`--round`, `--final`, `--reset`, `--one-pass`).
  - [`scripts/score_round.py`](skills/design-hill-climb/scripts/score_round.py): un-blinds critic responses, locks Step 1 blind scores, aggregates medians and within-call deltas against baseline and references, enforces per-category regression gates, updates the cumulative Keep list, and writes `scoreboard.md`.
  - [`scripts/gallery.py`](skills/design-hill-climb/scripts/gallery.py): builds a self-contained HTML board comparing baseline, best accepted, latest round, reference screenshots, and the scoreboard.
  - [`scripts/capture_web.py`](skills/design-hill-climb/scripts/capture_web.py) & [`scripts/look.py`](skills/design-hill-climb/scripts/look.py): deterministic capture and visual inspection tools.

## Requirements

- Python 3
- [Pillow](https://python-pillow.org/) (`pip install Pillow`) for `look.py`
- [Playwright](https://playwright.dev/python/) (`pip install playwright && python3 -m playwright install chromium`) for `capture_web.py`

## Installation

```bash
git clone https://github.com/3xC1ibR/interface-design.git

# Generic agent skills directory
ln -sfn "$(pwd)/interface-design/skills/interface-design" ~/.agents/skills/interface-design
ln -sfn "$(pwd)/interface-design/skills/design-hill-climb" ~/.agents/skills/design-hill-climb

# Claude Code (personal skills)
ln -sfn "$(pwd)/interface-design/skills/interface-design" ~/.claude/skills/interface-design
ln -sfn "$(pwd)/interface-design/skills/design-hill-climb" ~/.claude/skills/design-hill-climb
```

## Credits

- Review council format adapted from Theo Browne's T3 Code UI hill climb.
- Screenshot-only critic loop adapted from Anshu Chimala, *How to turn your AI into a world-class designer* (Lenny's Newsletter, 2026).

## License

MIT
