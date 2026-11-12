"""Customer Health Agent — a hand-written agent loop using Claude tool use.

Run:  python agent.py              (default: up to 40 steps)
      python agent.py --max-steps 10

THE AGENT LOOP
  1. Send the conversation (and the list of tools) to Claude.
  2. Claude replies. If it wants to use tools, the reply contains
     tool_use blocks and stop_reason == "tool_use".
  3. We run each requested tool in Python and send the results back
     as tool_result blocks.
  4. Repeat until Claude stops asking for tools (stop_reason == "end_turn")
     or we hit --max-steps.
"""

import argparse
import json
import sys
from datetime import date

import anthropic
from dotenv import load_dotenv

from prompts import USER_KICKOFF, build_system_prompt
from tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

MODEL = "claude-opus-5-5"
TODAY = date(2026, 11, 12)  # matches the sample data; use date.today() with real data

# Terminal colors (purely cosmetic)
DIM, BOLD, CYAN, GREEN, RED, YELLOW, RESET = "\033[2m", "\033[1m", "\033[36m", "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def short(value, limit: int = 110) -> str:
    """Compact one-line preview of a tool input/output for the terminal."""
    text = value if isinstance(value, str) else json.dumps(value)
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def run_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run one tool. Returns (result_text, is_error).

    Errors are returned to Claude instead of crashing the program, so the
    agent can notice the problem and try something else.
    """
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"Unknown tool: {name}", True
    try:
        result = func(**tool_input)
        return (result if isinstance(result, str) else json.dumps(result, indent=2)), False
    except Exception as e:  # noqa: BLE001 — any tool failure goes back to the model
        return f"Error running {name}: {e}", True


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Customer Health Agent.")
    parser.add_argument("--max-steps", type=int, default=40,
                        help="Safety limit on how many times we call the model (default: 40).")
    args = parser.parse_args()

    load_dotenv()  # reads ANTHROPIC_API_KEY (and optional SLACK_WEBHOOK_URL) from .env
    client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY automatically

    system_prompt = build_system_prompt(TODAY)

    # The conversation so far. This list IS the agent's memory: every
    # request re-sends it in full, and it grows by two messages each step
    # (Claude's reply, then our tool results).
    messages = [{"role": "user", "content": USER_KICKOFF}]

    print(f"{BOLD}Customer Health Agent{RESET}  model={MODEL}  max_steps={args.max_steps}\n")
    total_in = total_out = 0

    for step in range(1, args.max_steps + 1):
        print(f"{BOLD}── Step {step} ─────────────────────────────────────{RESET}")

        # ---- 1. Ask Claude what to do next -------------------------------
        # Streaming keeps long responses (like the full report) from timing
        # out; get_final_message() just waits for the complete reply.
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=32000,
            system=system_prompt,
            tools=TOOL_SCHEMAS,
            messages=messages,
            # Thinking lets Claude reason before acting. On this model it's
            # always adaptive; "effort" controls how hard it thinks.
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            # If a safety classifier ever declines a request, retry it on a
            # fallback model automatically instead of just stopping.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            response = stream.get_final_message()

        total_in += response.usage.input_tokens
        total_out += response.usage.output_tokens

        # Show any text Claude wrote alongside its tool calls.
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"{CYAN}Claude:{RESET} {block.text.strip()}")

        # Always store Claude's full reply (including tool_use blocks)
        # in the history — the next request must include it.
        messages.append({"role": "assistant", "content": response.content})

        # ---- 2. Is Claude done? ------------------------------------------
        if response.stop_reason == "end_turn":
            print(f"\n{GREEN}{BOLD}✔ Agent finished in {step} steps.{RESET}")
            break
        if response.stop_reason == "refusal":
            print(f"{RED}Claude declined to continue: {response.stop_details}{RESET}")
            return 1
        if response.stop_reason == "max_tokens":
            print(f"{RED}Response was cut off (max_tokens). Stopping.{RESET}")
            return 1
        if response.stop_reason != "tool_use":
            print(f"{YELLOW}Unexpected stop_reason: {response.stop_reason}{RESET}")
            break

        # ---- 3. Run every tool Claude asked for --------------------------
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"  {YELLOW}→ {block.name}{RESET}({short(block.input, 90)})")
            result_text, is_error = run_tool(block.name, block.input)
            color = RED if is_error else DIM
            print(f"    {color}← {short(result_text)}{RESET}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,   # links this result to Claude's request
                "content": result_text,
                "is_error": is_error,
            })

        # ---- 4. Send all results back in ONE user message, then loop -----
        messages.append({"role": "user", "content": tool_results})
    else:
        # The for-loop ran out without a break: the safety limit kicked in.
        print(f"\n{RED}{BOLD}✘ Stopped: reached --max-steps={args.max_steps} before the agent finished.{RESET}")
        return 1

    print(f"{DIM}Tokens used: {total_in:,} input / {total_out:,} output{RESET}")
    print("Outputs: output/report.md and output/drafts/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
