# FYP Project Diary

## 16/01/26
Project setup and initial architecture design based on interim report.

## 19/01/26
Create XML tagged prompts using `<role>`, `<goal>` and `<execution history>`. The goal here was to get a basic agent setup running, gave the agent history and gave it rules like "Always Try Before Concluding" and "Never Repeat Successful Actions".

## 12/02/26
Converted codebase to async/await, added Pydantic v2 config models, custom exceptions.

## 17/02/26
Basic agent demo working with simple clustering and vector DB spike.

## 20/02/26
Was at the Warsaw hackathon and looked deeper into the meaning of process mining, realised "process mining" is a mischaracterisation, what I plan to do is agent workflow optimisation / agent memory. Researched Graphiti and Microsoft Trace.

Would a company actually change their codebase to implement this - don't think so:
Pivot from an agent framework, to a layer alongside any agent system. Self-optimising feedback loop: SDK captures traces → collector stores in Postgres + pgvector → analysis discovers optimal paths → SDK returns them at runtime → system improves with every run.

New structure: `sdk/`, `platform/collector/`, `platform/analysis/`, `dashboard/`, `demo/`

Change title to "Self-Optimising AI Agent Workflows through Execution Trace Analysis"

## 21/02/26
Started work on Analysis Engine:
- PM4Py Inductive Miner
- Two-level clustering
- Pareto front for multi-objective optimisation

**Embedding Threshold Calibration Bug** — `similarity_threshold=0.90` was calibrated for ada-002 (OpenAI model) but I ended up using text-embedding-3-small and changing the threshold from 0.90 to 0.60. Later switched to Gemini gemini-embedding-001.

## 22/02/26
Demo Runner — TracingMCPClient for SDK tracing. The agent never knows it's being traced. Guided mode injected as soft constraint now.

**Guided Mode 40% Success Bug** — MCP state persists between rounds. MCPClient marks errors as SUCCESS, agent completes, therefore there are poisoned optimal paths stored. Loop detection relaxed — it was detecting a loop too easily.

## 23/02/26
**Clustering algorithm** — Replaced greedy single-pass subclustering with HAC, greedy clustering was putting unrelated workflows together.

**min_executions Threshold: 10 → 30** — Done research on this and looks like 10 is definitely too low, bumped up to 30.

## 24/02/26
Start work on frontend dashboard — 6 pages: Overview, Traces, Path Comparison, Execution Graph, Insights and Settings. 8 collector API endpoints added.

**Bug** — Compare page crash: null-safe computed values + empty-state.

Start work on per-cluster execution graph + optimal path overlay.

## 25/02/26
Add 5 new tools to demo: `escalate_ticket`, `apply_discount`, `check_warranty`, `get_shipping_status`, `schedule_callback`. Added 5 new scenarios: warranty claim, shipping inquiry, quality complaint, wrong item, cancellation.

Removed hardcoded keyword clustering, switched to HAC on embeddings. Lowered similarity threshold from 0.85 to 0.80 since Gemini embeddings have a compressed similarity range. Cluster naming now done by LLM instead of keyword matching.

Added 5 more scenarios (T-1011 to T-1015) so multiple different tickets cluster together — 4 refund tickets in one cluster, 5 complaint tickets in another, 3 shipping inquiries together. This proves the embedding clustering works across different customers/products with the same intent.

Group-level optimal path computation added so the cluster page shows a properly computed path for the whole group, not just per-variant.

**Bug** — Cross-ticket clustering wasn't working because clusters stored in a dict were overwriting each other when they got the same label. Also "complaining" doesn't contain "complaint" as a substring so keyword matching missed some scenarios. Fixed both, then removed keywords entirely and switched to HAC.

## 27/02/26
Built order fulfillment demo with SQLite-backed MCP server. Every tool returns data the next tool needs — agent can't skip steps. Server rejects wrong math (e.g. wrong discount or total). Ground-truth verification after each scenario checks the actual DB state.

**Key insight**: the platform only adds value when there are real decision points. A linear tool chain (A→B→C→D) has nothing to optimise. Added multi-warehouse routing, returns, and exchanges — real branching.

**Guided mode regression** after adding complexity — went from helping to +96% worse on duration.

Root cause: all fulfillments + exchanges + backorders landed in one cluster, Pareto front picked the backorder path as "optimal" (shortest/cheapest), then served that to fulfillment tasks. Also fragment paths like `["get_order"]` were dominating because they're faster/cheaper than complete paths.

Fixed in two rounds:
1. Stop upserting group-level paths, add minimum support filter, use centroid embeddings
2. Path coverage filter (must be ≥50% of avg trace length), strict min_support (return exploration instead of bad guidance)

After fixes: guided mode beats exploration — 31% faster, 24% fewer steps, 13% cheaper.

## 28/02/26
Expanded to 4 MCP servers (fulfillment, payments, notifications, risk), 31 tools, 43 scenarios. Added promotions and inventory reservation servers to create more decision points and dead-ends for exploration agents.

Standardised task descriptions — removed all detailed step-by-step scenarios, everything is now vague or medium. Agent has to figure out the tools itself.

Made error messages across all MCP servers vague so agents have to reason about failures instead of being told the answer. Added `get_loyalty_discount` tool because gemini-2.5-flash-lite wasn't reading the discount values from the schema description.

Fixed success detection — was trusting the agent's self-report, now uses DB verification as source of truth.

Added `/agents` page with real-time chat view of agent conversations showing LLM prompts, reasoning, tool calls, and guided injection.

## 01/03/26
**Interleaved analysis** — was running analysis only after all rounds finished, so guided mode never activated during the run. Changed to run analysis after each round:

> round1 → analysis → round2 → analysis → etc.

System now genuinely self-improves within a session.

**Automatic regression detection** — if guided mode success rate drops below exploration by more than 10%, the system automatically falls back to exploration mode. Self-correcting — catches bad guidance without manual intervention.

**MCP state verification** — agent sometimes completes the task correctly but never calls "complete", or calls "complete" without actually doing anything. Added `verify_outcome()` that checks actual MCP server state to catch both false negatives and false positives.

## 10/03/26
**ACE-inspired failure warnings** — compared successful vs failed traces to extract what agents commonly get wrong: missing steps (tool in 70% of successes but absent in 40% of failures) and parameter divergence (e.g. wrong warehouse choice). Stored in DB and surfaced in the guided mode prompt as "KNOWN FAILURE MODES".

## 11/03/26
**Statistical hypothesis testing** for guided vs exploration. Mann-Whitney U tests (unpaired, non-parametric) with Hedges' g effect sizes. Duration improvements exist but high LLM variance prevents significance at current sample sizes.

Important lesson: don't remove outliers for this analysis. The long-running failed exploration attempts ARE the effect we're measuring — guided mode prevents those. Removing them erases the improvement.

Found that lowered thresholds (similarity=0.70, min_executions=3) from earlier testing had polluted the optimal path pool with fragment paths.

## 13/03/26
**Outcome-variant path collision problem** — same task description leads to different tool sequences depending on runtime data. Both subclusters have nearly identical embeddings so pgvector picks randomly between them at runtime. Serving the short path to a complex case = bad guidance.

Fix: multi-variant decision tree. Store all variant paths and present them as a branching decision. Agent picks the right variant based on what it discovers at runtime.

## 18/03/26
**Hard constraints were breaking guided mode** — the prompt said "Execute these tools in exact order" and "Do not add extra tools" which made the LLM panic and retry tools instead of reasoning through errors.

Rewrote to soft constraints: "Suggested approach" instead of "Execute in exact order", "GUIDELINES" instead of "RULES". Added "do not retry blindly".

**Auto-generated decision trees** from trace data. Algorithm finds the divergence point between subclusters, then finds the discriminating key in tool responses that separates the groups. Nothing hardcoded.

Fixed min_executions back to 30 — had been lowered to 5 from earlier testing.

## 19/03/26
Analysis pipeline producing zero optimal paths despite 115 workflows. Root cause: 51% overall success rate meant failed workflows polluted every graph edge below the 85% success threshold. Fixed by filtering to successful traces only before building the execution graph. Failed traces still used for pattern detection.

Fixed ground-truth verification — was checking `expected_total` and `delivery_days` which depend on which warehouse the agent picks. Agent could pick a valid but different route and fail verification. Simplified to status-only checks (did the order reach "fulfilled" / "returned"?).

Fixed hardcoded dates in `seed.sql` — orders were drifting outside return windows as real time passed. Replaced with relative dates (`date('now', '-N days')`).

Generalised decision tree labels — was branching on product names which are useless for new queries. Added cardinality filter to skip high-cardinality keys like names/IDs, derive branch labels from distinguishing tools instead.
