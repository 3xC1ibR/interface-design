# Create mode: new designs

Use this file for a new app, a new screen or feature with no existing pattern, or a deliberate new direction. The core problem is that a language model makes the most probable choice at every step, so an unguided design is the average of everything it has seen. The process below adds variety from outside the model, then converges with an outside judge. It is loosely a double diamond: discover, define, deliver. Much of it follows Anshu Chimala's "How to turn your AI into a world-class designer" (Lenny's Newsletter, 2026) and Felix Rieseberg's "How to be more ambitious" (2026).

## 0. Ground it

Pin down five things before any styling:
- **Subject**: what the product is and works with.
- **Audience**: who uses it.
- **Job**: the primary job of this surface.
- **Platform**: web, desktop, iOS or Android, and which of the platform's conventions users will expect.
- **Posture**: sovereign, transient, auxiliary or daemonic (see `conceptual-model.md`).

Propose answers yourself when the brief is thin, then confirm them.

If a `frontend-design` skill is available, load it now. It is the best source of aesthetic direction and of the generic defaults to avoid. This file covers the process around it.

**Native platforms:** on iOS and Android, start from native components and the platform's type, spacing and navigation. Custom controls that imitate native ones almost always look worse than the real ones. Spend customization on content, imagery and the signature moment instead.

## 1. Model before pixels

Draft the conceptual model: objects, attributes, actions, concepts with their purposes, and a lexicon. Agree on it with the user at this level, the same way you'd agree on a schema before writing queries. Wrong nouns and verbs can't be fixed by visual polish later.

Use **altitude** here: ask what the user is ultimately trying to achieve, beyond the screen they asked for. Sometimes the right design removes the screen. For example, a review queue might become an automatic summary with exceptions flagged, instead of a list to page through.

Use **range**: describe the surface with verbs rather than nouns. "A settings page" becomes "letting someone change how the app behaves, confidently and reversibly". Then ask which fields know most about those verbs: game UI, instrument panels, editorial layout, wayfinding, music software. Borrow their *methods*, not their costume.

## 2. Discover: diverge for real

Asking for "something unique" or "random choices" doesn't work, because the model produces text that *sounds* random while making the same predictable choices. Variety has to come from outside the model.

- **Seed strings.** Generate a long random string in the shell (for example `head -c 32 /dev/urandom | base64`) and derive the creative direction from it: palette, type, layout and motifs, found in its sub-patterns and numbers. Don't show the string in the design. This is Sakana AI's "String Seed of Thought" technique applied to design.
- **Concrete, ambitious directions.** Name a real-world inspiration and say how it should shape the product: an industrial control panel with tactile, satisfying controls; an isometric city where features are neighborhoods; a radically asymmetric editorial layout. Ideas that sound like they can't work are often the most useful to try.
- **Help the user find their direction.** List many directions in one line each, broad rather than deep. Render the user's favorites, collect their reactions ("tactile yes, cartoonish no"), sharpen, and repeat. Their reactions supply the taste the model lacks.
- **Explore in parallel.** Build 3 to 5 directions at once, with subagents on separate branches or worktrees, then capture and present them side by side. Agent labor is cheap, so treat it that way.

Show directions as rendered images, never as paragraphs describing them.

## 3. Define: deepen one direction

Initial AI designs still lean on stale structures, such as a navbar on top, text on the left with a CTA, and a graphic on the right. Give the chosen direction its own identity:

- **Iterate against a critic, not yourself.** Capture screenshots, then send them to a fresh-context critic that never sees the code or earlier critiques. Give it a stable brief:
  - evaluate the aesthetic the design is reaching for;
  - imagine how a top studio would execute it;
  - name the biggest gaps;
  - penalize overdone or machine-made patterns;
  - score against a bar.

  A ranking against 3 or 4 professional reference images is more stable than an abstract score. Use the strongest available model as the critic, since it makes few calls, and a cheaper model to implement. Keep the stopping threshold out of the critic's prompt so it scores honestly, and check for convergence after one or two rounds before committing to more. The design-hill-climb skill runs this loop with blinding, a panel of critics and a regression gate.
- **Use real assets.** Coding agents default to gradients, shapes and CSS patterns because that's what code can do, and those are some of the clearest tells. If image generation is available (a built-in tool, an API key the user provides, or another CLI), generate imagery, textures or illustrations that belong to this direction. Never commit keys; keep them in a gitignored env file. Video models can produce looping animated graphics with keyed-out backgrounds, or interpolated transitions between two UI states that are scrubbed by scroll or gesture.
- **Insist on professional instruments (depth).** Measure contrast ratios instead of guessing, set type to a real scale and line length, build motion with springs and interruptibility, and check alignment edges in screenshots. Taking on a professional's vocabulary without their methods doesn't improve the result.
- **Decide the signature.** Pick the one or two things this design will be remembered for, and keep everything around them quiet.

## 4. Deliver: polish by subtraction

AI designs over-explain and over-decorate, and the model won't remove things unprompted because deleting feels risky. So most polish is removal:

- Remove glows, gradients, decorative color, random text highlights and unneeded containers.
- Remove labels that the content or imagery already makes obvious.
- Replace custom controls that are worse than the platform's own.
- Tighten type: often smaller, simpler and fewer weights.

Then work through `tells.md`.

Next, build to the quality floor without announcing it:
- every state (empty, loading, error, long content, many items);
- responsive down to the smallest target;
- visible keyboard focus;
- reduced motion respected;
- WCAG contrast;
- dynamic type on iOS.

## 5. Write the contract

Create mode isn't finished until DESIGN.md exists (template in `design-contract.md`), with tokens in code, the conceptual model, posture, layers, components, signature details and a never-list. This is what keeps the design intact through its first hundred edits.

## Keep a record of what didn't work

Save the prompts and directions that failed, and why. Models improve quickly; retry the ambitious ideas that failed when a new model ships, rather than assuming the old limits still hold.
