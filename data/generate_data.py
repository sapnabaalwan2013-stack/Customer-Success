"""Generate fake CRM data for the Customer Health Agent.

Run:  python data/generate_data.py

Each account is hand-designed to fall into one of three buckets so the
agent has something to reason about:
  - HEALTHY:    high seat usage, few/minor tickets, renewal far away
  - AT RISK:    low usage, open high-priority tickets, renewal soon
  - AMBIGUOUS:  mixed signals (e.g. great usage but an angry open ticket)

The intended bucket is NOT written into the data files — the agent has to
work it out. (Keep this list handy later for building an eval!)
"""

import csv
import json
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent
TODAY = date(2026, 11, 12)  # fixed "today" so the data is reproducible


def d(days_from_today: int) -> str:
    return (TODAY + timedelta(days=days_from_today)).isoformat()


# account_id, name, tier, ACV, seats, active_30d, active_prev_30d, renewal (days out), CSM, intended bucket
ACCOUNTS = [
    ("ACC-001", "Brightwave Analytics",   "Enterprise", 180000, 250, 231, 228, 210, "Priya Shah",   "healthy"),
    ("ACC-002", "Northwind Logistics",    "Business",    48000,  80,  22,  51,  34, "Marcus Lee",   "at_risk"),
    ("ACC-003", "Lumen Health",           "Enterprise", 240000, 400, 362, 300,  95, "Priya Shah",   "healthy"),
    ("ACC-004", "Copperleaf Foods",       "Starter",      6000,  15,   3,   6,  21, "Dana Ortiz",   "at_risk"),
    ("ACC-005", "Atlas Robotics",         "Business",    60000, 100,  88,  90,  45, "Marcus Lee",   "ambiguous"),
    ("ACC-006", "Silverline Insurance",   "Enterprise", 310000, 500, 205, 340,  60, "Priya Shah",   "at_risk"),
    ("ACC-007", "Pinecrest Schools",      "Business",    36000, 120, 101,  98, 300, "Dana Ortiz",   "healthy"),
    ("ACC-008", "Harborview Hotels",      "Business",    42000,  70,  41,  44,  28, "Marcus Lee",   "ambiguous"),
    ("ACC-009", "Quantum Ledger",         "Starter",      7200,  10,  10,   9, 150, "Dana Ortiz",   "healthy"),
    ("ACC-010", "Redfern Manufacturing",  "Enterprise", 150000, 300,  96, 110, 180, "Priya Shah",   "ambiguous"),
    ("ACC-011", "Tidewater Credit Union", "Business",    54000,  90,  30,  62,  15, "Marcus Lee",   "at_risk"),
    ("ACC-012", "Evergreen Retail Group", "Enterprise", 200000, 350, 318, 310, 120, "Dana Ortiz",   "healthy"),
    ("ACC-013", "Mosaic Media",           "Starter",      4800,   8,   5,   5,  40, "Dana Ortiz",   "ambiguous"),
    ("ACC-014", "Vantage Legal",          "Business",    39000,  60,  57,  40,  75, "Marcus Lee",   "healthy"),
    ("ACC-015", "Cobalt Energy",          "Enterprise", 275000, 450, 290, 295,  25, "Priya Shah",   "ambiguous"),
]

# account_id, days_ago, subject, priority, status, description
TICKETS = [
    # ACC-001 Brightwave — healthy, minor questions
    ("ACC-001", 40, "How to export dashboards to PDF", "Low", "Resolved", "User asked how to schedule PDF exports of dashboards. Shared help article; customer confirmed it worked."),
    ("ACC-001", 12, "Feature request: dark mode", "Low", "Open", "Several analysts requested a dark mode for late-night work. Logged with product."),
    # ACC-002 Northwind — usage collapse + SSO problems + renewal soon
    ("ACC-002", 55, "SSO login failing for warehouse staff", "High", "Open", "Warehouse team can't log in via Okta SSO since their IdP migration. Workaround is shared passwords, which their IT security team rejected."),
    ("ACC-002", 30, "Still can't log in — escalating", "Urgent", "Open", "Ops Director: 'We've been waiting nearly a month. Half my team has stopped using the tool.' Engineering investigating SAML assertion mismatch."),
    ("ACC-002", 9, "Request for contract cancellation terms", "Medium", "Open", "Procurement asked for a copy of the termination clause and data export options."),
    # ACC-003 Lumen — healthy, growing
    ("ACC-003", 25, "Add 50 more seats?", "Low", "Resolved", "Customer asked about pricing to add seats for new clinic rollout. Routed to account exec."),
    ("ACC-003", 6, "API rate limit question", "Low", "Resolved", "Dev team asked about API rate limits for a new integration. Answered same day."),
    # ACC-004 Copperleaf — tiny, champion left
    ("ACC-004", 35, "Who is our admin now?", "Medium", "Resolved", "Our main admin (Jen) left the company. Transferred admin rights to the office manager."),
    ("ACC-004", 14, "Billing: can we downgrade?", "Medium", "Open", "Office manager asked whether they can drop to 5 seats or pause the subscription for the winter season."),
    # ACC-005 Atlas — great usage, but angry bug ticket
    ("ACC-005", 20, "Data sync dropping records", "High", "Open", "Nightly sync from their ERP is dropping ~2% of records. Their VP Engineering says this is 'a blocker for renewal' if not fixed."),
    ("ACC-005", 8, "Sync issue — any update?", "High", "Open", "Follow-up asking for an ETA. Engineering identified the root cause; fix scheduled for next release in ~2 weeks."),
    ("ACC-005", 50, "Training session request", "Low", "Resolved", "Requested onboarding session for new hires. Completed."),
    # ACC-006 Silverline — big drop in usage, exec sponsor change, outage
    ("ACC-006", 60, "Performance degradation on reports", "High", "Resolved", "Large reports timing out. Resolved after index changes, but took 9 days."),
    ("ACC-006", 28, "New CIO wants a vendor review", "Medium", "Open", "New CIO has started a review of all analytics vendors. Requested ROI summary and usage stats."),
    ("ACC-006", 15, "Outage on Nov 2 impacted claims team", "Urgent", "Open", "4-hour outage during claims processing. Customer requesting RCA and SLA credits. Tone is frustrated."),
    ("ACC-006", 4, "Evaluating competitor — need data export", "High", "Open", "Asked for full data export in CSV/Parquet 'to support an evaluation'."),
    # ACC-007 Pinecrest — healthy
    ("ACC-007", 45, "Rostering import template", "Low", "Resolved", "Needed the latest CSV template for student roster import. Sent."),
    ("ACC-007", 18, "Thank you note", "Low", "Resolved", "Superintendent's office wrote to say teachers love the new attendance reports."),
    # ACC-008 Harborview — moderate usage, renewal soon, quiet
    ("ACC-008", 70, "Mobile app crashes on older iPads", "Medium", "Resolved", "Front desk iPads on iOS 15 crashing. Customer upgraded devices; resolved."),
    ("ACC-008", 22, "Question about price increase", "Medium", "Open", "Finance asked to confirm whether the 8% list price increase applies at their renewal."),
    # ACC-009 Quantum Ledger — fully used, small
    ("ACC-009", 30, "Invoice address change", "Low", "Resolved", "Updated billing address."),
    # ACC-010 Redfern — low % usage, but known phased rollout
    ("ACC-010", 90, "Phased rollout plan", "Low", "Resolved", "Agreed rollout: 100 seats per quarter across 3 plants. Plant 2 go-live scheduled for December."),
    ("ACC-010", 33, "Plant 2 go-live delayed?", "Medium", "Open", "Plant 2 IT lead says go-live may slip to Q1 due to network upgrades on their side."),
    ("ACC-010", 10, "Training materials for shop floor", "Low", "Open", "Requested simplified training guides for shop-floor supervisors."),
    # ACC-011 Tidewater — declining, renewal very soon, unresolved bug
    ("ACC-011", 48, "Member reports show wrong totals", "High", "Open", "Monthly member reports show incorrect totals for joint accounts. Board meeting used wrong numbers."),
    ("ACC-011", 26, "Reports still wrong — board unhappy", "Urgent", "Open", "Compliance officer: 'This is the second month of bad numbers going to our board.' No fix ETA yet."),
    ("ACC-011", 7, "Renewal — need to discuss", "Medium", "Open", "Procurement asked for a call before renewal and mentioned they are 'reviewing options'."),
    # ACC-012 Evergreen — healthy
    ("ACC-012", 38, "SSO setup for new subsidiary", "Medium", "Resolved", "Configured SSO for newly acquired subsidiary. Smooth rollout."),
    ("ACC-012", 11, "Custom dashboard request", "Low", "Open", "Merchandising team wants a custom sell-through dashboard. Scoped by solutions team."),
    ("ACC-012", 3, "Holiday traffic readiness", "Low", "Resolved", "Asked about capacity for holiday season. Confirmed no action needed."),
    # ACC-013 Mosaic — tiny, low-ish usage, no tickets recently
    ("ACC-013", 120, "Login help", "Low", "Resolved", "Password reset for a freelancer."),
    # ACC-014 Vantage Legal — rising usage, one fixed issue
    ("ACC-014", 52, "Document upload size limit", "Medium", "Resolved", "Large PDFs failing upload. Limit raised to 200MB; customer happy."),
    ("ACC-014", 16, "Onboarding second office", "Low", "Resolved", "Onboarded 15 users from their Denver office."),
    # ACC-015 Cobalt — big, decent usage, renewal soon, legal/security review
    ("ACC-015", 42, "Security questionnaire for renewal", "Medium", "Open", "Infosec sent a 200-question security questionnaire required before renewal sign-off."),
    ("ACC-015", 19, "SOC 2 report request", "Medium", "Resolved", "Sent latest SOC 2 Type II report under NDA."),
    ("ACC-015", 13, "Questionnaire — 30 items still outstanding", "High", "Open", "Infosec says renewal cannot be signed until remaining questionnaire items are answered. Our security team is working on it."),
    ("ACC-015", 5, "Field crews love the offline mode", "Low", "Resolved", "Positive feedback from field operations manager about offline mode."),
    # A few more across accounts for variety
    ("ACC-002", 75, "Dashboard slow to load", "Medium", "Resolved", "Dashboards loading slowly. Resolved by caching config."),
    ("ACC-006", 85, "Admin training request", "Low", "Resolved", "Admin training completed for 3 new admins."),
    ("ACC-011", 80, "Add read-only role", "Low", "Resolved", "Created read-only role for auditors."),
]


def main() -> None:
    with open(DATA_DIR / "accounts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "account_id", "account_name", "plan_tier", "annual_contract_value",
            "seats_purchased", "active_users_30d", "active_users_prev_30d",
            "renewal_date", "csm_owner",
        ])
        for (aid, name, tier, acv, seats, act, prev, renew_days, csm, _bucket) in ACCOUNTS:
            w.writerow([aid, name, tier, acv, seats, act, prev, d(renew_days), csm])

    tickets = []
    for i, (aid, days_ago, subject, prio, status, desc) in enumerate(
        sorted(TICKETS, key=lambda t: (t[0], -t[1])), start=1
    ):
        tickets.append({
            "ticket_id": f"T-{1000 + i}",
            "account_id": aid,
            "created_date": d(-days_ago),
            "subject": subject,
            "priority": prio,
            "status": status,
            "description": desc,
        })
    with open(DATA_DIR / "tickets.json", "w") as f:
        json.dump(tickets, f, indent=2)

    print(f"Wrote {len(ACCOUNTS)} accounts and {len(tickets)} tickets to {DATA_DIR}/")


if __name__ == "__main__":
    main()
