import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app import data as tools  # Day 2's synthetic alerts

load_dotenv()  # nearest .env, searching up from this file

client = OpenAI(
    base_url=os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
)
MODEL = os.environ.get("AGENT_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")

# The contract: role, scope, refusal rule, output format. Same shape for every step.
CONTRACT = """You are step {step} of an AML alert pipeline at a bank.
Scope: use only the input you are given. Never invent amounts, names or policies.
If the input is not a transaction-monitoring alert, reply exactly: OUT_OF_SCOPE
Output: {output}"""


class Facts(BaseModel):
    customer: str
    pattern: str
    amounts: list[float]
    total: float
    window_days: int


def ask(step: str, output: str, user: str) -> str:
    r = client.chat.completions.create(
        model=MODEL,
        temperature=1.0,
        top_p=0.95,
        max_tokens=800,
        messages=[
            {"role": "system", "content": CONTRACT.format(step=step, output=output)},
            {"role": "user", "content": user},
        ],
    )
    return r.choices[0].message.content.strip()


def extract(alert: str) -> Facts:
    out = "JSON only, no prose, with keys customer, pattern, amounts (list of numbers), total, window_days"
    raw = ask("2 (extract)", out, alert)
    for attempt in (1, 2):
        try:
            return Facts.model_validate_json(
                raw.strip().strip("`").removeprefix("json").strip()
            )
        except ValidationError as e:  # validate-and-retry: show the model its mistake
            if attempt == 2:
                raise
            raw = ask(
                "2 (extract)",
                out,
                f"{alert}\n\nYour last reply was invalid: {e.errors()[0]['msg']}. Try again.",
            )


def run(text: str) -> str:
    label = ask(
        "1 (triage)", "one word: STRUCTURING, HIGH_RISK_WIRES, PAYROLL or OTHER", text
    )
    if label == "OUT_OF_SCOPE":
        return "stopped at step 1: out of scope"
    facts = extract(text)
    if (
        abs(sum(facts.amounts) - facts.total) > 0.01
    ):  # the gate: a programmatic check between steps
        return f"stopped at the gate: amounts sum to {sum(facts.amounts)}, model said total {facts.total}"
    summary = ask(
        "3 (summarise)",
        "two sentences for an investigator, using only these facts",
        f"Facts: {facts.model_dump_json()}\nTriage label: {label}",
    )
    return f"[{label}] {facts.model_dump_json()}\n{summary}"


if __name__ == "__main__":
    arg = " ".join(sys.argv[1:])
    print(run(tools.get_alert(arg) if arg.upper().startswith("A-") else arg))
