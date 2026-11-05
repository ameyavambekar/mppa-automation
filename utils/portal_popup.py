"""
The "Portal Under Testing" pop-up
=================================
Since 05-Nov-2026 every dev page opens a modal (``#tpop``, "TESTING MODULE — Portal Under Testing") 400 ms
after it loads, on top of everything (z-index 99999), so clicks on the page time out. The portal shows it
once per browser tab: closing it sets ``sessionStorage['mppa_testing_popup_seen'] = '1'``.

``install()`` makes every browser context Playwright creates from then on start with that flag set, so the
pop-up never opens during a run. conftest.py installs it for the test session; scripts that drive the portal
(``utils.seed_agencies``, ``utils.seed_appeals``) install it themselves.
"""

from playwright.sync_api import Browser, BrowserContext

POPUP_SEEN_KEY = "mppa_testing_popup_seen"
POPUP_SEEN_SCRIPT = f"try {{ sessionStorage.setItem('{POPUP_SEEN_KEY}', '1'); }} catch (e) {{}}"


def suppress_testing_popup(context: BrowserContext) -> BrowserContext:
    """Marks the pop-up as already seen in every page of ``context``."""
    context.add_init_script(POPUP_SEEN_SCRIPT)
    return context


def install() -> None:
    """Wraps ``Browser.new_context`` so every new context suppresses the pop-up. Safe to call twice."""
    if getattr(Browser.new_context, "_suppresses_testing_popup", False):
        return
    original = Browser.new_context

    def new_context(self, *args, **kwargs):
        return suppress_testing_popup(original(self, *args, **kwargs))

    new_context._suppresses_testing_popup = True
    Browser.new_context = new_context
