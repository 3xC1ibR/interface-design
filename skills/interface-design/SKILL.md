---
name: interface-design
description: Design and change user interfaces for web, desktop, iOS and Android apps without drift. Use for ANY UI/UX work, including designing a new app, screen, feature or visual direction; adding or changing a button, panel, setting, list, sidebar, modal, empty state or flow in an existing app; restyling; fixing a UI that "looks off" or has slowly gotten worse; making mockups or exploring options. Also use it for feature work whose diff touches UI code (components, styles, views, screens), even when the request never mentions design. Use it even for small UI edits, because small edits are where apps drift. Covers the DESIGN.md contract, conceptual-model checks, screenshot verification and subtraction. For multi-round scored audits against reference apps, use design-hill-climb.
---

# Interface Design

## Required reading before design

Before designing or changing any UI—including a new app, screen, feature UI, restyle, or small edit—open and read Anshu Chimala's [How to turn your AI into a world-class designer](https://www.lennysnewsletter.com/p/how-to-turn-your-ai-into-a-world) (Lenny's Newsletter, September 1, 2026). Apply its relevant guidance in the workflow below; do not treat the link as optional background. Read it once per working context, before choosing a direction or editing UI code. Include this requirement when handing design work to another agent.

If fetching fails or a subscription gate limits access, read what is accessible, use this brief paraphrase, and state the access limitation in the work report. The public text checked on November 24, 2026 covers techniques 1–6; technique 7 begins behind the subscription gate.

Chimala's actionable guidance, summarized from that public portion:

- Explore distinct directions using outside inspiration or shell-generated random seeds.
- Make the brief specific and ambitious; refine it through the user's reactions.
- Use independent screenshot critics and professional references; keep feedback concrete and iteration bounded.
- Consider generated imagery and motion where they strengthen the direction; inspect the rendered result.
- Polish by removing redundant explanation, decoration, and unnecessary custom controls.

**Apply within this skill's contract.** Exploration belongs to Create mode or an explicitly requested redesign. Change mode preserves DESIGN.md, existing tokens and component conventions; the article does not authorize unrelated restyling. Deliberate system-level changes enter through the contract before implementation. Generated assets must serve the product's job and accessibility needs. Screenshot verification, state coverage, and subtraction remain required. Use the existing blind-critique protocol and stopping rules rather than importing an example score target from the article. Treat its model-specific examples and capability claims as dated observations, not permanent limits.

Agents fail at interface work in two opposite ways.

On a blank canvas they **converge on the generic**: the most probable layout, palette and component kit, because each design decision is the likeliest next token.

On an existing app they **diverge**: one more label, a new gray, a fourth button style, a modal where an inline control would do. Each edit is locally reasonable. After twenty of them the app "seems off" even though no single change was wrong.

This skill treats those as two different jobs with one shared backbone: a written design contract, a conceptual model, and actually looking at the result.

## Pick the mode first

| Situation | Mode | Posture |
|---|---|---|
| No UI exists for this surface yet, or the user asks for a new direction, a redesign, or options | **Create**: read `references/create-mode.md` | Diverge, then converge. Take risks in one place. |
| Anything that touches an existing interface, however small | **Change**: the workflow below | Converge on the contract. Novelty is a cost. |
| "Audit this", "score it against X", "polish until it's great", several rounds of improvement | **design-hill-climb** skill | A measured loop with blind critics |

A redesign of an existing surface is Create for the direction and Change for the integration. New ideas are welcome inside that surface, but they enter through the contract: update DESIGN.md first, then build. They should not arrive as one-off values.

Keep the postures apart. The creative push that rescues a new design ("be bold, be distinctive") is exactly what causes drift in an existing one.

## Work at the frontier of what you can do

Agents routinely undersell themselves in design work. They fall back to editing code blind and to describing options in prose. Calibrate up:

- **You can see.** Render the UI and look at it before calling any visual change done; a diff is not a design review. `scripts/capture_web.py` covers web. `references/seeing-your-work.md` covers Electron, the iOS simulator and Android.
- **Looking is cheap, so look broadly.** Check whole screens rather than single components, in every relevant state, not only the happy path.
- **You can explore in parallel.** When a decision has real alternatives, build 2 to 4 variants (with subagents, branches or worktrees), render them, and compare. Exploration that once cost a designer a day now costs minutes.
- **Show; don't ask in prose.** When a choice belongs to the human (taste, direction, a new concept), present rendered options side by side. For continuous qualities like shadow, radius or easing, build a small live tuning page wired to the real component. Nobody can judge a shadow described as "soft vs. crisp".
- **Don't grade your own work.** You know the intent behind the code, so you see what you meant rather than what is on screen. For anything non-trivial, use a fresh-context critic that sees only images.
- **Check the environment before assuming what's missing.** Look for a browser driver, a simulator, subagents and image generation. Use what is there, and say plainly what isn't.
- **Aim at the best product in the category, not at "it renders".** Model capabilities move fast. If you catch yourself assuming something is out of reach (a polished animation, a generated asset, a custom control), try it before saying so.

## The design contract: DESIGN.md

Drift is mostly amnesia. Each session re-derives spacing, colors and patterns from whichever file it happens to open, so the values multiply. The fix is a persistent contract in the repo that every UI change reads first.

- Look for `DESIGN.md` at the repo root, or in `docs/` or `design/`. Read it before any UI change.
- If none exists and the task is more than trivial, bootstrap one from the app as it stands. `references/design-contract.md` has the template and the procedure, and `scripts/drift_check.py inventory` measures the values actually in use. Show the user the draft: it encodes taste decisions, so it is theirs to approve.
- The contract holds more than tokens: the conceptual model (objects, actions, concepts and their names), the application's posture, the layer stack, the component inventory, the signature details that give the app its identity, a never-list, and a dated decision log.
- The token front matter follows Google's open DESIGN.md format, so `npx @google/design.md lint DESIGN.md` can check references and contrast when it is available.
- Change the contract only when a change is deliberately system-level: a new token, component or concept. Log the decision with a one-line reason, and never let the code and the contract disagree silently.
- **Keep anchor screenshots.** When the contract is approved, capture the key screens into `.design/shots/anchor/`. Before/after comparisons only catch drift *within* one edit; the anchor catches drift *across* many. After a few UI changes, or at the end of any session with several, compare the current screens with the anchor (`look.py sbs`/`diff`, and the anchor as a third image for the blind critic). Re-capture the anchor only when the user approves an intended change of direction.
- **Make the contract hard to miss.** Skills don't always load, so when you bootstrap a contract, add one line to the repo's CLAUDE.md or AGENTS.md: "Before any UI change, read DESIGN.md and follow the interface-design skill (contract, tokens, screenshots)". Offer a pre-commit hook running `drift_check.py diff --staged`. Add `.design/shots/` to .gitignore.

## Change workflow

Every change is a change to the whole screen. The component you edit is a few dozen lines of code, but the user experiences the screen it sits in, so work at that level.

1. **Read and look.** Read DESIGN.md. Capture the affected screens before touching code (`capture_web.py CONFIG --out .design/shots/before`), in every relevant viewport and theme, and look at them. Note what currently carries the emphasis. If the code is already edited, capture "before" from a `git worktree` of HEAD.

2. **Place the change in the grammar.** Before thinking about pixels, say what the change *is* in the app's conceptual model. It is one of these, in order of preference:
   - a new attribute of an existing object;
   - a new action on an existing object;
   - a new view of existing objects;
   - a new relationship;
   - a new concept.

   Take the earliest one that works. A new concept, a new top-level surface or a new modal is a design decision, so raise it with the user instead of slipping it in. Check the object–action matrix: an action that exists on one object should usually exist on its siblings, in the same place. See `references/conceptual-model.md`.

3. **Reuse before inventing.** Find how the app already does this job: the same kind of control, list row, empty state, confirmation or menu. Use that component and variant. A new variant needs a reason you can state in one sentence, and it goes in the contract.

4. **Spend emphasis from a budget.** Each view has one primary thing.
   - A new element enters at the lowest emphasis that still works. Reach for position and order before size, size before weight, weight before color, and color before decoration.
   - If it truly needs more emphasis, take emphasis away from something else, and say what.
   - Chrome must fit the app's posture. A sovereign tool used all day can be dense and quiet; a transient one must read at a glance.

5. **Build with tokens only.** No literal colors, sizes, radii, shadows, z-indexes or durations outside the token files. Run `python3 scripts/drift_check.py diff`, then fix or justify every finding. If the user agrees, add `drift_check.py diff --staged` to a pre-commit hook so the check doesn't depend on anyone remembering it.

6. **Render the states.** For every affected surface, render:
   - default, empty, loading and error;
   - long content (long names, many items, wrapped text);
   - narrow and wide;
   - light and dark;
   - hover, focus, selected and disabled.

   Agents usually render one happy state. The drift hides in the others.

7. **Compare.** Capture the same screens with `--out .design/shots/after`.
   - Put before and after side by side with `scripts/look.py sbs .design/shots/before .design/shots/after --out .design/shots/sbs`.
   - Run `look.py diff` on screens that should *not* have changed. Collateral changes there are regressions.
   - Run `look.py squint` on the after image. In a blurred render, the most prominent thing should be the most important thing.

8. **Subtract.** Before finishing, remove something: a label the context already supplies, a border or container doing no work, a duplicated affordance, a color used only as decoration. AI-built interfaces fail by accretion far more often than by omission, and `references/tells.md` lists the usual suspects.

9. **Get a blind opinion on anything non-trivial.** Run `look.py blind BEFORE.png AFTER.png`. It writes A.png, B.png and AB.png to a fresh folder in random order, and prints the key only to you. Spawn a fresh subagent, give it that folder (no code, no rationale), and ask:
   - which image better serves the screen's purpose;
   - what looks off in each;
   - what concrete fix it would make, with numbers.

   Then tell it which image is new, and ask what regressed. Act on what you agree with, and have a reason for anything you reject.

10. **Report with pictures.** Show the user before and after images, name any contract changes, and list anything you noticed but deliberately left alone.

Match the ceremony to the change: a copy fix doesn't need a critic. Steps 1, 5 and 7 still apply to every visual change, though, because skipping them is how drift accumulates.

## Create mode, in brief

The full process is in `references/create-mode.md`. In short:

- **Ground it.** Establish the subject, the audience, the primary job, the platform and the posture. If a `frontend-design` skill is available, load it for aesthetic direction; this skill handles the process around it.
- **Model before pixels.** Draft the objects, actions and concepts, and agree on them with the user at that level, the way you'd agree on a schema before writing queries.
- **Diverge for real.** Seed variety from outside the model, for example a random string from the shell or a concrete inspiration from another field. Render several directions in parallel and let the user steer by reacting to them.
- **Spend novelty in one place.** Put it into the signature interaction or visual idea, and use familiar platform primitives everywhere else. A familiar primitive is a stronger starting point than an invention.
- **Converge with an outside judge.** Iterate against a fresh-context critic; design-hill-climb runs the full loop.
- **Deliver by subtraction.** Then handle every state and the quality floor: contrast, focus, reduced motion, responsiveness and dynamic type.
- **Finish by writing DESIGN.md.** A new design without a contract starts drifting on the first edit.

## Asking the user

Ask about direction, taste and new concepts. Decide execution details yourself, from the contract. When you do ask, show rendered options, and never ask the user to evaluate something you could evaluate by looking.

## Files in this skill

- `references/conceptual-model.md`: the grammar layer (objects, actions, concepts, posture, layers, direct manipulation, signifiers, motion), distilled from the classic sources into checks an agent can run. Read it for step 2, and whenever a change adds a concept or surface.
- `references/design-contract.md`: the DESIGN.md template and how to bootstrap one from an existing app.
- `references/create-mode.md`: the full Create process (discover, define, deliver).
- `references/seeing-your-work.md`: capture on web, Electron, iOS and Android; deterministic screenshots; the state matrix; how to look.
- `references/tells.md`: drift smells and AI tells in product UI, to check during subtraction and critique.
- `scripts/capture_web.py CONFIG.json`: deterministic screenshots across screens, viewports and color schemes (needs Playwright). Start from `assets/capture-example.json`.
- `scripts/look.py sbs|diff|squint|blind`: side-by-side comparisons, pixel diffs with changed regions, the squint test, and blind A/B pairs for a critic (needs Pillow).
- `scripts/drift_check.py diff|inventory`: flags literal style values in your change, and measures how many distinct values the app already uses.

Run the scripts with the skill directory as the path prefix, for example `python3 <skill-dir>/scripts/look.py ...`.
