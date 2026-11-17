"""
Prepares desktop scrutiny test data on dev for the agency-side compliance tests (KAN-48). See
``utils.review_seeder``.

    python -m utils.seed_review --dry-run                       # show what is ready and what would be built
    python -m utils.seed_review --untouched 2 --compliance-1 2  # two awaiting corrections, two more untouched
    python -m utils.seed_review --park-hearing                  # park one agency at the hearing (TC-770)

--untouched is the number of untouched submissions to leave after the run; --compliance-1 is how many of the
untouched ones are sent Compliance 1 (awaiting corrections). Only the shortfall is built.

Runs headless unless HEADLESS=false. Sending notices and building applications cannot be undone on dev.
"""

import argparse
import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from utils import portal_popup
from utils.review_seeder import ReviewSeeder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--untouched", type=int, default=2, help="untouched submissions to leave (default 2)")
    parser.add_argument("--compliance-1", type=int, default=2,
                        help="untouched submissions to send Compliance 1 to (default 2)")
    parser.add_argument("--park-hearing", action="store_true", help="park one agency at the hearing (TC-770)")
    parser.add_argument("--dry-run", action="store_true", help="only report what would be built and sent")
    args = parser.parse_args()

    load_dotenv()
    portal_popup.install()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=os.getenv("HEADLESS", "true").lower() == "true")
        try:
            with ReviewSeeder(browser) as seeder:
                seeder.top_up(args.untouched, args.compliance_1, park_hearing=args.park_hearing,
                              dry_run=args.dry_run)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
