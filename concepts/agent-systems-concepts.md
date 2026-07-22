# Core Concepts for Building Multi-Agent Systems

*A conceptual foundation for everything in this repo. Each lesson in the curriculum applies one or more of these ideas in practice. The running example throughout is an ML research workflow — agents launching and monitoring GPU training runs — but the concepts apply to any agent system.*

## Contents

1. [Skill files](#1-skill-files)
2. [Subagent files](#2-subagent-files)
3. [Hooks](#3-hooks)
4. [MCP servers](#4-mcp-servers)
5. [Context engineering](#5-context-engineering)
6. [Orchestration topologies](#6-orchestration-topologies)
7. [Failure handling](#7-failure-handling)
8. [Observability and evals](#8-observability-and-evals)
9. [Cost/latency routing](#9-costlatency-routing)

---

## 1. Skill files

A **skill** is a markdown file (`SKILL.md`) containing knowledge or a workflow, loaded into the model's context *on demand* rather than always. That "on demand" is the entire point. A `CLAUDE.md` file is read every session — it pays context rent constantly, whether relevant or not. A skill costs nothing until it's needed.

**The mechanism.** Each skill has frontmatter with a name and a description. At session start, the model sees only the *descriptions* — a cheap index. When a request matches a description (or the skill is invoked explicitly, like `/launch-run`), the full skill body is loaded into context.

A skill is therefore two artifacts:

- a **trigger** — the description, which determines *when* it fires
- a **payload** — the instructions, which determine *what happens*

Most skill failures are trigger failures: a vague description means the skill never loads, or loads when it shouldn't. Description-writing is a craft of its own.

**Two flavors of skill:**

- **Reference skills** provide knowledge the model consults — your cluster's conventions, your eval framework's API, your team's style guide.
- **Action skills** encode a procedure — "how to launch a sweep: validate config, check GPU availability, submit, log to wandb."

Skills can also bundle scripts and files alongside the markdown, so `/profile-memory` can ship the actual profiling script rather than hoping the model rewrites it correctly each time.

> **Mental model:** a skill is a function you've written in English, with the description as its type signature.

---

## 2. Subagent files

A **subagent** is a separate model instance with its **own context window**, defined by a markdown file specifying its role, system prompt, and — crucially — its allowed tools. The main agent delegates a task to it; the subagent works in isolation; only its final summary returns to the main context.

There are two distinct reasons to use subagents, and it's worth keeping them separate:

**Context isolation.** When an agent greps through 40MB of training logs, all that output lands in context. In the main session, it pollutes everything after it. In a subagent, the mess stays in the subagent's window and dies with it — the main session receives only "run 47 OOM'd at step 12k; runs 48–52 healthy; val loss trending down." You're buying signal-to-noise.

**Capability restriction.** A subagent's file can deny tools. A `run-triager` that can read files and query wandb but *cannot* execute bash or edit files is structurally incapable of breaking a training run, no matter how confused it gets. This is least-privilege applied to agents — a stronger guarantee than prompting "please be careful."

**The key limitation:** communication is one-way and summary-shaped. The subagent can't ask the main agent questions mid-task, and the main agent sees only what the subagent chooses to report. That lossy handoff is where subagent systems fail — which is why several of the concepts below exist.

---

## 3. Hooks

Hooks are **deterministic scripts attached to lifecycle events** — before a tool runs (`PreToolUse`), after it runs, when a session starts, when the agent stops, and so on.

The word to hold onto is *deterministic*. Everything else in an agent system is probabilistic: a prompt is a request, a skill is a suggestion, and the model can misread either. A hook is code. It runs every time, and a `PreToolUse` hook that exits with a blocking status *prevents the tool call from happening* regardless of what the model intended.

This gives you a clean division of labor:

> **Prompts for judgment, hooks for law.**

- "Prefer smaller batch sizes when memory is tight" is judgment → `CLAUDE.md`.
- "Never delete anything under `/checkpoints`; never launch an instance above $2/hr" is law → a hook, because it must hold at 3am on the 200th iteration when the model's attention is somewhere else.

Hooks also do automation, not just blocking: fire a notification when the agent stops, auto-format code after edits, log every tool call to a file (foreshadowing observability).

The design skill is deciding what's law vs. judgment. Make too much law and the agent can't work; too little and you're trusting a stochastic process with your checkpoints.

---

## 4. MCP servers

**MCP (Model Context Protocol)** is a standard for giving models **structured tools** instead of a bash prompt. An MCP server is a small program exposing typed functions — `get_run_metrics(run_id) → {loss: float, ...}` — with the protocol handling discovery ("what tools exist and what are their schemas") and transport (stdio for local processes, HTTP for remote).

Why this beats "just use bash + the CLI" — three failure modes disappear:

1. **Parsing.** The model no longer scrapes human-formatted CLI text and occasionally misreads a number; it gets JSON.
2. **Discovery.** The model no longer guesses CLI flags from training data that may be outdated; the schema tells it exactly what's callable.
3. **Safety.** The server only exposes what you built. A wandb MCP server with read-only tools *cannot* delete runs, period — whereas bash access to the CLI can do anything the CLI can.

**The deeper shift:** an MCP server is where you encode your *domain's API for agents*. Writing one forces the question "what are the atomic operations of my workflow?" — and the quality of that answer shows up everywhere downstream. A well-designed tool surface makes any agent look smart; a bad one makes every agent look dumb.

> **Mental model:** MCP is the boundary layer between the probabilistic world (the model) and the deterministic world (your infrastructure). Design it with the same care as any public API.

---

## 5. Context engineering

The discipline underneath everything above: **deciding what information exists in each agent's window at each moment.**

The premise: context is a scarce, degrading resource. It's finite; long contexts dilute attention (models attend worse to the middle of a huge window); and every token costs money and latency. The question is never "can I fit this?" but "does this earn its place?"

**Core techniques:**

**Layering by lifetime.**
- Permanent (project conventions) → `CLAUDE.md`
- Situational (how to run a sweep) → skills, loaded on demand
- Ephemeral (this run's logs) → subagents, summarized then discarded

**Compaction and externalization.** Instead of keeping history in the window, write state to files — a lab notebook, a task list, a decisions log — and read back only what's needed. Files are context you can page in and out. This also makes work *resumable*: an agent that crashes can reconstruct its situation from the notebook rather than from a lost conversation.

**Summarize at boundaries.** Every handoff (subagent → main, session → session, agent → agent) should pass a *deliberate* summary, not raw history. The design question is the summary *schema*: for an analyst agent, perhaps `{runs examined, verdicts, anomalies, recommended next config}`. An unstructured "here's what I found" is where information silently dies.

**Poisoning awareness.** Once something wrong enters context — a hallucinated metric, a stale file — everything downstream conditions on it. Context engineering includes hygiene: prefer tool-fetched facts over remembered ones; re-read files rather than trusting the copy from 50 turns ago.

> If you learn only one concept deeply from this list, make it this one. Every multi-agent failure below has a context-engineering failure at its root.

---

## 6. Orchestration topologies

The recurring shapes of multi-agent systems. Four cover almost everything:

**Pipeline (sequential).** A → B → C, each transforming the previous output. *Example: lit-review → experiment design → implementation.* Simple, debuggable, the right default. Weakness: errors propagate — B faithfully builds on A's mistake.

**Orchestrator–worker.** One planner decomposes the goal, dispatches tasks to workers, integrates results. *Example: a planner proposes experiment configs; executors run them.* The orchestrator is the single point of judgment — spend your best model and best prompting there. Weakness: the plan is only as good as the orchestrator's visibility into what workers actually did (context engineering again).

**Parallel fan-out + aggregation.** Identical or varied workers run simultaneously; an aggregator merges. *Example: multi-seed sweeps, or three agents propose designs and a judge picks.* Cheap wall-clock wins; the aggregator is the hard part.

**Evaluator–optimizer loop.** A generator produces, a critic judges, the generator revises. A metric-driven experiment loop is a degenerate one-agent version of this (the metric is the critic). An LLM critic catches qualitative problems metrics miss — but beware **critic–generator collusion**, where both share the same blind spot because they're the same model.

> **The meta-lesson:** start with the least topology that works. A single agent with good skills beats a badly-coordinated five-agent system every time. Topology adds coordination cost — only pay it when a single context window demonstrably can't hold the job.

---

## 7. Failure handling

Supervised single-session use hides failure handling because *you* are the failure handler — you check in, notice the dead run, fix it. An autonomous system must do this itself, and it's less about intelligence than about mechanical properties you design in:

**Idempotency.** Every step must be safe to run twice, because retries *will* happen. "Launch run" must become "launch run if no run with this config hash exists." Without this, a retry after a timeout double-books your GPUs or double-writes your results.

**Retries with classification.** Distinguish *transient* failures (spot preemption, network blip → retry with backoff) from *deterministic* ones (OOM, bad config → retrying is pure waste; something must change). A cheap **preflight** — a short, low-cost trial run that catches bugs before the expensive run — is failure handling by design: fail early where failure is cheap.

**Timeouts and watchdogs.** Every agent action needs a "how long is too long," and something *outside* the agent must enforce it. A hung training process with an agent politely waiting forever is the classic 3am failure.

**Checkpointing state.** If the system dies at step 6 of 10, it should resume from 6, not restart from 1. This falls out naturally if you externalized state to files (context engineering pays off here).

**Escalation.** A defined "I'm stuck" path: stop, write a summary of the situation, notify the human. The worst failure mode isn't crashing — it's an agent confidently improvising past a problem it doesn't understand. Design the system so giving up gracefully is easy and cheap.

> **Design heuristic:** assume every component fails at the worst moment, and ask "what happens next?" for each. If the answer is "the agent figures it out," that's not a plan.

---

## 8. Observability and evals

Two related answers to "is this system actually working?"

### Observability — seeing what happened

Minimum viable version: **structured logs** of every agent action — timestamp, agent, tool called, arguments, result, tokens spent. A `PostToolUse` hook can capture this for free.

From logs you build **traces**: the causal chain of one task across agents ("planner proposed X → executor launched → OOM → retry → analyst summarized"). Without traces, debugging a multi-agent system is archaeology; with them, it's reading.

Dedicated tooling exists to pipe agent activity into trace UIs, but JSON-lines files plus a notebook gets you 80% of the value — and teaches you what the tools are actually doing. If you use wandb for training runs, you already have the instinct: this is wandb for *agent behavior* instead of model training.

### Evals — judging quality

Two levels:

- **Component evals.** Does each skill trigger when it should? Does the analyst subagent correctly identify a diverged run? Build small test sets (10 log files, 3 with problems — does it flag the right 3?) and run them on every change, exactly like unit tests.
- **System evals.** End-to-end: given this research question, does the loop produce a sensible experiment sequence? "Good" is fuzzy here; common tools are golden-path checks (did it complete the expected phases?), outcome metrics (did val loss improve?), and LLM-as-judge for qualitative parts (with the collusion caveat from §6).

> **The discipline that matters: evals before expansion.** Every added agent or skill makes the system harder to assess by vibes. The teams that scale agent systems are the ones for whom "run the eval suite" is as reflexive as running pytest.

---

## 9. Cost/latency routing

Every agent call has a model choice, and the spread between model tiers is large — roughly an order of magnitude in cost between top and cheap tiers, plus big latency differences. Routing is deciding **which intelligence level each task actually needs**:

| Role | Tier | Why |
|---|---|---|
| Planner / orchestrator | Top | Few calls, but every downstream action depends on its judgment; errors multiply through the system |
| Executors (mechanical work) | Mid | Edit config, launch, monitor — competence needed, brilliance not |
| Grunt work (scan 50 logs, extract metrics, format summaries) | Cheap | This is where call volume lives, so it's where savings live |
| Critic / evaluator | Top (counterintuitively) | A weak critic rubber-stamps everything and silently destroys your quality loop |

Beyond model choice:

- **Parallel vs. serial.** Fan-out costs the same tokens but collapses wall-clock time — worth it when a human is waiting, irrelevant overnight.
- **Caching.** System prompts and skills that prefix every call can be cached; stable prefix design is a real cost lever.
- **Budget guards.** A hook or SDK-level cap on spend per task. A retry loop with no budget ceiling is how people wake up to shocking bills — on metered cloud GPUs, this is not optional.

> **The practical method:** don't theorize the routing. Run everything on the top tier, use your traces (§8) to see where tokens went, downgrade the high-volume/low-judgment calls, and check your evals (§8) didn't regress. Routing decisions should be measured, not vibed.

Notice how the last three concepts form one loop: observability tells you where cost and failure live, evals tell you whether changes hurt, routing acts on both.

---

## How to actually learn these

Don't study these in sequence. **Build a real system and let each concept arrive as the solution to a pain you just felt:**

- Context bloat → skills and subagents
- The 3am dead run → failure handling
- "Why did it do that?" → observability
- The bill → routing

Concepts learned as painkillers stick. Concepts learned as vocabulary don't.
