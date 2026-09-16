const tableWrapper = document.querySelector(".table-scroll");
const tableBody = document.getElementById("ticket-table-body");
const emptyState = document.getElementById("empty-state");
const loadError = document.getElementById("load-error");
const form = document.getElementById("ticket-form");
const formError = document.getElementById("form-error");
const submitBtn = document.getElementById("submit-btn");
const refreshBtn = document.getElementById("refresh-btn");

function formatDueDate(isoString) {
    // isoString looks like "2026-09-16 06:27:01" (stored as UTC, no offset marker)
    const date = new Date(isoString.replace(" ", "T") + "Z");
    return date.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function renderTickets(tickets) {
    tableBody.innerHTML = "";

    if (tickets.length === 0) {
        tableWrapper.hidden = true;
        emptyState.hidden = false;
        return;
    }
    tableWrapper.hidden = false;
    emptyState.hidden = true;

    for (const ticket of tickets) {
        const row = document.createElement("tr");
        if (ticket.overdue) row.classList.add("overdue-row");

        row.innerHTML = `
            <td>${escapeHtml(ticket.customer_name)}</td>
            <td>${escapeHtml(ticket.subject)}</td>
            <td><span class="badge badge-${ticket.priority}">${ticket.priority}</span></td>
            <td><span class="status-tag">${ticket.status.replace("_", " ")}</span></td>
            <td>${ticket.assigned_to ? escapeHtml(ticket.assigned_to) : "—"}</td>
            <td>${formatDueDate(ticket.due_at)}${ticket.overdue ? '<span class="overdue-tag">Overdue</span>' : ""}</td>
        `;
        tableBody.appendChild(row);
    }
}

async function loadTickets() {
    try {
        const res = await fetch("/api/tickets");
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const tickets = await res.json();
        loadError.hidden = true;
        renderTickets(tickets);
    } catch (err) {
        // Network issue or server down — show it in the UI instead of
        // letting it surface only as a console error.
        tableWrapper.hidden = true;
        emptyState.hidden = true;
        loadError.hidden = false;
    }
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    formError.textContent = "";

    const payload = {
        customer_name: document.getElementById("customer_name").value,
        subject: document.getElementById("subject").value,
        priority: document.getElementById("priority").value,
        assigned_to: document.getElementById("assigned_to").value,
    };

    submitBtn.disabled = true;
    submitBtn.textContent = "Adding…";

    try {
        const res = await fetch("/api/tickets", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const data = await res.json();
            formError.textContent = (data.errors || ["Something went wrong."]).join(" ");
            return;
        }

        form.reset();
        document.getElementById("priority").value = "normal";
        await loadTickets();
    } catch (err) {
        formError.textContent = "Couldn't reach the server. Check it's running and try again.";
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Add ticket";
    }
});

refreshBtn.addEventListener("click", loadTickets);

// Load on page open, and keep it fresh automatically so "overdue" stays accurate.
loadTickets();
setInterval(loadTickets, 30000);
