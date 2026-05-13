# utils/state_store.py
"""
TestStateStore
==============
Local SQLite database that tracks every user the automation has registered
(across all three roles), their credentials, and the per-part status of every
Form-I application.

Why it exists
-------------
Full Pre-Registration including OTP verification is slow (testmail round-trips,
the pause between tests, etc.). Many tests need a *pre-existing* user in a
specific state — e.g. "an agency user who has completed parts A and B" — not a
fresh registration. The state store lets later tests query for what they need
instead of re-registering every time.

Usage
-----
After TC-23 generates a Registration ID::

    from utils.state_store import TestStateStore

    store = TestStateStore()
    store.record_user(
        role="agency",
        username=data.username,
        password=data.password,
        email=data.email,
        pan=data.pan_number,
        district=data.district,
        registration_id=registration_id,
    )

Reading back for later tests::

    user = TestStateStore().get_any_agency_user()
    # user.username, user.password, user.registration_id, …

The DB persists between test runs by design — it mirrors users actually
registered in the dev environment.  Delete ``state/test_state.db`` only if you
also reset the dev environment.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).parent.parent / "state" / "test_state.db"


@dataclass(frozen=True)
class UserRecord:
    """
    Immutable snapshot of one row from the ``users`` table, with the
    ``form_applications`` steps joined in as a dict.
    """
    id: int
    role: str
    username: str
    password: str
    email: Optional[str]
    pan: Optional[str]
    district: Optional[str]
    registration_id: Optional[str]
    # {"A": "completed", "B": "in_progress", …} — empty dict until Form-I starts
    steps: dict[str, str] = field(default_factory=dict)


class TestStateStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        """
         Creates tables and indexes if they do not already exist.

         Also validates that existing tables have the expected columns.
         If a stale table is detected (e.g. DB created by an older version of
         this file that lacked the ``part`` column), the table is dropped and
         recreated cleanly.  User rows are preserved when only
         ``form_applications`` is stale because the drop-recreate only targets
         the table whose schema is wrong.
         """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        EXPECTED_USERS_COLS = {
            "id", "role", "username", "password",
            "email", "pan", "district", "registration_id", "created_at",
        }
        EXPECTED_FORM_COLS = {"user_id", "part", "status", "updated_at"}

        with self._connect() as conn:
            # ── Detect and fix stale form_applications table ──────────────────
            existing_tables = {
                row[0] for row in
                conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

            if "form_applications" in existing_tables:
                actual_cols = {
                    row[1] for row in
                    conn.execute("PRAGMA table_info(form_applications)").fetchall()
                }
                if not EXPECTED_FORM_COLS.issubset(actual_cols):
                    # Stale schema — drop and let CREATE TABLE rebuild it below
                    conn.execute("DROP TABLE form_applications")

            if "users" in existing_tables:
                actual_cols = {
                    row[1] for row in
                    conn.execute("PRAGMA table_info(users)").fetchall()
                }
                if not EXPECTED_USERS_COLS.issubset(actual_cols):
                    conn.execute("DROP TABLE IF EXISTS form_applications")
                    conn.execute("DROP TABLE users")

            # ── Create tables (no-ops if already correct) ─────────────────────
            conn.executescript("""
                 CREATE TABLE IF NOT EXISTS users (
                     id              INTEGER PRIMARY KEY AUTOINCREMENT,
                     role            TEXT NOT NULL
                                     CHECK (role IN ('agency','admin','super_admin')),
                     username        TEXT NOT NULL UNIQUE,
                     password        TEXT NOT NULL,
                     email           TEXT,
                     pan             TEXT,
                     district        TEXT,
                     registration_id TEXT,
                     created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                 );

                 CREATE TABLE IF NOT EXISTS form_applications (
                     user_id     INTEGER NOT NULL
                                 REFERENCES users(id) ON DELETE CASCADE,
                     step        TEXT NOT NULL
                                 CHECK (step IN ('1','2','3','4','5','6','7','8')),
                     status      TEXT NOT NULL DEFAULT 'not_started'
                                 CHECK (status IN ('not_started','in_progress','completed')),
                     updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     PRIMARY KEY (user_id, step)
                 );

                 CREATE INDEX IF NOT EXISTS idx_users_role
                     ON users(role);

                 CREATE INDEX IF NOT EXISTS idx_form_app_status
                     ON form_applications(step, status);
             """)
    def _row_to_record(self, row: sqlite3.Row, conn: sqlite3.Connection) -> UserRecord:
        steps_rows = conn.execute(
            "SELECT step, status FROM form_applications WHERE user_id = ?", (row["id"],)
        ).fetchall()
        steps = {r["step"]: r["status"] for r in steps_rows}
        return UserRecord(
            id=row["id"],
            role=row["role"],
            username=row["username"],
            password=row["password"],
            email=row["email"],
            pan=row["pan"],
            district=row["district"],
            registration_id=row["registration_id"],
            steps=steps,
        )

    # ── Writers ───────────────────────────────────────────────────────────────

    def record_user(
        self,
        *,
        role: str,
        username: str,
        password: str,
        email: str = None,
        pan: str = None,
        district: str = None,
        registration_id: str = None,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (role, username, password, email, pan, district, registration_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    password=excluded.password,
                    email=excluded.email,
                    pan=excluded.pan,
                    district=excluded.district,
                    registration_id=excluded.registration_id
                """,
                (role, username, password, email, pan, district, registration_id),
            )
            return cursor.lastrowid

    def mark_form_step_status(self, *, username: str, step: str, status: str) -> None:
        """
               Upsert a Form-I part status for a given user.

               Call with ``status='in_progress'`` when a part is saved as draft,
               and ``status='completed'`` when it is finalised / submitted.
        """
        with self._connect() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if user is None:
                raise ValueError(f"No user found with username '{username}'")
            conn.execute(
                """
                INSERT INTO form_applications (user_id, step, status, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, step) DO UPDATE SET
                    status=excluded.status,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (user["id"], step, status),
            )

    # ── Readers ───────────────────────────────────────────────────────────────

    def get_any_agency_user(self) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE role = 'agency' LIMIT 1"
            ).fetchone()
            return self._row_to_record(row, conn) if row else None

    def get_any_admin(self) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE role = 'admin' LIMIT 1"
            ).fetchone()
            return self._row_to_record(row, conn) if row else None

    def get_any_super_admin(self) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE role = 'super_admin' LIMIT 1"
            ).fetchone()
            return self._row_to_record(row, conn) if row else None

    def get_agency_user_with_steps(self, steps: list[str]) -> Optional[UserRecord]:
        """Returns an agency user where every listed part has status='completed'."""
        with self._connect() as conn:
            placeholders = ",".join("?" * len(steps))
            row = conn.execute(
                f"""
                SELECT u.* FROM users u
                WHERE u.role = 'agency'
                  AND (
                      SELECT COUNT(*) FROM form_applications fa
                      WHERE fa.user_id = u.id
                        AND fa.step IN ({placeholders})
                        AND fa.status = 'completed'
                  ) = ?
                LIMIT 1
                """,
                (*steps, len(steps)),
            ).fetchone()
            return self._row_to_record(row, conn) if row else None

    def get_agency_user_with_step_in_status(
        self, step: str, status: str
    ) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT u.* FROM users u
                JOIN form_applications fa ON fa.user_id = u.id
                WHERE u.role = 'agency' AND fa.step = ? AND fa.status = ?
                LIMIT 1
                """,
                (step, status),
            ).fetchone()
            return self._row_to_record(row, conn) if row else None

    def get_user_by_username(self, username: str) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            return self._row_to_record(row, conn) if row else None