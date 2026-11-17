"""
sync_allure_to_notion.py
─────────────────────────────────────────────────────────────────────────────
Parses Allure result files from the last test run and updates the Module
Coverage database in Notion with pass/fail/skip/broken counts, pass rate,
flakiness detection, and average test duration.

Usage:
    python scripts/sync_allure_to_notion.py
    python scripts/sync_allure_to_notion.py --dry-run     # print without updating
    python scripts/sync_allure_to_notion.py --results-dir path/to/allure-results
    python scripts/sync_allure_to_notion.py --history-dir path/to/allure-html/history

Requirements:
    pip install requests python-dotenv

Authentication:
    Set NOTION_API_TOKEN in a .env file at the project root, or export it as an
    environment variable before running the script.

    echo "NOTION_API_TOKEN=secret_xxxx" > mppa-automation/.env
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ─── Optional dotenv support ─────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    _ENV_FILE = Path(__file__).parent.parent / ".env"
    if _ENV_FILE.exists():
        load_dotenv(_ENV_FILE)
except ImportError:
    pass  # dotenv not installed — rely on OS env vars

import requests

# ─── Configuration ────────────────────────────────────────────────────────────

NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN", "")
NOTION_API_BASE  = "https://api.notion.com/v1"
NOTION_VERSION   = "2022-06-28"

# Default paths relative to this script's location
_SCRIPT_DIR   = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent                         # mppa-automation/

DEFAULT_RESULTS_DIR = _PROJECT_ROOT / "reports" / "allure-results"
DEFAULT_HISTORY_DIR = _PROJECT_ROOT / "reports" / "allure-html" / "history"

# ─── Module Coverage Notion page IDs ─────────────────────────────────────────
# One row per Jira story in the Module Coverage database, keyed by story key.
# The name is only used in the printed summary; Notion rows are found by ID.
# KAN-24, 27, 28, 30 and 35 have no tests yet, so no run ever maps to them.
MODULE_PAGE_IDS: dict[str, tuple[str, str]] = {
    # Agency side
    "KAN-6":  ("Pre-Registration",              "383bcba1-5011-8125-b45e-fde7ded939e7"),
    "KAN-7":  ("Agency Login",                  "383bcba1-5011-81d1-adac-c0d0bbc8e229"),
    "KAN-8":  ("Part A: Basic Details",         "383bcba1-5011-81be-8f4d-eb0c1fae98c6"),
    "KAN-19": ("Part B: Key Persons",           "41abcba1-5011-81fd-ba65-d3b47ed1f2ef"),
    "KAN-20": ("Part C: Operations",            "41abcba1-5011-81cb-a157-fd03168ada0d"),
    "KAN-21": ("Part F: Certificates",          "41abcba1-5011-8190-acac-e8d2bb2b263c"),
    "KAN-9":  ("Enclosures",                    "41abcba1-5011-815a-838f-fe868bbf79e8"),
    "KAN-38": ("Premises Photos",               "41abcba1-5011-817e-a392-d18c3e2b28bd"),
    "KAN-10": ("Declaration & Authorization",   "41abcba1-5011-81aa-ae8a-eb5707a251ed"),
    "KAN-39": ("Application Preview",           "41abcba1-5011-818d-9074-d7181136fda5"),
    "KAN-40": ("Agency Home",                   "41abcba1-5011-81d1-a54b-e411085f4737"),
    "KAN-41": ("Notice Board",                  "41abcba1-5011-8193-9edd-c77d44a79317"),
    "KAN-42": ("Contact Us",                    "41abcba1-5011-81f3-b4f4-ed0db2808a63"),
    "KAN-43": ("Forgot Password",               "41abcba1-5011-81ca-b951-cdea78273c78"),
    "KAN-37": ("Licence Renewal (agency)",      "41abcba1-5011-81a3-9ce2-d683aafa9b8f"),
    "KAN-48": ("Compliance Loop (agency)",      "41abcba1-5011-819e-989b-fd4a31ebd250"),
    "KAN-49": ("Appeals (agency)",              "41abcba1-5011-81fc-847d-f60155632eb4"),
    # Officer side
    "KAN-23": ("Admin Login",                   "383bcba1-5011-815e-a97a-f779f53c26ac"),
    "KAN-34": ("Officers & Access",             "383bcba1-5011-815a-a3d3-efbc7866aad3"),
    "KAN-25": ("All Agencies View",             "383bcba1-5011-8178-9a81-d84bc7cacf67"),
    "KAN-29": ("First Appeal (officer)",        "383bcba1-5011-818e-b72e-f5c3e19348a4"),
    "KAN-30": ("Second Appeal (officer)",       "383bcba1-5011-81a3-859f-f35af145a57f"),
    "KAN-33": ("Licences & Certificates",       "383bcba1-5011-81a8-afb9-efe4d4af8870"),
    "KAN-31": ("Notices Management",            "383bcba1-5011-8190-b587-f00aa76c6a66"),
    "KAN-32": ("Session Management",            "383bcba1-5011-8197-baa9-c650e740b0ab"),
    "KAN-35": ("Permissions Matrix",            "383bcba1-5011-81df-8424-d2c298a26690"),
    "KAN-24": ("Admin Dashboard Overview",      "41abcba1-5011-811e-822c-cd7e99d36685"),
    "KAN-27": ("Approved Agencies",             "41abcba1-5011-816c-9bc7-f8de65ba4e62"),
    "KAN-28": ("Form-II Certificate",           "41abcba1-5011-8151-bc2c-f79ae47442b8"),
    "KAN-12": ("Desktop Scrutiny Review Loop",  "41abcba1-5011-8159-9ad3-eccd03c9ab84"),
    "KAN-36": ("Audit Log",                     "41abcba1-5011-81c1-8f25-fc0b988c06c2"),
    "KAN-44": ("Officer Notifications",         "41abcba1-5011-8132-826b-ff95d15a9c17"),
    "KAN-45": ("Registrations in Progress",     "41abcba1-5011-817c-b073-c89015c59e14"),
    "KAN-46": ("Compliance Cases",              "41abcba1-5011-816d-8c19-c0e5a719da93"),
    "KAN-47": ("District Breakup Report",       "41abcba1-5011-81fd-87dc-c559db72ff9b"),
    "KAN-50": ("Appeals Map (officer)",         "41abcba1-5011-810f-bfdb-c892af64006c"),
    "KAN-51": ("Renewal Applications",          "41abcba1-5011-81a0-a18d-c5b064459798"),
}

# Allure 'package' label (the test module's dotted path) → story key.
# The package is used rather than the 'suite' label because test_appeals_map
# exists in both tests/ and tests/admin/.
PACKAGE_TO_MODULE: dict[str, str] = {
    "tests.test_pre_registration":              "KAN-6",
    "tests.test_login":                         "KAN-7",
    "tests.test_partA":                         "KAN-8",
    "tests.test_partB":                         "KAN-19",
    "tests.test_partC":                         "KAN-20",
    "tests.test_partF":                         "KAN-21",
    "tests.test_enclosures":                    "KAN-9",
    "tests.test_premises":                      "KAN-38",
    "tests.test_declaration":                   "KAN-10",
    "tests.test_preview":                       "KAN-39",
    "tests.test_agency_home":                   "KAN-40",
    "tests.test_notice_board":                  "KAN-41",
    "tests.test_contact":                       "KAN-42",
    "tests.test_forgot_password":               "KAN-43",
    "tests.test_renewal":                       "KAN-37",
    "tests.test_first_appeal":                  "KAN-49",
    "tests.test_second_appeal":                 "KAN-49",
    "tests.test_appeals_map":                   "KAN-49",
    "tests.admin.test_admin_login":             "KAN-23",
    "tests.admin.test_admin_users":             "KAN-34",
    "tests.admin.test_agencies":                "KAN-25",
    "tests.admin.test_first_appeal_management": "KAN-29",
    "tests.admin.test_licenses":                "KAN-33",
    "tests.admin.test_notices":                 "KAN-31",
    "tests.admin.test_sessions":                "KAN-32",
    "tests.admin.test_application_review":      "KAN-12",  # see SPLIT_BY_CASE
    "tests.admin.test_audit_log":               "KAN-36",
    "tests.admin.test_notifications":           "KAN-44",
    "tests.admin.test_drafts":                  "KAN-45",
    "tests.admin.test_compliance":              "KAN-46",
    "tests.admin.test_district_breakup":        "KAN-47",
    "tests.admin.test_appeals_map":             "KAN-50",
    "tests.admin.test_renewals":                "KAN-51",
}

# Files that serve more than one story. A test's AIO case number is read from
# its Allure title ("TC-757: ..."); the first matching rule wins, and a test
# that matches no rule (or has no TC number) goes to PACKAGE_TO_MODULE.
_SHARED_REVIEW_CASES = {755, 756, 757, 758, 759, 760, 765}   # linked to KAN-12 and KAN-48
SPLIT_BY_CASE: dict[str, list[tuple[set[int], list[str]]]] = {
    "tests.admin.test_application_review": [
        (_SHARED_REVIEW_CASES,  ["KAN-12", "KAN-48"]),
        (set(range(769, 791)),  ["KAN-48"]),
    ],
}

_TC_TITLE = re.compile(r"^TC-(\d+)\b")


def modules_for(package: str, title: str) -> list[str]:
    """Story keys a result counts towards; empty when the package is unmapped."""
    for cases, keys in SPLIT_BY_CASE.get(package, []):
        m = _TC_TITLE.match(title)
        if m and int(m.group(1)) in cases:
            return keys
    module = PACKAGE_TO_MODULE.get(package)
    return [module] if module else []

# ─── Data structures ──────────────────────────────────────────────────────────

def _empty_module() -> dict:
    return {
        "passed":    0,
        "failed":    0,
        "broken":    0,
        "skipped":   0,
        "flaky":     0,
        "durations": [],    # milliseconds
    }

# ─── Parsing helpers ──────────────────────────────────────────────────────────

def load_result_files(results_dir: Path) -> list[dict]:
    """Return parsed JSON objects for every *-result.json in results_dir."""
    files = glob.glob(str(results_dir / "*-result.json"))
    if not files:
        print(f"[WARN] No result files found in {results_dir}", file=sys.stderr)
    results = []
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                results.append(json.load(f))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[WARN] Skipping {path}: {exc}", file=sys.stderr)
    return results


def load_history(history_dir: Path) -> dict[str, dict]:
    """
    Load allure-html/history/history.json.

    Returns a dict keyed by historyId.  Each value is the full history entry
    with a 'statistic' and an 'items' list (one entry per historical run).
    Returns an empty dict if the file doesn't exist.
    """
    path = history_dir / "history.json"
    if not path.exists():
        print(f"[INFO] history.json not found at {path} — flakiness will be 0.", file=sys.stderr)
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def detect_flaky_ids(history: dict[str, dict]) -> set[str]:
    """
    A test is considered flaky if across all recorded runs it has appeared
    with at least two different statuses where one was 'passed'.
    Requires history to contain data from ≥ 2 runs.
    """
    flaky = set()
    for hist_id, data in history.items():
        items = data.get("items", [])
        if len(items) < 2:
            continue  # insufficient history
        statuses = {item.get("status") for item in items}
        if len(statuses) > 1 and "passed" in statuses:
            flaky.add(hist_id)
    return flaky


# ─── Aggregation ──────────────────────────────────────────────────────────────

def aggregate(
    result_files: list[dict],
    flaky_ids: set[str],
) -> dict[str, dict]:
    """
    Group test results by story and accumulate counts + durations.

    allure-results is cleaned at the start of each run_tests.cmd run, but a
    direct pytest call appends to it, so a test may appear more than once.
    Only its latest result (by historyId) is counted.

    Returns:
        { story_key: { passed, failed, broken, skipped, flaky, durations } }
    """
    latest: dict[str, dict] = {}
    for r in result_files:
        key = r.get("historyId") or r.get("fullName") or r.get("uuid", "")
        if key not in latest or r.get("start", 0) > latest[key].get("start", 0):
            latest[key] = r

    modules: dict[str, dict] = defaultdict(_empty_module)
    unmapped: dict[str, int] = defaultdict(int)

    for r in latest.values():
        labels  = {lbl["name"]: lbl["value"] for lbl in r.get("labels", [])}
        package = labels.get("package", "")
        keys    = modules_for(package, r.get("name", ""))
        if not keys:
            unmapped[package or labels.get("suite", "?")] += 1
            continue

        status   = r.get("status", "unknown")
        start_ms = r.get("start", 0)
        stop_ms  = r.get("stop", 0)
        hist_id  = r.get("historyId", "")

        for key in keys:
            m = modules[key]
            m[status] = m.get(status, 0) + 1
            if stop_ms > start_ms:
                m["durations"].append(stop_ms - start_ms)
            if hist_id in flaky_ids:
                m["flaky"] += 1

    for package, count in sorted(unmapped.items()):
        print(f"[WARN] Unmapped package '{package}' — {count} result(s) skipped. Add it to PACKAGE_TO_MODULE.")

    return modules


# ─── Run-status helper ────────────────────────────────────────────────────────

def run_status(data: dict) -> str:
    if data["failed"] > 0:
        return "❌ Has Failures"
    if data["broken"] > 0:
        return "⚠️ Has Broken"
    if data["skipped"] > 0:
        return "⏭️ Has Skipped"
    if data["passed"] > 0:
        return "✅ All Pass"
    return "— Not Run"


# ─── Reliability helper ───────────────────────────────────────────────────────

def reliability_status(data: dict) -> str | None:
    """
    Update the manual Reliability field only when we have clear signal.
    Returns None to leave the field unchanged when uncertain.
    """
    if data["flaky"] > 0:
        return "Flaky"
    if data["failed"] == 0 and data["broken"] == 0:
        return "Stable"
    return None  # do not overwrite — failures ≠ flakiness


# ─── Notion API helpers ───────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    return {
        "Authorization":  f"Bearer {NOTION_API_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type":   "application/json",
    }


def update_notion_page(page_id: str, properties: dict) -> dict:
    """PATCH a Notion page's properties."""
    url  = f"{NOTION_API_BASE}/pages/{page_id}"
    body = {"properties": properties}
    resp = requests.patch(url, headers=_headers(), json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()


def build_notion_properties(data: dict, run_date: str) -> dict:
    """
    Convert aggregated module data into a Notion property update payload.

    `run_date`  ISO-8601 date string, e.g. '2026-06-18'
    """
    total = data["passed"] + data["failed"] + data["broken"] + data["skipped"]
    pass_rate = round(data["passed"] / total, 4) if total else 0.0  # 0–1 for Notion percent
    avg_dur   = (
        round(sum(data["durations"]) / len(data["durations"]) / 1000, 2)
        if data["durations"] else 0.0
    )
    reliability = reliability_status(data)

    props: dict = {
        "Last Run: Passed":  {"number": data["passed"]},
        "Last Run: Failed":  {"number": data["failed"]},
        "Last Run: Broken":  {"number": data["broken"]},
        "Last Run: Skipped": {"number": data["skipped"]},
        "Pass Rate %":       {"number": pass_rate},
        "Flaky Tests":       {"number": data["flaky"]},
        "Avg Duration (s)":  {"number": avg_dur},
        "Last Run Date":     {"date": {"start": run_date}},
        "Run Status":        {"select": {"name": run_status(data)}},
    }
    if reliability is not None:
        props["Reliability"] = {"select": {"name": reliability}}

    return props


# ─── Reporting ────────────────────────────────────────────────────────────────

def print_summary(modules: dict[str, dict]) -> None:
    header = f"{'Story':<40} {'Pass':>5} {'Fail':>5} {'Brkn':>5} {'Skip':>5} {'Flky':>5} {'Rate':>6} {'AvgDur':>8}  Status"
    print("\n" + header)
    print("─" * len(header))
    for key in sorted(modules, key=lambda k: int(k.split("-")[1])):
        d = modules[key]
        label = f"{key} {MODULE_PAGE_IDS.get(key, ('?', ''))[0]}"
        total = d["passed"] + d["failed"] + d["broken"] + d["skipped"]
        rate  = f"{d['passed']/total*100:.1f}%" if total else "—"
        avg   = f"{sum(d['durations'])/len(d['durations'])/1000:.2f}s" if d["durations"] else "—"
        print(
            f"{label:<40} {d['passed']:>5} {d['failed']:>5} {d['broken']:>5} "
            f"{d['skipped']:>5} {d['flaky']:>5} {rate:>6} {avg:>8}  {run_status(d)}"
        )
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sync Allure results → Notion Module Coverage")
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR,
                   help="Path to allure-results/ directory")
    p.add_argument("--history-dir", type=Path, default=DEFAULT_HISTORY_DIR,
                   help="Path to allure-html/history/ directory")
    p.add_argument("--dry-run", action="store_true",
                   help="Print aggregated metrics without calling the Notion API")
    # Local date: a UTC date would be the previous day for runs before 05:30 IST.
    p.add_argument("--run-date", default=datetime.now().strftime("%Y-%m-%d"),
                   help="Override run date (ISO-8601, e.g. 2026-06-18)")
    return p.parse_args()


def main() -> None:
    # The Windows console defaults to cp1252, which cannot print ─, ✓ or the
    # Run Status emoji.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    args = parse_args()

    if not args.dry_run and not NOTION_API_TOKEN:
        print(
            "[ERROR] NOTION_API_TOKEN is not set.\n"
            "  Add it to mppa-automation/.env  →  NOTION_API_TOKEN=secret_xxxx\n"
            "  or run with --dry-run to preview without updating Notion.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[INFO] Results dir : {args.results_dir}")
    print(f"[INFO] History dir : {args.history_dir}")
    print(f"[INFO] Run date    : {args.run_date}")
    print(f"[INFO] Mode        : {'DRY RUN' if args.dry_run else 'LIVE UPDATE'}")

    result_files = load_result_files(args.results_dir)
    print(f"[INFO] Loaded {len(result_files)} result file(s).")

    history   = load_history(args.history_dir)
    flaky_ids = detect_flaky_ids(history)
    print(f"[INFO] Flaky test IDs detected: {len(flaky_ids)}")

    modules = aggregate(result_files, flaky_ids)

    if not modules:
        print("[WARN] No results mapped to any story. Check PACKAGE_TO_MODULE.")
        sys.exit(0)

    print_summary(modules)

    if args.dry_run:
        print("[DRY RUN] No Notion pages were updated.")
        return

    # ── Live update ──────────────────────────────────────────────────────────
    updated = 0
    skipped = 0
    errors  = 0

    for key, data in modules.items():
        if key not in MODULE_PAGE_IDS:
            print(f"[WARN] No Notion page ID configured for '{key}' — skipping.")
            skipped += 1
            continue
        name, page_id = MODULE_PAGE_IDS[key]

        props = build_notion_properties(data, args.run_date)
        try:
            update_notion_page(page_id, props)
            print(f"  ✓  {key} {name}")
            updated += 1
        except requests.HTTPError as exc:
            print(f"  ✗  {key} {name}: {exc.response.status_code} {exc.response.text[:120]}")
            errors += 1

    print(f"\n[DONE] Updated {updated}, skipped {skipped}, errors {errors}.")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
