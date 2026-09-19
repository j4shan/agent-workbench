# Ensemble patterns for improving AI agent output quality

**Investigated:** 2026-09-19. **Scope:** published research and engineering write-ups on running several
AI agents over one problem to raise the quality of a single output, with emphasis on workloads whose
output no validator can score.

**Reading note.** Findings are marked with a confidence tag. `[strong]` means several independent
studies agree or the result comes from a large controlled evaluation. `[moderate]` means one solid
study or a consistent engineering report. `[weak]` means a single claim taken from an abstract or
summary that I did not verify against the full text. Every quantitative figure below carries the
benchmark it was measured on; none of them transfer to a new workload without re-measurement.

---

## 1. Objective and the shape of the problem

The goal is to spend more tokens to get a *better* single answer, not more answers. The classic
ensemble argument — average away independent noise — needs three things to hold:

1. **Diversity.** Branch errors must be substantially uncorrelated.
2. **An aggregator.** Something must turn N candidates into one output.
3. **A signal the aggregator can act on.** Majority voting needs answers that can be compared for
   equality; ranking needs a scorer whose ordering tracks the quality you care about.

For math and code, (3) is cheap: an answer is right or wrong, and a verifier or exact-match vote
supplies the signal. For creative writing, interior design, and visualization rendering, (3) is the
hard part. There is no equality relation over candidates, no verifier, and the ground truth is an
aggregate of human judgments that you do not have at inference time. **Most of the published wins
from ensembling come from exploiting (3); when (3) is weak, the wins shrink or invert.** That single
fact organizes the rest of this report.

A second framing point. The useful axis is not "one agent vs. many agents" — it is **parallel vs.
sequential test-time compute**. Parallel means sample N candidates and pick or merge. Sequential
means generate, critique, revise. On subjective and multimodal work the sequential side currently
has the stronger evidence, and the strongest systems use both.

---

## 2. Tested ensemble patterns

### 2.1 The standard taxonomy

The LLM-ensemble survey splits methods by *when* the ensemble happens relative to inference
([Harnessing Multiple LLMs, arXiv 2502.18036](https://arxiv.org/html/2502.18036v1)):

| Stage | Mechanism | Fit for unverifiable work |
|---|---|---|
| Before inference | Route the query to the best-suited model | Useful for cost control, not for quality lift on a single hard task |
| During inference | Fuse logits or token distributions across models | Requires logit access and vocabulary alignment; out of reach for a tool-using agent harness |
| After inference | Generate full responses, then select or merge | **The only stage that fits an agent ensemble**, since branches are opaque tool-using processes |

The pattern described in the objective — identical context, identical tools, configurable models,
free-form exchange, optional coordinator — is an after-inference ensemble with optional
mid-flight communication. Everything below concerns that regime.

### 2.2 Parallel sample-and-select

**Self-consistency (majority vote over N samples).** The baseline that every multi-agent paper has
to beat, and frequently does not. `[strong]` Under matched token budgets, self-consistency beats
most published multi-agent debate frameworks on reasoning benchmarks
([arXiv 2502.08788](https://arxiv.org/abs/2502.08788), 5 debate methods × 9 benchmarks × 4 models).
Its weakness is saturation: it plateaus quickly and does not convert extra budget into gains past a
small N ([arXiv 2510.20963](https://arxiv.org/html/2510.20963v2) reports roughly 3 points of
variance across the scaling range).

It also does not apply directly to free-form output, since there is no answer to count. Two
adaptations exist:

- **Universal Self-Consistency (USC)** — hand all N candidates to an LLM and ask it to pick the most
  consistent one. Works on summarization and open-ended QA where plain self-consistency cannot run
  ([arXiv 2311.17311](https://arxiv.org/abs/2311.17311)). `[moderate]`
- **Embedding-based agreement** — cluster the N generations in representation space and return a
  representative of the densest cluster; clustering plays the role that exact-match counting plays
  in classical self-consistency ([arXiv 2606.12003](https://arxiv.org/html/2606.12003)). `[weak]`

Both trade "most correct" for "most typical". On creative work that is an active hazard: the modal
candidate is by construction the least surprising one. Treat consistency-based selection as a
safety mechanism for factual spine, not as a quality selector for voice or design.

**Best-of-N with a scorer.** `[strong]` **BoN is the pattern that fails most clearly on subjective
tasks.** On the LeWiDi-2025 tasks (sarcasm, irony, paraphrase, NLI — chosen precisely because
annotators disagree), BoN with step-wise scoring was competitive in exactly one of the tested
settings and often lost to plain averaging and majority voting while costing more
([arXiv 2510.12516](https://arxiv.org/html/2510.12516)). The diagnosed causes generalize beyond
that benchmark: reasoning steps on subjective tasks are vague enough that a judge cannot
discriminate among them, and models spend far fewer thinking tokens on subjective prompts than on
math. The same paper's BoN *oracle* (pick the best candidate with hindsight) was strong — the
candidates were there, the selector could not find them. That gap is the whole problem in one
number.

Verifier-based scaling is more robust than verifier-free scaling in general
([arXiv 2503.01422](https://arxiv.org/pdf/2503.01422) and related). So for unverifiable workloads,
expect the selection step, not the generation step, to be your quality ceiling.

**Selection mechanics matter more than candidate count.** `[moderate]` Pairwise comparison beats
absolute rubric scoring for open-ended output, because the judge discriminates between two concrete
artifacts instead of calibrating an invented scale. Reported gains of roughly 10% for ranking-based
selection over discrete and continuous scoring, and — importantly — discrete and continuous
scoring plateau after about N=5 while ranking keeps improving with N
([Arena-Lite, arXiv 2411.01281](https://arxiv.org/html/2411.01281v5); Tournament-GRPO,
[arXiv 2605.26958](https://arxiv.org/html/2605.26958)). A seeded single-elimination bracket gets
close to full round-robin accuracy at O(N) comparisons instead of O(N²). Always run each comparison
in both orders to cancel position bias.

**Judge reliability.** `[moderate]` LLM judges reach roughly 80–85% agreement with human raters on
well-specified tasks, which is around human-to-human agreement
([Openlayer](https://www.openlayer.com/blog/llm-as-judge-evaluation-guide)), and structured literary
evaluation with ontology-grounded dimensions reports much higher inter-rater agreement
([SAGE, arXiv 2605.07102](https://arxiv.org/pdf/2605.07102)). But there is a documented gap between
*reliability* and *validity*: judges can be highly self-consistent while systematically wrong, and
they carry verbosity, position, and self-preference biases
([arXiv 2606.19544](https://arxiv.org/html/2606.19544v1)). A reliable-but-invalid judge is worse
than no judge in an ensemble, because it converts the whole compute budget into a confident march
toward its own bias.

### 2.3 Aggregation and fusion

**Mixture-of-Agents (MoA).** `[strong]` Layers of proposer models, each layer seeing the previous
layer's concatenated outputs, with a final aggregator that synthesizes rather than selects. Reported
65.1–65.8% on AlpacaEval 2.0 against 57.5% for single GPT-4o
([arXiv 2406.04692](https://arxiv.org/abs/2406.04692), ICLR 2025). Two details make this the most
transferable result for unverifiable workloads:

- AlpacaEval and MT-Bench are *preference* benchmarks, not correctness benchmarks. This is one of
  the few large ensemble wins measured on the kind of judgment the objective cares about.
- MoA beats an LLM-ranker baseline on the same candidate pool, which means the aggregator is
  genuinely synthesizing across candidates rather than picking a winner. When candidates have
  complementary partial merit — a good structure here, a good passage there — **merge beats select**.

MoA-Lite (2 layers, small aggregator) beat GPT-4o on quality at lower cost, so the pattern is not
purely a compute-dumping artifact.

**LLM-Blender.** Two-stage: PairRanker orders candidates pairwise, GenFuser writes a new response
conditioned on the top-k. Same lesson as MoA at smaller scale — ranking narrows, fusion produces.

**Design implication.** For creative and design output, prefer an architecture that ends in
*synthesis over a shortlist* rather than *selection of a single branch*. Selection discards the
complementary material that justified running the branches.

### 2.4 Debate and critique

This is where the literature has turned sharply skeptical since 2025, and the nuance is worth
carrying precisely.

**The negative case.** `[strong]`
- Multi-agent debate frequently loses to chain-of-thought and self-consistency at equal or greater
  inference cost ([arXiv 2502.08788](https://arxiv.org/abs/2502.08788)).
- Unguided homogeneous debate produces no statistically significant gain over isolated
  self-correction while adding heavy overhead; isolated self-correction reached 66.7% where debate
  reached 60.7% on the tested benchmark
  ([The Cost of Consensus, arXiv 2605.00914](https://arxiv.org/pdf/2605.00914)).
- The most damaging finding in that paper: **task-relevant peer rationales gave no measurable
  benefit over task-irrelevant ones.** If true in general, much of debate's apparent value is a
  re-sampling effect wearing a collaboration costume.
- Sycophancy propagates between agents, expressed disagreement decays over rounds, and correlated
  errors rise as agents converge — groupthink with a token bill
  ([arXiv 2604.02668](https://arxiv.org/html/2604.02668v2),
  [arXiv 2606.00820](https://arxiv.org/html/2606.00820),
  [arXiv 2509.05396](https://arxiv.org/pdf/2509.05396)).
- "A mixture of diverse models improves quality" does not hold unconditionally: a weak agent in the
  pool drags the group down.

**The positive case, and its conditions.** `[moderate]` The most useful single paper here is
*When and Why Does Multi-Agent Debate Fail* ([arXiv 2510.20963](https://arxiv.org/html/2510.20963v2)),
which separates three framings and finds they are not the same intervention at all:

| Framing | Incentive | Result |
|---|---|---|
| Competitive (persuade) | Win the exchange | Collapses. Fabricated evidence, overconfident claims; F2 fell to 24.89 vs ~82 for a single agent in one pairing |
| Consensus-seeking (agree) | Converge | Suppresses the disagreement signal that distinguished right from wrong |
| Collaborative (surface complementary evidence, quote exactly, concede valid points) | Find the truth together | +4 points over single agents; **+4.3 points over self-consistency at matched token budget**, and it keeps scaling where self-consistency plateaus |

Conditions under which collaborative debate is worth its cost, per the same work: **heterogeneous
models from different providers**, a baseline that is not already above ~90%, and a protocol that
requires evidence citation. With homogeneous models and no protocol, skip it.

**Critique-and-revise (sequential) has better evidence for subjective work than debate (parallel).**
`[moderate]`
- Blind peer review over creative writing — multiple independent reviewers, author identity hidden,
  structured critique, iterative revision — beats direct self-revision and single-reviewer
  baselines ([LLM Review, arXiv 2601.08003](https://arxiv.org/pdf/2601.08003)).
- On compositional image generation, a VLM critic + editor loop **beat compute-matched parallel
  sampling** and was preferred by human evaluators 59% of the time
  ([Iterative Refinement Improves Compositional Image Generation,
  arXiv 2601.15286](https://arxiv.org/html/2601.15286)). The compute-matched comparison is what
  makes this one load-bearing for the visualization-rendering case.
- Generation / verification / correction as three explicit roles with structured feedback is the
  recurring shape in multimodal pipelines
  ([FineGen, arXiv 2606.07645](https://arxiv.org/html/2606.07645)).
- Long-form narrative systems (StoryWriter, Agents' Room, Dramaturge) decompose into planning,
  drafting, and refinement roles rather than running identical branches, and report wins on both
  human and automated evaluation. `[weak]`

**Reading of the combined evidence.** Debate's failures are failures of *protocol*, not of the idea
that more branches help. The interventions that survive scrutiny all do the same thing: they force
branches to contribute material the others lack, and they keep a branch from folding to social
pressure. Blind review does it by hiding identity. Collaborative framing does it by requiring exact
quotes. Heterogeneity does it by making the priors genuinely different.

### 2.5 The diversity input, which is cheaper than another agent

`[moderate]` Post-training alignment causes mode collapse: annotators prefer familiar text, so
aligned models concentrate on typical outputs. **Verbalized Sampling** — asking for k candidates
*with their probabilities* in one prompt — recovers 1.6–2.1× diversity on creative writing with no
loss of quality or safety, training-free, and larger models benefit more
([arXiv 2510.01171](https://arxiv.org/abs/2510.01171)).

This matters for an ensemble design because N identical agents on identical context produce
correlated samples, and correlated samples are exactly what defeats ensembling. Before paying for
more branches, buy diversity at the prompt: verbalized sampling, different personas or design
briefs per branch, different models, different temperatures. **A 3-branch ensemble with real
diversity beats an 8-branch ensemble of near-duplicates, at less than half the cost.**

---

## 3. Synchronization patterns

### 3.1 Vocabulary

The communication-centric survey ([arXiv 2502.14321](https://arxiv.org/html/2502.14321v2)) gives the
cleanest decomposition. Worth adopting wholesale as design vocabulary:

- **Architecture:** flat (peer-to-peer), hierarchical, team, society, hybrid.
- **Goal:** cooperation (direct, or through debate), competition, mixed.
- **Strategy (the timing axis):** one-by-one (turn-based), simultaneous-talk,
  simultaneous-talk-with-summarizer.
- **Paradigm (the transport axis):** message passing, speech act, blackboard.
- **Content:** explicit (natural language, code, structured data) or implicit (behavioral and
  environmental signals).

The two axes that actually change a design are *strategy* (when may a branch speak) and *paradigm*
(where does the shared state live).

### 3.2 Topologies, and what each costs

**Coordinator / orchestrator-worker.** A lead agent plans, spawns workers, and synthesizes. This is
the pattern with the best production evidence: Anthropic's research system reports **90.2% improvement
over single-agent Claude Opus 4** on their internal research eval, using a lead agent with 3–5
parallel subagents and a separate citation pass, at roughly **15× the tokens of a chat interaction**
([engineering write-up; summarized at
ZenML](https://www.zenml.io/llmops-database/building-a-multi-agent-research-system-for-complex-information-tasks)).
`[moderate]` Costs: the coordinator must model each worker's capability, assignment is ambiguous
when workers overlap, and it is a throughput bottleneck.

**Blackboard.** Agents post requests and volunteer responses against shared state instead of being
addressed by name. Google's data-science variant reports **13–57% relative improvement in end-to-end
task success** over the best baselines, including a master-slave multi-agent setup and RAG, and the
gain held across proprietary and open models
([arXiv 2510.01285](https://arxiv.org/html/2510.01285v1)). `[moderate]` The structural advantage:
the poster does not need to know who can help. For an ensemble of identical branches this matters
less than for a heterogeneous crew, but the *response board* idea — contributions land in a
separate space the coordinator reads exclusively — is a clean way to stop branches from
contaminating each other prematurely.

**Flat / group chat.** Flexible, and prone to deadlock, livelock, and quadratic message growth.
Combined with the sycophancy findings in §2.4, unmoderated group chat is the worst available default
for an ensemble that is supposed to preserve independent judgment.

**Learned topology.** GPTSwarm treats the agent system as an optimizable graph and learns edge
probabilities by RL; DyLAN selects agents dynamically per task; MacNet studies DAG organizations at
scale and finds small-world structures favorable
([GPTSwarm, arXiv 2402.16823](https://arxiv.org/html/2402.16823v3), plus a 2026 line of generator-based
designers: G-Designer, ARG-Designer, QueenBee). `[weak]` Real, but it presumes a training loop over
a task distribution. Not applicable to a one-shot creative brief.

### 3.3 Timing: turn-based, simultaneous, asynchronous

`[moderate]` **Asynchrony is a genuine gap in the literature.** A survey of 1,400+ multi-agent papers
found only 22 addressing it ([arXiv 2607.28430](https://arxiv.org/html/2607.28430) citing the
communication survey). Nearly all published systems exchange information only at phase boundaries —
staged handoffs or synchronized rounds — so a discovery made mid-execution cannot reach another
branch until the next boundary. Where real-time exchange has been built, the mechanism is a
**pull-based per-agent message queue**: on each forward pass an agent pulls everything dispatched
since its last turn, which avoids imposing an artificial turn structure while guaranteeing nothing
is dropped.

Practical ranking for an ensemble over an unverifiable workload:

1. **Independent phase first, always.** Every branch produces its candidate with zero exposure to
   the others. This is the only phase that generates the diversity the whole pattern depends on.
   Contaminating it is the single most common way to spend 5× the tokens for 1× the quality.
2. **Turn-based exchange, few rounds.** Disagreement decays over rounds and sycophancy accumulates,
   so 1–2 exchange rounds is where the evidence sits. The prose-review protocol already in this
   repo (`project_metadata/plans/group-prose-review-protocol.md`) encodes this correctly: draft
   independently *before* reading the previous reviewer's post, then respond — a blind-then-informed
   gate at each turn. That is the right primitive, and it matches the blind-peer-review result.
3. **Simultaneous-talk-with-summarizer** when branches are many. A summarizer collapses N posts into
   one context, which keeps message volume linear.
4. **Asynchronous / real-time** only when subtasks are interdependent and one branch's finding
   genuinely invalidates another's work in flight. For creative and design work this is rarely true,
   and the coordination cost is real.

### 3.4 Shared state

- **Scratchpad (in-context).** Ephemeral, token-bounded, fastest. Fine for a handful of short posts.
- **Shared file / filesystem.** Branches write artifacts and return lightweight references; the
  coordinator reads a pointer, not a 40-page payload. This is standard practice in production
  harnesses and is the main defense against context blowup in the lead agent. `[moderate]`
- **Blackboard store.** Structured request/response boards with exclusive read by the coordinator.
- **Locking.** Concurrent appends to a shared scratchpad need an exclusive lock or a serializing
  coordinator. Missing termination conditions and unserialized writes are named failure modes, not
  hypotheticals (see §3.5).

### 3.5 Failure taxonomy worth designing against

`[strong]` MAST (UC Berkeley, NeurIPS 2025) annotated 1,600+ execution traces across 7 multi-agent
frameworks into 14 failure modes in 3 categories, with κ=0.88 inter-annotator agreement
([arXiv 2503.13657](https://arxiv.org/abs/2503.13657)):

1. **Specification and system design — ~41.8% of all failures.** Task misinterpretation, ambiguous
   role definitions, poor decomposition, duplicate roles, **missing termination conditions**.
2. **Inter-agent misalignment.** Information withheld, ignored, or contradicted across agents.
3. **Task verification.** No verification, or verification too shallow to catch the error.

The headline conclusion is that these are structural design defects, not model defects, and prompt
tweaks do not fix them. Two direct consequences for an ensemble design: write the branch brief and
the termination condition as explicitly as the task itself, and make sure two branches given the
same brief are not silently redundant.

---

## 4. Resource control

### 4.1 The measurement discipline that has to come first

`[strong]` Every credible negative result in §2.4 came from a **compute-matched comparison**. Most
ensemble wins evaporate when the baseline is allowed the same token budget. Before adopting any
pattern, the comparison must be: pattern at budget B vs. single agent at budget B vs. self-consistency
at budget B. A win over a single agent at 1/5 the budget is not a win.

### 4.2 Where the budget actually goes

`[moderate]` In Anthropic's production research system, three factors explained 95% of performance
variance: **token usage ~80%, number of tool calls ~10%, model choice ~5%**. Two readings, both
worth holding:

- Optimistic: quality scales with compute, so the ensemble premium buys something real.
- Cautionary: if token count dominates that completely, a topology's measured advantage may be
  mostly its token appetite. Which is exactly why §4.1 is non-negotiable.

### 4.3 The control surface

The adaptive test-time compute survey ([arXiv 2507.02076](https://arxiv.org/html/2507.02076v1))
splits methods into **L1 controllable** (fixed, pre-declared budget) and **L2 adaptive** (budget set
dynamically from task difficulty and model confidence). For an agent ensemble, the usable levers:

| Lever | Level | Mechanism | Notes |
|---|---|---|---|
| Branch count N | L1 | Fixed fan-out | Cheapest lever; diminishing past ~5 for scoring-based selection, further for ranking-based |
| Exchange rounds | L1 | Cap rounds | Evidence supports 1–2; disagreement decays after |
| Budget forcing | L1 | Truncate or extend thinking; per-step token caps | Reported up to 92.4% token reduction on arithmetic with per-step word limits |
| Confidence-based early stop | L2 | Halt sampling when candidates converge | Model-agnostic, lightweight; hypothesis-testing variants monitor answer convergence |
| Reliability-bounded stopping | L2 | Per-instance, per-round bound on the probability of acting on a wrong answer | ([arXiv 2606.29654](https://arxiv.org/html/2606.29654v1)) `[weak]` |
| Widen vs. deepen controller | L2 | Confidence gain suppresses new branches; stagnation triggers widening; abandon a branch only after persistent deviation, keep ≥2 alive | The most directly applicable adaptive policy found |
| Early abort of doomed episodes | L2 | Recall-controlled probe cascade kills runs predicted to fail | ([arXiv 2607.06503](https://arxiv.org/pdf/2607.06503)) `[weak]` |
| Routing / cascades | L1+L2 | Cheap model first, escalate on low confidence | The ensemble-before-inference family; cost control rather than quality lift |
| Reference-passing | — | Branches return file pointers, not payloads | Keeps coordinator context flat as N grows |
| Selection cost | — | Bracket (O(N)) instead of round-robin (O(N²)) | Near-equivalent ranking accuracy |

`[weak]` Confidence-gated stopping is the weakest link for unverifiable workloads, for the same
reason BoN fails there: the confidence signal is the thing you do not have. Expect to fall back on
fixed budgets (L1) plus a human gate, rather than adaptive stopping, until you have a calibrated
domain judge.

### 4.4 Cost anchors

- Orchestrator-worker research system: ~15× chat tokens for +90.2% on the internal eval.
- MoA-Lite: 2 layers, small aggregator, beat GPT-4o on AlpacaEval 2.0 at lower cost — evidence that
  layered aggregation is not purely pay-to-win.
- Debate: worst observed ratio. Several papers report heavy overhead for no significant gain.

---

## 5. What this implies for an unverifiable workload

A defensible default, assembled from the patterns that survived compute-matched scrutiny. Nothing
here is exotic; the value is in the ordering and the gates.

1. **Diversify the input before widening the ensemble.** Distinct briefs, personas, or design
   stances per branch; heterogeneous models where available; verbalized sampling inside each branch.
   Correlated branches are wasted branches.
2. **Independent generation, no cross-talk.** Identical problem context, identical tools, sealed
   from each other. Produce k candidates per branch rather than 1, since intra-branch diversity is
   nearly free.
3. **Blind structured critique, not debate.** Each branch reviews the others' artifacts with
   authorship hidden, against explicit named dimensions for the domain (for prose: structure, voice,
   claim preservation; for design: hierarchy, spatial logic, constraint satisfaction). Require
   citation of the exact passage or region. Collaborative framing only; never competitive, never
   "reach consensus."
4. **One or two exchange rounds, hard cap.** Draft the response before reading peers, then revise —
   the blind-then-informed gate. Cap the rounds in the protocol, not by judgment.
5. **Rank pairwise on a bracket, both orders.** Do not ask for 1–10 scores. Take a shortlist, not a
   winner.
6. **Synthesize over the shortlist.** The final step writes a new artifact conditioned on the top
   candidates plus the critique record. This is the MoA/GenFuser lesson, and it is the step that
   distinguishes "scaled tokens for quality" from "scaled tokens for a lottery."
7. **Coordinator owns state and termination.** Serialize writes to shared state, pass references
   rather than payloads, and declare the termination condition up front — missing termination is a
   top-3 MAST failure mode.
8. **Keep the human in the loop where the ground truth lives.** For workloads defined by aggregated
   human judgment, the ensemble's job is to produce a small set of genuinely different strong
   candidates plus an honest critique record. Treat the automated selector as a shortlister, and
   log pairwise human choices to calibrate the judge over time.

**When to skip the ensemble entirely:** baseline quality is already high, models are homogeneous, the
budget is tight, or no domain-grounded evaluation rubric exists. In those conditions the literature
favors a single agent with a longer sequential critique-revise loop.

---

## 6. Open questions

- **Selection is the bottleneck, and nobody has solved it for subjective work.** The BoN-oracle gap
  says the candidates are good enough; the selectors are not. Any future gain here is worth more
  than any topology change.
- **Reliability without validity.** Judges that are self-consistent and systematically wrong are the
  dangerous case, and current practice cannot detect this without human data.
- **Does complementarity survive at scale?** MoA's aggregator-beats-ranker result is the strongest
  evidence that merging exploits complementary partial merit. Whether that holds for long-form
  artifacts with global coherence constraints — a novel chapter, a floor plan — is untested.
- **Asynchrony is mostly unexplored** (22 of 1,400+ papers) and may simply not be worth it for
  creative work.
- **Is debate anything more than resampling?** The finding that task-irrelevant rationales help as
  much as task-relevant ones deserves replication. If it holds broadly, most of the debate
  literature is measuring a sampling effect.
- **Everything above was measured on benchmarks, not on interior design or visualization rendering.**
  The closest evidence is the compositional-image-generation refinement loop. Treat §5 as a
  hypothesis to A/B, not a conclusion.

---

## Sources

Ensemble patterns and aggregation
- [Harnessing Multiple Large Language Models: A Survey on LLM Ensemble (arXiv 2502.18036)](https://arxiv.org/html/2502.18036v1)
- [Mixture-of-Agents Enhances Large Language Model Capabilities (arXiv 2406.04692, ICLR 2025)](https://arxiv.org/abs/2406.04692)
- [Universal Self-Consistency for Large Language Model Generation (arXiv 2311.17311)](https://arxiv.org/abs/2311.17311)
- [Agreement in Representation Space for Open-Ended Self-Consistency (arXiv 2606.12003)](https://arxiv.org/html/2606.12003)
- [Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity (arXiv 2510.01171)](https://arxiv.org/abs/2510.01171)

Debate: evidence for and against
- [When and Why Does Multi-Agent Debate Fail and Does It Really Underperform? (arXiv 2510.20963)](https://arxiv.org/html/2510.20963v2)
- [Stop Overvaluing Multi-Agent Debate (arXiv 2502.08788)](https://arxiv.org/abs/2502.08788)
- [The Cost of Consensus: Isolated Self-Correction Prevails Over Unguided Homogeneous Multi-Agent Debate (arXiv 2605.00914)](https://arxiv.org/pdf/2605.00914)
- [Talk Isn't Always Cheap: Failure Modes in Multi-Agent Debate (arXiv 2509.05396)](https://arxiv.org/pdf/2509.05396)
- [Too Polite to Disagree: Sycophancy Propagation in Multi-Agent Systems (arXiv 2604.02668)](https://arxiv.org/html/2604.02668v2)
- [Not All Flips Are Conformity: Decomposing Stance Convergence (arXiv 2606.00820)](https://arxiv.org/html/2606.00820)
- [Multi-LLM-Agents Debate: Performance, Efficiency, and Scaling Challenges (ICLR 2025 blogpost)](https://d2jud02ci9yv69.cloudfront.net/2025-04-28-mad-159/blog/mad/)

Subjective / creative / multimodal workloads
- [BoN Appetit at LeWiDi-2025: Best-of-N Test-time Scaling Can Not Stomach Annotation Disagreements (arXiv 2510.12516)](https://arxiv.org/html/2510.12516)
- [LLM Review: Enhancing Creative Writing via Blind Peer Review Feedback (arXiv 2601.08003)](https://arxiv.org/pdf/2601.08003)
- [Iterative Refinement Improves Compositional Image Generation (arXiv 2601.15286)](https://arxiv.org/html/2601.15286)
- [FineGen: A VLM-based Multi-Agent Framework (arXiv 2606.07645)](https://arxiv.org/html/2606.07645)
- [SAGE: Hierarchical LLM-Based Literary Evaluation (arXiv 2605.07102)](https://arxiv.org/pdf/2605.07102)
- [StoryWriter: A Multi-Agent Framework for Long Story Generation (arXiv 2506.16445)](https://arxiv.org/html/2506.16445.pdf)
- [Agents' Room: Narrative Generation through Multi-step Collaboration (arXiv 2410.02603)](https://arxiv.org/html/2410.02603.pdf)

Selection and judging
- [Arena-Lite: Tournament-Based Direct Comparisons (arXiv 2411.01281)](https://arxiv.org/html/2411.01281v5)
- [Tournament-GRPO: Group-Wise Tournament Rewards (arXiv 2605.26958)](https://arxiv.org/html/2605.26958)
- [Reliability without Validity: Large-Scale Evaluation of LLM-as-a-Judge (arXiv 2606.19544)](https://arxiv.org/html/2606.19544v1)
- [LLM-as-judge evaluation best practices, March 2026 (Openlayer)](https://www.openlayer.com/blog/llm-as-judge-evaluation-guide)

Synchronization and topology
- [Beyond Self-Talk: A Communication-Centric Survey of LLM-Based Multi-Agent Systems (arXiv 2502.14321)](https://arxiv.org/html/2502.14321v2)
- [LLM-based Multi-Agent Blackboard System for Information Discovery in Data Science (arXiv 2510.01285)](https://arxiv.org/html/2510.01285v1)
- [GPTSwarm: Language Agents as Optimizable Graphs (arXiv 2402.16823)](https://arxiv.org/html/2402.16823v3)
- [AgentRadio: Passive Awareness for Long-Horizon Multi-Agent Collaboration (arXiv 2607.28430)](https://arxiv.org/html/2607.28430)
- [Why Do Multi-Agent LLM Systems Fail? / MAST (arXiv 2503.13657, NeurIPS 2025)](https://arxiv.org/abs/2503.13657)
- [Anthropic's multi-agent research system (summary)](https://www.zenml.io/llmops-database/building-a-multi-agent-research-system-for-complex-information-tasks)

Resource control
- [Reasoning on a Budget: A Survey of Adaptive and Controllable Test-Time Compute (arXiv 2507.02076)](https://arxiv.org/html/2507.02076v1)
- [Sampling-Efficient Test-Time Scaling: Self-Estimating Best-of-N (arXiv 2503.01422)](https://arxiv.org/pdf/2503.01422)
- [Budgeted Act-or-Defer Multi-Agent LLM Deliberation with Local Reliability Bounds (arXiv 2606.29654)](https://arxiv.org/html/2606.29654v1)
- [Doomed from the Start: Early Abort of LLM Agent Episodes (arXiv 2607.06503)](https://arxiv.org/pdf/2607.06503)
- [BAGEN: Are LLM Agents Budget-Aware? (arXiv 2606.00198)](https://arxiv.org/html/2606.00198v1)
