# Configuration and workspace

## config.json fields

| Field | Meaning | Default |
|---|---|---|
| `product` | Product name, used in the reveal message and on the board. | "the product" |
| `context` | A neutral description of the product, its users and the purpose of each screen. Critics read this. Never put targets, scores or what changed here. | — |
| `platform` | For example "iOS, light and dark", or "desktop Electron, dark". | — |
| `screens` | Capture filename stems (without `.png`) that are scored each round. If empty, every capture except the holdout is scored. | all |
| `holdout` | Stems scored only in the `--final` round, to check that gains generalize. Capture them in round 0 too, so the baseline has them. | [] |
| `references` | `{"Name": "dir"}`: directories of reference screenshots. The filenames should say what each screen is (`sidebar.png`, `empty-state.png`). | {} |
| `vocabulary` | Path to DESIGN.md. It is copied into each packet, minus its decision log and history sections, so critics can express specs in token and component names without seeing the product's history. | none |
| `categories` | Scoring categories. Overall is always added. | Typography, Hierarchy, Spacing & density, Color & contrast, Iconography, Consistency & polish, Clarity |
| `min_gain` | The Overall improvement over the best accepted round needed to accept a round. Set it to at least twice the critic noise you saw in round 0. | 0.15 |
| `max_category_drop` | The largest drop in any single category that a round may cause and still be accepted. | 0.3 |
| `target_gap` | Stop with "target reached" once the best reference beats the product by no more than this on Overall. Use 0 for parity, or a negative value to require surpassing it. | 0.0 |
| `plateau_rounds` | Stop after this many consecutive rounds without an accept. | 2 |
| `max_rounds` | The round budget. | 8 |
| `fixes_per_round` | Guidance for batch size. Smaller batches make it clearer what helped. | 3 |

Changing `context`, `platform`, `categories`, `screens` or `references` changes the brief hash. Rounds scored under different briefs aren't comparable, so `score_round.py` warns about it. Start a new round 0 in that case.

## Workspace layout

```
.design/hill-climb/
  config.json
  baseline/                  # product captures from round 0 (the fixed comparison point)
  references/<name>/         # reference screenshots
  rounds/rNN/
    labels.json              # per critic: packet path, letter -> identity, reveal text
    current/                 # this round's product captures
    changes.md               # one line per change made this round
    critic-1.md critic-2.md  # each critic's two replies, saved verbatim
    verdict.json             # medians, deltas, verdict, merged fixes
  state.json                 # accepted rounds and their deltas, cumulative Keep list
  scoreboard.md              # one row per round, regenerated from state.json
  board.html                 # gallery.py output
  archive/<timestamp>/       # earlier climbs moved aside by --reset

<system temp>/design-review-XXXX/   # one packet per critic, outside the workspace
  BRIEF.md  VOCABULARY.md  (REVEAL.md only with --one-pass)
  candidates/A/ B/ C/...    # this critic's own shuffle of product, baseline, references
```

Keep `.design/hill-climb/` out of the per-round code commits, so reverting a round never deletes its record. Gitignoring it is simplest. If the user wants the history in git, commit `config.json`, `scoreboard.md` and the references separately from the code.

## Choosing screens

- Cover the surfaces users spend the most time on, plus one empty state and one dense or long-content state.
- Use both themes if the product ships both, because problems often hide in one of them.
- Use one viewport per platform unless responsive behavior is in scope.
- Keep it to 10 screens or fewer. Critics' attention degrades with very large packets, so it's better to run focused climbs on different surfaces.

## Choosing references

- Pick products in the same category and posture. A dense developer tool should be compared with dense developer tools, not with landing pages.
- Use comparable screens: a sidebar for a sidebar, settings for settings.
- Use 2 to 4 of them. One reference becomes a target to copy; many dilute the bar.
- The user's own picks are best, because references are how their taste enters the loop.

## Running critics

- In Claude Code or similar harnesses, spawn each critic as a subagent with the printed prompt, at the strongest model tier, and run the panel in parallel. When each critic returns its Step 1 scores, send it the printed follow-up message (the reveal) by continuing that same subagent.
- If other model families are available, for example through another CLI or API the user has set up, use one critic from each. Different models notice different problems.
- Save each critic's full reply. Only the final JSON block is parsed, but the prose is useful when you merge fixes.
- Never send a critic the diff, the code, `changes.md`, earlier critiques or the scoreboard.
