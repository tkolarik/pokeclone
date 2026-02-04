# Battle AI Design (Current Implementation)

## Scope
This document describes the **current** opponent move selection behavior in `src/battle/battle_simulator.py`.
It is not a roadmap; it mirrors what the AI does today.

## Goals
- Use type effectiveness when choosing damaging moves.
- Prefer KO opportunities.
- Allow stat moves to matter when they provide value.
- Keep behavior simple and fast.

## Inputs
- Attacker creature: `type`, `attack`, `defense`, `current_hp`, `max_hp`, `base_stats`, `moves`
- Defender creature: `type`, `attack`, `defense`, `current_hp`, `max_hp`, `base_stats`
- Move fields: `type`, `power`, `effect` (optional dict with `target`, `stat`, `change`)
- Type chart from `data/type_chart.json`

## Output
One move from the attacker’s `moves` list.

## Core Heuristics

### 1) Damaging moves (`power > 0`)
For each damaging move:
1. Compute effectiveness from the type chart:
   - `effectiveness = type_chart[move.type][defender.type]` (default `1`)
2. Compute base damage:
   - `base_damage = (10 * attacker.attack * move.power) / (30 * defender.defense)`
3. Compute expected damage (average roll):
   - `expected = (base_damage + 2) * effectiveness * 0.925`
4. Scoring:
   - `score = expected`
   - If `expected >= defender.current_hp`: `score += 50` (KO bonus)
   - If `effectiveness > 1`: `score += 10`
   - If `effectiveness == 0`: `score -= 20`

### 2) Stat moves (`power == 0`)
Stat moves use a heuristic score based on how far a stat is from base:
- If `target == self`:
  - If `current < base * 1.2`: `score = 8 * change`
  - Else if `current < base * 1.5`: `score = 4 * change`
  - Else: `score = 1 * change`
- If `target == opponent`:
  - If `current > base * 1.2`: `score = 7 * change`
  - Else if `current > base * 1.05`: `score = 3 * change`
  - Else: `score = 1 * change`

HP modifiers:
- If attacker HP ratio `< 0.35`, halve stat-move score.
- If defender HP ratio `< 0.30`, quarter stat-move score.

### 3) Selection
1. Score all moves.
2. Sort by score descending.
3. Keep “top” moves with `score >= best_score * 0.95`.
4. Choose randomly among top moves.
5. If `best_score == 0`, choose any move randomly.

## Tradeoffs & Known Limitations
- No modeling of accuracy, status, speed, or multi-turn effects.
- No longer-term planning (e.g., setup for later).
- Stat moves are based on simple thresholds, not optimal play.
- Randomness can still produce suboptimal moves among top choices.

## Test Coverage
Tests validate:
- Super‑effective damaging moves are preferred over not‑very‑effective.
- Stat moves are selected when beneficial and avoided when attacker HP is low.
