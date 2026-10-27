#!/usr/bin/env python3
"""Capture deterministic screenshots of a web UI across screens, viewports and color schemes.

Usage:
  python3 capture_web.py CONFIG.json [--out DIR] [--only NAME[,NAME...]] [--base-url URL]

Output files are named  <screen>--<viewport>--<scheme>.png  so before/after sets line up
for look.py and the hill-climb scripts.

Config: JSON; a complete example is in ../assets/capture-example.json. Keys:
  base_url, out_dir            where the app runs; where PNGs go (--out overrides)
  viewports                    {"desktop": [1440, 900], "mobile": [390, 844]}
  color_schemes                ["light", "dark"] (emulates prefers-color-scheme)
  scheme_init                  {"dark": "<JS>"} run before page scripts, for apps themed by class
  device_scale_factor          1 or 2
  storage_state                Playwright storage-state file for a logged-in session
  freeze_time                  ISO time; fixes Date so "2h ago" doesn't change between runs
  wait_ms                      settle time after load and actions
  screens[]                    {"name", "path", optional: "wait_for" (selector), "full_page",
                                "clip" (selector: capture one element), "before" (JS run once,
                                then reload), "actions" (list of single-key objects: click,
                                hover, focus, fill [sel, text], type [sel, text], press, eval,
                                wait_for, wait_ms, scroll [sel|null, y]), "viewports",
                                "color_schemes" (limit this screen to some of them)}

Requires: pip install playwright && python -m playwright install chromium
"""
import argparse
import json
import sys
from pathlib import Path


def run_actions(page, actions):
    for action in actions or []:
        if not isinstance(action, dict) or len(action) != 1:
            raise ValueError(f"each action must be a single-key object, got {action!r}")
        (kind, arg), = action.items()
        if kind == "click":
            page.click(arg)
        elif kind == "hover":
            page.hover(arg)
        elif kind == "focus":
            page.focus(arg)
        elif kind == "fill":
            selector, text = arg
            page.fill(selector, text)
        elif kind == "type":
            selector, text = arg
            page.locator(selector).press_sequentially(text)
        elif kind == "press":
            page.keyboard.press(arg)
        elif kind == "eval":
            page.evaluate(arg)
        elif kind == "wait_for":
            page.wait_for_selector(arg, timeout=10000)
        elif kind == "wait_ms":
            page.wait_for_timeout(int(arg))
        elif kind == "scroll":
            page.evaluate("([s, y]) => { const el = s ? document.querySelector(s) : window; el.scrollTo(0, y); }", arg)
        else:
            raise ValueError(f"unknown action '{kind}'")


def settle(page, wait_ms):
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass  # dev servers with open sockets never go idle; carry on
    try:
        page.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true")
    except Exception:
        pass
    page.wait_for_timeout(wait_ms)


FREEZE_FALLBACK = """
(() => {
  const fixed = new Date(%s).getTime();
  const RealDate = Date;
  class FrozenDate extends RealDate {
    constructor(...a) { super(...(a.length ? a : [fixed])); }
    static now() { return fixed; }
  }
  window.Date = FrozenDate;
})();
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config")
    ap.add_argument("--out", help="output directory (overrides config out_dir)")
    ap.add_argument("--only", help="comma-separated screen names to capture")
    ap.add_argument("--base-url", help="overrides config base_url")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    base_url = (args.base_url or cfg.get("base_url", "")).rstrip("/")
    out_dir = Path(args.out or cfg.get("out_dir", ".design/shots/current"))
    out_dir.mkdir(parents=True, exist_ok=True)
    viewports = cfg.get("viewports") or {"desktop": [1440, 900]}
    schemes = cfg.get("color_schemes") or ["light"]
    scheme_init = cfg.get("scheme_init") or {}
    dsf = cfg.get("device_scale_factor", 1)
    wait_ms = int(cfg.get("wait_ms", 250))
    freeze = cfg.get("freeze_time")
    only = set(args.only.split(",")) if args.only else None
    screens = [s for s in cfg.get("screens", []) if not only or s["name"] in only]
    if not screens:
        sys.exit("no screens to capture (check 'screens' in the config or --only)")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright is not installed: pip install playwright && python -m playwright install chromium")

    written, failed = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for vp_name, (w, h) in viewports.items():
            for scheme in schemes:
                todo = [s for s in screens
                        if vp_name in s.get("viewports", [vp_name]) and scheme in s.get("color_schemes", [scheme])]
                if not todo:
                    continue
                ctx_kwargs = dict(viewport={"width": w, "height": h}, device_scale_factor=dsf,
                                  color_scheme=scheme, reduced_motion="reduce")
                if cfg.get("storage_state"):
                    ctx_kwargs["storage_state"] = cfg["storage_state"]
                ctx = browser.new_context(**ctx_kwargs)
                if freeze:
                    try:
                        ctx.clock.set_fixed_time(freeze)
                    except Exception:
                        ctx.add_init_script(FREEZE_FALLBACK % json.dumps(freeze))
                if scheme in scheme_init:
                    ctx.add_init_script(scheme_init[scheme])
                for s in todo:
                    name = f"{s['name']}--{vp_name}--{scheme}.png"
                    target = out_dir / name
                    page = ctx.new_page()
                    try:
                        url = s["path"] if s["path"].startswith("http") else base_url + s["path"]
                        page.goto(url, wait_until="load", timeout=30000)
                        if s.get("before"):
                            page.evaluate(s["before"])
                            page.reload(wait_until="load")
                        settle(page, wait_ms)
                        if s.get("wait_for"):
                            page.wait_for_selector(s["wait_for"], timeout=10000)
                        run_actions(page, s.get("actions"))
                        page.wait_for_timeout(int(s.get("wait_ms", wait_ms)))
                        shot = dict(path=str(target), animations="disabled", caret="hide")
                        if s.get("clip"):
                            page.locator(s["clip"]).first.screenshot(**shot)
                        else:
                            page.screenshot(full_page=bool(s.get("full_page")), **shot)
                        written.append(target)
                    except Exception as e:  # keep going; report at the end
                        failed.append((name, str(e).splitlines()[0]))
                    finally:
                        page.close()
                ctx.close()
        browser.close()

    for t in written:
        print(f"wrote {t}")
    for name, err in failed:
        print(f"FAILED {name}: {err}", file=sys.stderr)
    print(f"{len(written)} captured, {len(failed)} failed -> {out_dir}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
