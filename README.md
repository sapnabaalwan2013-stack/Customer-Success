# Customer Health Agent

An AI agent that reviews a portfolio of customer accounts, flags who is at risk of churning (and explains why), drafts a personalized check-in email for each at-risk account, and writes a summary report for the Customer Success team.

Built with Python and the [Claude API's tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview). The agent loop is hand-written so every step is visible.

## The business problem

A Customer Success Manager might own 50–150 accounts. Checking every account's usage dashboard and support queue every week isn't realistic, so warning signs get missed: a key user quietly stops logging in, an urgent ticket sits open for a month, a renewal date creeps up. By the time anyone notices, the customer has already decided to leave.

This agent does the weekly sweep for you. It reads the same signals a good CSM would, weighs them, and hands back a prioritized list with its reasoning and a ready-to-edit email. The CSM still makes the call and sends the email; the agent does the legwork.

## How it works

The agent is Claude running in a loop with access to six tools:

| Tool | What it does |
|---|---|
| `list_accounts()` | Lists all accounts |
| `get_account_details(account_id)` | Contract value, seats, active users (this month and last), renewal date |
| `get_tickets(account_id)` | Recent support tickets |
| `save_email_draft(account_id, subject, body)` | Writes a draft to `output/drafts/` (never sends) |
| `save_report(markdown)` | Writes `output/report.md` |
| `post_to_slack(message)` | Posts a summary if `SLACK_WEBHOOK_URL` is set; otherwise prints a dry run |

### The agent loop

```
            ┌───────────────────────────────────────────┐
            │  messages = [system prompt, "run review"] │
            └─────────────────────┬─────────────────────┘
                                  ▼
                ┌──────────────────────────────────┐
         ┌─────▶│ Send messages + tools to Claude  │
         │      └─────────────────┬────────────────┘
         │                        ▼
         │           Claude replies. stop_reason?
         │              │                    │
         │         "tool_use"            "end_turn"
         │              ▼                    ▼
         │   ┌──────────────────────┐    ┌────────┐
         │   │ My Python code runs  │    │  Done  │
         │   │ each requested tool  │    └────────┘
         │   └──────────┬───────────┘
         │              ▼
         │   Append tool results to messages
         └──────────────┘   (stop early if step > --max-steps)
```

Key ideas:

- **The model decides, my code acts.** Claude never touches files or Slack directly. It asks for a tool by name with JSON inputs; `agent.py` runs the real function and returns the result.
- **The conversation is the memory.** Every request re-sends the full message history, including earlier tool results. That is how the agent "remembers" what it has already looked at.
- **Guardrails are in the tools.** The email tool can only save drafts, so the agent physically cannot email a customer. `--max-steps` caps runaway loops.
- **Errors go back to the model.** If a tool fails (for example, a bad account id), the error message is returned to Claude so it can correct itself.

### Churn signals the agent weighs

Defined in the system prompt (`prompts.py`): low seat utilization, declining active users, unresolved High/Urgent tickets, renewal within ~60 days, and explicit warning signs (cancellation questions, data-export requests, competitor evaluations, a champion leaving). It's also told what *lowers* risk, such as a planned phased rollout or a bug with a scheduled fix, and to explain its reasoning when signals conflict.

## Project structure

```
customer-health-agent/
├── agent.py               # The agent loop (start here)
├── tools.py               # Tool schemas + Python implementations
├── prompts.py             # System prompt
├── data/
│   ├── generate_data.py   # Builds the fake CRM data
│   ├── accounts.csv       # 15 accounts
│   └── tickets.json       # 40 support tickets
├── output/                # Created on run (git-ignored)
│   ├── report.md
│   └── drafts/
├── .env.example
└── requirements.txt
```

## How to run

Requires Python 3.10+ and an [Anthropic API key](https://console.anthropic.com/).

```bash
git clone <your-repo-url>
cd customer-health-agent
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then put your API key in .env
python agent.py
```

Options:

```bash
python agent.py --max-steps 20   # stop after 20 model calls
python data/generate_data.py     # regenerate the sample data
```

To post to Slack, add an [incoming webhook URL](https://api.slack.com/messaging/webhooks) as `SLACK_WEBHOOK_URL` in `.env`.

A full run makes roughly 5–10 model calls.

## Example output

<!-- EXAMPLE_OUTPUT_START -->
_Run `python agent.py` and paste highlights here._
<!-- EXAMPLE_OUTPUT_END -->

## What I learned

- **About agents:** _…_
- **About tool design:** _…_
- **About prompting:** _…_
- **What surprised me:** _…_
- **How this applies to customer success:** _…_

## Next steps

- **Add an eval to measure accuracy.** `data/generate_data.py` labels each account as healthy, at-risk, or ambiguous. An eval script would run the agent several times and compare its ratings against those labels, so I can tell whether a prompt change actually made the agent better or worse.
- Grade email quality (specific to the customer? avoids mentioning risk scores?) using a rubric.
- Connect a real data source (CRM or product analytics export) in place of the CSV.
- Add a human approval step before anything is posted to Slack.
- Run it on a weekly schedule.
