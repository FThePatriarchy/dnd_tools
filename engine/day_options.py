"""Explicit day-model switches; legacy() reproduces the pre-realism contract."""
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class DayOptions:
    clock: bool = True
    prebuffs: bool = True
    death: bool = True
    backgrounds: bool = True
    engagement: bool = True
    spending: bool = True
    gap_minutes: float = 10
    screen: int = 2
    targeting: str = "threat"
    attack_downed: bool = False

    def __post_init__(self):
        for f in fields(self):
            if f.type is bool and type(getattr(self, f.name)) is not bool:
                raise ValueError(f"{f.name} must be boolean")
        if type(self.gap_minutes) not in (int, float) or not 0 <= self.gap_minutes < float("inf"):
            raise ValueError("gap_minutes must be finite and nonnegative")
        if type(self.screen) is not int or self.screen < 0: raise ValueError("screen must be nonnegative integer")
        if self.targeting not in {"focus_low_hp", "threat", "random"}: raise ValueError("unknown targeting policy")
        if not self.engagement and self.targeting == "threat": object.__setattr__(self,"targeting","focus_low_hp")

    @classmethod
    def legacy(cls):
        return cls(clock=False, prebuffs=False, death=False, backgrounds=False,
                   engagement=False, spending=False, targeting="focus_low_hp")


def day_options(value=None):
    if isinstance(value, DayOptions): return value
    if value is None: return DayOptions()
    if not isinstance(value, dict): raise ValueError("day options must be a mapping")
    try: return DayOptions(**value)
    except TypeError as exc: raise ValueError(str(exc)) from exc
