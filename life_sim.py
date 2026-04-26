import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


def clamp(v: float, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(v)))


COUNTRIES = ["USA", "Brazil", "India", "Japan", "Nigeria", "Germany", "Canada", "Mexico"]
PARENT_BACKGROUNDS = ["struggling", "working", "middle", "wealthy", "celebrity"]
FIRST_NAMES = [
    "Alex", "Jordan", "Kai", "Noah", "Maya", "Lina", "Ravi", "Sofia", "Sam", "Leila", "Rin", "Avery",
    "Evan", "Nora", "Milo", "Zara", "Asha", "Theo", "Jules", "Amara",
]


@dataclass
class Person:
    name: str
    kind: str
    age_offset: int
    personality: str
    closeness: int
    trust: int
    romance: int = 0
    memory: List[str] = field(default_factory=list)
    alive: bool = True
    status: str = "single"


@dataclass
class EventDef:
    key: str
    category: str
    min_age: int
    max_age: int
    base_weight: float
    once_per_life: bool
    condition: Callable[["GameState"], bool]
    text: Callable[["GameState"], str]
    choices: Callable[["GameState"], List[Tuple[str, Callable[["GameState"], str]]]]


@dataclass
class GameState:
    name: str
    age: int = 0
    alive: bool = True
    cause_of_death: Optional[str] = None

    location: str = ""
    upbringing: str = ""
    generation: int = 1

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
        "network": 0,
        "substance": 0,
    })
    traits: Dict[str, int] = field(default_factory=lambda: {
        "disciplined": 0,
        "reckless": 0,
        "kind": 0,
        "ambitious": 0,
    })

    education_level: str = "none"
    grades: int = 50
    school_rep: int = 50
    scholarships: int = 0
    dropped_out: bool = False

    career: str = "none"
    career_level: int = 0
    career_stability: int = 50
    fame: int = 0

    criminal_record: int = 0
    heat: int = 0
    gang_rank: int = 0
    prison_years: int = 0

    relatives: List[Person] = field(default_factory=list)
    friends: List[Person] = field(default_factory=list)
    partners: List[Person] = field(default_factory=list)
    flings: List[Person] = field(default_factory=list)
    children: List[Person] = field(default_factory=list)

    memories: List[str] = field(default_factory=list)
    chain_events: List[Dict] = field(default_factory=list)
    event_history: Dict[str, int] = field(default_factory=dict)
    once_flags: Dict[str, bool] = field(default_factory=dict)


class LifeSimGame:
    def __init__(self):
        self.rng = random.Random()
        self.state = GameState(name="")
        self.events = self._build_events()

    # --------------------------- Main loop ---------------------------

    def run(self):
        self._intro()
        while True:
            while self.state.alive:
                self._year()

            self._legacy_summary()
            if not self.state.children:
                print("No surviving children to continue your legacy. Game over.")
                break
            choice = input("Continue as one of your children? (y/n): ").strip().lower()
            if choice != "y":
                break
            if not self._continue_as_child():
                break

    def _year(self):
        s = self.state
        print("\n" + "-" * 62)
        print(f"Generation {s.generation} | Age {s.age} -> {s.age + 1}")
        s.age += 1

        self._process_chain_events()
        self._npc_world_tick()
        self._base_stat_tick()

        yearly_events = self._choose_events(1 if s.age < 8 else (2 if s.age < 40 else 3))
        for ev in yearly_events:
            self._run_event(ev)

        self._career_tick()
        self._death_check()
        self._print_summary()
        if s.alive:
            if input("Enter=next year, q=quit: ").strip().lower() == "q":
                s.alive = False
                s.cause_of_death = "chosen early retirement from this narrative"

    # --------------------------- Setup ---------------------------

    def _intro(self):
        name = input("Enter first character name: ").strip() or "Alex"
        s = self.state
        s.name = name
        s.location = self.rng.choice(COUNTRIES)
        s.upbringing = self.rng.choice(PARENT_BACKGROUNDS)
        s.hidden = {
            "luck": self.rng.randint(25, 90),
            "charisma": self.rng.randint(25, 90),
            "resilience": self.rng.randint(25, 90),
            "risk": self.rng.randint(15, 85),
        }

        bg_wealth = {"struggling": -12, "working": -3, "middle": 5, "wealthy": 22, "celebrity": 30}
        s.stats["wealth"] = clamp(s.stats["wealth"] + bg_wealth[s.upbringing])

        s.relatives = [
            Person(self.rng.choice(FIRST_NAMES), "parent", 28, self.rng.choice(["strict", "warm", "practical"]), 65, 60),
            Person(self.rng.choice(FIRST_NAMES), "parent", 30, self.rng.choice(["supportive", "impulsive", "private"]), 55, 55),
        ]
        print(f"\nBorn in {s.location} to a {s.upbringing} family.")

    # --------------------------- Event engine ---------------------------

    def _choose_events(self, n: int) -> List[EventDef]:
        weighted = []
        for ev in self.events:
            w = self._event_weight(ev)
            if w > 0:
                weighted.append((ev, w))

        chosen: List[EventDef] = []
        for _ in range(min(n, len(weighted))):
            total = sum(w for _, w in weighted)
            pick = self.rng.random() * total
            run = 0.0
            idx = 0
            for i, (_, w) in enumerate(weighted):
                run += w
                if run >= pick:
                    idx = i
                    break
            chosen.append(weighted[idx][0])
            weighted.pop(idx)
        return chosen

    def _event_weight(self, ev: EventDef) -> float:
        s = self.state
        if not (ev.min_age <= s.age <= ev.max_age):
            return 0.0
        if ev.once_per_life and s.once_flags.get(ev.key):
            return 0.0
        if not ev.condition(s):
            return 0.0
        seen = s.event_history.get(ev.key, 0)
        rep_penalty = 0.52 ** seen
        age_boost = 1.2 if ev.category == "school" and 6 <= s.age <= 22 else 1.0
        crime_boost = 1.4 if ev.category == "crime" and s.habits["crime"] > 20 else 1.0
        rare_noise = self.rng.uniform(0.85, 1.22)
        return ev.base_weight * rep_penalty * age_boost * crime_boost * rare_noise

    def _run_event(self, ev: EventDef):
        s = self.state
        print(f"\n[{ev.category.upper()}] {ev.text(s)}")
        options = ev.choices(s)
        for i, (label, _) in enumerate(options, 1):
            print(f"  {i}) {label}")
        c = self._read_choice(len(options))
        msg = options[c - 1][1](s)
        print(f"  -> {msg}")
        s.event_history[ev.key] = s.event_history.get(ev.key, 0) + 1
        if ev.once_per_life:
            s.once_flags[ev.key] = True

    @staticmethod
    def _read_choice(max_n: int) -> int:
        while True:
            r = input("Choose: ").strip()
            if r.isdigit() and 1 <= int(r) <= max_n:
                return int(r)
            print("Enter a valid option number.")

    # --------------------------- Systems ---------------------------

    def _base_stat_tick(self):
        s = self.state
        s.stats["health"] = clamp(s.stats["health"] - self.rng.randint(0, 2) + s.habits["exercise"] // 8 - s.habits["substance"] // 8)
        s.stats["happiness"] = clamp(s.stats["happiness"] - self.rng.randint(0, 3) + s.hidden["resilience"] // 24)
        s.stats["social"] = clamp(s.stats["social"] - self.rng.randint(0, 2) + s.habits["network"] // 8)
        s.stats["reputation"] = clamp(s.stats["reputation"] - s.criminal_record // 10)

        if s.prison_years > 0:
            s.prison_years -= 1
            s.stats["happiness"] = clamp(s.stats["happiness"] - 4)
            s.stats["wealth"] = clamp(s.stats["wealth"] - 3)
            print("\nYou are serving prison time this year.")

    def _npc_world_tick(self):
        s = self.state
        everyone = s.relatives + s.friends + s.partners + s.flings + s.children
        for p in everyone:
            if not p.alive:
                continue
            if self.rng.random() < 0.02 and s.age > 18:
                p.memory.append("had a major life change")
                p.trust = clamp(p.trust + self.rng.randint(-5, 5))
            if self.rng.random() < 0.012 and s.age > 45:
                p.alive = False
                s.memories.append(f"{p.name} ({p.kind}) passed away")

        if 9 <= s.age <= 70 and self.rng.random() < 0.13:
            new_friend = Person(
                self.rng.choice(FIRST_NAMES),
                self.rng.choice(["friend", "coworker"]),
                self.rng.randint(-4, 4),
                self.rng.choice(["loyal", "dramatic", "funny", "private", "strategic"]),
                self.rng.randint(30, 70),
                self.rng.randint(30, 70),
            )
            s.friends.append(new_friend)
            print(f"\nYou met {new_friend.name} ({new_friend.kind}, {new_friend.personality}).")

    def _career_tick(self):
        s = self.state
        if s.age < 16 or s.prison_years > 0:
            return
        if s.career == "none" and s.age >= 18:
            if s.criminal_record > 25 or s.habits["crime"] > 35:
                s.career = "criminal"
            elif s.fame > 40:
                s.career = "creator"
            elif s.education_level in {"college", "graduate"}:
                s.career = self.rng.choice(["engineering", "medicine", "law", "research"])
            else:
                s.career = self.rng.choice(["retail", "construction", "service"])
            print(f"\nCareer started: {s.career}")

        pay = 0
        if s.career in {"retail", "construction", "service"}:
            pay = 8 + s.career_level * 2
        elif s.career in {"engineering", "medicine", "law", "research"}:
            pay = 15 + s.career_level * 6
            s.stats["intelligence"] = clamp(s.stats["intelligence"] + 1)
        elif s.career == "creator":
            pay = 2 + s.fame // 4
            s.fame = clamp(s.fame + self.rng.randint(-2, 7))
        elif s.career == "criminal":
            pay = 6 + s.gang_rank * 3 + s.habits["crime"] // 4
            s.heat += self.rng.randint(1, 6)

        promo = 0.08 + s.traits["disciplined"] / 120 + s.hidden["luck"] / 500
        if self.rng.random() < promo:
            s.career_level += 1
            s.stats["reputation"] = clamp(s.stats["reputation"] + 2)
            print("  Promotion/major progression this year.")
        s.stats["wealth"] = clamp(s.stats["wealth"] + pay)

    def _death_check(self):
        s = self.state
        risk = max(0, s.age - 58) * 0.8 + max(0, 38 - s.stats["health"]) * 1.2 + s.heat * 0.2 + self.rng.uniform(0, 35)
        if s.age >= 100 or risk > 95:
            s.alive = False
            s.cause_of_death = self.rng.choice(["natural causes", "sudden illness", "stress-related collapse", "accident"])

    def _process_chain_events(self):
        s = self.state
        pending = []
        for ch in s.chain_events:
            if s.age >= ch["age"]:
                print(f"\n[CONSEQUENCE] {ch['text']}")
                ch["fx"](s)
            else:
                pending.append(ch)
        s.chain_events = pending

    # --------------------------- Gameplay helpers ---------------------------

    def _apply(self, stat: Dict[str, int], extra: Optional[Dict[str, int]] = None,
               habits: Optional[Dict[str, int]] = None, traits: Optional[Dict[str, int]] = None,
               memory: Optional[str] = None):
        s = self.state
        for k, v in stat.items():
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

    def _risk(self, success: Dict[str, int], fail: Dict[str, int], base_risk: float,
              success_msg: str, fail_msg: str,
              extra_success: Optional[Dict[str, int]] = None,
              extra_fail: Optional[Dict[str, int]] = None,
              habits: Optional[Dict[str, int]] = None,
              traits: Optional[Dict[str, int]] = None) -> str:
        s = self.state
        chance = (1 - base_risk) + s.hidden["luck"] / 110 + s.traits["disciplined"] / 220 - s.traits["reckless"] / 260
        chance += self.rng.uniform(-0.22, 0.22)
        chance = max(0.05, min(0.95, chance))
        if self.rng.random() < chance:
            self._apply(success, extra_success, habits, traits, success_msg)
            return success_msg
        self._apply(fail, extra_fail, habits, traits, fail_msg)
        return fail_msg

    # --------------------------- Event content ---------------------------

    def _build_events(self) -> List[EventDef]:
        fixed = [
            self._once_in_life_event(),
            self._school_event(),
            self._relationship_event(),
            self._romance_event(),
            self._crime_heist_event(),
            self._crime_gang_event(),
            self._crime_police_event(),
            self._family_event(),
            self._health_event(),
            self._fame_event(),
        ]
        generated = self._generate_event_pool(220)
        return fixed + generated

    def _once_in_life_event(self) -> EventDef:
        return EventDef(
            key="once_life_black_swan",
            category="rare",
            min_age=16,
            max_age=75,
            base_weight=1.1,
            once_per_life=True,
            condition=lambda s: True,
            text=lambda s: "Once-in-a-lifetime black swan event: a mysterious patron offers one extraordinary deal.",
            choices=lambda s: [
                ("Take the deal", lambda st: self._risk(
                    {"wealth": 25, "reputation": 6, "happiness": 5},
                    {"wealth": -15, "reputation": -12, "happiness": -8},
                    0.52,
                    "The deal changed your life in your favor.",
                    "The deal imploded and became a cautionary tale.",
                )),
                ("Decline and keep stable path", lambda st: (self._apply({"health": 2, "happiness": 1}, memory="You rejected a once-in-life gamble."), "You chose stability.")[1]),
            ],
        )

    def _school_event(self) -> EventDef:
        def do_school_focus(_: GameState) -> str:
            s = self.state
            self._apply({"intelligence": 3, "happiness": -1}, habits={"study": 3}, traits={"disciplined": 1}, memory="You doubled down on studying.")
            s.grades = clamp(s.grades + 7 + self.rng.randint(-3, 3))
            s.school_rep = clamp(s.school_rep + 2)
            if s.age >= 18 and s.grades > 62 and s.education_level in {"none", "high_school"}:
                s.education_level = "college"
                s.memories.append("You entered college.")
            elif s.age >= 22 and s.education_level == "college" and s.grades > 72:
                s.education_level = "graduate"
                s.memories.append("You completed graduate school.")
            return "Your academic profile improved."

        def do_dropout(_: GameState) -> str:
            s = self.state
            s.dropped_out = True
            s.education_level = "dropout"
            self._apply({"happiness": 2, "reputation": -5}, memory="You dropped out.")
            s.chain_events.append({"age": s.age + 3, "text": "Lack of credentials blocks several job tracks.",
                                   "fx": lambda ss: setattr(ss, "career_stability", ss.career_stability - 10)})
            return "You left formal education; consequences will appear over time."

        return EventDef(
            key="school_core",
            category="school",
            min_age=6,
            max_age=24,
            base_weight=16,
            once_per_life=False,
            condition=lambda s: not s.dropped_out,
            text=lambda s: f"School pressure rises (grades {s.grades}, school reputation {s.school_rep}).",
            choices=lambda s: [
                ("Study harder", do_school_focus),
                ("Focus social life", lambda st: (self._apply({"social": 4, "happiness": 2}, habits={"network": 2}, memory="You prioritized social life."), setattr(self.state, "grades", clamp(self.state.grades + self.rng.randint(-5, 3))), "Socially stronger, academically mixed.")[2]),
                ("Cheat on key exam", lambda st: self._risk({"intelligence": 1}, {"reputation": -8, "happiness": -3}, 0.5,
                                                             "Cheating worked this time.", "You were caught cheating.",
                                                             extra_fail={"school_rep": -8}, habits={"crime": 2}, traits={"reckless": 1})),
                ("Drop out", do_dropout if self.state.age >= 14 else (lambda st: "Too young to drop out.")),
            ],
        )

    def _family_event(self) -> EventDef:
        return EventDef(
            key="family_core",
            category="family",
            min_age=4,
            max_age=80,
            base_weight=12,
            once_per_life=False,
            condition=lambda s: len([p for p in s.relatives if p.alive]) > 0,
            text=lambda s: "A family member asks for help during a difficult period.",
            choices=lambda s: [
                ("Provide time and support", lambda st: (self._apply({"happiness": 1, "social": 3, "wealth": -2}, traits={"kind": 2}, memory="You supported family during crisis."), "Family bond strengthened.")[1]),
                ("Send money only", lambda st: (self._apply({"wealth": -6, "reputation": 2}, memory="You provided financial help to family."), "You helped financially.")[1]),
                ("Refuse", lambda st: self._risk({"wealth": 3}, {"social": -6, "happiness": -3}, 0.7,
                                                  "You preserved resources with limited fallout.", "Family trust collapsed after refusal.")),
            ],
        )

    def _relationship_event(self) -> EventDef:
        def target() -> Optional[Person]:
            s = self.state
            pool = [p for p in (s.friends + s.partners + s.relatives) if p.alive]
            return self.rng.choice(pool) if pool else None

        def reconnect(_: GameState) -> str:
            p = target()
            if not p:
                return "No one available right now."
            p.closeness = clamp(p.closeness + 8)
            p.trust = clamp(p.trust + 7)
            p.memory.append("You reconnected sincerely")
            self._apply({"social": 3, "happiness": 2}, memory=f"You rebuilt trust with {p.name}.")
            return f"You reconnected with {p.name}."

        def ask_favor(_: GameState) -> str:
            p = target()
            if not p:
                return "No one available right now."
            msg = self._risk({"wealth": 5, "social": 2}, {"social": -5, "happiness": -2}, 0.47,
                             f"{p.name} helped you significantly.", f"{p.name} felt used and withdrew.")
            p.trust = clamp(p.trust + (6 if "helped" in msg else -9))
            return msg

        return EventDef(
            key="relationship_core",
            category="social",
            min_age=12,
            max_age=95,
            base_weight=11,
            once_per_life=False,
            condition=lambda s: True,
            text=lambda s: "Someone from your life remembers your past behavior and reacts.",
            choices=lambda s: [
                ("Reconnect honestly", reconnect),
                ("Keep distance", lambda st: (self._apply({"social": -2, "happiness": -1}, memory="You chose distance in a relationship moment."), "Distance increased." )[1]),
                ("Ask for a big favor", ask_favor),
            ],
        )

    def _romance_event(self) -> EventDef:
        def date(_: GameState) -> str:
            s = self.state
            person = Person(self.rng.choice(FIRST_NAMES), "partner", self.rng.randint(-5, 5),
                            self.rng.choice(["passionate", "steady", "adventurous", "private"]), 45, 50, romance=55)
            result = self._risk({"happiness": 4, "social": 3}, {"happiness": -2}, 0.42,
                                f"You and {person.name} started dating.", f"Date with {person.name} had no spark.")
            if "started dating" in result:
                s.partners.append(person)
                if self.rng.random() < 0.18 and s.age > 22:
                    child = Person(self.rng.choice(FIRST_NAMES), "child", -s.age, self.rng.choice(["curious", "calm", "bold"]), 60, 60)
                    s.children.append(child)
                    s.memories.append(f"Child born: {child.name}.")
            return result

        def one_night(_: GameState) -> str:
            s = self.state
            fling = Person(self.rng.choice(FIRST_NAMES), "one_night_stand", self.rng.randint(-8, 8),
                           self.rng.choice(["wild", "gentle", "mysterious"]), 20, 25, romance=25)
            s.flings.append(fling)
            msg = self._risk({"happiness": 3}, {"reputation": -5, "health": -2}, 0.57,
                             f"You had a thrilling night with {fling.name}.", f"The fling with {fling.name} caused messy fallout.")
            if self.rng.random() < 0.08:
                child = Person(self.rng.choice(FIRST_NAMES), "child", -s.age, self.rng.choice(["curious", "calm", "bold"]), 40, 45)
                s.children.append(child)
                s.memories.append(f"Unexpected child from fling: {child.name}.")
            return msg

        return EventDef(
            key="romance_core",
            category="romance",
            min_age=16,
            max_age=75,
            base_weight=9,
            once_per_life=False,
            condition=lambda s: True,
            text=lambda s: "Romantic energy rises: commitment or impulse?",
            choices=lambda s: [
                ("Go on a serious date", date),
                ("One-night stand", one_night),
                ("Stay single this year", lambda st: (self._apply({"health": 1, "happiness": -1}, memory="You stayed single and focused elsewhere."), "You chose solitude.")[1]),
            ],
        )

    # Deep crime system
    def _crime_heist_event(self) -> EventDef:
        def small_heist(_: GameState) -> str:
            s = self.state
            return self._risk({"wealth": 10, "reputation": -2}, {"happiness": -4, "reputation": -9}, 0.48,
                              "Small heist succeeded.", "Small heist failed; police took interest.",
                              extra_success={"heat": 4}, extra_fail={"heat": 12, "criminal_record": 6},
                              habits={"crime": 4}, traits={"reckless": 1})

        def big_heist(_: GameState) -> str:
            s = self.state
            msg = self._risk({"wealth": 28, "reputation": -5}, {"wealth": -12, "happiness": -10, "reputation": -16}, 0.68,
                             "Major heist paid out huge.", "Major heist collapsed disastrously.",
                             extra_success={"heat": 15, "criminal_record": 3},
                             extra_fail={"heat": 30, "criminal_record": 14},
                             habits={"crime": 9}, traits={"reckless": 2})
            s.chain_events.append({
                "age": s.age + 1,
                "text": "Investigators connect evidence to your network.",
                "fx": lambda ss: setattr(ss, "heat", ss.heat + self.rng.randint(6, 14)),
            })
            return msg

        return EventDef(
            key="crime_heist",
            category="crime",
            min_age=14,
            max_age=90,
            base_weight=10,
            once_per_life=False,
            condition=lambda s: s.prison_years == 0,
            text=lambda s: f"A criminal contact proposes a heist (current heat {s.heat}).",
            choices=lambda s: [
                ("Decline", lambda st: (self._apply({"reputation": 1}, habits={"crime": -1}, memory="You avoided a heist."), "You stayed clean this time.")[1]),
                ("Run a small heist", small_heist),
                ("Run a major heist", big_heist),
            ],
        )

    def _crime_gang_event(self) -> EventDef:
        def join(_: GameState) -> str:
            s = self.state
            msg = self._risk({"wealth": 7}, {"happiness": -5, "reputation": -6}, 0.44,
                             "You joined a gang and gained protection.", "Initiation went badly and raised enemies.",
                             extra_success={"gang_rank": 1, "heat": 7}, extra_fail={"heat": 14, "criminal_record": 4},
                             habits={"crime": 5})
            return msg

        def move_up(_: GameState) -> str:
            s = self.state
            return self._risk({"wealth": 16}, {"health": -7, "happiness": -6}, 0.59,
                              "You rose in rank and now control territory.", "Power move failed; violent retaliation followed.",
                              extra_success={"gang_rank": 2, "heat": 12}, extra_fail={"heat": 18, "criminal_record": 7},
                              habits={"crime": 6}, traits={"reckless": 1})

        return EventDef(
            key="crime_gang",
            category="crime",
            min_age=15,
            max_age=90,
            base_weight=8,
            once_per_life=False,
            condition=lambda s: s.prison_years == 0,
            text=lambda s: f"Gang politics intensify (rank {s.gang_rank}, heat {s.heat}).",
            choices=lambda s: [
                ("Stay out", lambda st: (self._apply({"health": 1}, memory="You avoided gang escalation."), "You stayed out.")[1]),
                ("Join/maintain gang ties", join),
                ("Push for higher rank", move_up),
            ],
        )

    def _crime_police_event(self) -> EventDef:
        def fight_case(_: GameState) -> str:
            s = self.state
            lawyer = 8 if s.stats["wealth"] > 20 else 0
            chance = 0.35 + s.hidden["luck"] / 180 + lawyer / 100 - s.heat / 200
            if self.rng.random() < chance:
                self._apply({"wealth": -8, "reputation": 2}, extra={"heat": -10}, memory="You beat a criminal case in court.")
                return "Case dismissed after legal battle."
            sentence = self.rng.randint(1, 5)
            s.prison_years += sentence
            s.criminal_record += self.rng.randint(4, 10)
            self._apply({"happiness": -8, "wealth": -6}, memory=f"You lost a criminal case and got {sentence} years.")
            return f"Convicted. Sentence: {sentence} years."

        return EventDef(
            key="crime_police",
            category="crime",
            min_age=15,
            max_age=95,
            base_weight=9,
            once_per_life=False,
            condition=lambda s: s.heat >= 10 or s.criminal_record >= 8,
            text=lambda s: f"Law enforcement crackdowns intensify (heat {s.heat}, record {s.criminal_record}).",
            choices=lambda s: [
                ("Lay low", lambda st: (self._apply({"wealth": -2, "happiness": -1}, extra={"heat": -6}, memory="You laid low to avoid arrest."), "You stayed quiet.")[1]),
                ("Fight the case aggressively", fight_case),
                ("Attempt to flee city", lambda st: self._risk({"reputation": -3}, {"reputation": -10, "happiness": -4}, 0.62,
                                                               "You escaped immediate arrest but lost status.",
                                                               "You were caught while fleeing.",
                                                               extra_success={"heat": -5}, extra_fail={"heat": 12, "criminal_record": 6})),
            ],
        )

    def _health_event(self) -> EventDef:
        return EventDef(
            key="health_core",
            category="health",
            min_age=10,
            max_age=100,
            base_weight=10,
            once_per_life=False,
            condition=lambda s: True,
            text=lambda s: "Your physical and mental health demand attention.",
            choices=lambda s: [
                ("Exercise and recover", lambda st: (self._apply({"health": 6, "happiness": 2}, habits={"exercise": 4}, traits={"disciplined": 1}, memory="You committed to health."), "You got healthier.")[1]),
                ("Overwork and ignore it", lambda st: (self._apply({"health": -4, "wealth": 3}, traits={"ambitious": 1}, memory="You traded health for output."), "Short-term gain, long-term risk.")[1]),
                ("Substances to cope", lambda st: self._risk({"happiness": 3}, {"health": -8, "reputation": -4}, 0.7,
                                                              "Temporary relief worked.", "Dependence worsened your health.", habits={"substance": 5})),
            ],
        )

    def _fame_event(self) -> EventDef:
        return EventDef(
            key="fame_core",
            category="fame",
            min_age=13,
            max_age=90,
            base_weight=8,
            once_per_life=False,
            condition=lambda s: s.hidden["charisma"] > 55 or s.fame > 10,
            text=lambda s: "Audience attention spikes around your public persona.",
            choices=lambda s: [
                ("Build authentic audience", lambda st: (self._apply({"fame": 4, "reputation": 3, "wealth": 2}, habits={"network": 2}, memory="You built a genuine audience."), "Steady public growth.")[1]),
                ("Farm controversy", lambda st: self._risk({"fame": 11, "wealth": 5}, {"fame": -5, "reputation": -9}, 0.5,
                                                           "Controversy spiked your reach.", "Backlash damaged your image.", traits={"reckless": 2})),
                ("Take a privacy break", lambda st: (self._apply({"health": 2, "fame": -2, "happiness": 2}, memory="You took time away from public attention."), "You recovered in private.")[1]),
            ],
        )

    def _generate_event_pool(self, target_count: int) -> List[EventDef]:
        themes = [
            ("childhood", 1, 12), ("school", 6, 24), ("career", 18, 95), ("crime", 14, 95),
            ("social", 10, 95), ("family", 4, 95), ("health", 10, 100), ("chaos", 12, 95),
            ("finance", 16, 95), ("romance", 16, 80),
        ]
        pool: List[EventDef] = []
        idx = 0
        while len(pool) < target_count:
            for cat, amin, amax in themes:
                if len(pool) >= target_count:
                    break
                i = idx
                key = f"gen_{cat}_{i}"
                intensity = (i % 5) + 1

                def cond_factory(c: str, power: int):
                    if c == "crime":
                        return lambda s: s.prison_years == 0 and (s.habits["crime"] > power * 2 or s.age > 18)
                    if c == "school":
                        return lambda s: not s.dropped_out
                    if c == "career":
                        return lambda s: s.age >= 16
                    if c == "romance":
                        return lambda s: s.age >= 16
                    return lambda s: True

                def text_factory(c: str, n: int):
                    return lambda s: f"{c.title()} scenario #{n}: context reacts to your history, traits, and current pressures."

                def choices_factory(c: str, power: int):
                    def cautious(_: GameState) -> str:
                        self._apply({"health": 1, "reputation": 1}, memory=f"Handled {c} scenario carefully.")
                        return "You chose the cautious option."

                    def ambitious(_: GameState) -> str:
                        return self._risk(
                            {"wealth": 2 * power, "happiness": 1, "reputation": 1},
                            {"health": -2, "reputation": -2, "happiness": -1},
                            0.45 + power * 0.04,
                            "Ambitious move paid off.",
                            "Ambitious move backfired.",
                            extra_success={"heat": 2} if c == "crime" else None,
                            extra_fail={"criminal_record": 2, "heat": 4} if c == "crime" else None,
                            habits={"crime": 1} if c == "crime" else ({"network": 1} if c in {"career", "social", "romance"} else None),
                            traits={"ambitious": 1},
                        )

                    def impulsive(_: GameState) -> str:
                        return self._risk(
                            {"happiness": 2, "social": 2},
                            {"reputation": -3, "happiness": -2},
                            0.58,
                            "Impulsive choice created exciting momentum.",
                            "Impulsive choice caused messy consequences.",
                            habits={"crime": 2} if c == "crime" else None,
                            traits={"reckless": 1},
                        )

                    return [
                        (f"Cautious {c} response", cautious),
                        (f"Ambitious {c} response", ambitious),
                        (f"Impulsive {c} response", impulsive),
                    ]

                pool.append(EventDef(
                    key=key,
                    category=cat,
                    min_age=amin,
                    max_age=amax,
                    base_weight=5.0 + (i % 4),
                    once_per_life=False,
                    condition=cond_factory(cat, intensity),
                    text=text_factory(cat, i),
                    choices=lambda s, c=cat, p=intensity: choices_factory(c, p),
                ))
                idx += 1
        return pool

    # --------------------------- Legacy ---------------------------

    def _continue_as_child(self) -> bool:
        s = self.state
        eligible = [c for c in s.children if c.alive]
        if not eligible:
            return False
        print("\nChoose child:")
        for i, c in enumerate(eligible, 1):
            print(f"  {i}) {c.name} (personality: {c.personality})")
        choice = self._read_choice(len(eligible))
        heir = eligible[choice - 1]

        parent_wealth = s.stats["wealth"]
        parent_rep = s.stats["reputation"]

        new_state = GameState(name=heir.name)
        new_state.generation = s.generation + 1
        new_state.location = s.location
        new_state.upbringing = "legacy child"
        new_state.stats["wealth"] = clamp(20 + parent_wealth // 2)
        new_state.stats["reputation"] = clamp(45 + parent_rep // 3)
        new_state.hidden = {
            "luck": clamp((s.hidden["luck"] + self.rng.randint(20, 80)) / 2),
            "charisma": clamp((s.hidden["charisma"] + self.rng.randint(20, 80)) / 2),
            "resilience": clamp((s.hidden["resilience"] + self.rng.randint(20, 80)) / 2),
            "risk": clamp((s.hidden["risk"] + self.rng.randint(20, 80)) / 2),
        }
        # carry world continuity
        new_state.relatives = [Person(s.name, "parent", 28, "legacy", 60, 60, alive=False, status="deceased")]
        new_state.children = []
        new_state.memories.append(f"Inherited legacy from {s.name} (Gen {s.generation}).")
        self.state = new_state
        print(f"\nLegacy continues as {new_state.name} (Generation {new_state.generation}).")
        return True

    def _legacy_summary(self):
        s = self.state
        print("\n" + "=" * 62)
        print(f"{s.name} (Generation {s.generation}) died at age {s.age} due to {s.cause_of_death}.")
        print(f"Final stats: {s.stats}")
        print(f"Education={s.education_level} | Career={s.career} L{s.career_level} | Record={s.criminal_record} | Fame={s.fame}")
        print(f"Children: {len(s.children)} | Partners met: {len(s.partners)} | Flings: {len(s.flings)}")
        if s.memories:
            print("Legacy memories:")
            for m in s.memories[-8:]:
                print(f"  - {m}")

    def _print_summary(self):
        s = self.state
        print("\nYear summary:")
        print(f"  Hlt {s.stats['health']} | Hap {s.stats['happiness']} | Int {s.stats['intelligence']} | Wlt {s.stats['wealth']} | Soc {s.stats['social']} | Rep {s.stats['reputation']}")
        print(f"  Edu {s.education_level} (grades {s.grades}) | Career {s.career} L{s.career_level} | Record {s.criminal_record} Heat {s.heat} PrisonY {s.prison_years}")
        print(f"  Family {len([x for x in s.relatives if x.alive])} | Friends {len([x for x in s.friends if x.alive])} | Partners {len([x for x in s.partners if x.alive])} | Children {len([x for x in s.children if x.alive])}")


if __name__ == "__main__":
    LifeSimGame().run()
