# Fixed & Polished Version
import pickle
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


def clamp(v: float, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(v)))


COUNTRIES = ["USA", "Brazil", "India", "Japan", "Nigeria", "Germany", "Canada", "Mexico"]
BACKGROUNDS = ["struggling", "working", "middle", "wealthy", "celebrity"]
FIRST_NAMES = [
    "Alex", "Jordan", "Kai", "Noah", "Maya", "Lina", "Ravi", "Sofia", "Sam", "Leila", "Rin", "Avery",
    "Evan", "Nora", "Milo", "Zara", "Asha", "Theo", "Jules", "Amara", "Iris", "Diego", "Nia", "Omar",
]
LOOKS = ["plain", "charming", "striking", "unconventional", "elegant", "athletic"]
SEXUALITY = ["straight", "gay", "bisexual", "asexual", "pansexual"]


@dataclass
class Person:
    name: str
    kind: str
    age_offset: int
    personality: str
    closeness: int
    trust: int
    romance: int = 0
    mood: int = 50
    last_interaction: int = 0
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
    generation: int = 1

    location: str = ""
    upbringing: str = ""
    looks: int = 50
    looks_desc: str = "plain"
    sexuality: str = "straight"

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
        "alcohol": 0,
        "drugs": 0,
        "gambling": 0,
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
    dropped_out: bool = False

    career: str = "none"
    career_level: int = 0
    unemployed_years: int = 0
    fame: int = 0

    criminal_record: int = 0
    heat: int = 0
    gang_rank: int = 0
    prison_years: int = 0

    assets: Dict[str, int] = field(default_factory=lambda: {
        "house": 0,
        "car": 0,
        "luxury": 0,
        "pet": 0,
        "business": 0,
    })
    investments: int = 0
    debt: int = 0

    relatives: List[Person] = field(default_factory=list)
    friends: List[Person] = field(default_factory=list)
    partners: List[Person] = field(default_factory=list)
    flings: List[Person] = field(default_factory=list)
    children: List[Person] = field(default_factory=list)

    chain_events: List[Dict] = field(default_factory=list)
    event_history: Dict[str, int] = field(default_factory=dict)
    once_flags: Dict[str, bool] = field(default_factory=dict)
    achievements: Dict[str, bool] = field(default_factory=dict)
    memories: List[str] = field(default_factory=list)


class LifeSimGame:
    def __init__(self):
        self.rng = random.Random()
        self.state = GameState(name="")
        self.events = self._build_events()

    # ----------------------- run/setup -----------------------

    def run(self):
        self._intro()
        while True:
            while self.state.alive:
                self._year()
            self._legacy_summary()
            if not self.state.children:
                print("No children available for continuation.")
                break
            c = input("Continue as a child? (y/n): ").strip().lower()
            if c != "y":
                break
            if not self._continue_as_child():
                break

    def _intro(self):
        s = self.state
        s.name = input("Enter character name: ").strip() or "Alex"
        s.location = self.rng.choice(COUNTRIES)
        s.upbringing = self.rng.choice(BACKGROUNDS)
        s.looks = self.rng.randint(25, 85)
        s.looks_desc = self.rng.choice(LOOKS)
        s.sexuality = self.rng.choice(SEXUALITY)

        s.hidden = {
            "luck": self.rng.randint(20, 90),
            "charisma": self.rng.randint(20, 90),
            "resilience": self.rng.randint(20, 90),
            "risk": self.rng.randint(10, 85),
        }
        bonus = {"struggling": -12, "working": -3, "middle": 5, "wealthy": 20, "celebrity": 30}
        s.stats["wealth"] = clamp(s.stats["wealth"] + bonus[s.upbringing])
        s.relatives = [
            Person(self.rng.choice(FIRST_NAMES), "parent", 28, "practical", 65, 60),
            Person(self.rng.choice(FIRST_NAMES), "parent", 31, "supportive", 58, 57),
        ]
        print(f"\nBorn in {s.location} | upbringing: {s.upbringing} | looks: {s.looks_desc} ({s.looks}) | sexuality: {s.sexuality}")

    # ----------------------- yearly loop -----------------------

    def _year(self):
        s = self.state
        print("\n" + "-" * 70)
        print(f"Generation {s.generation} | Age {s.age} -> {s.age + 1}")
        s.age += 1

        self._process_chain_events()
        self._npc_world_tick()
        self._base_tick()

        action_result = self._activity_menu()
        print(f"\n=> {action_result}")

        yearly_events = self._choose_events(1 if s.age < 12 else 2 if s.age < 45 else 3)
        for ev in yearly_events:
            self._run_event(ev)

        self._economy_tick()
        self._relationship_manager()
        self._addiction_tick()
        self._career_tick()
        self._achievement_tick()
        self._death_check()
        self._summary()

        if s.alive:
            cmd = input("Enter=next year | save | load | q: ").strip().lower()
            if cmd == "q":
                s.alive = False
                s.cause_of_death = "retired this life early"
            elif cmd == "save":
                self.save_game()
            elif cmd == "load":
                fn = input("Filename: ").strip()
                self.load_game(fn)

    # ----------------------- activity menu -----------------------

    def _activity_menu(self) -> str:
        s = self.state
        print("\n" + "=" * 70)
        print(f"AGE {s.age}: What will you do this year?")
        print("=" * 70)
        
        actions = [
            ("1", "Focus on Studies/Work", self._do_study_or_work),
            ("2", "Exercise / Gym", self._do_exercise),
            ("3", "Socialize / Party", self._do_socialize),
            ("4", "Romantic Pursuit", self._do_romance_action),
            ("5", "Hustle / Side Income", self._do_hustle),
            ("6", "Rest & Self-Care", self._do_rest),
            ("7", "Travel", self._do_travel),
            ("8", "Gamble", self._do_gamble),
            ("9", "Crime Menu", self._crime_menu),
            ("10", "Buy Assets", self._do_buy_assets),
            ("11", "Invest / Trade", self._do_invest),
            ("12", "Appearance Upgrade", self._do_appearance),
            ("13", "Volunteer", self._do_volunteer),
            ("14", "Therapy / Meditation", self._do_therapy),
            ("15", "Start/Run Business", self._do_business),
            ("0", "Skip / Let Life Happen", lambda: "You let the year flow naturally."),
        ]
        
        for num, label, _ in actions:
            print(f"{num}) {label}")
        
        choice = input("\nChoose (0-15): ").strip()
        for num, _, func in actions:
            if choice == num:
                return func()
        return "Invalid choice. The year passed quietly."

    # ----------------------- action handlers -----------------------

    def _do_study_or_work(self) -> str:
        s = self.state
        if s.age < 23 and not s.dropped_out:
            s.grades = clamp(s.grades + self.rng.randint(3, 10))
            self._apply({"intelligence": 4, "happiness": -1}, habits={"study": 4}, traits={"disciplined": 1})
            return f"You focused academically (grades now {s.grades})."
        self._apply({"wealth": 4, "happiness": -1}, traits={"ambitious": 1})
        return "You pushed hard in work and made measurable progress."

    def _do_exercise(self) -> str:
        return self._risk({"health": 8, "happiness": 3}, {"health": 2}, 0.35,
                          "Great workout! You feel stronger.", "Minor strain, but still active.",
                          habits={"exercise": 5}, traits={"disciplined": 1}, reason="exercise boosts resilience")

    def _do_socialize(self) -> str:
        return self._risk({"social": 7, "happiness": 4}, {"reputation": -3, "health": -1}, 0.42,
                          "You had a memorable social year.", "Party choices caused small social backlash.",
                          habits={"network": 3, "alcohol": 2}, reason="social risk influenced by alcohol use")

    def _do_romance_action(self) -> str:
        s = self.state
        if s.age < 16:
            return "Too young for romance-focused actions."
        person = Person(self.rng.choice(FIRST_NAMES), "partner", self.rng.randint(-6, 6), self.rng.choice(["bold", "loyal", "funny", "chaotic"]), 45, 50, 55)
        msg = self._risk({"happiness": 4, "social": 3}, {"happiness": -2}, 0.45,
                         f"You and {person.name} started dating.", f"No connection with {person.name}.",
                         reason="romance impacted by looks+charisma")
        if "started dating" in msg:
            s.partners.append(person)
        return msg

    def _do_hustle(self) -> str:
        s = self.state
        if s.stats["intelligence"] > 58:
            return self._risk({"wealth": 12}, {"wealth": -5, "reputation": -3}, 0.4,
                              "Side hustle paid off.", "Hustle failed and cost you cash.", traits={"ambitious": 1}, reason="higher intelligence improves hustles")
        return self._risk({"wealth": 6}, {"wealth": -4}, 0.55,
                          "You made some side income.", "The hustle fizzled.", reason="low skill increased risk")

    def _do_rest(self) -> str:
        self._apply({"health": 3, "happiness": 4}, habits={"alcohol": -1, "drugs": -1})
        return "You prioritized recovery and sleep."

    def _do_travel(self) -> str:
        s = self.state
        cost = 4 + s.assets["luxury"]
        if s.stats["wealth"] < cost:
            return "Not enough money to travel this year."
        return self._risk({"happiness": 8, "social": 2, "wealth": -cost}, {"wealth": -cost - 3, "health": -2}, 0.3,
                          "Travel widened your perspective.", "Travel complications caused stress and expenses.", reason="travel has high reward and financial risk")

    def _do_gamble(self) -> str:
        s = self.state
        s.habits["gambling"] = clamp(s.habits["gambling"] + 5)
        return self._risk({"wealth": 20, "happiness": 3}, {"wealth": -12, "happiness": -4}, 0.65,
                          "Big win at the table.", "You lost heavily gambling.", reason="gambling favors luck and harms discipline")

    def _crime_menu(self) -> str:
        while True:
            print("\nCrime Menu:")
            print("1) Pickpocket")
            print("2) Heist")
            print("3) Gang Politics")
            print("4) Back")
            c = input("Crime choice (1-4): ").strip()
            if c == "1":
                return self._risk({"wealth": 8}, {"criminal_record": 4, "reputation": -6}, 0.52,
                                  "Pickpocketing worked.", "Caught pickpocketing.",
                                  extra_success={"heat": 3}, extra_fail={"heat": 10}, habits={"crime": 4}, traits={"reckless": 1}, reason="street crime has medium arrest risk")
            if c == "2":
                return self._risk({"wealth": 26}, {"wealth": -10, "criminal_record": 12, "happiness": -8}, 0.7,
                                  "Heist succeeded with huge payout.", "Heist collapsed and brought serious charges.",
                                  extra_success={"heat": 16}, extra_fail={"heat": 30}, habits={"crime": 8}, traits={"reckless": 2}, reason="major crime: very high reward/high risk")
            if c == "3":
                return self._risk({"wealth": 12}, {"health": -8, "criminal_record": 7}, 0.6,
                                  "You gained gang influence.", "Gang conflict turned violent.",
                                  extra_success={"gang_rank": 2, "heat": 10}, extra_fail={"heat": 18}, habits={"crime": 6}, traits={"reckless": 1}, reason="gang politics scale with heat")
            if c == "4":
                return "You backed out of criminal action."
            print("Invalid crime choice.")

    def _do_buy_assets(self) -> str:
        s = self.state
        print("Buy: 1) House(35) 2) Car(12) 3) Luxury(9) 4) Pet(7) 5) Cancel")
        c = input("Choice: ").strip()
        cost_map = {"1": ("house", 35), "2": ("car", 12), "3": ("luxury", 9), "4": ("pet", 7)}
        if c not in cost_map:
            return "No purchase made."
        item, cost = cost_map[c]
        if s.stats["wealth"] < cost:
            return "Not enough wealth."
        s.stats["wealth"] = clamp(s.stats["wealth"] - cost)
        s.assets[item] += 1
        if item == "pet":
            self._apply({"happiness": 5, "social": 2}, memory="You adopted a pet.")
        else:
            self._apply({"happiness": 2}, memory=f"You bought a {item}.")
        return f"Purchased {item}."

    def _do_invest(self) -> str:
        s = self.state
        if s.stats["wealth"] < 8:
            return "Not enough cash to invest."
        stake = min(20, s.stats["wealth"] // 3)
        s.stats["wealth"] = clamp(s.stats["wealth"] - stake)
        if self.rng.random() < 0.55:
            gain = int(stake * self.rng.uniform(1.1, 1.8))
            s.investments += gain
            return f"Investment rose; portfolio +{gain}."
        loss = int(stake * self.rng.uniform(0.4, 1.0))
        s.debt += loss
        return f"Investment crashed; added debt +{loss}."

    def _do_appearance(self) -> str:
        s = self.state
        if s.stats["wealth"] < 10:
            return "Appearance upgrade too expensive this year."
        msg = self._risk({"looks": 7, "happiness": 3, "wealth": -10}, {"looks": -5, "health": -4, "wealth": -12}, 0.5,
                         "Procedure improved your confidence and looks.", "Procedure complications hurt your health.", reason="plastic surgery has visible upside and risk")
        if "Procedure improved your confidence and looks." in msg:
            s.looks_desc = self.rng.choice(LOOKS)
        return msg

    def _do_volunteer(self) -> str:
        self._apply({"reputation": 6, "happiness": 2, "social": 2}, traits={"kind": 2})
        return "You volunteered and built community goodwill."

    def _do_therapy(self) -> str:
        s = self.state
        cost = 5
        if s.stats["wealth"] >= cost:
            self._apply({"wealth": -cost, "happiness": 6, "health": 2}, habits={"alcohol": -2, "drugs": -2, "substance": -2})
            return "Therapy/meditation improved your mental state."
        self._apply({"happiness": 2})
        return "You used low-cost self-help routines and felt somewhat better."

    def _do_business(self) -> str:
        s = self.state
        if s.assets["business"] == 0:
            if s.stats["wealth"] < 25:
                return "Need at least 25 wealth to start a business."
            s.stats["wealth"] = clamp(s.stats["wealth"] - 25)
            s.assets["business"] = 1
            return "You launched a small business."
        return self._risk({"wealth": 15, "reputation": 2}, {"wealth": -9, "happiness": -3}, 0.48,
                          "Business year was profitable.", "Business downturn hurt cash flow.", reason="business outcomes are market-sensitive")

    # ----------------------- state systems -----------------------

    def _base_tick(self):
        s = self.state
        s.stats["health"] = clamp(s.stats["health"] - self.rng.randint(0, 2) + s.habits["exercise"] // 8 - s.habits["substance"] // 10)
        s.stats["happiness"] = clamp(s.stats["happiness"] - self.rng.randint(0, 3) + s.hidden["resilience"] // 22)
        s.stats["social"] = clamp(s.stats["social"] - self.rng.randint(0, 2) + s.habits["network"] // 8)
        s.stats["reputation"] = clamp(s.stats["reputation"] - s.criminal_record // 9)

        if s.prison_years > 0:
            s.prison_years -= 1
            self._apply({"happiness": -4, "wealth": -3})
            print("You spent this year in prison.")

    def _economy_tick(self):
        s = self.state
        passive = s.assets["house"] * 3 + s.assets["business"] * 12 + s.investments // 8
        upkeep = s.assets["car"] * 2 + s.assets["luxury"] * 2 + int(s.debt * 0.08)
        taxes = max(0, s.stats["wealth"] // 25)
        s.stats["wealth"] = clamp(s.stats["wealth"] + passive - upkeep - taxes)

        if s.debt > 0:
            s.debt = int(s.debt * 1.05)
            if s.debt > 60:
                self._apply({"happiness": -3, "reputation": -2})

    def _addiction_tick(self):
        s = self.state
        addiction_load = s.habits["alcohol"] + s.habits["drugs"] + s.habits["gambling"]
        s.habits["substance"] = clamp(addiction_load // 3)
        if addiction_load > 120:
            self._apply({"health": -9, "happiness": -6, "wealth": -5}, memory="Severe addiction spiral this year.")
        elif addiction_load > 70:
            self._apply({"health": -5, "happiness": -3}, memory="Addiction symptoms disrupted your year.")
        if addiction_load > 40 and self.rng.random() < 0.25:
            self._apply({"happiness": -3}, memory="Withdrawal episodes increased stress.")

    def _relationship_manager(self):
        s = self.state
        everyone = [p for p in (s.partners + s.friends + s.relatives) if p.alive]
        for p in everyone:
            if "betrayed" in " ".join(p.memory).lower():
                p.trust = clamp(p.trust - 12)
            if s.age - p.last_interaction > 2:
                p.closeness = clamp(p.closeness - 3)
            p.last_interaction = s.age

        if s.partners and self.rng.random() < 0.18:
            partner = self.rng.choice([p for p in s.partners if p.alive])
            print(f"Relationship moment with {partner.name}:")
            print("1) Gift")
            print("2) Fight")
            print("3) Reconcile")
            print("4) Break up")
            c = input("Choice (1-4, Enter skip): ").strip()
            if c == "1":
                if s.stats["wealth"] >= 4:
                    self._apply({"wealth": -4, "happiness": 2, "social": 1}, memory=f"You gifted {partner.name}.")
                    partner.trust = clamp(partner.trust + 7)
                else:
                    self._apply({"happiness": -1})
            elif c == "2":
                self._apply({"happiness": -2, "social": -1}, memory=f"You fought with {partner.name}.")
                partner.trust = clamp(partner.trust - 10)
                partner.memory.append("betrayed")
            elif c == "3":
                self._apply({"happiness": 2}, memory=f"You reconciled with {partner.name}.")
                partner.trust = clamp(partner.trust + 5)
            elif c == "4":
                partner.alive = False
                self._apply({"happiness": -5}, memory=f"You broke up with {partner.name}.")
            elif c:
                self._apply({"happiness": -1}, memory="An awkward relationship moment passed without resolution.")

        # family growth / child-rearing flavor
        if s.partners and self.rng.random() < 0.14 and s.age > 21:
            child = Person(self.rng.choice(FIRST_NAMES), "child", -s.age, self.rng.choice(["calm", "curious", "wild"]), 55, 55)
            s.children.append(child)
            s.memories.append(f"Birth moment: child {child.name} was born.")

    def _npc_world_tick(self):
        s = self.state
        everyone = s.relatives + s.friends + s.partners + s.flings + s.children
        for p in everyone:
            if not p.alive:
                continue
            if self.rng.random() < 0.02 and s.age > 18:
                p.memory.append("had a major life transition")
                p.mood = clamp(p.mood + self.rng.randint(-6, 6))
            if self.rng.random() < 0.012 and s.age > 45:
                p.alive = False
                s.memories.append(f"Funeral: {p.name} ({p.kind}) passed away.")

        if 10 <= s.age <= 75 and self.rng.random() < 0.13:
            f = Person(self.rng.choice(FIRST_NAMES), self.rng.choice(["friend", "coworker"]), self.rng.randint(-5, 5),
                       self.rng.choice(["loyal", "dramatic", "strategic", "funny"]), self.rng.randint(30, 70), self.rng.randint(25, 70))
            s.friends.append(f)
            print(f"You met {f.name} ({f.kind}, {f.personality}).")

    def _career_tick(self):
        s = self.state
        if s.prison_years > 0:
            return
        if s.age < 16:
            return

        if s.career == "none" and s.age >= 18:
            if s.habits["crime"] > 35 or s.criminal_record > 18:
                s.career = "criminal"
            elif s.fame > 35:
                s.career = "creator"
            elif s.education_level in {"college", "graduate"}:
                s.career = self.rng.choice(["engineering", "medicine", "law", "research"])
            else:
                s.career = self.rng.choice(["retail", "construction", "service", "unemployed"])

        if s.career == "unemployed":
            s.unemployed_years += 1
            self._apply({"happiness": -2})
            if self.rng.random() < 0.35:
                s.career = self.rng.choice(["retail", "service"])
        else:
            pay = 0
            if s.career in {"retail", "construction", "service"}:
                pay = 8 + s.career_level * 2
            elif s.career in {"engineering", "medicine", "law", "research"}:
                pay = 16 + s.career_level * 6
                self._apply({"intelligence": 1})
            elif s.career == "creator":
                pay = 2 + s.fame // 4
                s.fame = clamp(s.fame + self.rng.randint(-2, 6))
            elif s.career == "criminal":
                pay = 6 + s.gang_rank * 3 + s.habits["crime"] // 4
                s.heat += self.rng.randint(1, 7)

            boss_drama = self.rng.random() < 0.2
            if boss_drama:
                self._apply({"happiness": -2, "reputation": -1}, memory="Workplace drama with boss/coworkers.")

            promo = 0.09 + s.traits["disciplined"] / 120 + s.hidden["luck"] / 500
            if self.rng.random() < promo:
                s.career_level += 1
                self._apply({"reputation": 2}, memory="Promotion gained this year.")
            s.stats["wealth"] = clamp(s.stats["wealth"] + pay)

    def _achievement_tick(self):
        s = self.state
        def unlock(key: str, msg: str):
            if not s.achievements.get(key):
                s.achievements[key] = True
                print(f"[RIBBON UNLOCKED] {msg}")

        if s.career == "criminal" and s.gang_rank >= 4:
            unlock("crime_lord", "Crime Lord")
        if s.stats["reputation"] > 90 and s.fame > 60:
            unlock("icon", "Cultural Icon")
        if s.age >= 80 and s.stats["health"] > 70:
            unlock("iron_body", "Iron Body")
        if s.children and s.generation >= 2:
            unlock("legacy_builder", "Legacy Builder")

    def _death_check(self):
        s = self.state
        risk = max(0, s.age - 58) * 0.8 + max(0, 40 - s.stats["health"]) * 1.2 + s.heat * 0.2 + self.rng.uniform(0, 35)
        if s.age >= 100 or risk > 95:
            s.alive = False
            s.cause_of_death = self.rng.choice([
                "natural causes", "sudden illness", "freak accident", "medical complication", "stress collapse"
            ])

    # ----------------------- generic event engine -----------------------

    def _choose_events(self, n: int) -> List[EventDef]:
        weighted = []
        for ev in self.events:
            w = self._event_weight(ev)
            if w > 0:
                weighted.append((ev, w))
        out = []
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
            out.append(weighted[idx][0])
            weighted.pop(idx)
        return out

    def _event_weight(self, ev: EventDef) -> float:
        s = self.state
        if not (ev.min_age <= s.age <= ev.max_age):
            return 0.0
        if ev.once_per_life and s.once_flags.get(ev.key):
            return 0.0
        if not ev.condition(s):
            return 0.0
        seen = s.event_history.get(ev.key, 0)
        rep_penalty = 0.5 ** seen
        boost = 1.3 if ev.category == "crime" and s.habits["crime"] > 20 else 1.0
        return ev.base_weight * rep_penalty * boost * self.rng.uniform(0.84, 1.25)

    def _run_event(self, ev: EventDef):
        s = self.state
        print(f"\n[{ev.category.upper()}] {ev.text(s)}")
        opts = ev.choices(s)
        for i, (lab, _) in enumerate(opts, 1):
            print(f"  {i}) {lab}")
        c = self._read_choice(len(opts))
        msg = opts[c - 1][1](s)
        print(f"  -> {msg}")
        s.event_history[ev.key] = s.event_history.get(ev.key, 0) + 1
        if ev.once_per_life:
            s.once_flags[ev.key] = True

    @staticmethod
    def _read_choice(max_n: int) -> int:
        while True:
            raw = input("Choose: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= max_n:
                return int(raw)
            print("Invalid choice.")

    # ----------------------- helper apply/risk -----------------------

    def _apply(self, stat: Dict[str, int], extra: Optional[Dict[str, int]] = None,
               habits: Optional[Dict[str, int]] = None, traits: Optional[Dict[str, int]] = None,
               memory: Optional[str] = None):
        s = self.state
        for k, v in stat.items():
            if k in s.stats:
                s.stats[k] = clamp(s.stats[k] + v)
            elif k == "looks":
                s.looks = clamp(s.looks + v)
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
        # Safety clamps for core stats and looks after compound changes.
        for key in s.stats:
            s.stats[key] = clamp(s.stats[key])
        s.looks = clamp(s.looks)

    def _risk(self, success: Dict[str, int], fail: Dict[str, int], base_risk: float,
              success_msg: str, fail_msg: str,
              extra_success: Optional[Dict[str, int]] = None,
              extra_fail: Optional[Dict[str, int]] = None,
              habits: Optional[Dict[str, int]] = None,
              traits: Optional[Dict[str, int]] = None,
              reason: str = "") -> str:
        s = self.state
        chance = (1 - base_risk) + s.hidden.get("luck", 50) / 110 + s.traits.get("disciplined", 0) / 240 - s.traits.get("reckless", 0) / 260
        chance += self.rng.uniform(-0.22, 0.22)
        chance = max(0.05, min(0.95, chance))

        if self.rng.random() < chance:
            self._apply(success, extra_success, habits, traits, memory=success_msg)
            return f"{success_msg} {f'(reason: {reason})' if reason else ''}"
        self._apply(fail, extra_fail, habits, traits, memory=fail_msg)
        return f"{fail_msg} {f'(reason: {reason})' if reason else ''}"

    # ----------------------- events -----------------------

    def _build_events(self) -> List[EventDef]:
        core = [self._once_event(), self._school_event(), self._crime_police_event(), self._chaos_event()]
        return core + self._generate_event_pool(220)

    def _once_event(self) -> EventDef:
        return EventDef(
            "once_black_swan", "rare", 16, 80, 1.0, True,
            lambda s: True,
            lambda s: "Once-per-life offer: a mysterious stranger offers a transformative deal.",
            lambda s: [
                ("Accept", lambda st: self._risk({"wealth": 25, "reputation": 6}, {"wealth": -15, "reputation": -8, "happiness": -5}, 0.52,
                                                  "The deal worked out massively.", "The deal backfired badly.", reason="black swan opportunity")),
                ("Decline", lambda st: (self._apply({"health": 2, "happiness": 1}), "You chose stability over a once-per-life gamble.")[1]),
            ]
        )

    def _school_event(self) -> EventDef:
        return EventDef(
            "school_core", "school", 6, 24, 14.0, False,
            lambda s: not s.dropped_out,
            lambda s: f"Academic crossroads: grades {s.grades}, school rep {s.school_rep}.",
            lambda s: [
                ("Study", lambda st: (setattr(self.state, "grades", clamp(self.state.grades + self.rng.randint(4, 10))), self._apply({"intelligence": 3}, habits={"study": 3}), "You improved academically.")[2]),
                ("Cheat", lambda st: self._risk({"intelligence": 1}, {"reputation": -8, "happiness": -2}, 0.5,
                                                "Cheating worked this time.", "Caught cheating.", habits={"crime": 2}, traits={"reckless": 1}, reason="exam surveillance risk")),
                ("Drop out", lambda st: self._drop_out()),
            ]
        )

    def _drop_out(self) -> str:
        s = self.state
        if s.age < 14:
            return "Too young to drop out."
        s.dropped_out = True
        s.education_level = "dropout"
        self._apply({"happiness": 2, "reputation": -5}, memory="Dropped out of school.")
        s.chain_events.append({"age": s.age + 3, "text": "Credential gap closed several job doors.", "fx": lambda ss: setattr(ss, "unemployed_years", ss.unemployed_years + 1)})
        return "You dropped out; short-term relief, long-term consequences."

    def _crime_police_event(self) -> EventDef:
        return EventDef(
            "crime_police", "crime", 15, 95, 10.0, False,
            lambda s: s.heat >= 10 or s.criminal_record >= 8,
            lambda s: f"Police pressure rises (heat {s.heat}, record {s.criminal_record}).",
            lambda s: [
                ("Lay low", lambda st: (self._apply({"wealth": -2}, extra={"heat": -6}), "You reduced visibility.")[1]),
                ("Fight in court", lambda st: self._fight_case()),
                ("Flee city", lambda st: self._risk({"reputation": -2}, {"criminal_record": 6, "happiness": -5}, 0.62,
                                                    "Escape worked for now.", "You were caught fleeing.",
                                                    extra_success={"heat": -7}, extra_fail={"heat": 10}, reason="flee attempt difficulty")),
            ]
        )

    def _fight_case(self) -> str:
        s = self.state
        chance = 0.34 + s.hidden["luck"] / 180 + (8 if s.stats["wealth"] > 20 else 0) / 100 - s.heat / 220
        if self.rng.random() < chance:
            self._apply({"wealth": -8, "reputation": 2}, extra={"heat": -10}, memory="Won a criminal case.")
            return "Case dismissed."
        sentence = self.rng.randint(1, 5)
        s.prison_years += sentence
        s.criminal_record += self.rng.randint(4, 10)
        self._apply({"happiness": -8, "wealth": -6}, memory=f"Lost case, sentenced {sentence} years.")
        return f"Convicted, sentence {sentence} years."

    def _chaos_event(self) -> EventDef:
        return EventDef(
            "chaos_core", "chaos", 12, 95, 6.0, False,
            lambda s: True,
            lambda s: "Wild life moment: scandal, miracle, or absurd twist looms.",
            lambda s: [
                ("Lean in", lambda st: self._risk({"fame": 10, "wealth": 8}, {"reputation": -10, "health": -3}, 0.57,
                                                  "You rode chaos to sudden fame.", "Chaos turned into scandal.", reason="chaos favors volatility")),
                ("Stay low", lambda st: (self._apply({"health": 1, "happiness": -1}), "Quiet year, less upside and downside.")[1]),
            ]
        )

    def _generate_event_pool(self, target: int) -> List[EventDef]:
        themes = [("childhood", 1, 12), ("school", 6, 24), ("career", 18, 95), ("crime", 14, 95),
                  ("social", 10, 95), ("family", 4, 95), ("health", 10, 100), ("finance", 16, 95),
                  ("romance", 16, 80), ("chaos", 12, 95)]
        out = []
        idx = 0
        while len(out) < target:
            for cat, amin, amax in themes:
                if len(out) >= target:
                    break
                n = idx
                level = (n % 5) + 1

                def cond_factory(c: str, lv: int):
                    if c == "crime":
                        return lambda s: s.prison_years == 0 and (s.habits["crime"] > lv * 2 or s.age > 18)
                    if c == "school":
                        return lambda s: not s.dropped_out
                    if c == "romance":
                        return lambda s: s.age >= 16
                    return lambda s: True

                def text_factory(c: str, i: int):
                    return lambda s: f"{c.title()} scenario #{i}: context references your past habits and reputation."

                def choices_factory(c: str, lv: int):
                    def cautious(_: GameState) -> str:
                        self._apply({"reputation": 1, "health": 1}, memory=f"Handled {c} scenario cautiously.")
                        return "You took the careful route."

                    def ambitious(_: GameState) -> str:
                        return self._risk({"wealth": 2 * lv, "happiness": 1}, {"health": -2, "reputation": -2}, 0.46 + lv * 0.04,
                                          "Ambitious move paid off.", "Ambitious move failed.",
                                          extra_success={"heat": 2} if c == "crime" else None,
                                          extra_fail={"criminal_record": 2, "heat": 4} if c == "crime" else None,
                                          habits={"crime": 1} if c == "crime" else {"network": 1},
                                          traits={"ambitious": 1}, reason=f"{c} volatility")

                    def reckless(_: GameState) -> str:
                        return self._risk({"social": 2, "happiness": 2}, {"reputation": -3, "happiness": -2}, 0.58,
                                          "Reckless move made life exciting.", "Reckless move caused fallout.",
                                          habits={"crime": 2} if c == "crime" else {"alcohol": 1},
                                          traits={"reckless": 1}, reason="impulsivity modifier")

                    return [(f"Cautious {c} response", cautious), (f"Ambitious {c} response", ambitious), (f"Reckless {c} response", reckless)]

                out.append(EventDef(
                    key=f"gen_{cat}_{n}",
                    category=cat,
                    min_age=amin,
                    max_age=amax,
                    base_weight=5.0 + (n % 4),
                    once_per_life=False,
                    condition=cond_factory(cat, level),
                    text=text_factory(cat, n),
                    choices=lambda s, c=cat, lv=level: choices_factory(c, lv),
                ))
                idx += 1
        return out

    # ----------------------- chain/save/load/legacy -----------------------

    def _process_chain_events(self):
        s = self.state
        pending = []
        for ch in s.chain_events:
            if s.age >= ch["age"]:
                print(f"[CONSEQUENCE] {ch['text']}")
                ch["fx"](s)
            else:
                pending.append(ch)
        s.chain_events = pending

    def save_game(self):
        fn = f"{self.state.name}_gen{self.state.generation}.save"
        with open(fn, "wb") as f:
            pickle.dump(self.state, f)
        print(f"Saved to {fn}")

    def load_game(self, filename: str):
        with open(filename, "rb") as f:
            self.state = pickle.load(f)
        print(f"Loaded {filename}")

    def _continue_as_child(self) -> bool:
        s = self.state
        choices = [c for c in s.children if c.alive]
        if not choices:
            return False
        print("Choose heir:")
        for i, c in enumerate(choices, 1):
            print(f"  {i}) {c.name} ({c.personality})")
        idx = self._read_choice(len(choices)) - 1
        heir = choices[idx]
        new = GameState(name=heir.name)
        new.generation = s.generation + 1
        new.location = s.location
        new.upbringing = "legacy"
        new.looks = clamp((s.looks + self.rng.randint(20, 80)) / 2)
        new.looks_desc = self.rng.choice(LOOKS)
        new.sexuality = self.rng.choice(SEXUALITY)
        new.stats["wealth"] = clamp(20 + s.stats["wealth"] // 2)
        new.stats["reputation"] = clamp(45 + s.stats["reputation"] // 3)
        new.stats["intelligence"] = clamp(45 + s.stats["intelligence"] // 3)
        new.stats["social"] = clamp(40 + s.stats["social"] // 3)
        new.hidden = {
            "luck": clamp((s.hidden["luck"] + self.rng.randint(20, 80)) / 2),
            "charisma": clamp((s.hidden["charisma"] + self.rng.randint(20, 80)) / 2),
            "resilience": clamp((s.hidden["resilience"] + self.rng.randint(20, 80)) / 2),
            "risk": clamp((s.hidden["risk"] + self.rng.randint(20, 80)) / 2),
        }
        new.habits = {k: clamp(v // 3) for k, v in s.habits.items()}
        new.traits = {k: clamp(v // 2, -20, 100) for k, v in s.traits.items()}
        new.assets = {k: max(0, v // 2) for k, v in s.assets.items()}
        new.career = "none"
        new.career_level = max(0, s.career_level // 3)
        new.investments = max(0, s.investments // 3)
        new.debt = max(0, s.debt // 4)
        new.relatives = [Person(s.name, "parent", 28, "legacy", 60, 60, alive=False, status="deceased")]
        new.memories.append(f"Inherited legacy from {s.name} (gen {s.generation}).")
        self.state = new
        print(f"Legacy continues as {new.name} (generation {new.generation}).")
        return True

    # ----------------------- display -----------------------

    def _summary(self):
        s = self.state
        biggest = s.memories[-1] if s.memories else "No major memory"
        print("\nYear Summary")
        print(f"  Health {s.stats['health']} | Happiness {s.stats['happiness']} | Int {s.stats['intelligence']} | Wealth {s.stats['wealth']} | Social {s.stats['social']} | Reputation {s.stats['reputation']}")
        print(f"  Looks {s.looks} ({s.looks_desc}) | Career {s.career} L{s.career_level} | Record {s.criminal_record} Heat {s.heat} Prison {s.prison_years}")
        print(f"  Assets {s.assets} | Investments {s.investments} | Debt {s.debt}")
        print(f"  Relations: friends {len([x for x in s.friends if x.alive])}, partners {len([x for x in s.partners if x.alive])}, children {len([x for x in s.children if x.alive])}")
        print(f"  Biggest moment: {biggest}")

    def _legacy_summary(self):
        s = self.state
        print("\n" + "=" * 70)
        print(f"{s.name} (generation {s.generation}) died at age {s.age} from {s.cause_of_death}.")
        print(f"Achievements: {', '.join([k for k, v in s.achievements.items() if v]) or 'None'}")
        print(f"Children {len(s.children)} | Fame {s.fame} | Career {s.career} | Wealth {s.stats['wealth']}")
        if s.memories:
            print("Legacy Hall of Fame moments:")
            for m in s.memories[-10:]:
                print(f"  - {m}")


if __name__ == "__main__":
    LifeSimGame().run()
