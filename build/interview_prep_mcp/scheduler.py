"""SM-2 spaced repetition algorithm."""
from datetime import date, timedelta
from typing import Tuple


def sm2(
    quality: int,          # 0-5: 0=blackout, 3=correct-effort, 5=perfect
    repetitions: int,
    ease_factor: float,
    interval: int,
) -> Tuple[int, float, int, str]:
    """
    Returns (new_repetitions, new_ease_factor, new_interval, next_review_date_str).
    quality < 3 resets the card; quality >= 3 advances it.
    """
    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * ease_factor)
        repetitions += 1

    ease_factor = max(1.3, ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    next_review = (date.today() + timedelta(days=interval)).isoformat()
    return repetitions, ease_factor, interval, next_review


def result_to_quality(result: str) -> int:
    """Map a log_problem result string to an SM-2 quality score."""
    return {"solved": 4, "hint": 2, "stuck": 1, "reviewed": 3}.get(result, 2)
