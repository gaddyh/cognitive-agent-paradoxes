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

| Run   | Score | Notes                 |
| ----- | ----- | --------------------- |
| Run 1 | FILL  | LLM calls made        |
| Run 2 | FILL  | All calls from cache  |

**Deterministic:** FILL (yes/no)

Results file: `gate_b_run.json`

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

- [ ] Smoke test passes
- [ ] Full run completes
- [ ] Re-run produces identical score
- [ ] Gate B frozen (this file + gate_b_run.json committed)
