# HYPOTHESES.md — Pre-Registration

> **This document is frozen before any experimental runs.** It is committed to git
> *prior* to executing any baseline, optimization, or decomposition code. Its purpose
> is to commit, in advance, to (a) what is claimed, (b) what result would confirm the
> claim, and (c) what result would falsify it — so that no conclusion can be fitted to
> the data after the fact.
>
> **Edit policy:** once committed, this file is not edited. If reality forces a change
> of plan, that change is recorded in a *new*, dated `AMENDMENTS.md` entry explaining
> what changed and why — the original prediction stays visible.
>
> Commit hash of registration: `22ca00c27eac14b233a1a524fe1a4ccb7499e031`
> Date of registration: `2026-05-27`

---

## 0. Scope (binding)

- **Benchmark:** tau2-bench-**verified** (amazon-agi fork), to avoid attributing
  benchmark-label errors to "semantic collisions."
- **Domain:** **retail only.** Every claim in this document is scoped to tau2 retail.
  No claim about tool-calling agents *in general* is made or implied. Phrasing such as
  "in tool agents" is forbidden in reporting; the permitted phrasing is "in tau2 retail."
- **Model:** a single fixed model for both agents, recorded in the lockfile. The
  monolithic baseline and the decomposed agent use the **same model and the same tools**.
  Any difference in results is therefore attributable to architecture, not model quality.
- **Variance:** every reported metric is the mean over **N ≥ 3 trials**, with the
  trial-to-trial spread reported. "Improvement" and "regression" are judged against this
  spread (see §3, variance band).

---

## 1. Primary Claim (the claim this repo lives or dies by)

**Decomposition improves a target behavioral objective without a behavioral regression
on its coupled objective — in tau2 retail, on the held-out test split.**

- The unit of evaluation is the set of **derived behavioral metrics** (precision, recall,
  F1 on tool calls vs. gold actions, hallucinated-argument rate, clarification rate),
  computed identically over both agents' traces by code blind to which agent produced them.
- "Behavioral objective" and "coupled objective" refer to a specific metric pair (the
  **headline pair**), selected as described in §2.
- This is a **directional** claim: the decomposed agent moves the target objective in the
  intended direction while the coupled objective does **not** regress beyond the variance
  band (§3).

**tau2 task reward is NOT the primary claim.** Reward is a secondary, explicitly uncertain
measurement (§4). The repo's success is defined by behavioral metrics, not reward.

---

## 2. The Headline Pair (selection rule, frozen now; identity filled at Gate D)

The single coupled-objective pair that constitutes the headline test is **not fixed in
advance**, because it is not yet known which behavioral tension tau2 retail surfaces most
sharply. To keep this honest, the selection is bound by the following rule:

- The headline pair is chosen **from train-split tension analysis only** (the baseline
  failure analysis at Gate D), and **frozen before any contact with the test split.**
- Choosing the pair from *train* is legitimate: train exists to make modeling/measurement
  decisions. The test split, which the pair will be evaluated on, never informs the choice.
- **Explicitly forbidden:** selecting or changing the headline pair after observing any
  test-split result. That would be fitting the hypothesis to the outcome.

**Headline pair (filled at Gate D, before test):** `[FILL: e.g. "recall ↑ without
precision/hallucination regression"]`
**Train-split evidence that motivated this choice:** `[FILL: reference to the baseline
train-split tension table]`
**Date pair frozen / commit hash:** `[FILL]`

The candidate pairs under consideration (the tensions the README predicts) are:
recall vs. precision; recall vs. hallucinated-argument rate; autonomy/completion vs.
hallucination; clarification rate vs. completion. The chosen pair will be one coupling
drawn from these.

---

## 3. What Counts as Confirmation vs. Falsification (operational)

The claim is stated so that it can actually fail on the data.

**Variance band.** From the N≥3 baseline trials, establish the trial-to-trial standard
deviation for each metric. A change is "real" only if it exceeds this band; a change
inside the band is treated as noise and counts as **no change** (neither improvement nor
regression). The band is computed and frozen at Gate C, before comparison.

**CONFIRMED if, on the held-out test split:**
- the decomposed agent improves the headline pair's *target* objective by an amount
  exceeding the variance band, **and**
- the headline pair's *coupled* objective does **not** regress by an amount exceeding the
  variance band.

**FALSIFIED if, on the held-out test split:**
- the target objective does not improve beyond the variance band, **or**
- the coupled objective regresses beyond the variance band when the target improves
  (i.e. the monolith's tradeoff reappears inside the decomposed agent).

**Declared cost, exempt from falsification: latency.** Decomposition is *expected* to cost
latency (multiple stages). A latency regression does **not** falsify the primary claim. It
is reported as a known, accepted cost in the README's "where decomposition got worse"
section. The primary claim is explicitly about the **behavioral** axis, not the latency axis.

**Inter-stage error class:** if decomposition introduces a new failure mode (e.g. stage-2
consuming stage-1's wrong output), this is reported honestly under "where decomposition got
worse." Whether it falsifies the claim depends solely on whether it pushes the *coupled
behavioral objective* beyond the variance band — latency and qualitative new-failure
descriptions do not, by themselves, falsify.

---

## 4. Secondary Claim (predicted, but genuinely under test)

**Prediction:** improvements in the derived behavioral metrics will propagate to tau2's
task reward (`reward_basis` / `evaluation_criteria.actions`).

This is **not** load-bearing. It is registered as a prediction whose outcome is reported
either way. Two caveats are registered in advance:

1. **Path vs. destination.** Behavioral metrics measure the *path* (per-decision quality);
   tau2 reward measures the *destination* (rewarded end state). These are correlated but
   not identical; an agent can clean up its path without changing its reward, or vice versa.
2. **Shared-source non-independence.** Because the derived turn-level labels are derived
   from tau2's `evaluation_criteria.actions` (the same rubric reward is keyed on), any
   observed metric↔reward correlation is **partly built-in, not discovered.** This is
   disclosed; the metric/reward relationship is interpreted with this entanglement in view.

---

## 5. Outcome Matrix (interpretation committed in advance)

Whatever happens, the reading below is the committed interpretation. No post-hoc spin.

**Case A — behavioral metrics improve (per §3) AND reward improves.**
Primary claim confirmed; secondary prediction also supported. Strongest outcome:
decomposition improves the behavioral tradeoff *and* behavioral metrics act as leading
indicators of reward (read with the §4.2 entanglement caveat).

**Case B — behavioral metrics improve (per §3) while tau2 reward stays flat (within its
band). This is a primary target outcome, reported as a headline finding.**
This case confirms the primary claim (which never depended on reward) *and* delivers the
repo's sharpest contribution: a direct, quantified demonstration that tau2's aggregate
end-state reward is **insensitive to real differences in behavioral path quality.**
Mechanism: both agents reach the same rewarded end states, but the monolith reaches them
via fabricated-then-recovered arguments, unnecessary clarification, and walked-back tool
calls, while the decomposed agent reaches them cleanly — and end-state reward is
structurally blind to this difference (reward saturation on already-passed tasks;
indifference to recoverable mid-trajectory errors; dilution by tasks where neither
architecture is the bottleneck).
This is **not** framed as "decomposition didn't help." It is framed as: *decomposition
improved measurable behavioral quality in a dimension the field's standard aggregate reward
cannot observe.* To earn this framing, the report **must** (i) justify the
production-relevance of each improved behavioral metric, and (ii) exhibit at least one
**matched-pair task** — identical reward, visibly different trace quality — as a concrete
existence proof alongside the aggregate result.
Headline statement of the finding, if it holds: *two agents, identical task-success scores,
materially different behavioral trustworthiness — and the benchmark cannot distinguish them.*

**Case C — reward moves BUT behavioral metrics are mixed/unmoved (per §3).**
Primary claim **falsified or unsupported.** Reported honestly as such. Interpretation:
decomposition's benefit (if any) is not located where the thesis predicted; the behavioral-
tension account did not hold in tau2 retail. No reframing to rescue the thesis.

**Case D — neither moves.**
Primary claim falsified. Reported as a null result. The baseline failure-analysis artifact
(Gate D / `reports/baseline/`) remains a standalone contribution regardless.

---

## 6. Frozen-Artifact Gates (referenced by PLAN.md)

This pre-registration is enforced by build gates; metric definitions and the variance band
are frozen *before* the comparison that could be influenced by them.

- **Gate A:** this file + scope + model + domain + trial count committed. (now)
- **Gate B:** baseline traces frozen (stock agent, unmodified).
- **Gate C:** metric definitions + analysis axes + variance band frozen — applied
  identically to both agents, blind to source.
- **Gate D:** baseline failure analysis frozen; **headline pair (§2) selected from train
  only and frozen**; decomposition boundaries chosen from train only.
- **Gate E:** decomposed agent frozen — no further tuning.
- **Gate F:** held-out test results frozen; README numbers filled; claim adjudicated
  against §3 and §5. **If the result is Case B**, two reporting obligations are binding
  before publication: (i) a written production-relevance justification for each improved
  behavioral metric, and (ii) at least one reproducible **matched-pair task** (identical
  tau2 reward, visibly different trace quality) included as a concrete existence proof.

---

## 7. One-Sentence Registration

In tau2 retail, on a held-out test split, decomposing a monolithic tool-calling agent into
coherent behavioral spaces will improve a train-selected target behavioral objective beyond
trial variance without a beyond-variance regression on its coupled behavioral objective
(latency exempted as a declared cost); reward propagation is predicted but not required, and
a metrics-improve-while-reward-flat result is a confirmation of the thesis, not a failure.
