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
After the pre-registration form is accepted by the server (TC-25)::

    from utils.state_store import TestStateStore

    store = TestStateStore()
    store.record_user(
        role="agency",
        username=data.username,
        password=data.password,
        agency_name=data.agency_name,
        email=data.email,
        mobile=data.mobile,
        alt_phone=data.alt_phone,
        pan=data.pan_number,
        district=data.district,
        city_name=data.city_name or None,      # only when district == "Other"
        registration_id=registration_id,       # None — no ID is issued at pre-registration any more
    )

Reading back for later tests::

    user = TestStateStore().get_any_agency_user()
    # user.username, user.password, user.agency_name, user.mobile, …

Form-I progress
---------------
``form_applications`` holds one row per (user, wizard step). Steps are named,
not numbered — the portal numbers them differently on different screens (the
public index counts "Create Account" as step 1, the forms count Part A as
step 1) — and run in ``FORM_STEPS`` order: part_a, part_b, part_c, part_f,
enclosures, declaration, payment.

Each row also keeps a small JSON ``data`` snapshot of what was saved, limited
to the facts later tests branch on (agency type, office state, …) — never
documents or personal details. Record a step once the portal accepts it::

    store.mark_form_step_status(
        username=user.username, step="part_a", status="completed",
        data={"legal_constitution": "Private Limited Company", "state": "Maharashtra", "branches": 0},
    )

and query by progress plus those facts::

    store.get_agency_users_with_steps(["part_a"], legal_constitution="Proprietorship")
    # user.steps == {"part_a": "completed"}; user.step_data["part_a"]["legal_constitution"]

The DB persists between test runs by design — it mirrors users actually
registered in the dev environment.  Delete ``state/test_state.db`` only if you
also reset the dev environment.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).parent.parent / "state" / "test_state.db"

# Form-I wizard steps after account creation, in the order the portal unlocks them.
FORM_STEPS = ("part_a", "part_b", "part_c", "part_f", "enclosures", "declaration", "payment")
FORM_STEP_STATUSES = ("not_started", "in_progress", "completed")

# Numbered steps written before steps were named ("1" was Part A, as in the forms' headings).
_LEGACY_STEP_NAMES = {str(i): name for i, name in enumerate(FORM_STEPS, start=1)}


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
    agency_name: Optional[str] = None
    mobile: Optional[str] = None
    alt_phone: Optional[str] = None
    city_name: Optional[str] = None     # set only when district == "Other"
    # {"part_a": "completed", "part_b": "in_progress", …} — empty dict until Form-I starts
    steps: dict[str, str] = field(default_factory=dict)
    # {"part_a": {"legal_constitution": …}, …} — only steps saved with data
    step_data: dict[str, dict] = field(default_factory=dict)


class TestStateStore:
    # Not a pytest test class — the leading 'Test' in the name otherwise makes
    # pytest try (and fail) to collect it because of the __init__ constructor.
    __test__ = False

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
         Optional user columns added after the table was first created
         (``ADDED_USERS_COLS``) are added in place with ``ALTER TABLE`` so
         existing rows survive.  Only if a *core* column is missing (e.g. a DB
         created by a much older version of this file) is the table dropped and
         recreated cleanly.  User rows are preserved when only
         ``form_applications`` is stale because the drop-recreate only targets
         the table whose schema is wrong.

         A ``form_applications`` table from before steps were named (numbered
         steps, no ``data`` column) is rebuilt with its rows carried over —
         "1" becomes "part_a" and so on (``_LEGACY_STEP_NAMES``).
         """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        EXPECTED_USERS_COLS = {
            "id", "role", "username", "password",
            "email", "pan", "district", "registration_id", "created_at",
        }
        # Redesigned pre-registration form (Oct 2026) — nullable, migrated in place.
        ADDED_USERS_COLS = {
            "agency_name": "TEXT",
            "mobile": "TEXT",
            "alt_phone": "TEXT",
            "city_name": "TEXT",
        }
        EXPECTED_FORM_COLS = {"user_id", "step", "status", "updated_at"}

        with self._connect() as conn:
            # ── Detect and fix stale form_applications table ──────────────────
            existing_tables = {
                row[0] for row in
                conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

            migrate_legacy_steps = False
            if "form_applications" in existing_tables:
                actual_cols = {
                    row[1] for row in
                    conn.execute("PRAGMA table_info(form_applications)").fetchall()
                }
                if not EXPECTED_FORM_COLS.issubset(actual_cols):
                    # Stale schema — drop and let CREATE TABLE rebuild it below
                    conn.execute("DROP TABLE form_applications")
                elif "data" not in actual_cols:
                    # Numbered steps — set aside, rows are copied back once the table is rebuilt.
                    # The index would follow the renamed table and block its re-creation below.
                    conn.execute("DROP INDEX IF EXISTS idx_form_app_status")
                    conn.execute("ALTER TABLE form_applications RENAME TO form_applications_legacy")
                    migrate_legacy_steps = True

            if "users" in existing_tables:
                actual_cols = {
                    row[1] for row in
                    conn.execute("PRAGMA table_info(users)").fetchall()
                }
                if not EXPECTED_USERS_COLS.issubset(actual_cols):
                    conn.execute("DROP TABLE IF EXISTS form_applications")
                    conn.execute("DROP TABLE users")
                else:
                    for col, col_type in ADDED_USERS_COLS.items():
                        if col not in actual_cols:
                            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")

            # ── Create tables (no-ops if already correct) ─────────────────────
            step_names = ",".join(f"'{s}'" for s in FORM_STEPS)
            status_names = ",".join(f"'{s}'" for s in FORM_STEP_STATUSES)
            conn.executescript(f"""
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
                     created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     agency_name     TEXT,
                     mobile          TEXT,
                     alt_phone       TEXT,
                     city_name       TEXT
                 );

                 CREATE TABLE IF NOT EXISTS form_applications (
                     user_id     INTEGER NOT NULL
                                 REFERENCES users(id) ON DELETE CASCADE,
                     step        TEXT NOT NULL
                                 CHECK (step IN ({step_names})),
                     status      TEXT NOT NULL DEFAULT 'not_started'
                                 CHECK (status IN ({status_names})),
                     data        TEXT CHECK (data IS NULL OR json_valid(data)),
                     updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     PRIMARY KEY (user_id, step)
                 );

                 CREATE INDEX IF NOT EXISTS idx_users_role
                     ON users(role);

                 CREATE INDEX IF NOT EXISTS idx_form_app_status
                     ON form_applications(step, status);
             """)

            if migrate_legacy_steps:
                legacy = ",".join("?" * len(_LEGACY_STEP_NAMES))
                case = " ".join(f"WHEN '{old}' THEN '{new}'" for old, new in _LEGACY_STEP_NAMES.items())
                conn.execute(
                    f"""
                    INSERT OR IGNORE INTO form_applications (user_id, step, status, updated_at)
                    SELECT user_id, CASE step {case} END, status, updated_at
                    FROM form_applications_legacy
                    WHERE step IN ({legacy})
                    """,
                    tuple(_LEGACY_STEP_NAMES),
                )
                conn.execute("DROP TABLE form_applications_legacy")
    def _row_to_record(self, row: sqlite3.Row, conn: sqlite3.Connection) -> UserRecord:
        steps_rows = conn.execute(
            "SELECT step, status, data FROM form_applications WHERE user_id = ?", (row["id"],)
        ).fetchall()
        steps = {r["step"]: r["status"] for r in steps_rows}
        step_data = {r["step"]: json.loads(r["data"]) for r in steps_rows if r["data"]}
        return UserRecord(
            id=row["id"],
            role=row["role"],
            username=row["username"],
            password=row["password"],
            email=row["email"],
            pan=row["pan"],
            district=row["district"],
            registration_id=row["registration_id"],
            agency_name=row["agency_name"],
            mobile=row["mobile"],
            alt_phone=row["alt_phone"],
            city_name=row["city_name"],
            steps=steps,
            step_data=step_data,
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
        agency_name: str = None,
        mobile: str = None,
        alt_phone: str = None,
        city_name: str = None,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (role, username, password, email, pan, district, registration_id,
                                   agency_name, mobile, alt_phone, city_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    password=excluded.password,
                    email=excluded.email,
                    pan=excluded.pan,
                    district=excluded.district,
                    registration_id=excluded.registration_id,
                    agency_name=excluded.agency_name,
                    mobile=excluded.mobile,
                    alt_phone=excluded.alt_phone,
                    city_name=excluded.city_name
                """,
                (role, username, password, email, pan, district, registration_id,
                 agency_name, mobile, alt_phone, city_name),
            )
            return cursor.lastrowid

    def mark_form_step_status(
        self, *, username: str, step: str, status: str, data: Optional[dict] = None
    ) -> None:
        """
               Upsert a Form-I step status for a given user.

               ``step`` is one of ``FORM_STEPS`` ('part_a' … 'payment'). Call with
               ``status='in_progress'`` when a step is saved as draft, and
               ``status='completed'`` when it is finalised / submitted.

               ``data`` replaces the step's stored snapshot; leave it ``None`` to
               keep what was recorded before (e.g. when only the status changes).
        """
        if step not in FORM_STEPS:
            raise ValueError(f"Unknown Form-I step '{step}' — expected one of {FORM_STEPS}")
        with self._connect() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if user is None:
                raise ValueError(f"No user found with username '{username}'")
            conn.execute(
                """
                INSERT INTO form_applications (user_id, step, status, data, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, step) DO UPDATE SET
                    status=excluded.status,
                    data=COALESCE(excluded.data, form_applications.data),
                    updated_at=CURRENT_TIMESTAMP
                """,
                (user["id"], step, status, json.dumps(data) if data is not None else None),
            )

    # ── Readers ───────────────────────────────────────────────────────────────

    # "Other" at registration carries no Maharashtra district into Part A.
    _LISTED_DISTRICT_SQL = "AND u.district IS NOT NULL AND u.district NOT IN ('', 'Other')"

    def get_any_agency_user(
        self, district: Optional[str] = None, listed_district_only: bool = False
    ) -> Optional[UserRecord]:
        """Returns any agency user — registered in ``district`` when one is given.
        ``listed_district_only`` excludes users registered with "Other" (or no district),
        i.e. users whose registration carries a Maharashtra district into Part A."""
        with self._connect() as conn:
            row = conn.execute(
                f"""SELECT * FROM users u WHERE u.role = 'agency' AND (? IS NULL OR u.district = ?)
                    {self._LISTED_DISTRICT_SQL if listed_district_only else ''} LIMIT 1""",
                (district, district),
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

    def get_agency_user_with_steps(
        self, steps: list[str], legal_constitution: Optional[str] = None
    ) -> Optional[UserRecord]:
        """Returns an agency user where every listed step has status='completed'
        (see ``get_agency_users_with_steps``)."""
        users = self.get_agency_users_with_steps(steps, legal_constitution)
        return users[0] if users else None

    def get_agency_users_with_steps(
        self, steps: list[str], legal_constitution: Optional[str] = None
    ) -> list[UserRecord]:
        """Every agency user where each listed step has status='completed', oldest first.
        ``legal_constitution`` keeps only users whose Part A was recorded with that
        agency type — it decides the key-person label and fields in Part B."""
        with self._connect() as conn:
            placeholders = ",".join("?" * len(steps))
            rows = conn.execute(
                f"""
                SELECT u.* FROM users u
                WHERE u.role = 'agency'
                  AND (
                      SELECT COUNT(*) FROM form_applications fa
                      WHERE fa.user_id = u.id
                        AND fa.step IN ({placeholders})
                        AND fa.status = 'completed'
                  ) = ?
                  AND (? IS NULL OR EXISTS (
                      SELECT 1 FROM form_applications fa
                      WHERE fa.user_id = u.id AND fa.step = 'part_a'
                        AND json_extract(fa.data, '$.legal_constitution') = ?
                  ))
                ORDER BY u.id
                """,
                (*steps, len(steps), legal_constitution, legal_constitution),
            ).fetchall()
            return [self._row_to_record(row, conn) for row in rows]

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

    def get_agency_user_with_no_form(
        self, district: Optional[str] = None, listed_district_only: bool = False
    ) -> Optional[UserRecord]:
        """Returns an agency user who has not started the Form-I wizard at all —
        registered in ``district`` when one is given. ``listed_district_only``
        excludes users registered with "Other" (see ``get_any_agency_user``)."""
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT * FROM users u
                WHERE u.role = 'agency'
                  AND (? IS NULL OR u.district = ?)
                  {self._LISTED_DISTRICT_SQL if listed_district_only else ''}
                  AND NOT EXISTS (
                      SELECT 1 FROM form_applications fa WHERE fa.user_id = u.id
                  )
                LIMIT 1
                """,
                (district, district),
            ).fetchone()
            return self._row_to_record(row, conn) if row else None