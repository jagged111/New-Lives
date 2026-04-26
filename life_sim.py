import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

# ============================================================
# Text-based Life Simulator
# Inspired by life-sim games, but with systems to reduce repetition:
# - weighted events + repetition penalties
# - chain events with delayed consequences
# - hidden traits/habits + uncertain outcomes
# - evolving NPC relationships with memory
# ============================================================


STAT_KEYS = ["health", "happiness", "intelligence", "wealth", "social", "reputation"]
COUNTRIES = ["USA", "Brazil", "India", "Japan", "Nigeria", "Germany", "Canada", "Mexico"]
PARENT_BACKGROUNDS = [
    "struggling household",
    "working-class family",
    "middle-class family",
    "wealthy family",
    "celebrity family",
]


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


@dataclass
class Relation:
    name: str
    kind: str
    closeness: int
    trust: int
    personality: str
    memory: List[str] = field(default_factory=list)
    alive: bool = True
    age_offset: int = 0
    reputation_view: int = 50


@dataclass
class EventDef:
    key: str
    category: str
    min_age: int
    max_age: int
    base_weight: float
    condition: Callable[["GameState"], bool]
    setup_text: Callable[["GameState"], str]
    choices: Callable[["GameState"], List[Tuple[str, Callable[["GameState"], str]]]]


@dataclass
class GameState:
    name: str
    age: int = 0
    alive: bool = True
    cause_of_death: Optional[str] = None
    location: str = ""
    upbringing: str = ""

    stats: Dict[str, int] = field(default_factory=lambda: {
        "health": 65,
        "happiness": 60,
        "intelligence": 55,
        "wealth": 15,
        "social": 50,
        "reputation": 50,
    })

    hidden: Dict[str, int] = field(default_factory=dict)
    habits: Dict[str, int] = field(default_factory=lambda: {
        "study": 0,
        "exercise": 0,
        "crime": 0,
        "networking": 0,
    })
    traits: Dict[str, int] = field(default_factory=lambda: {
        "disciplined": 0,
        "reckless": 0,
        "kind": 0,
        "ambitious": 0,
    })

    education_level: str = "none"
    school_grades: int = 50
    school_rep: int = 50
    scholarships: int = 0
    dropped_out: bool = False

    career: str = "none"
    career_level: int = 0
    career_stability: int = 50
    criminal_record: int = 0
    fame: int = 0

    partner: Optional[str] = None
    children: int = 0
    relationships: List[Relation] = field(default_factory=list)

    memories: List[str] = field(default_factory=list)
    event_history: Dict[str, int] = field(default_factory=dict)
    chain_events: List[Dict] = field(default_factory=list)


class LifeSimGame:
    def __init__(self):
        self.rng = random.Random()
        self.state = GameState(name="")
        self.events = self._build_events()

    def run(self):
        self._intro()
        while self.state.alive:
            self._year_header()
            self._age_up()
            self._process_chain_events()
            if not self.state.alive:
                break
            self._update_world_npcs()
            self._annual_decay_and_growth()
            self._run_year_events()
            self._career_tick()
            self._check_death()
            self._year_summary()
            if self.state.alive:
                cont = input("Press Enter for next year, or type q to quit: ").strip().lower()
                if cont == "q":
                    print("You chose to end this life early. Thanks for playing.")
                    break

        self._final_summary()

    def _intro(self):
        print("\n=== DEEP LIFE SIM ===")
        name = input("Enter your character's name: ").strip() or "Alex"
        self.state.name = name
        self.state.location = self.rng.choice(COUNTRIES)
        self.state.upbringing = self.rng.choice(PARENT_BACKGROUNDS)

        base = {"struggling household": -12, "working-class family": -3, "middle-class family": 5,
                "wealthy family": 20, "celebrity family": 28}
        self.state.stats["wealth"] = clamp(self.state.stats["wealth"] + base[self.state.upbringing])
        self.state.hidden = {
            "luck": self.rng.randint(30, 80),
            "risk_tolerance": self.rng.randint(20, 85),
            "charisma": self.rng.randint(25, 85),
            "resilience": self.rng.randint(25, 85),
        }

        self.state.relationships = [
            Relation(name=self.rng.choice(["Mom", "Maya", "Lina", "Sofia"]), kind="parent",
                     closeness=self.rng.randint(45, 80), trust=self.rng.randint(40, 80),
                     personality=self.rng.choice(["strict", "warm", "anxious", "practical"]), age_offset=28),
            Relation(name=self.rng.choice(["Dad", "Noah", "Evan", "Ravi"]), kind="parent",
                     closeness=self.rng.randint(35, 75), trust=self.rng.randint(35, 75),
                     personality=self.rng.choice(["strict", "supportive", "impulsive", "absent-minded"]), age_offset=30),
        ]

        print(f"\nYou were born in {self.state.location} into a {self.state.upbringing}.")
        print(f"Hidden strengths: Luck {self.state.hidden['luck']}, Charisma {self.state.hidden['charisma']}, "
              f"Resilience {self.state.hidden['resilience']} (not shown in-game).")

    def _year_header(self):
        print("\n" + "-" * 56)
        print(f"Age {self.state.age} -> {self.state.age + 1}")

    def _age_up(self):
        self.state.age += 1

    def _annual_decay_and_growth(self):
        s = self.state
        s.stats["health"] = clamp(s.stats["health"] - self.rng.randint(0, 2) + s.habits["exercise"] // 6)
        s.stats["happiness"] = clamp(s.stats["happiness"] - self.rng.randint(0, 3) + s.hidden["resilience"] // 25)
        s.stats["social"] = clamp(s.stats["social"] - self.rng.randint(0, 2) + s.habits["networking"] // 7)
        s.stats["reputation"] = clamp(s.stats["reputation"] - max(0, s.criminal_record // 8))

    def _event_weight(self, ev: EventDef) -> float:
        s = self.state
        if not (ev.min_age <= s.age <= ev.max_age):
            return 0
        if not ev.condition(s):
            return 0
        # Repetition penalty: recently/frequently seen events get downweighted heavily.
        seen = s.event_history.get(ev.key, 0)
        recency_penalty = 0.6 ** seen
        # Dynamic category weights
        cat_boost = 1.0
        if ev.category == "school" and 6 <= s.age <= 22:
            cat_boost = 1.5
        elif ev.category == "career" and s.age >= 18:
            cat_boost = 1.6
        elif ev.category == "crime" and s.habits["crime"] > 20:
            cat_boost = 1.5
        elif ev.category == "fame" and s.fame > 20:
            cat_boost = 1.4
        elif ev.category == "chaos":
            cat_boost = 0.7

        rarity_noise = self.rng.uniform(0.8, 1.25)
        return ev.base_weight * recency_penalty * cat_boost * rarity_noise

    def _choose_events_for_year(self) -> List[EventDef]:
        count = 1 if self.state.age < 6 else (2 if self.state.age < 40 else 3)
        pool = []
        for ev in self.events:
            w = self._event_weight(ev)
            if w > 0:
                pool.append((ev, w))

        chosen: List[EventDef] = []
        for _ in range(min(count, len(pool))):
            total = sum(w for _, w in pool)
            pick = self.rng.random() * total
            run = 0.0
            idx = 0
            for i, (_, w) in enumerate(pool):
                run += w
                if run >= pick:
                    idx = i
                    break
            chosen.append(pool[idx][0])
            pool.pop(idx)
        return chosen

    def _run_year_events(self):
        for ev in self._choose_events_for_year():
            self._run_event(ev)

    def _run_event(self, ev: EventDef):
        s = self.state
        print(f"\n[{ev.category.upper()}] {ev.setup_text(s)}")
        options = ev.choices(s)
        for i, (label, _) in enumerate(options, start=1):
            print(f"  {i}) {label}")
        choice = self._read_choice(len(options))
        outcome = options[choice - 1][1](s)
        print(f"  -> {outcome}")
        s.event_history[ev.key] = s.event_history.get(ev.key, 0) + 1

    @staticmethod
    def _read_choice(max_n: int) -> int:
        while True:
            raw = input("Choose: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= max_n:
                return int(raw)
            print("Please enter a valid option number.")

    def _check_death(self):
        s = self.state
        age_risk = max(0, s.age - 55) * 0.8
        health_risk = max(0, 40 - s.stats["health"]) * 1.1
        crime_risk = s.criminal_record * 0.3
        random_risk = self.rng.uniform(0, 40)
        if s.age >= 95 or (age_risk + health_risk + crime_risk + random_risk > 93):
            s.alive = False
            cause = self.rng.choice([
                "natural causes",
                "a sudden illness",
                "complications after a stressful year",
                "an unexpected accident",
            ])
            s.cause_of_death = cause

    def _career_tick(self):
        s = self.state
        if s.age < 16:
            return

        if s.career == "none":
            if s.age >= 18:
                if s.criminal_record > 25:
                    s.career = "underworld"
                elif s.fame > 35:
                    s.career = "creator"
                elif s.education_level in {"college", "graduate"}:
                    s.career = self.rng.choice(["engineering", "medicine", "law", "research"])
                else:
                    s.career = self.rng.choice(["retail", "construction", "service"])
                print(f"\nYou started a career in: {s.career}.")

        pay = 0
        if s.career in {"retail", "construction", "service"}:
            pay = 6 + s.career_level * 2
            if self.rng.random() < 0.2:
                s.career_stability -= 4
        elif s.career in {"engineering", "medicine", "law", "research"}:
            pay = 15 + s.career_level * 6
            if self.rng.random() < 0.25:
                s.career_stability += 3
                s.stats["intelligence"] = clamp(s.stats["intelligence"] + 1)
        elif s.career == "creator":
            pay = 2 + s.fame // 4
            fame_shift = self.rng.randint(-3, 6)
            s.fame = clamp(s.fame + fame_shift)
            s.stats["reputation"] = clamp(s.stats["reputation"] + (1 if fame_shift > 0 else -1))
        elif s.career == "underworld":
            pay = 10 + s.habits["crime"] // 3
            if self.rng.random() < 0.25:
                s.criminal_record += self.rng.randint(3, 9)
                print("  Underworld heat increased; your record got worse.")

        growth_chance = 0.1 + s.traits["disciplined"] * 0.02 + s.hidden["luck"] / 400
        if self.rng.random() < growth_chance:
            s.career_level += 1
            s.stats["reputation"] = clamp(s.stats["reputation"] + 2)
            print("  Career progression: You got promoted / expanded your influence.")

        s.stats["wealth"] = clamp(s.stats["wealth"] + pay)

    def _process_chain_events(self):
        s = self.state
        pending = []
        for ch in s.chain_events:
            if s.age >= ch["trigger_age"]:
                print(f"\n[CONSEQUENCE] {ch['text']}")
                ch["effect"](s)
            else:
                pending.append(ch)
        s.chain_events = pending

    def _update_world_npcs(self):
        s = self.state
        for rel in s.relationships:
            if not rel.alive:
                continue
            # NPC independent life updates
            if self.rng.random() < 0.03 and s.age > 20:
                rel.memory.append("moved to another city")
                rel.closeness = clamp(rel.closeness - 8)
            if self.rng.random() < 0.02 and s.age > 24:
                rel.memory.append("major life change (marriage/divorce/job loss)")
                rel.trust = clamp(rel.trust + self.rng.randint(-6, 6))
            if self.rng.random() < 0.008 and s.age > 45:
                rel.alive = False
                s.memories.append(f"Lost {rel.name} ({rel.kind})")
                s.stats["happiness"] = clamp(s.stats["happiness"] - 12)
                print(f"\nWorld event: {rel.name} passed away.")

        # Occasionally add a new friend/partner candidate.
        if 10 <= s.age <= 60 and self.rng.random() < 0.14:
            new = Relation(
                name=self.rng.choice(["Kai", "Jordan", "Avery", "Rin", "Sam", "Leila"]),
                kind=self.rng.choice(["friend", "coworker", "partner_candidate"]),
                closeness=self.rng.randint(30, 65),
                trust=self.rng.randint(25, 65),
                personality=self.rng.choice(["loyal", "dramatic", "strategic", "funny", "private"]),
                age_offset=self.rng.randint(-3, 3),
            )
            s.relationships.append(new)
            print(f"\nYou met {new.name} ({new.kind}, {new.personality}).")

    def _year_summary(self):
        s = self.state
        print("\nYear summary:")
        print(
            f"  Age {s.age} | Health {s.stats['health']} | Happy {s.stats['happiness']} | IQ {s.stats['intelligence']}"
            f" | Wealth {s.stats['wealth']} | Social {s.stats['social']} | Rep {s.stats['reputation']}"
        )
        print(
            f"  Education: {s.education_level} (Grades {s.school_grades}, School Rep {s.school_rep})"
            f" | Career: {s.career} L{s.career_level} | Record: {s.criminal_record} | Fame: {s.fame}"
        )

        top_mem = s.memories[-2:] if s.memories else []
        if top_mem:
            print("  Recent life memories:")
            for m in top_mem:
                print(f"    - {m}")

    def _final_summary(self):
        s = self.state
        print("\n" + "=" * 56)
        print(f"End of life for {s.name} at age {s.age}.")
        if s.cause_of_death:
            print(f"Cause of death: {s.cause_of_death}")
        print(f"Final stats: {s.stats}")
        print(f"Major path: Career={s.career}, Education={s.education_level}, Criminal record={s.criminal_record}, Fame={s.fame}")
        if s.memories:
            print("Legacy highlights:")
            for m in s.memories[-8:]:
                print(f"  * {m}")

    # -------------------------- Event Definitions --------------------------

    def _build_events(self) -> List[EventDef]:
        return [
            self._childhood_event(),
            self._family_event(),
            self._school_event(),
            self._scholarship_event(),
            self._crime_event(),
            self._health_event(),
            self._social_event(),
            self._career_event(),
            self._relationship_event(),
            self._midlife_event(),
            self._chaos_event(),
            self._fame_event(),
        ]

    def _childhood_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return s.age <= 12

        def text(_: GameState) -> str:
            return "A family moment forces you to pick between curiosity and comfort."

        def choices(s: GameState):
            return [
                ("Read and explore on your own", lambda st: self._apply(st, {"intelligence": +4, "happiness": -1},
                    traits={"disciplined": +1}, habits={"study": +2},
                    memory="You became self-driven early.")),
                ("Play with neighborhood kids", lambda st: self._apply(st, {"social": +4, "happiness": +2},
                    traits={"kind": +1},
                    memory="You built early social confidence.")),
                ("Sneak into a restricted place", lambda st: self._risk_action(
                    st,
                    success_msg="The thrill was exciting and nobody noticed.",
                    fail_msg="You were caught and family trust dropped.",
                    success_changes={"happiness": +3, "reputation": -1},
                    fail_changes={"happiness": -3, "reputation": -5},
                    risk=0.45,
                    habits={"crime": +2}, traits={"reckless": +1}
                )),
            ]

        return EventDef("childhood_core", "childhood", 1, 12, 14.0, cond, text, choices)

    def _family_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return s.age <= 18 and any(r.alive and r.kind == "parent" for r in s.relationships)

        def text(_: GameState) -> str:
            return "A family conflict reveals different values at home."

        def choices(s: GameState):
            return [
                ("Help at home and sacrifice free time", lambda st: self._apply(
                    st, {"happiness": -1, "social": +2, "reputation": +2},
                    traits={"kind": +1, "disciplined": +1},
                    memory="You took responsibility for family needs."
                )),
                ("Argue for independence", lambda st: self._risk_action(
                    st,
                    "You negotiated more freedom respectfully.",
                    "The argument escalated and trust fell.",
                    {"happiness": +3, "social": +1},
                    {"happiness": -4, "reputation": -3},
                    risk=0.44
                )),
                ("Avoid the conflict entirely", lambda st: self._apply(
                    st, {"happiness": +1, "social": -2},
                    memory="You avoided a difficult family conversation."
                )),
            ]

        return EventDef("family_core", "childhood", 3, 18, 10.0, cond, text, choices)

    def _school_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return 6 <= s.age <= 22 and not s.dropped_out

        def text(s: GameState) -> str:
            return f"Academic pressure rises. Current grades: {s.school_grades}."

        def choices(s: GameState):
            return [
                ("Study consistently", lambda st: self._school_progress(st, effort=8, rep=1, stress=-2)),
                ("Focus on social life", lambda st: self._school_progress(st, effort=2, rep=3, stress=3)),
                ("Cheat on an exam", lambda st: self._cheat_exam(st)),
                ("Drop out", lambda st: self._drop_out(st) if st.age >= 14 else "You are too young to drop out."),
            ]

        return EventDef("school_core", "school", 6, 22, 16.0, cond, text, choices)

    def _scholarship_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return 16 <= s.age <= 20 and s.school_grades >= 70 and s.education_level in {"none", "high_school"}

        def text(_: GameState) -> str:
            return "A scholarship committee reviews your profile."

        def choices(s: GameState):
            return [
                ("Submit with a sincere essay", lambda st: self._scholarship_try(st, flashy=False)),
                ("Submit a bold, attention-grabbing essay", lambda st: self._scholarship_try(st, flashy=True)),
            ]

        return EventDef("scholarship", "school", 16, 20, 8.0, cond, text, choices)

    def _career_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return s.age >= 18

        def text(s: GameState) -> str:
            return f"Workplace tension appears in your {s.career} track."

        def choices(s: GameState):
            return [
                ("Handle conflict diplomatically", lambda st: self._apply(st, {"social": +3, "reputation": +2},
                    habits={"networking": +2}, memory="You resolved a workplace conflict.")),
                ("Take a risky shortcut for results", lambda st: self._risk_action(
                    st, "Shortcut worked and impressed leadership.",
                    "Shortcut backfired, damaging stability.",
                    {"wealth": +6, "reputation": +2}, {"reputation": -5, "health": -3},
                    risk=0.38, traits={"reckless": +1, "ambitious": +1})),
                ("Stand up against unfair practices", lambda st: self._apply(st, {"reputation": +4, "happiness": +1},
                    {"career_stability": -5}, traits={"kind": +1},
                    memory="You challenged unfair workplace norms.")),
            ]

        return EventDef("career_core", "career", 18, 90, 13.0, cond, text, choices)

    def _crime_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return s.age >= 13

        def text(_: GameState) -> str:
            return "A questionable opportunity appears through your network."

        def choices(s: GameState):
            return [
                ("Ignore it", lambda st: self._apply(st, {"reputation": +1}, habits={"crime": -1},
                    memory="You avoided a criminal opportunity.")),
                ("Join a small illegal scheme", lambda st: self._crime_attempt(st, scale="small")),
                ("Organize a larger operation", lambda st: self._crime_attempt(st, scale="large")),
            ]

        return EventDef("crime_core", "crime", 13, 90, 9.5, cond, text, choices)

    def _health_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return s.age >= 8

        def text(s: GameState) -> str:
            return "Your body and mind signal that your routine needs attention."

        def choices(s: GameState):
            return [
                ("Build an exercise routine", lambda st: self._apply(st, {"health": +6, "happiness": +2},
                    habits={"exercise": +4}, traits={"disciplined": +1}, memory="You committed to fitness.")),
                ("Ignore it and push through", lambda st: self._apply(st, {"health": -4, "wealth": +2},
                    traits={"ambitious": +1}, memory="You sacrificed health for short-term output.")),
                ("See a professional and adjust lifestyle", lambda st: self._risk_action(
                    st,
                    "Treatment worked well; your baseline improved.",
                    "Costs were high and progress was slow.",
                    {"health": +7, "happiness": +3, "wealth": -4},
                    {"health": +2, "happiness": -2, "wealth": -8},
                    risk=0.25,
                    traits={"disciplined": +1}
                )),
            ]

        return EventDef("health_core", "health", 8, 90, 11.0, cond, text, choices)

    def _social_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return s.age >= 10

        def text(_: GameState) -> str:
            return "A social situation tests your values and loyalty."

        def choices(s: GameState):
            return [
                ("Support a friend during hardship", lambda st: self._apply(st, {"social": +5, "happiness": +2},
                    traits={"kind": +2}, memory="You were there for someone in need.")),
                ("Prioritize your own goals", lambda st: self._apply(st, {"wealth": +4, "social": -2},
                    traits={"ambitious": +2}, memory="You chose ambition over social obligations.")),
                ("Publicly call someone out", lambda st: self._risk_action(
                    st,
                    "People praised your honesty.",
                    "Backlash damaged your image.",
                    {"reputation": +4},
                    {"reputation": -6, "social": -3},
                    risk=0.5,
                    traits={"reckless": +1}
                )),
            ]

        return EventDef("social_core", "social", 10, 90, 10.0, cond, text, choices)

    def _relationship_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return s.age >= 14 and any(r.alive for r in s.relationships)

        def text(s: GameState) -> str:
            alive = [r for r in s.relationships if r.alive]
            pick = self.rng.choice(alive)
            return f"{pick.name} ({pick.kind}) remembers something you did in the past."

        def choices(s: GameState):
            return [
                ("Reconnect sincerely", lambda st: self._relationship_shift(st, +8, +6, "You repaired trust.")),
                ("Keep distance", lambda st: self._relationship_shift(st, -5, -4, "Distance increased.")),
                ("Ask for a big favor", lambda st: self._risk_action(
                    st, "They helped you, strengthening your bond.",
                    "They felt used and trust dropped.",
                    {"wealth": +5, "social": +2},
                    {"social": -6, "happiness": -2},
                    risk=0.47
                )),
            ]

        return EventDef("relationship_core", "social", 14, 90, 11.5, cond, text, choices)

    def _chaos_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return s.age >= 12

        def text(_: GameState) -> str:
            return "Rare chaos: a bizarre opportunity and danger appear together."

        def choices(s: GameState):
            return [
                ("Take the bizarre chance", lambda st: self._risk_action(
                    st,
                    "It became an unexpected breakthrough.",
                    "It collapsed and caused losses.",
                    {"wealth": +8, "happiness": +4, "fame": +5},
                    {"wealth": -10, "reputation": -4},
                    risk=0.58,
                    chain=(2, "The chaos event still echoes years later.",
                           lambda s2: self._apply(s2, {"happiness": +5, "reputation": +4}, memory="A past risky move paid off late."))
                )),
                ("Avoid it entirely", lambda st: self._apply(st, {"health": +1, "happiness": -1},
                    memory="You chose safety over chaos.")),
            ]

        return EventDef("chaos_rare", "chaos", 12, 90, 4.0, cond, text, choices)

    def _midlife_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return 35 <= s.age <= 75

        def text(_: GameState) -> str:
            return "You feel a major turning point: comfort, purpose, and regret collide."

        def choices(s: GameState):
            return [
                ("Reinvent yourself with a new long-term goal", lambda st: self._risk_action(
                    st,
                    "Reinvention worked; motivation surged.",
                    "The transition was messy and costly.",
                    {"happiness": +6, "intelligence": +2, "wealth": -3},
                    {"happiness": -5, "wealth": -8},
                    risk=0.40,
                    traits={"ambitious": +1},
                    chain=(3, "Your reinvention begins to pay dividends.",
                           lambda s2: self._apply(s2, {"wealth": +10, "reputation": +4}, memory="A midlife reinvention paid off."))
                )),
                ("Stay stable and protect what you built", lambda st: self._apply(
                    st, {"health": +2, "wealth": +3},
                    traits={"disciplined": +1},
                    memory="You chose stability over reinvention."
                )),
            ]

        return EventDef("midlife_reflection", "social", 35, 75, 7.5, cond, text, choices)

    def _fame_event(self) -> EventDef:
        def cond(s: GameState) -> bool:
            return s.age >= 13 and (s.hidden["charisma"] > 55 or s.fame > 15)

        def text(_: GameState) -> str:
            return "An audience discovers your public persona."

        def choices(s: GameState):
            return [
                ("Post regularly and build brand", lambda st: self._apply(st, {"fame": +6, "wealth": +2, "happiness": -1},
                    habits={"networking": +2}, memory="You committed to public visibility.")),
                ("Stay authentic but less frequent", lambda st: self._apply(st, {"fame": +2, "happiness": +2, "reputation": +2},
                    memory="You preferred depth over virality.")),
                ("Create controversy for attention", lambda st: self._risk_action(
                    st,
                    "The controversy boosted your profile.",
                    "Backlash hurt both fame and reputation.",
                    {"fame": +10, "wealth": +4, "reputation": -2},
                    {"fame": -4, "reputation": -8, "social": -3},
                    risk=0.5,
                    traits={"reckless": +2}
                )),
            ]

        return EventDef("fame_core", "fame", 13, 90, 8.0, cond, text, choices)

    # ----------------------- Core Effect / Logic Helpers -----------------------

    def _apply(
        self,
        s: GameState,
        stat_changes: Dict[str, int],
        extra: Optional[Dict[str, int]] = None,
        habits: Optional[Dict[str, int]] = None,
        traits: Optional[Dict[str, int]] = None,
        memory: Optional[str] = None,
    ) -> str:
        for k, v in stat_changes.items():
            if k in s.stats:
                s.stats[k] = clamp(s.stats[k] + v)
            elif hasattr(s, k):
                setattr(s, k, getattr(s, k) + v)

        if extra:
            for k, v in extra.items():
                if hasattr(s, k):
                    setattr(s, k, getattr(s, k) + v)

        if habits:
            for k, v in habits.items():
                s.habits[k] = clamp(s.habits.get(k, 0) + v)

        if traits:
            for k, v in traits.items():
                s.traits[k] = clamp(s.traits.get(k, 0) + v, -20, 100)

        if memory:
            s.memories.append(memory)

        # emergent trait dynamics
        if s.habits["study"] > 28:
            s.traits["disciplined"] = clamp(s.traits["disciplined"] + 1, -20, 100)
        if s.habits["crime"] > 20:
            s.traits["reckless"] = clamp(s.traits["reckless"] + 1, -20, 100)

        return "Life moves forward with consequences."

    def _risk_action(
        self,
        s: GameState,
        success_msg: str,
        fail_msg: str,
        success_changes: Dict[str, int],
        fail_changes: Dict[str, int],
        risk: float,
        habits: Optional[Dict[str, int]] = None,
        traits: Optional[Dict[str, int]] = None,
        chain: Optional[Tuple[int, str, Callable[[GameState], None]]] = None,
    ) -> str:
        luck = s.hidden["luck"] / 100
        discipline = s.traits["disciplined"] / 200
        reckless_penalty = s.traits["reckless"] / 250
        chance = (1 - risk) + luck + discipline - reckless_penalty + self.rng.uniform(-0.18, 0.18)
        success = self.rng.random() < max(0.05, min(0.95, chance))

        if success:
            self._apply(s, success_changes, habits=habits, traits=traits, memory=success_msg)
            if chain:
                years, text, effect = chain
                s.chain_events.append({"trigger_age": s.age + years, "text": text, "effect": effect})
            return success_msg

        self._apply(s, fail_changes, habits=habits, traits=traits, memory=fail_msg)
        return fail_msg

    def _school_progress(self, s: GameState, effort: int, rep: int, stress: int) -> str:
        luck = self.rng.randint(-4, 4)
        s.school_grades = clamp(s.school_grades + effort + luck + s.habits["study"] // 8)
        s.school_rep = clamp(s.school_rep + rep + s.hidden["charisma"] // 35)
        s.stats["happiness"] = clamp(s.stats["happiness"] - stress)
        s.stats["intelligence"] = clamp(s.stats["intelligence"] + max(1, effort // 3))

        if s.age >= 18 and s.school_grades > 62 and s.education_level in {"none", "high_school"}:
            s.education_level = "college"
            s.memories.append("You entered college.")
        elif s.age >= 22 and s.education_level == "college" and s.school_grades > 70:
            s.education_level = "graduate"
            s.memories.append("You completed graduate studies.")
        else:
            s.education_level = "high_school" if s.age >= 14 else s.education_level

        return "Your academic track evolved this year."

    def _cheat_exam(self, s: GameState) -> str:
        return self._risk_action(
            s,
            success_msg="You cheated successfully and boosted your grades.",
            fail_msg="You were caught cheating; disciplinary note added.",
            success_changes={"intelligence": +1},
            fail_changes={"reputation": -7, "happiness": -3},
            risk=0.5,
            habits={"crime": +2},
            traits={"reckless": +1},
            chain=(1, "Your cheating rumor resurfaces.", lambda st: self._apply(st, {"school_rep": -6}, memory="A past cheating scandal hurt your image.")),
        )

    def _drop_out(self, s: GameState) -> str:
        s.dropped_out = True
        s.education_level = "dropout"
        s.memories.append("You dropped out of school.")
        s.stats["happiness"] = clamp(s.stats["happiness"] + 2)
        s.stats["reputation"] = clamp(s.stats["reputation"] - 4)
        s.chain_events.append({
            "trigger_age": s.age + 3,
            "text": "Without formal credentials, some jobs are now closed.",
            "effect": lambda st: setattr(st, "career_stability", st.career_stability - 8),
        })
        return "You left formal education; freedom now, constraints later."

    def _scholarship_try(self, s: GameState, flashy: bool) -> str:
        base = 0.45 + s.school_grades / 200 + s.school_rep / 250
        if flashy:
            base += self.rng.uniform(-0.12, 0.2)
        success = self.rng.random() < min(0.92, base)
        if success:
            s.scholarships += 1
            s.stats["wealth"] = clamp(s.stats["wealth"] + 12)
            s.stats["reputation"] = clamp(s.stats["reputation"] + 4)
            s.memories.append("You won a scholarship.")
            return "Scholarship awarded. New opportunities unlocked."

        s.memories.append("You were rejected from a scholarship.")
        s.stats["happiness"] = clamp(s.stats["happiness"] - 3)
        return "Application rejected; you regroup for next year."

    def _crime_attempt(self, s: GameState, scale: str) -> str:
        if scale == "small":
            return self._risk_action(
                s,
                "Small scheme succeeded; quick money gained.",
                "Caught in a small scheme; legal warning issued.",
                {"wealth": +7, "reputation": -2},
                {"reputation": -6},
                risk=0.43,
                habits={"crime": +4},
                traits={"reckless": +1},
                chain=(2, "Your old contacts pull you deeper into crime.",
                       lambda st: self._apply(st, {}, extra={"criminal_record": 4}, habits={"crime": +3}, memory="Old criminal ties resurfaced.")),
            )

        return self._risk_action(
            s,
            "Large operation paid off massively.",
            "Major bust. Your record and reputation took a huge hit.",
            {"wealth": +15, "reputation": -4},
            {"reputation": -15, "happiness": -8},
            risk=0.65,
            habits={"crime": +8},
            traits={"reckless": +2},
            chain=(1, "An investigation opens into your network.",
                   lambda st: setattr(st, "criminal_record", st.criminal_record + self.rng.randint(5, 15))),
        )

    def _relationship_shift(self, s: GameState, closeness_delta: int, trust_delta: int, message: str) -> str:
        alive = [r for r in s.relationships if r.alive]
        if not alive:
            return "No one was available to reconnect with."
        rel = self.rng.choice(alive)
        rel.closeness = clamp(rel.closeness + closeness_delta)
        rel.trust = clamp(rel.trust + trust_delta)
        rel.memory.append(message)

        if rel.kind == "partner_candidate" and rel.trust > 65 and s.partner is None:
            s.partner = rel.name
            s.memories.append(f"You entered a relationship with {rel.name}.")
        if s.partner and self.rng.random() < 0.12 and s.age > 22:
            s.children += 1
            s.memories.append(f"You welcomed child #{s.children}.")
        return f"{message} ({rel.name}: closeness {rel.closeness}, trust {rel.trust})"


if __name__ == "__main__":
    LifeSimGame().run()
