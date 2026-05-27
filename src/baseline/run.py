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
"""

import argparse
import json
import sys
from pathlib import Path

import src.agents  # noqa: F401 — side-effect: registers all custom agents
from tau2.data_model.simulation import RunConfig
from tau2.run import run_domain

REPORTS_DIR = Path(__file__).parents[2] / "reports" / "baseline"

AGENT_LLM = "gpt-4.1"
USER_LLM = "gpt-4.1"
SEED = 300


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
    args = parser.parse_args()

    agent_name = args.agent

    if args.smoke:
        num_tasks = 5
        num_trials = 1
        out_name = args.out or f"{agent_name}_smoke"
    else:
        num_tasks = None
        num_trials = 3
        out_name = args.out or f"{agent_name}_run"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

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
    )

    print(f"[baseline] domain=retail  agent={agent_name}  llm={AGENT_LLM}  trials={num_trials}  seed={SEED}")
    results = run_domain(config)

    out_path = REPORTS_DIR / f"{out_name}.json"
    out_path.write_text(results.model_dump_json(indent=2))
    print(f"[baseline] saved → {out_path}")

    summary = {
        "agent": agent_name,
        "agent_llm": AGENT_LLM,
        "user_llm": USER_LLM,
        "num_trials": num_trials,
        "seed": SEED,
        "task_split": "base",
        "results_file": str(out_path.name),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    sys.exit(main())
