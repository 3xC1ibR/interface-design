# The grammar layer: conceptual models for agents

Most interface drift is not visual. It starts one layer down, when a feature is bolted on as a new thing instead of being expressed in the app's existing nouns and verbs. Visual inconsistency follows. Work at this layer first and present decisions to the user at this layer ("this is a new action on Thread, shown where the other Thread actions are"), not as widget choices ("I added a modal").

The ideas below come from a short canon of interface thinking. Each is paraphrased with the check it implies for an agent making a change.

## Quick grammar check

Run this before building any change that adds UI:

1. **Which object is this about?** Name the noun from the app's model. If no existing noun fits, you are proposing a new concept: stop and raise it with the user.
2. **Attribute, action, view or relationship?** Which one is it, and does it already exist on a sibling object?
3. **Where do this object's actions already live?** The new action goes there, in the same form, unless there is a stated reason not to.
4. **What is it called?** Use the app's existing term. Don't create a synonym; if a new term is needed, add it to the lexicon.
5. **Which layer does it belong to?** Content, controls/navigation, or a transient layer (popover, sheet, toast)? Does that layer already exist, and is it at the right elevation?
6. **Can the user do it directly** on the thing itself, reversibly, rather than through a form, a dialog or a confirmation?
7. **How does the user discover it, and what tells them it worked?** Name the signifier and the feedback.

## Concepts: Daniel Jackson, *The Essence of Software*

Software is a set of interacting **concepts**. Each concept has one purpose, its own state and actions, and an *operational principle*: the archetypal scenario showing how it fulfills that purpose (for example, "you put an item in the trash, and you can restore it until you empty the trash"). Concepts should be independent of each other and coordinated through explicit synchronizations. Typical failures:

- **Overloading**: one concept serving two purposes. For example, "archive" means both "hide" and "done".
- **Redundancy**: two concepts serving one purpose, such as tags and folders that both organize.
- **Purposeless features**: something you cannot state a purpose for.

Familiar concepts like trash, label, star, pin or undo carry user expectations, so use them with their standard behavior or don't use their names.

*Check:* state the purpose of the concept your change touches, in one sentence. Does the change serve that purpose, or smuggle in a second one? Could a user predict the new behavior from the concept's operational principle?

## Grammar and the object–action matrix: Daniel Rosenberg, *UX Magic*

The conceptual model works like a **grammar**: objects are nouns, actions are verbs, attributes are adjectives. Design patterns are how that grammar is expressed on screen. Lay the objects out as rows and the actions as columns. A sparse, irregular matrix is a direct source of cognitive load, because users have to memorize exceptions: "you can rename a project but not a thread", or "delete is in the menu here but on swipe there".

*Check:* when adding an action to one object, look across its row and its column. Should siblings get it too? Is it reached the same way everywhere? Prefer a regular matrix over a locally clever placement.

## The model before the widgets: Jeff Johnson & Austin Henderson, *Conceptual Models* (2nd ed., 2024)

The conceptual model is the objects users manipulate, their attributes and their operations. It deliberately excludes layout and widgets, and it comes first. A **lexicon** goes with it: one term for each concept, used consistently in every label, message and doc. Synonyms make users wonder whether two things are different.

*Check:* do labels, buttons, empty states and toasts all use the lexicon terms? If the code calls it a `session` but the UI says "thread", the UI wins. Don't let implementation names leak into the interface.

## Objects first: Sophia Prater, OOUX and ORCA

Model **O**bjects, **R**elationships, **C**alls-to-action and **A**ttributes before screens. Each object should have one recognizable representation (its row, card or chip) wherever it appears, and related objects should nest inside each other's views.

*Check:* does your change introduce a second visual representation of an existing object? If a Thread is a two-line row in the sidebar, it shouldn't become a card with a badge in search results unless the contract says so.

## Space, layers and elevation: Material Design 1, "Environment"

Treat the interface as a 3D space lit from above. Each surface sits at a single z-position, shadows communicate that elevation, and surfaces don't pass through one another. The elevation tells users what is on top, what is temporary and what is modal.

*Check:* the app should have a named layer stack in the contract, such as base content, raised controls, popovers, sheets and modals, and toasts. A new element takes a layer from that stack. Don't invent an ad hoc shadow or z-index.

## Controls float above content: Apple, Liquid Glass (WWDC25)

Controls and navigation form a **functional layer** that floats above the content layer. Content is primary, and chrome recedes and adapts to what's beneath it.

*Check:* decide whether the new element is content or control. Don't decorate the control layer to compete with content, and don't scatter controls through the content where the control layer already has a home for them.

## Direct manipulation: Ben Shneiderman (1983)

Direct manipulation has three properties:
- a continuous visible representation of the objects of interest;
- physical actions (click, drag, gesture) instead of typed syntax or forms;
- rapid, incremental, reversible actions whose effect is immediately visible.

*Check:* can this change happen in place, on the object itself, instead of in a dialog? Is it reversible with undo, instead of guarded by an "Are you sure?" dialog? Does the result appear where the user is looking?

## Affordances and signifiers: Don Norman, *The Design of Everyday Things* (revised edition)

**Affordances** are what an object makes possible. **Signifiers** are the cues that show people where and how to act. Good design also gives immediate **feedback**, natural **mapping** between controls and effects, and **constraints** that prevent errors. Together these close the gulfs of execution ("how do I do this?") and evaluation ("did it work?").

*Check:* every interactive element needs a signifier, but one is enough. Agents tend to over-signify, adding a label, an icon, a tooltip and a helper line all at once. Choose the lightest signifier that works in context, and make sure feedback appears within about 100 ms of the action.

## Motion that follows the hand: Apple, "Designing Fluid Interfaces" (WWDC18)

Motion should be **responsive** (it starts immediately), **interruptible** and **redirectable**, so the user can change their mind mid-gesture. It should preserve spatial continuity: things return to where they came from, and momentum carries through. Springs feel physical where fixed-duration curves feel canned.

*Check:* no transition should block input. Anything that opens should close back toward its origin, and animations should use the contract's motion tokens and respect reduced motion.

## Posture sets the chrome budget: Alan Cooper, *About Face*

An application's **posture** is how it occupies the user's attention:
- **Sovereign** apps are used full-screen for long stretches. They can be dense, use conservative chrome, and optimize for experts who learn them.
- **Transient** apps come and go for one quick job. They should be bold, simple and obvious at a glance, with large targets and little to learn.
- **Daemonic** apps run in the background and rarely need attention.
- **Auxiliary** (parasitic) apps sit beside a sovereign app.

Posture determines how much chrome and how much explanation the app can afford.

*Check:* record the posture in the contract and test changes against it. Onboarding-style labels and big empty-state illustrations bloat a sovereign tool, and expert density makes a transient one unusable. One product can contain surfaces with different postures, such as a sovereign main window and a transient quick-capture panel, so record posture per surface.

## Familiar primitives beat invention

A familiar primitive (a list, a table, a stack of cards, an outline) gives users a stronger starting point than a novel interaction, because they already know how to read it. Spend novelty only where it serves the product's core interaction, and say explicitly in the contract where that is.

## Presenting decisions at the right level

When you surface a choice to the user, frame it in grammar, then show it:

- Weak: "Should I use a modal or a popover for this?"
- Strong: "This is a new action, *Fork*, on Thread. Thread's other actions live in the row's context menu and the thread header. Option 1 puts Fork in both places, consistent with Rename and Archive (screenshot). Option 2 adds a header button, which makes it more discoverable but gives the header a fourth button (screenshot)."
