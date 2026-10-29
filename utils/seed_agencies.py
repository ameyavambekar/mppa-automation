"""
Tops up the pool of agencies waiting at a Form-I stage, so a large test run
doesn't spend its time building them one by one in the fixtures.

    python -m utils.seed_agencies --stage part_f --count 11
    python -m utils.seed_agencies --stage part_a --count 2 --legal-constitution Proprietorship

``--count`` is the number that should be ready: agencies already waiting at
``--stage`` (saved up to it, next step untouched) are counted first and only the
shortfall is built. Runs headless unless HEADLESS=false.
"""

import argparse
import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from utils.agency_builder import COMPANY, STAGES, AgencyBuilder, available


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", required=True, choices=STAGES[1:], help="last step the agencies should have saved")
    parser.add_argument("--count", type=int, required=True, help="agencies that should be waiting at --stage")
    parser.add_argument("--legal-constitution", default=COMPANY,
                        help=f"Part A agency type (only for --stage part_a; default {COMPANY})")
    args = parser.parse_args()

    load_dotenv()
    ready = len(available(args.stage, args.legal_constitution))
    missing = max(args.count - ready, 0)
    print(f"{ready} agencies already waiting at {args.stage}; building {missing}.")
    if not missing:
        return
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=os.getenv("HEADLESS", "true").lower() == "true")
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        context.set_default_timeout(30000)
        builder = AgencyBuilder(context.new_page())
        for n in range(1, missing + 1):
            user = builder.build(args.stage, args.legal_constitution)
            print(f"  {n}/{missing}: {user.username} ({user.district})")
        browser.close()
    print(f"{len(available(args.stage, args.legal_constitution))} agencies now waiting at {args.stage}.")


if __name__ == "__main__":
    main()
