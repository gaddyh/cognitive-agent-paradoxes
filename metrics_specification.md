# Metrics Specification

## Dataset Summary

These are global behavioral properties of the benchmark world.

Not performance metrics.

They characterize:

* task diversity
* interaction depth
* tool dependency structure
* read/write asymmetry
* behavioral entropy

---

# Tool Entropy

Measures distributional diversity of tool usage.

Conceptually:

```text
H = -Σ p(tool) log2 p(tool)
```

High entropy:

* many tools used relatively evenly
* broader behavioral space
* harder routing problem

Low entropy:

* a few dominant tools
* narrow behavior space

Why important:

Shows whether the agent lives in a concentrated or fragmented action world.

This is essentially:

> action-space uncertainty

---

# Avg Tools / Simulation

Measures operational density.

Higher:

* more multi-step planning
* more state tracking
* more opportunities for compounding errors

This approximates:

> interactional cognitive load

---

# Avg Turns Before Write

Measures how long the agent must maintain context before committing a state-changing action.

Higher:

* larger memory horizon
* delayed commitment pressure
* more grounding dependency

This is critical to the thesis because:

> write operations require higher confidence thresholds

---

# Read / Write Ratio

Measures environmental asymmetry.

High read/write ratio means:

* the agent mostly gathers evidence before acting

This reveals:

> epistemic burden before irreversible actions

---

# Cognitive Burden Breakdown

This section constructs:

> a cognitive-pressure decomposition per tool

Not just difficulty.

But *why* the tool is difficult.

---

# Extraction Burden

Derived from:

* number of required arguments
* argument structural complexity

Example:

```text
modify_user_address
```

requires many structured fields.

Meaning:

How much structured information must be extracted from language.

This measures:

> semantic parsing pressure

---

# Memory Burden

Derived from:

* average turns between first mention and actual tool call

Higher:

* requires long-range conversational retention

Meaning:

> delayed dependency pressure

This is important because:

> monolithic agents often collapse under long-horizon dependencies

---

# Readiness Burden

Measures whether the tool requires explicit confirmation/readiness before execution.

Example:

* write operations require commitment confirmation

Meaning:

> action authorization pressure

This captures:

* hesitation
* premature action
* over-eagerness

---

# Reasoning Burden

Derived from:

* average preceding chain depth

Meaning:

* how many intermediate operations precede the action

Example:

```text
find_user
→ get_order
→ get_product
→ exchange_items
```

This measures:

> dependency-chain complexity

Important because:

> errors compound geometrically across chains

---

# Grounding Burden

One of the most important metrics.

Measures:

* fraction of arguments not explicitly present in user language

Meaning:
the agent must:

* retrieve
* infer
* chain
* normalize
* resolve references

Example:

User says:

```text
replace the blue shoes with the cheaper ones
```

The agent must infer:

* item_ids
* product_ids
* candidate replacement mapping

This is:

> semantic grounding pressure

---

# Argument Emergence Matrix

Measures:

> where structured state originates

This functions as a causal observability layer for argument generation.

---

# Explicit

Argument appears directly in the user message.

Characteristics:

* low ambiguity
* low cognitive burden

---

# Tool-Chained

Argument originates from prior tool outputs.

This measures:

> inter-tool dependency flow

Example:

```text
order_id obtained from get_order_details
```

This is a major source of agent fragility.

---

# Grounding

Argument is not explicitly stated but is recoverable.

Example:

```text
my latest order
→ resolve order_id
```

This measures:

> semantic interpretation pressure

---

# Inference

Argument unresolved or hallucinated.

This measures:

> unsupported completion pressure

Important because:

> monolithic agents often over-complete missing state

---

# Failure Heatmap

This is the:

> cognitive failure localization layer

---

# Failures By Tool

Measures:

* which operations collapse most frequently

Purpose:

* identifies operationally unstable tools

---

# Failures By Cognitive Stage

Moves evaluation from:

```text
the agent failed
```

to:

```text
the failure originated in a specific cognitive phase
```

Examples:

* lookup
* reasoning
* action
* auth
* escalation

This is substantially more diagnostic.

---

# Failures By Argument

Measures:

* which semantic entities most frequently participate in failures

Examples:

* order_id
* item_ids

Meaning:

The bottleneck may not be tool selection itself.

It may instead be:

> state grounding and entity tracking

---

# Cognitive Complexity Score

This is NOT a scientific truth metric.

It should be presented as:

> a heuristic composite pressure index

Purpose:

* approximate the total cognitive pressure induced by a tool

Conceptually:

```text
tool difficulty ≈
information extraction
+ memory retention
+ grounding pressure
+ action risk
+ reasoning depth
```

This is defensible because:

* every component is observable
* every component corresponds to measurable behavior

---

# Conceptual Thesis

The report implicitly argues that:

> different tools induce different cognitive geometries

Some tools are:

* retrieval-heavy
* grounding-heavy
* memory-heavy
* commitment-heavy
* reasoning-chain-heavy

A monolithic agent must optimize all of these simultaneously.

This creates:

* metric tension
* semantic collisions
* unstable optimization behavior
* Pareto tradeoffs between competing objectives
