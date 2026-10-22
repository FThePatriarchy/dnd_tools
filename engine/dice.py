"""All randomness is supplied by the caller."""
import random
import re

DICE = re.compile(r"^(\d+)d(\d+)(?:\s*([+-])\s*(\d+))?$")


def parts(value: str) -> tuple[int, int, int]:
    match = DICE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"invalid dice: {value!r}")
    n, sides, sign, bonus = match.groups()
    if int(n) < 1 or int(sides) < 1:
        raise ValueError(f"invalid dice: {value!r}")
    return int(n), int(sides), int(bonus or 0) * (-1 if sign == "-" else 1)


def roll(rng: random.Random, value: str, critical: bool = False) -> int:
    n, sides, bonus = parts(value)
    return sum(rng.randint(1, sides) for _ in range(n * (2 if critical else 1))) + bonus


def mean(value: str) -> float:
    n, sides, bonus = parts(value)
    return n * (sides + 1) / 2 + bonus


def add(value: str, increment: str, count: int) -> str:
    n, sides, bonus = parts(value)
    dn, ds, db = parts(increment)
    if sides != ds:
        raise ValueError("scaling must use the same die size")
    total = bonus + db * count
    return f"{n + dn * count}d{sides}" + (f"{total:+d}" if total else "")


def d20(rng: random.Random, advantage: bool = False, disadvantage: bool = False) -> int:
    first = rng.randint(1, 20)
    if advantage == disadvantage:
        return first
    second = rng.randint(1, 20)
    return max(first, second) if advantage else min(first, second)
