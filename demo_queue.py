"""
demo_queue.py
-------------
Prints the queue exactly as get_queue() returns it, so you can eyeball
that the ordering rules are actually being applied correctly.
"""

from database import get_queue, is_overdue

def main():
    tickets = get_queue()
    print(f"{'#':<3}{'ID':<4}{'Customer':<20}{'Priority':<9}{'Overdue':<9}{'Due At':<21}{'Subject'}")
    print("-" * 100)
    for i, t in enumerate(tickets, start=1):
        overdue = "YES" if is_overdue(t) else "no"
        print(
            f"{i:<3}{t['id']:<4}{t['customer_name']:<20}{t['priority']:<9}"
            f"{overdue:<9}{t['due_at']:<21}{t['subject']}"
        )
    print(f"\n{len(tickets)} tickets in live queue (closed tickets excluded).")

if __name__ == "__main__":
    main()
