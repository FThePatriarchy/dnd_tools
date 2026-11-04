"""Adventuring-day presets: how many fights between long rests, how hard, and where the short rests fall.

The 2024 DMG gives XP budgets per fight but, unlike the 2014 DMG (6-8 medium or
hard encounters with about two short rests), no number of encounters per day.
Informal table polls put most groups at 2-5 combats per long rest. The default
here, "typical", is the day the project's user described: an easy fight, a hard
fight, a short rest, another easy fight, then a boss.

A preset is a list of slots: ("fight", difficulty, shape) or ("rest", "short"|"long").
Difficulty is a 2024 DMG budget (low, moderate, high) for the party, or "easy",
half of Low; shape is an engine.templates template. A day "scale" multiplies
every budget in the day.

Calibration note (2026-11-03): at full DMG budgets the simulated L5 standard
party does not survive a four-fight day (Low, High, short rest, Low, High boss
killed it in every run), and each Low fight costs it about 40% of its spell
slots. The DMG's 2024 budgets are per fight, not built to be chained, and the
simulated party plays without retreat, positioning or potions. So "typical" uses
easy (half Low) for its easy fights, and the scale lets a table match its own
days. Judge a fight in a day as a comparison, not an absolute. make_day fills each fight with real monsters
(seeded, so the same day comes back for the same seed) and can put a given
encounter in one slot, so a fight can be judged in its place in a day.
"""
from .calibration import budget

DIFFICULTY = {"easy": ("low", 0.5), "low": ("low", 1.0), "moderate": ("moderate", 1.0), "high": ("high", 1.0)}
FALLBACK_SHAPES = ("mixed", "elite_pack", "boss_minions", "swarm", "solo")
VARIETY = 8  # each fight is a seeded pick among this many lead monsters whose best fill is closest to its budget

PRESETS = {
    "typical": {"label": "Typical: easy, hard, short rest, easy, boss",
                "slots": [("fight", "easy", "mixed"), ("fight", "high", "elite_pack"), ("rest", "short"),
                          ("fight", "easy", "swarm"), ("fight", "high", "boss_minions")]},
    "short": {"label": "Short: hard, short rest, boss",
              "slots": [("fight", "high", "elite_pack"), ("rest", "short"), ("fight", "high", "boss_minions")]},
    "long": {"label": "Long (2014 DMG): six moderate/high fights, two short rests",
             "slots": [("fight", "moderate", "mixed"), ("fight", "high", "elite_pack"), ("rest", "short"),
                       ("fight", "moderate", "swarm"), ("fight", "high", "mixed"), ("rest", "short"),
                       ("fight", "moderate", "elite_pack"), ("fight", "high", "boss_minions")]},
}
DEFAULT = "typical"


def validate_slots(slots):
    from .templates import TEMPLATES
    if not isinstance(slots, (list, tuple)) or not slots: raise ValueError("a day needs at least one slot")
    if len(slots) > 16: raise ValueError("a day has at most 16 slots")
    for s in slots:
        if s[0] == "rest":
            if len(s) != 2 or s[1] not in ("short", "long"): raise ValueError("a rest slot is ('rest', 'short'|'long')")
        elif s[0] == "fight":
            if len(s) != 3 or s[1] not in DIFFICULTY or s[2] not in TEMPLATES:
                raise ValueError(f"a fight slot is ('fight', {'|'.join(DIFFICULTY)}, {'|'.join(TEMPLATES)})")
        else: raise ValueError("a slot is a fight or a rest")
    if not any(s[0] == "fight" for s in slots): raise ValueError("a day needs at least one fight")


def fight_slots(preset, slots=None):
    """Indices (into the slots) of the fights, and a label for each."""
    slots = slots or PRESETS[preset]["slots"]
    return [(i, f"fight {n + 1} ({s[1]}, {s[2].replace('_', ' ')})") for n, (i, s) in enumerate((i, s) for i, s in enumerate(slots) if s[0] == "fight")]


def boss_slot(preset, slots=None):
    """The slot a "how does this fight play in my day" question uses by default: the last fight."""
    return fight_slots(preset, slots)[-1][0]


def make_day(preset, level, size=4, *, seed=1, themes=None, fight=None, slot=None, exclude=None, scale=1.0, slots=None):
    """A day definition for engine.day: each fight slot filled at its DMG budget for the party.

    fight (a list of entries like "ogre x2") replaces the fight in slot (default: the last fight).
    Returns (day, labels) where labels describe each step."""
    import random
    from .templates import DEFAULT_EXCLUDE, TEMPLATES, encounter_entries, fills, themed
    if slots is None:
        if preset not in PRESETS: raise ValueError(f"unknown day preset {preset!r}; presets are {', '.join(PRESETS)}")
        slots = PRESETS[preset]["slots"]
    validate_slots(slots)
    if not 0.05 <= scale <= 5: raise ValueError("scale must be between 0.05 and 5")
    if fight is not None and slot is None: slot = boss_slot(preset, slots)
    if slot is not None and (not 0 <= slot < len(slots) or slots[slot][0] != "fight"): raise ValueError("slot must be one of the preset's fights")
    steps, labels = [], []
    for i, s in enumerate(slots):
        if s[0] == "rest":
            steps.append({"rest": s[1]}); labels.append(f"{s[1]} rest"); continue
        _, difficulty, shape = s
        if i == slot and fight is not None:
            steps.append({"encounter": list(fight)}); labels.append("your fight: " + ", ".join(fight)); continue
        base, factor = DIFFICULTY[difficulty]
        total = budget(level, base, size) * factor * scale
        skip = DEFAULT_EXCLUDE if exclude is None else exclude
        picks = None
        for theme in ([themes, None] if themes else [None]):  # the theme first; any monster if it has no fill
            for s_ in (shape,) + tuple(x for x in FALLBACK_SHAPES if x != shape):
                legal = fills(TEMPLATES[s_], total, exclude=skip, monsters=themed(theme) if theme else None)
                # A seeded pick among the closest fills, varied by lead monster (each fill's first role),
                # so different seeds give different days and one strong boss type doesn't take every slot.
                best = {}
                for f in legal: best.setdefault(f[0][0][1], f)
                varied = sorted(best.values(), key=lambda f: total - f[1])[:VARIETY]
                picks = [random.Random(f"{seed}:{i}").choice(varied)] if varied else None
                if picks: break
            if picks: break
        if not picks: raise ValueError(f"no fill for a level {level} {difficulty} budget ({total:,.0f} XP)")
        fill, xp = picks[0]
        steps.append({"encounter": encounter_entries(fill)})
        labels.append(f"{difficulty} {s_.replace('_', ' ')}: " + ", ".join(f"{n} {m.replace('_', ' ')}" for _, m, n, _ in fill) + f" ({xp:,} XP)")
    return {"name": f"{preset} day", "steps": steps}, labels
