import abc
import argparse
import multiprocessing
import random
import signal
import sys
import time
import traceback

from ctypes import c_bool, c_double
from multiprocessing.sharedctypes import Value
from typing import List, Type


RATE_DECAY = 0.25
RATE_SLEEP_K = 0.5


class Worker(abc.ABC):
    def __init__(self, count: int = None, rate: float = None):
        self._count = count
        self._target_rate = rate
        self._proc = None
        self._cur_rate = Value(c_double, 0.0)
        self._done = Value(c_bool, False)

    @property
    def cur_rate(self) -> float:
        return self._cur_rate.value

    @property
    def done(self) -> bool:
        return self._done.value

    @abc.abstractmethod
    def initialize(self):
        pass

    @abc.abstractmethod
    def request(self) -> int:
        pass

    def start(self):
        self._proc = multiprocessing.Process(target=self._worker)
        self._proc.start()

    def join(self):
        self._proc.join()

    def _worker(self):
        random.seed()

        try:
            self.initialize()
        except:
            traceback.print_exc()
            self._done.value = True
            return

        rate_avg = None
        rate_sleep = 0 if self._target_rate is None else None

        i = 0
        while self._count is None or i < self._count:
            num_reqs = 0
            t1 = time.time()
            for _ in range(5):
                try:
                    num_reqs += self.request()
                except:
                    traceback.print_exc()
                    self._done.value = True
                    return
            t2 = time.time()
            req_time = (t2 - t1) / num_reqs

            if rate_sleep is None:
                rate_sleep = 1 / self._target_rate - req_time
                if rate_sleep < 0:
                    rate_sleep = 0

            rate_inst = 1 / (req_time + rate_sleep)
            if rate_avg is None:
                rate_avg = rate_inst
            else:
                rate_avg = (1 - RATE_DECAY) * rate_avg + RATE_DECAY * rate_inst

            self._cur_rate.value = rate_avg

            if self._target_rate is not None:
                cur_period = 1 / rate_avg
                target_period = 1 / self._target_rate
                delta = target_period - cur_period
                rate_sleep += RATE_SLEEP_K * delta
                if rate_sleep < 0:
                    rate_sleep = 0

            if rate_sleep:
                time.sleep(rate_sleep)

            i += num_reqs

        self._done.value = True


class Benchmark:
    def __init__(self, workers: List[Worker], refresh: int):
        self._workers = workers
        self._refresh = refresh

    def add_worker(self, worker: Worker):
        self._workers.append(worker)

    def run(self):
        for worker in self._workers:
            worker.start()

        signal.signal(signal.SIGALRM, self._alarm_handler)
        signal.alarm(self._refresh)

        for worker in self._workers:
            worker.join()

        self._print_summary()

    def _alarm_handler(self, signum, stack):
        self._print_summary()
        signal.alarm(self._refresh)

    def _print_summary(self):
        num_done = len([worker for worker in self._workers if worker.done])
        num_running = len(self._workers) - num_done

        rates = [worker.cur_rate for worker in self._workers]

        print(
            f'{num_running} workers, {sum(rates):.2f} req/s '
            f'({min(rates):.2f} - {max(rates):.2f})')
        sys.stdout.flush()

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        parser.add_argument('-c', '--count', type=int, default=None,
                            help='Number of requests to perform per worker.')
        parser.add_argument('-r', '--rate', type=float, default=None,
                            help='Total request rate (req/s).')
        parser.add_argument('-j', '--jobs', type=int,
                            default=1, help='Parallel workers.')
        parser.add_argument('-R', '--refresh', type=int,
                            default=1, help='Refresh rate, in seconds.')

    @staticmethod
    def from_args(cmd_args: argparse.Namespace, worker_cls: Type[Worker], *args, **kwargs):
        worker_rate = cmd_args.rate / cmd_args.jobs if cmd_args.rate is not None else None
        workers = [
            worker_cls(count=cmd_args.count,
                       rate=worker_rate, *args, **kwargs)
            for _ in range(cmd_args.jobs)
        ]
        return Benchmark(workers, cmd_args.refresh)
