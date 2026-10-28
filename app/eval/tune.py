import json
import os
from pathlib import Path

import optuna
from openai import APIError

from app.tools import agent
from app.tools.registry import registry
from app.eval.run_evals import score

HERE = Path(__file__).resolve().parent
TASKS = [
    json.loads(l) for l in (HERE / "golden.jsonl").read_text().splitlines() if l.strip()
]
SUBSET = [
    t for t in TASKS if t["id"] in {"g01", "g02", "g04", "g05", "g08"}
]  # a mix, cheap enough per trial
# Super 404s on this key (Day 13), so main = lightning; the alternative tests "smaller model"
MODELS = list(
    dict.fromkeys(
        [agent.MODEL, os.environ.get("TUNE_ALT_MODEL", "nvidia/nemotron-3.5-bolt-e4b")]
    )
)
PROMPTS = {
    "strict": agent.SYSTEM,
    "loose": "You are a helpful assistant for financial-crime analysts. Use tools if useful.",
}
PRECISE = registry.schemas()
VAGUE = [
    {"type": "function", "function": {**s["function"], "description": "Tool."}}
    for s in PRECISE
]


def objective(trial):
    agent.MODEL = trial.suggest_categorical("model", MODELS)
    agent.SYSTEM = PROMPTS[trial.suggest_categorical("prompt", list(PROMPTS))]
    agent.MAX_STEPS = trial.suggest_categorical("max_steps", [3, 6, 10])
    schemas = (
        PRECISE
        if trial.suggest_categorical("descriptions", ["precise", "vague"]) == "precise"
        else VAGUE
    )
    results = [agent.run(t["question"], schemas=schemas, verbose=False) for t in SUBSET]
    success = sum(score(t, r) for t, r in zip(SUBSET, results)) / len(SUBSET)
    mean_steps = sum(r["steps"] for r in results) / len(results)
    return success, mean_steps  # maximise success, minimise LLM calls


study = optuna.create_study(
    directions=["maximize", "minimize"],
    study_name="aai-tuning",
    storage=f"sqlite:///{HERE / 'optuna.db'}",
    load_if_exists=True,
)
# an API error (e.g. a model that rejects tool calls) fails that trial, not the whole study
study.optimize(
    objective, n_trials=int(os.environ.get("TRIALS", "8")), catch=(APIError,)
)
print(f"{len(study.best_trials)} trials on the Pareto front:")
for t in study.best_trials:
    print(f"  #{t.number} success={t.values[0]:.0%} steps={t.values[1]:.1f} {t.params}")
