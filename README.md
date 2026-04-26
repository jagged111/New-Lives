# Deep Life Sim (Terminal Python)

A replayable text-based life simulation game with **200+ weighted events**, deep crime risk/reward loops, named relationship characters, and **generational legacy gameplay**.

## Run

```bash
python life_sim.py
```

## Highlights

- Birth-to-death progression with yearly choices.
- Core stats: Health, Happiness, Intelligence, Wealth, Social, Reputation.
- Hidden variables + habits + traits to avoid deterministic optimal paths.
- 200+ event pool with weighted randomness, repetition penalties, and chain consequences.
- Rare once-per-life black swan event.
- Education, career, fame, social, family, romance, and finance contexts.
- Deep crime progression:
  - heists (small/major)
  - gang rank escalation
  - heat/record pressure
  - police crackdowns, legal battles, prison time
- Named characters for family/friends/partners/one-night stands with memories and evolving trust.
- Children can be born naturally or unexpectedly; upon death you can continue as a child (new generation).

## Extending

- Add handcrafted events in `_build_events()`.
- Expand procedural variety in `_generate_event_pool()`.
- Add deeper NPC simulation in `_npc_world_tick()`.
