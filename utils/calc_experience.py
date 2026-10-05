from data_types import Experience
from datetime import date

def calc_yoe(experiences: list[Experience]) -> int:

    if not experiences:
        return 0

    intervals = sorted(
        (e.start_date, e.end_date or date.today()) for e in experiences
    )

    merged: list[tuple[date, date]] = []
    cur_start, cur_end = intervals[0]

    for start, end in intervals[1:]:
        if start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))

    total_days = sum((end - start).days for start, end in merged)
    return int(total_days / 365)

