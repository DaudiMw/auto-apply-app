from datetime import date
from data_types import Experience
from utils.calc_experience import calc_yoe


def test_calc_yoe_empty():
    assert calc_yoe([]) == 0


def test_calc_yoe_single_experience():
    exp = Experience(
        employer_name="Company A",
        title="Developer",
        city="NYC",
        description="Coding",
        start_date=date(2020, 1, 1),
        end_date=date(2022, 1, 1),
    )
    assert calc_yoe([exp]) == 2


def test_calc_yoe_overlapping_intervals():
    # Exp 1: 2020 to 2022 (2 years)
    exp1 = Experience(
        employer_name="Company A",
        title="Developer",
        city="NYC",
        description="Coding",
        start_date=date(2020, 1, 1),
        end_date=date(2022, 1, 1),
    )
    # Exp 2: 2021 to 2023 (overlaps by 1 year, combined 2020-2023 = 3 years)
    exp2 = Experience(
        employer_name="Company B",
        title="Consultant",
        city="NYC",
        description="Consulting",
        start_date=date(2021, 1, 1),
        end_date=date(2023, 1, 1),
    )
    assert calc_yoe([exp1, exp2]) == 3
