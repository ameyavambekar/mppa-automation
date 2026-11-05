"""
Tops up the First Appeal test data on dev, so the appeal suites (KAN-14 agency side, KAN-29 officer side)
run without skipping. See ``utils.appeal_seeder`` for what each step does.

    python -m utils.seed_appeals --dry-run          # show what is ready and what would be built
    python -m utils.seed_appeals                    # refused 5, pending 1, decided 1
    python -m utils.seed_appeals --refused 1 --pending 1 --decided 0

The counts are what should be READY after the run; only the shortfall is built. The defaults cover a full
run of tests/test_first_appeal.py with RUN_APPEAL_FILING_TESTS=true (its four filing tests use up to four
refused agencies, and one more stays for the tests that only open FORM-III). Without the filing tests,
``--refused 1`` is enough.

Refusing an application, filing an appeal and deciding one cannot be undone. Runs headless unless
HEADLESS=false; refusing takes about two minutes per agency.
"""

import argparse
import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from utils import portal_popup
from utils.appeal_seeder import AppealSeeder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refused", type=int, default=5, help="refused agencies without an appeal (default 5)")
    parser.add_argument("--pending", type=int, default=1, help="First Appeals awaiting decision (default 1)")
    parser.add_argument("--decided", type=int, default=1, help="First Appeals with an appellate order (default 1)")
    parser.add_argument("--dry-run", action="store_true", help="only report what is ready and what would be built")
    args = parser.parse_args()

    load_dotenv()
    portal_popup.install()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=os.getenv("HEADLESS", "true").lower() == "true")
        try:
            with AppealSeeder(browser) as seeder:
                seeder.top_up(args.refused, args.pending, args.decided, dry_run=args.dry_run)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
