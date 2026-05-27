# Gate B Reproduction

## Run parameters

| Parameter      | Value                              |
| -------------- | ---------------------------------- |
| Benchmark      | tau2-bench-verified                |
| Domain         | retail                             |
| Agent          | llm_agent (stock, unmodified)      |
| Agent LLM      | gpt-4.1                            |
| User LLM       | gpt-4.1                            |
| Task split     | base                               |
| Trials         | 3                                  |
| Seed           | 300                                |
| Tau2 commit    | 864350a8971a8f8ee9e7b8472e2edc380a806b0c |

## Cache configuration

LLM caching is enabled via Redis (localhost:6379).  
This requires a **local edit** to `external/tau2-bench-verified/src/tau2/config.py`:

```
LLM_CACHE_ENABLED = False  →  LLM_CACHE_ENABLED = True
```

This edit is **not committed** to the submodule. To reproduce, apply it manually before running.

## Results

| Run   | Score  | Notes                |
| ----- | ------ | -------------------- |
| Run 1 | 0.7632 | LLM calls made       |
| Run 2 | 0.7632 | All calls from cache |

**Deterministic:** yes

Results files: `llm_agent_run.json` (run 1), `llm_agent_run_2.json` (run 2)

## Reproduction commands

```bash
# Prerequisites
brew services start redis
# Apply local cache edit to external/tau2-bench-verified/src/tau2/config.py

# Smoke test (5 tasks, 1 trial)
python -m src.baseline.run --smoke

# Full Gate B run (base split, 3 trials)
python -m src.baseline.run

# Re-run to verify cache determinism
python -m src.baseline.run --out gate_b_run_2
```

## Gate B status

- [x] Smoke test passes
- [x] Full run completes
- [x] Re-run produces identical score
- [x] Gate B frozen (this file + llm_agent_run.json committed)
