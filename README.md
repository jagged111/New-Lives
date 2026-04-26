# Deep Life Sim (Terminal Python)

A text life simulator with a **yearly player action menu**, **224 total events**, deeper economy/crime systems, named NPC relationships, addictions, and generational legacy continuation.

## Run

```bash
python life_sim.py
```

## Key Features

- Birth-to-death progression with optional continuation as a child.
- Core stats: Health, Happiness, Intelligence, Wealth, Social, Reputation.
- **Player agency menu** each year (15 actions): study/work, gym, socialize, romance, hustle, travel, gamble, crime menu, buy assets, invest, therapy, business, appearance upgrades, etc.
- 200+ weighted events with repetition penalties and once-per-life rare event.
- Deeper economy: assets, maintenance, passive income, debt growth, taxes, investments.
- Deeper crime loops: pickpocket/heist/gang + police pressure, court outcomes, prison time.
- Relationship manager: gifts/fights/reconcile/breakup, memory effects, child birth moments.
- Addiction system: alcohol/drugs/gambling accumulation with withdrawal penalties.
- Save/load support via pickle save files.
- Ribbons/Achievements + legacy hall-of-fame summary.

## Extend

- Add custom events in `_build_events()`.
- Increase procedural variety in `_generate_event_pool()`.
- Expand yearly activity actions in `_activity_menu()`.
