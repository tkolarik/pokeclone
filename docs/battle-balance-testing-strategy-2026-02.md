# Automated Battle Balance Testing Strategy (2026-02)

## Goal
Detect centralization early while keeping per-PR checks fast, deterministic, and actionable.

## Candidate Methods
### 1) MLP self-play with usage logging
- Pros: can discover emergent dominant loops.
- Cons: cold-start noise, higher compute, unstable short-run metrics.
- Signal: medium-high after warmup.
- Cost: high.

### 2) Scripted baseline agents
- Pros: deterministic, reproducible, CI-friendly.
- Cons: limited exploration beyond authored policy space.
- Signal: medium (high precision, lower recall).
- Cost: low.

### 3) Random/pseudo-random rollouts
- Pros: broad cheap coverage and good null baseline.
- Cons: weak strategic pressure, noisy outcomes.
- Signal: low-medium.
- Cost: low.

### 4) Targeted scenario simulations
- Pros: high-signal guardrails for known failure modes.
- Cons: coverage only as good as scenario catalog quality.
- Signal: high on covered mechanics.
- Cost: low.

## Core Metrics
### Move concentration
- `top_1_share`, `top_3_share`, `herfindahl_index` (HHI), `normalized_entropy`.
- Use **HHI for alerting** (dominance spikes), **entropy for health trend** (tail collapse).

### Opportunity-conditioned move pressure
- Track both:
  - `uses(move)`
  - `eligible_opportunities(move)` (turns where move was legal)
- Derived:
  - `pick_rate(move) = uses / eligible_opportunities`
- Compute both:
  - weighted pick-rate concentration (weighted by opportunities) for gating
  - unweighted pick-rate concentration for diagnostics
- Always report top moves by `pick_rate` and by raw `uses`.

### Win-rate skew by archetype
- Per archetype `win_rate = wins / battles`.
- Include Wilson 95% intervals per archetype.
- Use sample-size floors before skew alerting.

### Matchup diversity and concentration
- `unique_ratio`, matchup entropy, matchup HHI, and `effective_matchups = 1 / matchup_hhi`.

### Matchup polarization (hard-counter risk)
- Detect rock-paper-scissors determinism hidden by average 50% win rates.
- Polarization index:
  - `polarization = weighted_mean((WR_shrunk(i->j) - 0.5)^2, weight=n(i,j))`
- Use per-cell sample floors and shrinkage:
  - `WR_shrunk = (wins + k*0.5) / (n + k)`
- High values indicate rigid counter structure and reduced skill expression.

### Meta-stability (replicator dynamics)
- Build a payoff matrix from shrunk directed matchup win rates.
- Simulate population share updates with replicator dynamics.
- Run this nightly/diagnostic by default (not required in per-PR CI).
- Report convergence and stability diagnostics:
  - convergence status + iteration
  - cycle detection
  - payoff coverage and missing cells
  - sensitivity to shrinkage parameter `k`

### Degeneracy early warnings
- Turn length stats: mean/median/p90.
- Repeat-loop metrics: longest same-move streak per side and `% battles with streak >= 8`.
- Non-decision outcomes: timeout/draw/surrender rates.
- Tempo proxy: average final HP differential.

## CI and Rollout Plan
### Stage 0: deterministic CI foundation (immediate)
- Scripted mirrors + targeted scenarios as hard per-PR gate.
- Small seeded random batch as warning lane.

### Stage 1: scenario hardening (short-term)
- Add deterministic parameter fuzzing (fixed seeds).
- Start at `+/- 5%`, then tune to observed cliff locations.
- Expand known-risk scenario catalog (stall loops, setup sweep, priority abuse, lock states).

### Stage 2: self-play diagnostics (medium-term)
- Keep self-play off per-PR path (nightly/offline).
- Use imitation-learning warm start from scripted policy traces before RL.
- Evaluate learned policy against fixed scripted league and prior snapshots.

### Stage 3: blended governance (long-term)
- Hard gates remain deterministic (scripted/scenarios).
- Self-play remains diagnostic/trend channel for discovery and triage.

## Thresholding Model
- Prefer delta gates for normal balancing:
  - entropy drop, HHI rise, win-rate spread shift, effective matchup drop.
- Keep absolute tripwires for clear emergencies:
  - extreme top-1 share, timeout spikes, severe p90 turn inflation.
- Enforce sample-size requirements on skew/polarization decisions.

## Reporting Requirements
Each report should carry:
- commit hash / content hash
- sampler + agent config
- RNG seed(s)
- ruleset version
- top 5 move offenders by pick-rate and uses
- top polarized matchup contributors
- archetypes driving win-rate spread (with CI)
- degeneracy drivers (`p90` turns, repeat-loop rate, timeout rate)
- optional replicator dynamics state (nullable in per-PR reports)
- explicit availability markers for optional metrics (`available: false` when source data is missing)

This keeps failed runs debuggable and reproducible.

## Minimal PoC (Implemented)
Module:
- `src/battle/balance_metrics.py`

Command:
```bash
python -m src.battle.balance_metrics tests/fixtures/balance_logs/sample_battle_logs.json
```

CI-ready options:
```bash
python -m src.battle.balance_metrics <logs.json> \
  --baseline <baseline_report.json> \
  --fail-on <rules.json> \
  --include-replicator \
  --out <report.json>
```

Rules file supports:
- `absolute_max`
- `absolute_min`
- `delta_max`
- `delta_min`
- `min_total_battles`
- `min_cell_battles`
- `min_opportunities_per_move`

The command exits non-zero when threshold violations are detected.
