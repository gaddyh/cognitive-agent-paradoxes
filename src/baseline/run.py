"""
Baseline runner — runs any registered agent on tau2-verified retail.

Prereqs:
  - Redis running: brew services start redis
  - LLM_CACHE_ENABLED = True in external/tau2-bench-verified/src/tau2/config.py (local edit, not committed)
  - OPENAI_API_KEY set in .env

Usage:
  python -m src.baseline.run                             # llm_agent, base split, 3 trials
  python -m src.baseline.run --agent my_llm_agent        # custom registered agent
  python -m src.baseline.run --smoke                     # 5 tasks, 1 trial (sanity check)
  python -m src.baseline.run --agent my_llm_agent --smoke

MLflow:
  .venv/bin/mlflow ui --port 5000 --backend-store-uri sqlite:///mlflow.db
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import mlflow
import mlflow.dspy

import src.agents  # noqa: F401 — side-effect: registers all custom agents
from tau2.data_model.simulation import RunConfig
from tau2.run import run_domain

REPORTS_DIR = Path(__file__).parents[2] / "reports" / "baseline"

AGENT_LLM_DEFAULT = "gpt-4o-mini"
USER_LLM_DEFAULT = "gpt-4o"
SEED = 300

SKIPPED_MOVES = {"tool_result", "cheap_user_message", "cognition_disabled", "cognition_error"}

MLFLOW_TRACKING_URI = "sqlite:///mlflow.db"


def _compute_tau2_metrics(results) -> dict:
    sims = results.simulations
    if not sims:
        return {}
    rewards = [s.reward_info.reward for s in sims if s.reward_info is not None]
    n = len(rewards)
    mean_reward = sum(rewards) / n
    variance = sum((r - mean_reward) ** 2 for r in rewards) / n
    return {
        "num_simulations": n,
        "mean_reward": mean_reward,
        "reward_std": math.sqrt(variance),
        "pass_rate_strict": sum(1 for r in rewards if r == 1.0) / n,
        "pass_rate_any": sum(1 for r in rewards if r > 0) / n,
        "total_agent_cost": sum(s.agent_cost for s in sims if s.agent_cost is not None),
        "total_user_cost": sum(s.user_cost for s in sims if s.user_cost is not None),
        "mean_duration_s": sum(s.duration for s in sims if s.duration is not None) / n,
    }


def _compute_turn_metrics(turns_path: Path) -> dict:
    if not turns_path.exists():
        return {}
    rows = []
    with turns_path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if not rows:
        return {}
    n = len(rows)
    skipped = sum(1 for r in rows if r.get("move") in SKIPPED_MOVES)
    return {
        "avg_reason_ms": sum(r.get("reason_ms", 0) for r in rows) / n,
        "avg_generate_ms": sum(r.get("generate_ms", 0) for r in rows) / n,
        "avg_total_ms": sum(r.get("total_ms", 0) for r in rows) / n,
        "avg_convo_chars": sum(r.get("convo_chars", 0) for r in rows) / n,
        "pct_tool_call": sum(1 for r in rows if r.get("move") == "tool_call") / n,
        "pct_clarify": sum(1 for r in rows if r.get("move") == "clarify") / n,
        "pct_answer": sum(1 for r in rows if r.get("move") == "answer") / n,
        "pct_skipped_cognition": skipped / n,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate B baseline run")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke test: 5 tasks, 1 trial only",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="llm_agent",
        help="Registered agent name (default: llm_agent)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Override output filename (no extension)",
    )
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=None,
        help="Override number of tasks (default: 5 for smoke, all for full run)",
    )
    parser.add_argument(
        "--llm",
        type=str,
        default=None,
        help=f"Agent LLM model (default: {AGENT_LLM_DEFAULT})",
    )
    parser.add_argument(
        "--user-llm",
        type=str,
        default=None,
        help=f"User simulator LLM model (default: {USER_LLM_DEFAULT})",
    )
    args = parser.parse_args()

    AGENT_LLM = args.llm or AGENT_LLM_DEFAULT
    USER_LLM = args.user_llm or USER_LLM_DEFAULT

    agent_name = args.agent

    if args.smoke:
        num_tasks = args.num_tasks if args.num_tasks is not None else 5
        num_trials = 1
        out_name = args.out or f"{agent_name}_smoke"
    else:
        num_tasks = args.num_tasks
        num_trials = 3
        out_name = args.out or f"{agent_name}_run"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    turns_path = REPORTS_DIR / f"{out_name}_turns.jsonl"
    os.environ["TAU2_TURN_LOG"] = str(turns_path)
    turns_path.unlink(missing_ok=True)

    config = RunConfig(
        domain="retail",
        agent=agent_name,
        llm_agent=AGENT_LLM,
        llm_args_agent={"temperature": 0.0},
        user="user_simulator",
        llm_user=USER_LLM,
        llm_args_user={"temperature": 0.0},
        task_split_name="base",
        num_trials=num_trials,
        num_tasks=num_tasks,
        seed=SEED,
        log_level="INFO",
        max_concurrency=1,
    )

    cog_model = os.environ.get("COG_MODEL", "openai/gpt-4o-mini")
    cog_enabled = os.environ.get("COG_ENABLED", "true").lower() == "true"
    run_kind = "smoke" if args.smoke else "full"

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.dspy.autolog(
        log_traces=True,
        log_traces_from_eval=False,
        log_evals=False,
        silent=True,
    )
    mlflow.set_experiment("cognitive-agent-paradoxes")
    with mlflow.start_run(run_name=f"{agent_name}_{run_kind}"):
        mlflow.set_tags({
            "agent": agent_name,
            "smoke": str(args.smoke).lower(),
            "cog_model": cog_model,
        })
        mlflow.log_params({
            "agent": agent_name,
            "agent_llm": AGENT_LLM,
            "user_llm": USER_LLM,
            "num_trials": num_trials,
            "num_tasks": num_tasks if num_tasks is not None else "all",
            "seed": SEED,
            "task_split": "base",
            "smoke": args.smoke,
            "cog_enabled": cog_enabled,
        })

        print(f"[baseline] domain=retail  agent={agent_name}  llm={AGENT_LLM}  trials={num_trials}  seed={SEED}")
        results = run_domain(config)

        out_path = REPORTS_DIR / f"{out_name}.json"
        out_path.write_text(results.model_dump_json(indent=2))
        print(f"[baseline] saved → {out_path}")

        tau2_metrics = _compute_tau2_metrics(results)
        turn_metrics = _compute_turn_metrics(turns_path)
        mlflow.log_metrics({**tau2_metrics, **turn_metrics})

        mlflow.log_artifact(str(out_path), artifact_path="results")
        if turns_path.exists():
            mlflow.log_artifact(str(turns_path), artifact_path="results")

    summary = {
        "agent": agent_name,
        "agent_llm": AGENT_LLM,
        "user_llm": USER_LLM,
        "num_trials": num_trials,
        "seed": SEED,
        "task_split": "base",
        "results_file": str(out_path.name),
        **tau2_metrics,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    sys.exit(main())
