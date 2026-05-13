# utils/state_store.py
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).parent.parent / "state" / "test_state.db"


@dataclass(frozen=True)
class UserRecord:
    id: int
    role: str
    username: str
    password: str
    email: Optional[str]
    pan: Optional[str]
    district: Optional[str]
    registration_id: Optional[str]
    parts: dict[str, str] = field(default_factory=dict)  # {"A": "completed", ...}


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
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    role            TEXT NOT NULL CHECK (role IN ('agency','admin','super_admin')),
                    username        TEXT NOT NULL UNIQUE,
                    password        TEXT NOT NULL,
                    email           TEXT,
                    pan             TEXT,
                    district        TEXT,
                    registration_id TEXT,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS form_applications (
                    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    part        TEXT NOT NULL CHECK (part IN ('A','B','C','D','E')),
                    status      TEXT NOT NULL DEFAULT 'not_started'
                                CHECK (status IN ('not_started','in_progress','completed')),
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, part)
                );

                CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
                CREATE INDEX IF NOT EXISTS idx_form_app_status ON form_applications(part, status);
            """)

    def _row_to_record(self, row: sqlite3.Row, conn: sqlite3.Connection) -> UserRecord:
        parts_rows = conn.execute(
            "SELECT part, status FROM form_applications WHERE user_id = ?", (row["id"],)
        ).fetchall()
        parts = {r["part"]: r["status"] for r in parts_rows}
        return UserRecord(
            id=row["id"],
            role=row["role"],
            username=row["username"],
            password=row["password"],
            email=row["email"],
            pan=row["pan"],
            district=row["district"],
            registration_id=row["registration_id"],
            parts=parts,
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

    def mark_form_part_status(self, *, username: str, part: str, status: str) -> None:
        with self._connect() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if user is None:
                raise ValueError(f"No user found with username '{username}'")
            conn.execute(
                """
                INSERT INTO form_applications (user_id, part, status, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, part) DO UPDATE SET
                    status=excluded.status,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (user["id"], part, status),
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

    def get_agency_user_with_parts(self, parts: list[str]) -> Optional[UserRecord]:
        """Returns an agency user where every listed part has status='completed'."""
        with self._connect() as conn:
            placeholders = ",".join("?" * len(parts))
            row = conn.execute(
                f"""
                SELECT u.* FROM users u
                WHERE u.role = 'agency'
                  AND (
                      SELECT COUNT(*) FROM form_applications fa
                      WHERE fa.user_id = u.id
                        AND fa.part IN ({placeholders})
                        AND fa.status = 'completed'
                  ) = ?
                LIMIT 1
                """,
                (*parts, len(parts)),
            ).fetchone()
            return self._row_to_record(row, conn) if row else None

    def get_agency_user_with_part_in_status(
        self, part: str, status: str
    ) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT u.* FROM users u
                JOIN form_applications fa ON fa.user_id = u.id
                WHERE u.role = 'agency' AND fa.part = ? AND fa.status = ?
                LIMIT 1
                """,
                (part, status),
            ).fetchone()
            return self._row_to_record(row, conn) if row else None

    def get_user_by_username(self, username: str) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            return self._row_to_record(row, conn) if row else None