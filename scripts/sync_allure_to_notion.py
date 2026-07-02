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
import sys
from collections import defaultdict
from datetime import datetime, timezone
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
# One page ID per module row in the Module Coverage database.
MODULE_PAGE_IDS: dict[str, str] = {
    "Pre-Registration":        "383bcba1-5011-8125-b45e-fde7ded939e7",
    "Agency Login":            "383bcba1-5011-81d1-adac-c0d0bbc8e229",
    "Application Step 1":      "383bcba1-5011-81be-8f4d-eb0c1fae98c6",
    "Admin Login":             "383bcba1-5011-815e-a97a-f779f53c26ac",
    "User Management":         "383bcba1-5011-815a-a3d3-efbc7866aad3",
    "Agencies Management":     "383bcba1-5011-8178-9a81-d84bc7cacf67",
    "First Appeal Management": "383bcba1-5011-818e-b72e-f5c3e19348a4",
    "License Management":      "383bcba1-5011-81a8-afb9-efe4d4af8870",
    "Notices":                 "383bcba1-5011-8190-b587-f00aa76c6a66",
    "Session Management":      "383bcba1-5011-8197-baa9-c650e740b0ab",
    "Permissions Matrix":      "383bcba1-5011-81df-8424-d2c298a26690",
    "Second Appeal Management":"383bcba1-5011-81a3-859f-f35af145a57f",
}

# Allure 'suite' label value → Module Coverage row name
SUITE_TO_MODULE: dict[str, str] = {
    "test_pre_registration":         "Pre-Registration",
    "test_login":                    "Agency Login",
    "test_step1":                    "Application Step 1",
    "test_admin_login":              "Admin Login",
    "test_admin_users":              "User Management",
    "test_agencies":                 "Agencies Management",
    "test_first_appeal_management":  "First Appeal Management",
    "test_licenses":                 "License Management",
    "test_notices":                  "Notices",
    "test_sessions":                 "Session Management",
}

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
    Group test results by module and accumulate counts + durations.

    Returns:
        { module_name: { passed, failed, broken, skipped, flaky, durations } }
    """
    modules: dict[str, dict] = defaultdict(_empty_module)

    for r in result_files:
        labels = {lbl["name"]: lbl["value"] for lbl in r.get("labels", [])}
        suite  = labels.get("suite", "")
        module = SUITE_TO_MODULE.get(suite)
        if not module:
            print(f"[DEBUG] Unmapped suite '{suite}' — skipping '{r.get('name', '')}'")
            continue

        status   = r.get("status", "unknown")
        start_ms = r.get("start", 0)
        stop_ms  = r.get("stop", 0)
        hist_id  = r.get("historyId", "")

        m = modules[module]
        m[status] = m.get(status, 0) + 1
        if stop_ms > start_ms:
            m["durations"].append(stop_ms - start_ms)
        if hist_id in flaky_ids:
            m["flaky"] += 1

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
    header = f"{'Module':<32} {'Pass':>5} {'Fail':>5} {'Brkn':>5} {'Skip':>5} {'Flky':>5} {'Rate':>6} {'AvgDur':>8}  Status"
    print("\n" + header)
    print("─" * len(header))
    for mod in sorted(modules):
        d = modules[mod]
        total = d["passed"] + d["failed"] + d["broken"] + d["skipped"]
        rate  = f"{d['passed']/total*100:.1f}%" if total else "—"
        avg   = f"{sum(d['durations'])/len(d['durations'])/1000:.2f}s" if d["durations"] else "—"
        print(
            f"{mod:<32} {d['passed']:>5} {d['failed']:>5} {d['broken']:>5} "
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
    p.add_argument("--run-date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                   help="Override run date (ISO-8601, e.g. 2026-06-18)")
    return p.parse_args()


def main() -> None:
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
        print("[WARN] No results mapped to any module. Check SUITE_TO_MODULE mapping.")
        sys.exit(0)

    print_summary(modules)

    if args.dry_run:
        print("[DRY RUN] No Notion pages were updated.")
        return

    # ── Live update ──────────────────────────────────────────────────────────
    updated = 0
    skipped = 0
    errors  = 0

    for module, data in modules.items():
        page_id = MODULE_PAGE_IDS.get(module)
        if not page_id:
            print(f"[WARN] No Notion page ID configured for module '{module}' — skipping.")
            skipped += 1
            continue

        props = build_notion_properties(data, args.run_date)
        try:
            update_notion_page(page_id, props)
            print(f"  ✓  {module}")
            updated += 1
        except requests.HTTPError as exc:
            print(f"  ✗  {module}: {exc.response.status_code} {exc.response.text[:120]}")
            errors += 1

    print(f"\n[DONE] Updated {updated}, skipped {skipped}, errors {errors}.")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
