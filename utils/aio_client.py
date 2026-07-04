"""Thin REST client for AIO Tests for Jira.

Used by conftest.py to POST pytest results back to AIO. Credentials and
project/cycle keys come from environment variables (loaded from .env):

    AIO_BASE_URL       e.g. https://tcms.aiojiraapps.com/aio-tcms/api/v1
    AIO_API_TOKEN      access token (sent as `AioAuth <token>`)
    AIO_PROJECT_KEY    e.g. KAN
    AIO_CYCLE_KEY      cycle to push runs into, e.g. KAN-CY-Adhoc

If AIO_API_TOKEN is unset the client is disabled and all calls are no-ops,
so tests work in environments without AIO configured.
"""

from __future__ import annotations

import os
from typing import Optional

import requests


# pytest outcome -> AIO test run status (case-sensitive on the AIO side)
_STATUS_MAP = {
    "passed": "Passed",
    "failed": "Failed",
    "skipped": "Skipped",
}


def _config() -> Optional[dict]:
    token = os.getenv("AIO_API_TOKEN")
    if not token:
        return None
    return {
        "base_url": os.getenv("AIO_BASE_URL", "").rstrip("/"),
        "token": token,
        "project": os.getenv("AIO_PROJECT_KEY", ""),
        "cycle": os.getenv("AIO_CYCLE_KEY", ""),
    }


def is_enabled() -> bool:
    return _config() is not None


def map_status(pytest_outcome: str) -> Optional[str]:
    return _STATUS_MAP.get(pytest_outcome)


def post_test_run(
    case_key: str,
    status: str,
    comment: Optional[str] = None,
    effort_ms: Optional[int] = None,
    timeout: float = 10.0,
) -> Optional[int]:
    """POST a test run result for `case_key` into the configured cycle.

    Returns the new run ID on success, None on any failure or when the
    client is not configured. Never raises — reporting must not break the
    test session.
    """
    cfg = _config()
    if cfg is None:
        return None

    url = (
        f"{cfg['base_url']}/project/{cfg['project']}"
        f"/testcycle/{cfg['cycle']}/testcase/{case_key}/testrun"
    )
    payload: dict = {"testRunStatus": status}
    if comment:
        payload["comments"] = [comment[:4000]]
    if effort_ms is not None:
        payload["effort"] = effort_ms

    try:
        resp = requests.post(
            url,
            params={"createNewRun": "true"},
            json=payload,
            headers={
                "Authorization": f"AioAuth {cfg['token']}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        print(f"[AIO] POST failed for {case_key}: {exc}")
        return None

    if not resp.ok:
        print(
            f"[AIO] {case_key} -> HTTP {resp.status_code}: "
            f"{resp.text[:300]}"
        )
        return None

    try:
        return resp.json().get("ID")
    except ValueError:
        return None


def post_attachment(
    run_id: int,
    file_bytes: bytes,
    filename: str,
    mime_type: str = "image/png",
    timeout: float = 15.0,
) -> bool:
    """Attach a file (e.g. a failure screenshot) to an existing AIO test run.

    Returns True on success, False otherwise. Never raises.
    """
    cfg = _config()
    if cfg is None or run_id is None:
        return False

    url = (
        f"{cfg['base_url']}/project/{cfg['project']}"
        f"/testcycle/{cfg['cycle']}/testrun/{run_id}/attachment"
    )
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"AioAuth {cfg['token']}"},
            files={"file": (filename, file_bytes, mime_type)},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        print(f"[AIO] attachment POST failed for run {run_id}: {exc}")
        return False

    if not resp.ok:
        print(
            f"[AIO] attachment run {run_id} -> HTTP {resp.status_code}: "
            f"{resp.text[:300]}"
        )
        return False
    return True
