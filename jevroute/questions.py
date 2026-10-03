"""The Jev request: a small state (the delegated task) and atomic questions about it.

Questions are deliberately literal and one-judgment-each (see jev-1.13 jaggedness:
literal reading, indirection, large irrelevant state). Combining them is policy.py's job.
"""

MAX_TASK_CHARS = 6000  # keep the state small: Jev accuracy drops with irrelevant detail

KINDS = {
    "search": "Find, read, or summarize existing files, logs, or docs. No code changes.",
    "test_run": "Run existing tests, builds, or commands and report the output.",
    "mechanical_edit": "A small, local change that follows an obvious pattern: rename, format, typo, config value.",
    "feature": "Implement new behavior or extend existing behavior in code.",
    "debug": "Find the cause of a bug or failure and fix it.",
    "review": "Judge the correctness, quality, or security of existing code or changes.",
    "design": "Decide requirements, architecture, interfaces, or a plan before coding.",
}

QUESTIONS = {
    "kind": {
        "type": "choice",
        "instructions": "Which kind of work does `task` ask the agent to do?",
        "criteria": KINDS,
    },
    "edits_code": {
        "type": "noul",
        "instructions": "`task` asks the agent to create or modify files.",
    },
    "multi_module": {
        "type": "noul",
        "instructions": "`task` requires changing or understanding more than one module, package, or component.",
    },
    "ambiguous": {
        "type": "noul",
        "instructions": "`task` leaves important requirements or acceptance criteria unstated.",
    },
    "risky_domain": {
        "type": "noul",
        "instructions": "`task` involves security, authentication, concurrency, data migration, payments, or deleting data.",
    },
    "novelty": {
        "type": "score",
        "instructions": "How much original reasoning does `task` need?",
        "criteria": [
            "Follows an obvious existing pattern or is pure lookup",
            "Needs some judgment within known patterns",
            "Needs new design, deep debugging, or non-obvious trade-offs",
        ],
    },
}


def build_state(tool_input):
    """State sent to Jev: only the delegated task, never the conversation history."""
    prompt = tool_input.get("prompt") or ""
    if len(prompt) > MAX_TASK_CHARS:
        prompt = prompt[:MAX_TASK_CHARS] + "\n[truncated]"
    return {
        "agent_type": tool_input.get("subagent_type") or "general-purpose",
        "summary": tool_input.get("description") or "",
        "task": prompt,
    }


def build_request(state, model="jev-latest"):
    return {"state": state, "model": model, "questions": QUESTIONS}
