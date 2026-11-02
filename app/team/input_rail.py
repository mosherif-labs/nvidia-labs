"""Day 21's input rail as a gate: screen an alert before any case starts."""

import sys
from pathlib import Path
from nemoguardrails import LLMRails, RailsConfig

CONFIG = Path(__file__).resolve().parents[1] / "guardrails" / "config"  # Day 21's rails
rails = LLMRails(RailsConfig.from_path(str(CONFIG)))


def check(alert: str) -> bool:
    """True if the input rails let the alert through unchanged."""
    res = rails.generate(
        messages=[{"role": "user", "content": alert}], options={"rails": ["input"]}
    )
    return res.response[0]["content"] == alert  # blocked -> the refusal text instead


if __name__ == "__main__":
    print("allowed" if check(" ".join(sys.argv[1:])) else "BLOCKED by the input rail")
