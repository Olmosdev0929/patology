"""SuperMemo-2 spaced repetition with Anki-style answer buttons."""
from dataclasses import dataclass
from datetime import date, timedelta

# Anki buttons mapped to SM-2 quality grades (0–5).
GRADES = {"again": 1, "hard": 3, "good": 4, "easy": 5}
MIN_EF = 1.3


@dataclass
class CardState:
    interval: int = 0
    reps: int = 0
    easiness: float = 2.5
    lapses: int = 0


def review(state: CardState, answer: str, today: date | None = None) -> tuple[CardState, date]:
    """Return the new card state and next review date."""
    if answer not in GRADES:
        raise ValueError(f"answer must be one of {list(GRADES)}")
    q = GRADES[answer]
    today = today or date.today()

    ef = state.easiness + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ef = max(MIN_EF, round(ef, 4))

    if q < 3:
        # Failed recall: restart the repetition sequence, review again tomorrow.
        new = CardState(interval=1, reps=0, easiness=ef, lapses=state.lapses + 1)
    else:
        if state.reps == 0:
            interval = 1
        elif state.reps == 1:
            interval = 6
        else:
            interval = round(state.interval * ef)
        if answer == "easy":
            interval = max(interval, round(interval * 1.3))  # Anki-style easy bonus
        new = CardState(interval=max(1, interval), reps=state.reps + 1, easiness=ef, lapses=state.lapses)
    return new, today + timedelta(days=new.interval)
