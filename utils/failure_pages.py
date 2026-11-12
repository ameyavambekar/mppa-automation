"""
Failure screenshots — which pages
=================================
When a test fails, the report hook in conftest.py screenshots every page the test had open. Fixtures tell this
module which pages those are:

- ``page`` registers the primary page, plus every tab or pop-up opened beside it during the test.
- ``second_browser`` registers each browser it launches; every page in that browser counts.
- A fixture that opens a page any other way registers that page itself. For example, the fake-camera browser in
  ``logged_in_premises_camera_page``.

A fixture can also name a page, as in ``register(request.node, page, "agency <username>")``, so the screenshot
says whose page it is: 'FAILED — <test> (<name>)'. A page nobody named is called after where it came from
('second browser', 'new tab'). The primary page has no name, so its screenshot keeps the old 'FAILED — <test>'.
"""

from collections import Counter

import pytest
from playwright.sync_api import Browser, Page

_ENTRIES = pytest.StashKey[list]()


def register(node: pytest.Item, page: Page, name: str = "") -> None:
    """Screenshot ``page`` if the test ``node`` (``request.node``) fails. A later name for the same page replaces
    an earlier one."""
    node.stash.setdefault(_ENTRIES, []).append(("page", name, page))


def register_browser(node: pytest.Item, browser: Browser, name: str) -> None:
    """Screenshot every page open in ``browser``, in any of its contexts, if the test ``node`` fails. Pages not
    named with ``register`` are called ``name``."""
    node.stash.setdefault(_ENTRIES, []).append(("browser", name, browser))


def pages(node: pytest.Item) -> list[tuple[str, Page]]:
    """(name, page) for each page still open, in the order the pages were registered. When several pages share a
    name, they are numbered: 'second browser 1', 'second browser 2'."""
    entries = node.stash.get(_ENTRIES, [])
    named = {id(obj): name for kind, name, obj in entries if kind == "page" and name}
    names, order = {}, []

    def add(page: Page, default: str):
        if id(page) in names or page.is_closed():
            return
        names[id(page)] = named.get(id(page), default)
        order.append(page)

    for kind, name, obj in entries:
        if kind == "page":
            add(obj, name)
            continue
        try:
            browser_pages = [p for context in obj.contexts for p in context.pages]
        except Exception:
            continue    # the browser is already gone
        for p in browser_pages:
            add(p, name)

    shared = Counter(names[id(p)] for p in order)
    seen = Counter()
    result = []
    for p in order:
        name = names[id(p)]
        if name and shared[name] > 1:
            seen[name] += 1
            name = f"{name} {seen[name]}"
        result.append((name, p))
    return result
