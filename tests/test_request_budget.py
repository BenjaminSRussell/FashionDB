import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reddit_db"))
from request_budget import RequestBudget


def test_daily_max_exhausted_with_fake_clock():
    sleeps = []
    budget = RequestBudget(requests_per_minute=1000, daily_max=3)
    assert budget.wait_turn(sleep=sleeps.append) is True
    assert budget.wait_turn(sleep=sleeps.append) is True
    assert budget.wait_turn(sleep=sleeps.append) is True
    assert budget.exhausted is True
    assert budget.wait_turn(sleep=sleeps.append) is False
    assert budget.remaining_today() == 0


def test_rpm_paces_requests():
    sleeps = []
    budget = RequestBudget(requests_per_minute=2, daily_max=10)
    assert budget.wait_turn(now=1000.0, sleep=sleeps.append) is True
    assert budget.wait_turn(now=1000.0, sleep=sleeps.append) is True
    assert budget.wait_turn(now=1000.0, sleep=sleeps.append) is True
    assert sleeps  # paced
