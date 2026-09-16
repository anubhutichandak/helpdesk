"""
app.py
------
Minimal Flask app for the helpdesk ticket queue.

Endpoints:

GET  /api/tickets
    Returns the ticket queue in the correct order.

POST /api/tickets
    Creates a new ticket.

The application also runs an automatic escalation check
when the server starts.
"""

from flask import Flask, jsonify, render_template, request

from database import (
    VALID_PRIORITIES,
    create_ticket,
    escalate_overdue_tickets,
    get_queue,
    init_db,
    is_overdue,
)

app = Flask(__name__)


@app.route("/")
def index():
    """Display the main helpdesk page."""
    return render_template("index.html")


@app.route("/api/tickets", methods=["GET"])
def list_tickets():
    """
    Return tickets in queue order.

    Overdue status is calculated and sent to the frontend.
    """

    # Run the escalation check before returning the queue.
    escalated = escalate_overdue_tickets()

    if escalated:
        print("Automatic escalation check:")

        for ticket in escalated:
            print(
                f"Ticket #{ticket['id']}: "
                f"{ticket['old_priority']} -> "
                f"{ticket['new_priority']}"
            )

    tickets = get_queue()

    for ticket in tickets:
        ticket["overdue"] = is_overdue(ticket)

    return jsonify(tickets)


@app.route("/api/tickets", methods=["POST"])
def add_ticket():
    """Create a new helpdesk ticket."""

    data = request.get_json(silent=True) or {}

    customer_name = (data.get("customer_name") or "").strip()
    subject = (data.get("subject") or "").strip()
    priority = (data.get("priority") or "").strip().lower()
    assigned_to = (data.get("assigned_to") or "").strip() or None

    errors = []

    if not customer_name:
        errors.append("Customer name is required.")

    if not subject:
        errors.append("Problem description is required.")

    if priority not in VALID_PRIORITIES:
        errors.append(
            f"Priority must be one of: "
            f"{', '.join(sorted(VALID_PRIORITIES))}."
        )

    if errors:
        return jsonify({"errors": errors}), 400

    new_id = create_ticket(
        customer_name=customer_name,
        subject=subject,
        priority=priority,
        assigned_to=assigned_to,
    )

    return jsonify({"id": new_id}), 201


def run_escalation_check():
    """
    Run one automatic escalation check when the application starts.
    """

    escalated = escalate_overdue_tickets()

    if escalated:
        print("Startup escalation check:")

        for ticket in escalated:
            print(
                f"Ticket #{ticket['id']}: "
                f"{ticket['old_priority']} -> "
                f"{ticket['new_priority']}"
            )
    else:
        print("Startup escalation check: no tickets needed escalation.")


if __name__ == "__main__":
    init_db()

    # Run one escalation check when the server starts.
    run_escalation_check()

    app.run(debug=True, port=5000)