# Deep Life Sim (Terminal Python)

A replayable text-based life simulation game inspired by BitLife, with deeper systems and anti-repetition mechanics.

## Run

```bash
python life_sim.py
```

## Systems included

- Year-by-year life progression from birth to death.
- Core stats: Health, Happiness, Intelligence, Wealth, Social, Reputation.
- Hidden systems: luck, charisma, resilience, risk tolerance.
- Education: grades, school reputation, scholarships, dropout with delayed consequences.
- Career: multiple tracks (professional, creator, underworld, blue-collar) with unique behavior.
- Relationships: evolving NPCs with memory, trust, closeness, and independent life changes.
- Anti-repetition design:
  - weighted event pool
  - event history repetition penalties
  - rare chaos events
  - chain events with delayed outcomes
- Emergent narrative via memories and delayed consequences.

## Expandability notes

The code is intentionally organized around:

- `GameState` (all player/world state)
- `EventDef` (event metadata + choice handlers)
- `_build_events()` and one method per event category
- helper methods (`_apply`, `_risk_action`, etc.) for outcome logic

Add new content by creating more `EventDef` methods and including them in `_build_events()`.
