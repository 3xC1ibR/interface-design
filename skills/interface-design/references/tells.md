# Drift smells and AI tells in product UI

Use this list during the subtraction pass, during self-review, and when briefing a critic. Each item is a common way interfaces degrade under repeated agent edits, or a mark of a machine-made default. None of them is always wrong. Each is a question to answer: is this a choice for this product, or a default?

## Hierarchy

- **Metadata louder than titles.** Colored project chips, branch names, timestamps and provider logos pull the eye before the thing the row is about. Titles should be the strongest element in a row, and metadata should share one quiet secondary style.
- **Whole-row opacity used to mean "read" or "inactive".** It makes the titles look disabled. Quiet individual pieces of metadata instead, and keep titles legible.
- **Everything emphasized.** Bold, color and size have all been applied to many elements, so none of them stands out. Each view should have one primary element.
- **More than one primary button** in a view, or primary styling on something reversible and routine.
- **Accent color as decoration.** If the accent appears on icons, borders and headings, it no longer means "act here" or "you are here".

## Chrome and labels

- **Labels on everything.** Section headers above single items, "Name:" in front of a value that is obviously a name, helper text restating the placeholder.
- **Triple signifiers.** Icon, text label, tooltip and helper line on a single control.
- **Containers doing no work.** Cards inside cards, a border around a section that already has a heading, a background panel holding one element.
- **Badges and counts by default.** "New", "Beta", "3" pills that nobody asked for.
- **A divider between every item**, where spacing alone would group them.
- **Toolbars that grow by one button with each feature.** New actions belong in the object's existing action surfaces, such as the context menu, the header or keyboard shortcuts.

## Values and consistency

- **Near-duplicate values.** Two grays 3% apart, 6/8/10/12px radii side by side, 13px and 14px body text in neighboring components. `drift_check.py inventory` finds these.
- **Off-grid spacing**, such as 7px, 13px or 18px, in an otherwise 4px system.
- **A new variant per feature.** A fourth button style, a third kind of list row, a second toast system.
- **Mixed icon styles.** Outline and filled icons, or icons of different stroke widths, from different sets on one screen. Emoji used as icons.
- **Inconsistent radii by nesting level.** Children need smaller radii than their parent containers, or the corners look off.
- **Hard-coded colors that break dark mode**: white text on a light hover state, or shadows invisible on dark backgrounds.

## Interaction model

- **A modal for everything.** Pickers, confirmations and settings all open dialogs, when in-place editing, a popover or undo would do.
- **"Are you sure?" on reversible actions.** Offer undo instead.
- **Toasts for things already visible.** A "Saved!" toast when the UI already shows the saved state.
- **Synonyms.** The same thing is called "thread", "conversation" and "chat" on different screens.
- **Irregular action placement.** Rename lives in a context menu on one object and in a header button on its sibling.

## Generic aesthetics (mostly in new designs)

- Purple or blue gradient washes, glows, glassmorphism with no reason behind it.
- The SaaS card kit: everything chopped into identical rounded cards with the same soft shadow.
- Centered empty states with a huge line-art icon, a heading such as "No items yet", and a paragraph of encouragement. A useful empty state tells people what goes here and gives them the action to start.
- Tracked-out all-caps eyebrow labels over every heading. Numbered "01 / 02 / 03" markers on content that isn't a sequence.
- Fade-and-slide-up entrance animation on every section, and hover lift on every card.
- Custom controls imitating native ones on iOS and Android, done worse than the native ones.

## Copy

- Buttons labeled "Submit" or "OK" instead of the action they perform. An action whose name changes between the button and its confirmation ("Publish" leading to "Post created").
- Errors that apologize or are vague instead of saying what happened and how to fix it.
- Implementation words leaking into the UI, such as "session", "payload" or "webhook config".
