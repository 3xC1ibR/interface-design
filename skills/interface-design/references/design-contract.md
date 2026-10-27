# DESIGN.md: the design contract

A design contract gives every future agent session the same memory of the product: what it is, how it is modeled, what values it uses, and what makes it feel like itself. It is the difference between the seventh edit fitting in and the seventh edit inventing a new gray.

## Where values live

- If the code already has token files (CSS custom properties, a Tailwind theme, a `Theme.swift`, a Compose theme), **those stay the source of truth for implementation values**. DESIGN.md mirrors the semantic set in its front matter and adds the rationale and rules. Keep the two in sync; when you add a token, add it in both places.
- If the code has no token files, create them as part of the bootstrap. A contract that no code reads is a wish.
- The YAML front matter follows Google's open DESIGN.md format (colors, typography, rounded, spacing, components; components can reference tokens like `{colors.primary}`). Use the spec's section names, in its order (Overview, Colors, Typography, Layout, Elevation & Depth, Shapes, Components, Do's and Don'ts), so other tools can read the file. Put this skill's extra sections after them. Where `npx @google/design.md` is available, `lint` checks references and contrast, `diff` compares two versions, and `export --format tailwind|dtcg` produces token files. Its "orphaned token" warnings for colors no component references are expected and fine. The format is still evolving, so check `npx @google/design.md spec` for the current schema before relying on optional keys.

## Template

```markdown
---
name: <Product>
colors:
  primary: "#..."       # the one accent: primary action and current selection
  bg: "#..."            # semantic roles, not hues
  surface: "#..."
  fg: "#..."
  fg-muted: "#..."
  border: "#..."
  danger: "#..."
  success: "#..."
typography:
  title:    { fontFamily: <Family>, fontSize: 14px, fontWeight: 500, lineHeight: 20px }
  body:     { fontFamily: <Family>, fontSize: 14px, lineHeight: 20px }
  meta:     { fontFamily: <Family>, fontSize: 12px, lineHeight: 16px }
  heading:  { fontFamily: <Family>, fontSize: 20px, fontWeight: 600, lineHeight: 28px }
rounded:
  sm: 4px
  md: 8px
spacing:
  1: 4px
  2: 8px
  3: 12px
  4: 16px
  6: 24px
components:
  list-row:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.fg}"
---

## Overview
What the product is, who uses it, and for what, in two or three sentences. The feeling it
should give, in a phrase. Themes and platforms.
Posture, per surface: sovereign / transient / auxiliary / daemonic, and what that means here
(density, chrome budget, how much explanation is acceptable).

## Colors
What each role means and where it may appear. Primary marks the one primary action or the
current selection, never decoration. Status colors carry status only.

## Typography
Roles and rules. Example: "Titles are the strongest element in a row. Metadata is quieter than
titles in every state, including unread." Fonts actually shipped, with the weights that exist:
a weight with no font file renders as the nearest one.

## Layout
Grid unit, regions (for example sidebar, content, inspector, composer) and what belongs in
each. Row heights and density. Padding rules for containers versus rows.

## Elevation & Depth
The layer stack, bottom to top: content, controls, popovers, sheets/modals, toasts. The
elevation and shadow token for each, and what may live on each layer.

## Shapes
Radius per nesting level (children smaller than parents), border widths, icon set and stroke.

## Components
| Component | Variants | Use for | Don't use for |
|---|---|---|---|

## Do's and Don'ts
Explicit rules for this product, including the never-list. Example: "no badges on list rows",
"no modal for anything reversible", "no gradients".

## Conceptual model
### Objects
| Object | Key attributes | Actions | Canonical representation | Appears in |
|---|---|---|---|---|

### Object–action matrix
|        | Create | Rename | Archive | Delete | Share | ... |
|--------|--------|--------|---------|--------|-------|-----|
| Thread | ✓ (cmd-N, sidebar +) | ✓ (context menu, header) | ... |

### Concepts
| Concept | Purpose (one sentence) | Operational principle |
|---|---|---|

### Lexicon
| Term | Means | Never call it |
|---|---|---|

## Motion
Duration and easing tokens. What animates and what never does. Reduced-motion behavior.

## States
How empty, loading, error, offline and permission-denied look in this product.

## Signature details
The three to five specific things that make this product feel like itself. Protect them.

## Decision log
| Date | Decision | Why | Who |
|---|---|---|---|
```

## Bootstrapping a contract from an existing app

Do this when an app has no DESIGN.md and you are about to make non-trivial UI changes, or when the user asks for one.

1. **Capture the app.** Take screenshots of the key screens in each theme and viewport (`scripts/capture_web.py`, or the platform methods in `seeing-your-work.md`). Look at all of them before writing anything.
2. **Measure what's in use.** Run `python3 scripts/drift_check.py inventory`. It reports distinct colors (with near-duplicate clusters), font sizes, radii and spacing values, and how many sit outside token files. This is the app's de facto system, drift included. Near-duplicate clusters can be false alarms when a light-theme value and a dark-theme value happen to sit close together.
3. **Find the token files**, if any, and read them.
4. **Choose the canonical set.** For each role, take the most-used on-grid value and list the near-duplicates it should absorb. Don't silently refactor the app while bootstrapping; record consolidation as a proposed migration.
5. **Write the conceptual model** from the data model, routes and UI. The objects are the nouns users see. The actions are everything in buttons, menus, shortcuts and gestures. Fill in the object–action matrix and mark its irregularities, which are often where the UX is confusing.
6. **Name the posture and the signature details** from the screenshots: what is distinctive and worth protecting.
7. **Mark guesses.** Tag anything you inferred rather than found as `(proposed)`, and show the user the draft with screenshots. Taste is theirs to confirm.
8. **Once approved**, capture the anchor set (`.design/shots/anchor/`), add the DESIGN.md line to CLAUDE.md or AGENTS.md, and offer the pre-commit drift check.

## Keeping it alive

- Read it at the start of every UI task.
- Add a decision-log line when you add a token, component, variant or concept, or when you break a rule on purpose.
- When code and contract disagree, don't pick one silently. Say which is right, and fix the other.
- If a rule keeps getting broken for good reasons, the rule is wrong. Propose changing it.
