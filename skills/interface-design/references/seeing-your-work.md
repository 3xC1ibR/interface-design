# Seeing your work

A UI change you haven't looked at is unverified. This file covers how to capture screens on each platform, how to make captures repeatable, which states to render, and what to look for.

## Capture by platform

**Web (any framework).** Run the dev server, then use `scripts/capture_web.py CONFIG.json`. It captures every screen across viewports and light/dark themes. It can freeze `Date`, wait for fonts, disable animations, run actions (click, fill, hover, eval) to reach particular states, and clip to one element. Name screens by surface and state, for example `sidebar-empty`, so before/after sets line up. If the app themes with a class instead of `prefers-color-scheme`, set `scheme_init` to the JS that switches the theme. For logged-in apps, save a Playwright storage state once and point `storage_state` at it. If Playwright isn't installed: `pip install playwright && python -m playwright install chromium`.

**Electron.** If the renderer runs in a plain browser (it doesn't need Electron APIs in order to render), point capture_web.py at the renderer's dev URL. Otherwise, use Playwright's Electron support from Node:

```js
// capture-electron.cjs  (run: node capture-electron.cjs)
const { _electron: electron } = require('playwright');
(async () => {
  const app = await electron.launch({ args: ['.'] });
  const win = await app.firstWindow();
  await win.setViewportSize({ width: 1440, height: 900 });
  await win.screenshot({ path: '.design/shots/current/main--desktop--dark.png', animations: 'disabled' });
  await app.close();
})();
```

**Tauri and other webview shells.** Capture the frontend through its dev server with capture_web.py. Use OS-level window capture only for native chrome.

**iOS (simulator).**
- Boot, install and launch:
  - `xcrun simctl boot "<device name>"`
  - build with `xcodebuild -scheme <Scheme> -destination 'platform=iOS Simulator,name=<device name>' -derivedDataPath build build`
  - `xcrun simctl install booted build/Build/Products/Debug-iphonesimulator/<App>.app`
  - `xcrun simctl launch booted <bundle id> <launch args>`
- Make captures repeatable:
  - `xcrun simctl status_bar booted override --time 9:41 --batteryState charged --batteryLevel 100`
  - `xcrun simctl ui booted appearance dark|light`
  - on recent Xcode, `xcrun simctl ui booted content_size extra-large` (or another size) for Dynamic Type
- Reach a state with launch arguments that seed fixture data, or with a deep link: `xcrun simctl openurl booted <app-scheme>://<route>`.
- Capture with `xcrun simctl io booted screenshot <file>.png`.
- If an Xcode build MCP server (such as XcodeBuildMCP) is connected, it can build, run, screenshot and describe the UI hierarchy for you.

**iOS and SwiftUI in tests.** For deterministic renders of individual views in every state, use snapshot tests (for example pointfreeco's swift-snapshot-testing), or SwiftUI's `ImageRenderer` in a unit test. These make a good per-component state matrix. Still capture the full screen in the simulator, though: drift shows up at the screen level.

**Android.**
- Capture with `adb exec-out screencap -p > <file>.png`.
- Set dark mode with `adb shell cmd uimode night yes|no`, and font scale with `adb shell settings put system font_scale 1.3`.
- Turn off animations: `adb shell settings put global window_animation_scale 0`, and the same for `transition_animation_scale` and `animator_duration_scale`.
- Fix the status bar with demo mode: `adb shell settings put global sysui_demo_allowed 1`, then `adb shell am broadcast -a com.android.systemui.demo -e command enter` and `... -e command clock -e hhmm 0941`.
- Reach a state with a deep link: `adb shell am start -W -a android.intent.action.VIEW -d "<app-scheme>://<route>"`.
- For Compose, JVM screenshot tests (Paparazzi, Roborazzi) render previews deterministically.

**Native macOS.** Use `screencapture -o -l <windowid> <file>.png` (`-o` drops the window shadow; getting the window ID needs a small script), or capture a fixed region with `screencapture -R x,y,w,h <file>.png`. Computer use, if available in this environment, also works.

**If you genuinely cannot render.** Say so plainly, and don't describe the change as visually verified. Offer the user the capture config or commands so that they, or a later session, can verify it.

## Make captures repeatable

Critics and pixel diffs both mistake noise for change. Hold these constant between before and after:
- **Data**: fixtures or a seeded account. Use the same threads, names and counts every run, including a long name and a many-items case.
- **Time**: freeze the clock, so "2h ago" doesn't become "3h ago".
- **Fonts**: wait for them to load, since a fallback-font frame ruins a comparison.
- **Motion**: disable animations and hide carets.
- **Size**: use the same viewport and device scale.
- **Network imagery**: mock or pin avatars and remote images.
- **Randomness**: disable or seed anything random, such as greetings, tips and shuffles.

## The state matrix

For each surface you touched, render the states that apply:

| Axis | States |
|---|---|
| Data | empty, one item, typical, many (scrolling), long text (names, titles, messages that wrap) |
| Lifecycle | loading, loaded, error, offline, permission denied |
| Interaction | hover, focus (keyboard), active, selected, disabled, dragging |
| Environment | light, dark, narrow/mobile, wide, large text, reduced motion, RTL if supported |

Agents usually check one typical, light, desktop state. Drift and breakage live in the other cells.

## How to look

Open the images and review them in this order:

1. **Squint.** Run `look.py squint`. What do you see first, second and third? Does that order match what matters on this screen? If metadata, badges or icons dominate the titles, the hierarchy is wrong.
2. **Edges and alignment.** Follow the left edges down the screen. How many distinct starting x-positions are there? Each extra one needs a reason. Check that baselines line up across adjacent columns.
3. **Rhythm.** Is the vertical spacing on the grid, and is it consistent between equivalent elements? Look for doubled padding where containers nest.
4. **Count.** Count the font sizes, weights, colors and radii visible on this one screen, and compare them with the contract. Several more than the contract allows means drift.
5. **Consistency with siblings.** Compare the new element with the existing ones that do the same job. They should look identical in form.
6. **Compare with the contract's signature details.** Are they intact?
7. **Collateral.** Run `look.py diff` on screens that shouldn't have changed.
8. **Read it as a user.** What does each label say? Is any of it redundant with what's already visible?

Then put before and after side by side (`look.py sbs`) and decide honestly whether the after is better as a whole screen, not just whether the requested thing is now present.
