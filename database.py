"""
database.py
-----------
Everything about storing tickets and getting them back out IN THE RIGHT ORDER.

Design:
- SQLite file `helpdesk.db` sitting next to this file.
- One table: tickets.
- `due_at` is computed once, at creation time, from the priority's response-time
  window.
- Overdue tickets are automatically escalated by one priority level per run.
- The queue ordering is:
    1. Overdue tickets
    2. Priority
    3. Nearest due time
    4. Oldest ticket
"""

import sqlite3
from datetime import datetime, timedelta, UTC
from pathlib import Path

DB_PATH = Path(__file__).parent / "helpdesk.db"

# Response time for each priority.
RESPONSE_WINDOWS = {
    "urgent": timedelta(hours=2),
    "high": timedelta(hours=8),
    "normal": timedelta(hours=24),
    "low": timedelta(hours=72),
}

# Lower number = more important.
PRIORITY_RANK = {
    "urgent": 1,
    "high": 2,
    "normal": 3,
    "low": 4,
}

VALID_PRIORITIES = set(PRIORITY_RANK)
VALID_STATUSES = {"open", "in_progress", "closed"}


def now_iso() -> str:
    """Return the current UTC time."""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def compute_due_at(priority: str, created_at: str) -> str:
    """Calculate the response deadline based on priority."""
    created_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    due_dt = created_dt + RESPONSE_WINDOWS[priority]
    return due_dt.strftime("%Y-%m-%d %H:%M:%S")


def get_connection() -> sqlite3.Connection:
    """Create a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create the tickets table if it does not already exist."""
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            subject       TEXT NOT NULL,
            description   TEXT DEFAULT '',
            priority      TEXT NOT NULL CHECK (
                priority IN ('urgent','high','normal','low')
            ),
            status        TEXT NOT NULL DEFAULT 'open' CHECK (
                status IN ('open','in_progress','closed')
            ),
            assigned_to   TEXT DEFAULT NULL,
            created_at    TEXT NOT NULL,
            due_at        TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def create_ticket(
    customer_name: str,
    subject: str,
    priority: str,
    description: str = "",
    assigned_to: str | None = None,
    created_at: str | None = None,
) -> int:
    """Insert a new ticket and calculate its response deadline."""

    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {priority}")

    created_at = created_at or now_iso()
    due_at = compute_due_at(priority, created_at)

    conn = get_connection()

    cur = conn.execute(
        """
        INSERT INTO tickets (
            customer_name,
            subject,
            description,
            priority,
            status,
            assigned_to,
            created_at,
            due_at
        )
        VALUES (?, ?, ?, ?, 'open', ?, ?, ?)
        """,
        (
            customer_name,
            subject,
            description,
            priority,
            assigned_to,
            created_at,
            due_at,
        ),
    )

    conn.commit()

    new_id = cur.lastrowid

    conn.close()

    return new_id


def escalate_overdue_tickets() -> list[dict]:
    """
    Automatically escalate overdue tickets by exactly ONE priority level.

    Escalation rules:

        low    -> normal
        normal -> high
        high   -> urgent
        urgent -> urgent

    Only open/in-progress tickets are considered.

    IMPORTANT:
    A ticket can move only one level during a single run.
    """

    current_time = now_iso()

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT id, priority
        FROM tickets
        WHERE due_at < ?
          AND status != 'closed'
        """,
        (current_time,),
    ).fetchall()

    escalated = []

    for row in rows:
        ticket_id = row["id"]
        current_priority = row["priority"]

        escalation_map = {
            "low": "normal",
            "normal": "high",
            "high": "urgent",
            "urgent": "urgent",
        }

        new_priority = escalation_map[current_priority]

        # Urgent cannot be escalated further.
        if new_priority == current_priority:
            continue

        conn.execute(
            """
            UPDATE tickets
            SET priority = ?
            WHERE id = ?
            """,
            (new_priority, ticket_id),
        )

        escalated.append(
            {
                "id": ticket_id,
                "old_priority": current_priority,
                "new_priority": new_priority,
            }
        )

    conn.commit()
    conn.close()

    return escalated


def get_queue(include_closed: bool = False) -> list[dict]:
    """
    Return tickets in the order they should be handled:

    1. Overdue tickets first
    2. Urgent > High > Normal > Low
    3. Nearest due time
    4. Oldest ticket
    """

    conn = get_connection()

    where_clause = "" if include_closed else "WHERE status != 'closed'"

    rows = conn.execute(
        f"""
        SELECT *,
            CASE
                WHEN due_at < ? AND status != 'closed' THEN 0
                ELSE 1
            END AS overdue_rank,

            CASE priority
                WHEN 'urgent' THEN 1
                WHEN 'high'   THEN 2
                WHEN 'normal' THEN 3
                WHEN 'low'    THEN 4
            END AS priority_rank

        FROM tickets

        {where_clause}

        ORDER BY
            overdue_rank ASC,
            priority_rank ASC,
            due_at ASC,
            created_at ASC
        """,
        (now_iso(),),
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def is_overdue(ticket: dict) -> bool:
    """
    Check whether a ticket has passed its response deadline.
    Closed tickets are never considered overdue.
    """

    if ticket["status"] == "closed":
        return False

    return ticket["due_at"] < now_iso()


def clear_all_tickets() -> None:
    """Delete all tickets. Used for reseeding demo data."""

    conn = get_connection()

    conn.execute("DELETE FROM tickets")

    conn.commit()
    conn.close()