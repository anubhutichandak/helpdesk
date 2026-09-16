"""
seed.py
-------
Populates the DB with demo tickets specifically chosen to exercise every
rule in the ordering logic:
  - some overdue, some not
  - same-priority tiebreaks by due_at
  - same-priority-and-due_at tiebreaks by created_at (age)
  - a closed ticket (should never appear in the live queue)

Run with: python seed.py
"""

from datetime import datetime, timedelta, UTC
from database import init_db, clear_all_tickets, create_ticket, get_connection, now_iso

def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def main():
    init_db()
    clear_all_tickets()
    now = datetime.now(UTC)

    # --- Overdue tickets (created far enough in the past that their window has passed) ---
    create_ticket(
        "Acme Corp", "Laptop won't boot before client demo", "urgent",
        description="Dell XPS won't POST, demo in 30 min",
        assigned_to="priya",
        created_at=iso(now - timedelta(hours=5)),   # urgent window = 2h -> overdue by 3h
    )
    create_ticket(
        "Globex", "VPN drops every few minutes", "normal",
        assigned_to="sam",
        created_at=iso(now - timedelta(hours=30)),  # normal window = 24h -> overdue by 6h
    )
    create_ticket(
        "Initech", "Printer offline", "low",
        created_at=iso(now - timedelta(hours=80)),  # low window = 72h -> overdue by 8h
    )

    # --- Not overdue, spread across priorities ---
    create_ticket(
        "Umbrella Inc", "Second monitor request", "low",
        assigned_to="sam",
        created_at=iso(now - timedelta(hours=1)),
    )
    create_ticket(
        "Wayne Enterprises", "Email sync broken on mobile", "high",
        created_at=iso(now - timedelta(hours=1)),
    )
    create_ticket(
        "Stark Industries", "New hire laptop setup", "normal",
        assigned_to="priya",
        created_at=iso(now - timedelta(minutes=30)),
    )

    # --- Two URGENT tickets, not overdue, to test the due_at tiebreak ---
    # Both created "now", but we stagger created_at slightly so due_at differs.
    create_ticket(
        "Pied Piper", "Production API down for one client", "urgent",
        assigned_to="priya",
        created_at=iso(now - timedelta(minutes=10)),  # due sooner
    )
    create_ticket(
        "Hooli", "Urgent: exec's monitor flickering", "urgent",
        assigned_to="sam",
        created_at=iso(now - timedelta(minutes=5)),   # due a bit later
    )

    # --- Closed ticket: must NOT show up in the live queue ---
    tid = create_ticket(
        "Massive Dynamic", "Old ticket, already resolved", "urgent",
        created_at=iso(now - timedelta(hours=48)),
    )
    conn = get_connection()
    conn.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (tid,))
    conn.commit()
    conn.close()

    print("Seeded demo tickets.")

if __name__ == "__main__":
    main()
