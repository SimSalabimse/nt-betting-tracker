from __future__ import annotations

from typing import Callable

from nt.research_gates.profiles import basketball, darts, default, football, snooker, tennis
from nt.research_gates.types import GateContext, GateResult

ProfileFn = Callable[[GateContext, GateResult], None]

PROFILES: dict[str, ProfileFn] = {
    "football": football.apply,
    "tennis": tennis.apply,
    "basketball": basketball.apply,
    "darts": darts.apply,
    "snooker": snooker.apply,
    "hockey": default.apply,
    "handball": default.apply,
    "volleyball": default.apply,
    "esports": default.apply,
    "baseball": default.apply,
    "default": default.apply,
}


def get_profile(sport: str) -> ProfileFn:
    return PROFILES.get(sport, default.apply)
