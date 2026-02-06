# Battle Balance Pass (February 2026)

This pass adjusts battle pacing and stat swing strength to reduce one-turn snowballing while keeping type advantages meaningful.

## Formula updates

- Damage now uses tunable constants in `src/core/config.py`:
  - `DAMAGE_ATTACK_FACTOR = 8`
  - `DAMAGE_DEFENSE_FACTOR = 34`
  - `DAMAGE_BASE_OFFSET = 2`
  - `DAMAGE_RANDOM_MIN = 0.9`
  - `DAMAGE_RANDOM_MAX = 1.0`
- Stat-change multiplier was reduced:
  - `STAT_CHANGE_MULTIPLIER: 0.66 -> 0.55`

## Why

- The previous damage curve plus mostly high-power moves (`70-120`) caused frequent short battles.
- Large stat jumps made buff/debuff turns disproportionately strong early in fights.
- The updated values keep type matchups relevant but reduce immediate blowout turns.

## Expected combat behavior

- Fewer first-hit knockouts at equal levels.
- Stat moves still matter, but they are less likely to decide the entire fight in one use.
- Average team battles should run for more turns without feeling stalled.
