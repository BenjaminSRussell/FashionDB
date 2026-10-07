"""Request budget + RPM throttle for Reddit scrapes."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RequestBudget:
    """Track requests against RPM and daily caps.

    ``now`` is injectable for tests (seconds since epoch).
    """

    requests_per_minute: float = 30.0
    daily_max: int = 2000
    _count: int = 0
    _window_start: float = field(default_factory=time.time)
    _window_count: int = 0
    exhausted: bool = False

    def remaining_today(self) -> int:
        return max(0, int(self.daily_max) - self._count)

    def allow(self, *, now: float | None = None) -> bool:
        """Return True if another request may proceed; False if daily budget done."""
        if self._count >= self.daily_max:
            self.exhausted = True
            return False
        return True

    def wait_turn(self, *, now: float | None = None, sleep=time.sleep) -> bool:
        """Block for RPM spacing, then consume one request slot.

        Returns False when daily budget is exhausted (caller should stop).
        """
        now = time.time() if now is None else now
        if not self.allow(now=now):
            return False

        # RPM window
        rpm = max(float(self.requests_per_minute), 0.01)
        min_interval = 60.0 / rpm
        if self._window_count == 0:
            self._window_start = now
        elapsed = now - self._window_start
        if self._window_count >= rpm:
            # new minute window
            sleep_for = max(0.0, 60.0 - elapsed)
            if sleep_for > 0:
                sleep(sleep_for)
                now = time.time() if now is None else now + sleep_for
            self._window_start = now
            self._window_count = 0
        else:
            # pace within the minute
            target = self._window_start + self._window_count * min_interval
            sleep_for = max(0.0, target - now)
            if sleep_for > 0:
                sleep(sleep_for)

        self._window_count += 1
        self._count += 1
        if self._count >= self.daily_max:
            self.exhausted = True
        return True
