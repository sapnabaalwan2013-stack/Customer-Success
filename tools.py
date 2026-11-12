"""The agent's tools.

Each tool has two halves:
  1. A SCHEMA (in TOOL_SCHEMAS) — what Claude sees. The name, a description
     of when to use it, and a JSON Schema for the inputs. Claude reads these
     to decide which tool to call. Good descriptions = better decisions.
  2. A PYTHON FUNCTION — what actually runs on your machine when Claude
     asks for that tool.

Claude never executes anything itself. It only *asks*; agent.py runs it.
"""

import csv
import json
import os
import re
from pathlib import Path

import requests

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DRAFTS_DIR = OUTPUT_DIR / "drafts"


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _load_accounts() -> list[dict]:
    with open(DATA_DIR / "accounts.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:  # CSV gives strings; convert numeric fields
        for k in ("annual_contract_value", "seats_purchased",
                  "active_users_30d", "active_users_prev_30d"):
            r[k] = int(r[k])
    return rows


def _load_tickets() -> list[dict]:
    with open(DATA_DIR / "tickets.json") as f:
        return json.load(f)


def _find_account(account_id: str) -> dict:
    for a in _load_accounts():
        if a["account_id"] == account_id:
            return a
    # Raising an error is fine: agent.py turns it into an is_error tool
    # result, and Claude can read the message and correct itself.
    raise ValueError(f"No account with id '{account_id}'. Call list_accounts to see valid ids.")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def list_accounts() -> list[dict]:
    """Lightweight list — just enough for Claude to know what exists."""
    return [
        {"account_id": a["account_id"], "account_name": a["account_name"],
         "plan_tier": a["plan_tier"], "csm_owner": a["csm_owner"]}
        for a in _load_accounts()
    ]


def get_account_details(account_id: str) -> dict:
    a = _find_account(account_id)
    # Pre-compute utilization so the model doesn't have to do arithmetic.
    a["seat_utilization_pct"] = round(100 * a["active_users_30d"] / a["seats_purchased"], 1)
    prev = a["active_users_prev_30d"]
    a["active_users_change_pct"] = round(100 * (a["active_users_30d"] - prev) / prev, 1) if prev else None
    return a


def get_tickets(account_id: str) -> list[dict]:
    _find_account(account_id)  # validates the id
    return [t for t in _load_tickets() if t["account_id"] == account_id]


def save_email_draft(account_id: str, subject: str, body: str) -> str:
    account = _find_account(account_id)
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", account["account_name"].lower()).strip("-")
    path = DRAFTS_DIR / f"{account_id}_{slug}.md"
    path.write_text(
        f"**To:** {account['account_name']}\n"
        f"**From:** {account['csm_owner']}\n"
        f"**Subject:** {subject}\n\n---\n\n{body}\n"
    )
    return f"Draft saved to {path.relative_to(ROOT)} (not sent)."


def save_report(markdown: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "report.md"
    path.write_text(markdown)
    return f"Report saved to {path.relative_to(ROOT)}."


def post_to_slack(message: str) -> str:
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        print("\n      [Slack dry run — SLACK_WEBHOOK_URL not set. Would have posted:]")
        for line in message.splitlines():
            print(f"      | {line}")
        return "SLACK_WEBHOOK_URL is not set, so nothing was posted (dry run printed to terminal)."
    resp = requests.post(webhook, json={"text": message}, timeout=10)
    resp.raise_for_status()
    return "Posted to Slack."


# ---------------------------------------------------------------------------
# Schemas — this is exactly what Claude sees
# ---------------------------------------------------------------------------

_ACCOUNT_ID = {"type": "string", "description": "Account id, e.g. 'ACC-001'."}

TOOL_SCHEMAS = [
    {
        "name": "list_accounts",
        "description": "List every customer account (id, name, plan tier, CSM owner). "
                       "Call this first to see which accounts need reviewing.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_account_details",
        "description": "Get contract and usage data for one account: annual contract value, seats purchased, "
                       "active users in the last 30 days and the 30 days before that, seat utilization %, "
                       "change in active users %, renewal date and CSM owner.",
        "input_schema": {"type": "object", "properties": {"account_id": _ACCOUNT_ID},
                         "required": ["account_id"], "additionalProperties": False},
    },
    {
        "name": "get_tickets",
        "description": "Get recent support tickets for one account, with created date, subject, priority "
                       "(Low/Medium/High/Urgent), status (Open/Resolved) and a short description.",
        "input_schema": {"type": "object", "properties": {"account_id": _ACCOUNT_ID},
                         "required": ["account_id"], "additionalProperties": False},
    },
    {
        "name": "save_email_draft",
        "description": "Save a check-in email draft for an account's CSM to review. This does NOT send the "
                       "email; it writes a file to output/drafts/. Use once per at-risk account.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": _ACCOUNT_ID,
                "subject": {"type": "string", "description": "Email subject line."},
                "body": {"type": "string", "description": "Full email body, signed by the CSM owner."},
            },
            "required": ["account_id", "subject", "body"],
            "additionalProperties": False,
        },
    },
    {
        "name": "save_report",
        "description": "Save the final portfolio health report as Markdown to output/report.md. "
                       "Call this once, after all accounts have been reviewed and emails drafted.",
        "input_schema": {
            "type": "object",
            "properties": {"markdown": {"type": "string", "description": "The full report in Markdown."}},
            "required": ["markdown"],
            "additionalProperties": False,
        },
    },
    {
        "name": "post_to_slack",
        "description": "Post a short summary (a few lines, Slack mrkdwn) to the CS team's Slack channel. "
                       "Call after saving the report. If Slack isn't configured it does a harmless dry run.",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string", "description": "Short summary message."}},
            "required": ["message"],
            "additionalProperties": False,
        },
    },
]

# Maps the tool name Claude uses -> the Python function to run.
TOOL_FUNCTIONS = {
    "list_accounts": list_accounts,
    "get_account_details": get_account_details,
    "get_tickets": get_tickets,
    "save_email_draft": save_email_draft,
    "save_report": save_report,
    "post_to_slack": post_to_slack,
}
