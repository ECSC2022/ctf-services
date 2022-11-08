import random

from typing import Callable, Tuple

from ctf_gameserver.checkerlib import BaseChecker, CheckResult


class RandomScheduler:
    def __init__(self):
        self._tasks = {}

    def add_task(self, func: Callable, name: str, *deps: str, prob: float = 1.0):
        assert name not in self._tasks, f'Redefined task: {name}'
        for dep in deps:
            assert dep in self._tasks, f'Unknown dependency: {dep}'
        self._tasks[name] = (func, set(deps), prob)

    def task(self, *args, **kwargs):
        def decorator(func):
            self.add_task(func, *args, **kwargs)
            return func
        return decorator

    def schedule(self, run_all=False):
        names = list(self._tasks.keys())

        sched = []
        processed = set()
        scheduled = set()
        have_new_scheduled = True
        while have_new_scheduled:
            have_new_scheduled = False
            random.shuffle(names)
            for name in names:
                if name in processed:
                    continue
                func, deps, prob = self._tasks[name]
                if not deps.issubset(scheduled):
                    continue
                processed.add(name)
                if run_all or random.random() < prob:
                    sched.append(func)
                    scheduled.add(name)
                    have_new_scheduled = True
                    break

        return sched


class RandomChecker(BaseChecker):
    def __init__(self, checks_scheduler: RandomScheduler, ip: str, team: str):
        super().__init__(ip, team)
        self._checks_scheduler = checks_scheduler

    def check_service(self) -> Tuple[CheckResult, str]:
        sched = self._checks_scheduler.schedule()
        for check in sched:
            result, msg = self.before_check()
            if result != CheckResult.OK:
                return result, msg
            result, msg = check(self)
            if result != CheckResult.OK:
                return result, msg
        return CheckResult.OK, ''

    def before_check(self) -> Tuple[CheckResult, str]:
        return CheckResult.OK, ''
