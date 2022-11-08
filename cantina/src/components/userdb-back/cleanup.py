#!/usr/bin/env python3
import signal
import sqlite3
import os
from pathlib import Path
from threading import Event


def do_cleanup(data_dir: Path):
    # Cleanup sqlite database
    con = sqlite3.connect(data_dir / "user.db")
    with con:
        cur = con.cursor()
        cur.execute('delete from users where created <= datetime("now", "-30 minute")')
        print(f"Deleted rows: {cur.rowcount}")
    con.close()


if __name__ == '__main__':
    stop = Event()

    def quit(_, __):
        stop.set()
    for sig in('TERM', 'HUP', 'INT'):
        signal.signal(getattr(signal, 'SIG'+sig), quit)

    data_dir = Path(os.environ.get("DATA_DIR", "/data"))

    while not stop.is_set():
        do_cleanup(data_dir)
        stop.wait(120)
